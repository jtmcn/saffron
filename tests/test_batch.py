from datetime import datetime
from pathlib import Path

import pytest

from saffron.batch import ABORT_STATES, run_batch
from saffron.cell.session import CellOutcome
from saffron.intake import Spec
from saffron.ledger import Ledger
from saffron.preflight import Readiness
from saffron.scheduler import REQUEUE_STATES, Candidate


@pytest.fixture
def ledger(tmp_path):
    made = Ledger(tmp_path / "ledger.db")
    yield made
    made.close()


@pytest.fixture
def repo_id(ledger):
    return ledger.upsert_repo("thermal-edge", "/o", "/m.git", policy_sha="p" * 64)


def _ready() -> Readiness:
    """No readiness gate for this test. Named rather than defaulted: the loop
    used to bind a permissive stub, so a caller who simply forgot got a
    vacuous §4.4 step 1 and a night that could start on an expired token."""
    return Readiness(ok=True)


def _candidate(spec_id: str, *, budget_usd: float = 10.0) -> Candidate:
    return Candidate(
        path=Path(f"{spec_id}.md"),
        spec=Spec(id=spec_id, title="t", type="chore", budget_usd=budget_usd),
        spec_sha="s" * 64,
        task_id=None,
    )


def _outcome(*, state: str, run_id: int, task_id: int = 1) -> CellOutcome:
    return CellOutcome(
        state=state,
        task_id=task_id,
        run_id=run_id,
        task_dir=Path("/tmp/nonexistent-task-dir"),
    )


def _spend(ledger, repo_id: int, cost_usd: float) -> int:
    """Mint a run, a task and one closed attempt costing `cost_usd`, the
    scaffolding a real `run_one_cell` would have left behind — so
    `ledger.batch_spend` and `ledger.attach_run_to_batch` have real rows to
    read and stamp, exactly as `run_batch`'s docstring requires: the ledger is
    read back, never re-tallied by a caller."""
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    task_id = ledger.create_task(
        run_id,
        spec_id="TE-0001",
        spec_sha="s" * 64,
        branch="saffron/TE-0001",
        budget_usd=cost_usd,
    )
    attempt_id = ledger.open_attempt(task_id, phase="IMPLEMENT")
    ledger.close_attempt(
        attempt_id,
        session_id="sess",
        subtype="success",
        terminal_reason=None,
        num_turns=1,
        cost_usd_est=cost_usd,
    )
    return run_id


class FakeRunner:
    """Records calls in order and returns canned outcomes (or raises) one
    per call, so a test can assert exactly which candidates ran and in what
    order — no cell, no network."""

    def __init__(self, results):
        self._results = list(results)
        self.calls: list[Candidate] = []

    def __call__(self, candidate: Candidate) -> CellOutcome:
        self.calls.append(candidate)
        result = self._results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class CrashingRunner:
    """Mints a real run, task and billed attempt — exactly what a real
    `run_one_cell` does before its phase loop even opens — then raises
    without ever returning them, exactly what `run_one_cell`'s own outermost
    handler does: it re-raises the *original* exception untouched, carrying
    no `run_id`. Proves `run_batch` still finds and attaches that spend
    rather than losing it behind a `batch_id` that stays NULL forever."""

    def __init__(self, ledger: Ledger, repo_id: int, cost_usd: float):
        self._ledger = ledger
        self._repo_id = repo_id
        self._cost_usd = cost_usd
        self.calls: list[Candidate] = []

    def __call__(self, candidate: Candidate) -> CellOutcome:
        self.calls.append(candidate)
        _spend(self._ledger, self._repo_id, self._cost_usd)
        raise RuntimeError("cell died mid-repair, after real attempts billed")


class FakeClock:
    """Returns canned times in order, one per call — an eight-hour window is
    untestable any other way."""

    def __init__(self, times):
        self._times = list(times)

    def __call__(self) -> datetime:
        return self._times.pop(0) if len(self._times) > 1 else self._times[0]


def _batch_row(ledger, batch_id: int):
    return ledger._db.execute(
        "SELECT * FROM batches WHERE batch_id = ?", (batch_id,)
    ).fetchone()


