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

import dataclasses
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import Literal

from saffron import spec_review
from saffron.cell.session import CellOutcome
from saffron.intake import Spec
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

# A spec still unclean after this many revisions in one call escalates
# instead (ADR 7). Never read from the ledger: each call starts at zero (D1).
MAX_REVISE_ROUNDS = 3


class SpecReviewWait(Exception):
    """A stack batch's review wrapper raises this for a `wait` route.

    Caught in `_drive`, before its general handler, and fed the same wait
    `_wait_out_rate_limit` already builds for a `RATE_LIMITED` task. No run
    exists for it, so it is never turned into a `CellOutcome`."""

    def __init__(self, resets_at: int | None) -> None:
        super().__init__("spec review met the account's rate limit")
        self.resets_at = resets_at


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
    # Fired right after each task's attach, never for a `Refused` or a raise.
    after_attach: Callable[[Candidate, CellOutcome, int], None] | None = None,
    reserve_usd: float = 0.0,
    # `None` for every direct caller. Only `run_stack_batch` passes one,
    # through this same keyword (SA-0148).
    sleep: Callable[[float], None] | None = None,
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
            after_attach=after_attach,
            reserve_usd=reserve_usd,
            sleep=sleep,
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
    after_attach: Callable[[Candidate, CellOutcome, int], None] | None = None,
    reserve_usd: float = 0.0,
    sleep: Callable[[float], None] | None = None,
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
    # By spec id: a re-offered spec returns as a new `Candidate` and would
    # start twice. A rate-limited one with `sleep` set is taken back out.
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

        # `reserve_usd` is held back here, not subtracted from `budget_usd`
        # itself. The batch row still records the whole budget it was given.
        remaining = budget_usd - reserve_usd - ledger.batch_spend(batch_id)
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
        except SpecReviewWait as wait:
            # No run exists for a review wait, so this touches neither
            # `consecutive_aborts` nor the ledger.
            assert sleep is not None
            wait_stop = _wait_out_rate_limit(
                candidate, wait.resets_at, until, clock, emit, sleep
            )
            if wait_stop is not None:
                return _stop(ledger, batch_id, wait_stop, in_flight, emit)
            started.discard(candidate.spec.id)
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
                # After the attach above, so any fact `after_attach` builds
                # already carries this run's `batch_id`.
                if after_attach is not None:
                    after_attach(candidate, outcome, batch_id)

                if outcome.state == "RATE_LIMITED" and sleep is not None:
                    # A stack batch's own rule: the account's own limit
                    # closes the window for the next spec too (SA-0148).
                    wait_stop = _wait_out_rate_limit(
                        candidate, outcome.resets_at, until, clock, emit, sleep
                    )
                    if wait_stop is not None:
                        return _stop(ledger, batch_id, wait_stop, in_flight, emit)
                    started.discard(candidate.spec.id)
                else:
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


