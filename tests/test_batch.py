import dataclasses
from collections import defaultdict
from collections.abc import Mapping, Sequence
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

    # A candidate at exactly the budget runs, so any default hold stops it.
    exact = [_candidate("TE-0002", budget_usd=5.0)]
    exact_runner = FakeRunner(
        [_outcome(state="READY_FOR_REVIEW", run_id=_spend(ledger, repo_id, 0.0))]
    )
    reason = run_batch(
        exact,
        ledger,
        budget_usd=5.0,
        until=None,
        runner=exact_runner,
        rescan=lambda: exact,
        readiness_check=_ready,
    )
    assert reason == "DRAINED"
    assert exact_runner.calls == exact


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
    assert {
        "GATE_ERROR",
        "PREFLIGHT_FAILED",
        "RATE_LIMITED",
        "PROVIDER_UNREACHABLE",
    } == ABORT_STATES
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


def test_a_provider_that_served_nothing_counts_toward_the_breaker(ledger, repo_id):
    """A plain batch treats `PROVIDER_UNREACHABLE` as it treats
    `PREFLIGHT_FAILED` (b-031ac2): two in a row still fire the breaker."""
    candidates = [_candidate("TE-0001"), _candidate("TE-0002"), _candidate("TE-0003")]
    run_one = _spend(ledger, repo_id, 1.0)
    run_two = _spend(ledger, repo_id, 1.0)
    runner = FakeRunner(
        [
            _outcome(state="PROVIDER_UNREACHABLE", run_id=run_one),
            _outcome(state="PROVIDER_UNREACHABLE", run_id=run_two),
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


def test_a_stack_batch_offers_a_provider_that_served_nothing_again_until_the_breaker(
    ledger, repo_id, monkeypatch
):
    """A stack batch does not treat `PROVIDER_UNREACHABLE` as a miss
    (b-031ac2): the same spec is offered again at once, on the same
    predecessor, with no wait, and nothing that depends on it is refused.
    The breaker is still the only bound on the re-offers."""
    from saffron.batch import run_stack_batch

    _raise_on_real_sleep(monkeypatch)
    order = [
        _candidate("TE-0"),
        _candidate("TE-1"),
        _candidate("TE-2", depends_on=["TE-1"]),
        _candidate("TE-3"),
    ]
    clock = AdvancingClock(datetime(2030, 1, 1, 2, 0))
    runner = RateLimitScript(
        ledger,
        repo_id,
        clock,
        {
            "TE-0": [{"state": "READY_FOR_REVIEW"}],
            "TE-1": [
                {"state": "PROVIDER_UNREACHABLE"},
                {"state": "READY_FOR_REVIEW"},
            ],
            "TE-2": [{"state": "READY_FOR_REVIEW"}],
            "TE-3": [
                {"state": "PROVIDER_UNREACHABLE"},
                {"state": "READY_FOR_REVIEW"},
            ],
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

    assert reason == "DRAINED"
    assert not any(" refused " in line for line in lines)
    assert clock.sleeps == []
    assert runner.calls == [
        ("TE-0", None),
        ("TE-1", "TE-0"),
        ("TE-1", "TE-0"),
        ("TE-2", "TE-1"),
        ("TE-3", "TE-2"),
        ("TE-3", "TE-2"),
    ]

    order2 = [_candidate("TE-5")]
    clock2 = AdvancingClock(datetime(2030, 1, 1, 2, 0))
    runner2 = RateLimitScript(
        ledger,
        repo_id,
        clock2,
        {
            "TE-5": [
                {"state": "PROVIDER_UNREACHABLE"},
                {"state": "PROVIDER_UNREACHABLE"},
                {"state": "READY_FOR_REVIEW"},
            ],
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

    assert reason2 == "INFRASTRUCTURE"
    assert clock2.sleeps == []
    assert runner2.calls == [("TE-5", None), ("TE-5", None)]

    # With the state left out of the breaker's own abort set, the same
    # spec runs a third time and the night drains instead.
    monkeypatch.setattr(
        "saffron.batch.ABORT_STATES",
        ABORT_STATES - {"PROVIDER_UNREACHABLE"},
    )
    order3 = [_candidate("TE-8")]
    clock3 = AdvancingClock(datetime(2030, 1, 1, 2, 0))
    runner3 = RateLimitScript(
        ledger,
        repo_id,
        clock3,
        {
            "TE-8": [
                {"state": "PROVIDER_UNREACHABLE"},
                {"state": "PROVIDER_UNREACHABLE"},
                {"state": "READY_FOR_REVIEW"},
            ],
        },
    )

    reason3 = run_stack_batch(
        order3,
        ledger,
        budget_usd=100.0,
        until=None,
        runner=runner3,
        readiness_check=_ready,
        clock=clock3,
        sleep=clock3.sleep,
    )

    assert reason3 == "DRAINED"
    assert runner3.calls == [("TE-8", None), ("TE-8", None), ("TE-8", None)]


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


def _clean_run_review(candidate, predecessor=None, **kwargs):
    """A `review` double that always routes `run`, at no cost. Every call
    site in this file needs `review` only to satisfy `follow_ups`' own
    check, not to drive a scripted route."""
    return _clean_review(cost=0.0)


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


def _candidate_x(spec_id: str, *, budget_usd: float = 12.0, **kw) -> Candidate:
    """A candidate whose path is `<id>-x.md`, never the bare spec id, so a
    text `run_stack_batch` records at the spec id's own name fails."""
    candidate = _candidate(spec_id, budget_usd=budget_usd, **kw)
    return dataclasses.replace(candidate, path=Path(f"{spec_id}-x.md"))


class _RevisionReview:
    """The `review` double for the revision-round witnesses. Each call
    pops the spec's next scripted round of findings and records
    `(spec id, layer's spec id or None, kw)`. Its session's text is one
    fenced ```json block alone, its claim naming the spec and this
    review's own number. Two rounds sharing findings never share text."""

    def __init__(self, table: dict[str, list[list[dict]]]):
        self._table = {sid: list(rounds) for sid, rounds in table.items()}
        self.calls: list[tuple[str, str | None, dict]] = []
        self.sessions: dict[str, list] = {}

    def __call__(self, candidate: Candidate, layer: Candidate | None, **kw):
        spec_id = candidate.spec.id
        self.calls.append((spec_id, layer.spec.id if layer else None, kw))
        n = len(self.sessions.setdefault(spec_id, [])) + 1
        findings = self._table[spec_id].pop(0)
        session = _review_session(
            [{**f, "claim": f"{spec_id} review {n}"} for f in findings]
        )
        self.sessions[spec_id].append(session)
        return session


class _Rejected:
    """A writer turn scripted to meet the account's own rate limit, at the
    clock's own time when `_RevisionWrite` is called for it. Never a
    figure fixed when the table is built."""

    def __init__(self, cost: float = 0.25):
        self.cost = cost


def _written(text: str, *, session_id: str = "w-1", turns: int = 9, cost: float = 1.0):
    from saffron.spec_review import SpecWriterSession

    return SpecWriterSession(
        text=text,
        cost_usd=cost,
        error=None,
        resets_at=None,
        session_id=session_id,
        num_turns=turns,
        spec_sha=hash_artifact(text),
    )


def _writer_error(message: str, *, cost: float = 0.125):
    from saffron.spec_review import SpecWriterSession

    return SpecWriterSession(
        text="",
        cost_usd=cost,
        error=message,
        resets_at=None,
        session_id=None,
        num_turns=0,
        spec_sha=None,
    )


class _RevisionWrite:
    """The `revise` double for the revision-round witnesses. Each call
    records `(spec id, layer's spec id or None, spec text, review text,
    the spec's task state at the call)`, then pops the spec's next
    scripted turn or exception, raising `AssertionError` when none is
    left."""

    def __init__(self, ledger: Ledger, clock, table: dict[str, list]):
        from saffron.spec_review import SpecWriterSession

        self._ledger = ledger
        self._clock = clock
        self._table = {sid: list(turns) for sid, turns in table.items()}
        self.calls: list[tuple] = []
        self._SpecWriterSession = SpecWriterSession

    def __call__(
        self,
        candidate: Candidate,
        layer: Candidate | None,
        spec_text: str | None,
        review_text: str,
    ):
        assert candidate.task_id is not None
        self.calls.append(
            (
                candidate.spec.id,
                layer.spec.id if layer else None,
                spec_text,
                review_text,
                _task_state(self._ledger, candidate.task_id),
            )
        )
        queue = self._table.get(candidate.spec.id)
        if not queue:
            raise AssertionError(f"no writer turn scripted for {candidate.spec.id}")
        entry = queue.pop(0)
        if isinstance(entry, _Rejected):
            return self._SpecWriterSession(
                text="",
                cost_usd=entry.cost,
                error=None,
                resets_at=int(self._clock().timestamp()) + 60,
                session_id=None,
                num_turns=0,
                spec_sha=None,
            )
        if isinstance(entry, Exception):
            raise entry
        return entry


class _RevisionMint(MintDouble):
    """`MintDouble`, except `TE-5` alone gets three `revision` texts
    recorded on its new task first. A round count read from those rows
    would start it at three, which rounds never do (D1): they come from
    this call alone."""

    def __call__(self, candidate: Candidate) -> int:
        task_id = super().__call__(candidate)
        if candidate.spec.id == "TE-5":
            for text in ("s1\n", "s2\n", "s3\n"):
                self._ledger.record_spec_text(
                    task_id,
                    origin="revision",
                    spec_id="TE-5",
                    path=".saffron/specs/TE-5-x.md",
                    text=text,
                )
        return task_id


class _RevisionRunner(RunnerDouble):
    """`RunnerDouble`, always returning `READY_FOR_REVIEW`. It also keeps
    in `texts` the text of `ledger.spec_text` of `candidate.task_id`, or
    `None`, as each call saw it."""

    def __init__(self, ledger: Ledger, repo_id: int):
        super().__init__(ledger, repo_id, {})
        self._table = defaultdict(lambda: ["READY_FOR_REVIEW"])
        self.texts: list[str | None] = []

    def __call__(self, candidate: Candidate, predecessor: Candidate | None):
        assert candidate.task_id is not None
        row = self._ledger.spec_text(candidate.task_id)
        self.texts.append(row["text"] if row else None)
        return super().__call__(candidate, predecessor)


def _task_state(ledger: Ledger, task_id: int) -> str:
    row = ledger._db.execute(
        "SELECT state FROM tasks WHERE task_id = ?", (task_id,)
    ).fetchone()
    return row["state"]


def _task_routes(ledger: Ledger, task_id: int) -> list[str]:
    rows = ledger._db.execute(
        "SELECT route FROM spec_reviews WHERE task_key = ? ORDER BY n",
        (ledger.record_key(task_id),),
    ).fetchall()
    return [row["route"] for row in rows]


def _last_line(lines: list[str], spec_id: str, word: str) -> str:
    """The last of `lines` that starts with `spec_id`'s own column and
    holds `word`, for the revision-round witnesses' own emitted lines."""
    matches = [
        line for line in lines if line.startswith(f"{spec_id:<10}") and word in line
    ]
    assert matches, f"no {word!r} line for {spec_id}"
    return matches[-1]


def _revision_round_order() -> list[Candidate]:
    return [
        _candidate_x("TE-1"),
        _candidate_x("TE-2"),
        _candidate_x("TE-3", depends_on=["TE-2"]),
        _candidate_x("TE-4"),
        _candidate_x("TE-5"),
        _candidate_x("TE-10"),
        _candidate_x("TE-7"),
        _candidate_x("TE-9", budget_usd=37.625),
        _candidate_x("TE-6"),
        _candidate_x("TE-8"),
        _candidate_x("TE-11"),
    ]


def _revision_round_arrangement(ledger: Ledger, repo_id: int, clock):
    """The one arrangement shared by every revision-round witness (SA-0164).
    Returns `(order, mint, reviews, revise, runner)`, freshly built so each
    witness runs it on its own ledger and its own clock."""
    mint = _RevisionMint(ledger, repo_id)
    reviews = _RevisionReview(
        {
            "TE-1": [[_blocker("build")], [_blocker("witness")], []],
            "TE-2": [
                [_blocker("witness")],
                [_blocker("witness")],
                [_blocker("build")],
                [_blocker("witness")],
            ],
            "TE-4": [[_concern("witness")]] * 4,
            "TE-5": [[_blocker("build")], [_concern("witness")], []],
            "TE-10": [
                [_blocker("build")],
                [_blocker("build")],
                [_blocker("build")],
                [_concern("witness")],
            ],
            "TE-7": [[]],
            "TE-9": [[_blocker("witness")], [_blocker("witness")]],
            "TE-6": [[_blocker("build")]],
            "TE-8": [[_blocker("build")]],
        }
    )
    revise = _RevisionWrite(
        ledger,
        clock,
        {
            "TE-1": [_written("r1a\n"), _written("r1b\n")],
            "TE-2": [
                _Rejected(0.25),
                _written("r2a\n"),
                _written("r2b\n"),
                _written("r2c\n"),
            ],
            "TE-4": [_written("r4a\n"), _written("r4b\n"), _written("r4c\n")],
            "TE-5": [_written("r5a\n"), _written("r5b\n")],
            "TE-10": [_written("t1\n"), _written("t2\n"), _written("t3\n")],
            "TE-9": [_written("r9\n"), _Rejected(0.25)],
            "TE-6": [_writer_error("api_error", cost=0.125)],
            "TE-8": [RuntimeError("writer cell would not start")],
        },
    )
    runner = _RevisionRunner(ledger, repo_id)
    return _revision_round_order(), mint, reviews, revise, runner


def test_a_revisable_blocker_is_revised_and_reviewed_again_for_at_most_three_rounds(
    ledger, repo_id, tmp_path
):
    """A `build` or `witness` blocker, or any `concern` tagged
    `witness`, is revised for up to three rounds before it escalates. A
    clean read after fewer rounds runs instead. Rounds reset for a fresh
    call of `run_stack_batch`, never carried by the ledger, and `revise`
    left unset keeps the old escalate-or-run behavior with no suffix."""
    from saffron.batch import run_stack_batch

    clock = AdvancingClock(datetime(2030, 1, 1, 2, 0))
    order, mint, reviews, revise, runner = _revision_round_arrangement(
        ledger, repo_id, clock
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
        mint=mint,
        revise=revise,
        reserve_usd=8.0,
    )

    assert reason == "INFRASTRUCTURE"

    assert reviews.calls[:19] == [
        ("TE-1", None, {}),
        ("TE-1", None, {"spec_text": "r1a\n"}),
        ("TE-1", None, {"spec_text": "r1b\n"}),
        ("TE-2", "TE-1", {}),
        ("TE-2", "TE-1", {"spec_text": "r2a\n"}),
        ("TE-2", "TE-1", {"spec_text": "r2b\n"}),
        ("TE-2", "TE-1", {"spec_text": "r2c\n"}),
        ("TE-4", "TE-1", {}),
        ("TE-4", "TE-1", {"spec_text": "r4a\n"}),
        ("TE-4", "TE-1", {"spec_text": "r4b\n"}),
        ("TE-4", "TE-1", {"spec_text": "r4c\n"}),
        ("TE-5", "TE-1", {"spec_text": "s3\n"}),
        ("TE-5", "TE-1", {"spec_text": "r5a\n"}),
        ("TE-5", "TE-1", {"spec_text": "r5b\n"}),
        ("TE-10", "TE-5", {}),
        ("TE-10", "TE-5", {"spec_text": "t1\n"}),
        ("TE-10", "TE-5", {"spec_text": "t2\n"}),
        ("TE-10", "TE-5", {"spec_text": "t3\n"}),
        ("TE-7", "TE-5", {}),
    ]

    def _writer_texts(spec_id: str) -> list[tuple[str | None, str | None, str]]:
        return [(c[1], c[2], c[3]) for c in revise.calls if c[0] == spec_id]

    te1_sessions = reviews.sessions["TE-1"]
    assert _writer_texts("TE-1") == [
        (None, None, te1_sessions[0].text),
        (None, "r1a\n", te1_sessions[1].text),
    ]
    te2_sessions = reviews.sessions["TE-2"]
    assert _writer_texts("TE-2") == [
        ("TE-1", None, te2_sessions[0].text),
        ("TE-1", None, te2_sessions[0].text),
        ("TE-1", "r2a\n", te2_sessions[1].text),
        ("TE-1", "r2b\n", te2_sessions[2].text),
    ]
    te4_sessions = reviews.sessions["TE-4"]
    assert _writer_texts("TE-4") == [
        ("TE-1", None, te4_sessions[0].text),
        ("TE-1", "r4a\n", te4_sessions[1].text),
        ("TE-1", "r4b\n", te4_sessions[2].text),
    ]
    te5_sessions = reviews.sessions["TE-5"]
    assert _writer_texts("TE-5") == [
        ("TE-1", "s3\n", te5_sessions[0].text),
        ("TE-1", "r5a\n", te5_sessions[1].text),
    ]
    te10_sessions = reviews.sessions["TE-10"]
    assert _writer_texts("TE-10") == [
        ("TE-5", None, te10_sessions[0].text),
        ("TE-5", "t1\n", te10_sessions[1].text),
        ("TE-5", "t2\n", te10_sessions[2].text),
    ]

    assert runner.calls == [
        ("TE-1", mint.tasks["TE-1"]),
        ("TE-5", mint.tasks["TE-5"]),
        ("TE-7", mint.tasks["TE-7"]),
    ]
    assert runner.texts[0] == "r1b\n"
    assert runner.texts[1] == "r5b\n"
    assert runner.texts[2] is None

    assert _last_line(lines, "TE-1", "revised").strip().endswith("revised  2")
    assert _last_line(lines, "TE-5", "revised").strip().endswith("revised  2")
    assert _last_line(lines, "TE-2", "revised").strip().endswith("revised  3")
    assert _last_line(lines, "TE-4", "revised").strip().endswith("revised  3")
    assert _last_line(lines, "TE-10", "revised").strip().endswith("revised  3")
    assert (
        _last_line(lines, "TE-2", "escalated")
        .strip()
        .endswith("escalated  1 after 3 revisions")
    )
    assert (
        _last_line(lines, "TE-4", "escalated")
        .strip()
        .endswith("escalated  0 after 3 revisions")
    )
    assert (
        _last_line(lines, "TE-10", "escalated")
        .strip()
        .endswith("escalated  0 after 3 revisions")
    )
    assert any(
        line.startswith(f"{'TE-3':<10}") and " refused " in line for line in lines
    )

    # A second batch in the same process, on a fresh ledger: rounds reset,
    # so a store of rounds kept at module scope would carry over and fail.
    ledger2 = Ledger(tmp_path / "second.db")
    repo_id2 = ledger2.upsert_repo(
        "thermal-edge-2", "/o2", "/m2.git", policy_sha="p" * 64
    )
    clock2 = AdvancingClock(datetime(2030, 1, 1, 2, 0))
    mint2 = _RevisionMint(ledger2, repo_id2)
    reviews2 = _RevisionReview(
        {
            "TE-2": [[_blocker("build")], []],
            "TE-9": [[_blocker("build")], []],
        }
    )
    revise2 = _RevisionWrite(
        ledger2, clock2, {"TE-2": [_written("v2\n")], "TE-9": [_written("v9\n")]}
    )
    runner2 = _RevisionRunner(ledger2, repo_id2)
    lines2: list[str] = []

    reason2 = run_stack_batch(
        [_candidate_x("TE-2"), _candidate_x("TE-9")],
        ledger2,
        budget_usd=100.0,
        until=None,
        runner=runner2,
        readiness_check=_ready,
        clock=clock2,
        sleep=clock2.sleep,
        emit=lines2.append,
        review=reviews2,
        mint=mint2,
        revise=revise2,
        reserve_usd=8.0,
    )

    assert reason2 == "DRAINED"
    assert _last_line(lines2, "TE-2", "revised").strip().endswith("revised  1")
    assert _last_line(lines2, "TE-9", "revised").strip().endswith("revised  1")

    # A third batch on a fresh ledger, `revise` left unset: the old
    # escalate-or-run behavior, with no suffix on the escalated line.
    ledger3 = Ledger(tmp_path / "third.db")
    repo_id3 = ledger3.upsert_repo(
        "thermal-edge-3", "/o3", "/m3.git", policy_sha="p" * 64
    )
    mint3 = _RevisionMint(ledger3, repo_id3)
    reviews3 = _RevisionReview(
        {
            "TE-11": [[_blocker("build")]],
            "TE-12": [[_concern("witness")]],
        }
    )
    runner3 = _RevisionRunner(ledger3, repo_id3)
    lines3: list[str] = []

    reason3 = run_stack_batch(
        [_candidate_x("TE-11"), _candidate_x("TE-12")],
        ledger3,
        budget_usd=100.0,
        until=None,
        runner=runner3,
        readiness_check=_ready,
        emit=lines3.append,
        review=reviews3,
        mint=mint3,
    )

    assert reason3 == "DRAINED"
    assert runner3.calls[0][0] == "TE-12"
    assert len(runner3.calls) == 1
    te11_escalated = _last_line(lines3, "TE-11", "escalated")
    assert te11_escalated.strip().endswith("escalated  1")
    assert "after" not in te11_escalated
    assert _task_routes(ledger3, mint3.tasks["TE-11"]) == ["escalate"]
    assert _task_state(ledger3, mint3.tasks["TE-11"]) == "SPEC_WITHHELD"
    assert _task_routes(ledger3, mint3.tasks["TE-12"]) == ["run"]


def _finding(severity, claim, *, fixes=None, criterion=None, file=None, line=None):
    """One raw finding dict for a scripted review session's own
    ```json block, for the `spec_finding`-recording witnesses below."""
    return {
        "severity": severity,
        "claim": claim,
        "fixes": fixes,
        "criterion": criterion,
        "file": file,
        "line": line,
    }


class _FindingsReview:
    """The `review` double for the `spec_finding`-recording witnesses. Each
    call pops the spec's next scripted `SpecReviewSession`, or raises its
    next scripted exception, and records `(spec id, layer's spec id or
    None, kw)`."""

    def __init__(self, table: dict[str, list]):
        self._table = {sid: list(entries) for sid, entries in table.items()}
        self.calls: list[tuple[str, str | None, dict]] = []

    def __call__(self, candidate: Candidate, layer: Candidate | None, **kw):
        spec_id = candidate.spec.id
        self.calls.append((spec_id, layer.spec.id if layer else None, kw))
        entry = self._table[spec_id].pop(0)
        if isinstance(entry, Exception):
            raise entry
        return entry


def _spec_findings(ledger: Ledger) -> list[dict]:
    """Every `spec_findings` row, ordered by `(task_key, n, position)`, as
    plain dicts so an assertion can compare them by value and by type."""
    rows = ledger._db.execute(
        "SELECT * FROM spec_findings ORDER BY task_key, n, position"
    ).fetchall()
    return [dict(row) for row in rows]


def _assert_rows_match(actual: list[dict], expected: list[dict]) -> None:
    """Field-by-field, value and type alike. `True == 1` under plain `==`,
    so a `bool` kept as an `int` must fail this check on its type."""
    assert len(actual) == len(expected), (actual, expected)
    for row, want in zip(actual, expected, strict=True):
        assert row.keys() == want.keys(), (row, want)
        for key, value in want.items():
            assert row[key] == value, (key, row, want)
            assert type(row[key]) is type(value), (key, row, want)


def _spec_finding_arrangement(ledger: Ledger, repo_id: int, clock: AdvancingClock):
    """The one arrangement shared by both `spec_finding`-recording witnesses
    (`tests/test_batch.py::test_each_spec_review_round_records_each_of_its_findings`,
    `::test_the_spec_findings_fold_back_from_the_record_alone`). Eight
    specs, with a clean round between any two whose round aborts, so the
    breaker (`_BREAKER_THRESHOLD`, two in a row) never fires. Returns
    `(order, mint, reviews, revise, runner)`."""
    order = [
        _candidate_x("TE-1"),
        _candidate_x("TE-2"),
        _candidate_x("TE-3"),
        _candidate_x("TE-4"),
        _candidate_x("TE-5"),
        _candidate_x("TE-6"),
        _candidate_x("TE-7"),
        _candidate_x("TE-8"),
    ]
    mint = MintDouble(ledger, repo_id)
    wait_resets_at = int(clock().timestamp()) + 60
    reviews = _FindingsReview(
        {
            "TE-1": [
                _review_session(
                    [
                        _finding("concern", "TE-1 r1 f1", fixes="witness"),
                        _finding(
                            "blocker",
                            "TE-1 r1 f2",
                            fixes="build",
                            criterion=1,
                            file="a.py",
                            line=40,
                        ),
                        _finding("note", "TE-1 r1 f3", criterion=2, file="a.py"),
                    ]
                ),
                _review_session([_finding("note", "TE-1 r2 f1", line=99)]),
            ],
            "TE-2": [
                _review_session(
                    [
                        _finding(
                            "concern", "TE-2 r1 f1", criterion=1, file="b.py", line=2
                        )
                    ],
                    error="cell died",
                )
            ],
            "TE-3": [
                _review_session(
                    [
                        _finding(
                            "concern",
                            "TE-3 r1 f1",
                            fixes="build",
                            criterion=[1, 2],
                            file={"path": "c.py"},
                            line=[12, 40],
                        ),
                        _finding("note", "TE-3 r1 f2", criterion=True, line=2.5),
                    ]
                )
            ],
            "TE-4": [_review_session([], fenced=False)],
            "TE-5": [
                _review_session([], fenced=False, resets_at=wait_resets_at),
                _review_session(
                    [_finding("note", "TE-5 r2 f1", criterion=3, file="e.py", line=7)]
                ),
            ],
            "TE-6": [RuntimeError("spec review crashed for TE-6")],
            "TE-7": [_review_session([])],
            "TE-8": [
                _review_session(
                    [
                        _finding(
                            "blocker",
                            "TE-8 r1 f1",
                            fixes="scope",
                            criterion=1,
                            file="h.py",
                            line=5,
                        ),
                        _finding(
                            "note", "TE-8 r1 f2", criterion="2", file="h.py", line=9
                        ),
                    ]
                )
            ],
        }
    )
    revise = _RevisionWrite(ledger, clock, {"TE-1": [_written("te1-r2\n")]})
    runner = _RevisionRunner(ledger, repo_id)
    return order, mint, reviews, revise, runner


def test_each_spec_review_round_records_each_of_its_findings(tmp_path):
    """`run_stack_batch` records each spec review round's findings one by
    one. Each becomes a `spec_finding` fact and a `spec_findings` row, `n`
    and `position` from 1 in block order. It carries the finding's
    `severity`, `fixes`, `claim`, `criterion`, `file` and `line` as read,
    a null included. Any `criterion`, `file` or `line` that is not `None`,
    a `str`, or an in-range non-`bool` `int` is stored as its JSON text. A
    round's `spec_finding` facts are appended after its own `spec_review`
    fact, and a round with no findings, or routed `error`, writes none."""
    from saffron.batch import run_stack_batch
    from saffron.record.memory import MemoryRecord

    record = MemoryRecord()
    ledger = Ledger(tmp_path / "ledger.db", record=record)
    repo_id = ledger.upsert_repo("thermal-edge", "/o", "/m.git", policy_sha="p" * 64)
    clock = AdvancingClock(datetime(2030, 1, 1, 2, 0))
    order, mint, reviews, revise, runner = _spec_finding_arrangement(
        ledger, repo_id, clock
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
        mint=mint,
        revise=revise,
        reserve_usd=8.0,
    )

    assert reason == "DRAINED"

    routes = {
        "TE-1": ["revise", "run"],
        "TE-2": ["error"],
        "TE-3": ["run"],
        "TE-4": ["error"],
        "TE-5": ["wait", "run"],
        "TE-6": ["error"],
        "TE-7": ["run"],
        "TE-8": ["escalate"],
    }
    for spec_id, want in routes.items():
        assert _task_routes(ledger, mint.tasks[spec_id]) == want, spec_id

    keys = {
        spec_id: ledger.record_key(task_id) for spec_id, task_id in mint.tasks.items()
    }

    def _row(spec_id, n, position, severity, fixes, claim, criterion, file, line):
        return {
            "task_key": keys[spec_id],
            "n": n,
            "position": position,
            "severity": severity,
            "fixes": fixes,
            "claim": claim,
            "criterion": criterion,
            "file": file,
            "line": line,
        }

    expected = [
        _row("TE-1", 1, 1, "concern", "witness", "TE-1 r1 f1", None, None, None),
        _row("TE-1", 1, 2, "blocker", "build", "TE-1 r1 f2", 1, "a.py", 40),
        _row("TE-1", 1, 3, "note", None, "TE-1 r1 f3", 2, "a.py", None),
        _row("TE-1", 2, 1, "note", None, "TE-1 r2 f1", None, None, 99),
        _row(
            "TE-3",
            1,
            1,
            "concern",
            "build",
            "TE-3 r1 f1",
            "[1, 2]",
            '{"path": "c.py"}',
            "[12, 40]",
        ),
        _row("TE-3", 1, 2, "note", None, "TE-3 r1 f2", "true", None, "2.5"),
        _row("TE-5", 2, 1, "note", None, "TE-5 r2 f1", 3, "e.py", 7),
        _row("TE-8", 1, 1, "blocker", "scope", "TE-8 r1 f1", 1, "h.py", 5),
        _row("TE-8", 1, 2, "note", None, "TE-8 r1 f2", "2", "h.py", 9),
    ]
    expected.sort(key=lambda row: (row["task_key"], row["n"], row["position"]))
    _assert_rows_match(_spec_findings(ledger), expected)
    # The facts too: a fold re-normalizing raw facts would pass the rows alone.
    facts = [
        {"task_key": key, **fact.payload}
        for key in sorted(k for k in keys.values() if k is not None)
        for fact in record.read(key)
        if fact.kind == "spec_finding"
    ]
    _assert_rows_match(facts, expected)

    for spec_id in ("TE-2", "TE-4", "TE-6", "TE-7"):
        assert [
            row for row in _spec_findings(ledger) if row["task_key"] == keys[spec_id]
        ] == []

    te1_key = keys["TE-1"]
    assert te1_key is not None
    te1_facts = record.read(te1_key)
    assert [
        (f.kind, f.payload["n"])
        for f in te1_facts
        if f.kind in ("spec_review", "spec_finding")
    ] == [
        ("spec_review", 1),
        ("spec_finding", 1),
        ("spec_finding", 1),
        ("spec_finding", 1),
        ("spec_review", 2),
        ("spec_finding", 2),
    ]


def test_the_spec_findings_fold_back_from_the_record_alone(tmp_path):
    """Folding the record into a fresh ledger, and back into the source,
    rebuilds every `spec_findings` row as written. `fold_task` given no
    facts drops that task's rows and no other task's. Given a task's facts
    less its first round's `spec_review` and `spec_finding` facts, it keeps
    the second round's rows with their own `n`."""
    from saffron.batch import run_stack_batch
    from saffron.record.fold import fold
    from saffron.record.memory import MemoryRecord

    record = MemoryRecord()
    ledger = Ledger(tmp_path / "source.db", record=record)
    repo_id = ledger.upsert_repo("thermal-edge", "/o", "/m.git", policy_sha="p" * 64)
    clock = AdvancingClock(datetime(2030, 1, 1, 2, 0))
    order, mint, reviews, revise, runner = _spec_finding_arrangement(
        ledger, repo_id, clock
    )

    run_stack_batch(
        order,
        ledger,
        budget_usd=100.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
        clock=clock,
        sleep=clock.sleep,
        review=reviews,
        mint=mint,
        revise=revise,
        reserve_usd=8.0,
    )

    te1_key = ledger.record_key(mint.tasks["TE-1"])
    assert te1_key is not None
    source_rows = _spec_findings(ledger)

    fresh = Ledger(tmp_path / "fresh.db")
    other_repo = fresh.upsert_repo(
        "other-repo", "/other/o", "/other/m.git", policy_sha="q" * 64
    )
    other_run = fresh.create_run(other_repo, base_sha="c" * 40)
    fresh.create_task(
        other_run, spec_id="ZZ-0", spec_sha="z" * 64, branch="saffron/ZZ-0"
    )

    fold(record, fresh)
    assert _spec_findings(fresh) == source_rows

    fold(record, ledger)
    assert _spec_findings(ledger) == source_rows

    fresh.fold_task(te1_key, [])
    after_drop = _spec_findings(fresh)
    assert [row for row in after_drop if row["task_key"] == te1_key] == []
    assert [row for row in after_drop if row["task_key"] != te1_key] == [
        row for row in source_rows if row["task_key"] != te1_key
    ]

    te1_facts = record.read(te1_key)
    kept = [
        fact
        for fact in te1_facts
        if not (fact.kind in ("spec_review", "spec_finding") and fact.payload["n"] == 1)
    ]
    fresh.fold_task(te1_key, kept)
    te1_rows = [row for row in _spec_findings(fresh) if row["task_key"] == te1_key]
    assert te1_rows == [
        row for row in source_rows if row["task_key"] == te1_key and row["n"] == 2
    ]


def test_a_revision_waits_on_a_rate_limit_and_stops_on_an_error_a_raise_or_the_budget(
    ledger, repo_id
):
    """A writer session with `resets_at` set waits like a rate-limited
    review does, and the retry hands the same review text back with no
    fresh review. `revise` is not called once the budget left falls
    short of both session ceilings and the spec's own `budget_usd`. The
    spec is refused instead, its task's state untouched. An errored
    writer session ends `GATE_ERROR` and is charged as an abort, and so
    does a writer callable that raises outright."""
    from saffron.batch import run_stack_batch

    clock = AdvancingClock(datetime(2030, 1, 1, 2, 0))
    order, mint, reviews, revise, runner = _revision_round_arrangement(
        ledger, repo_id, clock
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
        mint=mint,
        revise=revise,
        reserve_usd=8.0,
    )

    assert reason == "INFRASTRUCTURE"
    assert clock.sleeps == [60.0, 60.0]

    te2_states = [c[4] for c in revise.calls if c[0] == "TE-2"][:2]
    assert te2_states == ["QUEUED", "RATE_LIMITED"]

    last_writers = [c[:2] for c in revise.calls][-4:]
    assert last_writers == [
        ("TE-9", "TE-7"),
        ("TE-9", "TE-7"),
        ("TE-6", "TE-7"),
        ("TE-8", "TE-7"),
    ]

    te9_reviews = [c for c in reviews.calls if c[0] == "TE-9"]
    assert te9_reviews == [
        ("TE-9", "TE-7", {}),
        ("TE-9", "TE-7", {"spec_text": "r9\n"}),
    ]

    te9_lines = [line for line in lines if line.startswith(f"{'TE-9':<10}")]
    assert any(line.strip().endswith("revised  1") for line in te9_lines)
    assert sum("unrevised" in line for line in te9_lines) == 1

    te6_lines = [
        line
        for line in lines
        if line.startswith(f"{'TE-6':<10}") and "unrevised" in line
    ]
    assert len(te6_lines) == 1
    assert te6_lines[0].strip().endswith("unrevised  api_error")

    raised_te8 = [
        line
        for line in lines
        if line.startswith(f"{'TE-8':<10}") and "raised RuntimeError" in line
    ]
    assert len(raised_te8) == 1

    assert not any(line.startswith(f"{'TE-11':<10}") for line in lines)


def test_each_revision_is_an_attempt_and_a_spec_text_on_its_specs_task(ledger, repo_id):
    """Each writer session that returns adds one attempt on the spec's
    task in phase `SPEC_WRITING`, charged whether it wrote or errored.
    A raise adds none. Each written text is one `spec_text` fact,
    numbered on from the task's own earlier rows. `batch_spend` counts
    every attempt this round exactly once."""
    from saffron.batch import run_stack_batch
    from saffron.spec_review import WRITING_PHASE

    clock = AdvancingClock(datetime(2030, 1, 1, 2, 0))
    order, mint, reviews, revise, runner = _revision_round_arrangement(
        ledger, repo_id, clock
    )

    reason = run_stack_batch(
        order,
        ledger,
        budget_usd=100.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
        clock=clock,
        sleep=clock.sleep,
        review=reviews,
        mint=mint,
        revise=revise,
        reserve_usd=8.0,
    )

    assert reason == "INFRASTRUCTURE"

    def _attempts(spec_id: str) -> list[tuple[str, float, str]]:
        task_id = mint.tasks[spec_id]
        return [
            (a["phase"], a["cost_usd_est"], a["subtype"])
            for a in ledger.attempts(task_id)
        ]

    assert _attempts("TE-1") == [
        ("SPEC_REVIEW", 0.5, "success"),
        (WRITING_PHASE, 1.0, "success"),
        ("SPEC_REVIEW", 0.5, "success"),
        (WRITING_PHASE, 1.0, "success"),
        ("SPEC_REVIEW", 0.5, "success"),
    ]
    te1_attempts = ledger.attempts(mint.tasks["TE-1"])
    assert te1_attempts[1]["session_id"] == "w-1"
    assert te1_attempts[1]["num_turns"] == 9

    assert _attempts("TE-2") == [
        ("SPEC_REVIEW", 0.5, "success"),
        (WRITING_PHASE, 0.25, "success"),
        (WRITING_PHASE, 1.0, "success"),
        ("SPEC_REVIEW", 0.5, "success"),
        (WRITING_PHASE, 1.0, "success"),
        ("SPEC_REVIEW", 0.5, "success"),
        (WRITING_PHASE, 1.0, "success"),
        ("SPEC_REVIEW", 0.5, "success"),
    ]

    assert _attempts("TE-4") == [
        ("SPEC_REVIEW", 0.5, "success"),
        (WRITING_PHASE, 1.0, "success"),
        ("SPEC_REVIEW", 0.5, "success"),
        (WRITING_PHASE, 1.0, "success"),
        ("SPEC_REVIEW", 0.5, "success"),
        (WRITING_PHASE, 1.0, "success"),
        ("SPEC_REVIEW", 0.5, "success"),
    ]

    assert _attempts("TE-9") == [
        ("SPEC_REVIEW", 0.5, "success"),
        (WRITING_PHASE, 1.0, "success"),
        ("SPEC_REVIEW", 0.5, "success"),
        (WRITING_PHASE, 0.25, "success"),
    ]

    assert _attempts("TE-6") == [
        ("SPEC_REVIEW", 0.5, "success"),
        (WRITING_PHASE, 0.125, "error"),
    ]

    assert _attempts("TE-8") == [("SPEC_REVIEW", 0.5, "success")]

    def _state(spec_id: str) -> str:
        return _task_state(ledger, mint.tasks[spec_id])

    assert _state("TE-1") == "QUEUED"
    assert _state("TE-2") == "SPEC_WITHHELD"
    assert _state("TE-4") == "SPEC_WITHHELD"
    assert _state("TE-9") == "RATE_LIMITED"
    assert _state("TE-6") == "GATE_ERROR"
    assert _state("TE-8") == "GATE_ERROR"

    def _texts(spec_id: str) -> list[tuple[int, str, str, str]]:
        task_id = mint.tasks[spec_id]
        return [
            (row["n"], row["origin"], row["path"], row["text"])
            for row in ledger.spec_texts(task_id)
        ]

    assert _texts("TE-1") == [
        (1, "revision", ".saffron/specs/TE-1-x.md", "r1a\n"),
        (2, "revision", ".saffron/specs/TE-1-x.md", "r1b\n"),
    ]
    assert _texts("TE-2") == [
        (1, "revision", ".saffron/specs/TE-2-x.md", "r2a\n"),
        (2, "revision", ".saffron/specs/TE-2-x.md", "r2b\n"),
        (3, "revision", ".saffron/specs/TE-2-x.md", "r2c\n"),
    ]
    assert _texts("TE-4") == [
        (1, "revision", ".saffron/specs/TE-4-x.md", "r4a\n"),
        (2, "revision", ".saffron/specs/TE-4-x.md", "r4b\n"),
        (3, "revision", ".saffron/specs/TE-4-x.md", "r4c\n"),
    ]
    te5_texts = _texts("TE-5")
    assert te5_texts[:3] == [
        (1, "revision", ".saffron/specs/TE-5-x.md", "s1\n"),
        (2, "revision", ".saffron/specs/TE-5-x.md", "s2\n"),
        (3, "revision", ".saffron/specs/TE-5-x.md", "s3\n"),
    ]
    assert te5_texts[3:] == [
        (4, "revision", ".saffron/specs/TE-5-x.md", "r5a\n"),
        (5, "revision", ".saffron/specs/TE-5-x.md", "r5b\n"),
    ]
    assert _texts("TE-9") == [(1, "revision", ".saffron/specs/TE-9-x.md", "r9\n")]
    assert _texts("TE-6") == []
    assert _texts("TE-8") == []

    def _routes(spec_id: str) -> list[str]:
        return _task_routes(ledger, mint.tasks[spec_id])

    routes = {
        spec_id: _routes(spec_id)
        for spec_id in ("TE-1", "TE-2", "TE-4", "TE-5", "TE-10", "TE-9")
    }
    assert routes["TE-1"] == ["revise", "revise", "run"]
    assert routes["TE-2"] == ["revise", "revise", "revise", "escalate"]
    assert routes["TE-4"] == ["revise", "revise", "revise", "escalate"]
    assert routes["TE-5"] == ["revise", "revise", "run"]
    assert routes["TE-10"] == ["revise", "revise", "revise", "escalate"]
    assert routes["TE-9"] == ["revise", "revise"]

    assert ledger.batch_spend(ledger.latest_batch_id()) == pytest.approx(29.125)


def test_each_spec_session_attempt_records_the_model_its_session_names(ledger, repo_id):
    """`run_stack_batch` closes each `SPEC_REVIEW` attempt with its review
    session's own `model`. Each spec-writing attempt closes with its writer
    session's own `model`, a writer session that carried an error included.
    A session whose `model` is `None` writes `None` (SA-0205)."""
    from dataclasses import replace

    from saffron.batch import run_stack_batch
    from saffron.spec_review import WRITING_PHASE

    order = [_candidate_x("TE-1"), _candidate_x("TE-2")]

    review_calls: dict[str, int] = {}

    def review(candidate, layer, **kw):
        spec_id = candidate.spec.id
        review_calls[spec_id] = review_calls.get(spec_id, 0) + 1
        if spec_id == "TE-1":
            if review_calls[spec_id] == 1:
                return replace(
                    _review_session([_blocker("build")]), model="rm-1a,rm-1b"
                )
            # TE-1's second review, after its one revision below. The one
            # row this witness expects left at `None`.
            return _review_session([])
        return replace(_review_session([_blocker("build")]), model="rm-2")

    revise_table = {
        "TE-1": [replace(_written("r1\n"), model="wm-1a,wm-1b")],
        "TE-2": [replace(_writer_error("api_error"), model="wm-2")],
    }

    def revise(candidate, layer, spec_text, review_text):
        return revise_table[candidate.spec.id].pop(0)

    mint = _RevisionMint(ledger, repo_id)
    runner = _RevisionRunner(ledger, repo_id)

    reason = run_stack_batch(
        order,
        ledger,
        budget_usd=100.0,
        until=None,
        runner=runner,
        readiness_check=_ready,
        review=review,
        revise=revise,
        mint=mint,
    )
    assert reason == "DRAINED"

    def _attempts(spec_id: str) -> list[tuple[str, str | None]]:
        return [(a["phase"], a["model"]) for a in ledger.attempts(mint.tasks[spec_id])]

    # TE-1 revises once (a modeled review, a modeled writer turn) and runs
    # on a second, unmodeled review.
    assert _attempts("TE-1") == [
        ("SPEC_REVIEW", "rm-1a,rm-1b"),
        (WRITING_PHASE, "wm-1a,wm-1b"),
        ("SPEC_REVIEW", None),
    ]
    # TE-2's writer session carries an error, and its own model still
    # reaches the attempt row.
    assert _attempts("TE-2") == [
        ("SPEC_REVIEW", "rm-2"),
        (WRITING_PHASE, "wm-2"),
    ]


def test_a_stack_batch_hands_its_end_review_to_follow_ups_and_holds_the_writer_share(
    ledger, repo_id
):
    """`writer_usd` sits beside `reserve_usd`, never inside it (the stack-batch
    design's section 3, Money). Both hold back the per-task check and the pre-revision check.
    `end_review` still keeps `reserve_usd` alone, and the batch row still
    records the whole budget given. `follow_ups` runs once, right after
    `end_review`, with its return, whenever both are given, whatever the
    order's own pass stopped on. A follow-up it returns runs only once that
    pass drained. One it returns otherwise is unrun (`SA-0162`)."""
    from saffron.batch import run_stack_batch

    def _spending_runner(log: list):
        def runner(candidate, predecessor=None):
            log.append(
                (candidate.spec.id, predecessor.spec.id if predecessor else None)
            )
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
                cost_usd_est=0.5,
            )
            return _outcome(state="READY_FOR_REVIEW", run_id=run_id, task_id=task_id)

        return runner

    order = [_candidate("SY-1", budget_usd=12.0), _candidate("SY-2", budget_usd=12.25)]
    end_calls: list = []
    follow_calls: list = []
    sy90_mint = MintDouble(ledger, repo_id)
    sy90_task_id = sy90_mint(_candidate("SY-90"))

    def end_review(batch_key, reserve_usd, specs):
        end_calls.append((batch_key, reserve_usd))
        return "stack-review-sentinel"

    def follow_ups(batch_key, stack_review):
        follow_calls.append((batch_key, stack_review))
        return [dataclasses.replace(_candidate("SY-90"), task_id=sy90_task_id)]

    run_log: list = []
    lines: list[str] = []
    reason = run_stack_batch(
        order,
        ledger,
        20.0,
        None,
        _spending_runner(run_log),
        readiness_check=_ready,
        reserve_usd=3.0,
        writer_usd=4.5,
        end_review=end_review,
        follow_ups=follow_ups,
        review=_clean_run_review,
        mint=MintDouble(ledger, repo_id),
        emit=lines.append,
    )

    assert reason == "BUDGET"
    assert run_log == [("SY-1", None)]
    batch_id = _latest_batch_id(ledger)
    assert end_calls == [(str(batch_id), 3.0)]
    assert follow_calls == [(str(batch_id), "stack-review-sentinel")]
    assert _batch_row(ledger, batch_id)["budget_usd"] == 20.0
    # The order's own pass stopped `BUDGET`, not `DRAINED`, so `SY-90` is
    # never driven, reviewed, minted or run, and is unrun on that account.
    assert "follow-ups unrun  SY-90" in lines

    # With `follow_ups` given but no `end_review`, `follow_ups` never runs,
    # and the lone over-budget candidate never reaches the runner either.
    lone_log: list = []
    lone_follow: list = []

    def lone_follow_ups(batch_key, stack_review):
        lone_follow.append((batch_key, stack_review))
        return []

    for given in (lone_follow_ups, None):
        reason2 = run_stack_batch(
            [_candidate("SY-4", budget_usd=12.75)],
            ledger,
            20.0,
            None,
            _spending_runner(lone_log),
            readiness_check=_ready,
            reserve_usd=3.0,
            writer_usd=4.5,
            follow_ups=given,
            review=_clean_run_review,
            mint=MintDouble(ledger, repo_id),
        )
        assert reason2 == "BUDGET"
    assert lone_log == []
    assert lone_follow == []

    # A raise leaving the loop calls neither `end_review` nor `follow_ups`.
    raised_end: list = []
    raised_follow: list = []

    def _raising_readiness():
        raise RuntimeError("token expired")

    with pytest.raises(RuntimeError, match="token expired"):
        run_stack_batch(
            [_candidate("SY-6")],
            ledger,
            20.0,
            None,
            _spending_runner([]),
            readiness_check=_raising_readiness,
            reserve_usd=3.0,
            writer_usd=4.5,
            end_review=lambda *a: raised_end.append(a),
            follow_ups=lambda *a: raised_follow.append(a) or [],
            review=_clean_run_review,
            mint=MintDouble(ledger, repo_id),
        )
    assert raised_end == []
    assert raised_follow == []

    # `writer_usd` is held back before each round too. `need` is the
    # writer's session, the reviewer's session and the spec's own budget.
    from saffron.spec_review import SPEC_REVIEW_SESSION_USD, SPEC_WRITER_SESSION_USD

    need = SPEC_WRITER_SESSION_USD + SPEC_REVIEW_SESSION_USD + 12.0
    revision_budget = 3.0 + need + 2.0

    def _build_blocker_review(candidate, predecessor=None, **kwargs):
        return _review_session([_blocker("build")], cost=0.0)

    class _RecordingRevise:
        def __init__(self) -> None:
            self.calls = 0

        def __call__(self, candidate, predecessor, spec_text, review_text):
            self.calls += 1
            return _written(f"rev{self.calls}\n", session_id=f"w-{self.calls}")

    # `writer_usd` of 4.0 leaves `need` less 2: too little for the first
    # round, so `revise` is never called.
    revise_never = _RecordingRevise()
    reason3 = run_stack_batch(
        [_candidate_x("SY-3", budget_usd=12.0)],
        ledger,
        revision_budget,
        None,
        FakeStackRunner({}),
        readiness_check=_ready,
        reserve_usd=3.0,
        writer_usd=4.0,
        review=_build_blocker_review,
        mint=MintDouble(ledger, repo_id),
        revise=revise_never,
    )
    assert reason3 == "DRAINED"
    assert revise_never.calls == 0

    # `writer_usd` of 1.5 leaves `need` plus 0.5 for the first round, which
    # admits one `revise` call. The second round leaves `need` less 0.5.
    revise_once = _RecordingRevise()
    end_calls2: list = []
    follow_calls2: list = []
    reason4 = run_stack_batch(
        [_candidate_x("SY-3", budget_usd=12.0)],
        ledger,
        revision_budget,
        None,
        FakeStackRunner({}),
        readiness_check=_ready,
        reserve_usd=3.0,
        writer_usd=1.5,
        review=_build_blocker_review,
        mint=MintDouble(ledger, repo_id),
        revise=revise_once,
        end_review=lambda key, reserve, specs: (
            end_calls2.append((key, reserve)) or "stack-review-sentinel-2"
        ),
        follow_ups=lambda key, stack_review: (
            follow_calls2.append((key, stack_review)) or []
        ),
    )
    assert reason4 == "DRAINED"
    assert revise_once.calls == 1
    batch_id4 = _latest_batch_id(ledger)
    assert end_calls2 == [(str(batch_id4), 3.0)]
    assert follow_calls2 == [(str(batch_id4), "stack-review-sentinel-2")]


_REV_ONE = "---\nid: SY-1\ntitle: t\ntype: chore\n---\nrev one\n"
_REV_TWO = (
    "---\n"
    "id: SY-1\n"
    "title: t\n"
    "type: chore\n"
    "touches: [src/two.py]\n"
    "acceptance:\n"
    "  - claim: two holds\n"
    "    witness: tests/test_two.py::test_two\n"
    "---\n"
    "rev two\n"
)


def test_a_stack_batch_hands_its_end_review_each_revised_specs_latest_text(
    ledger, repo_id
):
    """`end_review`'s mapping reads a minted task's latest recorded text
    through `intake.parse_spec`, in place of the order's own queued `Spec`,
    for a spec that holds one. A spec whose latest text is no spec, or
    whose minted task holds no text, keeps its queued `Spec`."""
    from saffron.batch import run_stack_batch
    from saffron.intake import parse_spec

    class _TextMint(MintDouble):
        def __call__(self, candidate: Candidate) -> int:
            task_id = super().__call__(candidate)
            if candidate.spec.id == "SY-1":
                self._ledger.record_spec_text(
                    task_id,
                    origin="revision",
                    spec_id="SY-1",
                    path=".saffron/specs/SY-1.md",
                    text=_REV_ONE,
                )
                self._ledger.record_spec_text(
                    task_id,
                    origin="revision",
                    spec_id="SY-1",
                    path=".saffron/specs/SY-1.md",
                    text=_REV_TWO,
                )
            elif candidate.spec.id == "SY-3":
                self._ledger.record_spec_text(
                    task_id,
                    origin="revision",
                    spec_id="SY-3",
                    path=".saffron/specs/SY-3.md",
                    text="not a spec",
                )
            return task_id

    def _runner(candidate: Candidate, predecessor: Candidate | None = None):
        assert candidate.task_id is not None
        run_id = ledger.task_run(candidate.task_id)
        attempt_id = ledger.open_attempt(candidate.task_id, phase="IMPLEMENT")
        ledger.close_attempt(
            attempt_id,
            session_id="sess",
            subtype="success",
            terminal_reason=None,
            num_turns=1,
            cost_usd_est=1.0,
        )
        return _outcome(
            state="READY_FOR_REVIEW", run_id=run_id, task_id=candidate.task_id
        )

    order = [
        _candidate("SY-1", budget_usd=1.0),
        _candidate("SY-2", budget_usd=1.0),
        _candidate("SY-3", budget_usd=1.0),
    ]
    captured: dict = {}

    def end_review(batch_key, reserve_usd, specs):
        captured["specs"] = specs
        return None

    reason = run_stack_batch(
        order,
        ledger,
        20.0,
        None,
        _runner,
        readiness_check=_ready,
        review=lambda candidate, predecessor=None, **kw: _clean_review(),
        mint=_TextMint(ledger, repo_id),
        end_review=end_review,
    )

    assert reason == "DRAINED"
    specs = captured["specs"]
    assert set(specs) == {"SY-1", "SY-2", "SY-3"}
    assert specs["SY-1"] == parse_spec(_REV_TWO)
    assert specs["SY-1"] is not order[0].spec
    assert specs["SY-2"] is order[1].spec
    assert specs["SY-3"] is order[2].spec


# SA-0162: follow-up layers, one close, gate 0 on a follow-up and on a
# revised spec of the order. One shared arrangement drives criteria 1-6.


def _spec_text(spec_id: str, *, touches: Sequence[str] = ()) -> str:
    """A minimal parseable spec text for `StackDoubles` below: `feature`,
    a `budget_usd` of 1, and the given `touches`."""
    lines = ["---", f"id: {spec_id}", "title: t", "type: feature", "budget_usd: 1"]
    if touches:
        lines.append("touches:")
        lines += [f"  - {t}" for t in touches]
    lines += ["---", "body", ""]
    return "\n".join(lines)


def _lowest_layer_task_id(ledger: Ledger, batch_id: int) -> int:
    row = ledger._db.execute(
        "SELECT t.task_id AS task_id FROM stack_layers sl "
        "JOIN tasks t ON t.record_key = sl.task_key "
        "WHERE sl.batch_key = ? AND sl.position = 1",
        (str(batch_id),),
    ).fetchone()
    return int(row["task_id"])


class StackDoubles:
    """The one arrangement every SA-0162 witness drives: a runner, a review,
    a revise, a mint, an end review and a follow-ups double, each keyed by
    spec id against one `rows` table. `order` logs every call by a short
    tag, in the order it happened. It is shared across every double built
    with the same list, so a witness that checks interleaving, not
    membership alone, reads one list."""

    def __init__(self, ledger: Ledger, repo_id: int, rows: dict, *, order=None):
        self.ledger = ledger
        self.repo_id = repo_id
        self.rows = rows
        self.order: list[str] = order if order is not None else []
        self.runner_calls: list[tuple[str, str | None]] = []
        self.review_calls: list[tuple[str, str | None]] = []
        self.revise_calls: list[str] = []
        self.mint_calls: list[str] = []
        self._route_i: dict[str, int] = {}

    def runner(self, candidate: Candidate, predecessor: Candidate | None = None):
        spec_id = candidate.spec.id
        self.runner_calls.append(
            (spec_id, predecessor.spec.id if predecessor else None)
        )
        self.order.append(f"runner:{spec_id}")
        run_id = self.ledger.create_run(self.repo_id, base_sha="a" * 40)
        task_id = self.ledger.create_task(
            run_id,
            spec_id=spec_id,
            spec_sha=candidate.spec_sha,
            branch=f"saffron/{spec_id}-run",
        )
        attempt_id = self.ledger.open_attempt(task_id, phase="IMPLEMENT")
        self.ledger.close_attempt(
            attempt_id,
            session_id=None,
            subtype="success",
            terminal_reason=None,
            num_turns=1,
            cost_usd_est=1.0,
        )
        state = self.rows.get(spec_id, {}).get("runner", "READY_FOR_REVIEW")
        if state == "raise":
            raise RuntimeError("runner")
        self.ledger.set_task_state(task_id, state)
        return _outcome(state=state, run_id=run_id, task_id=task_id)

    def review(self, candidate: Candidate, predecessor: Candidate | None = None, **kw):
        spec_id = candidate.spec.id
        self.review_calls.append(
            (spec_id, predecessor.spec.id if predecessor else None)
        )
        self.order.append(f"review:{spec_id}")
        row = self.rows.get(spec_id, {})
        route = row.get("route", "run")
        if isinstance(route, list):
            i = self._route_i.get(spec_id, 0)
            this = route[i]
            self._route_i[spec_id] = i + 1
        else:
            this = route
        if this == "raise":
            raise RuntimeError("review")
        if this == "wait":
            return _review_session(
                [], cost=0.0, fenced=False, resets_at=row.get("resets_at")
            )
        if this == "error":
            return _review_session([], cost=0.0, fenced=False)
        if this == "escalate":
            return _review_session([_blocker("scope")], cost=0.0)
        if this == "revise":
            return _review_session([_blocker("build")], cost=0.0)
        return _review_session([], cost=0.0)

    def revise(self, candidate: Candidate, predecessor, spec_text, review_text):
        spec_id = candidate.spec.id
        self.revise_calls.append(spec_id)
        self.order.append(f"revise:{spec_id}")
        touches = self.rows.get(spec_id, {}).get("revised_touches", [])
        return _written(
            _spec_text(spec_id, touches=touches), session_id=f"w-{spec_id}", cost=0.0
        )

    def mint(self, candidate: Candidate) -> int:
        spec_id = candidate.spec.id
        self.mint_calls.append(spec_id)
        self.order.append(f"mint:{spec_id}")
        run_id = self.ledger.create_run(self.repo_id, base_sha="a" * 40)
        task_id = self.ledger.create_task(
            run_id,
            spec_id=spec_id,
            spec_sha=candidate.spec_sha,
            branch=f"saffron/{spec_id}",
        )
        follow_up_touches = self.rows.get(spec_id, {}).get("follow_up_text_touches")
        if follow_up_touches is not None:
            self.ledger.record_spec_text(
                task_id,
                origin="follow_up",
                spec_id=spec_id,
                path=f".saffron/specs/{spec_id}-f.md",
                text=_spec_text(spec_id, touches=follow_up_touches),
            )
        return task_id

    def end_review(self, batch_key: str, reserve_usd: float, specs):
        self.order.append("end_review")
        cfg = self.rows.get("__end_review__", {})
        if "on_call" in cfg:
            cfg["on_call"]()
        cost = cfg.get("cost")
        if cost is not None:
            task_id = _lowest_layer_task_id(self.ledger, int(batch_key))
            self.ledger.record_end_review(
                task_id, lens="Spec", status="reviewed", cost_usd=cost, error=None
            )
        return "stack-review-sentinel"

    def follow_ups(self, batch_key: str, stack_review) -> list[Candidate]:
        self.order.append("follow_ups")
        candidates = []
        for entry in self.rows.get("__follow_ups__", []):
            spec_id = entry["id"]
            run_id = self.ledger.create_run(self.repo_id, base_sha="a" * 40)
            task_id = self.ledger.create_task(
                run_id, spec_id=spec_id, spec_sha="f" * 64, branch=f"saffron/{spec_id}"
            )
            self.ledger.attach_run_to_batch(run_id, int(batch_key))
            touches = entry.get("touches", [])
            self.ledger.record_spec_text(
                task_id,
                origin="follow_up",
                spec_id=spec_id,
                path=f".saffron/specs/{spec_id}-f.md",
                text=_spec_text(spec_id, touches=touches),
            )
            built = dataclasses.replace(
                _candidate(
                    spec_id,
                    budget_usd=entry.get("budget_usd", 1.0),
                    priority=entry.get("priority", 1),
                ),
                task_id=task_id,
            )
            built = dataclasses.replace(
                built, spec=built.spec.model_copy(update={"touches": touches})
            )
            candidates.append(built)
        return candidates


def test_a_stack_batch_runs_its_follow_ups_on_top_as_generation_one_layers(
    ledger, repo_id
):
    """Follow-ups run after `end_review` and `follow_ups`, through the same
    wrapper as the order, once the order's own pass drains. Each is reviewed
    and run once, on the last layer, in the order `follow_ups` returned,
    never resorted. `mint` runs for every spec of the order and never for a
    follow-up. Each follow-up that reaches `READY_FOR_REVIEW` is a layer of
    generation 1, positioned after the order's own layers."""
    from saffron.batch import run_stack_batch

    rows = {
        "TE-2": {"runner": "EXHAUSTED"},
        "TE-27": {"route": "escalate"},
        "TE-35": {"runner": "EXHAUSTED"},
        "__follow_ups__": [
            {"id": "TE-31", "priority": 3},
            {"id": "TE-27", "priority": 1},
            {"id": "TE-35", "priority": 2},
            {"id": "TE-29", "priority": 1},
        ],
    }
    doubles = StackDoubles(ledger, repo_id, rows)
    order = [
        _candidate("TE-1"),
        _candidate("TE-2"),
        dataclasses.replace(_candidate("TE-3"), task_id=999),
    ]
    lines: list[str] = []

    reason = run_stack_batch(
        order,
        ledger,
        30.0,
        None,
        doubles.runner,
        readiness_check=_ready,
        reserve_usd=6.0,
        writer_usd=2.0,
        review=doubles.review,
        mint=doubles.mint,
        end_review=doubles.end_review,
        follow_ups=doubles.follow_ups,
        emit=lines.append,
    )

    assert reason == "DRAINED"
    assert doubles.runner_calls == [
        ("TE-1", None),
        ("TE-2", "TE-1"),
        ("TE-3", "TE-1"),
        ("TE-31", "TE-3"),
        ("TE-35", "TE-31"),
        ("TE-29", "TE-31"),
    ]
    assert doubles.review_calls == [
        ("TE-1", None),
        ("TE-2", "TE-1"),
        ("TE-3", "TE-1"),
        ("TE-31", "TE-3"),
        ("TE-27", "TE-31"),
        ("TE-35", "TE-31"),
        ("TE-29", "TE-31"),
    ]
    assert doubles.mint_calls == ["TE-1", "TE-2", "TE-3"]

    te3_runner_i = doubles.order.index("runner:TE-3")
    te31_review_i = doubles.order.index("review:TE-31")
    end_review_i = doubles.order.index("end_review")
    follow_ups_i = doubles.order.index("follow_ups")
    assert end_review_i > te3_runner_i
    assert follow_ups_i == end_review_i + 1
    assert follow_ups_i < te31_review_i
    assert doubles.order.count("end_review") == 1
    assert doubles.order.count("follow_ups") == 1

    layers = _stack_layers(ledger, batch_id=_latest_batch_id(ledger))
    by_key = {row["task_key"]: row for row in layers}
    got = [
        (
            row["spec_id"],
            row["position"],
            row["generation"],
            by_key[row["predecessor_key"]]["spec_id"]
            if row["predecessor_key"]
            else None,
        )
        for row in layers
    ]
    assert got == [
        ("TE-1", 1, 0, None),
        ("TE-3", 2, 0, "TE-1"),
        ("TE-31", 3, 1, "TE-3"),
        ("TE-29", 4, 1, "TE-31"),
    ]

    escalated = [line for line in lines if "escalated" in line]
    assert len(escalated) == 1
    assert escalated[0].startswith("TE-27")
    assert not any(line.startswith("follow-ups unrun") for line in lines)


def test_a_stack_batch_closes_its_row_once_after_its_follow_ups_or_their_raise(
    ledger, repo_id, monkeypatch
):
    """`run_stack_batch` checks readiness once and closes its batch row once,
    after `end_review` and `follow_ups`, with the spend both of them left
    behind included. A raise from either, or from readiness, closes the row
    `INFRASTRUCTURE` and leaves `run_stack_batch`. `follow_ups` given
    without `review` raises before any row opens, and so does `review`
    without `mint`, the existing check unchanged."""
    from saffron.batch import run_stack_batch

    log: list[str] = []
    real_close_batch = ledger.close_batch

    def _logging_close(batch_id, status):
        log.append(f"close:{status}")
        return real_close_batch(batch_id, status)

    monkeypatch.setattr(ledger, "close_batch", _logging_close)

    readiness_calls: list[int] = []

    def _counted_ready():
        readiness_calls.append(1)
        return _ready()

    # A: a follow-up runs. One close, after it, with both spends counted.
    rows_a = {"__end_review__": {"cost": 0.5}, "__follow_ups__": [{"id": "TE-72"}]}
    doubles_a = StackDoubles(ledger, repo_id, rows_a, order=log)
    reason_a = run_stack_batch(
        [_candidate("TE-71", budget_usd=1)],
        ledger,
        30.0,
        None,
        doubles_a.runner,
        readiness_check=_counted_ready,
        reserve_usd=6.0,
        writer_usd=2.0,
        review=doubles_a.review,
        mint=doubles_a.mint,
        end_review=doubles_a.end_review,
        follow_ups=doubles_a.follow_ups,
    )
    assert reason_a == "DRAINED"
    assert log[-2:] == ["runner:TE-72", "close:DRAINED"]
    batch_id_a = _latest_batch_id(ledger)
    assert ledger.batch_spend(batch_id_a) == 2.5
    assert len(readiness_calls) == 1

    # B: `follow_ups` of `None`. One close, after `end_review` alone.
    rows_b = {"__end_review__": {"cost": 0.5}}
    doubles_b = StackDoubles(ledger, repo_id, rows_b, order=log)
    reason_b = run_stack_batch(
        [_candidate("TE-73", budget_usd=1)],
        ledger,
        30.0,
        None,
        doubles_b.runner,
        readiness_check=_ready,
        reserve_usd=6.0,
        writer_usd=2.0,
        review=doubles_b.review,
        mint=doubles_b.mint,
        end_review=doubles_b.end_review,
    )
    assert reason_b == "DRAINED"
    assert log[-2:] == ["end_review", "close:DRAINED"]
    batch_id_b = _latest_batch_id(ledger)
    assert ledger.batch_spend(batch_id_b) == 1.5

    # C: generation 0 drains, so only the follow-up's own stop can say `BUDGET`.
    rows_c = {"__follow_ups__": [{"id": "TE-75", "budget_usd": 40}]}
    doubles_c = StackDoubles(ledger, repo_id, rows_c, order=log)
    reason_c = run_stack_batch(
        [_candidate("TE-74", budget_usd=1)],
        ledger,
        30.0,
        None,
        doubles_c.runner,
        readiness_check=_ready,
        reserve_usd=6.0,
        writer_usd=2.0,
        review=doubles_c.review,
        mint=doubles_c.mint,
        end_review=doubles_c.end_review,
        follow_ups=doubles_c.follow_ups,
    )
    assert reason_c == "BUDGET"
    assert "runner:TE-74" in log
    assert "runner:TE-75" not in log
    batch_id_c = _latest_batch_id(ledger)
    assert _batch_row(ledger, batch_id_c)["status"] == "BUDGET"

    # D: three raises, each closing `INFRASTRUCTURE`, logging nothing else.
    def _raising_end_review(*a, **kw):
        raise RuntimeError("end_review")

    doubles_d1 = StackDoubles(ledger, repo_id, {}, order=log)
    with pytest.raises(RuntimeError, match=r"^end_review$"):
        run_stack_batch(
            [_candidate("TE-76")],
            ledger,
            30.0,
            None,
            doubles_d1.runner,
            readiness_check=_ready,
            reserve_usd=6.0,
            writer_usd=2.0,
            review=doubles_d1.review,
            mint=doubles_d1.mint,
            end_review=_raising_end_review,
        )
    batch_id_d1 = _latest_batch_id(ledger)
    assert _batch_row(ledger, batch_id_d1)["status"] == "INFRASTRUCTURE"
    assert _batch_row(ledger, batch_id_d1)["ended_at"] is not None

    def _raising_follow_ups(*a, **kw):
        raise RuntimeError("follow_ups")

    doubles_d2 = StackDoubles(ledger, repo_id, {"__end_review__": {}}, order=log)
    with pytest.raises(RuntimeError, match=r"^follow_ups$"):
        run_stack_batch(
            [_candidate("TE-77")],
            ledger,
            30.0,
            None,
            doubles_d2.runner,
            readiness_check=_ready,
            reserve_usd=6.0,
            writer_usd=2.0,
            review=doubles_d2.review,
            mint=doubles_d2.mint,
            end_review=doubles_d2.end_review,
            follow_ups=_raising_follow_ups,
        )
    batch_id_d2 = _latest_batch_id(ledger)
    assert _batch_row(ledger, batch_id_d2)["status"] == "INFRASTRUCTURE"

    def _raising_readiness():
        raise RuntimeError("readiness")

    before_d3 = len(log)
    doubles_d3 = StackDoubles(ledger, repo_id, {}, order=log)
    with pytest.raises(RuntimeError, match=r"^readiness$"):
        run_stack_batch(
            [_candidate("TE-78")],
            ledger,
            30.0,
            None,
            doubles_d3.runner,
            readiness_check=_raising_readiness,
            reserve_usd=6.0,
            writer_usd=2.0,
            review=doubles_d3.review,
            mint=doubles_d3.mint,
        )
    batch_id_d3 = _latest_batch_id(ledger)
    assert _batch_row(ledger, batch_id_d3)["status"] == "INFRASTRUCTURE"
    assert log[before_d3:] == ["close:INFRASTRUCTURE"]

    # E: `follow_ups` without `review` raises, with `mint` alone or with
    # neither. `review` without `mint` keeps its own unchanged message.
    before_count = ledger._db.execute("SELECT COUNT(*) AS n FROM batches").fetchone()[
        "n"
    ]
    before_e = len(log)
    doubles_e = StackDoubles(ledger, repo_id, {"__end_review__": {}}, order=log)
    with pytest.raises(ValueError, match="follow_ups"):
        run_stack_batch(
            [_candidate("TE-791")],
            ledger,
            30.0,
            None,
            doubles_e.runner,
            readiness_check=_ready,
            end_review=doubles_e.end_review,
            follow_ups=doubles_e.follow_ups,
        )
    with pytest.raises(ValueError, match="follow_ups"):
        run_stack_batch(
            [_candidate("TE-792")],
            ledger,
            30.0,
            None,
            doubles_e.runner,
            readiness_check=_ready,
            mint=doubles_e.mint,
            end_review=doubles_e.end_review,
            follow_ups=doubles_e.follow_ups,
        )
    with pytest.raises(ValueError, match="needs mint whenever review is given"):
        run_stack_batch(
            [_candidate("TE-793")],
            ledger,
            30.0,
            None,
            doubles_e.runner,
            readiness_check=_ready,
            review=doubles_e.review,
            end_review=doubles_e.end_review,
            follow_ups=doubles_e.follow_ups,
        )
    after_count = ledger._db.execute("SELECT COUNT(*) AS n FROM batches").fetchone()[
        "n"
    ]
    assert after_count == before_count
    assert log[before_e:] == []


def _pr(number: int, branch: str, path: str) -> dict:
    return {
        "number": number,
        "headRefName": branch,
        "url": f"https://example.invalid/pull/{number}",
        "files": [{"path": path}],
    }


def test_a_follow_up_meets_gate_0_with_only_this_batchs_layers_exempt(ledger, repo_id):
    """`open_prs` is called once, right after `follow_ups` returns at least
    one follow-up to run. Each follow-up then meets gate 0's own refusals
    before its review. Exempt only for its own branch and this batch's own
    recorded layers, either generation. A refused follow-up is never
    reviewed or run, adds no layer, counts as no abort, and is named on the
    unrun line."""
    from saffron.batch import run_stack_batch

    pull_requests = [
        _pr(1, "saffron/TE-81", "a.py"),
        _pr(2, "saffron/TE-82", "b.py"),
        _pr(3, "saffron/TE-83", "c.py"),
        _pr(4, "saffron/SA-9000", "d.py"),
        _pr(5, "saffron/TE-79", "e.py"),
        _pr(6, "saffron/TE-91", "a.py"),
    ]
    open_pr_log: list[int] = []

    def open_prs(doubles) -> list[dict]:
        open_pr_log.append(len(doubles.order))
        return pull_requests

    # An earlier batch: TE-79 alone, ready. Its `follow_ups` returns no
    # candidate, so `open_prs` is never reached.
    doubles0 = StackDoubles(ledger, repo_id, {"__follow_ups__": []})
    reason0 = run_stack_batch(
        [_candidate("TE-79", budget_usd=1)],
        ledger,
        30.0,
        None,
        doubles0.runner,
        readiness_check=_ready,
        reserve_usd=6.0,
        writer_usd=2.0,
        review=doubles0.review,
        mint=doubles0.mint,
        end_review=doubles0.end_review,
        follow_ups=doubles0.follow_ups,
        open_prs=lambda: open_prs(doubles0),
    )
    assert reason0 == "DRAINED"
    assert open_pr_log == []

    rows = {
        "TE-82": {"runner": "MERGE_FAILED"},
        "__follow_ups__": [
            {"id": "TE-91", "touches": ["a.py"]},
            {"id": "TE-96", "touches": ["e.py"]},
            {"id": "TE-92", "touches": ["b.py"]},
            {"id": "TE-93", "touches": ["d.py"]},
            {"id": "TE-94", "touches": ["c.py"]},
        ],
    }
    doubles = StackDoubles(ledger, repo_id, rows)
    order = [
        _candidate("TE-81", budget_usd=1),
        _candidate("TE-82", budget_usd=1),
        _candidate("TE-83", budget_usd=1),
    ]
    lines: list[str] = []

    reason = run_stack_batch(
        order,
        ledger,
        30.0,
        None,
        doubles.runner,
        readiness_check=_ready,
        reserve_usd=6.0,
        writer_usd=2.0,
        review=doubles.review,
        mint=doubles.mint,
        end_review=doubles.end_review,
        follow_ups=doubles.follow_ups,
        open_prs=lambda: open_prs(doubles),
        emit=lines.append,
    )

    assert reason == "DRAINED"
    follow_up_runner_pairs = [
        pair
        for pair in doubles.runner_calls
        if pair[0] not in ("TE-81", "TE-82", "TE-83")
    ]
    assert follow_up_runner_pairs == [("TE-91", "TE-83"), ("TE-94", "TE-91")]
    follow_up_review_ids = [
        sid
        for sid, _pred in doubles.review_calls
        if sid not in ("TE-81", "TE-82", "TE-83")
    ]
    assert follow_up_review_ids == ["TE-91", "TE-94"]

    refused = {
        line.split()[0]: line
        for line in lines
        if "refused" in line and "/pull/" in line
    }
    assert set(refused) == {"TE-96", "TE-92", "TE-93"}
    assert "/pull/5" in refused["TE-96"]
    assert "/pull/2" in refused["TE-92"]
    assert "/pull/4" in refused["TE-93"]

    assert "follow-ups unrun  TE-96 TE-92 TE-93" in lines
    # Called once, right after `follow_ups`, which is the log's own last
    # entry at that moment.
    assert len(open_pr_log) == 1
    assert doubles.order[open_pr_log[0] - 1] == "follow_ups"


def test_a_revised_spec_meets_gate_0s_open_pull_request_refusals_before_its_cell(
    ledger, repo_id, monkeypatch
):
    """A spec of the order whose latest `spec_texts` row is a revision meets
    gate 0's open-pull-request refusals again, on that text's `touches`.
    This happens once its review routes `run`, exempt for this batch's own
    recorded layers. An unrevised spec, and one whose latest text is a
    `follow_up`, meet no check. `open_prs` is read fresh for each one
    checked."""
    from saffron import spec_review as spec_review_module
    from saffron.batch import run_stack_batch

    monkeypatch.setattr(spec_review_module, "SPEC_WRITER_SESSION_USD", 1.0)
    monkeypatch.setattr(spec_review_module, "SPEC_REVIEW_SESSION_USD", 1.0)

    pull_requests = [
        _pr(1, "saffron/TE-141", "a.py"),
        _pr(2, "saffron/TE-142", "b.py"),
        _pr(3, "saffron/SA-9000", "d.py"),
    ]
    open_pr_log: list[int] = []

    rows = {
        "TE-142": {"runner": "MERGE_FAILED"},
        "TE-143": {"route": ["revise", "run"], "revised_touches": ["m.py", "n.py"]},
        "TE-144": {"route": ["revise", "run"], "revised_touches": ["m.py", "b.py"]},
        "TE-145": {"route": ["revise", "run"], "revised_touches": ["m.py", "d.py"]},
        "TE-147": {"route": ["revise", "run"], "revised_touches": ["m.py", "a.py"]},
        "TE-148": {"follow_up_text_touches": ["m.py", "d.py"]},
    }
    doubles = StackDoubles(ledger, repo_id, rows)

    def open_prs() -> list[dict]:
        open_pr_log.append(len(doubles.order))
        return pull_requests

    # `TE-146` touches only `d.py`, so checking an unrevised spec refuses it.
    order = [
        dataclasses.replace(
            c,
            spec=c.spec.model_copy(
                update={"touches": ["d.py"] if c.spec.id == "TE-146" else ["m.py"]}
            ),
        )
        for c in (_candidate(f"TE-14{n}", budget_usd=1) for n in range(1, 9))
    ]
    lines: list[str] = []

    reason = run_stack_batch(
        order,
        ledger,
        30.0,
        None,
        doubles.runner,
        readiness_check=_ready,
        reserve_usd=6.0,
        writer_usd=2.0,
        review=doubles.review,
        mint=doubles.mint,
        revise=doubles.revise,
        open_prs=open_prs,
        emit=lines.append,
    )

    assert reason == "DRAINED"
    assert doubles.runner_calls == [
        ("TE-141", None),
        ("TE-142", "TE-141"),
        ("TE-143", "TE-141"),
        ("TE-146", "TE-143"),
        ("TE-147", "TE-146"),
        ("TE-148", "TE-147"),
    ]
    assert doubles.revise_calls == ["TE-143", "TE-144", "TE-145", "TE-147"]

    refused = {
        line.split()[0]: line
        for line in lines
        if "refused" in line and "/pull/" in line
    }
    assert set(refused) == {"TE-144", "TE-145"}
    assert "/pull/2" in refused["TE-144"]
    assert "/pull/3" in refused["TE-145"]

    layers = _stack_layers(ledger, batch_id=_latest_batch_id(ledger))
    assert [row["spec_id"] for row in layers] == [
        "TE-141",
        "TE-143",
        "TE-146",
        "TE-147",
        "TE-148",
    ]
    assert len(open_pr_log) == 4
    # Each read comes right after that spec's last review, never earlier.
    for at, spec_id in zip(
        open_pr_log, ["TE-143", "TE-144", "TE-145", "TE-147"], strict=True
    ):
        assert doubles.order[at - 1] == f"review:{spec_id}"


def _fail_sleep(seconds: float) -> None:
    raise AssertionError(f"should not sleep for {seconds}")


def test_a_follow_up_meets_until_the_budget_and_the_breaker_as_any_task_does(
    ledger, repo_id, monkeypatch
):
    """Follow-ups run only when generation 0's loop drained. Before each
    follow-up the batch checks `--until`, the budget and the breaker, as it
    does for a spec of the order. Neither `reserve_usd` nor `writer_usd` is
    held back. The breaker's count and the in-flight list carry over from
    generation 0. A follow-up the batch stops before is unrun. So is one
    whose review raised, routed `error`, or waited before the batch
    stopped. One whose review waited and then routed `run` is not."""
    from saffron import spec_review as spec_review_module
    from saffron.batch import run_stack_batch

    # Batch 1: the reserve and the writer's share are released for a
    # follow-up that needed them.
    rows1 = {
        "__end_review__": {"cost": 3.0},
        "__follow_ups__": [{"id": "TE-42", "budget_usd": 25}],
    }
    doubles1 = StackDoubles(ledger, repo_id, rows1)
    reason1 = run_stack_batch(
        [_candidate("TE-41", budget_usd=5)],
        ledger,
        30.0,
        None,
        doubles1.runner,
        readiness_check=_ready,
        reserve_usd=6.0,
        writer_usd=2.0,
        review=doubles1.review,
        mint=doubles1.mint,
        end_review=doubles1.end_review,
        follow_ups=doubles1.follow_ups,
        sleep=_fail_sleep,
    )
    assert reason1 == "DRAINED"
    assert doubles1.runner_calls == [("TE-41", None), ("TE-42", "TE-41")]

    # Batch 2: the follow-up loop's own budget check, past the order's.
    open_pr_calls2: list[int] = []

    def _open_prs2() -> list[dict]:
        open_pr_calls2.append(1)
        return [_pr(7, "saffron/SA-9001", "x.py")]

    rows2 = {
        "__end_review__": {"cost": 3.0},
        "__follow_ups__": [
            {"id": "TE-44", "budget_usd": 27, "touches": ["y.py"]},
            {"id": "TE-40", "budget_usd": 1, "touches": ["x.py"]},
        ],
    }
    doubles2 = StackDoubles(ledger, repo_id, rows2)
    lines2: list[str] = []
    reason2 = run_stack_batch(
        [_candidate("TE-43", budget_usd=5)],
        ledger,
        30.0,
        None,
        doubles2.runner,
        readiness_check=_ready,
        reserve_usd=6.0,
        writer_usd=2.0,
        review=doubles2.review,
        mint=doubles2.mint,
        end_review=doubles2.end_review,
        follow_ups=doubles2.follow_ups,
        open_prs=_open_prs2,
        sleep=_fail_sleep,
        emit=lines2.append,
    )
    assert reason2 == "BUDGET"
    assert doubles2.runner_calls == [("TE-43", None)]
    assert len(open_pr_calls2) == 1
    assert not any("refused" in line for line in lines2)
    assert "follow-ups unrun  TE-44 TE-40" in lines2

    # Batch 3: the order's own pass stopped `BUDGET`, so the follow-up
    # `follow_ups` returns is never driven, and is unrun on that account.
    rows3 = {"__follow_ups__": [{"id": "TE-47", "budget_usd": 1}]}
    doubles3 = StackDoubles(ledger, repo_id, rows3)
    lines3: list[str] = []
    reason3 = run_stack_batch(
        [_candidate("TE-45", budget_usd=5), _candidate("TE-46", budget_usd=24)],
        ledger,
        30.0,
        None,
        doubles3.runner,
        readiness_check=_ready,
        reserve_usd=6.0,
        writer_usd=2.0,
        review=doubles3.review,
        mint=doubles3.mint,
        end_review=doubles3.end_review,
        follow_ups=doubles3.follow_ups,
        sleep=_fail_sleep,
        emit=lines3.append,
    )
    assert reason3 == "BUDGET"
    assert doubles3.runner_calls == [("TE-45", None)]
    assert "follow-ups unrun  TE-47" in lines3

    # Batch 4: the end review moves the clock past `--until`, so the
    # follow-up it returns meets the same deadline check and is unrun.
    start4 = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    until4 = start4 + timedelta(hours=1)
    clock4 = AdvancingClock(start4)

    def _move_clock_past_until() -> None:
        clock4.advance((until4 + timedelta(minutes=1) - clock4()).total_seconds())

    open_pr_calls4: list[int] = []

    def _open_prs4() -> list[dict]:
        open_pr_calls4.append(1)
        return [_pr(7, "saffron/SA-9001", "x.py")]

    rows4 = {
        "__end_review__": {"on_call": _move_clock_past_until},
        "__follow_ups__": [{"id": "TE-49", "budget_usd": 1, "touches": ["x.py"]}],
    }
    doubles4 = StackDoubles(ledger, repo_id, rows4)
    lines4: list[str] = []
    reason4 = run_stack_batch(
        [_candidate("TE-48", budget_usd=5)],
        ledger,
        30.0,
        until4,
        doubles4.runner,
        readiness_check=_ready,
        reserve_usd=6.0,
        writer_usd=2.0,
        review=doubles4.review,
        mint=doubles4.mint,
        end_review=doubles4.end_review,
        follow_ups=doubles4.follow_ups,
        open_prs=_open_prs4,
        clock=clock4,
        sleep=_fail_sleep,
        emit=lines4.append,
    )
    assert reason4 == "UNTIL"
    assert doubles4.runner_calls == [("TE-48", None)]
    assert len(open_pr_calls4) == 1
    assert not any("refused" in line for line in lines4)
    assert "follow-ups unrun  TE-49" in lines4

    # Batch 5: the breaker's own count carries over, and fires before the
    # follow-up on `x.py` is ever reached.
    open_pr_calls5: list[int] = []

    def _open_prs5() -> list[dict]:
        open_pr_calls5.append(1)
        return [_pr(7, "saffron/SA-9001", "x.py")]

    rows5 = {
        "TE-52": {"runner": "GATE_ERROR"},
        "TE-53": {"runner": "GATE_ERROR"},
        "__end_review__": {},
        "__follow_ups__": [
            {"id": "TE-53", "budget_usd": 1, "touches": ["y.py"]},
            {"id": "TE-54", "budget_usd": 1, "touches": ["x.py"]},
        ],
    }
    doubles5 = StackDoubles(ledger, repo_id, rows5)
    lines5: list[str] = []
    reason5 = run_stack_batch(
        [_candidate("TE-51", budget_usd=1), _candidate("TE-52", budget_usd=1)],
        ledger,
        30.0,
        None,
        doubles5.runner,
        readiness_check=_ready,
        reserve_usd=6.0,
        writer_usd=2.0,
        review=doubles5.review,
        mint=doubles5.mint,
        end_review=doubles5.end_review,
        follow_ups=doubles5.follow_ups,
        open_prs=_open_prs5,
        sleep=_fail_sleep,
        emit=lines5.append,
    )
    assert reason5 == "INFRASTRUCTURE"
    assert doubles5.runner_calls == [
        ("TE-51", None),
        ("TE-52", "TE-51"),
        ("TE-53", "TE-51"),
    ]
    assert len(open_pr_calls5) == 1
    assert "follow-ups unrun  TE-54" in lines5

    # Batch 6: the in-flight list carries over, turning a clean drain of
    # both passes into `INCOMPLETE`.
    rows6 = {
        "TE-62": {"runner": "REVIEWING"},
        "__end_review__": {},
        "__follow_ups__": [{"id": "TE-63", "budget_usd": 1}],
    }
    doubles6 = StackDoubles(ledger, repo_id, rows6)
    lines6: list[str] = []
    reason6 = run_stack_batch(
        [_candidate("TE-61", budget_usd=1), _candidate("TE-62", budget_usd=1)],
        ledger,
        30.0,
        None,
        doubles6.runner,
        readiness_check=_ready,
        reserve_usd=6.0,
        writer_usd=2.0,
        review=doubles6.review,
        mint=doubles6.mint,
        end_review=doubles6.end_review,
        follow_ups=doubles6.follow_ups,
        sleep=_fail_sleep,
        emit=lines6.append,
    )
    assert reason6 == "INCOMPLETE"
    assert doubles6.runner_calls == [
        ("TE-61", None),
        ("TE-62", "TE-61"),
        ("TE-63", "TE-61"),
    ]
    assert not any(line.startswith("follow-ups unrun") for line in lines6)
    assert any(line.startswith("TE-62") and "in flight" in line for line in lines6)

    # Batch 7: a revision's own check holds `reserve_usd` and `writer_usd`
    # for a spec of the order, and holds neither for a follow-up's.
    monkeypatch.setattr(spec_review_module, "SPEC_WRITER_SESSION_USD", 10.0)
    monkeypatch.setattr(spec_review_module, "SPEC_REVIEW_SESSION_USD", 8.0)
    rows7 = {
        "TE-103": {"route": "revise", "revised_touches": []},
        "TE-102": {"route": ["revise", "run"], "revised_touches": []},
        "__end_review__": {},
        "__follow_ups__": [{"id": "TE-102", "budget_usd": 10}],
    }
    doubles7 = StackDoubles(ledger, repo_id, rows7)
    lines7: list[str] = []
    reason7 = run_stack_batch(
        [
            _candidate("TE-101", budget_usd=1),
            dataclasses.replace(_candidate("TE-103", budget_usd=4), task_id=424242),
        ],
        ledger,
        30.0,
        None,
        doubles7.runner,
        readiness_check=_ready,
        reserve_usd=6.0,
        writer_usd=2.0,
        review=doubles7.review,
        mint=doubles7.mint,
        revise=doubles7.revise,
        end_review=doubles7.end_review,
        follow_ups=doubles7.follow_ups,
        sleep=_fail_sleep,
        emit=lines7.append,
    )
    assert reason7 == "DRAINED"
    assert doubles7.runner_calls == [("TE-101", None), ("TE-102", "TE-101")]
    assert doubles7.revise_calls == ["TE-102"]
    assert any(line.startswith("TE-103") and "unrevised" in line for line in lines7)
    assert not any(line.startswith("follow-ups unrun") for line in lines7)

    # Batch 8: a follow-up's own wait meets `--until` exactly as a task's
    # own `RATE_LIMITED` wait does (`SA-0148`).
    start8 = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    until8 = start8 + timedelta(hours=1)
    resets_at8 = int((start8 + timedelta(hours=2)).timestamp())
    rows8 = {
        "TE-112": {"route": "wait", "resets_at": resets_at8},
        "__end_review__": {},
        "__follow_ups__": [{"id": "TE-112", "budget_usd": 1}],
    }
    doubles8 = StackDoubles(ledger, repo_id, rows8)
    sleep_calls8: list[float] = []
    lines8: list[str] = []
    reason8 = run_stack_batch(
        [_candidate("TE-111", budget_usd=1)],
        ledger,
        30.0,
        until8,
        doubles8.runner,
        readiness_check=_ready,
        reserve_usd=6.0,
        writer_usd=2.0,
        review=doubles8.review,
        mint=doubles8.mint,
        end_review=doubles8.end_review,
        follow_ups=doubles8.follow_ups,
        clock=lambda: start8,
        sleep=sleep_calls8.append,
        emit=lines8.append,
    )
    assert reason8 == "UNTIL"
    assert doubles8.runner_calls == [("TE-111", None)]
    assert sleep_calls8 == []
    assert "follow-ups unrun  TE-112" in lines8

    # Batch 9: a raise, a clean `error` route, and a wait that retries into
    # `run` each settle the breaker and the unrun line their own way.
    start9 = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    until9 = start9 + timedelta(hours=1)
    resets_at9 = int((start9 + timedelta(minutes=10)).timestamp())
    clock9 = AdvancingClock(start9)
    rows9 = {
        "TE-122": {"route": "raise"},
        "TE-123": {"route": "error"},
        "TE-126": {"runner": "raise"},
        "TE-127": {"route": ["wait", "run"], "resets_at": resets_at9},
        "__end_review__": {},
        "__follow_ups__": [
            {"id": "TE-122", "budget_usd": 1},
            {"id": "TE-124", "budget_usd": 1},
            {"id": "TE-123", "budget_usd": 1},
            {"id": "TE-125", "budget_usd": 1},
            {"id": "TE-126", "budget_usd": 1},
            {"id": "TE-127", "budget_usd": 1},
        ],
    }
    doubles9 = StackDoubles(ledger, repo_id, rows9)
    lines9: list[str] = []
    reason9 = run_stack_batch(
        [_candidate("TE-121", budget_usd=1)],
        ledger,
        30.0,
        until9,
        doubles9.runner,
        readiness_check=_ready,
        reserve_usd=6.0,
        writer_usd=2.0,
        review=doubles9.review,
        mint=doubles9.mint,
        end_review=doubles9.end_review,
        follow_ups=doubles9.follow_ups,
        clock=clock9,
        sleep=clock9.sleep,
        emit=lines9.append,
    )
    assert reason9 == "DRAINED"
    assert doubles9.runner_calls == [
        ("TE-121", None),
        ("TE-124", "TE-121"),
        ("TE-125", "TE-124"),
        ("TE-126", "TE-125"),
        ("TE-127", "TE-125"),
    ]
    assert len(clock9.sleeps) == 1
    assert any(
        line.startswith("TE-122") and "RuntimeError: review" in line for line in lines9
    )
    assert any(line.startswith("TE-123") and "unreviewed" in line for line in lines9)
    assert any(
        line.startswith("TE-126") and "RuntimeError: runner" in line for line in lines9
    )
    assert "follow-ups unrun  TE-122 TE-123" in lines9


def test_the_finish_runs_once_after_the_follow_ups_while_the_batch_row_is_open(
    ledger, repo_id
):
    """`finish` runs once, after the follow-ups, while the batch row is open.
    It carries the task ids of every follow-up whose review never reached a
    route (ADR 7, `SA-0151`). Driven across five nights: `UNTIL` mid
    follow-up, a drain with no follow-ups offered, a `BUDGET` stop before
    any candidate starts, and two drains with `follow_ups` then `end_review`
    left out."""
    from saffron.batch import run_stack_batch

    finish_calls: list[tuple[int, list[int]]] = []
    status_at_call: list[tuple[object, object]] = []
    # Each night's id must be that night's own batch, as an `int`.
    id_is_this_batch: list[bool] = []

    def finish(batch_id, unrun, /):
        id_is_this_batch.append(
            type(batch_id) is int and batch_id == _latest_batch_id(ledger)
        )
        row = ledger._db.execute(
            "SELECT status, ended_at FROM batches WHERE batch_id = ?", (batch_id,)
        ).fetchone()
        status_at_call.append((row["status"], row["ended_at"]))
        finish_calls.append((batch_id, list(unrun)))

    # Night 1: `UNTIL` fires mid follow-up, at task 44's wait.
    start1 = datetime(2026, 1, 1, tzinfo=UTC)
    until1 = start1 + timedelta(seconds=30)

    def _no_sleep(seconds):
        raise AssertionError("sleep must not be called")

    label_task_ids: dict[str, int] = {}

    def follow_ups1(batch_key, stack_review):
        for label in range(40, 49):
            spec_id = f"TE-{label}"
            run_id = ledger.create_run(
                repo_id, base_sha="a" * 40, batch_id=int(batch_key)
            )
            task_id = ledger.create_task(
                run_id, spec_id=spec_id, spec_sha="f" * 64, branch=f"saffron/{spec_id}"
            )
            label_task_ids[spec_id] = task_id
        built = []
        for label in (40, 41, 42, 48, 43, 46, 47, 44, 45):
            spec_id = f"TE-{label}"
            touches = ["f41.py"] if label == 41 else []
            candidate = dataclasses.replace(
                _candidate(spec_id, budget_usd=1.0, priority=1),
                task_id=label_task_ids[spec_id],
            )
            candidate = dataclasses.replace(
                candidate, spec=candidate.spec.model_copy(update={"touches": touches})
            )
            built.append(candidate)
        return built

    def _open_prs():
        return [{"headRefName": "some/other-branch", "files": [{"path": "f41.py"}]}]

    rows1 = {
        "TE-42": {"route": "escalate"},
        "TE-48": {"route": "raise"},
        "TE-43": {"runner": "EXHAUSTED"},
        "TE-46": {"route": "error"},
        "TE-44": {
            "route": "wait",
            "resets_at": int((start1 + timedelta(minutes=10)).timestamp()),
        },
    }
    doubles1 = StackDoubles(ledger, repo_id, rows1)

    def runner1(candidate, predecessor=None):
        if candidate.spec.id == "TE-47":
            return Refused(reason="gate 0 refused")
        return doubles1.runner(candidate, predecessor)

    reason1 = run_stack_batch(
        [_candidate("SP-1", budget_usd=1.0)],
        ledger,
        1000.0,
        until1,
        runner1,
        readiness_check=_ready,
        clock=lambda: start1,
        emit=lambda line: None,
        review=doubles1.review,
        mint=doubles1.mint,
        sleep=_no_sleep,
        end_review=doubles1.end_review,
        follow_ups=follow_ups1,
        open_prs=_open_prs,
        finish=finish,
    )
    assert reason1 == "UNTIL"
    assert (
        label_task_ids["TE-40"]
        < label_task_ids["TE-41"]
        < label_task_ids["TE-42"]
        < label_task_ids["TE-43"]
        < label_task_ids["TE-44"]
        < label_task_ids["TE-45"]
        < label_task_ids["TE-46"]
        < label_task_ids["TE-47"]
        < label_task_ids["TE-48"]
    )
    assert len(finish_calls) == 1
    batch_id_1, unrun_1 = finish_calls[0]
    assert unrun_1 == [
        label_task_ids["TE-41"],
        label_task_ids["TE-48"],
        label_task_ids["TE-46"],
        label_task_ids["TE-44"],
        label_task_ids["TE-45"],
    ]
    assert unrun_1 != sorted(unrun_1)
    assert status_at_call[0] == (None, None)
    closed = ledger._db.execute(
        "SELECT status FROM batches WHERE batch_id = ?", (batch_id_1,)
    ).fetchone()
    assert closed["status"] == "UNTIL"

    # Night 2: drains, and its own `follow_ups` offers nothing.
    doubles0 = StackDoubles(ledger, repo_id, {})
    reason2 = run_stack_batch(
        [_candidate("SP-2", budget_usd=1.0)],
        ledger,
        1000.0,
        None,
        doubles0.runner,
        readiness_check=_ready,
        review=doubles0.review,
        mint=doubles0.mint,
        end_review=doubles0.end_review,
        follow_ups=lambda batch_key, stack_review: [],
        finish=finish,
    )
    assert reason2 == "DRAINED"
    assert len(finish_calls) == 2
    assert finish_calls[1][1] == []

    # Night 3: `BUDGET` fires before the order's own spec ever starts. Its
    # `follow_ups` still runs and offers one follow-up, never driven.
    task60: dict[str, int] = {}

    def follow_ups3(batch_key, stack_review):
        run_id = ledger.create_run(repo_id, base_sha="a" * 40, batch_id=int(batch_key))
        task_id = ledger.create_task(
            run_id, spec_id="TE-60", spec_sha="f" * 64, branch="saffron/TE-60"
        )
        task60["id"] = task_id
        built = dataclasses.replace(
            _candidate("TE-60", budget_usd=1.0), task_id=task_id
        )
        return [built]

    reason3 = run_stack_batch(
        [_candidate("SP-3", budget_usd=100.0)],
        ledger,
        10.0,
        None,
        doubles0.runner,
        readiness_check=_ready,
        review=doubles0.review,
        mint=doubles0.mint,
        end_review=doubles0.end_review,
        follow_ups=follow_ups3,
        finish=finish,
    )
    assert reason3 == "BUDGET"
    assert len(finish_calls) == 3
    assert finish_calls[2][1] == [task60["id"]]

    # Night 4: drains, given `end_review` and no `follow_ups`.
    reason4 = run_stack_batch(
        [_candidate("SP-4", budget_usd=1.0)],
        ledger,
        1000.0,
        None,
        doubles0.runner,
        readiness_check=_ready,
        review=doubles0.review,
        mint=doubles0.mint,
        end_review=doubles0.end_review,
        follow_ups=None,
        finish=finish,
    )
    assert reason4 == "DRAINED"
    assert len(finish_calls) == 4
    assert finish_calls[3][1] == []

    # Night 5: drains, given neither.
    reason5 = run_stack_batch(
        [_candidate("SP-5", budget_usd=1.0)],
        ledger,
        1000.0,
        None,
        doubles0.runner,
        readiness_check=_ready,
        review=doubles0.review,
        mint=doubles0.mint,
        end_review=None,
        follow_ups=None,
        finish=finish,
    )
    assert reason5 == "DRAINED"
    assert len(finish_calls) == 5
    assert finish_calls[4][1] == []
    assert id_is_this_batch == [True] * 5
