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
    runner: Callable[[Candidate], CellOutcome],
    *,
    rescan: Callable[[], Sequence[Candidate]],
    clock: Callable[[], datetime] = datetime.now,
    readiness_check: Callable[[], Readiness],
    emit: Callable[[str], None] = print,
) -> StopReason:
    """Drive one night, starting from the opening scan's already-sorted
    candidates and rescanning after every task for the rest of the night.

    `candidates` is `build_queue`'s own return value for the *opening* scan
    only — this module never re-derives it (`cli.py` is forbidden here, and
    re-deriving it would mean copying four `cli`-private helpers). It decides
    only which candidate runs first; every candidate after that comes from
    `rescan`. `ledger` is an ordinary argument, never a keyword default: every
    witness that involves money reads the batch's spend back through it
    rather than trusting a tally kept here, which is exactly what a caller cut
    mid-loop would lose.

    `runner` takes no default, and the reason changed without the decision
    changing. It used to be that no real default was *constructible*: building
    a `CellSpec` from a `Candidate` needed the ceilings and stacked-on
    resolvers, both `cli`-private and both forbidden to the spec that built
    this loop, so a default that built one itself would pass no stacked-on
    parent for any candidate, cutting every child of a stack from `base_sha`
    and failing its own gates the moment it ran (§4.2.1). `task.run_task` is
    now that driver and importable, so a real default *could* be written. It
    is still not, for `readiness_check`'s reason rather than its own: every
    test here supplies a fake runner, and a default would buy production
    nothing — `cli` always passes the real one — while making a forgotten
    argument silent instead of a `TypeError`. `readiness_check` takes no default
    either, and for a related reason: `check_readiness` needs repo paths and a
    token this signature never receives, so no *real* default is constructible
    here. The permissive stub that stood in its place meant a caller who
    forgot the argument got a vacuous gate and a night that starts on an
    expired token — which is precisely what §4.4 step 1 exists to prevent. A
    night with no readiness gate is now something a caller has to say out
    loud. `clock` keeps its real default, because `datetime.now` is one.

    `rescan` takes no default either, for `readiness_check`'s own reason: no
    real one is constructible here (`cli.py` is forbidden, and a rescan needs
    the pinned base, the ledger, and the repo's own policy and specs at that
    base — all of it `cli._resolve_queue`'s to build). Called after every
    task this loop runs — never only once the opening list is exhausted — and
    expected to return the *current* candidates over the same pinned base,
    resolved with `stamp_orphaned=False`: a task this same night left in
    flight is live work, not a corpse a dead scan should stamp. Its return
    value **replaces** the loop's notion of what is left to run; it is never
    merged with the opening list or any earlier rescan, because a spec the
    latest rescan no longer offers (an open-pull-request overlap a sibling
    task just created, say) must not run anyway. The loop tracks what it has
    started tonight by `Candidate.spec.id`, never by comparing whole
    `Candidate`s — a spec that ended in a re-queueing state comes back from a
    rescan as a *new* `Candidate` carrying its resumed `task_id`, and value
    equality would start it a second time.

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
    runner: Callable[[Candidate], CellOutcome],
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
    # Every spec id this night has already started, whatever task_id it ran
    # under — checked by identity, never by comparing whole `Candidate`s: a
    # spec a rescan re-offers after a `RATE_LIMITED` task comes back as a
    # *new* `Candidate` carrying the resumed `task_id`, so value equality
    # would start it a second time.
    started: set[str] = set()
    # The opening scan's own list decides only the first task — everything
    # after it comes from `rescan`, replacing this outright rather than
    # merging with it, so a spec the latest rescan no longer offers (an
    # open-pull-request overlap a sibling task just created, say) does not
    # run just because an earlier scan once offered it.
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

        # The log names a task before it starts — the one place an operator
        # (or a rescan's own witness) can see which candidate the *latest*
        # scan chose to run next, ahead of calling into it.
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
            # `create_run` mints the row with no `batch_id`; stamped on after
            # the fact, the shape `record_push` already uses on `tasks`.
            ledger.attach_run_to_batch(outcome.run_id, batch_id)

            if outcome.state in ABORT_STATES:
                consecutive_aborts += 1
            else:
                # Any earned state resets the counter (`EXHAUSTED` included),
                # in-flight states too — two blips must not end a recoverable night.
                consecutive_aborts = 0

            if outcome.state in IN_FLIGHT_STATES:
                # Read from `reconcile`, never copied, so the two share one
                # definition of "in flight".
                in_flight.append((candidate.spec.id, outcome.state))

        # Rescanned after every task, success or not, so a child whose parent
        # just packaged is reachable tonight rather than tomorrow.
        pending = rescan()


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
