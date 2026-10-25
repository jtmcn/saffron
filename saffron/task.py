"""Driving one task: a resolved spec and a pinned base in, a `CellOutcome` or
a `Refused` out.

The span is one task from `CellSpec` to packaged pull request — a cell *and*
PACKAGE, which is why this is neither `cell/` nor `phases/`. `CONTEXT.md` §2
already has the word for it: a **task** is one spec being executed.

**Why it is a module and not two copies.** `cli._run_cell` (attended) and
`cli._batch_runner.run` (unattended) drove a task with the same sixty lines
written twice, and the copies drifted: only the attended one resolved and
printed the ceilings, so the path that runs with nobody watching kept no
record of what bounded it. `batch.py` names the cause in its own `runner`
docstring — the resolvers this needs were `cli`-private, and `cli.py` was
`forbidden` to the spec that built the loop.

What stays outside, deliberately, except the refusals named below:

- **The refusals and the mirror fetch.** They run at different times on the
  two paths for good reasons — a batch refuses at scan time so a night never
  pays for the cell, and pays for the mirror once per run (§4.2.1); an
  attended run has no scan and pays per task. Folding either in would force
  one of those to move.
- **The one exception.** An unresolved `consumes` entry needs the tree base
  it must resolve against. Neither caller knows that base until
  `_resolve_stacked_on` has run, so this refusal returns `Refused` from here
  instead.
- **The other exception.** A stack batch's recorded spec text (ADR 7) is not
  at `base_sha`. The scan never reads it, so `run_task` re-runs the gate 0
  refusals that need no GitHub against it, keyed on `task_id`. The open-PR
  and dependency refusals are not re-run.
- **`CELL_EXIT`.** An exit code is the process contract `saffron cell` owes a
  script, not a fact about a task; `run_batch` would have to ignore it.
- **The `CLAUDE_CODE_OAUTH_TOKEN` read.** Scoped to the invocation
  (`CLAUDE.md`), so it is read at the edge and passed. A module that reaches
  into `os.environ` is one a test has to reach into too.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import get_args

from saffron import preflight, spec_review
from saffron.agents import context
from saffron.agents.findings import Finding
from saffron.cell import runtime
from saffron.cell.session import _SHA as _RESOLVED_SHA
from saffron.cell.session import CellOutcome, CellSpec, LiveState, run_one_cell
from saffron.events import (
    Ceiling,
    Ceilings,
    CeilingSource,
    Event,
    EventLog,
    Preflight,
    Teardown,
    describe,
)
from saffron.intake import Spec, SpecError, discover_specs, parse_spec
from saffron.ledger import Ledger, _ledger_time
from saffron.phases import package as package_phase
from saffron.phases.rebut import (
    LensVerdicts,
    RebutResult,
    Rebuttal,
    RebuttalTurn,
    Verdict,
    sustained_blockers,
    unkept_fixes,
)
from saffron.phases.review import LensReview, anchored_blockers, anchored_concerns
from saffron.reconcile import GhRunner, reconcile
from saffron.record.contract import RecordError
from saffron.report import index as index_report
from saffron.repos import image as repo_image
from saffron.repos.mirror import (
    GitError,
    UnreadablePath,
    _run,
    ensure_mirror,
    export_saffron_dir,
    file_at,
    has_commit,
    retirement_markers,
    unresolved_consumes,
)
from saffron.repos.policy import load_policy
from saffron.scheduler import (
    DEPENDENCY_WAITING_STATES,
    _branch,
    _deepest_open_parent,
    _retired_ids,
    _unmatched_criterion_path,
    protected_touch_refusal,
    retirement_refusal,
)

# `_resolve_stacked_on`'s accepted states once a `gh` reconciles the parent.
# `CHANGES_REQUESTED` joins only on that path. Its review fixes land on its branch.
_STACKABLE_ON_RECONCILE = DEPENDENCY_WAITING_STATES | frozenset({"CHANGES_REQUESTED"})


@dataclass(frozen=True, kw_only=True)
class Handoff:
    """What a stack batch hands a task in place of `_resolve_stacked_on`
    (`SA-0143`): the predecessor's tree and its branch, decided once by the
    batch's own planned order rather than re-derived from the ledger.

    The two travel together or not at all, `PinnedBase`'s reason for
    `kw_only`: `stacked_on` and `target_branch` are adjacent strings, and a
    positional swap would type-check and stack a cell on the wrong tree.
    """

    stacked_on: str | None
    target_branch: str | None

    def __post_init__(self) -> None:
        if (self.stacked_on is None) != (self.target_branch is None):
            raise ValueError(
                "a Handoff carries both stacked_on and target_branch, or neither"
            )


@dataclass(frozen=True, kw_only=True)
class PinnedBase:
    """The tree one night is pinned to — one fact about one repo, carried
    together rather than as three adjacent parameters. `check_readiness`
    already derives exactly these three values and returns them on
    `Readiness`; this is what a caller hands back to `cli._resolve_queue` and
    to `run_task` so the derivation happens once per run, not once per caller.

    `kw_only` for the reason `check_readiness` itself is keyword-only about
    `scratch`/`home`: `url` and `base_sha` are adjacent and both `str`, and
    positionally `PinnedBase(mirror, base_sha, url)` type-checks cleanly and
    puts the URL in `base_sha` — measured, before the keyword-only was added."""

    mirror: Path
    url: str
    base_sha: str


@dataclass(frozen=True, kw_only=True)
class ResolvedCeilings:
    """The three ceilings that bound one task, each with where it came from.

    One value rather than two parallel dicts keyed by the same three names,
    and not a `dict` at all: `CellSpec` takes these three by keyword among
    fourteen, and `CellSpec(**ceilings)` is a construction no type checker can
    see into. Splatting an untyped mapping into the widest constructor in the
    codebase is the drift this module was extracted to end, reintroduced one
    layer down.

    `kw_only` for `PinnedBase`'s reason: `max_attempts` and `max_turns` are
    adjacent and both `int`, so positionally they swap cleanly and silently.

    Distinct from `events.Ceilings`, which is this plus an envelope — the
    event is what gets *recorded*, this is what gets *applied*, and only one
    of the two belongs in a `CellSpec`.
    """

    budget_usd: float
    max_attempts: int
    max_turns: int
    budget_source: CeilingSource
    attempts_source: CeilingSource
    turns_source: CeilingSource


def spec_ceilings(spec: Spec) -> ResolvedCeilings:
    """The three ceilings a spec declares, and where each came from.

    The half of `cli._ceilings` that has nothing to do with flags, so the
    unattended path can say what bound a task without growing an `argparse`
    dependency it has no use for. "spec" only where the author actually wrote
    the field: `model_fields_set` is what separates a declared value from a
    model default that happens to equal it.
    """

    def _source(name: str) -> CeilingSource:
        return "spec" if name in spec.model_fields_set else "default"

    return ResolvedCeilings(
        budget_usd=spec.budget_usd,
        max_attempts=spec.max_attempts,
        max_turns=spec.max_turns,
        budget_source=_source("budget_usd"),
        attempts_source=_source("max_attempts"),
        turns_source=_source("max_turns"),
    )


class _StackingRefused(Exception):
    """Raised inside `_resolve_stacked_on` when two or more open parents
    lie on no one chain (b-1572e7). Also raised when an on-chain
    parent's fetched head is not an ancestor of the deepest parent's.
    `run_task` catches this and returns `Refused` before any cell
    starts."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _is_ancestor(mirror: Path, maybe_ancestor: str, descendant: str) -> bool:
    """Whether `maybe_ancestor` reaches `descendant` in `mirror`, the way
    `cli._pushed_landed` asks it. `rev-parse --verify` first, because
    `merge-base --is-ancestor` alone exits 128 for a missing commit too."""
    verify = _run(
        [
            "git",
            "-C",
            str(mirror),
            "rev-parse",
            "--verify",
            "--quiet",
            f"{maybe_ancestor}^{{commit}}",
        ]
    )
    if verify.returncode == 1:
        return False
    if verify.returncode != 0:
        raise GitError(
            f"git rev-parse --verify {maybe_ancestor}: {verify.stderr.strip()}"
        )
    ancestor = _run(
        [
            "git",
            "-C",
            str(mirror),
            "merge-base",
            "--is-ancestor",
            maybe_ancestor,
            descendant,
        ]
    )
    if ancestor.returncode == 0:
        return True
    if ancestor.returncode == 1:
        return False
    raise GitError(
        f"git merge-base {maybe_ancestor}..{descendant}: {ancestor.stderr.strip()}"
    )