def _latest_batch_id(ledger) -> int:
    row = ledger._db.execute(
        "SELECT batch_id FROM batches ORDER BY batch_id DESC LIMIT 1"
    ).fetchone()
    return int(row["batch_id"])


def test_a_drained_queue_runs_every_candidate_once_in_order(ledger, repo_id):
    candidates = [_candidate("TE-0001"), _candidate("TE-0002"), _candidate("TE-0003")]
    runs = [_spend(ledger, repo_id, 1.0) for _ in candidates]
    runner = FakeRunner([_outcome(state="READY_FOR_REVIEW", run_id=r) for r in runs])

    reason = run_batch(
        candidates,
        ledger,
        budget_usd=50.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
    )

    assert reason == "DRAINED"
    assert runner.calls == candidates

    batch_id = _latest_batch_id(ledger)
    row = _batch_row(ledger, batch_id)
    assert row["status"] == "DRAINED"


def test_an_empty_queue_drains_immediately(ledger):
    runner = FakeRunner([])

    reason = run_batch(
        [], ledger, budget_usd=50.0, until=None, runner=runner, readiness_check=_ready
    )

    assert reason == "DRAINED"
    assert runner.calls == []


def test_the_budget_gate_is_one_comparison_before_each_task(ledger, repo_id):
    candidates = [_candidate("TE-0001", budget_usd=20.0)]
    runner = FakeRunner([])

    reason = run_batch(
        candidates,
        ledger,
        budget_usd=5.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
    )

    assert reason == "BUDGET"
    assert runner.calls == []

    batch_id = _latest_batch_id(ledger)
    assert _batch_row(ledger, batch_id)["status"] == "BUDGET"


def test_a_task_overshooting_its_own_budget_does_not_stop_the_batch(ledger, repo_id):
    overshooting = _candidate("TE-0001", budget_usd=5.0)
    second = _candidate("TE-0002", budget_usd=5.0)
    # The first task's own attempt spends far more than its declared
    # budget_usd — the batch ceiling (30) still has plenty of room, so the
    # gate before the *second* task must still pass.
    run_one = _spend(ledger, repo_id, 25.0)
    run_two = _spend(ledger, repo_id, 1.0)
    runner = FakeRunner(
        [
            _outcome(state="READY_FOR_REVIEW", run_id=run_one),
            _outcome(state="READY_FOR_REVIEW", run_id=run_two),
        ]
    )

    reason = run_batch(
        [overshooting, second],
        ledger,
        budget_usd=30.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
    )

    assert reason == "DRAINED"
    assert runner.calls == [overshooting, second]


def test_the_until_deadline_is_read_from_an_injected_clock(ledger, repo_id):
    deadline = datetime(2026, 9, 5, 6, 30)
    candidates = [_candidate("TE-0001")]
    runner = FakeRunner([])
    clock = FakeClock([datetime(2026, 9, 5, 6, 30)])

    reason = run_batch(
        candidates,
        ledger,
        budget_usd=50.0,
        until=deadline,
        runner=runner,
        clock=clock,
        readiness_check=_ready,
    )

    assert reason == "UNTIL"
    assert runner.calls == []

    batch_id = _latest_batch_id(ledger)
    assert _batch_row(ledger, batch_id)["status"] == "UNTIL"


def test_the_clock_is_checked_before_a_task_still_inside_the_window(ledger, repo_id):
    deadline = datetime(2026, 9, 5, 6, 30)
    candidates = [_candidate("TE-0001")]
    run_id = _spend(ledger, repo_id, 1.0)
    runner = FakeRunner([_outcome(state="READY_FOR_REVIEW", run_id=run_id)])
    clock = FakeClock([datetime(2026, 9, 5, 1, 0)])

    reason = run_batch(
        candidates,
        ledger,
        budget_usd=50.0,
        until=deadline,
        runner=runner,
        clock=clock,
        readiness_check=_ready,
    )

    assert reason == "DRAINED"
    assert runner.calls == candidates


