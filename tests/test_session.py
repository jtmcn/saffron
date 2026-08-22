from __future__ import annotations

import json

import pytest

from saffron.agents import artifacts
from saffron.cell import runtime, session
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


def test_an_early_return_still_produces_a_complete_outcome(tmp_path, monkeypatch):
    """PREFLIGHT_FAILED returns before `spent` and `reviews` are bound.

    Defaults on CellOutcome are not tidiness: constructing one at that return
    without them raises UnboundLocalError on the failure path that matters most.
    """
    outcome = session.CellOutcome(
        state="PREFLIGHT_FAILED", task_id=1, run_id=1, task_dir=tmp_path
    )
    assert outcome.spent_usd == 0.0
    assert outcome.attempts == 0
    assert outcome.reviews == []
    assert outcome.rebut_result is None
    assert outcome.agent_subjects == []


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
            session_id=_run.session_id,
            subtype="success",
            terminal_reason="completed",
            num_turns=1,
            cost_usd_est=0.1,
            text=next(turns),
        )

    _run.prompts = []
    _run.resumes = []
    _run.session_id = "sess-1"
    return _run


def _block(plan):
    return f"Here is the plan.\n<output>\n{json.dumps(plan)}\n</output>"


def test_an_accepted_plan_costs_exactly_one_turn():
    agent = _agent(_block(_PLAN))
    attempt, raw, spent = session.plan_checkpoint(
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
    assert spent == 0.1


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
    _attempt, raw, spent = session.plan_checkpoint(
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
    # Both turns, or the turn that failed validation is a cost nobody counts.
    assert spent == 0.2


def test_a_turn_with_no_session_id_is_never_resumed():
    """`resume=None` starts a fresh session with no memory of the plan, and the
    repair loop would read the resulting flailing as the agent's fault."""
    agent = _agent("not the schema", _block(_PLAN))
    agent.session_id = None
    with pytest.raises(session.CellSessionError):
        session.plan_checkpoint(
            "cell",
            options={},
            spec=_spec(),
            protected=[],
            agent=agent,
            watch=lambda _line: None,
        )


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
    state, _attempts, _new = session.repair_loop(
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


def test_a_gate_that_stopped_running_between_the_suites_is_not_a_green():
    """§5.4: gate-status or `tool` drift is grounds to distrust the subtraction
    rather than report it — and both suites here carry zero failures."""
    baseline = [GateResult(gate="tests", status="pass", tool="pytest 8.0")]
    head = [GateResult(gate="tests", status="skip")]
    state, _attempts, _new = session.repair_loop(
        run_gates=lambda: head,
        baseline=baseline,
        max_attempts=4,
        repair=lambda _new: None,
        watch=lambda _line: None,
    )
    assert state == "GATE_ERROR"


def test_a_baseline_failure_is_not_the_tasks_problem():
    """Only new failures count, or every task inherits the repo's flaky tests."""
    pre_existing = Failure(file="old.py", code="E501", message="too long")
    state, _attempts, _new = session.repair_loop(
        run_gates=lambda: _results(pre_existing),
        baseline=_results(pre_existing),
        max_attempts=4,
        repair=lambda _new: None,
        watch=lambda _line: None,
    )
    assert state == "READY_FOR_REVIEW"


class _Cell:
    """What the stubbed runtime was asked to do, so a test can assert on it."""

    def __init__(self):
        self.removed: list[tuple[str, str]] = []
        self.turns: list[str] = []
        self.system_prompts: list[str] = []
        self.measured_from: str | None = None
        self.watched: list[str] = []
        self.exported = False
        self.timeouts: list[float | None] = []
        self.denied: list[str] = []


_DIFF = """diff --git a/src/x.py b/src/x.py
+++ b/src/x.py
+def x(): ...
"""


def _stub_the_runtime(
    monkeypatch, *, commits=1, suites=(), patch=_DIFF, changed=("src/x.py",)
):
    """Everything past the ledger writes, stubbed. No test reached here before,
    which is why a shadowed volume name survived lint and 247 green tests."""
    cell = _Cell()

    def _remove(kind):
        def _f(name):
            cell.removed.append((kind, name))
            return runtime.Completed(0, "", "")

        return _f

    monkeypatch.setattr("saffron.cell.runtime.remove_container", _remove("container"))
    monkeypatch.setattr("saffron.cell.runtime.remove_network", _remove("network"))
    monkeypatch.setattr("saffron.cell.runtime.remove_volume", _remove("volume"))
    monkeypatch.setattr("saffron.cell.runtime.create_network", lambda *a, **k: None)
    monkeypatch.setattr("saffron.cell.runtime.create_volume", lambda *a, **k: None)
    monkeypatch.setattr("saffron.cell.proxy.start_proxy", lambda *a, **k: "10.88.0.2")
    monkeypatch.setattr("saffron.cell.proxy.stop_proxy", lambda *a, **k: None)
    monkeypatch.setattr("saffron.cell.proxy.denied_egress", lambda *a, **k: cell.denied)
    monkeypatch.setattr(
        "saffron.preflight.assert_host_is_unreachable", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "saffron.preflight.host_probe_ports", lambda: ([8000], ["rapportd:49152"])
    )
    monkeypatch.setattr("saffron.repos.image.build_cell_image", lambda repo: "img")

    def _prepare_worktree(**k):
        # The real one records each name against its own create; a stub that
        # does not is a stub whose teardown ledger is always empty.
        if k.get("created") is not None:
            k["created"].update((k["state_volume"], k["container"]))

    monkeypatch.setattr("saffron.cell.worktree.prepare_worktree", _prepare_worktree)
    monkeypatch.setattr("saffron.cell.worktree.head_sha", lambda c: "c" * 40)
    monkeypatch.setattr("saffron.cell.worktree.export_patch", lambda c, sha: patch)

    def _changed_files(_container, _sha):
        # Empty until the agent has taken a turn: the baseline suite runs at
        # base_sha, on a worktree nothing has committed to yet.
        return list(changed) if cell.turns else []

    monkeypatch.setattr("saffron.cell.worktree.changed_files", _changed_files)

    def _commits_ahead(_container, sha):
        cell.measured_from = sha
        return commits

    monkeypatch.setattr("saffron.cell.worktree.commits_ahead", _commits_ahead)

    scripted = iter(suites)
    monkeypatch.setattr(
        "saffron.gates.runner.run_suite", lambda *a, **k: next(scripted, [])
    )
    return cell


def _turn(text="", cost=0.1):
    return implement.AttemptResult(
        session_id="sess-1",
        subtype="success",
        terminal_reason="completed",
        num_turns=1,
        cost_usd_est=cost,
        text=text,
    )


def _drive(monkeypatch, tmp_path, *, cell, turns, spec=None, policy="gates: {}\n"):
    """Run one whole cell against the stubbed runtime and return its outcome."""
    repo = tmp_path / "repo"
    (repo / ".saffron" / "gates").mkdir(parents=True)
    (repo / ".saffron" / "policy.yaml").write_text(policy)

    scripted = iter(turns)

    def _run_agent(container, *, prompt, options, resume=None, **kwargs):
        cell.turns.append(prompt)
        cell.system_prompts.append(options["system_prompt"])
        cell.timeouts.append(kwargs.get("timeout_s"))
        # A default, not a scripted turn: REVIEW invokes one session per lens
        # after a green loop, and every test predating it scripts the
        # implementer's turns only. An empty findings block is a clean review.
        turn = next(scripted, _turn(_block({"findings": []})))
        if isinstance(turn, BaseException):
            raise turn
        return turn

    monkeypatch.setattr("saffron.phases.implement.run_agent", _run_agent)

    # Left open: the caller reads its rows. tmp_path takes the file away.
    ledger = Ledger(tmp_path / "ledger.db")
    outcome = session.run_one_cell(
        spec or _spec(),
        repo=repo,
        mirror=tmp_path / "m.git",
        ledger=ledger,
        out_dir=tmp_path / "out",
        watch=cell.watched.append,
    )
    return outcome, ledger


def test_the_preflight_line_reports_what_was_tolerated(monkeypatch, tmp_path):
    """Every run, not the first: an exception that goes quiet recreates the
    invisibility §7's hazard row exists for."""
    cell = _stub_the_runtime(monkeypatch)
    _drive(monkeypatch, tmp_path, cell=cell, turns=[_turn(_block(_PLAN)), _turn()])
    (probing,) = [x for x in cell.watched if x.startswith("preflight: probing")]
    assert probing.startswith("preflight: probing 1 host ports at 10.88.0.1")
    assert probing.endswith("; tolerating rapportd:49152")


def test_teardown_removes_both_volumes_not_the_loops_result(monkeypatch, tmp_path):
    """C1: `state` named the state volume *and* the repair loop's outcome, so
    teardown ran `volume rm READY_FOR_REVIEW` — swallowed, and the volume
    holding CLAUDE_CONFIG_DIR survived every run that reached the loop."""
    cell = _stub_the_runtime(monkeypatch)
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn()],
    )
    assert outcome.state == "READY_FOR_REVIEW"
    # The last two calls are teardown's; the earlier ones pre-cleaned.
    assert cell.removed[-2:] == [
        ("volume", "saffron-wt-SY-1"),
        ("volume", "saffron-st-SY-1"),
    ]


def _every_removal_fails(monkeypatch, cell):
    """What the runtime prints for a leak and for a name that never existed:
    `container volume rm <missing>` exits 1, measured."""

    def _remove(kind):
        def _f(name):
            cell.removed.append((kind, name))
            return runtime.Completed(1, "", f"no such {kind}")

        return _f

    for kind in ("container", "network", "volume"):
        monkeypatch.setattr(f"saffron.cell.runtime.remove_{kind}", _remove(kind))


def test_teardown_reports_only_what_this_run_created(monkeypatch, tmp_path):
    """C1 inverted: a run that aborts before `create_volume` reported survivors
    for volumes that never existed, training the operator to ignore the exact
    line C1 needed visible. The network this run did create is still reported."""
    cell = _stub_the_runtime(monkeypatch)
    _every_removal_fails(monkeypatch, cell)

    def _boom(_repo):
        raise RuntimeError("the image build failed")

    monkeypatch.setattr("saffron.repos.image.build_cell_image", _boom)
    with pytest.raises(RuntimeError, match="image build"):
        _drive(monkeypatch, tmp_path, cell=cell, turns=[])

    assert [line for line in cell.watched if "survived" in line] == [
        "teardown: network saffron-cells survived — no such network"
    ]


def test_a_volume_this_run_created_and_could_not_remove_is_reported(
    monkeypatch, tmp_path
):
    """The other half: a silent non-zero teardown is what let the state volume
    survive every run unnoticed."""
    cell = _stub_the_runtime(monkeypatch)
    _every_removal_fails(monkeypatch, cell)
    outcome, _ledger = _drive(
        monkeypatch, tmp_path, cell=cell, turns=[_turn(_block(_PLAN)), _turn()]
    )
    assert outcome.state == "READY_FOR_REVIEW"
    survived = [line for line in cell.watched if "survived" in line]
    assert any("volume saffron-wt-SY-1 survived" in line for line in survived)
    assert any("volume saffron-st-SY-1 survived" in line for line in survived)


def test_doneness_is_measured_from_after_the_plan_turn(monkeypatch, tmp_path):
    """I7: the plan turn holds Write/Edit/Bash, so a commit it makes would
    otherwise satisfy the implement turn's measurement."""
    cell = _stub_the_runtime(monkeypatch)
    _drive(monkeypatch, tmp_path, cell=cell, turns=[_turn(_block(_PLAN)), _turn()])
    assert cell.measured_from == "c" * 40  # head_sha after the checkpoint


def test_the_implement_prompt_names_the_paths_it_is_judged_against(
    monkeypatch, tmp_path
):
    """`touches`, `forbidden` and protected paths live in frontmatter and
    policy.yaml, never in the spec body — so the prompt told the agent to obey a
    list it was auto-rejected against and never shown."""
    cell = _stub_the_runtime(monkeypatch)
    _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn()],
        spec=_spec(forbidden=["alembic/versions/**"]),
        policy="gates: {}\nprotected:\n  - DESIGN.md\n",
    )
    prompt = cell.system_prompts[0]
    for path in ("src/**", "tests/**", "alembic/versions/**", "DESIGN.md"):
        assert f"- `{path}`" in prompt


