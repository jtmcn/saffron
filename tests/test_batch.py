import dataclasses
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from saffron.agents.artifacts import hash_artifact
from saffron.batch import ABORT_STATES, run_batch
from saffron.cell.session import CellOutcome
from saffron.intake import Spec
from saffron.ledger import Ledger
from saffron.preflight import Readiness
from saffron.scheduler import REQUEUE_STATES, Candidate, build_queue
from saffron.task import Refused
from tests.test_scheduler import _write_spec


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


def _soon() -> int:
    """A `resets_at` a minute past now, read for a `RATE_LIMITED` outcome
    that never needs an exact figure checked."""
    return int(datetime.now(UTC).timestamp()) + 60


def _candidate(
    spec_id: str,
    *,
    budget_usd: float = 10.0,
    priority: int = 3,
    depends_on: list[str] | None = None,
) -> Candidate:
    return Candidate(
        path=Path(f"{spec_id}.md"),
        spec=Spec(
            id=spec_id,
            title="t",
            type="chore",
            budget_usd=budget_usd,
            priority=priority,
            depends_on=depends_on or [],
        ),
        spec_sha="s" * 64,
        task_id=None,
    )


def _spend_task(ledger, repo_id: int, cost_usd: float) -> tuple[int, int]:
    """`_spend`, plus the `task_id` it minted. A layer's outcome must carry
    its own task_id, never the shared default `_outcome` otherwise uses,
    because `record_stack_layer` reads the row it names."""
    run_id = _spend(ledger, repo_id, cost_usd)
    row = ledger._db.execute(
        "SELECT task_id FROM tasks WHERE run_id = ?", (run_id,)
    ).fetchone()
    return run_id, int(row["task_id"])


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


class FakeStackRunner:
    """`run_stack_batch`'s predecessor-aware runner. Records each call as
    `(spec id, predecessor spec id or None)`, in order. Keyed by spec id
    rather than queued, so a table's rows can be given in any order."""

    def __init__(self, results: Mapping[str, CellOutcome | Refused | Exception]):
        self._results = dict(results)
        self.calls: list[tuple[str, str | None]] = []

    def __call__(self, candidate: Candidate, predecessor: Candidate | None):
        self.calls.append(
            (candidate.spec.id, predecessor.spec.id if predecessor else None)
        )
        result = self._results[candidate.spec.id]
        if isinstance(result, Exception):
            raise result
        return result


class ScriptedRunner:
    """Both `stack_layers` witnesses' one arrangement. Each call plays back
    the next `(spec id, entry)` pair from an ordered script. A `Refused`
    entry creates nothing. Any other entry creates a run and a task, records
    a push unique to the spec, and packages `READY_FOR_REVIEW` or
    `MERGE_FAILED` through `set_task_package`. It then returns an outcome,
    or raises the entry once the task exists."""

    def __init__(
        self,
        ledger: Ledger,
        repo_id: int,
        script: list[tuple[str, str | Refused | Exception]],
    ):
        self._ledger = ledger
        self._repo_id = repo_id
        self._script = list(script)
        self.calls: list[tuple[str, str | None]] = []
        self.task_ids: dict[str, int] = {}
        self.pushed_shas: dict[str, str] = {}

    def __call__(
        self, candidate: Candidate, predecessor: Candidate | None = None
    ) -> CellOutcome | Refused:
        self.calls.append(
            (candidate.spec.id, predecessor.spec.id if predecessor else None)
        )
        spec_id, entry = self._script.pop(0)
        if spec_id != candidate.spec.id:
            raise ValueError(f"script expected {spec_id!r}, got {candidate.spec.id!r}")
        if isinstance(entry, Refused):
            return entry
        run_id = self._ledger.create_run(self._repo_id, base_sha="a" * 40)
        task_id = self._ledger.create_task(
            run_id,
            spec_id=spec_id,
            spec_sha="s" * 64,
            branch=f"saffron/{spec_id}",
        )
        self.task_ids[spec_id] = task_id
        pushed_sha = f"{spec_id}-sha"
        self.pushed_shas[spec_id] = pushed_sha
        self._ledger.record_push(task_id, pushed_sha)
        if isinstance(entry, Exception):
            raise entry
        if entry in ("READY_FOR_REVIEW", "MERGE_FAILED"):
            self._ledger.set_task_package(
                task_id,
                entry,
                f"saffron/{spec_id}",
                pushed_sha,
                "https://example.invalid/1",
            )
        return _outcome(state=entry, run_id=run_id, task_id=task_id)


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


class AdvancingClock:
    """A clock whose `now` its own `sleep` advances by exactly the seconds
    slept. A plain read never moves it forward."""

    def __init__(self, start: datetime):
        self._now = start
        self.sleeps: list[float] = []

    def __call__(self) -> datetime:
        return self._now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self._now += timedelta(seconds=seconds)

    def advance(self, seconds: float) -> None:
        self._now += timedelta(seconds=seconds)


class RateLimitScript:
    """`run_stack_batch`'s runner for the rate-limit witnesses. Each call
    pops the next step queued for its spec id, mints a run and task at the
    step's cost, and returns a `CellOutcome`. A step can advance the clock,
    name `resets_at` directly, or name an `offset` read from the clock,
    after its own advance."""

    def __init__(
        self,
        ledger: Ledger,
        repo_id: int,
        clock: AdvancingClock,
        steps: Mapping[str, list[dict]],
    ):
        self._ledger = ledger
        self._repo_id = repo_id
        self._clock = clock
        self._steps = {spec_id: list(queue) for spec_id, queue in steps.items()}
        self.calls: list[tuple[str, str | None]] = []

    def __call__(
        self, candidate: Candidate, predecessor: Candidate | None = None
    ) -> CellOutcome:
        spec_id = candidate.spec.id
        self.calls.append((spec_id, predecessor.spec.id if predecessor else None))
        step = self._steps[spec_id].pop(0)
        if step.get("advance"):
            self._clock.advance(step["advance"])
        run_id, task_id = _spend_task(
            self._ledger, self._repo_id, step.get("cost", 1.0)
        )
        outcome = _outcome(state=step["state"], run_id=run_id, task_id=task_id)
        if "offset" in step:
            resets_at = int(self._clock().timestamp()) + step["offset"]
            outcome = dataclasses.replace(outcome, resets_at=resets_at)
        elif "resets_at" in step:
            outcome = dataclasses.replace(outcome, resets_at=step["resets_at"])
        return outcome


def _raise_on_real_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """A build that calls `time.sleep` by its module attribute, rather
    than the injected `sleep` keyword, fails loudly here instead of
    sleeping for real seconds."""
    import time

    def _raise(seconds: float) -> None:
        raise AssertionError(f"real time.sleep called with {seconds}")

    monkeypatch.setattr(time, "sleep", _raise)


def _batch_row(ledger, batch_id: int):
    return ledger._db.execute(
        "SELECT * FROM batches WHERE batch_id = ?", (batch_id,)
    ).fetchone()


def _latest_batch_id(ledger) -> int:
    row = ledger._db.execute(
        "SELECT batch_id FROM batches ORDER BY batch_id DESC LIMIT 1"
    ).fetchone()
    return int(row["batch_id"])


def _stack_layers(ledger, *, batch_id: int | None = None) -> list[dict]:
    """Every `stack_layers` row, ordered by position, as plain dicts so an
    assertion can compare them by value. Scoped to one batch when asked."""
    if batch_id is None:
        rows = ledger._db.execute(
            "SELECT * FROM stack_layers ORDER BY position"
        ).fetchall()
    else:
        rows = ledger._db.execute(
            "SELECT * FROM stack_layers WHERE batch_key = ? ORDER BY position",
            (str(batch_id),),
        ).fetchall()
    return [dict(row) for row in rows]


def _stack_script() -> list[tuple[str, str | Refused | Exception]]:
    """The eight-spec script both `stack_layers` witnesses drive, in order.
    Three specs reach `READY_FOR_REVIEW` and become layers 1, 2 and 3. The
    other five miss it in five different ways. No two misses sit next to
    each other, so the breaker never fires."""
    return [
        ("TE-7", "READY_FOR_REVIEW"),
        ("TE-3", "GATE_ERROR"),
        ("TE-9", "READY_FOR_REVIEW"),
        ("TE-1", RuntimeError("boom")),
        ("TE-5", "EXHAUSTED"),
        ("TE-8", "MERGE_FAILED"),
        ("TE-2", Refused(reason="scripted")),
        ("TE-6", "READY_FOR_REVIEW"),
    ]


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
        rescan=lambda: candidates,
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
        [],
        ledger,
        budget_usd=50.0,
        until=None,
        runner=runner,
        rescan=lambda: [],
        readiness_check=_ready,
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
        rescan=lambda: candidates,
        readiness_check=_ready,
    )

    assert reason == "BUDGET"
    assert runner.calls == []

    batch_id = _latest_batch_id(ledger)
    assert _batch_row(ledger, batch_id)["status"] == "BUDGET"


def test_a_task_overshooting_its_own_budget_does_not_stop_the_batch(ledger, repo_id):
    overshooting = _candidate("TE-0001", budget_usd=5.0)
    second = _candidate("TE-0002", budget_usd=5.0)
    candidates = [overshooting, second]
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
        candidates,
        ledger,
        budget_usd=30.0,
        until=None,
        runner=runner,
        rescan=lambda: candidates,
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
        rescan=lambda: candidates,
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
        rescan=lambda: candidates,
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
        rescan=lambda: candidates,
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
        rescan=lambda: candidates,
        readiness_check=_ready,
    )

    # The breaker never reaches two in a row, so the queue drains — and every
    # candidate ran, including the fourth. Without the reset the count stands
    # at two by the third, the fourth is refused, and this is INFRASTRUCTURE
    # after three calls.
    assert reason == "DRAINED"
    assert runner.calls == candidates


def test_a_task_left_in_flight_is_not_a_clean_drain(ledger, repo_id):
    """A night whose queue drains after a task came back still in flight
    closes INCOMPLETE, not DRAINED. DRAINED says the queue emptied, and a
    queue that emptied with a task stopped mid-phase is a different night:
    nobody can say what happened to that task, which is not the same as the
    task failing."""
    candidates = [_candidate("TE-0001")]
    run_id = _spend(ledger, repo_id, 1.0)
    runner = FakeRunner([_outcome(state="REBUTTING", run_id=run_id)])

    reason = run_batch(
        candidates,
        ledger,
        budget_usd=50.0,
        until=None,
        runner=runner,
        rescan=lambda: candidates,
        readiness_check=_ready,
    )

    assert reason == "INCOMPLETE"
    batch_id = _latest_batch_id(ledger)
    assert _batch_row(ledger, batch_id)["status"] == "INCOMPLETE"


def test_a_task_left_in_flight_outranks_an_ordinary_stop(ledger, repo_id):
    """INCOMPLETE outranks the other ordinary stop reasons: a night that left
    a task in flight and then stopped at BUDGET or at UNTIL still closes
    INCOMPLETE, because what the morning most needs to know is that a task
    reached no end state, not which of the ordinary limits came first."""
    # BUDGET, after an in-flight task: the first candidate fits the budget
    # and comes back REVIEWING; the second cannot fit what is left.
    over_budget = [_candidate("TE-0001", budget_usd=1.0), _candidate("TE-0002")]
    run_id = _spend(ledger, repo_id, 1.0)
    runner = FakeRunner([_outcome(state="REVIEWING", run_id=run_id)])
    lines: list[str] = []

    budget_reason = run_batch(
        over_budget,
        ledger,
        budget_usd=5.0,
        until=None,
        runner=runner,
        rescan=lambda: over_budget,
        readiness_check=_ready,
        emit=lines.append,
    )
    assert budget_reason == "INCOMPLETE"
    assert _batch_row(ledger, _latest_batch_id(ledger))["status"] == "INCOMPLETE"
    assert any("TE-0001" in line and "REVIEWING" in line for line in lines)

    # UNTIL, after an in-flight task: the clock is still inside the window
    # for the first candidate, then past the deadline for the second.
    deadline = datetime(2026, 9, 5, 6, 30)
    run_id_two = _spend(ledger, repo_id, 1.0)
    runner_two = FakeRunner([_outcome(state="REVIEWING", run_id=run_id_two)])
    clock = FakeClock([datetime(2026, 9, 5, 1, 0), deadline])
    until_candidates = [_candidate("TE-0003"), _candidate("TE-0004")]

    until_reason = run_batch(
        until_candidates,
        ledger,
        budget_usd=50.0,
        until=deadline,
        runner=runner_two,
        clock=clock,
        rescan=lambda: until_candidates,
        readiness_check=_ready,
        emit=lines.append,
    )
    assert until_reason == "INCOMPLETE"
    assert _batch_row(ledger, _latest_batch_id(ledger))["status"] == "INCOMPLETE"
    assert any("TE-0003" in line and "REVIEWING" in line for line in lines)