def _newest_stackable(
    rows: list[sqlite3.Row], stackable_states: frozenset[str]
) -> sqlite3.Row | None:
    """The newest of `rows` in `stackable_states`, the row a parent stacks from."""
    stackable = [row for row in rows if row["state"] in stackable_states]
    return stackable[-1] if stackable else None


def _fetch_parent_head(
    branch: str | None,
    pushed_sha: str | None,
    *,
    parent_id: str,
    mirror: Path,
    url: str,
    spec_id: str,
    emit: Callable[[Event], None],
) -> tuple[str | None, str | None]:
    """The fetched head and `branch` of a parent's newest waiting row, or
    `(None, None)` after an `unstacked` line.

    `ParentGone` is an unstacked cell, not a failure. A deleted branch
    either merged, so its work is on the default branch, or was
    abandoned, where the default branch is the safe cut.
    """
    # Refused here rather than left to the fetch: a row that evidences no push
    # has no branch worth fetching, and "branch None is gone" would send an
    # operator to look for a deleted ref instead of at the row.
    if not branch or not _RESOLVED_SHA.fullmatch(pushed_sha or ""):
        emit(
            Preflight(
                timestamp=time.time(),
                spec_id=spec_id,
                step="unstacked",
                detail=f"{parent_id}'s newest waiting task records no pushed branch",
            )
        )
        return None, None
    try:
        head = package_phase.fetch_parent_branch(mirror, url, branch)
    except package_phase.ParentGone as gone:
        emit(
            Preflight(
                timestamp=time.time(),
                spec_id=spec_id,
                step="unstacked",
                detail=str(gone),
            )
        )
        return None, None
    if not _RESOLVED_SHA.fullmatch(head):
        return None, None
    return head, branch