def _wait_out_rate_limit(
    candidate: Candidate,
    resets_at: int | None,
    until: datetime | None,
    clock: Callable[[], datetime],
    emit: Callable[[str], None],
    sleep: Callable[[float], None],
) -> Literal["UNTIL"] | None:
    """A `RATE_LIMITED` task's own wait, capped at six hours (SA-0148), and a
    stack batch's own `SpecReviewWait`'s wait besides. Returns `UNTIL` when
    one clock read shows the wait running at or past `until`. Otherwise it
    emits one line, sleeps, and returns `None`, so the caller retries the
    same spec.

    Bounds come before any subtraction. An untrusted cell's `resets_at`
    can be far larger than a plain subtraction can carry (measured)."""
    now = clock()
    now_ts = now.timestamp()
    readable = resets_at is not None and now_ts < resets_at <= now_ts + 21600
    wait = resets_at - now_ts if readable else 3600.0
    if until is not None and wait >= (until - now).total_seconds():
        return "UNTIL"
    reopen = (now + timedelta(seconds=wait)).strftime("%H:%M")
    emit(f"{candidate.spec.id:<10} rate limited, window reopens {reopen}")
    sleep(wait)
    return None


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
    reserve_usd: float = 0.0,
    end_review: Callable[[str, float, Mapping[str, Spec]], object] | None = None,
    # A real default. `SA-0144`'s caller passes none (SA-0148).
    sleep: Callable[[float], None] = time.sleep,
    # `None` means no review runs, and nothing here changes. `SA-0156` passes
    # the production one, and `saffron batch` passes none until then.
    review: Callable[..., spec_review.SpecReviewSession] | None = None,
    # Required whenever `review` is given (checked below). Mints the task a
    # review's own facts are recorded against. `SA-0156` passes the real one.
    mint: Callable[[Candidate], int] | None = None,
    # `None` means a `revise` route is escalated (a blocker) or run (none),
    # as it always was. `SA-0164` passes the production writer callable.
    revise: (
        Callable[
            [Candidate, Candidate | None, str | None, str],
            spec_review.SpecWriterSession,
        ]
        | None
    ) = None,
) -> StopReason:
    """Run one stack's planned `order` once, without rescanning (`SA-0142`). `runner` takes
    each candidate and its predecessor, the last one that reached `READY_FOR_REVIEW`, or
    `None` before any has. A `RATE_LIMITED` task waits on it instead of refusing (`sleep`,
    SA-0148). `review`, when given, runs first and can refuse the spec, raise, or wait
    (`SpecReviewWait`, ADR 7). A `revise` route calls `revise` for up to
    `MAX_REVISE_ROUNDS` rounds.

    A candidate is refused before `run_batch` sees it, when `depends_on` reaches a spec
    that ran and missed, direct or through a refused spec. `reserve_usd` holds back the
    budget check, and `end_review` runs once, given the batch id, reserve and specs."""
    if review is not None and mint is None:
        raise ValueError("run_stack_batch needs mint whenever review is given")
    order = list(order)
    remaining = list(order)
    missed: dict[str, frozenset[str]] = {}  # spec id -> the misses it reaches
    predecessor: Candidate | None = None
    predecessor_task_id: int | None = None
    position = 0
    # Spec ids cleared `run`. A `wait` route is never added here, so the
    # next call for that spec reviews it again (ADR 7).
    reviewed: set[str] = set()
    # Spec id -> the task `mint` gave it, kept for one call only. A rerun
    # after `wait` or `RATE_LIMITED` reuses it rather than minting again.
    task_ids: dict[str, int] = {}
    # Spec id -> revisions run this call, never the ledger's own count (D1):
    # every call of `run_stack_batch` starts every spec at zero.
    rounds: dict[str, int] = {}
    # Spec id -> the pair a rate-limited writer call was given. A retry
    # after the wait hands `revise` the same one, with no review between.
    pending_revision: dict[str, tuple[str | None, str]] = {}

    # One `stack_layers` row per task that reaches `READY_FOR_REVIEW`, at
    # generation 0. The predecessor is the last such task, not `candidate`.
    def record_layer(candidate: Candidate, outcome: CellOutcome, batch_id: int) -> None:
        nonlocal position, predecessor_task_id
        if not _is_layer(outcome):
            return
        position += 1
        ledger.record_stack_layer(
            outcome.task_id,
            position=position,
            predecessor_task_id=predecessor_task_id,
            generation=0,
        )
        predecessor_task_id = outcome.task_id

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
        # `remaining` holds the object `run_batch` offered, not the one
        # `dataclasses.replace` builds below. `list.remove` matches by value.
        original = candidate
        if review is not None:
            if candidate.spec.id not in task_ids:
                # Minted once per spec, whatever `candidate.task_id` names.
                # A raise here is a miss, as one from `review` or `runner` is.
                assert mint is not None
                try:
                    task_id = mint(candidate)
                except Exception:
                    missed[candidate.spec.id] = frozenset({candidate.spec.id})
                    remaining.remove(original)
                    raise
                task_ids[candidate.spec.id] = task_id
                ledger.attach_run_to_batch(
                    ledger.task_run(task_id), ledger.latest_batch_id()
                )
            candidate = dataclasses.replace(
                candidate, task_id=task_ids[candidate.spec.id]
            )
        if review is not None and candidate.spec.id not in reviewed:
            task_id = task_ids[candidate.spec.id]
            while True:
                pending = pending_revision.pop(candidate.spec.id, None)
                if pending is None:
                    text_row = ledger.spec_text(task_id)
                    spec_text = text_row["text"] if text_row is not None else None
                    kwargs = {} if spec_text is None else {"spec_text": spec_text}
                    # A raise from `review` is a miss, as one from `runner`
                    # is below, with no attempt for the session it never opened.
                    try:
                        session = review(candidate, pred, **kwargs)
                    except Exception as exc:
                        ledger.record_spec_review(
                            task_id,
                            route="error",
                            block=None,
                            block_sha256=None,
                            error=f"{type(exc).__name__}: {exc}",
                        )
                        ledger.set_task_state(task_id, "GATE_ERROR")
                        missed[candidate.spec.id] = frozenset({candidate.spec.id})
                        remaining.remove(original)
                        raise
                    read = spec_review.read_spec_review(session)
                    route = spec_review.spec_review_route(read)
                    capped = False
                    if route == "revise":
                        has_blocker = any(
                            f.severity == "blocker" for f in read.findings
                        )
                        if revise is None:
                            route = "escalate" if has_blocker else "run"
                        elif rounds.get(candidate.spec.id, 0) >= MAX_REVISE_ROUNDS:
                            route = "escalate"
                            capped = True
                    attempt_id = ledger.open_attempt(task_id, phase="SPEC_REVIEW")
                    ledger.close_attempt(
                        attempt_id,
                        session_id=session.session_id,
                        subtype="error" if session.error is not None else "success",
                        terminal_reason=None,
                        num_turns=session.num_turns,
                        cost_usd_est=session.cost_usd,
                    )
                    ledger.record_spec_review(
                        task_id,
                        route=route,
                        block=read.block,
                        block_sha256=read.block_sha256,
                        error=read.error,
                    )
                    if route == "wait":
                        ledger.set_task_state(task_id, "RATE_LIMITED")
                        raise SpecReviewWait(resets_at=read.resets_at)
                    if route == "escalate":
                        blockers = sum(
                            1 for f in read.findings if f.severity == "blocker"
                        )
                        suffix = (
                            f" after {MAX_REVISE_ROUNDS} revisions" if capped else ""
                        )
                        emit(f"{candidate.spec.id:<10} escalated  {blockers}{suffix}")
                        ledger.set_task_state(task_id, "SPEC_WITHHELD")
                        missed[candidate.spec.id] = frozenset({candidate.spec.id})
                        remaining.remove(original)
                        return Refused(
                            reason=f"spec review escalated with {blockers} blocker(s)"
                        )
                    if route == "error":
                        emit(f"{candidate.spec.id:<10} unreviewed  {read.error}")
                        ledger.set_task_state(task_id, "GATE_ERROR")
                        missed[candidate.spec.id] = frozenset({candidate.spec.id})
                        remaining.remove(original)
                        raise RuntimeError(
                            f"spec review for {candidate.spec.id} could not be read"
                        )
                    if route == "run":
                        reviewed.add(candidate.spec.id)
                        break
                    # route == "revise": a fresh round starts from this read.
                    review_text = session.text
                else:
                    spec_text, review_text = pending

                assert revise is not None
                needed = (
                    spec_review.SPEC_WRITER_SESSION_USD
                    + spec_review.SPEC_REVIEW_SESSION_USD
                    + candidate.spec.budget_usd
                )
                budget_left = (
                    budget_usd
                    - reserve_usd
                    - ledger.batch_spend(ledger.latest_batch_id())
                )
                if budget_left < needed:
                    emit(
                        f"{candidate.spec.id:<10} unrevised  "
                        f"needs {needed:.3f}, {budget_left:.3f} left"
                    )
                    missed[candidate.spec.id] = frozenset({candidate.spec.id})
                    remaining.remove(original)
                    return Refused(
                        reason=f"revision for {candidate.spec.id} needs more budget "
                        "than remains"
                    )
                try:
                    turn = revise(candidate, pred, spec_text, review_text)
                except Exception:
                    ledger.set_task_state(task_id, "GATE_ERROR")
                    missed[candidate.spec.id] = frozenset({candidate.spec.id})
                    remaining.remove(original)
                    raise
                attempt_id = ledger.open_attempt(
                    task_id, phase=spec_review.WRITING_PHASE
                )
                ledger.close_attempt(
                    attempt_id,
                    session_id=turn.session_id,
                    subtype="error" if turn.error is not None else "success",
                    terminal_reason=None,
                    num_turns=turn.num_turns,
                    cost_usd_est=turn.cost_usd,
                )
                if turn.resets_at is not None:
                    ledger.set_task_state(task_id, "RATE_LIMITED")
                    pending_revision[candidate.spec.id] = (spec_text, review_text)
                    raise SpecReviewWait(resets_at=turn.resets_at)
                if turn.error is not None:
                    emit(f"{candidate.spec.id:<10} unrevised  {turn.error}")
                    ledger.set_task_state(task_id, "GATE_ERROR")
                    missed[candidate.spec.id] = frozenset({candidate.spec.id})
                    remaining.remove(original)
                    raise RuntimeError(
                        f"spec writer for {candidate.spec.id} could not be read"
                    )
                rounds[candidate.spec.id] = rounds.get(candidate.spec.id, 0) + 1
                ledger.record_spec_text(
                    task_id,
                    origin="revision",
                    spec_id=candidate.spec.id,
                    path=f".saffron/specs/{candidate.path.name}",
                    text=turn.text,
                )
                emit(f"{candidate.spec.id:<10} revised  {rounds[candidate.spec.id]}")
        try:
            result = runner(candidate, pred)
        except Exception:
            missed[candidate.spec.id] = frozenset({candidate.spec.id})
            remaining.remove(original)
            raise
        if isinstance(result, CellOutcome) and result.state == "RATE_LIMITED":
            # Neither a layer nor a miss: `original` stays in `remaining` so
            # the same spec is offered again, against this same `pred`.
            return result
        remaining.remove(original)
        if _is_layer(result):
            predecessor = candidate
        else:
            missed[candidate.spec.id] = frozenset({candidate.spec.id})
        return result

    stopped = run_batch(
        resolve_prefix(),
        ledger,
        budget_usd,
        until,
        wrapped,
        rescan=resolve_prefix,
        clock=clock,
        readiness_check=readiness_check,
        emit=emit,
        after_attach=record_layer,
        reserve_usd=reserve_usd,
        sleep=sleep,
    )
    if end_review is not None:
        specs = {c.spec.id: c.spec for c in order}
        end_review(str(ledger.latest_batch_id()), reserve_usd, specs)
    return stopped


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