def test_two_consecutive_aborts_fire_the_breaker(ledger, repo_id):
    assert {"GATE_ERROR", "PREFLIGHT_FAILED", "RATE_LIMITED"} == ABORT_STATES
    # Never scheduler.REQUEUE_STATES — that set also contains CHANGES_REQUESTED
    # and ORPHANED, both states a task earned.
    assert ABORT_STATES < REQUEUE_STATES
    assert "CHANGES_REQUESTED" in REQUEUE_STATES - ABORT_STATES
    assert "ORPHANED" in REQUEUE_STATES - ABORT_STATES

    candidates = [_candidate("TE-0001"), _candidate("TE-0002"), _candidate("TE-0003")]
    run_one = _spend(ledger, repo_id, 1.0)
    run_two = _spend(ledger, repo_id, 1.0)
    runner = FakeRunner(
        [
            _outcome(state="GATE_ERROR", run_id=run_one),
            _outcome(state="PREFLIGHT_FAILED", run_id=run_two),
        ]
    )

    reason = run_batch(
        candidates,
        ledger,
        budget_usd=50.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
    )

    assert reason == "INFRASTRUCTURE"
    assert runner.calls == candidates[:2]

    batch_id = _latest_batch_id(ledger)
    assert _batch_row(ledger, batch_id)["status"] == "INFRASTRUCTURE"


def test_an_exhausted_task_between_two_aborts_resets_the_breaker(ledger, repo_id):
    """A fourth candidate, and it is the whole test.

    With three, this passed with the reset deleted: the breaker is only
    consulted *before* a task, so the count ran 1 -> 1 -> 2 with no fourth
    candidate for the standing 2 to block, and the queue drained either way.
    The fourth is what makes the reset observable — it is the task a standing
    count would refuse, and `runner.calls` is what says it was not refused."""
    candidates = [
        _candidate("TE-0001"),
        _candidate("TE-0002"),
        _candidate("TE-0003"),
        _candidate("TE-0004"),
    ]
    runs = [_spend(ledger, repo_id, 1.0) for _ in candidates]
    runner = FakeRunner(
        [
            _outcome(state="GATE_ERROR", run_id=runs[0]),
            _outcome(state="EXHAUSTED", run_id=runs[1]),
            _outcome(state="RATE_LIMITED", run_id=runs[2]),
            _outcome(state="READY_FOR_REVIEW", run_id=runs[3]),
        ]
    )

    reason = run_batch(
        candidates,
        ledger,
        budget_usd=50.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
    )

    # The breaker never reaches two in a row, so the queue drains — and every
    # candidate ran, including the fourth. Without the reset the count stands
    # at two by the third, the fourth is refused, and this is INFRASTRUCTURE
    # after three calls.
    assert reason == "DRAINED"
    assert runner.calls == candidates


def _assert_closed(ledger, reason, expected):
    assert reason == expected
    batch_id = _latest_batch_id(ledger)
    row = _batch_row(ledger, batch_id)
    assert row["status"] == expected
    assert row["ended_at"] is not None


def test_every_stop_path_closes_the_batch_row_with_its_reason(ledger, repo_id):
    # One test, all four stop reasons — a parametrized test would leave no
    # bare node id for the host to check this witness against.
    drained = run_batch(
        [],
        ledger,
        budget_usd=50.0,
        until=None,
        runner=FakeRunner([]),
        readiness_check=_ready,
    )
    _assert_closed(ledger, drained, "DRAINED")

    over_budget = [_candidate("TE-0001", budget_usd=100.0)]
    budget = run_batch(
        over_budget,
        ledger,
        budget_usd=5.0,
        until=None,
        runner=FakeRunner([]),
        readiness_check=_ready,
    )
    _assert_closed(ledger, budget, "BUDGET")

    deadline = datetime(2026, 9, 5, 6, 30)
    until_reason = run_batch(
        [_candidate("TE-0001")],
        ledger,
        budget_usd=50.0,
        until=deadline,
        runner=FakeRunner([]),
        clock=FakeClock([deadline]),
        readiness_check=_ready,
    )
    _assert_closed(ledger, until_reason, "UNTIL")

    infrastructure = run_batch(
        [_candidate("TE-0001")],
        ledger,
        budget_usd=50.0,
        until=None,
        runner=FakeRunner([]),
        readiness_check=lambda: Readiness(False, "auth", "no token"),
    )
    _assert_closed(ledger, infrastructure, "INFRASTRUCTURE")