def _resolve_multi_parent(
    ledger: Ledger,
    repo_id: int,
    depends_on: list[str],
    *,
    mirror: Path,
    url: str,
    base_sha: str | None,
    spec_id: str,
    emit: Callable[[Event], None],
    gh: GhRunner | None,
) -> tuple[str | None, str | None]:
    """`_resolve_stacked_on`'s rule for two or more `depends_on` entries
    (b-1572e7): the scan's own open-parent rule, applied to every entry.

    A parent with no task counts for nothing, the gap the module
    docstring names. Once one remains, `.saffron` is exported at
    `base_sha` to read every live spec's `depends_on` and `specs/done/`.
    Every open parent must lie on the deepest one's chain, or this
    raises `_StackingRefused`, as must each fetched head against it.
    """
    rows_by_dep: dict[str, list[sqlite3.Row]] = {}
    for dep in depends_on:
        if gh is not None:
            reconciled = reconcile(ledger, repo_id, gh=gh, spec_id=dep)
            if reconciled.unasked:
                emit(
                    Preflight(
                        timestamp=time.time(),
                        spec_id=spec_id,
                        step="gh_unreachable",
                        detail=(
                            f"GitHub could not be asked whether {dep}'s "
                            "pull request merged"
                        ),
                    )
                )
        rows = ledger.tasks_by_spec_id(repo_id, dep)
        if rows:
            rows_by_dep[dep] = rows

    if not rows_by_dep:
        return None, None
    if base_sha is None:
        raise ValueError(
            "_resolve_stacked_on needs base_sha once a depends_on entry has a task"
        )

    with tempfile.TemporaryDirectory() as scratch:
        exported = export_saffron_dir(mirror, base_sha, Path(scratch) / "at-base")
        specs_dir = exported / ".saffron" / "specs"
        retired_ids, _retired_failures = _retired_ids(specs_dir)
        discovered, _failures = discover_specs(specs_dir)
    edges = {d.spec.id: d.spec.depends_on for d in discovered}

    stackable_states = (
        _STACKABLE_ON_RECONCILE if gh is not None else DEPENDENCY_WAITING_STATES
    )
    stack_rows: dict[str, sqlite3.Row] = {}
    for dep, rows in rows_by_dep.items():
        if any(row["state"] == "MERGED" for row in rows):
            continue
        if dep in retired_ids:
            continue
        if any(
            row["pushed_sha"] and _is_ancestor(mirror, row["pushed_sha"], base_sha)
            for row in rows
        ):
            continue
        newest = _newest_stackable(rows, stackable_states)
        if newest is not None:
            stack_rows[dep] = newest

    if not stack_rows:
        return None, None

    open_set = frozenset(stack_rows)
    chosen, off_chain = _deepest_open_parent(open_set, open_set, edges)
    assert chosen is not None
    if off_chain:
        names = ", ".join(sorted(off_chain))
        verb = "is" if len(off_chain) == 1 else "are"
        raise _StackingRefused(
            f"depends_on {names} {verb} outside {chosen}'s depends_on "
            "chain, and no spec may stack on two unrelated open parents"
        )

    chosen_row = stack_rows[chosen]
    if chosen_row["state"] == "CHANGES_REQUESTED":
        emit(
            Preflight(
                timestamp=time.time(),
                spec_id=spec_id,
                step="changes_requested",
                detail=f"newest task is CHANGES_REQUESTED for {chosen}",
            )
        )
    stacked = _fetch_parent_head(
        chosen_row["branch"],
        chosen_row["pushed_sha"],
        parent_id=chosen,
        mirror=mirror,
        url=url,
        spec_id=spec_id,
        emit=emit,
    )
    head, branch = stacked
    if head is None:
        return stacked

    for dep in sorted(open_set - {chosen}):
        dep_row = stack_rows[dep]
        dep_branch = dep_row["branch"]
        if not dep_branch or not _RESOLVED_SHA.fullmatch(dep_row["pushed_sha"] or ""):
            continue
        try:
            dep_head = package_phase.fetch_parent_branch(mirror, url, dep_branch)
        except package_phase.ParentGone:
            continue
        if not _is_ancestor(mirror, dep_head, head):
            raise _StackingRefused(
                f"depends_on {dep}'s branch {dep_branch} is not an ancestor "
                f"of {chosen}'s branch {branch}"
            )

    return stacked


def _resolve_stacked_on(
    ledger: Ledger,
    repo_id: int | None,
    depends_on: list[str],
    *,
    mirror: Path,
    url: str,
    spec_id: str,
    emit: Callable[[Event], None] = lambda event: print(describe(event)),
    gh: GhRunner | None = None,
    base_sha: str | None = None,
) -> tuple[str | None, str | None]:
    """The tree sha `CellSpec.stacked_on` should carry and the branch name
    `package()`'s stacking parameter should carry, or `(None, None)`
    together for an ordinary unstacked cell. Never one without the other,
    since a worktree stacked on a sha whose pull request targets `main`
    is exactly the defect `SA-0026` closed.

    One entry stacks on its own newest waiting row, by the rule below. Two
    or more apply `_resolve_multi_parent`'s rule instead (b-1572e7), which
    needs `base_sha` once any entry has a task. Raises `_StackingRefused`,
    which `run_task` turns into `Refused` before any cell starts.
    """
    if repo_id is None or not depends_on:
        return None, None
    if len(depends_on) > 1:
        return _resolve_multi_parent(
            ledger,
            repo_id,
            depends_on,
            mirror=mirror,
            url=url,
            base_sha=base_sha,
            spec_id=spec_id,
            emit=emit,
            gh=gh,
        )
    parent_id = depends_on[0]
    if gh is None:
        rows = ledger.tasks_by_spec_id(repo_id, parent_id)
        waiting = [row for row in rows if row["state"] in DEPENDENCY_WAITING_STATES]
        if not waiting:
            return None, None
        newest = waiting[-1]
    else:
        # Narrowed to this one spec, and read only after it comes back
        # (`b-877e93`), so a stale merge is never stacked on by accident.
        reconciled = reconcile(ledger, repo_id, gh=gh, spec_id=parent_id)
        rows = ledger.tasks_by_spec_id(repo_id, parent_id)
        if not rows:
            return None, None
        # A merged or closed newest task unstacks. Else the newest stackable row stacks.
        # An older pending row shares that branch, so it would restack on the merge.
        newest_task = rows[-1]
        stackable = [row for row in rows if row["state"] in _STACKABLE_ON_RECONCILE]
        if newest_task["state"] in {"MERGED", "REJECTED"} or not stackable:
            emit(
                Preflight(
                    timestamp=time.time(),
                    spec_id=spec_id,
                    step="unstacked",
                    detail=f"{parent_id}'s newest task is {newest_task['state']}",
                )
            )
            return None, None
        newest = stackable[-1]
        if newest["task_id"] in reconciled.unasked:
            emit(
                Preflight(
                    timestamp=time.time(),
                    spec_id=spec_id,
                    step="gh_unreachable",
                    detail=(
                        f"GitHub could not be asked whether {parent_id}'s "
                        "pull request merged"
                    ),
                )
            )
        if newest["state"] == "CHANGES_REQUESTED":
            emit(
                Preflight(
                    timestamp=time.time(),
                    spec_id=spec_id,
                    step="changes_requested",
                    detail=f"newest task is CHANGES_REQUESTED for {parent_id}",
                )
            )
    # The branch is fetched rather than `pushed_sha` trusted, since a review
    # fix moves the branch past the recorded push.
    return _fetch_parent_head(
        newest["branch"],
        newest["pushed_sha"],
        parent_id=parent_id,
        mirror=mirror,
        url=url,
        spec_id=spec_id,
        emit=emit,
    )


@dataclass(frozen=True, kw_only=True)
class Refused:
    """A task rejected before any cell starts (`CONTEXT.md`'s **Refusal**).

    A `consumes` entry did not resolve at the tree base, or the reader could
    not read it there. Or, for a task holding a stack batch's recorded spec
    text (ADR 7), a gate 0 refusal that needs no GitHub refused that text.
    Carries only `reason`, the same text `run_task` prints on the refused
    line. No run and no task row exist for a caller to read anything else
    back from."""

    reason: str