def test_a_spec_with_no_forbidden_shows_no_forbidden_list(monkeypatch, tmp_path):
    """CONTEXT.md defines the term either way; what must not appear is a heading
    with nothing under it for the agent to fill in."""
    cell = _stub_the_runtime(monkeypatch)
    _drive(monkeypatch, tmp_path, cell=cell, turns=[_turn(_block(_PLAN)), _turn()])
    prompt = cell.system_prompts[0]
    assert "- `src/**`" in prompt
    assert "`forbidden` — deny paths" not in prompt


def test_no_commit_is_not_implemented(monkeypatch, tmp_path):
    cell = _stub_the_runtime(monkeypatch, commits=0)
    outcome, _ledger = _drive(
        monkeypatch, tmp_path, cell=cell, turns=[_turn(_block(_PLAN)), _turn()]
    )
    assert outcome.state == "NOT_IMPLEMENTED"


def test_a_green_run_leaves_the_patch_behind(monkeypatch, tmp_path):
    """The first live green run committed, then teardown removed the volume and
    the commit ceased to exist. §0: the product is a reviewable artifact."""
    cell = _stub_the_runtime(monkeypatch)
    outcome, _ledger = _drive(
        monkeypatch, tmp_path, cell=cell, turns=[_turn(_block(_PLAN)), _turn()]
    )
    assert outcome.state == "READY_FOR_REVIEW"
    task_dir = tmp_path / "out" / "SY-1"
    assert (task_dir / "patch.diff").read_text() == _DIFF
    assert json.loads((task_dir / "patch.json").read_text()) == {
        "base_sha": "b" * 40,
        "head_sha": "c" * 40,
        "files": ["src/x.py"],
    }


