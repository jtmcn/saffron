"""The batch loop — a night, driven (DESIGN.md §4.2.1).

`saffron queue` resolves candidates and prints them; nothing consumed the
list. This module is the consumer: `run_batch` is a K=1 `for` loop over the
sorted candidates `build_queue` already produced, calling an injected runner
once per candidate and stopping four ways — the queue drains, the budget is
gone, `--until` hits, or the breaker fires.

Deliberately not here: resolving the scan (`cli._queue` already does it and
`cli.py` is forbidden to this module), building a `CellSpec` (needs two
`cli`-private helpers — the ceilings resolver and the one that decides what a
child stacks on — that only `cli._run_cell` has), concurrency (K=1, §4.2.1),
multi-repo (v2, §9), and stamping a corpse `ORPHANED` (that is the batch
*scan*'s job, not this loop's).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Literal

from saffron.cell.session import CellOutcome
from saffron.ledger import Ledger
from saffron.preflight import Readiness
from saffron.scheduler import Candidate

StopReason = Literal["DRAINED", "BUDGET", "UNTIL", "INFRASTRUCTURE"]

# The breaker's own set — deliberately not `scheduler.REQUEUE_STATES`, which
# answers a different question (what re-queues tomorrow) and contains
# `CHANGES_REQUESTED` and `ORPHANED`, both states a task *earned*. Only these
# three mean the run itself is broken rather than the task's outcome.
ABORT_STATES = frozenset({"GATE_ERROR", "PREFLIGHT_FAILED", "RATE_LIMITED"})

# Two consecutive aborts is what fires the breaker (§4.2.1) — enough to tell
# "the toolchain is broken" from "three flaky tasks", never fewer.
_BREAKER_THRESHOLD = 2


def _max_run_id(ledger: Ledger) -> int:
    """The high-water mark on `runs.run_id`, read just before a candidate's
    call so a raise from it can be told apart from every run that already
    existed."""
    row = ledger._db.execute(
        "SELECT COALESCE(MAX(run_id), 0) AS m FROM runs"
    ).fetchone()
    return int(row["m"])


def _attach_runs_minted_since(ledger: Ledger, batch_id: int, high_water: int) -> None:
    """Sweep in any run a raising `runner` minted before it died.

    `run_one_cell` creates `run_id`/`task_id` (session.py, around the mirror
    read) *before* opening the try block whose only handler re-raises the
    original exception untouched — so a crash after one or more attempts have
    already billed real `cost_usd_est` (a runtime dying mid-REPAIR, say)
    still reaches `run_batch` as a bare exception with no `run_id` on it.
    `attach_run_to_batch` can only be called with a `run_id`, and the normal
    per-candidate call (below) has none to give it on this path.

    Scoped to `run_id > high_water` — recorded immediately before the call —
    rather than every row with `batch_id IS NULL`: a ledger accumulates
    plenty of those from `saffron cell` and `replay.py`, both of which pass
    no batch on purpose, and sweeping all of them would silently fold a past
    unrelated run's spend into tonight's batch. Under K=1 nothing else can
    mint a run while one candidate's call is in flight, so `run_id >
    high_water` is exactly the set — zero or one row — that this call
    produced, never a stale orphan from outside it.
    """
    rows = ledger._db.execute(
        "SELECT run_id FROM runs WHERE run_id > ? AND batch_id IS NULL",
        (high_water,),
    ).fetchall()
    for row in rows:
        ledger.attach_run_to_batch(row["run_id"], batch_id)


def _always_ready() -> Readiness:
    """The real default for `readiness_check`: no additional gate requested.

    Unlike the runner (below), a real readiness probe *is* reachable from
    here — `preflight.check_readiness` needs nothing this module is forbidden
    to touch — but it needs repo-specific paths and a token this loop has no
    reason to carry, so the default that costs nothing is "proceed". A real
    caller (`SA-0051`) passes its own callable, typically
    `preflight.check_readiness` bound to the run's own paths.
    """
    return Readiness(ok=True)


def run_batch(
    candidates: Sequence[Candidate],
    ledger: Ledger,
    budget_usd: float,
    until: datetime | None,
    runner: Callable[[Candidate], CellOutcome],
    *,
    clock: Callable[[], datetime] = datetime.now,
    readiness_check: Callable[[], Readiness] = _always_ready,
) -> StopReason:
    """Drive one night against one repo's already-sorted candidates.

    `candidates` is `build_queue`'s own return value — this module never
    re-derives the scan (`cli.py` is forbidden here, and re-deriving it would
    mean copying four `cli`-private helpers). `ledger` is an ordinary
    argument, never a keyword default: every witness that involves money
    reads the batch's spend back through it rather than trusting a tally kept
    here, which is exactly what a caller cut mid-loop would lose.

    `runner` takes no default. Building a real `CellSpec` from a `Candidate`
    needs the ceilings resolver and the stacked-on resolver, both
    `cli`-private and both forbidden to this spec — a loop that built one
    itself would pass no stacked-on parent for any candidate, cutting every
    child of a stack from `base_sha` and failing its own gates the moment it
    ran (§4.2.1). `SA-0051` owns `cli.py` and supplies the real adapter;
    every test here supplies a fake instead. `clock` and `readiness_check` do
    take real, usable defaults — `datetime.now` and "proceed" respectively —
    because neither needs anything forbidden to be real.

    Returns the stop reason itself, one of `DRAINED`, `BUDGET`, `UNTIL`,
    `INFRASTRUCTURE` — never a boolean or an exit code. `SA-0051` owns the
    mapping to an exit code.
    """
    until_ts = until.isoformat() if until is not None else None
    batch_id = ledger.create_batch(budget_usd, until_ts=until_ts)

    readiness = readiness_check()
    if not readiness.ok:
        # §4.4 step 1: a readiness failure ends the night before any task
        # starts, but it still has to leave a row behind, or an expired token
        # at 22:00 produces a night with no record it was attempted.
        ledger.close_batch(batch_id, "INFRASTRUCTURE")
        return "INFRASTRUCTURE"

    consecutive_aborts = 0

    for candidate in candidates:
        # Before each task, in this order: the deadline, then the budget,
        # then the breaker's standing count (§4.2.1's ordering, named once
        # here rather than re-derived at each check).
        if until is not None and clock() >= until:
            ledger.close_batch(batch_id, "UNTIL")
            return "UNTIL"

        remaining = budget_usd - ledger.batch_spend(batch_id)
        if candidate.spec.budget_usd > remaining:
            ledger.close_batch(batch_id, "BUDGET")
            return "BUDGET"

        if consecutive_aborts >= _BREAKER_THRESHOLD:
            ledger.close_batch(batch_id, "INFRASTRUCTURE")
            return "INFRASTRUCTURE"

        high_water = _max_run_id(ledger)
        try:
            outcome = runner(candidate)
        except Exception:
            # Driving one cell can raise from outside the block that would
            # catch it — an unreadable policy at base, a runtime that will
            # not start, a mirror that will not fetch, or a crash well into
            # REPAIR after real attempts already billed real money. Unhandled,
            # the night ends with no `ended_at` and no status, indistinguishable
            # from one still running. Caught here, the raise counts as an
            # abort for the breaker, the same as a returned `GATE_ERROR` — and
            # whatever run this candidate's call minted before it died is
            # swept into the batch by run_id, not by an outcome this path
            # never gets, so its spend still counts against the budget gate
            # rather than vanishing behind a NULL `batch_id` forever.
            consecutive_aborts += 1
            _attach_runs_minted_since(ledger, batch_id, high_water)
            continue

        # `create_run` mints the row with no `batch_id` (`run_one_cell`,
        # forbidden here, passes none) — this stamps it on after the fact,
        # the shape `record_push` and `set_task_package` already use on
        # `tasks`: the row exists, then the fact about it arrives.
        ledger.attach_run_to_batch(outcome.run_id, batch_id)

        if outcome.state in ABORT_STATES:
            consecutive_aborts += 1
        else:
            # Any state a task earned resets the counter, `EXHAUSTED`
            # included — "any terminal state" would also reset on
            # `GATE_ERROR` and `PREFLIGHT_FAILED` themselves, and the counter
            # would never reach two.
            consecutive_aborts = 0

    ledger.close_batch(batch_id, "DRAINED")
    return "DRAINED"