# The attribute a marked exception carries, private to this module.
_RAISED_IN_PACKAGE = "_saffron_raised_in_package"


def mark_raised_in_package(exc: BaseException) -> None:
    """Mark `exc` as having escaped `run_task`'s own `package_phase.package`
    call for a `READY_FOR_REVIEW` cell. The mark lives on the object itself.
    A bare re-raise of the same instance still carries it wherever a batch
    next catches it. `run_task` never marks an exhausted-mode raise:
    `saffron package` refuses a task that is not `READY_FOR_REVIEW`, so
    naming that command for one would send the operator to a refusal
    (`b-066901`)."""
    setattr(exc, _RAISED_IN_PACKAGE, True)


def raised_in_package(exc: BaseException) -> bool:
    """True for an exception `mark_raised_in_package` marked. False for any
    other, a fresh never-raised one included. The mark lives on the object,
    never on its type, so a caller cannot read it off the class."""
    return bool(getattr(exc, _RAISED_IN_PACKAGE, False))


def _recorded_spec_text(
    ledger: Ledger, task_id: int, spec: Spec, base: PinnedBase
) -> tuple[Spec, str] | Refused | None:
    """Gate 0's refusals that need no GitHub, re-run against a stack batch's
    recorded spec text (ADR 7) and keyed on `task_id`. Checks the task's latest
    `spec_texts` row in order: its own hash, `parse_spec`, the id,
    `depends_on`, and each ceiling. Then a follow-up task's `touches`, a
    `revision` row's path, `protected_touch_refusal`,
    `_unmatched_criterion_path` and `retirement_refusal` against
    `.saffron/` exported at `base`. Returns the parsed text and its
    `spec_sha`, a `Refused`, or `None` for a task with no text. A
    `GitError` or `PolicyError` from a read below is left to propagate."""
    row = ledger.spec_text(task_id)
    if row is None:
        return None
    n = row["n"]

    def _refused(detail: str) -> Refused:
        return Refused(reason=f"task {task_id}'s text {n} {detail}")

    if hashlib.sha256(row["text"].encode()).hexdigest() != row["spec_sha"]:
        return _refused("does not hash to its spec_sha")

    try:
        text_spec = parse_spec(row["text"])
    except SpecError as exc:
        # A YAML error's own message can span lines with runs of spaces
        # after each break. The refused line collapses to one line.
        return _refused(f"does not parse: {' '.join(str(exc).split())}")

    if text_spec.id != spec.id:
        return _refused(f"declares {text_spec.id}, not {spec.id}")

    if text_spec.depends_on != spec.depends_on:
        return _refused(
            f"depends_on {text_spec.depends_on} differs from {spec.depends_on}"
        )

    for field in get_args(Ceiling):
        theirs, ours = getattr(text_spec, field), getattr(spec, field)
        if theirs > ours:
            return _refused(f"{field} {theirs} exceeds the handed spec's {ours}")

    texts = ledger.spec_texts(task_id)
    first_row = texts[0]
    if first_row["origin"] == "follow_up":
        try:
            first_spec = parse_spec(first_row["text"])
        except SpecError as exc:
            detail = " ".join(str(exc).split())
            first_n = first_row["n"]
            return _refused(
                f"follows first text {first_n}, which does not parse: {detail}"
            )
        widened = sorted(set(text_spec.touches) - set(first_spec.touches))
        if widened:
            return _refused(f"widens touches beyond text {first_row['n']}'s: {widened}")

    if row["origin"] == "revision":
        earlier_same_path = any(t["path"] == row["path"] for t in texts if t["n"] < n)
        if not earlier_same_path:
            is_own_file = False
            file_text = file_at(base.mirror, base.base_sha, row["path"])
            if file_text is not None:
                try:
                    is_own_file = parse_spec(file_text).id == spec.id
                except SpecError:
                    is_own_file = False
            if not is_own_file:
                return _refused(f"is at {row['path']!r}, not the task's spec file")

    with tempfile.TemporaryDirectory() as scratch:
        exported = export_saffron_dir(base.mirror, base.base_sha, Path(scratch))
        policy, _policy_sha = load_policy(exported)

    if (
        reason := protected_touch_refusal(
            text_spec.touches, policy.protected, text_spec.forbidden
        )
    ) is not None:
        return _refused(reason)

    if (escaped := _unmatched_criterion_path(text_spec)) is not None:
        return _refused(
            f"acceptance criteria name {escaped!r}, which no touches pattern matches"
        )

    markers = retirement_markers(base.mirror, base.base_sha)
    if (reason := retirement_refusal(text_spec, markers)) is not None:
        return _refused(reason)

    return text_spec, row["spec_sha"]