def test_the_breaker_still_reports_infrastructure_over_a_task_left_in_flight(
    ledger, repo_id
):
    """INFRASTRUCTURE outranks INCOMPLETE. A breaker that fires after a task
    was left in flight still closes INFRASTRUCTURE, the one stop reason that
    must never be hidden behind another — and the night still names the task
    it left in flight, and that task's state, on the way out."""
    candidates = [
        _candidate("TE-0001"),
        _candidate("TE-0002"),
        _candidate("TE-0003"),
    ]
    runs = [_spend(ledger, repo_id, 1.0) for _ in candidates]
    runner = FakeRunner(
        [
            _outcome(state="REBUTTING", run_id=runs[0]),
            _outcome(state="GATE_ERROR", run_id=runs[1]),
            _outcome(state="PREFLIGHT_FAILED", run_id=runs[2]),
        ]
    )
    lines: list[str] = []

    reason = run_batch(
        candidates,
        ledger,
        budget_usd=50.0,
        until=None,
        runner=runner,
        rescan=lambda: candidates,
        readiness_check=_ready,
        emit=lines.append,
    )

    assert reason == "INFRASTRUCTURE"
    assert any("TE-0001" in line and "REBUTTING" in line for line in lines)
    batch_id = _latest_batch_id(ledger)
    assert _batch_row(ledger, batch_id)["status"] == "INFRASTRUCTURE"

    # The breaker also fires before a task, mid-loop, when a fourth candidate
    # is still queued — a different `_stop` call, and it names the same way.
    queued = [_candidate(f"TE-001{i}") for i in range(4)]
    runs = [_spend(ledger, repo_id, 1.0) for _ in range(3)]
    runner = FakeRunner(
        [
            _outcome(state="REBUTTING", run_id=runs[0]),
            _outcome(state="GATE_ERROR", run_id=runs[1]),
            _outcome(state="GATE_ERROR", run_id=runs[2]),
        ]
    )
    lines = []
    reason = run_batch(
        queued,
        ledger,
        budget_usd=50.0,
        until=None,
        runner=runner,
        rescan=lambda: queued,
        readiness_check=_ready,
        emit=lines.append,
    )
    assert reason == "INFRASTRUCTURE"
    assert runner.calls == queued[:3]
    assert any("TE-0010" in line and "REBUTTING" in line for line in lines)


def test_in_flight_outcomes_do_not_fire_the_breaker(ledger, repo_id):
    """The breaker is unchanged: an in-flight outcome still resets the
    consecutive-abort count, so two provider blips in a row do not end a
    night that would have recovered on its third task. A night of
    GATE_ERROR, REBUTTING, RATE_LIMITED, READY_FOR_REVIEW runs all four
    candidates and closes INCOMPLETE, not INFRASTRUCTURE — item 70 argues
    this deliberately, and the recovery it relies on works."""
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
            _outcome(state="REBUTTING", run_id=runs[1]),
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
        rescan=lambda: candidates,
        readiness_check=_ready,
    )

    assert reason == "INCOMPLETE"
    assert runner.calls == candidates
    assert _batch_row(ledger, _latest_batch_id(ledger))["status"] == "INCOMPLETE"


def test_a_task_left_in_flight_is_named_on_the_way_out(ledger, repo_id):
    """The night names each task it left in flight, and the state it
    stopped in, on the way out, whatever the stop reason. A stop reason says
    that something went wrong; this line says which spec to look at."""
    candidates = [_candidate("TE-0001"), _candidate("TE-0002")]
    run_one = _spend(ledger, repo_id, 1.0)
    run_two = _spend(ledger, repo_id, 1.0)
    runner = FakeRunner(
        [
            _outcome(state="REBUTTING", run_id=run_one),
            _outcome(state="GATING", run_id=run_two),
        ]
    )
    lines: list[str] = []

    reason = run_batch(
        candidates,
        ledger,
        budget_usd=50.0,
        until=None,
        runner=runner,
        rescan=lambda: candidates,
        readiness_check=_ready,
        emit=lines.append,
    )

    assert reason == "INCOMPLETE"
    assert any("TE-0001" in line and "REBUTTING" in line for line in lines)
    assert any("TE-0002" in line and "GATING" in line for line in lines)


def test_a_night_that_raises_still_names_the_task_it_left_in_flight(
    ledger, repo_id, monkeypatch
):
    """`run_batch`'s `finally` closes `INFRASTRUCTURE` for a raise nothing
    below caught — a ledger error, a 3am Ctrl-C. That is the night the
    operator most needs to know which spec was left mid-phase."""
    import sqlite3

    real_spend = ledger.batch_spend
    calls = {"n": 0}

    def _locked_on_the_second_candidate(batch_id):
        calls["n"] += 1
        if calls["n"] == 2:
            raise sqlite3.OperationalError("database is locked")
        return real_spend(batch_id)

    monkeypatch.setattr(ledger, "batch_spend", _locked_on_the_second_candidate)
    run_id = _spend(ledger, repo_id, 1.0)
    lines: list[str] = []
    locked_candidates = [_candidate("TE-0001"), _candidate("TE-0002")]
    with pytest.raises(sqlite3.OperationalError):
        run_batch(
            locked_candidates,
            ledger,
            budget_usd=50.0,
            until=None,
            runner=FakeRunner([_outcome(state="REBUTTING", run_id=run_id)]),
            rescan=lambda: locked_candidates,
            readiness_check=_ready,
            emit=lines.append,
        )
    assert _batch_row(ledger, _latest_batch_id(ledger))["status"] == "INFRASTRUCTURE"
    assert any("TE-0001" in line and "REBUTTING" in line for line in lines)

    monkeypatch.undo()
    run_id = _spend(ledger, repo_id, 1.0)
    seen: list = []

    def _interrupted_on_the_second(candidate):
        seen.append(candidate)
        if len(seen) == 2:
            raise KeyboardInterrupt
        return _outcome(state="REVIEWING", run_id=run_id)

    lines = []
    interrupted_candidates = [_candidate("TE-0003"), _candidate("TE-0004")]
    with pytest.raises(KeyboardInterrupt):
        run_batch(
            interrupted_candidates,
            ledger,
            budget_usd=50.0,
            until=None,
            runner=_interrupted_on_the_second,
            rescan=lambda: interrupted_candidates,
            readiness_check=_ready,
            emit=lines.append,
        )
    assert _batch_row(ledger, _latest_batch_id(ledger))["status"] == "INFRASTRUCTURE"
    assert any("TE-0003" in line and "REVIEWING" in line for line in lines)


def _assert_closed(ledger, reason, expected):
    assert reason == expected
    batch_id = _latest_batch_id(ledger)
    row = _batch_row(ledger, batch_id)
    assert row["status"] == expected
    assert row["ended_at"] is not None


