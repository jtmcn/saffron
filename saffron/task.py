"""Driving one task: a resolved spec and a pinned base in, a `CellOutcome` out.

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

What stays outside, deliberately:

- **The refusals and the mirror fetch.** They run at different times on the
  two paths for good reasons — a batch refuses at scan time so a night never
  pays for the cell, and pays for the mirror once per run (§4.2.1); an
  attended run has no scan and pays per task. Folding either in would force
  one of those to move.
- **`CELL_EXIT`.** An exit code is the process contract `saffron cell` owes a
  script, not a fact about a task; `run_batch` would have to ignore it.
- **The `CLAUDE_CODE_OAUTH_TOKEN` read.** Scoped to the invocation
  (`CLAUDE.md`), so it is read at the edge and passed. A module that reaches
  into `os.environ` is one a test has to reach into too.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from saffron.cell.session import _SHA as _RESOLVED_SHA
from saffron.cell.session import CellOutcome, CellSpec, run_one_cell
from saffron.events import Ceilings, CeilingSource, Event, EventLog, Preflight, describe
from saffron.intake import Spec
from saffron.ledger import Ledger
from saffron.phases import package as package_phase
from saffron.repos import image as repo_image
from saffron.scheduler import DEPENDENCY_WAITING_STATES


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


def spec_ceilings(spec: Spec) -> tuple[dict, dict[str, CeilingSource]]:
    """The three ceilings a spec declares, and where each came from.

    The half of `cli._ceilings` that has nothing to do with flags, so the
    unattended path can say what bound a task without growing an `argparse`
    dependency it has no use for. "spec" only where the author actually wrote
    the field: `model_fields_set` is what separates a declared value from a
    model default that happens to equal it.
    """
    values = {
        "budget_usd": spec.budget_usd,
        "max_attempts": spec.max_attempts,
        "max_turns": spec.max_turns,
    }
    sources: dict[str, CeilingSource] = {
        name: ("spec" if name in spec.model_fields_set else "default")
        for name in values
    }
    return values, sources


def _resolve_stacked_on(
    ledger: Ledger,
    repo_id: int | None,
    depends_on: list[str],
    *,
    mirror: Path,
    url: str,
    spec_id: str,
    emit: Callable[[Event], None] = lambda event: print(describe(event)),
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

    Among that one parent's task rows in this repo, across every `spec_sha`
    it has ever carried (`Ledger.tasks_by_spec_id` — this path never reads
    the parent's spec file, so it has no current sha to filter on, the
    same reach `scheduler.build_queue`'s `merged_anywhere` already takes),
    the newest row in a `scheduler.DEPENDENCY_WAITING_STATES` state is "the
    parent's task": the same waiting-outranks-dead precedence
    `scheduler._dependency_refusal` gives it. Not the *same* row, though —
    that function reads only the parent's current `spec_sha`, and a parent
    whose spec text moved after its pull request opened has a waiting row
    here and none there. The branch is real either way; it is the gate, not
    this resolver, that decides whether the dependent runs at all.
    A parent merged, retired, dead, unrun, or never in the
    ledger at all has no such row, and this function does not distinguish
    why — every one of those needs no stacking (its work, if any, is already
    on the default branch) or was never a candidate the gate should have
    admitted, which is not this resolver's check to make.

    **The ledger supplies the branch; the branch supplies the sha.** A row's
    `pushed_sha` is written once, by PACKAGE, and every review fix an operator
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
    rows = ledger.tasks_by_spec_id(repo_id, parent_id)
    waiting = [row for row in rows if row["state"] in DEPENDENCY_WAITING_STATES]
    if not waiting:
        return None, None
    newest = waiting[-1]
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


def run_task(
    spec: Spec,
    spec_sha: str,
    *,
    ceilings: dict,
    ceiling_sources: dict[str, CeilingSource],
    base: PinnedBase,
    repo_id: int | None,
    repo: Path,
    ledger: Ledger,
    out_dir: Path,
    token: str | None,
    emit: Callable[[Event], None] | None = None,
) -> CellOutcome:
    """One task, start to finish: stack it if it has a parent, run its cell,
    and package the result if the cell came back reviewable.

    `ceilings` arrives resolved — `{budget_usd, max_attempts, max_turns}` —
    because only the attended path has flags to arbitrate against the spec
    (`cli._ceilings`); a batch has none, so there is nothing to arbitrate and
    no reason for `argparse` to reach this far. `ceiling_sources` travels with
    it so the record can say *where* each value came from, which is the whole
    of what makes the line worth printing: a number with no provenance sends
    an operator to grep a spec file for a line that may not be in it.

    Emitted here rather than by either caller, because being printed on one
    path and not the other is the defect this module exists to end.

    `state` on the returned outcome is the *packaging* result's where
    packaging ran, so a caller reads what actually happened to the task —
    `MERGE_FAILED` included — rather than the pre-packaging
    `READY_FOR_REVIEW` every packaged task would otherwise report.
    """
    task_dir = out_dir / spec.id
    if emit is None:
        # Print plus the task's own log, the shape `session._default_emit` and
        # `package()` both default to: a caller that passes nothing must still
        # get `events.jsonl`. A print-only default is the defect item 43 is
        # about, and is not this.
        log = EventLog(task_dir)

        def emit(event: Event) -> None:
            line = describe(event)
            if line:
                print(line)
            log.append(event)

    emit(
        Ceilings(
            timestamp=time.time(),
            spec_id=spec.id,
            budget_usd=ceilings["budget_usd"],
            max_attempts=ceilings["max_attempts"],
            max_turns=ceilings["max_turns"],
            budget_source=ceiling_sources["budget_usd"],
            attempts_source=ceiling_sources["max_attempts"],
            turns_source=ceiling_sources["max_turns"],
        )
    )

    # Resolved from `depends_on[0]`'s newest waiting task, or `(None, None)`
    # together for an ordinary unstacked cell (`_resolve_stacked_on`,
    # `SA-0026`) — the one place a `CellSpec` is built, so this is the only
    # place either has to be read.
    stacked_on, target_branch = _resolve_stacked_on(
        ledger,
        repo_id,
        spec.depends_on,
        mirror=base.mirror,
        url=base.url,
        spec_id=spec.id,
        emit=emit,
    )
    # Printed for the same reason the ceilings are: which tree a run was cut
    # from is not recoverable from the exit code, and a stacked run that
    # surprises an operator is one they cannot diagnose.
    if stacked_on is not None:
        print(f"stacked on {target_branch} @ {stacked_on[:12]}")

    cell_spec = CellSpec(
        spec_id=spec.id,
        spec_sha=spec_sha,
        branch=f"saffron/{spec.id}",
        base_sha=base.base_sha,
        touches=spec.touches,
        spec_type=spec.type,
        body=spec.body,
        forbidden=spec.forbidden,
        acceptance=spec.acceptance,
        risk=spec.risk,
        stacked_on=stacked_on,
        **ceilings,
    )
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
        print(f"{spec.id:<10} {outcome.state}")
    return outcome