def run_task(
    spec: Spec,
    spec_sha: str,
    *,
    ceilings: ResolvedCeilings,
    base: PinnedBase,
    repo_id: int | None,
    repo: Path,
    ledger: Ledger,
    out_dir: Path,
    token: str | None,
    handoff: Handoff | None = None,
    # `_stack_runner` passes the candidate's own task, so its cell runs on
    # that task instead of minting a fresh one (§4.2.1).
    task_id: int | None = None,
    emit: Callable[[Event], None] | None = None,
    # `cli._run_cell`'s reason for a `gh`: it reaches `_resolve_stacked_on`,
    # which reconciles the parent before it stacks on one (`b-877e93`).
    gh: GhRunner | None = None,
) -> CellOutcome | Refused:
    """One task, start to finish: stack it if it has a parent, run its cell,
    and package a reviewable or standing-blocker `EXHAUSTED` result alike.

    A given `handoff` replaces `_resolve_stacked_on` (`Handoff`, `SA-0143`).
    Given a `task_id`, `_recorded_spec_text` runs first and rebinds `spec`,
    `spec_sha` and `ceilings` to the task's recorded text (ADR 7). `state`
    on the outcome is PACKAGE's own, not the pre-packaging
    `READY_FOR_REVIEW`. Returns `Refused` before any cell exists: for an
    unresolved `spec.consumes`, a refused recorded text, or open parents
    on no one chain (`b-1572e7`). A base the mirror lacks raises `GitError`."""
    if task_id is not None:
        recorded = _recorded_spec_text(ledger, task_id, spec, base)
        if isinstance(recorded, Refused):
            print(f"{spec.id:<10} refused  {recorded.reason}")
            return recorded
        if recorded is not None:
            spec, spec_sha = recorded
            ceilings = spec_ceilings(spec)

    if emit is None:
        # Print plus the task's own log, the shape `session._default_emit` and
        # `package()` both default to: a caller that passes nothing must still
        # get `events.jsonl`. A print-only default is the defect item 43 is
        # about, and is not this.
        log = EventLog(out_dir / spec.id, token=token)
        # ponytail: re-derives `EventLog`'s private path, since it has no accessor.
        log_path = out_dir / spec.id / "events.jsonl"

        def emit(event: Event) -> None:
            line = describe(event)
            if line:
                print(line)
            # `failed` never resets, so its flip is seen once. Printed, never
            # appended: the log is what failed.
            was_failed = log.failed
            log.append(event)
            if log.failed and not was_failed:
                print(f"warning: {log_path} refused a write; events may be missing")

    # Emitted here, not by either caller: a ceiling printed on one path only
    # is the defect this module ends.
    emit(
        Ceilings(
            timestamp=time.time(),
            spec_id=spec.id,
            budget_usd=ceilings.budget_usd,
            max_attempts=ceilings.max_attempts,
            max_turns=ceilings.max_turns,
            budget_source=ceilings.budget_source,
            attempts_source=ceilings.attempts_source,
            turns_source=ceilings.turns_source,
        )
    )

    # Resolved from the deepest open parent's newest waiting task, or
    # `(None, None)` for an unstacked cell (`SA-0026`, `b-1572e7`).
    if handoff is not None:
        stacked_on, target_branch = handoff.stacked_on, handoff.target_branch
    else:
        try:
            stacked_on, target_branch = _resolve_stacked_on(
                ledger,
                repo_id,
                spec.depends_on,
                mirror=base.mirror,
                url=base.url,
                base_sha=base.base_sha,
                spec_id=spec.id,
                emit=emit,
                gh=gh,
            )
        except _StackingRefused as refused:
            print(f"{spec.id:<10} refused  {refused.reason}")
            return Refused(reason=refused.reason)
    # Which tree a run was cut from is not recoverable from the exit code, and
    # a stacked run that surprises an operator is one they cannot diagnose.
    # ponytail: a `print`, so `events.jsonl` carries the *negative* stacking
    # decision (`unstacked:`, a `Preflight`) and not the positive one, and no
    # kind carries `CellSpec.stacked_on` at all. Backlog item 43.
    if stacked_on is not None:
        print(f"stacked on {target_branch} @ {stacked_on[:12]}")

    cell_spec = CellSpec(
        spec_id=spec.id,
        spec_sha=spec_sha,
        branch=_branch(spec.id),
        base_sha=base.base_sha,
        touches=spec.touches,
        spec_type=spec.spec_type,
        body=spec.body + context.estimate_section(spec.estimated_lines),
        forbidden=spec.forbidden,
        acceptance=spec.acceptance,
        risk=spec.risk,
        declared_risk=spec.declared_risk,
        history=spec.history,
        stacked_on=stacked_on,
        budget_usd=ceilings.budget_usd,
        max_attempts=ceilings.max_attempts,
        max_turns=ceilings.max_turns,
        task_id=task_id,
    )
    # A `consumes` entry resolves against the tree base `CellSpec` names.
    # An entry the reader cannot read joins the unresolved ones by name.
    if spec.consumes:
        tree_base = cell_spec.tree_base
        if not has_commit(base.mirror, tree_base):
            raise GitError(f"{tree_base} is not a commit {base.mirror} holds")
        unresolved: list[str] = []
        for entry in spec.consumes:
            try:
                unresolved += unresolved_consumes(base.mirror, tree_base, [entry])
            except (UnreadablePath, UnicodeDecodeError):
                unresolved.append(entry)
        if unresolved:
            reason = f"{tree_base[:12]} does not resolve {', '.join(unresolved)}"
            print(f"{spec.id:<10} refused  {reason}")
            return Refused(reason=reason)

    def _live_row(state: str) -> index_report.QueueLine:
        return index_report.QueueLine(
            repo=repo.name,
            spec_id=spec.id,
            state=state,
            attempts=0,
            cost_usd_est=None,
            concerns=0,
            added=0,
            removed=0,
            link="",
            risk=spec.risk,
        )

    # A live row never stops a running cell. `written` flips only on a
    # landed write, so a raise past only failed ones stamps no row.
    written = False

    def _write_live(state: LiveState) -> None:
        nonlocal written
        try:
            index_report.append_queue_line(
                out_dir,
                _live_row(state),
                header={
                    "trailing accept rate": index_report.trailing_accept_rate(ledger)
                },
            )
        except Exception as exc:
            print(f"{spec.id}: the live row for {state} could not be written: {exc}")
            return
        written = True

    try:
        outcome = run_one_cell(
            cell_spec,
            repo=repo,
            mirror=base.mirror,
            ledger=ledger,
            out_dir=out_dir,
            emit=emit,
            on_state=_write_live,
        )
    except BaseException:
        if written:
            try:
                index_report.append_queue_line(
                    out_dir,
                    _live_row("ORPHANED"),
                    header={
                        "trailing accept rate": index_report.trailing_accept_rate(
                            ledger
                        )
                    },
                )
            except Exception as exc:
                print(
                    f"{spec.id}: the live row for ORPHANED could not be written: {exc}"
                )
        raise
    # Everything below runs only when `run_one_cell` returned, never
    # when it raised: that path above already re-raised past this point.
    try:
        # SA-0204: an EXHAUSTED cell with gates green and a standing blocker
        # still reaches package(), in its exhausted mode.
        exhausted_package = (
            outcome.state == "EXHAUSTED"
            and outcome.rebut_result is None
            and bool(anchored_blockers(outcome.reviews))
        )
        if outcome.state == "READY_FOR_REVIEW" or exhausted_package:
            package_error_note: str | None = None
            try:
                result = package_phase.package(
                    outcome,
                    spec=spec,
                    repo=repo,
                    mirror=base.mirror,
                    # Derived, not rebuilt: preflight already built this tag.
                    image=repo_image.cell_tag(repo),
                    ledger=ledger,
                    out_dir=out_dir,
                    token=token,
                    # `None` unless `stacked_on` is too: a stacked worktree must not
                    # reach a pull request that is not.
                    parent_branch=target_branch,
                    exhausted=exhausted_package,
                    emit=emit,
                )
            except package_phase.PackageError as exc:
                # Only in the exhausted mode: a READY_FOR_REVIEW cell's error
                # still reaches cli.main (exit 2), as it always has.
                if not exhausted_package:
                    # The cell's own write stopped short of this state
                    # (b-dce9a4), so the raise path writes it here instead.
                    ledger.set_task_state(outcome.task_id, "READY_FOR_REVIEW")
                    # Marked so a batch names `saffron package` and closes `INFRASTRUCTURE`.
                    # The breaker still counts it like any raise (`b-066901`).
                    mark_raised_in_package(exc)
                    raise
                result = None
                package_error_note = str(exc)
            except BaseException as exc:
                # Any other raise, `KeyboardInterrupt` included, leaves the
                # same row in flight unless this writes it (b-dce9a4).
                if not exhausted_package:
                    ledger.set_task_state(outcome.task_id, "READY_FOR_REVIEW")
                    mark_raised_in_package(exc)
                raise
            else:
                print(f"{spec.id:<10} {result.state}  {result.pr_url or result.note}")
                outcome.state = result.state
            if exhausted_package and (result is None or not result.pr_url):
                # No pull request either way, refused or raised, so the branch
                # is pushed as any `EXHAUSTED` task's, told why PACKAGE did not open one.
                package_note = result.note if result is not None else package_error_note
                pushed = package_phase.push_unpackaged_work(
                    outcome,
                    spec=spec,
                    repo=repo,
                    mirror=base.mirror,
                    out_dir=out_dir,
                    repo_id=repo_id,
                    ledger=ledger,
                    token=token,
                    package_refusal=package_note,
                    emit=emit,
                )
                combined_note = f"{package_note}; {pushed.note}"
                # This overwrites a refusal's `_finish` row, since `append_queue_line`
                # upserts on `(repo, spec_id)`. A raised PACKAGE wrote none.
                index_report.append_queue_line(
                    out_dir,
                    index_report.QueueLine(
                        repo=repo.name,
                        spec_id=spec.id,
                        state="EXHAUSTED",
                        attempts=outcome.attempts,
                        cost_usd_est=outcome.spent_usd,
                        concerns=anchored_concerns(outcome.reviews),
                        added=0,
                        removed=0,
                        link="",
                        note=combined_note,
                        risk=outcome.effective_risk,
                        sustained=sustained_blockers(outcome.rebut_result),
                        unkept=unkept_fixes(outcome.rebut_result),
                    ),
                    header={
                        "trailing accept rate": index_report.trailing_accept_rate(
                            ledger
                        )
                    },
                )
                print(f"{spec.id:<10} EXHAUSTED  {combined_note}")
                outcome.state = "EXHAUSTED"
        else:
            # PACKAGE never ran, but teardown may still have exported commits to
            # the cell's own branch (backlog item 45, `SA-0069`). Never packaged,
            # and never allowed to change `outcome.state`: a caller reading
            # `MERGE_FAILED` or `READY_FOR_REVIEW` here would believe PACKAGE ran.
            pushed = package_phase.push_unpackaged_work(
                outcome,
                spec=spec,
                repo=repo,
                mirror=base.mirror,
                out_dir=out_dir,
                repo_id=repo_id,
                ledger=ledger,
                token=token,
                emit=emit,
            )
            # `_finish` never ran, so this is the task's only row. No pull request
            # exists, so `link` stays empty; a pushed branch is already in `note`.
            index_report.append_queue_line(
                out_dir,
                index_report.QueueLine(
                    repo=repo.name,
                    spec_id=spec.id,
                    state=outcome.state,
                    attempts=outcome.attempts,
                    cost_usd_est=outcome.spent_usd,
                    concerns=anchored_concerns(outcome.reviews),
                    added=0,
                    removed=0,
                    link="",
                    note=pushed.note,
                    risk=outcome.effective_risk,
                    sustained=sustained_blockers(outcome.rebut_result),
                    unkept=unkept_fixes(outcome.rebut_result),
                ),
                header={
                    "trailing accept rate": index_report.trailing_accept_rate(ledger)
                },
            )
            print(f"{spec.id:<10} {outcome.state}  {pushed.note}")
    finally:
        try:
            ledger.push_record(outcome.task_id)
        except (RecordError, OSError) as exc:
            emit(
                Teardown(
                    timestamp=time.time(),
                    spec_id=spec.id,
                    step="record_push",
                    ok=False,
                    detail=f"record push refused: {exc}",
                )
            )
    return outcome