def test_a_run_that_never_went_green_still_exports_its_commits(monkeypatch, tmp_path):
    """§5.4 calls EXHAUSTED a respectable outcome — green-only export would
    throw away exactly the runs worth reading."""
    failing = Failure(file="a.py", code="E501", message="too long")
    cell = _stub_the_runtime(
        monkeypatch, suites=([], _results(failing), _results(failing))
    )
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn(), _turn()],
    )
    assert outcome.state == "EXHAUSTED"
    assert (tmp_path / "out" / "SY-1" / "patch.diff").read_text() == _DIFF


def test_no_commits_writes_no_patch_at_all(monkeypatch, tmp_path):
    """Absence and emptiness must not look alike: an empty patch.diff reads as
    a run whose work was lost."""
    cell = _stub_the_runtime(monkeypatch, commits=0, patch="")
    outcome, _ledger = _drive(
        monkeypatch, tmp_path, cell=cell, turns=[_turn(_block(_PLAN)), _turn()]
    )
    assert outcome.state == "NOT_IMPLEMENTED"
    assert not (tmp_path / "out" / "SY-1" / "patch.diff").exists()
    assert any("nothing to export" in line for line in cell.watched)


def test_a_dead_cell_reports_the_failed_export_rather_than_raising(
    monkeypatch, tmp_path
):
    """Teardown runs in a `finally`: an export that raises there would replace
    the run's own outcome with the export's failure."""
    cell = _stub_the_runtime(monkeypatch)

    def _dies_at_teardown(_container, _sha):
        # The gates and REVIEW read the diff first; the cell dies once the
        # outcome is decided, and teardown's export is what finds out.
        if any(line.startswith("teardown") for line in cell.watched):
            raise runtime.CellRuntimeError("no such cell")
        return _DIFF

    monkeypatch.setattr("saffron.cell.worktree.export_patch", _dies_at_teardown)
    outcome, _ledger = _drive(
        monkeypatch, tmp_path, cell=cell, turns=[_turn(_block(_PLAN)), _turn()]
    )
    assert outcome.state == "READY_FOR_REVIEW"
    assert any("export FAILED — no such cell" in line for line in cell.watched)


