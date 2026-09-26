"""The batch loop — a night, driven (DESIGN.md §4.2.1).

`saffron queue` resolves candidates and prints them; nothing consumed the
list. This module is the consumer: `run_batch` is a K=1 loop, driven by an
injected runner, that stops five ways — the queue drains, the budget is gone,
`--until` hits, the breaker fires, or a task comes back mid-phase having
reached no end state at all (`INCOMPLETE`, backlog item 70). It runs the
opening scan's candidates first, then — after every task, not only once the
list runs out — rescans through an injected `rescan` callable and starts the
first spec it offers that has not already started tonight, so a child whose
parent packages mid-night runs the same night rather than waiting for
tomorrow's scan (backlog item b-d6bff7).

Deliberately not here: resolving the scan (`cli._resolve_queue` already does
it and `cli.py` is forbidden to this module — `rescan` is taken the same way
`runner` and `readiness_check` already are, an injected callable rather than
an import), driving a task (`task.run_task` owns that, and both commands go
through it — this loop takes it as `runner` rather than importing it, so
what a night runs stays the caller's to say), concurrency (K=1, §4.2.1),
multi-repo (v2, §9), and stamping a corpse `ORPHANED` (that is the batch
*scan*'s job, not this loop's — every rescan this loop triggers passes
`stamp_orphaned=False`, since a task this same night left in flight is not a
corpse a dead scan left behind).

`Refused` is imported from `saffron.task` for its type alone. Importing a
type is not importing the driver that builds it.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Literal

from saffron.cell.session import CellOutcome
from saffron.ledger import Ledger
from saffron.preflight import Readiness
from saffron.reconcile import IN_FLIGHT_STATES
from saffron.scheduler import Candidate
from saffron.task import Refused

# The loop returns `INCOMPLETE` for a night that left a task in flight — a
# task that came back mid-phase, having reached no end state, which is not
# the same as the task failing (backlog item 70). `reconcile.IN_FLIGHT_STATES`
# is read, never copied: a second list is how the loop and the next batch
# scan would come to disagree about what a finished task is.
StopReason = Literal["DRAINED", "BUDGET", "UNTIL", "INFRASTRUCTURE", "INCOMPLETE"]

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
    runner: Callable[[Candidate], CellOutcome | Refused],
    *,
    rescan: Callable[[], Sequence[Candidate]],
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

    `runner` takes no default, and the reason changed without the decision
    changing. None was once *constructible* (§4.2.1: the stacked-on resolver
    was `cli`-private); `task.run_task` is now that driver and importable,
    so a real default *could* be written. It is still not, for
    `readiness_check`'s reason rather than its own: every test here supplies
    a fake runner, and a default would buy production
    nothing — `cli` always passes the real one — while making a forgotten
    argument silent instead of a `TypeError`. `readiness_check` takes no default
    either, and for a related reason: `check_readiness` needs repo paths and a
    token this signature never receives, so no *real* default is constructible
    here. The permissive stub that stood in its place meant a caller who
    forgot the argument got a vacuous gate and a night that starts on an
    expired token — which is precisely what §4.4 step 1 exists to prevent. A
    night with no readiness gate is now something a caller has to say out
    loud. `clock` keeps its real default, because `datetime.now` is one.

    `rescan` takes no default, for `readiness_check`'s reason. Called after
    every task, its return replaces what is left to run — `candidates` decide
    only the first — never merged; what has started is tracked by spec id.

    Returns the stop reason itself, one of `DRAINED`, `BUDGET`, `UNTIL`,
    `INFRASTRUCTURE`, `INCOMPLETE` — never a boolean or an exit code.
    `SA-0051` owns the mapping to an exit code.
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

    # Every task this run left mid-phase, in the order it happened —
    # `(spec_id, state)`. Owned here, not in `_drive`, so a night that raises
    # after leaving one in flight still names it on the way out (item 70).
    in_flight: list[tuple[str, str]] = []
    stopped: StopReason | None = None
    try:
        stopped = _drive(
            candidates,
            ledger,
            budget_usd,
            until,
            runner,
            rescan,
            batch_id=batch_id,
            clock=clock,
            readiness_check=readiness_check,
            emit=emit,
            in_flight=in_flight,
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
            _stop(ledger, batch_id, "INFRASTRUCTURE", in_flight, emit)


def _drive(
    candidates: Sequence[Candidate],
    ledger: Ledger,
    budget_usd: float,
    until: datetime | None,
    runner: Callable[[Candidate], CellOutcome | Refused],
    rescan: Callable[[], Sequence[Candidate]],
    *,
    batch_id: int,
    clock: Callable[[], datetime],
    readiness_check: Callable[[], Readiness],
    emit: Callable[[str], None],
    in_flight: list[tuple[str, str]],
) -> StopReason:
    """`run_batch`'s body, split out so every exit closes the batch row.

    Every `return` here is `_stop`, which is the one call to `close_batch`;
    anything that leaves without returning is the caller's `finally` to deal
    with — through `_stop` too, with the same `in_flight`."""
    readiness = readiness_check()
    if not readiness.ok:
        # §4.4 step 1: a readiness failure ends the night before any task
        # starts, but it still has to leave a row behind, or an expired token
        # at 22:00 produces a night with no record it was attempted.
        return _stop(ledger, batch_id, "INFRASTRUCTURE", in_flight, emit)

    consecutive_aborts = 0
    # By spec id, not whole `Candidate`: a re-offered spec returns as a new
    # `Candidate` with its resumed `task_id`, and would start twice.
    started: set[str] = set()
    # Each rescan replaces this rather than merging, so a spec the latest
    # scan no longer offers does not run because an earlier one did.
    pending: Sequence[Candidate] = candidates

    while True:
        candidate = next((c for c in pending if c.spec.id not in started), None)
        if candidate is None:
            if consecutive_aborts >= _BREAKER_THRESHOLD:
                # The breaker is consulted before a task, so a queue whose
                # last candidates all aborted falls out of the loop with the
                # count standing. Reporting `DRAINED` there would exit 0, and
                # launchd would record a successful night in which every task
                # died of one global condition.
                return _stop(ledger, batch_id, "INFRASTRUCTURE", in_flight, emit)
            return _stop(ledger, batch_id, "DRAINED", in_flight, emit)

        # Before each task, in this order: the deadline, then the budget,
        # then the breaker's standing count (§4.2.1's ordering, named once
        # here rather than re-derived at each check).
        if until is not None and clock() >= until:
            return _stop(ledger, batch_id, "UNTIL", in_flight, emit)

        remaining = budget_usd - ledger.batch_spend(batch_id)
        if candidate.spec.budget_usd > remaining:
            return _stop(ledger, batch_id, "BUDGET", in_flight, emit)

        if consecutive_aborts >= _BREAKER_THRESHOLD:
            return _stop(ledger, batch_id, "INFRASTRUCTURE", in_flight, emit)

        # Named before it starts: the one place the log shows which candidate
        # the latest scan chose.
        emit(f"{candidate.spec.id:<10} starting")
        started.add(candidate.spec.id)

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
        else:
            if isinstance(outcome, Refused):
                # No run to attach, and the breaker's count stands exactly
                # where it was: a refusal is not a task outcome.
                pass
            else:
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
                    # would never reach two. An in-flight state resets it the same
                    # way: two provider blips in a row must not end a night that
                    # would have recovered on its third task (backlog item 70).
                    consecutive_aborts = 0

                if outcome.state in IN_FLIGHT_STATES:
                    # Read from `reconcile`, never copied: the next batch scan's own
                    # definition of "in flight" is what decides a corpse there, and a
                    # second list here is how the two would come to disagree about
                    # what a finished task is.
                    in_flight.append((candidate.spec.id, outcome.state))

        # Rescanned after every task, success or not, so a child whose parent
        # just packaged is reachable tonight rather than tomorrow.
        pending = rescan()


def _is_layer(result: CellOutcome | Refused) -> bool:
    """`run_stack_batch`'s one predicate. A result adds a layer only when it
    is a `CellOutcome` in `READY_FOR_REVIEW`. Anything else is a miss:
    `EXHAUSTED`, any other state, or a `Refused`."""
    return isinstance(result, CellOutcome) and result.state == "READY_FOR_REVIEW"


def run_stack_batch(
    order: Sequence[Candidate],
    ledger: Ledger,
    budget_usd: float,
    until: datetime | None,
    runner: Callable[[Candidate, Candidate | None], CellOutcome | Refused],
    *,
    readiness_check: Callable[[], Readiness],
    clock: Callable[[], datetime] = datetime.now,
    emit: Callable[[str], None] = print,
) -> StopReason:
    """Run one stack's planned `order` once, never rescanning the repo
    (`SA-0142` fixes the order at batch start). `runner` takes each
    candidate and its predecessor: the last candidate before it,
    positionally, that reached `READY_FOR_REVIEW`, or `None` before any has.

    A candidate is refused here, before `run_batch` ever sees it, when a
    `depends_on` entry reaches a spec that ran this batch and missed. It can
    reach one directly, or through another refused spec. `--until`, the
    budget, the breaker and the batch row stay `run_batch`'s own.
    """
    order = list(order)
    remaining = list(order)
    missed: dict[str, frozenset[str]] = {}  # spec id -> the misses it reaches
    predecessor: Candidate | None = None

    def blocking(candidate: Candidate) -> frozenset[str]:
        found: set[str] = set()
        for entry in candidate.spec.depends_on:
            if entry in missed:
                found |= missed[entry]
        return frozenset(found)

    def resolve_prefix() -> list[Candidate]:
        while remaining:
            candidate = remaining[0]
            found = blocking(candidate)
            if not found:
                break
            names = ", ".join(sorted(found))
            emit(f"{candidate.spec.id:<10} refused  reaches {names}")
            missed[candidate.spec.id] = found
            remaining.pop(0)
        return remaining

    def wrapped(candidate: Candidate) -> CellOutcome | Refused:
        nonlocal predecessor
        pred = predecessor
        try:
            result = runner(candidate, pred)
        except Exception:
            missed[candidate.spec.id] = frozenset({candidate.spec.id})
            remaining.remove(candidate)
            raise
        remaining.remove(candidate)
        if _is_layer(result):
            predecessor = candidate
        else:
            missed[candidate.spec.id] = frozenset({candidate.spec.id})
        return result

    return run_batch(
        resolve_prefix(),
        ledger,
        budget_usd,
        until,
        wrapped,
        rescan=resolve_prefix,
        clock=clock,
        readiness_check=readiness_check,
        emit=emit,
    )


def _stop(
    ledger: Ledger,
    batch_id: int,
    reason: StopReason,
    in_flight: list[tuple[str, str]],
    emit: Callable[[str], None],
) -> StopReason:
    """Name every task this night left in flight, then close the batch row
    with `reason` — or with `INCOMPLETE` in its place, whenever `in_flight`
    is non-empty and `reason` is not already `INFRASTRUCTURE`.

    `INFRASTRUCTURE` outranks `INCOMPLETE`, which outranks every ordinary
    reason (`DRAINED`, `BUDGET`, `UNTIL`) — never the other way, and never
    hidden behind either (backlog item 70, `DESIGN.md` §4.2.1). Naming
    happens first and unconditionally, whatever the final reason turns out to
    be, `INFRASTRUCTURE` included: a stop reason says something went wrong,
    and this line says which spec to look at.

    The single call site for `close_batch` — every `_drive` return and
    `run_batch`'s `finally` come through here: decide the reason, close once,
    return it."""
    for spec_id, state in in_flight:
        emit(f"{spec_id:<10} left in flight in {state}")
    if in_flight and reason != "INFRASTRUCTURE":
        reason = "INCOMPLETE"
    ledger.close_batch(batch_id, reason)
    return reason
