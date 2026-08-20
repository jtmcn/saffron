from __future__ import annotations

import json

import pytest

from saffron.agents import artifacts
from saffron.cell import session
from saffron.gates.baseline import NewFailure
from saffron.gates.contract import Failure, GateResult
from saffron.ledger import Ledger
from saffron.phases import implement


def _failure(gate, file, code, message="m"):
    return NewFailure(gate, Failure(file=file, code=code, message=message))


def test_the_loop_stops_when_there_are_no_new_failures():
    decision = session.repair_decision(attempt=1, max_attempts=4, new=[], previous=[])
    assert decision == "green"


def test_the_loop_stops_on_no_progress():
    same = [_failure("lint", "a.py", "E501")]
    decision = session.repair_decision(
        attempt=2, max_attempts=4, new=same, previous=same
    )
    assert decision == "no-progress"


def test_fixing_three_of_four_colliding_failures_is_progress():
    """Counted, not set-compared — §5.4."""
    previous = [_failure("lint", "a.py", "E501") for _ in range(4)]
    current = [_failure("lint", "a.py", "E501")]
    decision = session.repair_decision(
        attempt=2, max_attempts=4, new=current, previous=previous
    )
    assert decision == "repair"


def test_the_loop_exhausts_at_max_attempts():
    new = [_failure("lint", "a.py", "E501")]
    decision = session.repair_decision(attempt=4, max_attempts=4, new=new, previous=[])
    assert decision == "exhausted"


def test_an_errored_gate_aborts_rather_than_counting_against_the_task():
    from saffron.gates.contract import GateResult

    results = [
        GateResult(gate="lint", status="pass", tool="ruff 1.0"),
        GateResult(gate="tests", status="error", summary="toolchain missing"),
    ]
    assert session.aborted_gates(results) == ["tests"]


def test_no_errored_gate_means_no_abort():
    from saffron.gates.contract import GateResult

    results = [GateResult(gate="lint", status="fail", tool="ruff 1.0")]
    assert session.aborted_gates(results) == []


def _spec(**overrides):
    fields = dict(
        spec_id="SY-1",
        spec_sha="a" * 64,
        branch="saffron/SY-1",
        base_sha="b" * 40,
        touches=["src/**", "tests/**"],
        spec_type="feature",
        body="do the thing",
    )
    return session.CellSpec(**(fields | overrides))


_PLAN = {
    "understanding": "u",
    "approach": "a",
    "files_to_change": ["src/x.py", "tests/test_x.py"],
    "test_strategy": "t",
    "risks": [],
    "blocking_questions": [],
}


def _agent(*texts):
    """A fake agent: one turn per text, each returning a result the host can
    read. It records the prompts, because the checkpoint's whole behaviour is
    what it asks for and when."""
    turns = iter(texts)

    def _run(container, *, prompt, options, resume=None, watch=print, **kwargs):
        _run.prompts.append(prompt)
        _run.resumes.append(resume)
        return implement.AttemptResult(
            session_id="sess-1",
            subtype="success",
            terminal_reason="completed",
            num_turns=1,
            cost_usd_est=0.1,
            text=next(turns),
        )

    _run.prompts = []
    _run.resumes = []
    return _run


def _block(plan):
    return f"Here is the plan.\n<output>\n{json.dumps(plan)}\n</output>"


def test_an_accepted_plan_costs_exactly_one_turn():
    agent = _agent(_block(_PLAN))
    attempt, raw = session.plan_checkpoint(
        "cell",
        options={},
        spec=_spec(),
        protected=["DESIGN.md"],
        agent=agent,
        watch=lambda _line: None,
    )
    assert json.loads(raw) == _PLAN
    assert attempt.session_id == "sess-1"
    assert len(agent.prompts) == 1


def test_a_plan_outside_touches_is_rejected_without_a_second_turn():
    """No implementation token is spent, and the rejection is about content,
    so there is nothing to re-ask (§5.3)."""
    agent = _agent(_block(_PLAN | {"files_to_change": ["infra/deploy.tf"]}))
    with pytest.raises(artifacts.PlanRejected):
        session.plan_checkpoint(
            "cell",
            options={},
            spec=_spec(),
            protected=[],
            agent=agent,
            watch=lambda _line: None,
        )
    assert len(agent.prompts) == 1


def test_output_that_is_not_the_schema_is_re_prompted_exactly_once():
    agent = _agent("I'll get to it.", _block(_PLAN))
    _attempt, raw = session.plan_checkpoint(
        "cell",
        options={},
        spec=_spec(),
        protected=[],
        agent=agent,
        watch=lambda _line: None,
    )
    assert json.loads(raw) == _PLAN
    assert len(agent.prompts) == 2
    # Bounded, and about shape: the re-prompt carries the validation error and
    # resumes the same session rather than starting a new one.
    assert "not the schema" in agent.prompts[1]
    assert agent.resumes[1] == "sess-1"


def test_a_second_schema_failure_rejects_rather_than_asking_again():
    agent = _agent("nope", "still nope")
    with pytest.raises(artifacts.PlanNotSchema):
        session.plan_checkpoint(
            "cell",
            options={},
            spec=_spec(),
            protected=[],
            agent=agent,
            watch=lambda _line: None,
        )
    assert len(agent.prompts) == 2


def _results(*failures):
    return [
        GateResult(
            gate="lint",
            status="fail" if failures else "pass",
            tool="ruff 1.0",
            failures=list(failures),
        )
    ]