def test_a_diff_outside_touches_fails_the_suite(monkeypatch, tmp_path):
    """§3.2 promises `touches` is enforced mechanically, but only the *plan*
    was checked against it. Both live runs committed with `git add -A`."""
    cell = _stub_the_runtime(
        monkeypatch, changed=("infra/deploy.tf",), suites=([], [], [])
    )
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn(), _turn()],
    )
    assert outcome.state == "EXHAUSTED"
    # The repair prompt is the whole of what the agent receives about a gate.
    assert (
        "- [scope] infra/deploy.tf:? out-of-scope: outside touches: src/**, tests/**"
        in cell.turns[2]
    )


def test_the_baseline_scope_neither_invents_nor_cancels_an_escape(
    monkeypatch, tmp_path
):
    """The baseline is measured at base_sha, where the diff is empty: `scope`
    passes carrying no failures, so no task inherits one and none is subtracted
    away from head."""
    cell = _stub_the_runtime(monkeypatch)
    outcome, ledger = _drive(
        monkeypatch, tmp_path, cell=cell, turns=[_turn(_block(_PLAN)), _turn()]
    )
    assert outcome.state == "READY_FOR_REVIEW"

    (scope,) = json.loads((tmp_path / "out" / "SY-1" / "baseline.json").read_text())
    assert (scope["status"], scope["failures"]) == ("pass", [])
    assert scope["summary"] == "0 changed files within touches"

    # And at head it measured the real diff rather than nothing.
    assert [
        row["summary"]
        for row in ledger._db.execute(
            "SELECT summary FROM gate_results WHERE gate = 'scope' AND run_id IS NULL"
        )
    ] == ["1 changed files within touches"]