# A spec session charged to this task outside its own cell is not this
# cell's own spend.
_NOT_THIS_CELLS_PHASE = frozenset({"SPEC_REVIEW", spec_review.WRITING_PHASE})
# The repair loop's own phases. The live cell's outcome leaves the rebuttal's
# re-run out of its count, measured on tasks 240 and 249.
_SUITE_PHASES = frozenset({"IMPLEMENTING", "REPAIRING"})


@dataclass(frozen=True, kw_only=True)
class ReadyTask:
    """What `ready_task` rebuilds for a `READY_FOR_REVIEW` task whose
    `package()` raised. Carries a live-shaped `outcome`, the `spec` the
    task ran, and the `parent_branch` it stacked on, or `None` unstacked."""

    outcome: CellOutcome
    spec: Spec
    parent_branch: str | None


def _newest_for_spec(rows: list[sqlite3.Row], spec_id: str) -> sqlite3.Row | None:
    """The last row naming `spec_id`, or `None`. `tasks_by_repo` and
    `tasks_by_spec_id` both order oldest first, so the last match is the
    newest task."""
    matches = [row for row in rows if row["spec_id"] == spec_id]
    return matches[-1] if matches else None


def _cell_cutoff(baseline_path: Path) -> str:
    """`baseline.json`'s own mtime, floored to the second and rendered in
    UTC by `ledger._ledger_time`, the way it renders `started_at`. A plain
    text comparison, never a parsed one, decides which turns are this cell's."""
    floored = int(baseline_path.stat().st_mtime)
    return _ledger_time(datetime.fromtimestamp(floored, tz=UTC).isoformat())


