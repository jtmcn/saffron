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
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import get_args

from saffron.agents import context
from saffron.cell.session import _SHA as _RESOLVED_SHA
from saffron.cell.session import CellOutcome, CellSpec, run_one_cell
from saffron.events import (
    Ceiling,
    Ceilings,
    CeilingSource,
    Event,
    EventLog,
    Preflight,
    describe,
)
from saffron.intake import Spec, SpecError, parse_spec
from saffron.ledger import Ledger
from saffron.phases import package as package_phase
from saffron.phases.rebut import sustained_blockers, unkept_fixes
from saffron.phases.review import anchored_concerns
from saffron.reconcile import GhRunner, reconcile
from saffron.report import index as index_report
from saffron.repos import image as repo_image
from saffron.repos.mirror import (
    GitError,
    UnreadablePath,
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
) -> tuple[str | None, str | None]:
    """The tree sha `CellSpec.stacked_on` should carry and the branch name
    `package()`'s stacking parameter should carry, or `(None, None)`
    together for an ordinary unstacked cell — never one without the other,
    since a worktree stacked on a sha whose pull request targets `main` is
    exactly the defect this spec exists to close (`SA-0026`).

    Only `depends_on[0]` is ever consulted — K=1. A spec naming a second,
    unmerged parent does not stack on it too: nothing here orders one
    batch's tasks against each other yet, so a grandchild (or a second
    unmerged parent) is out of reach by design, not by oversight.

    Given no `GhRunner`, the next rule holds. Among that one parent's task rows in this
    repo, across every `spec_sha` it has ever carried (`Ledger.tasks_by_spec_id` — this
    path never reads the parent's spec file, so it has no current sha to filter on, the
    same reach `scheduler.build_queue`'s `merged_anywhere` already takes), the newest
    row in a `scheduler.DEPENDENCY_WAITING_STATES` state is "the parent's task": the
    same waiting-outranks-dead precedence `scheduler._dependency_refusal` gives it. Not
    the *same* row, though — that function reads only the parent's current `spec_sha`,
    and a parent whose spec text moved after its pull request opened has a waiting row
    here and none there. The branch is real either way; it is the gate, not this
    resolver, that decides whether the dependent runs at all. A parent merged, retired,
    dead, unrun, or never in the ledger at all has no such row, and this function does
    not distinguish why — every one of those needs no stacking (its work, if any, is
    already on the default branch) or was never a candidate the gate should have
    admitted, which is not this resolver's check to make. Given a `GhRunner`, it
    reconciles that parent first. A merged or closed newest task unstacks the cell.
    Otherwise the newest row in `_STACKABLE_ON_RECONCILE` supplies the branch.

    **The ledger supplies the branch; the branch supplies the sha.** A row's
    `pushed_sha` is written by PACKAGE — or, since `SA-0069`, by a push of
    unpackaged work when PACKAGE never ran — and every review fix an operator
    commits by hand moves the branch past it — so the recorded sha is a tree
    the parent's pull request may no longer show. Worse, nothing puts that
    commit where the cell can read it: `ensure_mirror` fetches `+refs/*:refs/*`
    from the operator's *local checkout* with `--prune`, so a parent branch the
    operator does not happen to have locally is deleted from the mirror, and
    the cell's own seed (`worktree.py`) fetches the mirror's default refspec.
    Fetching the branch here fixes both — it is `fetch_default_branch`'s own
    argument (`package.py`), one branch over.

    `ParentGone` is an unstacked cell, not a failure: a parent branch that is
    deleted has either merged, in which case its work is on the default branch
    already, or been abandoned, in which case cutting from the default branch
    is the safe answer. Neither is worth killing a run over.

    A `pushed_sha` that is absent, empty, or not a resolved sha still yields
    `(None, None)` rather than reaching `CellSpec`: `__post_init__`
    (`SA-0022`) raises `ValueError` on anything else, and an operator's
    `saffron cell` must not die on a row this path cannot fully
    trust. A row with no `branch` recorded is treated the same way, since
    the two values this returns travel together.
    """
    if repo_id is None or not depends_on:
        return None, None
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
    branch = newest["branch"]
    # Refused here rather than left to the fetch: a row that evidences no push
    # has no branch worth fetching, and "branch None is gone" would send an
    # operator to look for a deleted ref instead of at the row.
    if not branch or not _RESOLVED_SHA.fullmatch(newest["pushed_sha"] or ""):
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
    and package the result if the cell came back reviewable.

    A given `handoff` replaces `_resolve_stacked_on` (`Handoff`, `SA-0143`).
    Given a `task_id`, `_recorded_spec_text` runs first and rebinds `spec`,
    `spec_sha` and `ceilings` to the task's recorded text (ADR 7). `state`
    on the outcome is PACKAGE's own, not the pre-packaging
    `READY_FOR_REVIEW`. Returns `Refused` before any cell exists when
    `spec.consumes` fails to resolve or gate 0 refuses a recorded text. A
    base the mirror lacks raises `GitError`."""
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
        log = EventLog(out_dir / spec.id)
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

    # Resolved from `depends_on[0]`'s newest waiting task, or `(None, None)`
    # together for an ordinary unstacked cell (`_resolve_stacked_on`,
    # `SA-0026`) — the one place a `CellSpec` is built, so this is the only
    # place either has to be read.
    if handoff is not None:
        stacked_on, target_branch = handoff.stacked_on, handoff.target_branch
    else:
        stacked_on, target_branch = _resolve_stacked_on(
            ledger,
            repo_id,
            spec.depends_on,
            mirror=base.mirror,
            url=base.url,
            spec_id=spec.id,
            emit=emit,
            gh=gh,
        )
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

    outcome = run_one_cell(
        cell_spec,
        repo=repo,
        mirror=base.mirror,
        ledger=ledger,
        out_dir=out_dir,
        emit=emit,
    )
    if outcome.state == "READY_FOR_REVIEW":
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
            emit=emit,
        )
        print(f"{spec.id:<10} {result.state}  {result.pr_url or result.note}")
        outcome.state = result.state
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
            header={"trailing accept rate": index_report.trailing_accept_rate(ledger)},
        )
        print(f"{spec.id:<10} {outcome.state}  {pushed.note}")
    return outcome