def _loop(*rounds, max_attempts=4):
    """Drive the loop over a scripted sequence of gate suites."""
    suites = iter(rounds)
    repairs = []
    state = session.repair_loop(
        run_gates=lambda: next(suites),
        baseline=[],
        max_attempts=max_attempts,
        repair=repairs.append,
        watch=lambda _line: None,
    )
    return state, repairs


def test_a_green_suite_ends_the_loop_ready_for_review():
    state, repairs = _loop(_results())
    assert state == "READY_FOR_REVIEW"
    assert repairs == []


def test_a_fixed_failure_ends_green_after_one_repair():
    failing = Failure(file="a.py", code="E501", message="too long")
    state, repairs = _loop(_results(failing), _results())
    assert state == "READY_FOR_REVIEW"
    assert len(repairs) == 1


def test_the_same_failures_twice_running_stops_paying():
    failing = Failure(file="a.py", code="E501", message="too long")
    state, repairs = _loop(_results(failing), _results(failing))
    assert state == "EXHAUSTED"
    assert len(repairs) == 1


def test_the_loop_stops_at_max_attempts():
    """Different failures every round: progress, but not enough of it."""
    rounds = [
        _results(Failure(file=f"{n}.py", code="E501", message="m")) for n in range(3)
    ]
    state, repairs = _loop(*rounds, max_attempts=3)
    assert state == "EXHAUSTED"
    assert len(repairs) == 2


def test_an_errored_gate_aborts_the_loop_without_charging_the_task():
    errored = [GateResult(gate="tests", status="error", summary="toolchain missing")]
    state, repairs = _loop(errored)
    assert state == "GATE_ERROR"
    assert repairs == []


def test_a_baseline_failure_is_not_the_tasks_problem():
    """Only new failures count, or every task inherits the repo's flaky tests."""
    pre_existing = Failure(file="old.py", code="E501", message="too long")
    state = session.repair_loop(
        run_gates=lambda: _results(pre_existing),
        baseline=_results(pre_existing),
        max_attempts=4,
        repair=lambda _new: None,
        watch=lambda _line: None,
    )
    assert state == "READY_FOR_REVIEW"


def test_the_task_row_carries_the_specs_own_sha_not_the_policys(tmp_path, monkeypatch):
    """§4.1: a spec edited mid-batch must invalidate the task, on its own
    hash — not the policy's, which the two distinguishable shas here catch."""
    repo = tmp_path / "repo"
    (repo / ".saffron" / "gates").mkdir(parents=True)
    (repo / ".saffron" / "policy.yaml").write_text("gates: {}\n")

    spec = session.CellSpec(
        spec_id="SY-1",
        spec_sha="spec" + "0" * 60,
        branch="saffron/SY-1",
        base_sha="a" * 40,
        touches=["src/**"],
        spec_type="bug",
        body="do the thing",
    )

    # Stop right after the ledger writes, before anything touches a real
    # cell runtime — this test asserts the ledger rows, nothing past it.
    # KeyboardInterrupt, not Exception: the abort the attended driver actually
    # sees is Ctrl-C, so this also pins the `except BaseException` clause.
    class _StopHere(KeyboardInterrupt):
        pass

    def _stop(*_a, **_k):
        raise _StopHere

    monkeypatch.setattr("saffron.repos.image.build_cell_image", _stop)
    for name in (
        "remove_container",
        "remove_network",
        "create_network",
        "remove_volume",
    ):
        monkeypatch.setattr(f"saffron.cell.runtime.{name}", lambda *a, **k: None)
    monkeypatch.setattr("saffron.cell.proxy.stop_proxy", lambda *a, **k: None)

    ledger = Ledger(tmp_path / "ledger.db")
    try:
        with pytest.raises(_StopHere):
            session.run_one_cell(
                spec,
                repo=repo,
                mirror=tmp_path / "m.git",
                ledger=ledger,
                out_dir=tmp_path / "out",
            )
        row = ledger._db.execute(
            "SELECT spec_sha FROM tasks WHERE spec_id = 'SY-1'"
        ).fetchone()
        (repo_row,) = ledger._db.execute("SELECT policy_sha FROM repos").fetchall()

        assert row["spec_sha"] == spec.spec_sha
        assert row["spec_sha"] != repo_row["policy_sha"]

        # An aborted run must not read as still going, and its task must not
        # read as never started.
        (run_row,) = ledger._db.execute("SELECT status FROM runs").fetchall()
        assert run_row["status"] == "ABORTED"
        (queued,) = ledger.queue_lines()
        assert queued["state"] == "ORPHANED"
    finally:
        ledger.close()


def test_the_cell_env_carries_the_proxy_and_the_state_dir(monkeypatch):
    """§5.1's per-task block: without these the cell has full egress and the
    agent writes its session state into the tree the scope gate walks."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    env = session.cell_env("10.88.0.2", {"RAYON_NUM_THREADS": "2"})
    assert env["HTTPS_PROXY"] == "http://10.88.0.2:3128"
    assert env["CLAUDE_CONFIG_DIR"] == "/agent-state"
    assert env["RAYON_NUM_THREADS"] == "2"
    assert "ANTHROPIC_API_KEY" not in env

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert session.cell_env("10.88.0.2", {})["ANTHROPIC_API_KEY"] == "sk-test"