def _spec_for_task(
    ledger: Ledger, repo: Path, repo_id: int, spec_id: str, task_id: int
) -> Spec | Refused:
    """The spec text the task ran. Its newest recorded text, or the file
    under `.saffron/specs/` (`done/` included) whose bytes hash to the
    task's own `spec_sha`."""
    recorded = ledger.spec_text(task_id)
    if recorded is not None:
        try:
            return parse_spec(recorded["text"])
        except SpecError as exc:
            return Refused(
                reason=f"task {task_id}'s recorded text does not parse: {exc}"
            )

    own = _newest_for_spec(ledger.tasks_by_spec_id(repo_id, spec_id), spec_id)
    spec_sha = own["spec_sha"] if own is not None else None
    if spec_sha is None:
        return Refused(reason=f"task {task_id} carries no recorded spec_sha")

    specs_dir = repo / ".saffron" / "specs"
    candidates = sorted(specs_dir.rglob(f"{spec_id}*.md")) if specs_dir.is_dir() else []
    for candidate in candidates:
        if hashlib.sha256(candidate.read_bytes()).hexdigest() == spec_sha:
            try:
                return parse_spec(candidate.read_text())
            except SpecError:
                continue
    return Refused(reason=f"no spec file under {specs_dir} hashes to {spec_sha[:12]}")


def _rebuild_rebut_result(task_dir: Path) -> RebutResult:
    """`rebuttal.json` rebuilt into a `RebutResult`, with a bare
    `RebuttalTurn`. Its `cost_usd` and `session_id` are not in the file,
    and no reader of the result reads either."""
    data = json.loads((task_dir / "rebuttal.json").read_text())
    rebuttal = data["rebuttal"]
    return RebutResult(
        state=data["state"],
        why=data["why"],
        rebuttal=RebuttalTurn(
            rebuttals=[Rebuttal(**r) for r in rebuttal["rebuttals"]],
            error=rebuttal["error"],
        ),
        verdicts=[
            LensVerdicts(
                lens=v["lens"],
                verdicts=[Verdict(**d) for d in v["verdicts"]],
                cost_usd=v["cost_usd"],
                error=v["error"],
                never_started=v["never_started"],
                quote_failures=v["quote_failures"],
                withdrawal_refusals=v["withdrawal_refusals"],
            )
            for v in data["verdicts"]
        ],
        moved=data["head_moved"],
        cost_usd=data["cost_usd"],
    )


def _task_branch(ledger: Ledger, repo_id: int, row: sqlite3.Row) -> str | None:
    """The `branch` recorded against `row`'s own task. `Ledger.tasks_by_repo`
    carries no `branch` column, so it is read
    off the matching row of `tasks_by_spec_id` instead."""
    match = next(
        (
            r
            for r in ledger.tasks_by_spec_id(repo_id, row["spec_id"])
            if r["task_id"] == row["task_id"]
        ),
        None,
    )
    return match["branch"] if match is not None else None


def _origin_branch_heads(url: str) -> dict[str, str]:
    """Every branch `url` holds right now, name to sha, from one
    `ls-remote`. The fallback below filters its candidates by this, so
    a branch origin already dropped costs no fetch (`SA-0315`)."""
    done = _run(["git", "ls-remote", url, "refs/heads/*"])
    if done.returncode != 0:
        raise GitError(f"git ls-remote {url}: {done.stderr.strip()}")
    heads: dict[str, str] = {}
    for line in done.stdout.splitlines():
        sha, ref = line.split("\t", 1)
        heads[ref.removeprefix("refs/heads/")] = sha
    return heads


def _fallback_parent_branch(
    tree_base: str,
    *,
    repo: Path,
    repo_id: int,
    ledger: Ledger,
    mirror_path: Path,
) -> str | Refused:
    """`parent_branch` for a `tree_base` no task's `pushed_sha` matches
    (`DESIGN.md` §5.7, `SA-0315`). Walks every `pushed_sha`-carrying
    task, newest first, kept to those whose `branch`
    `_origin_branch_heads` still lists. Each is fetched into the mirror
    first, so an unfetched `tree_base` disqualifies instead of raising.
    The winner is the first whose fetched head reaches `tree_base`, and
    whose own `pushed_sha` is an ancestor of it. A listed branch gone by
    its own fetch raises, and so does a failed `ls-remote`: both
    infrastructure, never a refusal.
    """
    mirror = ensure_mirror(repo, mirror_path)
    url = package_phase.real_remote(repo)
    origin_heads = _origin_branch_heads(url)

    candidates = [
        row for row in reversed(ledger.tasks_by_repo(repo_id)) if row["pushed_sha"]
    ]
    for row in candidates:
        branch = _task_branch(ledger, repo_id, row)
        if branch is None or branch not in origin_heads:
            continue
        head = package_phase.fetch_parent_branch(mirror, url, branch)
        if not _is_ancestor(mirror, tree_base, head):
            continue
        if not _is_ancestor(mirror, row["pushed_sha"], tree_base):
            continue
        return branch

    return Refused(
        reason=(
            f"{tree_base[:12]} was pushed by no task in this repo, and no "
            "branch at origin carries it"
        )
    )