def test_a_repair_turn_that_fails_does_not_discard_committed_work(
    monkeypatch, tmp_path
):
    """I1: a bound firing mid-loop escaped into `except BaseException` and
    marked the run ABORTED — after the implement turn had committed (§4.3)."""
    failing = Failure(file="a.py", code="E501", message="too long")
    cell = _stub_the_runtime(monkeypatch, suites=([], _results(failing), []))
    outcome, ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[
            _turn(_block(_PLAN)),
            _turn(),
            implement.AgentFailed("max turns", _turn(cost=0.4)),
        ],
    )
    assert outcome.state == "READY_FOR_REVIEW"
    (run_row,) = ledger._db.execute("SELECT status FROM runs").fetchall()
    assert run_row["status"] == "COMPLETE"
    # Plan, implement, the failed repair turn's $0.40, and REVIEW's two lenses:
    # the critic is spend too, and a total that omits it stops being a total.
    assert any("$0.80 spent" in line for line in cell.watched)


def test_the_host_stops_spending_at_the_tasks_budget(monkeypatch, tmp_path):
    """I2: `max_budget_usd` is per turn and lives inside the cell. Without a
    host-side sum, a $12 task can spend (2 + max_attempts) x $12."""
    cell = _stub_the_runtime(monkeypatch)
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN), cost=0.5)],
        spec=_spec(budget_usd=0.4),
    )
    assert outcome.state == "EXHAUSTED"
    assert len(cell.turns) == 1  # the implement turn is never bought


def test_the_ceiling_also_stops_the_repair_loop(monkeypatch, tmp_path):
    failing = Failure(file="a.py", code="E501", message="too long")
    cell = _stub_the_runtime(
        monkeypatch, suites=([], _results(failing), _results(failing))
    )
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn(), _turn()],
        spec=_spec(budget_usd=0.25),
    )
    assert outcome.state == "EXHAUSTED"
    assert len(cell.turns) == 3


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

    _stub_the_runtime(monkeypatch)
    monkeypatch.setattr("saffron.repos.image.build_cell_image", _stop)

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
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    env = session.cell_env("10.88.0.2", {"RAYON_NUM_THREADS": "2"})
    assert env["HTTPS_PROXY"] == "http://10.88.0.2:3128"
    assert env["CLAUDE_CONFIG_DIR"] == "/agent-state"
    assert env["RAYON_NUM_THREADS"] == "2"
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in env

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat-test")
    assert (
        session.cell_env("10.88.0.2", {})["CLAUDE_CODE_OAUTH_TOKEN"]
        == "sk-ant-oat-test"
    )


