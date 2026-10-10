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

**A live task is skipped by its state**, and that is not the whole of it. A
first run carries no `pr_url`, since `set_task_package` writes one only once
PACKAGE ends. A cell bound for PACKAGE leaves its row in flight, `REVIEWING`
or `REBUTTING`, until PACKAGE ends (backlog item b-dce9a4). The gap left is a
stamping scan that marks a live cell's row `ORPHANED`. A wider state guard
here does not close it.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import NamedTuple

from saffron.ledger import Ledger

GhRunner = Callable[[list[str]], subprocess.CompletedProcess[str]]


def run_gh(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, capture_output=True, text=True, check=False)


# Undecided states. An `EXHAUSTED` row is asked too, below, and moves only on a merge.
# `MERGED`/`REJECTED` stay out, so a row never moves backwards once gh errors on it.
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
    "APPROVED": "approved",
    "MERGED": "merged",
    "REJECTED": "rejected",
    "CHANGES_REQUESTED": "changes_requested",
}


class HeadMoved(NamedTuple):
    """A pull request whose head is not the commit PACKAGE pushed — review
    fixes or a restack, judged by no gate, critic or record (backlog
    item 97)."""

    task_id: int
    packaged: str
    head: str


@dataclass
class ReconcileResult:
    """What one call changed. Task ids, not bare counts, so an operator can
    trace exactly which row moved and why."""

    merged: list[int] = field(default_factory=list)
    rejected: list[int] = field(default_factory=list)
    changes_requested: list[int] = field(default_factory=list)
    approved: list[int] = field(default_factory=list)
    orphaned: list[int] = field(default_factory=list)
    # Pull requests `gh` gave no trustworthy answer about — missing,
    # unauthenticated, erroring, or an unparseable/wrong shape. Absence of an
    # answer is never recorded as "not merged"; the row is left exactly as it
    # was and its id recorded here.
    unasked: list[int] = field(default_factory=list)
    # The merge path writes a head onto the ledger at the merge below;
    # `head_moved` is reported only — the extra commits are not ours to judge.
    head_moved: list[HeadMoved] = field(default_factory=list)


def _pr_status(url: str, gh: GhRunner) -> dict | None:
    """One pull request's `state`, `reviewDecision`, `isDraft` and `headRefOid`, or
    `None` on anything that keeps the answer from being trustworthy."""
    done = gh(
        ["gh", "pr", "view", url, "--json", "state,reviewDecision,isDraft,headRefOid"]
    )
    if done.returncode != 0:
        return None
    try:
        parsed = json.loads(done.stdout)
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _next_state(pr: dict) -> str | None:
    """What a task should become given `pr`, or `None` to leave it exactly
    as it was. Five outcomes, and only five: merged, closed-unmerged,
    open-with-changes-requested, open and marked ready, open-undecided. Any
    other `reviewDecision` or unrecognised `state` is treated as the last.

    Marked ready is `APPROVED`: PACKAGE opens a draft, and GitHub refuses an
    author's own approval, so the operator's `gh pr ready` is the signal (item 52)."""
    state = pr.get("state")
    if state == "MERGED":
        return "MERGED"
    if state == "CLOSED":
        return "REJECTED"
    if state == "OPEN" and pr.get("reviewDecision") == "CHANGES_REQUESTED":
        return "CHANGES_REQUESTED"
    # `is False`, not falsy: an answer without the field says nothing about a draft.
    if state == "OPEN" and pr.get("isDraft") is False:
        return "APPROVED"
    return None


def reconcile(
    ledger: Ledger,
    repo_id: int,
    *,
    gh: GhRunner = run_gh,
    stamp_orphaned: bool = False,
    spec_id: str | None = None,
) -> ReconcileResult:
    """Bring one repo's `tasks.state` into line with what GitHub decided,
    and — only when `stamp_orphaned=True` asserts §4.2.1's batch-scan
    premise — stamp any corpse a dead scan left behind. Defaults to `False`,
    which is what `saffron queue` and `saffron reconcile` want; `saffron
    batch` is the one caller that passes `True`.

    `spec_id` narrows the rows read to one spec, matched exactly rather
    than by prefix. `None`, the default, reads every task in the repo, the
    shape every caller before `task._resolve_stacked_on` still wants."""
    result = ReconcileResult()
    rows = ledger.tasks_by_repo(repo_id)
    if spec_id is not None:
        rows = [row for row in rows if row["spec_id"] == spec_id]

    for row in rows:
        state, pr_url = row["state"], row["pr_url"]
        # `EXHAUSTED` is askable too, below, through its own narrower rule.
        if not pr_url or (state not in PR_PENDING_STATES and state != "EXHAUSTED"):
            continue
        merged_head = row["merged_head_sha"]
        if merged_head:
            # GitHub already said this merged. b-3e0dbe reports, unmeasured
            # here, that gh fails once the branch is deleted.
            ledger.set_task_state(row["task_id"], "MERGED")
            result.merged.append(row["task_id"])
            continue
        pr = _pr_status(pr_url, gh)
        if pr is None:
            result.unasked.append(row["task_id"])
            continue
        # Before the state check, so a merge still reports a moved head.
        # A non-merged `EXHAUSTED` row is asked every scan, so it can report each time.
        head, pushed = pr.get("headRefOid"), row["pushed_sha"]
        if isinstance(head, str) and head and pushed and head != pushed:
            result.head_moved.append(HeadMoved(row["task_id"], pushed, head))
        candidate = _next_state(pr)
        # A merge is the only answer that moves an `EXHAUSTED` row (b-8e30bd).
        new_state = candidate if state != "EXHAUSTED" or candidate == "MERGED" else None
        if new_state is None or new_state == state:
            continue
        # Bucket first: a state outside `_BUCKET` must not raise *after* the
        # row is written, which would abort the loop half-reconciled.
        bucket = _BUCKET.get(new_state)
        if bucket is None:
            continue
        if new_state == "MERGED" and isinstance(head, str) and head:
            ledger.record_merged_head(row["task_id"], head)
        ledger.set_task_state(row["task_id"], new_state)
        getattr(result, bucket).append(row["task_id"])

    if stamp_orphaned:
        for row in rows:
            if row["state"] in IN_FLIGHT_STATES:
                ledger.set_task_state(row["task_id"], "ORPHANED")
                result.orphaned.append(row["task_id"])

    return result