def ready_task(
    spec_id: str,
    *,
    repo: Path,
    repo_id: int | None,
    ledger: Ledger,
    out_dir: Path,
    mirror_path: Path,
) -> ReadyTask | Refused:
    """Rebuilds what `package()` needs for `spec_id`'s newest task in this
    repo, from the ledger and the task directory alone. No live
    `CellOutcome` is required, and nothing here writes, ledger or disk,
    save the one path that writes `mirror_path`: the `tree_base`
    fallback below, reached only when no task's `pushed_sha` matches it.

    Refuses by name, naming the spec id, the state, the pull request
    url, and the missing, stale or unmatched file or sha. A git failure
    in the fallback raises instead, since it is infrastructure.
    """
    if repo_id is None:
        return Refused(reason=f"{spec_id} has no task in this repo")
    newest = _newest_for_spec(ledger.tasks_by_repo(repo_id), spec_id)
    if newest is None:
        return Refused(reason=f"{spec_id} has no task in this repo")
    task_id = newest["task_id"]
    if newest["state"] != "READY_FOR_REVIEW":
        return Refused(
            reason=f"task {task_id} is {newest['state']}, not READY_FOR_REVIEW"
        )
    if newest["pr_url"]:
        return Refused(
            reason=f"task {task_id} already carries a pull request: {newest['pr_url']}"
        )

    task_dir = out_dir / spec_id
    baseline_path = task_dir / "baseline.json"
    if not baseline_path.is_file():
        return Refused(reason=f"{baseline_path} does not exist")
    baseline_mtime = baseline_path.stat().st_mtime

    for name in ("patch.diff", "patch.json", "findings.json"):
        path = task_dir / name
        if not path.is_file():
            return Refused(reason=f"{path} does not exist")
        if path.stat().st_mtime < baseline_mtime:
            return Refused(
                reason=f"{path} is older than {baseline_path}, so it is another cell's"
            )

    patch_meta = json.loads((task_dir / "patch.json").read_text())
    base_sha = patch_meta["base_sha"]
    tree_base = patch_meta.get("tree_base", base_sha)

    spec = _spec_for_task(ledger, repo, repo_id, spec_id, task_id)
    if isinstance(spec, Refused):
        return spec

    cutoff = _cell_cutoff(baseline_path)
    this_cells = [a for a in ledger.attempts(task_id) if a["started_at"] >= cutoff]

    spent_usd = sum(
        (a["cost_usd_est"] or 0.0)
        for a in this_cells
        if a["phase"] not in _NOT_THIS_CELLS_PHASE
    )
    attempts = sum(
        1
        for a in this_cells
        if a["phase"] in _SUITE_PHASES and ledger.attempt_results(a["attempt_id"])
    )
    effective_risk = spec.risk
    for attempt in reversed(this_cells):
        if attempt["earned_risk"]:
            effective_risk = attempt["earned_risk"]
            break

    reviews = [
        LensReview(
            lens=review["lens"],
            findings=[Finding.model_validate(f) for f in review["findings"]],
            cost_usd=review["cost_usd"],
            error=review["error"],
        )
        for review in json.loads((task_dir / "findings.json").read_text())
    ]

    def _fresh(name: str) -> bool:
        path = task_dir / name
        return path.is_file() and path.stat().st_mtime >= baseline_mtime

    rebut_result = _rebuild_rebut_result(task_dir) if _fresh("rebuttal.json") else None
    wrong_versions = (
        json.loads((task_dir / "wrong-versions.json").read_text())
        if _fresh("wrong-versions.json")
        else []
    )
    notes = (
        json.loads((task_dir / "notes.json").read_text())["raw"]
        if _fresh("notes.json")
        else ""
    )

    parent_branch: str | None = None
    if tree_base != base_sha:
        pushers = [
            row
            for row in ledger.tasks_by_repo(repo_id)
            if row["pushed_sha"] == tree_base
        ]
        if pushers:
            parent_branch = _task_branch(ledger, repo_id, pushers[-1])
        else:
            fallback = _fallback_parent_branch(
                tree_base,
                repo=repo,
                repo_id=repo_id,
                ledger=ledger,
                mirror_path=mirror_path,
            )
            if isinstance(fallback, Refused):
                return fallback
            parent_branch = fallback

    outcome = CellOutcome(
        state="READY_FOR_REVIEW",
        task_id=task_id,
        run_id=ledger.task_run(task_id),
        task_dir=task_dir,
        spent_usd=spent_usd,
        attempts=attempts,
        cell_head_sha=patch_meta.get("head_sha"),
        reviews=reviews,
        wrong_versions=wrong_versions,
        rebut_result=rebut_result,
        effective_risk=effective_risk,
        notes=notes,
    )
    return ReadyTask(outcome=outcome, spec=spec, parent_branch=parent_branch)


def package_ready_task(
    spec_id: str,
    *,
    repo: Path,
    repo_id: int | None,
    ledger: Ledger,
    out_dir: Path,
    mirror_path: Path,
    token: str | None,
) -> package_phase.PackageResult | Refused:
    """`saffron package`'s whole body: `ready_task`'s rebuild, then every
    step PACKAGE needs on its own, with no agent and no `run_one_cell`.

    Returns `ready_task`'s `Refused` untouched, before the image or the
    network exist. `ready_task`'s own `tree_base` fallback reads
    `mirror_path` earlier, whether it then refuses or not. On a `ReadyTask` it
    prepares the mirror and builds the repo's image. It then runs N1's
    host-binding probe in a network named for this spec id, and calls
    `package_phase.package` once.
    """
    ready = ready_task(
        spec_id,
        repo=repo,
        repo_id=repo_id,
        ledger=ledger,
        out_dir=out_dir,
        mirror_path=mirror_path,
    )
    if isinstance(ready, Refused):
        return ready

    mirror, _, _ = preflight.prepare_mirror(repo, mirror_path)
    image = repo_image.build_cell_image(repo)

    # A prefix no other network uses, so a killed invocation's leftover cannot
    # collide with re-verification's own `saffron-pkg-` names.
    network = f"saffron-hostprobe-{spec_id}"
    runtime.remove_network(network)
    try:
        subnet = runtime.allocate_network(network)
        gateway = runtime.gateway(subnet)
        ports, tolerated, sockets = preflight.host_probe_ports()
        addresses = preflight.probe_addresses(gateway=gateway)
        detail = (
            f"probing {len(ports)} host ports at "
            + ", ".join(addresses)
            + "; tolerating "
            + (", ".join(tolerated) or "nothing")
        )
        print(
            describe(
                Preflight(
                    timestamp=time.time(),
                    spec_id=spec_id,
                    step="ports",
                    detail=detail,
                )
            )
        )
        preflight.assert_host_is_unreachable(
            repo_image.BASE_TAG, network, gateway=gateway, ports=ports, sockets=sockets
        )
    finally:
        runtime.remove_network(network)

    return package_phase.package(
        ready.outcome,
        spec=ready.spec,
        repo=repo,
        mirror=mirror,
        image=image,
        ledger=ledger,
        out_dir=out_dir,
        token=token,
        parent_branch=ready.parent_branch,
    )
