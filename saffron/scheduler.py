"""The queue scan — which specs on disk are worth running tonight, and in
what order (DESIGN.md §4.2.1).

This is the second of `SA-0009`'s split: the `spec_sha`-keyed done/re-queue
filter and the ordering. `SA-0016` adds the other four of §4.2.1's six
refusals to `build_queue`; at this spec a refusal exists only for a path
`discover_specs` could not parse.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from saffron.intake import Spec, discover_specs
from saffron.ledger import Ledger

# A spec is queued unless a task at *this* spec_sha is in one of these states
# — done with it, in the sense that running it again learns nothing new
# (§4.2.1). Keyed on spec_sha, not spec_id: an edited spec (a new spec_sha)
# is unaffected by a stale task's disposition.
DONE_STATES = frozenset(
    {
        "READY_FOR_REVIEW",
        "APPROVED",
        "MERGE_TRAIN",
        "MERGED",
        "MERGE_FAILED",
        "REJECTED",
        "EXHAUSTED",
        "NOT_IMPLEMENTED",
        "PLAN_REJECTED",
        "SCOPE_REVIEW",
    }
)

# The other side of the same rule: re-queue when nothing was learned about
# the spec. A spec whose task is in one of these states is queued again,
# resuming that same task_id rather than minting a new one.
REQUEUE_STATES = frozenset(
    {
        "CHANGES_REQUESTED",
        "RATE_LIMITED",
        "GATE_ERROR",
        "PREFLIGHT_FAILED",
        "ORPHANED",
    }
)


@dataclass(frozen=True)
class Candidate:
    """One spec worth running tonight.

    `task_id` is `None` when there is no existing task to resume — either
    none was ever created at this `spec_sha`, or the one that exists is in an
    in-flight state (a corpse this spec does not stamp `ORPHANED`; that write
    belongs to the half of `SA-0009` that runs a cell). It is set only when a
    task at this `spec_sha` is in a `REQUEUE_STATES` state, so the resumed
    work reattaches to the row it was sent back to fix rather than a fresh
    one gate 0 (`SA-0016`) would refuse on its own PR.
    """

    path: Path
    spec: Spec
    spec_sha: str
    task_id: int | None


@dataclass(frozen=True)
class Refusal:
    """One path refused before any cell starts. At this spec, only a parse
    failure — the other five of §4.2.1's six refusals are `SA-0016`."""

    path: Path
    reason: str


def build_queue(
    directory: Path, repo_id: int | None, ledger: Ledger
) -> tuple[list[Candidate], list[Refusal]]:
    """Turn the specs `discover_specs` found in `directory` into an ordered
    queue and a list of refusals.

    `repo_id` is `resolve_repo`'s answer, and `None` is a real case — a repo
    with no ledger row has no history to filter against, so every parseable
    spec is a fresh candidate.

    Ordered by `spec.priority` (lower runs first), then by `discover_specs`'
    filename order to break ties — `sorted` is stable and `discover_specs`
    already returns its specs in that order, so no second key is needed.
    """
    specs, failures = discover_specs(directory)
    existing = ledger.tasks_by_spec(repo_id) if repo_id is not None else {}

    candidates: list[Candidate] = []
    for discovered in specs:
        row = existing.get((discovered.spec.id, discovered.spec_sha))
        if row is not None and row["state"] in DONE_STATES:
            continue
        task_id = (
            int(row["task_id"])
            if row is not None and row["state"] in REQUEUE_STATES
            else None
        )
        candidates.append(
            Candidate(
                path=discovered.path,
                spec=discovered.spec,
                spec_sha=discovered.spec_sha,
                task_id=task_id,
            )
        )
    candidates.sort(key=lambda c: c.spec.priority)

    refusals = [Refusal(path=f.path, reason=f.reason) for f in failures]
    return candidates, refusals