def test_every_stop_path_closes_the_batch_row_with_its_reason(ledger, repo_id):
    # One test, four of the five stop reasons — a parametrized test would
    # leave no bare node id for the host to check this witness against.
    # `INCOMPLETE` gets its own tests above, since it needs an in-flight
    # outcome rather than a bare readiness/budget/deadline condition.
    drained = run_batch(
        [],
        ledger,
        budget_usd=50.0,
        until=None,
        runner=FakeRunner([]),
        rescan=lambda: [],
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
        rescan=lambda: over_budget,
        readiness_check=_ready,
    )
    _assert_closed(ledger, budget, "BUDGET")

    deadline = datetime(2026, 9, 5, 6, 30)
    until_candidates = [_candidate("TE-0001")]
    until_reason = run_batch(
        until_candidates,
        ledger,
        budget_usd=50.0,
        until=deadline,
        runner=FakeRunner([]),
        clock=FakeClock([deadline]),
        rescan=lambda: until_candidates,
        readiness_check=_ready,
    )
    _assert_closed(ledger, until_reason, "UNTIL")

    infrastructure_candidates = [_candidate("TE-0001")]
    infrastructure = run_batch(
        infrastructure_candidates,
        ledger,
        budget_usd=50.0,
        until=None,
        runner=FakeRunner([]),
        rescan=lambda: infrastructure_candidates,
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
        rescan=lambda: [candidate],
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
        rescan=lambda: candidates,
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
        rescan=lambda: candidates,
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
        rescan=lambda: candidates,
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
            rescan=lambda: [],
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
            rescan=lambda: [_candidate("TE-0001")],
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
        rescan=lambda: candidates,
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
    candidates = [_candidate("TE-0001")]

    def _explodes(_candidate):
        raise RuntimeError("cell runtime would not start")

    reason = run_batch(
        candidates,
        ledger,
        budget_usd=50.0,
        until=None,
        runner=_explodes,
        rescan=lambda: candidates,
        readiness_check=_ready,
        emit=lines.append,
    )

    assert reason == "DRAINED"
    # One line, not three independent checks — a "starting" line also names
    # the spec, so three loose `any(...)` checks could pass on the wrong line.
    assert any(
        "TE-0001" in line
        and "RuntimeError" in line
        and "cell runtime would not start" in line
        for line in lines
    )


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
        # Tomorrow at 06:30 Pacific, computed rather than written: a literal
        # date makes `started_at < until_ts` below true only until the clock
        # passes it, and this test was red within a day of being written.
        deadline = (datetime.now() + timedelta(days=1)).replace(
            hour=6, minute=30, second=0, microsecond=0
        )
        expected = (
            deadline.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")
            if deadline.tzinfo
            else deadline.astimezone().astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")
        )
        run_batch(
            [],
            ledger,
            budget_usd=50.0,
            until=deadline,
            runner=FakeRunner([]),
            rescan=lambda: [],
            readiness_check=_ready,
        )
    finally:
        # monkeypatch restores the variable; only tzset re-reads it.
        monkeypatch.undo()
        time.tzset()

    row = _batch_row(ledger, _latest_batch_id(ledger))
    # The conversion, asserted against a value derived the same way rather than
    # against a literal: 06:30 Pacific is 13:30 UTC, and what this pins is the
    # seven-hour shift, not the date it happens on.
    assert row["until_ts"] == expected
    assert "T" not in row["until_ts"]
    assert row["until_ts"].endswith(" 13:30:00")
    assert row["started_at"] < row["until_ts"]


class PackagingRunner:
    """A runner that leaves the ledger the way a real task would: a run, a
    task at the candidate's own `spec_sha`, and `READY_FOR_REVIEW` — the
    shape `create_run` / `create_task` / `set_task_state` leave behind, with
    none of the cell work a real `run_one_cell` + PACKAGE does in between.
    `FakeRunner`'s own shape: records call order on `.calls`, so a test can
    see which candidate the loop chose to run, and when."""

    def __init__(self, ledger: Ledger, repo_id: int):
        self._ledger = ledger
        self._repo_id = repo_id
        self.calls: list[Candidate] = []

    def __call__(self, candidate: Candidate) -> CellOutcome:
        self.calls.append(candidate)
        run_id = self._ledger.create_run(self._repo_id, base_sha="a" * 40)
        task_id = self._ledger.create_task(
            run_id,
            spec_id=candidate.spec.id,
            spec_sha=candidate.spec_sha,
            branch=f"saffron/{candidate.spec.id}",
        )
        self._ledger.set_task_state(task_id, "READY_FOR_REVIEW")
        return CellOutcome(
            state="READY_FOR_REVIEW",
            task_id=task_id,
            run_id=run_id,
            task_dir=Path("/tmp/nonexistent-task-dir"),
        )


def test_a_child_refused_at_the_opening_scan_runs_after_its_parent_packages(
    tmp_path, ledger, repo_id
):
    """A spec refused at the night's opening scan because its `depends_on`
    parent had no task starts later that night, once the parent's task
    reaches `READY_FOR_REVIEW`: the loop rescans after every task, not only
    once the opening list runs out, and starts the first spec the *latest*
    rescan offers — here, right after the parent, ahead of an opening
    candidate of lower priority. A grandchild waiting on that child starts
    after the child, the same night. Uses the real `build_queue`, not a hand-
    built rescan, so this proves the admission and the loop together, not
    just the loop (backlog item b-d6bff7)."""
    directory = tmp_path / "specs"
    directory.mkdir()
    _write_spec(directory, "parent.md", id="TE-0001", priority=1, touches=["a/**"])
    _write_spec(
        directory,
        "child.md",
        id="TE-0002",
        priority=1,
        touches=["b/**"],
        depends_on=["TE-0001"],
    )
    _write_spec(
        directory,
        "grandchild.md",
        id="TE-0003",
        priority=1,
        touches=["c/**"],
        depends_on=["TE-0002"],
    )
    _write_spec(directory, "unrelated.md", id="TE-0004", priority=3, touches=["d/**"])

    opening, refusals = build_queue(directory, repo_id, ledger)
    # Today's whole defect, pinned: the child and grandchild are refused —
    # their parent has no task yet — and only the other two run without a rescan.
    assert [c.spec.id for c in opening] == ["TE-0001", "TE-0004"]
    assert {r.path.name for r in refusals} == {"child.md", "grandchild.md"}

    packaging = PackagingRunner(ledger, repo_id)
    lines: list[str] = []
    last_line_at_call: list[str] = []

    def runner(candidate):
        last_line_at_call.append(lines[-1] if lines else "")
        return packaging(candidate)

    reason = run_batch(
        opening,
        ledger,
        budget_usd=50.0,
        until=None,
        runner=runner,
        rescan=lambda: build_queue(directory, repo_id, ledger)[0],
        readiness_check=_ready,
        emit=lines.append,
    )

    assert reason == "DRAINED"
    order = [c.spec.id for c in packaging.calls]
    assert order == ["TE-0001", "TE-0002", "TE-0003", "TE-0004"]

    # The log names each task before it starts: the last line at each call.
    assert last_line_at_call == [f"{spec_id:<10} starting" for spec_id in order]


def test_a_spec_the_rescan_requeues_is_not_started_twice_in_one_night(ledger, repo_id):
    """After the first task, the latest rescan decides what runs, and a spec
    is started at most once a night. When a rescan offers again a spec whose
    task ended `RATE_LIMITED` earlier that night, the night does not start
    it a second time. An opening candidate the rescan no longer offers is
    not started at all."""
    first = _candidate("TE-0001")
    second = _candidate("TE-0002")
    run_id = _spend(ledger, repo_id, 1.0)
    runner = FakeRunner([_outcome(state="RATE_LIMITED", run_id=run_id)])

    # Offers TE-0001 again as a *new* Candidate (a resumed task_id) and drops
    # TE-0002 — comparing whole Candidates, not spec.id, would start it twice.
    requeued = Candidate(
        path=Path("TE-0001.md"),
        spec=Spec(id="TE-0001", title="t", type="chore", budget_usd=10.0),
        spec_sha="s" * 64,
        task_id=99,
    )
    assert requeued != first
    rescan_calls = {"n": 0}

    def rescan() -> list[Candidate]:
        rescan_calls["n"] += 1
        return [requeued] if rescan_calls["n"] == 1 else []

    reason = run_batch(
        [first, second],
        ledger,
        budget_usd=50.0,
        until=None,
        runner=runner,
        rescan=rescan,
        readiness_check=_ready,
    )

    assert reason == "DRAINED"
    assert runner.calls == [first]
    assert rescan_calls["n"] == 1


def test_a_stack_batch_hands_each_task_the_last_task_that_reached_review(
    ledger, repo_id
):
    """Predecessor is purely positional. It is the last candidate, in the
    given order, whose result was `READY_FOR_REVIEW`. Never the previous
    candidate, never sorted by id or priority, and never `ABORT_STATES`
    widened or narrowed."""
    from saffron.batch import run_stack_batch

    order = [
        _candidate("TE-7", priority=3),
        _candidate("TE-3", priority=3),
        _candidate("TE-9", priority=2),
        _candidate("TE-1", priority=2),
        _candidate("TE-5", priority=2),
        _candidate("TE-8", priority=2),
        _candidate("TE-2", priority=1),
        _candidate("TE-6", priority=1),
        _candidate("TE-10", priority=1),
        _candidate("TE-4", priority=1),
    ]
    run_te7, task_te7 = _spend_task(ledger, repo_id, 1.0)
    run_te8, task_te8 = _spend_task(ledger, repo_id, 1.0)
    run_te6, task_te6 = _spend_task(ledger, repo_id, 1.0)
    run_te4, task_te4 = _spend_task(ledger, repo_id, 1.0)
    results = {
        "TE-7": _outcome(state="READY_FOR_REVIEW", run_id=run_te7, task_id=task_te7),
        "TE-3": _outcome(state="EXHAUSTED", run_id=_spend(ledger, repo_id, 1.0)),
        "TE-9": _outcome(state="MERGE_FAILED", run_id=_spend(ledger, repo_id, 1.0)),
        "TE-1": _outcome(state="GATE_ERROR", run_id=_spend(ledger, repo_id, 1.0)),
        "TE-5": Refused(reason="nope"),
        "TE-8": _outcome(state="READY_FOR_REVIEW", run_id=run_te8, task_id=task_te8),
        "TE-2": RuntimeError("boom"),
        "TE-6": _outcome(state="READY_FOR_REVIEW", run_id=run_te6, task_id=task_te6),
        "TE-10": _outcome(state="PLAN_REJECTED", run_id=_spend(ledger, repo_id, 1.0)),
        "TE-4": _outcome(state="READY_FOR_REVIEW", run_id=run_te4, task_id=task_te4),
    }
    runner = FakeStackRunner(results)

    reason = run_stack_batch(
        order,
        ledger,
        budget_usd=100.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
    )

    assert reason == "DRAINED"
    assert runner.calls == [
        ("TE-7", None),
        ("TE-3", "TE-7"),
        ("TE-9", "TE-7"),
        ("TE-1", "TE-7"),
        ("TE-5", "TE-7"),
        ("TE-8", "TE-7"),
        ("TE-2", "TE-8"),
        ("TE-6", "TE-8"),
        ("TE-10", "TE-6"),
        ("TE-4", "TE-6"),
    ]


def test_a_stack_batch_refuses_every_descendant_of_a_task_that_missed_review(
    ledger, repo_id
):
    """A spec whose `depends_on` reaches, at any position, a spec that ran
    this batch and missed `READY_FOR_REVIEW` is refused before the runner
    ever sees it. It can reach one directly or through a refused spec. Its
    line names only the specs that ran and missed."""
    from saffron.batch import run_stack_batch

    order = [
        _candidate("TE-11", priority=3),
        _candidate("TE-12", priority=3, depends_on=["TE-11"]),
        _candidate("TE-14", priority=2),
        _candidate("TE-13", priority=2, depends_on=["TE-14", "TE-12"]),
        _candidate("TE-15", priority=2, depends_on=["TE-14", "TE-11"]),
        _candidate("TE-16", priority=1),
        _candidate("TE-17", priority=1),
        _candidate("TE-18", priority=1, depends_on=["TE-16", "TE-17"]),
        _candidate("TE-19", priority=1, depends_on=["TE-14"]),
        _candidate("TE-20", priority=1, depends_on=["TE-14", "TE-99"]),
    ]
    run_te14, task_te14 = _spend_task(ledger, repo_id, 1.0)
    run_te19, task_te19 = _spend_task(ledger, repo_id, 1.0)
    run_te20, task_te20 = _spend_task(ledger, repo_id, 1.0)
    results = {
        "TE-11": _outcome(state="MERGE_FAILED", run_id=_spend(ledger, repo_id, 1.0)),
        "TE-14": _outcome(state="READY_FOR_REVIEW", run_id=run_te14, task_id=task_te14),
        "TE-16": RuntimeError("boom"),
        "TE-17": Refused(reason="nope"),
        "TE-19": _outcome(state="READY_FOR_REVIEW", run_id=run_te19, task_id=task_te19),
        "TE-20": _outcome(state="READY_FOR_REVIEW", run_id=run_te20, task_id=task_te20),
    }
    runner = FakeStackRunner(results)
    lines: list[str] = []

    reason = run_stack_batch(
        order,
        ledger,
        budget_usd=100.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
        emit=lines.append,
    )

    assert reason == "DRAINED"
    assert runner.calls == [
        ("TE-11", None),
        ("TE-14", None),
        ("TE-16", "TE-14"),
        ("TE-17", "TE-14"),
        ("TE-19", "TE-14"),
        ("TE-20", "TE-19"),
    ]

    assert [line for line in lines if " refused " in line] == [
        f"{'TE-12':<10} refused  reaches TE-11",
        f"{'TE-13':<10} refused  reaches TE-11",
        f"{'TE-15':<10} refused  reaches TE-11",
        f"{'TE-18':<10} refused  reaches TE-16, TE-17",
    ]
    refused = {line.split()[0]: line for line in lines if "refused" in line}
    assert set(refused) == {"TE-12", "TE-13", "TE-15", "TE-18"}
    assert "TE-11" in refused["TE-12"]
    assert "TE-11" in refused["TE-13"]
    assert "TE-14" not in refused["TE-13"]
    assert "TE-12" not in refused["TE-13"], "names the miss, not the refused go-between"
    assert "TE-11" in refused["TE-15"] and "TE-14" not in refused["TE-15"]
    assert "TE-16" in refused["TE-18"] and "TE-17" in refused["TE-18"]
    assert not any("TE-20" in line for line in refused.values())


def test_a_stack_batch_counts_a_raise_as_an_abort(ledger, repo_id):
    """A stack batch still runs on `run_batch`'s own breaker: two raises in a
    row end the night `INFRASTRUCTURE` before a third candidate starts."""
    from saffron.batch import run_stack_batch

    order = [_candidate("TE-1"), _candidate("TE-2"), _candidate("TE-3")]
    runner = FakeStackRunner(
        {
            "TE-1": RuntimeError("boom"),
            "TE-2": RuntimeError("boom"),
            "TE-3": _outcome(
                state="READY_FOR_REVIEW", run_id=_spend(ledger, repo_id, 1.0)
            ),
        }
    )

    reason = run_stack_batch(
        order,
        ledger,
        budget_usd=100.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
    )

    assert reason == "INFRASTRUCTURE"
    assert runner.calls == [("TE-1", None), ("TE-2", None)]


def test_a_stack_batch_records_one_layer_for_each_task_that_reached_review(tmp_path):
    """One `stack_layers` row per layer that reached `READY_FOR_REVIEW`. The
    same three rows come back with no record behind the ledger. A second
    batch opens its own count. A plain `run_batch` writes none."""
    from saffron.batch import run_stack_batch
    from saffron.record.memory import MemoryRecord

    record = MemoryRecord()
    ledger = Ledger(tmp_path / "with-record.db", record=record)
    repo_id = ledger.upsert_repo("thermal-edge", "/o", "/m.git", policy_sha="p" * 64)
    script = _stack_script()
    order = [_candidate(spec_id) for spec_id, _ in script]
    runner = ScriptedRunner(ledger, repo_id, script)

    reason = run_stack_batch(
        order,
        ledger,
        budget_usd=100.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
    )

    assert reason == "DRAINED"
    batch_id = _latest_batch_id(ledger)
    rows = _stack_layers(ledger)
    assert len(rows) == 3

    def key(spec_id: str) -> str | None:
        return ledger.record_key(runner.task_ids[spec_id])

    def sha(spec_id: str) -> str:
        return runner.pushed_shas[spec_id]

    expected = [
        {
            "task_key": key("TE-7"),
            "batch_key": str(batch_id),
            "position": 1,
            "spec_id": "TE-7",
            "predecessor_key": None,
            "predecessor_head": None,
            "generation": 0,
        },
        {
            "task_key": key("TE-9"),
            "batch_key": str(batch_id),
            "position": 2,
            "spec_id": "TE-9",
            "predecessor_key": key("TE-7"),
            "predecessor_head": sha("TE-7"),
            "generation": 0,
        },
        {
            "task_key": key("TE-6"),
            "batch_key": str(batch_id),
            "position": 3,
            "spec_id": "TE-6",
            "predecessor_key": key("TE-9"),
            "predecessor_head": sha("TE-9"),
            "generation": 0,
        },
    ]
    assert rows == expected

    layered_keys = {row["task_key"] for row in rows}
    stack_fact_counts = {
        task_key: sum(1 for f in record.read(task_key) if f.kind == "stack_layer")
        for task_key in record.task_keys()
    }
    for task_key, count in stack_fact_counts.items():
        assert count == (1 if task_key in layered_keys else 0)
    assert sum(stack_fact_counts.values()) == 3

    # The same three rows, by the same rules, with no record behind the ledger.
    no_record = Ledger(tmp_path / "no-record.db")
    repo_id_2 = no_record.upsert_repo(
        "thermal-edge", "/o2", "/m2.git", policy_sha="p" * 64
    )
    script_2 = _stack_script()
    order_2 = [_candidate(spec_id) for spec_id, _ in script_2]
    runner_2 = ScriptedRunner(no_record, repo_id_2, script_2)

    reason_2 = run_stack_batch(
        order_2,
        no_record,
        budget_usd=100.0,
        until=None,
        runner=runner_2,
        readiness_check=_ready,
    )

    assert reason_2 == "DRAINED"
    batch_id_2 = _latest_batch_id(no_record)
    rows_2 = _stack_layers(no_record)

    def key_2(spec_id: str) -> str | None:
        return no_record.record_key(runner_2.task_ids[spec_id])

    def sha_2(spec_id: str) -> str:
        return runner_2.pushed_shas[spec_id]

    assert rows_2 == [
        {
            "task_key": key_2("TE-7"),
            "batch_key": str(batch_id_2),
            "position": 1,
            "spec_id": "TE-7",
            "predecessor_key": None,
            "predecessor_head": None,
            "generation": 0,
        },
        {
            "task_key": key_2("TE-9"),
            "batch_key": str(batch_id_2),
            "position": 2,
            "spec_id": "TE-9",
            "predecessor_key": key_2("TE-7"),
            "predecessor_head": sha_2("TE-7"),
            "generation": 0,
        },
        {
            "task_key": key_2("TE-6"),
            "batch_key": str(batch_id_2),
            "position": 3,
            "spec_id": "TE-6",
            "predecessor_key": key_2("TE-9"),
            "predecessor_head": sha_2("TE-9"),
            "generation": 0,
        },
    ]

    # A second stack batch on the same ledger opens its own position count
    # and its own predecessor chain, and leaves the first batch's rows alone.
    script_3 = _stack_script()
    order_3 = [_candidate(spec_id) for spec_id, _ in script_3]
    runner_3 = ScriptedRunner(no_record, repo_id_2, script_3)

    reason_3 = run_stack_batch(
        order_3,
        no_record,
        budget_usd=100.0,
        until=None,
        runner=runner_3,
        readiness_check=_ready,
    )

    assert reason_3 == "DRAINED"
    batch_id_3 = _latest_batch_id(no_record)
    assert batch_id_3 != batch_id_2
    rows_3 = _stack_layers(no_record, batch_id=batch_id_3)
    assert [row["position"] for row in rows_3] == [1, 2, 3]
    assert rows_3[0]["spec_id"] == "TE-7"
    assert rows_3[0]["predecessor_key"] is None
    assert _stack_layers(no_record, batch_id=batch_id_2) == rows_2

    # A plain `run_batch` writes no `stack_layers` row at all.
    plain = Ledger(tmp_path / "run-batch.db")
    repo_id_3 = plain.upsert_repo("thermal-edge", "/o3", "/m3.git", policy_sha="p" * 64)
    script_4 = _stack_script()
    order_4 = [_candidate(spec_id) for spec_id, _ in script_4]
    runner_4 = ScriptedRunner(plain, repo_id_3, script_4)

    reason_4 = run_batch(
        order_4,
        plain,
        budget_usd=100.0,
        until=None,
        runner=runner_4,
        rescan=lambda: order_4,
        readiness_check=_ready,
    )

    assert reason_4 == "DRAINED"
    assert _stack_layers(plain) == []


def test_the_stack_layers_fold_back_from_the_record_alone(tmp_path):
    """Folding the record alone rebuilds every `stack_layers` row. Each
    keeps a predecessor's key and head as first pushed. `fold_task` with
    no facts removes exactly the layer it names."""
    from saffron.batch import run_stack_batch
    from saffron.record.fold import fold
    from saffron.record.memory import MemoryRecord

    record = MemoryRecord()
    ledger = Ledger(tmp_path / "source.db", record=record)
    repo_id = ledger.upsert_repo("thermal-edge", "/o", "/m.git", policy_sha="p" * 64)
    script = _stack_script()
    order = [_candidate(spec_id) for spec_id, _ in script]
    runner = ScriptedRunner(ledger, repo_id, script)

    reason = run_stack_batch(
        order,
        ledger,
        budget_usd=100.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
    )
    assert reason == "DRAINED"

    run_te4 = ledger.create_run(repo_id, base_sha="a" * 40)
    task_te4 = ledger.create_task(
        run_te4, spec_id="TE-4", spec_sha="s" * 64, branch="saffron/TE-4"
    )
    ledger.record_push(task_te4, "TE-4-sha")
    ledger.set_task_package(
        task_te4,
        "READY_FOR_REVIEW",
        "saffron/TE-4",
        "TE-4-sha",
        "https://example.invalid/4",
    )
    ledger.record_stack_layer(
        task_te4,
        position=4,
        predecessor_task_id=runner.task_ids["TE-6"],
        generation=1,
    )

    source_rows = _stack_layers(ledger)
    assert [row["position"] for row in source_rows] == [1, 2, 3, 4]
    assert source_rows[3]["spec_id"] == "TE-4"
    assert source_rows[3]["generation"] == 1

    # Taken before the push below, and before either fold.
    te7_key = ledger.record_key(runner.task_ids["TE-7"])
    te7_sha = runner.pushed_shas["TE-7"]
    te9_key = ledger.record_key(runner.task_ids["TE-9"])
    assert te9_key is not None

    ledger.record_push(runner.task_ids["TE-7"], "TE-7-new-sha")

    fresh = Ledger(tmp_path / "fresh.db")
    other_repo = fresh.upsert_repo(
        "other-repo", "/other/o", "/other/m.git", policy_sha="q" * 64
    )
    other_run = fresh.create_run(other_repo, base_sha="b" * 40)
    fresh.create_task(
        other_run, spec_id="ZZ-0", spec_sha="z" * 64, branch="saffron/ZZ-0"
    )

    fold(record, fresh)

    fresh_rows = _stack_layers(fresh)
    assert fresh_rows == source_rows

    te9_row = next(row for row in fresh_rows if row["spec_id"] == "TE-9")
    assert te9_row["predecessor_key"] == te7_key
    assert te9_row["predecessor_head"] == te7_sha

    fold(record, ledger)
    assert _stack_layers(ledger) == source_rows

    fresh.fold_task(te9_key, [])
    remaining = {row["spec_id"] for row in _stack_layers(fresh)}
    assert remaining == {"TE-7", "TE-6", "TE-4"}


def test_a_stack_layer_naming_an_unknown_task_raises(tmp_path):
    """`record_stack_layer` raises `ValueError` for a task or a predecessor
    that names no row, like every other write method. A silent `NULL`
    predecessor would read as a stack's first layer."""
    from saffron.ledger import Ledger

    ledger = Ledger(tmp_path / "l.db")
    repo_id = ledger.upsert_repo("r", "/o", "/m.git", policy_sha="p" * 64)
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    task_id = ledger.create_task(
        run_id, spec_id="TE-1", spec_sha="s" * 64, branch="saffron/TE-1"
    )

    with pytest.raises(ValueError, match="no task 999"):
        ledger.record_stack_layer(
            999, position=1, predecessor_task_id=None, generation=0
        )
    with pytest.raises(ValueError, match="no predecessor task 998"):
        ledger.record_stack_layer(
            task_id, position=2, predecessor_task_id=998, generation=0
        )
    assert ledger._db.execute("SELECT COUNT(*) FROM stack_layers").fetchone()[0] == 0


def _package_runner(ledger, repo_id, log: list):
    """Criterion 4's ordinary runner: mints a real run, task and one 5.0
    attempt per call, packages it `READY_FOR_REVIEW`, and appends the
    spec id to `log`."""

    def runner(candidate, predecessor=None):
        log.append(candidate.spec.id)
        run_id = ledger.create_run(repo_id, base_sha="a" * 40)
        task_id = ledger.create_task(
            run_id,
            spec_id=candidate.spec.id,
            spec_sha="s" * 64,
            branch=f"saffron/{candidate.spec.id}",
        )
        attempt_id = ledger.open_attempt(task_id, phase="IMPLEMENT")
        ledger.close_attempt(
            attempt_id,
            session_id="sess",
            subtype="success",
            terminal_reason=None,
            num_turns=1,
            cost_usd_est=5.0,
        )
        ledger.set_task_package(
            task_id,
            "READY_FOR_REVIEW",
            f"saffron/{candidate.spec.id}",
            f"{candidate.spec.id}-sha",
            "https://example.invalid/1",
        )
        return _outcome(state="READY_FOR_REVIEW", run_id=run_id, task_id=task_id)

    return runner


def _logging_end_review(log: list):
    def end_review(batch_key, reserve_usd, specs):
        log.append((batch_key, reserve_usd, specs))

    return end_review


def test_a_stack_batch_holds_its_end_review_reserve_and_calls_it_once_the_loop_returns(
    ledger, repo_id
):
    """`reserve_usd` is held back before each task, and the batch row
    still records the whole budget. `end_review` runs once the loop
    returns, whatever the stop reason, but never after a raise."""
    from saffron.batch import run_stack_batch

    order = [
        _candidate("TE-1", budget_usd=5.0),
        _candidate("TE-2", budget_usd=5.0),
        _candidate("TE-3", budget_usd=5.0),
    ]
    specs = {c.spec.id: c.spec for c in order}

    # Batch 1: 20.0 less the 6.0 reserve leaves 14.0. TE-1 and TE-2 spend
    # it to 10.0, and TE-3's own 5.0 no longer fits.
    log1: list = []
    reason1 = run_stack_batch(
        order,
        ledger,
        20.0,
        None,
        _package_runner(ledger, repo_id, log1),
        readiness_check=_ready,
        reserve_usd=6.0,
        end_review=_logging_end_review(log1),
    )
    assert reason1 == "BUDGET"
    batch_id1 = _latest_batch_id(ledger)
    assert log1 == ["TE-1", "TE-2", (str(batch_id1), 6.0, specs)]
    assert _batch_row(ledger, batch_id1)["status"] == "BUDGET"
    assert _batch_row(ledger, batch_id1)["budget_usd"] == 20.0

    # Batch 2: 30.0 less the reserve leaves 24.0, enough for all three.
    log2: list = []
    reason2 = run_stack_batch(
        order,
        ledger,
        30.0,
        None,
        _package_runner(ledger, repo_id, log2),
        readiness_check=_ready,
        reserve_usd=6.0,
        end_review=_logging_end_review(log2),
    )
    assert reason2 == "DRAINED"
    batch_id2 = _latest_batch_id(ledger)
    assert log2 == ["TE-1", "TE-2", "TE-3", (str(batch_id2), 6.0, specs)]
    assert _batch_row(ledger, batch_id2)["status"] == "DRAINED"
    assert _batch_row(ledger, batch_id2)["budget_usd"] == 30.0

    # Batch 3: the runner raises on every call, so the breaker fires after
    # two consecutive aborts and TE-3 is never reached.
    log3: list = []

    def _raising_runner(candidate, predecessor=None):
        log3.append(candidate.spec.id)
        raise RuntimeError("cell died mid-repair")

    reason3 = run_stack_batch(
        order,
        ledger,
        30.0,
        None,
        _raising_runner,
        readiness_check=_ready,
        reserve_usd=6.0,
        end_review=_logging_end_review(log3),
    )
    assert reason3 == "INFRASTRUCTURE"
    batch_id3 = _latest_batch_id(ledger)
    assert log3 == ["TE-1", "TE-2", (str(batch_id3), 6.0, specs)]
    assert _batch_row(ledger, batch_id3)["status"] == "INFRASTRUCTURE"
    assert _batch_row(ledger, batch_id3)["budget_usd"] == 30.0

    # Batch 4: the readiness check itself raises before any candidate.
    # The raise leaves `run_stack_batch`, and `end_review` never runs.
    log4: list = []

    def _raising_readiness():
        raise RuntimeError("token expired")

    with pytest.raises(RuntimeError, match="token expired"):
        run_stack_batch(
            order,
            ledger,
            30.0,
            None,
            _package_runner(ledger, repo_id, log4),
            readiness_check=_raising_readiness,
            reserve_usd=6.0,
            end_review=_logging_end_review(log4),
        )
    assert log4 == []


def test_a_stack_batch_waits_out_a_rate_limit_and_runs_the_same_spec_again(
    ledger, repo_id, monkeypatch
):
    """SA-0148: a `RATE_LIMITED` task waits out its own window, adds no
    layer, and runs again on the same predecessor. Driven under a naive
    clock and an aware one at a fixed offset of minus seven hours."""
    from saffron.batch import run_stack_batch

    _raise_on_real_sleep(monkeypatch)
    starts = [
        datetime(2030, 1, 1, 2, 0),
        datetime(2030, 1, 1, 2, 0, tzinfo=timezone(timedelta(hours=-7))),
    ]
    for start in starts:
        order = [
            _candidate("TE-1"),
            _candidate("TE-2"),
            _candidate("TE-3", depends_on=["TE-2"]),
        ]
        clock = AdvancingClock(start)
        runner = RateLimitScript(
            ledger,
            repo_id,
            clock,
            {
                "TE-1": [{"state": "READY_FOR_REVIEW"}],
                "TE-2": [
                    {"state": "RATE_LIMITED", "offset": 3900},
                    {"state": "READY_FOR_REVIEW"},
                ],
                "TE-3": [{"state": "READY_FOR_REVIEW"}],
            },
        )
        lines: list[str] = []

        reason = run_stack_batch(
            order,
            ledger,
            budget_usd=100.0,
            until=start + timedelta(hours=4),
            runner=runner,
            readiness_check=_ready,
            clock=clock,
            sleep=clock.sleep,
            emit=lines.append,
        )

        assert reason == "DRAINED"
        assert runner.calls == [
            ("TE-1", None),
            ("TE-2", "TE-1"),
            ("TE-2", "TE-1"),
            ("TE-3", "TE-2"),
        ]
        assert clock.sleeps == [3900.0]
        batch_id = _latest_batch_id(ledger)
        assert ledger.batch_spend(batch_id) == 4.0
        rate_lines = [
            line
            for line in lines
            if line.startswith(f"{'TE-2':<10}") and "rate limited" in line
        ]
        assert len(rate_lines) == 1
        assert "03:05" in rate_lines[0]
        assert not any(" refused " in line for line in lines)


def test_a_rate_limit_in_a_stack_batch_neither_counts_toward_the_breaker_nor_resets_it(
    ledger, repo_id, monkeypatch
):
    """A `RATE_LIMITED` result leaves `_drive`'s own breaker count exactly
    where it was. A second abort right after it can still fire the breaker.
    Plain `run_batch` keeps its old breaker treatment for the same rate
    limit instead."""
    from saffron.batch import run_stack_batch

    _raise_on_real_sleep(monkeypatch)
    order = [
        _candidate("TE-1"),
        _candidate("TE-2"),
        _candidate("TE-3", depends_on=["TE-2"]),
    ]
    clock = AdvancingClock(datetime(2030, 1, 1, 2, 0))
    runner = RateLimitScript(
        ledger,
        repo_id,
        clock,
        {
            "TE-1": [{"state": "GATE_ERROR"}],
            "TE-2": [
                {"state": "RATE_LIMITED", "offset": 60},
                {"state": "GATE_ERROR"},
            ],
            "TE-3": [{"state": "READY_FOR_REVIEW"}],
        },
    )
    lines: list[str] = []

    reason = run_stack_batch(
        order,
        ledger,
        budget_usd=100.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
        clock=clock,
        sleep=clock.sleep,
        emit=lines.append,
    )

    assert reason == "INFRASTRUCTURE"
    assert runner.calls == [
        ("TE-1", None),
        ("TE-2", None),
        ("TE-2", None),
    ]
    refused = [line for line in lines if " refused " in line]
    assert len(refused) == 1
    assert refused[0].startswith(f"{'TE-3':<10}")

    order2 = [_candidate("TE-4"), _candidate("TE-5")]
    clock2 = AdvancingClock(datetime(2030, 1, 1, 2, 0))
    runner2 = RateLimitScript(
        ledger,
        repo_id,
        clock2,
        {
            "TE-4": [
                {"state": "RATE_LIMITED", "offset": 60},
                {"state": "RATE_LIMITED", "offset": 60},
                {"state": "READY_FOR_REVIEW"},
            ],
            "TE-5": [{"state": "READY_FOR_REVIEW"}],
        },
    )

    reason2 = run_stack_batch(
        order2,
        ledger,
        budget_usd=100.0,
        until=None,
        runner=runner2,
        readiness_check=_ready,
        clock=clock2,
        sleep=clock2.sleep,
    )

    assert reason2 == "DRAINED"
    assert runner2.calls == [
        ("TE-4", None),
        ("TE-4", None),
        ("TE-4", None),
        ("TE-5", "TE-4"),
    ]

    candidates3 = [_candidate("TE-1"), _candidate("TE-2")]
    run_one = _spend(ledger, repo_id, 1.0)
    run_two = _spend(ledger, repo_id, 1.0)
    runner3 = FakeRunner(
        [
            _outcome(state="GATE_ERROR", run_id=run_one),
            _outcome(state="RATE_LIMITED", run_id=run_two),
        ]
    )

    reason3 = run_batch(
        candidates3,
        ledger,
        budget_usd=100.0,
        until=None,
        runner=runner3,
        rescan=lambda: candidates3,
        readiness_check=_ready,
    )

    assert reason3 == "INFRASTRUCTURE"
    assert runner3.calls == candidates3


def test_a_stack_batch_stops_at_until_rather_than_wait_past_it(
    ledger, repo_id, monkeypatch
):
    """The wait and the distance to `until` both come from one clock read
    taken after the task returns. A wait that would end at or past `until`
    stops the batch `UNTIL` at once, with no sleep and no line."""
    from saffron.batch import run_stack_batch

    _raise_on_real_sleep(monkeypatch)
    start = datetime(2030, 1, 1, 2, 0)

    def _run(*, until_hours, steps, budget=100.0, spec_budget=10.0):
        clock = AdvancingClock(start)
        until = (
            start + timedelta(hours=until_hours) if until_hours is not None else None
        )
        runner = RateLimitScript(ledger, repo_id, clock, {"TE-1": steps})
        lines: list[str] = []
        reason = run_stack_batch(
            [_candidate("TE-1", budget_usd=spec_budget)],
            ledger,
            budget,
            until,
            runner,
            readiness_check=_ready,
            clock=clock,
            sleep=clock.sleep,
            emit=lines.append,
        )
        return reason, runner, clock, lines

    reason, runner, clock, lines = _run(
        until_hours=1,
        steps=[
            {"state": "RATE_LIMITED", "offset": 3 * 3600},
            {"state": "READY_FOR_REVIEW"},
        ],
    )
    assert reason == "UNTIL"
    assert len(runner.calls) == 1
    assert clock.sleeps == []
    assert not any("rate limited" in line for line in lines)
    assert ledger.batch_spend(_latest_batch_id(ledger)) == 1.0

    reason, runner, clock, _ = _run(
        until_hours=1,
        steps=[
            {"state": "RATE_LIMITED", "offset": 3600},
            {"state": "READY_FOR_REVIEW"},
        ],
    )
    assert reason == "UNTIL"
    assert len(runner.calls) == 1
    assert clock.sleeps == []

    reason, runner, clock, _ = _run(
        until_hours=20 / 60,
        steps=[
            {"state": "RATE_LIMITED", "resets_at": None},
            {"state": "READY_FOR_REVIEW"},
        ],
    )
    assert reason == "UNTIL"
    assert len(runner.calls) == 1
    assert clock.sleeps == []

    reason, runner, clock, _ = _run(
        until_hours=0.5,
        steps=[
            {"state": "RATE_LIMITED", "advance": 3600, "offset": 3 * 3600},
            {"state": "READY_FOR_REVIEW"},
        ],
    )
    assert reason == "UNTIL"
    assert len(runner.calls) == 1
    assert clock.sleeps == []

    reason, runner, clock, _ = _run(
        until_hours=2,
        steps=[
            {"state": "RATE_LIMITED", "resets_at": None},
            {"state": "READY_FOR_REVIEW"},
        ],
    )
    assert reason == "DRAINED"
    assert len(runner.calls) == 2
    assert clock.sleeps == [3600.0]

    reason, runner, clock, _ = _run(
        until_hours=None,
        steps=[
            {"state": "RATE_LIMITED", "advance": 3600, "offset": 60},
            {"state": "READY_FOR_REVIEW"},
        ],
    )
    assert reason == "DRAINED"
    assert len(runner.calls) == 2
    assert clock.sleeps == [60.0]

    reason, runner, clock, _ = _run(
        until_hours=2,
        steps=[
            {"state": "RATE_LIMITED", "advance": 3600, "offset": 90 * 60},
            {"state": "READY_FOR_REVIEW"},
        ],
    )
    assert reason == "UNTIL"
    assert len(runner.calls) == 1
    assert clock.sleeps == []

    reason, runner, clock, _ = _run(
        until_hours=None,
        budget=15.0,
        spec_budget=10.0,
        steps=[
            {"state": "RATE_LIMITED", "cost": 6.0, "offset": 60},
            {"state": "READY_FOR_REVIEW"},
        ],
    )
    assert reason == "BUDGET"
    assert len(runner.calls) == 1


def test_a_stack_batch_waits_an_hour_when_it_cannot_read_the_reset_time(
    ledger, repo_id, monkeypatch
):
    """`resets_at` values `_wait_out_rate_limit` cannot read all wait an
    hour. Only a value strictly after now and no more than six hours on is
    read, and waited in full."""
    from saffron.batch import run_stack_batch

    _raise_on_real_sleep(monkeypatch)
    start = datetime(2030, 1, 1, 2, 0)
    clock = AdvancingClock(start)
    steps = (
        [{"state": "RATE_LIMITED", "resets_at": None}]
        + [{"state": "RATE_LIMITED", "resets_at": 10**20}]
        + [{"state": "RATE_LIMITED", "resets_at": 10**12}]
        + [{"state": "RATE_LIMITED", "offset": 0}]
        + [{"state": "RATE_LIMITED", "offset": -60}]
        + [{"state": "RATE_LIMITED", "offset": 7 * 3600}]
        + [{"state": "RATE_LIMITED", "resets_at": 10**400}]
        + [{"state": "RATE_LIMITED", "resets_at": -(10**400)}]
        + [{"state": "RATE_LIMITED", "offset": 6 * 3600}]
        + [{"state": "READY_FOR_REVIEW"}]
    )
    runner = RateLimitScript(ledger, repo_id, clock, {"TE-1": steps})
    lines: list[str] = []

    reason = run_stack_batch(
        [_candidate("TE-1")],
        ledger,
        budget_usd=100.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
        clock=clock,
        sleep=clock.sleep,
        emit=lines.append,
    )

    assert reason == "DRAINED"
    assert runner.calls == [("TE-1", None)] * 10
    assert clock.sleeps == [3600.0] * 8 + [21600.0]
    rate_lines = [
        line
        for line in lines
        if line.startswith(f"{'TE-1':<10}") and "rate limited" in line
    ]
    assert len(rate_lines) == 9


def _review_session(
    findings=(),
    *,
    cost=0.5,
    error=None,
    resets_at=None,
    fenced=True,
    session_id=None,
    num_turns=0,
):
    """A `SpecReviewSession` fixture for the review witnesses below. Imports
    lazily, so a reverted `saffron/spec_review.py` fails a calling test at
    call time rather than failing collection for the whole file."""
    import json

    from saffron.spec_review import SpecReviewSession

    if fenced:
        body = json.dumps({"findings": list(findings)})
        text = f"```json\n{body}\n```"
    else:
        text = "spec review text with no fenced block"
    return SpecReviewSession(
        text=text,
        cost_usd=cost,
        error=error,
        resets_at=resets_at,
        session_id=session_id,
        num_turns=num_turns,
    )


def _clean_review(**kwargs):
    return _review_session([], **kwargs)


def _blocker(fixes=None) -> dict:
    return {
        "severity": "blocker",
        "claim": "c",
        "criterion": "1",
        "file": "f",
        "line": 1,
        "fixes": fixes,
    }


def _concern(fixes) -> dict:
    return {
        "severity": "concern",
        "claim": "c",
        "criterion": "1",
        "file": "f",
        "line": 1,
        "fixes": fixes,
    }


def _note() -> dict:
    return {"severity": "note", "claim": "c", "criterion": "1", "file": "f", "line": 1}


class ReviewScript:
    """A `review` double keyed by spec id. Each call pops the next queued
    session for that spec id and records `(spec id, predecessor spec id or
    None)`, in order. It is the one arrangement of `run_stack_batch`'s review
    witnesses."""

    def __init__(self, sessions):
        self._sessions = {spec_id: list(queue) for spec_id, queue in sessions.items()}
        self.calls: list[tuple[str, str | None]] = []

    def __call__(self, candidate: Candidate, predecessor: Candidate | None):
        self.calls.append(
            (candidate.spec.id, predecessor.spec.id if predecessor else None)
        )
        return self._sessions[candidate.spec.id].pop(0)


class MintDouble:
    """The `mint` double shared by every `review`-driven witness. Each call
    records the spec id, in order, before raising for a spec id named in
    `raise_on`. Otherwise it mints a run and a task for the candidate, keeps
    the task id by spec id in `tasks`, and returns it."""

    def __init__(self, ledger: Ledger, repo_id: int, raise_on=frozenset()):
        self._ledger = ledger
        self._repo_id = repo_id
        self._raise_on = frozenset(raise_on)
        self.calls: list[str] = []
        self.tasks: dict[str, int] = {}

    def __call__(self, candidate: Candidate) -> int:
        self.calls.append(candidate.spec.id)
        if candidate.spec.id in self._raise_on:
            raise RuntimeError(f"mint failed for {candidate.spec.id}")
        run_id = self._ledger.create_run(self._repo_id, base_sha="a" * 40)
        task_id = self._ledger.create_task(
            run_id,
            spec_id=candidate.spec.id,
            spec_sha=candidate.spec_sha,
            branch=f"saffron/{candidate.spec.id}",
        )
        self.tasks[candidate.spec.id] = task_id
        return task_id


class ReviewDouble:
    """The `review` double for the mint-and-review witnesses. Records
    `(spec id, length of the mint log at the moment of the call)`, and pops
    the next scripted session or exception for that spec id, raising
    `AssertionError` for a spec id the table names nothing for. It also
    records the batch that holds the run of the spec's newest task.
    `TE-5`'s own spend is captured at its second call. `TE-2` gets an
    unrelated $8 run and task, as an attended `saffron cell` would leave
    behind."""

    def __init__(self, ledger: Ledger, repo_id: int, mint_log: list[str], table):
        self._ledger = ledger
        self._repo_id = repo_id
        self._mint_log = mint_log
        self._table = {spec_id: list(queue) for spec_id, queue in table.items()}
        self.calls: list[tuple[str, int]] = []
        self.batches_at_call: list[int | None] = []
        self.te5_second_call_spend: float | None = None

    def __call__(self, candidate: Candidate, predecessor: Candidate | None):
        spec_id = candidate.spec.id
        self.calls.append((spec_id, len(self._mint_log)))
        queue = self._table.get(spec_id)
        if not queue:
            raise AssertionError(f"no review scripted for {spec_id}")
        entry = queue.pop(0)

        newest = self._ledger.tasks_by_spec_id(self._repo_id, spec_id)[-1]["task_id"]
        run_id = self._ledger.task_run(newest)
        batch_row = self._ledger._db.execute(
            "SELECT batch_id FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        self.batches_at_call.append(batch_row["batch_id"])

        if spec_id == "TE-5" and not queue:
            self.te5_second_call_spend = self._ledger.batch_spend(batch_row["batch_id"])

        if spec_id == "TE-2":
            unrelated_run = self._ledger.create_run(self._repo_id, base_sha="b" * 40)
            unrelated_task = self._ledger.create_task(
                unrelated_run,
                spec_id="TE-2-unrelated",
                spec_sha="u" * 64,
                branch="saffron/TE-2-unrelated",
            )
            attempt_id = self._ledger.open_attempt(unrelated_task, phase="IMPLEMENT")
            self._ledger.close_attempt(
                attempt_id,
                session_id=None,
                subtype="success",
                terminal_reason=None,
                num_turns=1,
                cost_usd_est=8.0,
            )

        if isinstance(entry, Exception):
            raise entry
        return entry


class RunnerDouble:
    """The `runner` double for the mint-and-review witnesses. Records
    `(spec id, candidate.task_id)`. Mints its own run and task with one
    closed $1 attempt, as `SA-0149`'s own runner double does. Returns the
    next scripted state for the spec, wrapped in a `CellOutcome`."""

    def __init__(self, ledger: Ledger, repo_id: int, table):
        self._ledger = ledger
        self._repo_id = repo_id
        self._table = {spec_id: list(queue) for spec_id, queue in table.items()}
        self.calls: list[tuple[str, int | None]] = []

    def __call__(self, candidate: Candidate, predecessor: Candidate | None):
        self.calls.append((candidate.spec.id, candidate.task_id))
        run_id = self._ledger.create_run(self._repo_id, base_sha="a" * 40)
        task_id = self._ledger.create_task(
            run_id,
            spec_id=candidate.spec.id,
            spec_sha=candidate.spec_sha,
            branch=f"saffron/{candidate.spec.id}-run",
        )
        attempt_id = self._ledger.open_attempt(task_id, phase="IMPLEMENT")
        self._ledger.close_attempt(
            attempt_id,
            session_id=None,
            subtype="success",
            terminal_reason=None,
            num_turns=1,
            cost_usd_est=1.0,
        )
        state = self._table[candidate.spec.id].pop(0)
        outcome = _outcome(state=state, run_id=run_id, task_id=task_id)
        if state == "RATE_LIMITED":
            outcome = dataclasses.replace(outcome, resets_at=_soon())
        return outcome


def _spec_reviews(ledger: Ledger) -> list[dict]:
    """Every `spec_reviews` row, ordered by `(task_key, n)`, as plain dicts
    so an assertion can compare them by value."""
    rows = ledger._db.execute(
        "SELECT * FROM spec_reviews ORDER BY task_key, n"
    ).fetchall()
    return [dict(row) for row in rows]


def _mint_and_review_arrangement(ledger: Ledger, repo_id: int):
    """The one arrangement shared by every mint-and-review witness. The
    ten-spec order comes from the spec's own table, with an older `TE-7`
    task left `GATE_ERROR` in an earlier batch. Returns `(order, older_task,
    earlier_batch, mint, reviews, runner)`, the doubles that drive the rest."""
    earlier_batch = ledger.create_batch(10.0)
    older_run = ledger.create_run(repo_id, base_sha="a" * 40, batch_id=earlier_batch)
    older_task = ledger.create_task(
        older_run, spec_id="TE-7", spec_sha="s" * 64, branch="saffron/TE-7"
    )
    older_attempt = ledger.open_attempt(older_task, phase="IMPLEMENT")
    ledger.close_attempt(
        older_attempt,
        session_id=None,
        subtype="success",
        terminal_reason=None,
        num_turns=1,
        cost_usd_est=2.0,
    )
    ledger.set_task_state(older_task, "GATE_ERROR")
    ledger.close_batch(earlier_batch, "DRAINED")

    order = [
        _candidate("TE-1"),
        _candidate("TE-2"),
        _candidate("TE-3", depends_on=["TE-2"]),
        _candidate("TE-4"),
        _candidate("TE-5"),
        _candidate("TE-6"),
        dataclasses.replace(_candidate("TE-7"), task_id=older_task),
        _candidate("TE-9"),
        _candidate("TE-80"),
        _candidate("TE-81"),
    ]

    mint = MintDouble(ledger, repo_id, raise_on={"TE-80"})
    reviews = ReviewDouble(
        ledger,
        repo_id,
        mint.calls,
        {
            "TE-1": [_review_session([], cost=0.5, session_id="s-1", num_turns=7)],
            "TE-2": [_review_session([_blocker("scope")], cost=0.25)],
            "TE-4": [_review_session([], error="cell died", cost=0.125)],
            "TE-5": [
                _review_session([], fenced=False, resets_at=_soon(), cost=0.0625),
                _review_session([], cost=0.03125),
            ],
            "TE-6": [RuntimeError("critic cell would not start")],
            "TE-7": [_review_session([], cost=0.75)],
            "TE-9": [_review_session([], fenced=False, cost=0.015625)],
        },
    )
    runner = RunnerDouble(
        ledger,
        repo_id,
        {
            "TE-1": ["READY_FOR_REVIEW"],
            "TE-5": ["RATE_LIMITED", "READY_FOR_REVIEW"],
            "TE-7": ["RATE_LIMITED", "READY_FOR_REVIEW"],
        },
    )
    return order, older_task, earlier_batch, mint, reviews, runner


def test_a_stack_batch_mints_each_reviewed_specs_task_before_its_first_review(
    ledger, repo_id
):
    """`mint` runs once per spec, before that spec's own first review,
    whatever the candidate's `task_id` names. It never runs for a spec
    refused before its review reaches it. It never runs twice for the same
    spec, and never on the older task a re-queued candidate carries. A
    `mint` that raises counts as an abort, as a runner's raise does, and its
    spec is never reviewed."""
    from saffron.batch import run_stack_batch

    order, older_task, _earlier_batch, mint, reviews, runner = (
        _mint_and_review_arrangement(ledger, repo_id)
    )
    lines: list[str] = []

    reason = run_stack_batch(
        order,
        ledger,
        budget_usd=100.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
        emit=lines.append,
        review=reviews,
        mint=mint,
        sleep=lambda seconds: None,
    )

    assert reason == "INFRASTRUCTURE"
    assert mint.calls == [
        "TE-1",
        "TE-2",
        "TE-4",
        "TE-5",
        "TE-6",
        "TE-7",
        "TE-9",
        "TE-80",
    ]
    assert reviews.calls == [
        ("TE-1", 1),
        ("TE-2", 2),
        ("TE-4", 3),
        ("TE-5", 4),
        ("TE-5", 4),
        ("TE-6", 5),
        ("TE-7", 6),
        ("TE-9", 7),
    ]
    raised_te80 = [
        line
        for line in lines
        if line.startswith(f"{'TE-80':<10}") and "raised RuntimeError" in line
    ]
    assert len(raised_te80) == 1

    assert runner.calls == [
        ("TE-1", mint.tasks["TE-1"]),
        ("TE-5", mint.tasks["TE-5"]),
        ("TE-5", mint.tasks["TE-5"]),
        ("TE-7", mint.tasks["TE-7"]),
        ("TE-7", mint.tasks["TE-7"]),
    ]
    assert mint.tasks["TE-7"] != older_task

    # A second batch on the same ledger mints TE-1 a fresh task.
    mint2 = MintDouble(ledger, repo_id)
    reviews2 = ReviewDouble(
        ledger, repo_id, mint2.calls, {"TE-1": [_review_session([], cost=0.1)]}
    )
    runner2 = RunnerDouble(ledger, repo_id, {"TE-1": ["READY_FOR_REVIEW"]})

    reason2 = run_stack_batch(
        [_candidate("TE-1")],
        ledger,
        budget_usd=100.0,
        until=None,
        runner=runner2,
        readiness_check=_ready,
        review=reviews2,
        mint=mint2,
    )

    assert reason2 == "DRAINED"
    assert mint2.calls == ["TE-1"]
    rows = [
        row
        for row in _spec_reviews(ledger)
        if row["task_key"] == ledger.record_key(mint2.tasks["TE-1"])
    ]
    assert [row["n"] for row in rows] == [1]

    batches_before = ledger._db.execute("SELECT COUNT(*) AS n FROM batches").fetchone()[
        "n"
    ]
    with pytest.raises(ValueError):
        run_stack_batch(
            [_candidate("TE-90")],
            ledger,
            budget_usd=100.0,
            until=None,
            runner=runner2,
            readiness_check=_ready,
            review=reviews2,
        )
    batches_after = ledger._db.execute("SELECT COUNT(*) AS n FROM batches").fetchone()[
        "n"
    ]
    assert batches_after == batches_before

    mint3 = MintDouble(ledger, repo_id, raise_on={"TE-80"})
    order3 = [_candidate("TE-80"), _candidate("TE-82", depends_on=["TE-80"])]
    run_stack_batch(
        order3,
        ledger,
        100.0,
        None,
        runner2,
        readiness_check=_ready,
        review=reviews2,
        mint=mint3,
    )
    assert mint3.calls == ["TE-80"]


def test_each_spec_review_is_a_fact_on_its_specs_minted_task(tmp_path):
    """Each reviewed task's `spec_review` facts, attempts and state match its
    own review's route. The older task `TE-7`'s candidate carries keeps its
    own state and its one attempt, and gets no `spec_review` fact at all."""
    from saffron.batch import run_stack_batch
    from saffron.record.memory import MemoryRecord

    record = MemoryRecord()
    ledger = Ledger(tmp_path / "reviews.db", record=record)
    repo_id = ledger.upsert_repo("thermal-edge", "/o", "/m.git", policy_sha="p" * 64)
    order, older_task, _earlier_batch, mint, reviews, runner = (
        _mint_and_review_arrangement(ledger, repo_id)
    )

    run_stack_batch(
        order,
        ledger,
        budget_usd=100.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
        review=reviews,
        mint=mint,
        sleep=lambda seconds: None,
    )

    def facts(task_id: int) -> list:
        key = ledger.record_key(task_id)
        assert key is not None
        return [f for f in record.read(key) if f.kind == "spec_review"]

    def state(task_id: int) -> str:
        row = ledger._db.execute(
            "SELECT state FROM tasks WHERE task_id = ?", (task_id,)
        ).fetchone()
        return row["state"]

    te1 = mint.tasks["TE-1"]
    te1_facts = facts(te1)
    assert [f.payload["n"] for f in te1_facts] == [1]
    assert te1_facts[0].payload["route"] == "run"
    assert te1_facts[0].payload["error"] is None
    te1_attempts = ledger.attempts(te1)
    assert len(te1_attempts) == 1
    assert te1_attempts[0]["phase"] == "SPEC_REVIEW"
    assert te1_attempts[0]["cost_usd_est"] == 0.5
    assert te1_attempts[0]["subtype"] == "success"
    assert te1_attempts[0]["session_id"] == "s-1"
    assert te1_attempts[0]["num_turns"] == 7
    assert state(te1) == "QUEUED"

    te2 = mint.tasks["TE-2"]
    te2_facts = facts(te2)
    assert len(te2_facts) == 1 and te2_facts[0].payload["n"] == 1
    assert te2_facts[0].payload["route"] == "escalate"
    block = te2_facts[0].payload["block"]
    assert block is not None
    assert te2_facts[0].payload["block_sha256"] == hash_artifact(block)
    te2_attempts = ledger.attempts(te2)
    assert len(te2_attempts) == 1
    assert te2_attempts[0]["cost_usd_est"] == 0.25
    assert te2_attempts[0]["subtype"] == "success"
    assert te2_attempts[0]["session_id"] is None
    assert te2_attempts[0]["num_turns"] == 0
    assert state(te2) == "SPEC_WITHHELD"

    te4 = mint.tasks["TE-4"]
    te4_facts = facts(te4)
    assert len(te4_facts) == 1
    assert te4_facts[0].payload["route"] == "error"
    assert te4_facts[0].payload["error"] == "cell died"
    assert te4_facts[0].payload["block"] == '{"findings": []}'
    te4_attempts = ledger.attempts(te4)
    assert len(te4_attempts) == 1
    assert te4_attempts[0]["cost_usd_est"] == 0.125
    assert te4_attempts[0]["subtype"] == "error"
    assert state(te4) == "GATE_ERROR"

    te5 = mint.tasks["TE-5"]
    te5_facts = facts(te5)
    assert [f.payload["n"] for f in te5_facts] == [1, 2]
    assert [f.payload["route"] for f in te5_facts] == ["wait", "run"]
    te5_attempts = ledger.attempts(te5)
    assert [a["cost_usd_est"] for a in te5_attempts] == [0.0625, 0.03125]
    assert [a["subtype"] for a in te5_attempts] == ["success", "success"]
    assert state(te5) == "RATE_LIMITED"

    te6 = mint.tasks["TE-6"]
    te6_facts = facts(te6)
    assert len(te6_facts) == 1 and te6_facts[0].payload["n"] == 1
    assert te6_facts[0].payload["route"] == "error"
    assert te6_facts[0].payload["block"] is None
    assert te6_facts[0].payload["block_sha256"] is None
    assert te6_facts[0].payload["error"] == "RuntimeError: critic cell would not start"
    assert ledger.attempts(te6) == []
    assert state(te6) == "GATE_ERROR"

    te7 = mint.tasks["TE-7"]
    te7_facts = facts(te7)
    assert len(te7_facts) == 1
    assert te7_facts[0].payload["route"] == "run"
    assert te7_facts[0].payload["error"] is None
    te7_attempts = ledger.attempts(te7)
    assert len(te7_attempts) == 1 and te7_attempts[0]["cost_usd_est"] == 0.75
    assert state(te7) == "QUEUED"

    assert state(older_task) == "GATE_ERROR"
    assert len(ledger.attempts(older_task)) == 1
    assert facts(older_task) == []

    te9 = mint.tasks["TE-9"]
    te9_facts = facts(te9)
    assert len(te9_facts) == 1
    assert te9_facts[0].payload["route"] == "error"
    assert te9_facts[0].payload["block"] is None
    te9_attempts = ledger.attempts(te9)
    assert len(te9_attempts) == 1
    assert te9_attempts[0]["cost_usd_est"] == 0.015625
    assert te9_attempts[0]["subtype"] == "success"
    assert state(te9) == "GATE_ERROR"


def test_a_stack_batch_counts_each_spec_review_once_in_its_spend(ledger, repo_id):
    """`ledger.batch_spend` counts each review's own cost once, plus every
    runner call, and nothing minted outside the batch it reviewed."""
    from saffron.batch import run_stack_batch

    order, older_task, earlier_batch, mint, reviews, runner = (
        _mint_and_review_arrangement(ledger, repo_id)
    )

    reason = run_stack_batch(
        order,
        ledger,
        budget_usd=100.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
        review=reviews,
        mint=mint,
        sleep=lambda seconds: None,
    )

    assert reason == "INFRASTRUCTURE"
    batch_id = ledger.latest_batch_id()
    assert batch_id != earlier_batch
    assert ledger.batch_spend(batch_id) == 6.734375
    assert ledger.batch_spend(earlier_batch) == 2.0
    assert reviews.te5_second_call_spend == 1.9375
    assert set(reviews.batches_at_call) == {batch_id}

    with pytest.raises(ValueError):
        ledger.task_run(999999)


def test_the_spec_reviews_fold_back_from_the_record_alone(tmp_path):
    """Folding the record rebuilds every `spec_reviews` row as written, into
    a fresh ledger and back into the source alike. `fold_task` with no facts
    drops exactly the task it names, and with an earlier fact missing keeps
    the later one's own `n`."""
    from saffron.batch import run_stack_batch
    from saffron.record.fold import fold
    from saffron.record.memory import MemoryRecord

    record = MemoryRecord()
    ledger = Ledger(tmp_path / "source.db", record=record)
    repo_id = ledger.upsert_repo("thermal-edge", "/o", "/m.git", policy_sha="p" * 64)
    order, _older_task, _earlier_batch, mint, reviews, runner = (
        _mint_and_review_arrangement(ledger, repo_id)
    )

    run_stack_batch(
        order,
        ledger,
        budget_usd=100.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
        review=reviews,
        mint=mint,
        sleep=lambda seconds: None,
    )

    te5_key = ledger.record_key(mint.tasks["TE-5"])
    assert te5_key is not None
    source_rows = _spec_reviews(ledger)
    assert [r for r in source_rows if r["task_key"] == te5_key] == [
        {"task_key": te5_key, **f.payload}
        for f in record.read(te5_key)
        if f.kind == "spec_review"
    ]

    fresh = Ledger(tmp_path / "fresh.db")
    other_repo = fresh.upsert_repo(
        "other-repo", "/other/o", "/other/m.git", policy_sha="q" * 64
    )
    other_run = fresh.create_run(other_repo, base_sha="c" * 40)
    fresh.create_task(
        other_run, spec_id="ZZ-0", spec_sha="z" * 64, branch="saffron/ZZ-0"
    )

    fold(record, fresh)
    assert _spec_reviews(fresh) == source_rows

    fold(record, ledger)
    assert _spec_reviews(ledger) == source_rows

    fresh.fold_task(te5_key, [])
    after_drop = _spec_reviews(fresh)
    assert [row for row in after_drop if row["task_key"] == te5_key] == []
    assert [row for row in after_drop if row["task_key"] != te5_key] == [
        row for row in source_rows if row["task_key"] != te5_key
    ]

    te5_facts = record.read(te5_key)
    dropped_first = False
    kept: list = []
    for fact in te5_facts:
        if not dropped_first and fact.kind == "spec_review":
            dropped_first = True
            continue
        kept.append(fact)
    fresh.fold_task(te5_key, kept)
    te5_rows = [row for row in _spec_reviews(fresh) if row["task_key"] == te5_key]
    assert len(te5_rows) == 1
    assert te5_rows[0]["n"] == 2


def test_a_stack_batch_runs_a_spec_only_when_its_own_review_routes_it_to_run(
    ledger, repo_id
):
    """A `blocker`, whatever its `fixes`, escalates and never reaches the
    runner. An unreadable review raises and never reaches the runner
    either. A `depends_on` chain that reaches either kind of miss is
    refused before its own review runs. Every other spec runs on the last
    layer, the same predecessor its own review was given."""
    from saffron.batch import run_stack_batch

    order = [
        _candidate("TE-1"),
        _candidate("TE-2"),
        _candidate("TE-3"),
        _candidate("TE-4"),
        _candidate("TE-5"),
        _candidate("TE-6"),
        _candidate("TE-7"),
        _candidate("TE-12", depends_on=["TE-1"]),
        _candidate("TE-8"),
        _candidate("TE-16", depends_on=["TE-99"]),
        _candidate("TE-9", depends_on=["TE-6", "TE-2"]),
        _candidate("TE-10", depends_on=["TE-9"]),
        _candidate("TE-11", depends_on=["TE-7"]),
        _candidate("TE-13", depends_on=["TE-3"]),
        _candidate("TE-14", depends_on=["TE-12", "TE-1"]),
        _candidate("TE-17"),
        _candidate("TE-18"),
        _candidate("TE-15"),
    ]
    reviews = ReviewScript(
        {
            "TE-1": [_clean_review()],
            "TE-2": [_review_session([_blocker("scope"), _blocker("build"), _note()])],
            "TE-3": [_review_session([_blocker("build")])],
            "TE-4": [_review_session([_blocker("witness")])],
            "TE-5": [_review_session([_blocker()])],
            "TE-6": [_review_session([_concern("scope"), _note()])],
            "TE-7": [_review_session([], error="review session failed")],
            "TE-12": [_clean_review()],
            "TE-8": [_review_session([], fenced=False)],
            "TE-16": [_clean_review()],
            "TE-14": [_clean_review()],
            "TE-17": [_clean_review()],
            "TE-18": [_clean_review()],
            "TE-15": [_clean_review()],
        }
    )

    # `_spend_task`, not `_spend`: two layers sharing `_outcome`'s default
    # `task_id=1` would collide on `record_stack_layer`'s own row.
    def _layer(state="READY_FOR_REVIEW"):
        run_id, task_id = _spend_task(ledger, repo_id, 1.0)
        return _outcome(state=state, run_id=run_id, task_id=task_id)

    results = {
        "TE-1": _layer(),
        "TE-6": _layer(),
        "TE-12": _layer(),
        "TE-16": _layer(),
        "TE-14": _layer(),
        "TE-17": _layer(state="EXHAUSTED"),
        "TE-18": _layer(),
        "TE-15": _layer(),
    }
    runner = FakeStackRunner(results)
    lines: list[str] = []

    reason = run_stack_batch(
        order,
        ledger,
        budget_usd=100.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
        emit=lines.append,
        review=reviews,
        mint=MintDouble(ledger, repo_id),
    )

    assert reason == "DRAINED"
    assert runner.calls == [
        ("TE-1", None),
        ("TE-6", "TE-1"),
        ("TE-12", "TE-6"),
        ("TE-16", "TE-12"),
        ("TE-14", "TE-16"),
        ("TE-17", "TE-14"),
        ("TE-18", "TE-14"),
        ("TE-15", "TE-18"),
    ]
    assert reviews.calls == [
        ("TE-1", None),
        ("TE-2", "TE-1"),
        ("TE-3", "TE-1"),
        ("TE-4", "TE-1"),
        ("TE-5", "TE-1"),
        ("TE-6", "TE-1"),
        ("TE-7", "TE-6"),
        ("TE-12", "TE-6"),
        ("TE-8", "TE-12"),
        ("TE-16", "TE-12"),
        ("TE-14", "TE-16"),
        ("TE-17", "TE-14"),
        ("TE-18", "TE-14"),
        ("TE-15", "TE-18"),
    ]

    escalated = {
        line[:10].strip(): line
        for line in lines
        if line[10:].startswith(" escalated  ")
    }
    assert set(escalated) == {"TE-2", "TE-3", "TE-4", "TE-5"}
    assert escalated["TE-2"].strip().endswith("2")
    assert escalated["TE-3"].strip().endswith("1")
    assert escalated["TE-4"].strip().endswith("1")
    assert escalated["TE-5"].strip().endswith("1")

    unreviewed = {
        line[:10].strip(): line
        for line in lines
        if line[10:].startswith(" unreviewed  ")
    }
    assert set(unreviewed) == {"TE-7", "TE-8"}
    assert "review session failed" in unreviewed["TE-7"]

    refused = {line.split()[0]: line for line in lines if " refused  " in line}
    assert set(refused) == {"TE-9", "TE-10", "TE-11", "TE-13"}
    assert "TE-2" in refused["TE-9"] and "TE-2" in refused["TE-10"]
    assert "TE-7" in refused["TE-11"]
    assert "TE-3" in refused["TE-13"]

    starting = [line for line in lines if line.startswith(f"{'TE-2':<10} starting")]
    assert len(starting) == 1


def test_a_spec_run_again_after_a_rate_limit_keeps_its_first_review(ledger, repo_id):
    """A spec `run_stack_batch` runs a second time after `RATE_LIMITED` is
    reviewed once: the cached `run` route is never re-read on a task-level
    rerun, only on a review-level `wait`."""
    from saffron.batch import run_stack_batch

    order = [
        _candidate("TE-41"),
        _candidate("TE-42", depends_on=["TE-41"]),
    ]
    run_one, task_one = _spend_task(ledger, repo_id, 1.0)
    run_two, task_two = _spend_task(ledger, repo_id, 1.0)
    run_three, task_three = _spend_task(ledger, repo_id, 1.0)
    outcomes = iter(
        [
            _outcome(state="RATE_LIMITED", run_id=run_one, task_id=task_one),
            _outcome(state="READY_FOR_REVIEW", run_id=run_two, task_id=task_two),
            _outcome(state="READY_FOR_REVIEW", run_id=run_three, task_id=task_three),
        ]
    )

    class RerunRunner:
        def __init__(self):
            self.calls: list[tuple[str, str | None]] = []

        def __call__(self, candidate: Candidate, predecessor: Candidate | None):
            self.calls.append(
                (candidate.spec.id, predecessor.spec.id if predecessor else None)
            )
            outcome = next(outcomes)
            if outcome.state == "RATE_LIMITED":
                return dataclasses.replace(outcome, resets_at=60)
            return outcome

    runner = RerunRunner()
    reviews = ReviewScript({"TE-41": [_clean_review()], "TE-42": [_clean_review()]})

    reason = run_stack_batch(
        order,
        ledger,
        budget_usd=100.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
        review=reviews,
        mint=MintDouble(ledger, repo_id),
        sleep=lambda seconds: None,
    )

    assert reason == "DRAINED"
    assert reviews.calls == [("TE-41", None), ("TE-42", "TE-41")]
    assert runner.calls == [
        ("TE-41", None),
        ("TE-41", None),
        ("TE-42", "TE-41"),
    ]


def test_a_spec_review_that_raises_or_errors_counts_toward_the_breaker(ledger, repo_id):
    """A review that raises counts as an abort, exactly as a raising runner
    does, and so does one that routes `error`. Two in a row fire the breaker
    before the third spec's runner is ever called. Readiness or the budget
    stopping the first spec calls no review at all. A raising review is a
    miss, so its dependent is refused unreviewed."""
    from saffron.batch import run_stack_batch

    order = [_candidate("TE-31"), _candidate("TE-32"), _candidate("TE-33")]

    class RaisingReviews:
        def __init__(self, results):
            self._results = list(results)
            self.calls: list[tuple[str, str | None]] = []

        def __call__(self, candidate: Candidate, predecessor: Candidate | None):
            self.calls.append(
                (candidate.spec.id, predecessor.spec.id if predecessor else None)
            )
            result = self._results.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

    runner = FakeStackRunner({})

    reviews = RaisingReviews([RuntimeError("boom"), RuntimeError("boom")])
    reason = run_stack_batch(
        order,
        ledger,
        budget_usd=100.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
        review=reviews,
        mint=MintDouble(ledger, repo_id),
    )
    assert reason == "INFRASTRUCTURE"
    assert runner.calls == []
    assert reviews.calls == [("TE-31", None), ("TE-32", None)]

    reviews2 = RaisingReviews(
        [
            _review_session([], error="session died"),
            _review_session([], fenced=False),
        ]
    )
    reason2 = run_stack_batch(
        order,
        ledger,
        budget_usd=100.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
        review=reviews2,
        mint=MintDouble(ledger, repo_id),
    )
    assert reason2 == "INFRASTRUCTURE"
    assert runner.calls == []
    assert reviews2.calls == [("TE-31", None), ("TE-32", None)]

    def _failing_readiness():
        return Readiness(ok=False)

    reviews3 = RaisingReviews([_clean_review(), _clean_review(), _clean_review()])
    reason3 = run_stack_batch(
        order,
        ledger,
        budget_usd=100.0,
        until=None,
        runner=runner,
        readiness_check=_failing_readiness,
        review=reviews3,
        mint=MintDouble(ledger, repo_id),
    )
    assert reason3 == "INFRASTRUCTURE"
    assert reviews3.calls == []

    order5 = [_candidate("TE-31"), _candidate("TE-34", depends_on=["TE-31"])]
    reviews5 = RaisingReviews([RuntimeError("boom"), _clean_review()])
    reason5 = run_stack_batch(
        order5,
        ledger,
        budget_usd=100.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
        review=reviews5,
        mint=MintDouble(ledger, repo_id),
    )
    assert reason5 == "DRAINED"
    assert reviews5.calls == [("TE-31", None)]

    reviews4 = RaisingReviews([_clean_review(), _clean_review(), _clean_review()])
    reason4 = run_stack_batch(
        [_candidate("TE-31", budget_usd=10.0)],
        ledger,
        budget_usd=5.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
        review=reviews4,
        mint=MintDouble(ledger, repo_id),
    )
    assert reason4 == "BUDGET"
    assert reviews4.calls == []


def test_a_rate_limited_spec_review_waits_and_reviews_again(
    ledger, repo_id, monkeypatch
):
    """A `wait` route leaves the runner untouched and is never counted by
    the breaker. It offers the same spec again next, on the same
    predecessor, reviewed afresh, never after the rest of the order and
    never past `until`."""
    from saffron.batch import run_stack_batch

    _raise_on_real_sleep(monkeypatch)
    order = [
        _candidate("TE-49"),
        _candidate("TE-50"),
        _candidate("TE-51"),
        _candidate("TE-52", depends_on=["TE-51"]),
    ]
    start = datetime(2030, 1, 1, 2, 0)
    clock = AdvancingClock(start)
    resets_at = int(start.timestamp()) + 60
    reviews = ReviewScript(
        {
            "TE-49": [_clean_review()],
            "TE-50": [_review_session([], error="session died")],
            "TE-51": [
                _review_session([], fenced=False, resets_at=resets_at),
                _clean_review(),
            ],
            "TE-52": [_clean_review()],
        }
    )
    run_49, task_49 = _spend_task(ledger, repo_id, 1.0)
    run_51, task_51 = _spend_task(ledger, repo_id, 1.0)
    run_52, task_52 = _spend_task(ledger, repo_id, 1.0)
    # `TE-51` runs only once despite two reviews, so `FakeStackRunner`'s
    # per-spec-id lookup, never popped, is exactly the shape this needs.
    runner = FakeStackRunner(
        {
            "TE-49": _outcome(state="READY_FOR_REVIEW", run_id=run_49, task_id=task_49),
            "TE-51": _outcome(state="READY_FOR_REVIEW", run_id=run_51, task_id=task_51),
            "TE-52": _outcome(state="READY_FOR_REVIEW", run_id=run_52, task_id=task_52),
        }
    )
    lines: list[str] = []

    reason = run_stack_batch(
        order,
        ledger,
        budget_usd=100.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
        clock=clock,
        sleep=clock.sleep,
        emit=lines.append,
        review=reviews,
        mint=MintDouble(ledger, repo_id),
    )

    assert reason == "DRAINED"
    assert reviews.calls == [
        ("TE-49", None),
        ("TE-50", "TE-49"),
        ("TE-51", "TE-49"),
        ("TE-51", "TE-49"),
        ("TE-52", "TE-51"),
    ]
    assert runner.calls == [
        ("TE-49", None),
        ("TE-51", "TE-49"),
        ("TE-52", "TE-51"),
    ]
    assert not any(" refused " in line for line in lines)
    starting_51 = [line for line in lines if line.startswith(f"{'TE-51':<10} starting")]
    assert len(starting_51) == 2
    assert clock.sleeps == [60.0]

    start2 = datetime(2030, 1, 1, 2, 0)
    clock2 = AdvancingClock(start2)
    reviews2 = ReviewScript(
        {"TE-51": [_review_session([], resets_at=int(start2.timestamp()) + 60)]}
    )
    runner2 = FakeStackRunner({})

    reason2 = run_stack_batch(
        [_candidate("TE-51")],
        ledger,
        budget_usd=100.0,
        until=start2 + timedelta(seconds=30),
        runner=runner2,
        readiness_check=_ready,
        clock=clock2,
        sleep=clock2.sleep,
        review=reviews2,
        mint=MintDouble(ledger, repo_id),
    )

    assert reason2 == "UNTIL"
    assert clock2.sleeps == []
    assert reviews2.calls == [("TE-51", None)]
    assert runner2.calls == []