def test_each_run_is_attached_to_the_batch_it_ran_under(ledger, repo_id):
    candidate = _candidate("TE-0001")
    run_id = _spend(ledger, repo_id, 1.0)
    runner = FakeRunner([_outcome(state="READY_FOR_REVIEW", run_id=run_id)])

    reason = run_batch(
        [candidate],
        ledger,
        budget_usd=50.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
    )

    assert reason == "DRAINED"
    row = ledger._db.execute(
        "SELECT batch_id FROM runs WHERE run_id = ?", (run_id,)
    ).fetchone()
    assert row["batch_id"] == _latest_batch_id(ledger)


def test_a_readiness_failure_closes_the_batch_without_starting_a_task(ledger, repo_id):
    candidates = [_candidate("TE-0001")]
    runner = FakeRunner([])

    reason = run_batch(
        candidates,
        ledger,
        budget_usd=50.0,
        until=None,
        runner=runner,
        readiness_check=lambda: Readiness(False, "auth", "token invalid"),
    )

    assert reason == "INFRASTRUCTURE"
    assert runner.calls == []

    batch_id = _latest_batch_id(ledger)
    assert _batch_row(ledger, batch_id)["status"] == "INFRASTRUCTURE"


def test_a_runner_that_raises_still_closes_the_batch_row(ledger, repo_id):
    candidates = [_candidate("TE-0001"), _candidate("TE-0002"), _candidate("TE-0003")]
    runner = FakeRunner([RuntimeError("mirror will not fetch"), RuntimeError("boom")])

    reason = run_batch(
        candidates,
        ledger,
        budget_usd=50.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
    )

    assert reason == "INFRASTRUCTURE"
    # Only the two raising candidates were tried — the breaker fired before a
    # third was ever started.
    assert runner.calls == candidates[:2]

    batch_id = _latest_batch_id(ledger)
    row = _batch_row(ledger, batch_id)
    assert row["status"] == "INFRASTRUCTURE"
    assert row["ended_at"] is not None


def test_a_crash_after_real_spend_still_counts_against_the_next_budget_gate(
    ledger, repo_id
):
    # The run this candidate's call minted spent 40 of a 50 budget before the
    # cell died — a raise carries no run_id, so without sweeping it in by
    # run_id, ledger.batch_spend would read 0.0 and the second candidate
    # would wrongly be admitted against a budget that is really down to 10.
    crashing = CrashingRunner(ledger, repo_id, cost_usd=40.0)
    expensive_second = _candidate("TE-0002", budget_usd=20.0)
    candidates = [_candidate("TE-0001"), expensive_second]

    reason = run_batch(
        candidates,
        ledger,
        budget_usd=50.0,
        until=None,
        runner=crashing,
        readiness_check=_ready,
    )

    assert reason == "BUDGET"
    assert crashing.calls == [candidates[0]]

    batch_id = _latest_batch_id(ledger)
    assert ledger.batch_spend(batch_id) == pytest.approx(40.0)
    minted_run = ledger._db.execute(
        "SELECT batch_id FROM runs ORDER BY run_id DESC LIMIT 1"
    ).fetchone()
    assert minted_run["batch_id"] == batch_id


def test_a_readiness_probe_that_raises_still_closes_the_batch_row(ledger, repo_id):
    """`readiness_check` was called outside every handler, and the real one
    does network and disk work. A raise there left `status` and `ended_at`
    NULL — the one state that cannot be told from a night still running, and
    the state §6's morning queue reads."""

    def _explodes() -> Readiness:
        raise OSError("mirror fetch died")

    with pytest.raises(OSError, match="mirror fetch died"):
        run_batch(
            [_candidate("TE-0001")],
            ledger,
            budget_usd=50.0,
            until=None,
            runner=FakeRunner([]),
            readiness_check=_explodes,
        )

    row = _batch_row(ledger, _latest_batch_id(ledger))
    assert row["status"] == "INFRASTRUCTURE"
    assert row["ended_at"] is not None