def test_the_cell_env_never_carries_an_api_key(monkeypatch):
    """The credential swap has to hold in the direction that can regress
    silently. A host with a key exported must not put one in a cell: the
    subscription token is separately revocable and its ceiling is
    provider-side, which the key's is not (§5.1)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat-test")
    env = session.cell_env("10.88.0.2", {})
    assert "ANTHROPIC_API_KEY" not in env
    assert env["CLAUDE_CODE_OAUTH_TOKEN"] == "sk-ant-oat-test"


_BLOCKER = {
    "findings": [
        {
            "file": "src/x.py",
            "line": 1,
            "severity": "blocker",
            "claim": "x returns nothing",
        }
    ]
}

# _DIFF carries no `@@`, so nothing in it anchors; a blocker has to point at a
# real changed line to route anywhere (§5.5).
_ANCHORING_DIFF = """diff --git a/src/x.py b/src/x.py
--- a/src/x.py
+++ b/src/x.py
@@ -1 +1 @@
-def x(): pass
+def x(): ...
"""

_CLAIMED_FIX = {"rebuttals": [{"finding": 0, "action": "fixed", "argument": "done"}]}


def _rebuttable(monkeypatch, cell, *, rebut_commits):
    """A cell whose review anchors one blocker, and whose HEAD after the
    rebuttal is the caller's to decide. The stub's `commits_ahead` is constant,
    so IMPLEMENT's measurement and REBUT's are told apart by call order — the
    order run_one_cell makes them in."""
    monkeypatch.setattr(
        "saffron.cell.worktree.read_at_head", lambda _c, _p: "def x(): ...\n"
    )
    measured: list[str] = []

    def _commits_ahead(_container, sha):
        cell.measured_from = sha
        measured.append(sha)
        return 1 if len(measured) == 1 else rebut_commits

    monkeypatch.setattr("saffron.cell.worktree.commits_ahead", _commits_ahead)


def _through_rebut(*rebut_turns):
    """Plan, implement, one lens filing a blocker, one filing nothing, then the
    rebuttal's own turns."""
    return [
        _turn(_block(_PLAN)),
        _turn(),
        _turn(_block(_BLOCKER)),
        _turn(_block({"findings": []})),
        *rebut_turns,
    ]


def test_a_rebuttal_that_claims_a_fix_and_commits_nothing_stops_at_rebutting(
    monkeypatch, tmp_path
):
    """§4.3's REBUT row, end to end: "I have addressed the findings" with no
    commit and no argument is not doneness, and the task must not advance."""
    cell = _stub_the_runtime(monkeypatch, patch=_ANCHORING_DIFF)
    _rebuttable(monkeypatch, cell, rebut_commits=0)
    outcome, ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=_through_rebut(
            _turn("I have addressed the findings."), _turn(_block(_CLAIMED_FIX))
        ),
    )
    assert outcome.state == "REBUTTING"
    (queued,) = ledger.queue_lines()
    assert queued["state"] == "REBUTTING"
    record = json.loads((tmp_path / "out" / "SY-1" / "rebuttal.json").read_text())
    assert record["head_moved"] is False
    assert record["verdicts"] == []


def test_gates_red_after_the_rebuttal_exhausts_and_keeps_the_diff(
    monkeypatch, tmp_path
):
    """§5.6: the rebuttal diff and the failing gate are both kept, and the
    repair loop does not reopen."""
    failing = Failure(file="a.py", code="E501", message="too long")
    cell = _stub_the_runtime(
        monkeypatch, suites=([], [], _results(failing)), patch=_ANCHORING_DIFF
    )
    _rebuttable(monkeypatch, cell, rebut_commits=1)
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=_through_rebut(_turn("Fixed it."), _turn(_block(_CLAIMED_FIX))),
    )
    assert outcome.state == "EXHAUSTED"
    assert (tmp_path / "out" / "SY-1" / "patch.diff").read_text() == _ANCHORING_DIFF
    assert any("new failures after the rebuttal" in line for line in cell.watched)


