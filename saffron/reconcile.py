"""Reconciling `tasks.state` against decisions made outside the ledger
(`DESIGN.md` §4.2.1, §6.1). PACKAGE's last word is `READY_FOR_REVIEW`, or
`MERGE_FAILED` where the push or the pull request could not be made; the ledger
learns what happened to the first of those only by asking GitHub.

`GhRunner` is duplicated a third time here, matching `scheduler.py` and
`phases/package.py` (both forbidden to import from here).

**The reader/writer asymmetry is the whole defect risk.** `scheduler._open_prs`
treats a failed `gh` as "nothing found", safe for a *refuser*. Here that
would be catastrophic — an untrustworthy answer read as "not merged" would
stamp `REJECTED` on a healthy branch — so every failure path below returns
`None`, and the caller counts it rather than acting on it.

**A live task is skipped by its state, and that is not the whole of it.** The
in-flight guard covers a first run: `pr_url` is NULL until PACKAGE's last write,
so there is nothing here to ask about. A *resumed* task is the gap. `_drive_cell`
writes `READY_FOR_REVIEW` and calls `finish_run` before `cli._run_cell` invokes
PACKAGE, so for as long as PACKAGE runs the row reads `READY_FOR_REVIEW` while
still carrying the **previous** attempt's `pr_url` — whose `reviewDecision` is
the `CHANGES_REQUESTED` that requeued it. Reconciling in that window writes a
`REQUEUE_STATES` value onto a task whose cell is alive. Harmless in v0.5, where
no scan starts a cell and PACKAGE overwrites the row immediately after; it stops
being harmless the moment `SA-0020` gives a scan teeth. `docs/BACKLOG.md` carries
it; do not close that item by widening this module's state guard alone.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field

from saffron.ledger import Ledger

GhRunner = Callable[[list[str]], subprocess.CompletedProcess[str]]


def run_gh(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, capture_output=True, text=True, check=False)


# Worth asking about only while undecided. `MERGED`/`REJECTED` are excluded
# so "never moves backwards" holds even once a merged branch is deleted and
# `gh pr view` starts erroring on it.
PR_PENDING_STATES = frozenset({"READY_FOR_REVIEW", "APPROVED", "CHANGES_REQUESTED"})

# §4.2.1: a corpse only at a batch scan's own premise (one batch runs at a
# time). Neither `queue` nor `reconcile` is a batch scan, so this is
# consulted only when a caller asserts that premise (`stamp_orphaned=True`).
# `ORPHANED` is in `scheduler.REQUEUE_STATES`, so stamping a live row hands
# it back out as resumable: a second cell on the same branch.
IN_FLIGHT_STATES = frozenset(
    {
        "DRAFT",
        "QUEUED",
        "DIAGNOSING",
        "IMPLEMENTING",
        "GATING",
        "REPAIRING",
        "REVIEWING",
        "REBUTTING",
    }
)

# What one `_next_state` outcome writes into, keyed off the state it produces.
_BUCKET = {
    "MERGED": "merged",
    "REJECTED": "rejected",
    "CHANGES_REQUESTED": "changes_requested",
}


@dataclass
class ReconcileResult:
    """What one call changed. Task ids, not bare counts, so an operator can
    trace exactly which row moved and why."""

    merged: list[int] = field(default_factory=list)
    rejected: list[int] = field(default_factory=list)
    changes_requested: list[int] = field(default_factory=list)
    orphaned: list[int] = field(default_factory=list)
    # Pull requests `gh` gave no trustworthy answer about — missing,
    # unauthenticated, erroring, or an unparseable/wrong shape. Absence of an
    # answer is never recorded as "not merged"; the row is left exactly as it
    # was and its id recorded here.
    unasked: list[int] = field(default_factory=list)


def _pr_status(url: str, gh: GhRunner) -> dict | None:
    """One pull request's `state` and `reviewDecision`, or `None` on
    anything that keeps the answer from being trustworthy."""
    done = gh(["gh", "pr", "view", url, "--json", "state,reviewDecision"])
    if done.returncode != 0:
        return None
    try:
        parsed = json.loads(done.stdout)
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _next_state(pr: dict) -> str | None:
    """What a task should become given `pr`, or `None` to leave it exactly
    as it was. Four outcomes, and only four: merged, closed-unmerged,
    open-with-changes-requested, open-undecided — any other `reviewDecision`
    or unrecognised `state` is treated as the last, a fifth mapping nothing
    here exercises."""
    state = pr.get("state")
    if state == "MERGED":
        return "MERGED"
    if state == "CLOSED":
        return "REJECTED"
    if state == "OPEN" and pr.get("reviewDecision") == "CHANGES_REQUESTED":
        return "CHANGES_REQUESTED"
    return None


def reconcile(
    ledger: Ledger,
    repo_id: int,
    *,
    gh: GhRunner = run_gh,
    stamp_orphaned: bool = False,
) -> ReconcileResult:
    """Bring one repo's `tasks.state` into line with what GitHub decided,
    and — only when `stamp_orphaned=True` asserts §4.2.1's batch-scan
    premise — stamp any corpse a dead scan left behind. Defaults to `False`:
    no command in this version of Saffron is a batch scan."""
    result = ReconcileResult()
    rows = ledger.tasks_by_repo(repo_id)

    for row in rows:
        state, pr_url = row["state"], row["pr_url"]
        if not pr_url or state not in PR_PENDING_STATES:
            continue
        pr = _pr_status(pr_url, gh)
        if pr is None:
            result.unasked.append(row["task_id"])
            continue
        new_state = _next_state(pr)
        if new_state is None or new_state == state:
            continue
        # Bucket first: a state outside `_BUCKET` must not raise *after* the
        # row is written, which would abort the loop half-reconciled.
        bucket = _BUCKET.get(new_state)
        if bucket is None:
            continue
        ledger.set_task_state(row["task_id"], new_state)
        getattr(result, bucket).append(row["task_id"])

    if stamp_orphaned:
        for row in rows:
            if row["state"] in IN_FLIGHT_STATES:
                ledger.set_task_state(row["task_id"], "ORPHANED")
                result.orphaned.append(row["task_id"])

    return result