def test_an_interrupted_night_closes_its_row_rather_than_leaving_it_open(
    ledger, repo_id
):
    """`except Exception` does not catch `BaseException`, so an operator's
    Ctrl-C at 3am propagated straight through — and `run_one_cell`'s own
    outermost handler is deliberately `except BaseException` for the same
    reason. The interrupt must still stop the night; it must not leave a
    corpse behind while doing it."""

    def _interrupted(_candidate):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        run_batch(
            [_candidate("TE-0001")],
            ledger,
            budget_usd=50.0,
            until=None,
            runner=_interrupted,
            readiness_check=_ready,
        )

    row = _batch_row(ledger, _latest_batch_id(ledger))
    assert row["status"] == "INFRASTRUCTURE"
    assert row["ended_at"] is not None


def test_a_queue_whose_last_tasks_all_abort_is_not_a_clean_drain(ledger, repo_id):
    """The breaker is consulted before a task, so a queue whose final
    candidates all abort falls out of the loop with the count standing and
    used to report `DRAINED` — which the command maps to exit 0, so launchd
    would record a successful night in which every task died of one global
    condition."""
    candidates = [_candidate("TE-0001"), _candidate("TE-0002")]
    runs = [_spend(ledger, repo_id, 1.0) for _ in candidates]
    runner = FakeRunner(
        [
            _outcome(state="GATE_ERROR", run_id=runs[0]),
            _outcome(state="PREFLIGHT_FAILED", run_id=runs[1]),
        ]
    )

    reason = run_batch(
        candidates,
        ledger,
        budget_usd=50.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
    )

    assert reason == "INFRASTRUCTURE"
    assert runner.calls == candidates  # both ran; the verdict is about the exit
    assert _batch_row(ledger, _latest_batch_id(ledger))["status"] == "INFRASTRUCTURE"


def test_a_runner_that_raises_says_what_died(ledger, repo_id):
    """The exception was swallowed whole — not bound, not printed, not
    recorded. By the time `run_batch` returned it was gone, so an unattended
    night that died from a runtime that would not start left the operator a
    stop reason and no traceback anywhere."""
    lines: list[str] = []

    def _explodes(_candidate):
        raise RuntimeError("cell runtime would not start")

    reason = run_batch(
        [_candidate("TE-0001")],
        ledger,
        budget_usd=50.0,
        until=None,
        runner=_explodes,
        readiness_check=_ready,
        emit=lines.append,
    )

    assert reason == "DRAINED"
    assert any("cell runtime would not start" in line for line in lines)
    assert any("RuntimeError" in line for line in lines)
    assert any("TE-0001" in line for line in lines)


def test_the_until_stored_is_utc_not_the_operators_wall_clock(
    ledger, repo_id, monkeypatch
):
    """`_resolve_until` hands over a *naive local* datetime, and
    `isoformat()` stored the operator's wall clock while `started_at` beside
    it is `datetime('now')` in UTC — one row, two timestamps, eight hours
    apart in this timezone and not comparable.

    Pinned with a fixed TZ rather than the host's: on a machine already in UTC
    the two spellings coincide and the bug is invisible."""
    import time

    monkeypatch.setenv("TZ", "America/Los_Angeles")
    time.tzset()
    try:
        # 06:30 Pacific on 2026-09-06 is 13:30 UTC (PDT, UTC-7).
        deadline = datetime(2026, 9, 6, 6, 30)
        run_batch(
            [],
            ledger,
            budget_usd=50.0,
            until=deadline,
            runner=FakeRunner([]),
            readiness_check=_ready,
        )
    finally:
        # monkeypatch restores the variable; only tzset re-reads it.
        monkeypatch.undo()
        time.tzset()

    row = _batch_row(ledger, _latest_batch_id(ledger))
    assert row["until_ts"] == "2026-09-06 13:30:00"
    assert row["started_at"] < row["until_ts"]