def test_a_bound_firing_on_the_implement_turn_still_measures_the_worktree(
    monkeypatch, tmp_path
):
    """§4.3: a timeout must never discard committed work. The idle bound cuts
    the turn mid-sentence; what decides the outcome is the commits already in
    the worktree, not whether the process exited cleanly."""
    cell = _stub_the_runtime(monkeypatch)
    outcome, ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[
            _turn(_block(_PLAN)),
            implement.AgentFailed(
                "the agent was cut by the idle bound", _turn(cost=0.4)
            ),
        ],
    )
    assert outcome.state == "READY_FOR_REVIEW"
    assert cell.measured_from == "c" * 40  # commits_ahead ran anyway
    (run_row,) = ledger._db.execute("SELECT status FROM runs").fetchall()
    assert run_row["status"] == "COMPLETE"


def test_every_turn_carries_the_drivers_wall_clock_not_the_librarys(
    monkeypatch, tmp_path
):
    """3600s is the transport's ceiling; the bound an operator actually sits
    through is set here, and a turn that inherits the default is an hour of
    watching nothing happen."""
    cell = _stub_the_runtime(monkeypatch)
    _drive(monkeypatch, tmp_path, cell=cell, turns=[_turn(_block(_PLAN)), _turn()])
    assert session.TURN_TIMEOUT_S < 3600
    assert cell.timeouts == [session.TURN_TIMEOUT_S] * len(cell.turns)


def test_a_crashed_plan_turn_keeps_its_own_exception_and_its_cost():
    """A plan turn that crashed is neither a plan rejected on content nor a dead
    cell (§4.5). It carries what the checkpoint already spent, or the re-prompt's
    first half is a turn nobody charged for."""

    def _crash(container, *, prompt, options, resume=None, watch=print, **kwargs):
        if not _crash.called:
            _crash.called = True
            return implement.AttemptResult(
                session_id="sess-1",
                subtype="success",
                terminal_reason="completed",
                num_turns=1,
                cost_usd_est=0.1,
                text="not the schema",
            )
        raise implement.AgentFailed(
            "cut by the wall bound",
            implement.AttemptResult(
                session_id="sess-1",
                subtype="error",
                terminal_reason=None,
                num_turns=0,
                cost_usd_est=3.0,
                is_error=True,
            ),
        )

    _crash.called = False
    with pytest.raises(implement.AgentFailed) as raised:
        session.plan_checkpoint(
            "cell",
            options={},
            spec=_spec(),
            protected=[],
            agent=_crash,
            watch=lambda _line: None,
        )
    # Both turns: the one that failed validation and the one that crashed.
    assert raised.value.attempt.cost_usd_est == 3.1


def test_a_critic_session_is_capped_at_what_is_left_not_at_the_whole_budget():
    """REVIEW is deliberately not gated on the ceiling, so the cap is the only
    thing standing between a $12 task and a $40 bill."""
    assert session.critic_budget(12.0, 4.0) == 8.0
    # The floor is what keeps "not gated" true: a lens with no room is a task
    # that reaches the operator unreviewed.
    assert session.critic_budget(12.0, 12.0) == session.REVIEW_FLOOR_USD
    assert session.critic_budget(12.0, 99.0) == session.REVIEW_FLOOR_USD


def test_a_volume_create_that_fails_reports_only_that_volume(monkeypatch, tmp_path):
    """The other half of C1: recording all three names before the first create
    reports the state volume and the container as survivors of a run that never
    attempted either — the same false leak, one step further along."""
    cell = _stub_the_runtime(monkeypatch)
    _every_removal_fails(monkeypatch, cell)

    def _boom(_name):
        raise RuntimeError("no space left on device")

    monkeypatch.setattr("saffron.cell.runtime.create_volume", _boom)
    with pytest.raises(RuntimeError, match="no space left"):
        _drive(monkeypatch, tmp_path, cell=cell, turns=[])

    survived = [line for line in cell.watched if "survived" in line]
    # The volume whose create was attempted, and the network this run made.
    assert any("volume saffron-wt-SY-1 survived" in line for line in survived)
    assert any("network saffron-cells survived" in line for line in survived)
    assert not any("saffron-st-SY-1" in line for line in survived)
    assert not any("saffron-cell-SY-1" in line for line in survived)
    # And nothing execs a patch export into a container that was never created.
    assert not any("patch export" in line for line in cell.watched)


