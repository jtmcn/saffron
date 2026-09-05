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
from datetime import UTC, datetime
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


def run_batch(
    candidates: Sequence[Candidate],
    ledger: Ledger,
    budget_usd: float,
    until: datetime | None,
    runner: Callable[[Candidate], CellOutcome],
    *,
    clock: Callable[[], datetime] = datetime.now,
    readiness_check: Callable[[], Readiness],
    emit: Callable[[str], None] = print,
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
    every test here supplies a fake instead. `readiness_check` takes no default
    either, and for a related reason: `check_readiness` needs repo paths and a
    token this signature never receives, so no *real* default is constructible
    here. The permissive stub that stood in its place meant a caller who
    forgot the argument got a vacuous gate and a night that starts on an
    expired token — which is precisely what §4.4 step 1 exists to prevent. A
    night with no readiness gate is now something a caller has to say out
    loud. `clock` keeps its real default, because `datetime.now` is one.

    Returns the stop reason itself, one of `DRAINED`, `BUDGET`, `UNTIL`,
    `INFRASTRUCTURE` — never a boolean or an exit code. `SA-0051` owns the
    mapping to an exit code.
    """
    # UTC, and space-separated: `batches.started_at` is `datetime('now')`,
    # which is both. A naive local `isoformat()` matched neither, so the two
    # columns of one row were not comparable.
    until_ts = (
        until.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")
        if until is not None
        else None
    )
    batch_id = ledger.create_batch(budget_usd, until_ts=until_ts)

    stopped: StopReason | None = None
    try:
        stopped = _drive(
            candidates,
            ledger,
            budget_usd,
            until,
            runner,
            batch_id=batch_id,
            clock=clock,
            readiness_check=readiness_check,
            emit=emit,
        )
        return stopped
    finally:
        if stopped is None:
            # Nothing below returned a reason, so nothing below closed the
            # row: a readiness probe that raised (it does real network and
            # disk work), a `BaseException` the per-candidate handler does
            # not catch, or an operator's Ctrl-C at 3am. An open row is the
            # one state indistinguishable from a night still running, and it
            # is what §6's morning queue reads.
            ledger.close_batch(batch_id, "INFRASTRUCTURE")


def _drive(
    candidates: Sequence[Candidate],
    ledger: Ledger,
    budget_usd: float,
    until: datetime | None,
    runner: Callable[[Candidate], CellOutcome],
    *,
    batch_id: int,
    clock: Callable[[], datetime],
    readiness_check: Callable[[], Readiness],
    emit: Callable[[str], None],
) -> StopReason:
    """`run_batch`'s body, split out so every exit closes the batch row.

    Every `return` here is paired with a `close_batch`; anything that leaves
    without returning is the caller's `finally` to deal with."""
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

        high_water = ledger.max_run_id()
        try:
            outcome = runner(candidate)
        except Exception as exc:
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
            # Bound and reported: by the time `run_batch` returns the
            # exception is gone, and an unattended night that died from a
            # runtime that would not start otherwise leaves the operator a
            # stop reason and no traceback anywhere.
            emit(f"{candidate.spec.id:<10} raised {type(exc).__name__}: {exc}")
            ledger.attach_orphan_runs_to_batch(batch_id, high_water)
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

    if consecutive_aborts >= _BREAKER_THRESHOLD:
        # The breaker is consulted before a task, so a queue whose last
        # candidates all aborted falls out of the loop with the count
        # standing. Reporting `DRAINED` there would exit 0, and launchd would
        # record a successful night in which every task died of one global
        # condition.
        ledger.close_batch(batch_id, "INFRASTRUCTURE")
        return "INFRASTRUCTURE"

    ledger.close_batch(batch_id, "DRAINED")
    return "DRAINED"