def test_a_rejected_window_is_not_exhaustion():
    """§3.3: a provider limit and a task that could not pass its own gates are
    different outcomes, and one state for both is how the operator is misled
    into retrying a wall."""
    assert session.terminal_for_rate_limit("rejected") == "RATE_LIMITED"
    assert session.terminal_for_rate_limit("allowed_warning") is None
    assert session.terminal_for_rate_limit("allowed") is None
    assert session.terminal_for_rate_limit(None) is None


def _rejected(resets_at=1755800000):
    """What a closed window actually looks like coming back: the CLI reports the
    rejection and the turn errors."""
    return implement.AttemptResult(
        session_id="sess-1",
        subtype="success",
        terminal_reason="api_error",
        num_turns=0,
        cost_usd_est=0.0,
        is_error=True,
        rate_limit_status="rejected",
        rate_limit_resets_at=resets_at,
    )


def test_a_wall_on_the_plan_turn_is_not_the_task_failing(monkeypatch, tmp_path):
    """The plan turn comes back as `AgentFailed`, not as a result, so the guard
    that read the returned attempt never ran and the provider's wall was stamped
    NOT_IMPLEMENTED — the task blamed for the ceiling (§3.3)."""
    cell = _stub_the_runtime(monkeypatch)
    outcome, ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[implement.AgentFailed("api_error", attempt=_rejected())],
    )
    assert outcome.state == "RATE_LIMITED"
    (task_row,) = ledger._db.execute("SELECT state FROM tasks").fetchall()
    assert task_row["state"] == "RATE_LIMITED"
    (run_row,) = ledger._db.execute("SELECT status FROM runs").fetchall()
    # COMPLETE, not the ABORTED a raise out of the cell would leave.
    assert run_row["status"] == "COMPLETE"
    # And it says when, in something the operator can act on.
    assert any("window reopens" in line for line in cell.watched)
    assert not any("1755800000" in line for line in cell.watched)


def test_a_wall_after_the_gates_go_green_stops_the_lenses(monkeypatch, tmp_path):
    """REVIEW had no guard of its own: every lens failed against the closed
    window, `review_state` read the errors as an incomplete review, and the run
    ended REVIEWING — not a terminal state, and two turns spent."""
    cell = _stub_the_runtime(monkeypatch)
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn(), _rejected()],
    )
    assert outcome.state == "RATE_LIMITED"
    # The second lens is never asked: one closed window, one turn spent.
    assert len([p for p in cell.turns if "REVIEW" in p.upper()]) <= 1


def test_a_wall_after_the_gates_go_green_reports_what_was_spent(monkeypatch, tmp_path):
    """A window closed during REVIEW arrives long after `spent` holds a real
    total, unlike a window closed on the plan turn: the RATE_LIMITED outcome
    must carry it rather than fall back to the zero meant for that earlier
    case."""
    cell = _stub_the_runtime(monkeypatch)
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn(), _rejected()],
    )
    assert outcome.state == "RATE_LIMITED"
    # Plan and implement, each the default turn cost — REVIEW's own turn is
    # never credited, since the window closed before its cost was added.
    assert outcome.spent_usd == 0.2


def test_a_denied_connect_reaches_the_operator(monkeypatch, tmp_path):
    """The proxy's log is its stdout, so it dies with the container: unread at
    teardown, a blocked host reaches the operator as an unexplained API error
    and the allowlist is the last place anyone looks."""
    cell = _stub_the_runtime(monkeypatch)
    cell.denied = ["TCP_DENIED/403 4 CONNECT platform.claude.com:443"]
    _drive(monkeypatch, tmp_path, cell=cell, turns=[_turn(_block(_PLAN)), _turn()])
    assert any(
        "proxy DENIED" in line and "platform.claude.com" in line
        for line in cell.watched
    )
