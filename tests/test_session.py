from __future__ import annotations

import hashlib
import json
import shutil

import pytest

from saffron.agents import artifacts
from saffron.cell import runtime, session
from saffron.gates.baseline import NewFailure
from saffron.gates.contract import Failure, GateResult
from saffron.gates.core.committed import committed_gate
from saffron.ledger import Ledger
from saffron.phases import implement
from saffron.repos import mirror
from saffron.repos import policy as policy_mod


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


def test_stacked_on_defaults_to_unset():
    """The shape every caller produces today: no second base at all, so
    `worktree.prepare_worktree` checks out `base_sha` exactly as before this
    field existed."""
    assert _spec().stacked_on is None


def test_stacked_on_carries_a_second_base_distinct_from_base_sha():
    spec = _spec(base_sha="b" * 40, stacked_on="c" * 40)
    assert spec.stacked_on == "c" * 40
    assert spec.base_sha == "b" * 40
    assert spec.stacked_on != spec.base_sha


def test_tree_base_is_the_pin_unstacked_and_the_parent_stacked():
    """One name for the second base. `base_sha` keeps pinning the gates and
    the policy either way (§5.4), which is why the two cannot be one field."""
    assert _spec().tree_base == "b" * 40
    assert _spec(stacked_on="c" * 40).tree_base == "c" * 40


def test_a_stacked_specs_patch_is_exported_against_its_parent_not_the_pin(
    monkeypatch, tmp_path
):
    """Criterion 3 at the caller. `tests/test_worktree.py`'s real-git witness
    proves that base yields only the child's commits; this proves Saffron is
    the one that picks it. A test that hands `export_patch` its own answer
    proves neither — the defect was every consumer choosing separately."""
    from saffron.cell import worktree as wt

    asked: list[str] = []

    def _record(_container, base, /):
        asked.append(base)
        return "diff --git a/x b/x\n"

    monkeypatch.setattr(wt, "commit_subjects", lambda c, base: asked.append(base) or [])
    monkeypatch.setattr(wt, "export_patch", _record)
    monkeypatch.setattr(wt, "changed_files", lambda c, base: asked.append(base) or [])
    monkeypatch.setattr(wt, "head_sha", lambda c: "c" * 40)

    session.export_patch(
        "cell-1", _spec(stacked_on="d" * 40), tmp_path / "out", lambda _m: None
    )

    assert asked == ["d" * 40] * 3, "a consumer still reading the run's pin"


_PLAN = {
    "understanding": "u",
    "approach": "a",
    "files_to_change": ["src/x.py", "tests/test_x.py"],
    "test_strategy": "t",
    "risks": [],
    "blocking_questions": [],
    "estimated_lines": 10,
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


# --- proposing scope instead of a plan (SA-0018) ---

_PROPOSAL = {
    "kind": "scope_proposal",
    "proposed_touches": ["infra/deploy.tf"],
    "root_cause": "the criteria describe behaviour that lives in infra/deploy.tf",
}


def test_a_proposal_outside_touches_ends_the_checkpoint_in_one_turn():
    """Accepted on the first turn: no plan, no diff, no further turns (§5.2's
    door, reached from IMPLEMENT for the first time by SA-0018)."""
    agent = _agent(_block(_PROPOSAL))
    with pytest.raises(artifacts.ScopeProposed) as excinfo:
        session.plan_checkpoint(
            "cell",
            options={},
            spec=_spec(),
            protected=[],
            agent=agent,
            watch=lambda _line: None,
        )
    assert excinfo.value.proposal.proposed_touches == ["infra/deploy.tf"]
    assert excinfo.value.spent_usd == 0.1
    assert len(agent.prompts) == 1


def test_a_refused_proposal_is_reprompted_and_a_plan_can_follow():
    """Refusal is not final: unlike an ordinary content `PlanRejected`, the
    attempt continues — the escape hatch closes and the agent still has to do
    the work, or name a path that genuinely escapes `touches`."""
    inside = _PROPOSAL | {"proposed_touches": ["src/x.py"]}  # already in _spec()
    agent = _agent(_block(inside), _block(_PLAN))
    attempt, raw, spent = session.plan_checkpoint(
        "cell",
        options={},
        spec=_spec(),
        protected=[],
        agent=agent,
        watch=lambda _line: None,
    )
    assert json.loads(raw) == _PLAN
    assert len(agent.prompts) == 2
    assert "already inside touches" in agent.prompts[1]
    assert spent == 0.2


def test_a_proposal_refused_twice_ends_as_plan_rejected():
    """Bounded exactly like a shape failure: one re-prompt, then final —
    the escape hatch cannot be used to stall a checkpoint indefinitely."""
    inside = _PROPOSAL | {"proposed_touches": ["src/x.py"]}
    agent = _agent(_block(inside), _block(inside))
    with pytest.raises(artifacts.PlanRejected):
        session.plan_checkpoint(
            "cell",
            options={},
            spec=_spec(),
            protected=[],
            agent=agent,
            watch=lambda _line: None,
        )
    assert len(agent.prompts) == 2


def test_sa_0005s_own_criteria_reach_scope_review_naming_cli_py():
    """Item 18's own corpse, driven through `plan_checkpoint` rather than
    handed a fake proposal to a recorder: SA-0005's real spec, its real
    `touches` (which do not include cli.py), and a stub agent proposing exactly
    the gap item 18 found unanchorable — `saffron/cli.py` never carrying
    `risk=spec.risk` and the queue line never carrying the effective tier.

    What SA-0005's *criteria* say never enters this path: `CellSpec.acceptance`
    is not read by the checkpoint, so the fixture is its `touches` plus a
    scripted proposal. That is the honest maximum without a model in the loop,
    and the criteria's own unreachability is item 18's point, not this test's.
    """
    from pathlib import Path

    from saffron.intake import load_spec

    spec_path = (
        Path(__file__).resolve().parents[1]
        / ".saffron"
        / "specs"
        / "done"
        / "SA-0005-size-wiring.md"
    )
    parsed, spec_sha = load_spec(spec_path)
    assert "saffron/cli.py" not in parsed.touches

    cell_spec = _spec(
        spec_id=parsed.id,
        spec_sha=spec_sha,
        touches=parsed.touches,
        spec_type=parsed.type,
        body=parsed.body,
        forbidden=parsed.forbidden,
    )
    proposal = {
        "kind": "scope_proposal",
        "proposed_touches": ["saffron/cli.py"],
        "root_cause": (
            "the effective tier the queue line and PR body header report is "
            "computed in cli.py, which this spec's touches never named"
        ),
    }
    agent = _agent(_block(proposal))
    with pytest.raises(artifacts.ScopeProposed) as excinfo:
        session.plan_checkpoint(
            "cell",
            options={},
            spec=cell_spec,
            protected=[],
            agent=agent,
            watch=lambda _line: None,
        )
    assert "saffron/cli.py" in excinfo.value.proposal.proposed_touches


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


def _dirty_suite(paths):
    return [committed_gate(paths)]


def test_a_dirty_tree_buys_one_repair_turn():
    """Attempt 1 repairs, attempt 2 is clean."""
    calls: list[str] = []
    trees = iter([["a.py"], []])

    state, attempts, _ = session.repair_loop(
        run_gates=lambda: _dirty_suite(next(trees)),
        baseline=_dirty_suite([]),
        max_attempts=4,
        repair=lambda new: calls.append("repair"),
        watch=lambda _: None,
    )
    assert calls == ["repair"]
    assert state == "READY_FOR_REVIEW"
    assert attempts == 2


def test_a_tree_still_dirty_after_the_repair_turn_ends_the_attempt():
    calls: list[str] = []

    state, attempts, new = session.repair_loop(
        run_gates=lambda: _dirty_suite(["a.py"]),
        baseline=_dirty_suite([]),
        max_attempts=4,
        repair=lambda _: calls.append("repair"),
        watch=lambda _: None,
    )
    assert calls == ["repair"]  # exactly one, not four
    assert state == "EXHAUSTED"
    assert attempts == 2
    assert [n.failure.file for n in new] == ["a.py"]


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
        self.subjects_from: str | None = None
        self.timeouts: list[float | None] = []
        self.checkpointed: list[str] = []
        self.denied: list[str] = []
        self.failed: list[str] = []
        self.preflight: list[str] = []
        self.gate_paths: list[list[str]] = []


_DIFF = """diff --git a/src/x.py b/src/x.py
+++ b/src/x.py
+def x(): ...
"""

# A diff `size` fails against a `bug` spec's 300-line ceiling. Built, not
# hand-written: what matters is the count, not the content.
_BIG_DIFF = (
    "diff --git a/src/x.py b/src/x.py\n"
    "--- a/src/x.py\n"
    "+++ b/src/x.py\n"
    "@@ -1,1 +1,310 @@\n" + "".join(f"+line {n}\n" for n in range(310))
)


def _grow_the_diff_after_the_first_turn(
    monkeypatch, cell, *, small=_DIFF, big=_BIG_DIFF
):
    """The baseline suite runs before any turn, on a worktree at `base_sha`
    where the real diff is empty. `_stub_the_runtime`'s `export_patch` stub is
    constant, so a gate that reads the diff itself (`size`) would otherwise
    see the same content on both sides of the subtraction and never produce a
    new failure. This mirrors `_changed_files`' own `cell.turns` check: small
    before the agent has moved, big once it has."""
    monkeypatch.setattr(
        "saffron.cell.worktree.export_patch",
        lambda _c, _s: small if not cell.turns else big,
    )


def _stub_the_runtime(
    monkeypatch,
    *,
    commits=1,
    suites=(),
    patch=_DIFF,
    changed=("src/x.py",),
    subjects=("the agent's work",),
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

    # The order these run in is load-bearing, so it is recorded rather than
    # described: the runtime's routing depends on it (§5.1.1, evidence
    # 2026-08-28), and so does what the probe is told to look at.
    def _ordered(name, result):
        def _f(*a, **k):
            cell.preflight.append(name)
            return result

        return _f

    monkeypatch.setattr(
        "saffron.cell.proxy.start_proxy", _ordered("proxy", "10.88.0.2")
    )
    monkeypatch.setattr("saffron.cell.proxy.stop_proxy", _ordered("stop", None))

    # Recorded, not described: the proxy's log is its stdout and dies with the
    # container, so a `stop_proxy` moved above these reads silences both reports
    # and every other test still passes.
    def _reads(name, attr):
        # Read at call time, not at stub time: a test sets these after this
        # fixture has run.
        def _f(*a, **k):
            cell.preflight.append(name)
            return getattr(cell, attr)

        return _f

    monkeypatch.setattr(
        "saffron.cell.proxy.denied_egress", _reads("read-denied", "denied")
    )
    monkeypatch.setattr(
        "saffron.cell.proxy.failed_egress", _reads("read-failed", "failed")
    )
    monkeypatch.setattr(
        "saffron.preflight.assert_proxy_reaches_upstream", _ordered("egress", "401")
    )
    monkeypatch.setattr(
        "saffron.preflight.assert_host_is_unreachable", _ordered("probe", None)
    )
    monkeypatch.setattr(
        "saffron.preflight.host_probe_ports",
        _ordered("enumerate", ([8000], ["rapportd:49152"])),
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

    def _commit_subjects(_container, sha):
        cell.subjects_from = sha
        return list(subjects)

    monkeypatch.setattr("saffron.cell.worktree.commit_subjects", _commit_subjects)

    def _changed_files(_container, _sha):
        # Empty until the agent has taken a turn: the baseline suite runs at
        # base_sha, on a worktree nothing has committed to yet.
        return list(changed) if cell.turns else []

    monkeypatch.setattr("saffron.cell.worktree.changed_files", _changed_files)
    monkeypatch.setattr("saffron.cell.worktree.dirty_paths", lambda container: [])

    def _commit_dirty(_container, message):
        cell.checkpointed.append(message)
        return True

    monkeypatch.setattr("saffron.cell.worktree.commit_dirty", _commit_dirty)

    def _commits_ahead(_container, sha):
        cell.measured_from = sha
        return commits

    monkeypatch.setattr("saffron.cell.worktree.commits_ahead", _commits_ahead)

    scripted = iter(suites)

    def _run_suite(gates, **_kwargs):
        # The paths the session actually hands the runner. Captured because
        # the cell tests name `GATES_MOUNT` themselves and so cannot tell
        # whether `_drive_cell` asked for the mount or for `/work` (§5.4).
        cell.gate_paths.append([str(path) for path in gates.values()])
        return next(scripted, [])

    monkeypatch.setattr("saffron.gates.runner.run_suite", _run_suite)
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


def _stub_the_export(monkeypatch, repo, policy=None, recorded=None):
    """`export_saffron_dir` with no mirror to `git archive` from: the working copy
    stands in for `base_sha`'s tree — except where `policy` makes the two
    diverge, which is the only thing that can tell them apart. The dest is
    the mount source, and the session reads its policy back out of it."""
    recorded = [] if recorded is None else recorded

    def _export(_mirror, _sha, dest):
        # Recorded beside the removals: the export clears `dest`, which is the
        # bind-mount source, so the order of the two is load-bearing.
        recorded.append(("export", str(dest)))
        shutil.rmtree(dest, ignore_errors=True)
        shutil.copytree(repo / ".saffron", dest / ".saffron")
        if policy is not None:
            (dest / ".saffron" / "policy.yaml").write_text(policy)
        return dest

    monkeypatch.setattr("saffron.repos.mirror.export_saffron_dir", _export)


def _drive(
    monkeypatch,
    tmp_path,
    *,
    cell,
    turns,
    spec=None,
    policy="gates: {}\n",
    base_policy=None,
    gates=(),
):
    """Run one whole cell against the stubbed runtime and return its outcome."""
    repo = tmp_path / "repo"
    (repo / ".saffron" / "gates").mkdir(parents=True)
    for name in gates:
        # `load_policy` refuses a declared gate whose executable is missing
        # or not +x, so a policy naming one needs a real file behind it.
        executable = repo / ".saffron" / "gates" / name
        executable.write_text("#!/bin/sh\nexit 0\n")
        executable.chmod(0o755)
    (repo / ".saffron" / "policy.yaml").write_text(policy)

    _stub_the_export(monkeypatch, repo, base_policy, cell.removed)

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


def test_the_proxy_starts_before_anything_the_probe_reads(monkeypatch, tmp_path):
    """The ordering that cost a run: on apple/container 1.3.0 a container on the
    internal network before the proxy leaves the proxy with no route out, and
    `assert_host_is_unreachable` is such a container. Asserted rather than
    described, because a comment is not a boundary."""
    cell = _stub_the_runtime(monkeypatch)
    _drive(monkeypatch, tmp_path, cell=cell, turns=[_turn(_block(_PLAN)), _turn()])
    assert cell.preflight[:4] == ["proxy", "egress", "enumerate", "probe"]
    # What answered, not merely that something did — the same reason the port
    # count is on the line beside it.
    (reaches,) = [x for x in cell.watched if "proxy reaches" in x]
    assert reaches == "preflight: proxy reaches api.anthropic.com (401)"


def test_a_proxy_that_reaches_nothing_aborts_before_the_cell_is_built(
    monkeypatch, tmp_path
):
    """§5.1.1. The run this exists for spent a whole attempt to learn it: every
    layer reported success and the first use of the network was the agent's."""
    cell = _stub_the_runtime(monkeypatch)

    def refuse(*a, **k):
        cell.preflight.append("egress")
        raise runtime.CellRuntimeError("the proxy at 10.88.0.2 could not reach it")

    monkeypatch.setattr("saffron.preflight.assert_proxy_reaches_upstream", refuse)
    with pytest.raises(runtime.CellRuntimeError):
        _drive(monkeypatch, tmp_path, cell=cell, turns=[_turn()])
    # Nothing was built and nothing was enumerated: the answer cost a container.
    assert cell.turns == []
    assert cell.preflight == [
        "proxy",
        "egress",
        "read-denied",
        "read-failed",
        "stop",
    ]


def test_no_cell_is_created_until_the_host_probe_has_passed(monkeypatch, tmp_path):
    """N1's structural half, and the half the reorder could have cost: the probe
    may now run with the proxy up, but never with a cell up."""
    cell = _stub_the_runtime(monkeypatch)

    def refuse(*a, **k):
        cell.preflight.append("probe")
        raise runtime.CellRuntimeError("host services answered from inside a cell")

    monkeypatch.setattr("saffron.preflight.assert_host_is_unreachable", refuse)
    with pytest.raises(runtime.CellRuntimeError):
        _drive(monkeypatch, tmp_path, cell=cell, turns=[_turn()])
    # The proxy is a sibling and is allowed to exist; a cell is not.
    assert cell.turns == []
    assert not cell.exported
    # And the sibling it did start does not survive the failure.
    assert cell.preflight == [
        "proxy",
        "egress",
        "enumerate",
        "probe",
        "read-denied",
        "read-failed",
        "stop",
    ]


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


def test_a_proposed_scope_reaches_scope_review_and_spends_no_further_turns(
    monkeypatch, tmp_path
):
    """The whole cell, not just the checkpoint: a proposal accepted on turn one
    ends the attempt there — no IMPLEMENT turn, no gate suite, no REVIEW.

    The turn count is the guard, not the script: `_drive` falls back to a clean
    review turn rather than raising, so reaching for a second turn would pass
    silently. `len(cell.turns) == 1` is what actually catches it."""
    cell = _stub_the_runtime(monkeypatch)
    outcome, ledger = _drive(
        monkeypatch, tmp_path, cell=cell, turns=[_turn(_block(_PROPOSAL))]
    )
    assert outcome.state == "SCOPE_REVIEW"
    assert outcome.scope_root_cause == _PROPOSAL["root_cause"]
    assert "infra/deploy.tf" in outcome.proposed_touches
    # Host-added, never asked of the model (§5.2's writeback rule). This repo
    # has no `.saffron/specs` at all, so it pins the *fallback* spelling; the
    # resolved-from-frontmatter case is
    # `test_the_recorded_spec_path_is_the_real_file_not_a_name_guess`.
    assert ".saffron/specs/SY-1-*.md" in outcome.proposed_touches
    assert len(cell.turns) == 1
    # One call: the baseline, taken before any agent turn (§5.4's own rule to
    # catch PREFLIGHT_FAILED). No second suite ran after the proposal.
    assert len(cell.gate_paths) == 1
    task = ledger.queue_lines()[0]
    assert task["state"] == "SCOPE_REVIEW"

    task_dir = tmp_path / "out" / "SY-1"
    recorded = json.loads((task_dir / "scope_proposal.json").read_text())
    assert recorded["proposed_touches"] == outcome.proposed_touches
    assert recorded["root_cause"] == _PROPOSAL["root_cause"]
    assert json.loads(recorded["raw"]) == _PROPOSAL


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
        # Equal unstacked, and recorded separately so a stacked task's record
        # says what its diff is relative to rather than what pinned its gates.
        "tree_base": "b" * 40,
        "head_sha": "c" * 40,
        "files": ["src/x.py"],
    }


def test_dirty_paths_is_read_after_run_suite_on_both_calls(monkeypatch, tmp_path):
    """A gate that writes an uncommitted artifact (`.coverage`, a build dir)
    must show up on baseline and head alike, or `committed` reports it only at
    head with nothing on the other side for the subtraction to cancel (§5.4)."""
    cell = _stub_the_runtime(monkeypatch)
    order: list[str] = []

    def _run_suite(*_a, **_k):
        order.append("run_suite")
        return []

    def _dirty_paths(_container):
        order.append("dirty_paths")
        return []

    monkeypatch.setattr("saffron.gates.runner.run_suite", _run_suite)
    monkeypatch.setattr("saffron.cell.worktree.dirty_paths", _dirty_paths)

    outcome, _ledger = _drive(
        monkeypatch, tmp_path, cell=cell, turns=[_turn(_block(_PLAN)), _turn()]
    )
    assert outcome.state == "READY_FOR_REVIEW"
    # One suite call apiece for the baseline and the (green) first attempt.
    assert order == ["run_suite", "dirty_paths", "run_suite", "dirty_paths"]


def test_the_suite_execs_the_gates_from_the_mount_never_the_worktree(
    monkeypatch, tmp_path
):
    """Both suites take their executables from `/gates` — the host's read-only
    export at `base_sha` — and never from `/work`, which the agent can rewrite
    and commit (§5.4).

    `tests/test_worktree.py` proves the mount is read-only and that a gate suite
    from it beats the lying one in `/work`, but it names `GATES_MOUNT` itself,
    so it cannot tell whether `_drive_cell` asked for the mount. This pins the
    call: repointing it at `WORKTREE_MOUNT` is otherwise green.
    """
    cell = _stub_the_runtime(monkeypatch)
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn()],
        policy="gates:\n  tests: {}\n",
        gates=("tests",),
    )
    assert outcome.state == "READY_FOR_REVIEW"
    # Baseline and head alike, and the whole path — not just its prefix: the
    # mount holds the exported tree, so the gate sits under its own .saffron/.
    assert cell.gate_paths == [["/gates/.saffron/gates/tests"]] * 2


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


def test_the_outcome_carries_what_only_teardown_can_learn(monkeypatch, tmp_path):
    """Both fields are read after the cell is dead and after every `return`
    inside the driver. Unset, every squashed commit body reads `cell head
    (unknown)` and lists no agent commits (§5.7)."""
    cell = _stub_the_runtime(monkeypatch, subjects=["fix the tz default", "add a test"])

    outcome, _ledger = _drive(
        monkeypatch, tmp_path, cell=cell, turns=[_turn(_block(_PLAN)), _turn()]
    )

    assert outcome.cell_head_sha == "c" * 40
    assert outcome.agent_subjects == ["fix the tz default", "add a test"]
    # From the spec's base, or the list is every commit in the repo's history.
    assert cell.subjects_from == "b" * 40


def test_the_agents_subjects_survive_an_export_that_dies(monkeypatch, tmp_path):
    """A missing subject list is not worth losing a package over, and neither
    half of teardown may take the other down with it."""
    cell = _stub_the_runtime(monkeypatch, subjects=["fix the tz default"])

    def _dies(_container, _sha):
        # The gates read the diff first; the cell dies once the outcome is
        # decided, exactly as in the export-failure test above.
        if any(line.startswith("teardown") for line in cell.watched):
            raise runtime.CellRuntimeError("no such cell")
        return _DIFF

    monkeypatch.setattr("saffron.cell.worktree.export_patch", _dies)
    outcome, _ledger = _drive(
        monkeypatch, tmp_path, cell=cell, turns=[_turn(_block(_PLAN)), _turn()]
    )

    assert outcome.agent_subjects == ["fix the tz default"]
    assert outcome.cell_head_sha is None
    assert any("export FAILED" in line for line in cell.watched)


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


def test_a_forbidden_path_inside_touches_fails_the_suite(monkeypatch, tmp_path):
    """`spec.forbidden` was read into the plan checkpoint (`validate_plan`)
    and never against the diff (SA-0024's Context) — an agent that declares
    one plan and commits another left it invisible. `src/secret.py` is inside
    the default touches (`src/**`), is not named in the plan's
    `files_to_change` (so `validate_plan` never sees it), and would pass
    `scope` before this change; `spec.forbidden` denies it specifically,
    driven through the real suite rather than by calling `scope_gate`
    directly."""
    cell = _stub_the_runtime(
        monkeypatch, changed=("src/secret.py",), suites=([], [], [])
    )
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn(), _turn()],
        spec=_spec(forbidden=["src/secret.py"]),
    )
    assert outcome.state == "EXHAUSTED"
    # The repair prompt is the whole of what the agent receives about a gate.
    assert (
        "- [scope] src/secret.py:? forbidden: "
        "denied by this spec's forbidden list: src/secret.py"
    ) in cell.turns[2]


def test_a_protected_path_inside_touches_fails_the_suite(monkeypatch, tmp_path):
    """`policy.protected` reaches the same `scope_gate` call `spec.forbidden`
    does, proven from the real policy YAML `_drive` writes to
    `.saffron/policy.yaml` rather than a hand-built list. `src/secret.py` is
    again absent from the plan's `files_to_change`, so `validate_plan` never
    refuses it at the checkpoint."""
    cell = _stub_the_runtime(
        monkeypatch, changed=("src/secret.py",), suites=([], [], [])
    )
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn(), _turn()],
        policy="gates: {}\nprotected:\n  - src/secret.py\n",
    )
    assert outcome.state == "EXHAUSTED"
    assert (
        "- [scope] src/secret.py:? protected: "
        "denied by the repo's protected list: src/secret.py"
    ) in cell.turns[2]


def test_a_size_failure_at_standard_does_not_enter_the_repair_loop(
    monkeypatch, tmp_path
):
    """§5.4/§5.6: `size` is advisory at `standard` — a task must not pay a
    repair turn for it, and it must not be a task's problem."""
    cell = _stub_the_runtime(monkeypatch)
    _grow_the_diff_after_the_first_turn(monkeypatch, cell)
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn()],
        spec=_spec(spec_type="bug"),
    )
    assert outcome.state == "READY_FOR_REVIEW"
    # No repair turn was bought — REVIEW's own lens turns are the only ones
    # past IMPLEMENT, and none of them carry a repair prompt.
    assert not any("These failures are new" in turn for turn in cell.turns)
    assert not any(nf.gate == "size" for nf in outcome.new_failures)
    # Still reported, host-side, beside `scope` and `integrity`: a gate
    # nothing reads is not a gate, and neither is one whose result vanishes
    # because it never blocked.
    (size_result,) = [g for g in outcome.gates if g.gate == "size"]
    assert size_result.status == "fail"
    # Carried on the outcome, so a caller downstream of `_drive_cell` — the PR
    # body, the queue line — has the effective tier and the advisory set to
    # render, rather than re-deriving them from `spec.risk` alone.
    assert outcome.effective_risk == "standard"
    assert outcome.advisory_gates == ["size"]


_HIDDEN_DIFF = (
    "diff --git a/src/x.py b/src/x.py\n"
    "index 1111111..2222222 100644\n"
    "Binary files a/src/x.py and b/src/x.py differ\n"
)


_INTEGRITY_POLICY = 'gates: {}\nintegrity:\n  suppressions: ["# noqa"]\n'


def test_size_does_not_refuse_an_unreadable_diff_at_a_tier_it_cannot_block(
    monkeypatch, tmp_path
):
    """`size` refuses a diff it cannot measure with `error`, and `error` reaches
    `aborted_gates` before any advisory filter — so at `standard`, where §5.6
    says the gate stops nothing, the refusal would end the attempt instead.

    Driven under a policy that declares integrity patterns, because every real
    repo does and the default `gates: {}` makes `integrity` *skip*: asserting
    `READY_FOR_REVIEW` here would be green for a reason unrelated to `size`.
    What this pins is `size`'s own result. The attempt still ends, and the next
    test says which gate ends it — a distinction `outcome.state` alone cannot
    make.
    """
    cell = _stub_the_runtime(monkeypatch)
    _grow_the_diff_after_the_first_turn(monkeypatch, cell, big=_HIDDEN_DIFF)
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn()],
        spec=_spec(spec_type="bug"),
        policy=_INTEGRITY_POLICY,
    )
    (size_result,) = [g for g in outcome.gates if g.gate == "size"]
    assert size_result.status != "error"
    # And it says what it could not read, so an advisory count with a hole in
    # it is never reported as a plain number.
    assert "unreadable" in size_result.summary


def test_integrity_still_refuses_that_diff_at_every_tier(monkeypatch, tmp_path):
    """The ceiling on the test above, asserted rather than described: making
    `size` quiet at `standard` does not make the attempt survive, because
    `integrity` answers the identical shape with no tier awareness at all.

    A repo declaring no integrity patterns is the only one that sees the
    difference. If this ever goes green, `integrity`'s rule moved and `size`'s
    `blocking` switch became load-bearing on its own.
    """
    cell = _stub_the_runtime(monkeypatch)
    _grow_the_diff_after_the_first_turn(monkeypatch, cell, big=_HIDDEN_DIFF)
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn()],
        spec=_spec(spec_type="bug"),
        policy=_INTEGRITY_POLICY,
    )
    assert outcome.state == "GATE_ERROR"
    (integrity_result,) = [g for g in outcome.gates if g.gate == "integrity"]
    assert integrity_result.status == "error"


def test_without_integrity_patterns_the_standard_tier_attempt_survives(
    monkeypatch, tmp_path
):
    """The case `size`'s switch is for: nothing else refuses the diff, so a
    task adding a binary asset at `standard` reaches review instead of being
    abandoned as infrastructure."""
    cell = _stub_the_runtime(monkeypatch)
    _grow_the_diff_after_the_first_turn(monkeypatch, cell, big=_HIDDEN_DIFF)
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn()],
        spec=_spec(spec_type="bug"),
    )
    assert outcome.state == "READY_FOR_REVIEW"


def test_the_same_unreadable_file_aborts_the_attempt_at_elevated_risk(
    monkeypatch, tmp_path
):
    """The other half: where the gate blocks, a diff it cannot measure must not
    read as one it measured and passed."""
    cell = _stub_the_runtime(monkeypatch)
    _grow_the_diff_after_the_first_turn(monkeypatch, cell, big=_HIDDEN_DIFF)
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn()],
        spec=_spec(spec_type="bug", risk="elevated"),
    )
    assert outcome.state == "GATE_ERROR"


def test_the_same_size_failure_repairs_at_elevated_risk(monkeypatch, tmp_path):
    """The identical diff, the identical ceiling — only the tier differs, and
    that is what decides whether the task has to answer for it (§5.6)."""
    cell = _stub_the_runtime(monkeypatch)
    _grow_the_diff_after_the_first_turn(monkeypatch, cell)
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn(), _turn()],
        spec=_spec(spec_type="bug", risk="elevated"),
    )
    assert outcome.state == "EXHAUSTED"
    # A repair turn *was* bought this time, and it was told about `size`.
    assert len(cell.turns) == 3
    assert "- [size] diff-too-large:" in cell.turns[2]
    assert any(nf.gate == "size" for nf in outcome.new_failures)
    assert outcome.effective_risk == "elevated"
    assert outcome.advisory_gates == []


def test_an_elevate_on_match_elevates_a_standard_spec_for_the_suite(
    monkeypatch, tmp_path
):
    """§5.6's second clause, wired rather than proved in isolation: a path the
    repo names in `elevate_on` elevates the tier even though the spec itself
    never asked to be `elevated`."""
    cell = _stub_the_runtime(monkeypatch, changed=("src/x.py",))
    _grow_the_diff_after_the_first_turn(monkeypatch, cell)
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn(), _turn()],
        spec=_spec(spec_type="bug"),
        policy="gates: {}\nelevate_on:\n  - src/**\n",
    )
    assert outcome.state == "EXHAUSTED"
    assert len(cell.turns) == 3
    assert any(nf.gate == "size" for nf in outcome.new_failures)
    # The spec itself is still `standard` — it is the path match that elevated
    # this attempt, and the outcome must carry *that*, not `spec.risk`.
    assert outcome.effective_risk == "elevated"


def test_a_declared_gate_with_blocking_false_does_not_repair(monkeypatch, tmp_path):
    """A repo's own `blocking: false` behaves the same at every tier — reported,
    never repaired — which is a different rule from `size`'s tier switch."""
    failing_lint = [
        GateResult(
            gate="lint",
            status="fail",
            tool="ruff 1.0",
            failures=[Failure(file="a.py", code="E501", message="too long")],
        )
    ]
    cell = _stub_the_runtime(monkeypatch, suites=([], failing_lint, failing_lint))
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn()],
        policy="gates:\n  lint: { blocking: false }\n",
        gates=("lint",),
    )
    assert outcome.state == "READY_FOR_REVIEW"
    assert not any("These failures are new" in turn for turn in cell.turns)
    assert not any(nf.gate == "lint" for nf in outcome.new_failures)
    (lint_result,) = [g for g in outcome.gates if g.gate == "lint"]
    assert lint_result.status == "fail"
    # `size` is also advisory here — the spec is `standard` and nothing
    # declared an `elevate_on` match — beside `lint`'s own `blocking: false`.
    assert outcome.advisory_gates == ["lint", "size"]


def test_the_task_is_recorded_with_the_specs_declared_risk(monkeypatch, tmp_path):
    """The best the ledger's `risk` column can carry (§5.6): no diff exists yet
    at `create_task`, so an `elevate_on` match cannot be reflected here — only
    what the spec itself declared."""
    cell = _stub_the_runtime(monkeypatch)
    _outcome, ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn()],
        spec=_spec(risk="elevated"),
    )
    (line,) = ledger.queue_lines()
    assert line["risk"] == "elevated"


def test_a_test_missing_at_head_reaches_the_agent_as_a_census_failure(
    monkeypatch, tmp_path
):
    """The head-side wiring, through `_drive_cell` rather than around it.

    Both tests below call `census_gate` directly, so both stayed green under
    two mutations that make the branch's whole purpose vanish: `_suite([])` at
    the head call (census becomes a permanent `skip`) and `census_gate` with
    its two sides swapped (nothing is ever reported removed). This one runs
    the real suite closure, so it is the one that goes red.
    """

    def _tests(*names):
        return [
            GateResult(
                gate="tests",
                status="pass",
                tool="pytest 8.3.2",
                collected=list(names),
            )
        ]

    cell = _stub_the_runtime(
        monkeypatch,
        suites=(
            _tests("t.py::test_a", "t.py::test_b"),
            _tests("t.py::test_a"),
            _tests("t.py::test_a"),
        ),
    )
    outcome, ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn(), _turn()],
    )

    # `fail`, not `error`: the code is wrong, and the agent is asked to fix it.
    assert outcome.state == "EXHAUSTED"
    assert (
        "- [census] t.py::test_b:? removed-test: collected at base_sha, absent at head"
        in cell.turns[2]
    )
    # And the baseline it was measured against is the one with both names.
    assert (
        json.loads((tmp_path / "out" / "SY-1" / "baseline.json").read_text())[-1][
            "status"
        ]
        == "skip"
    )
    assert [
        row["status"]
        for row in ledger._db.execute(
            "SELECT status FROM gate_results WHERE gate = 'census' AND run_id IS NULL"
        )
    ] == ["fail", "fail"]


def test_the_baseline_suite_skips_census_because_there_is_no_base_yet():
    """`_suite([])` is the baseline call. A census with nothing to compare is
    a skip, not a report that every test was removed."""
    from saffron.gates.core.census import census_gate

    assert census_gate(base=[], head=[]).status == "skip"


def test_a_census_that_skips_at_baseline_and_fails_at_head_is_not_suite_drift():
    """The shape production actually produces. `_suite` appends `census`
    unconditionally, so the baseline holds a `census` `skip` — not a missing
    gate. The branch that protects the wiring is therefore `suite_drift`'s
    `was.status != "skip"` guard, not its `was is None` one, and a fixture
    built head-only would pin a branch the real suite never reaches."""
    from saffron.gates.baseline import subtract_baseline, suite_drift
    from saffron.gates.contract import Failure, GateResult

    baseline = [
        GateResult(gate="tests", status="pass", tool="pytest 8.3.2"),
        GateResult(gate="census", status="skip"),
    ]
    head = [
        GateResult(gate="tests", status="pass", tool="pytest 8.3.2"),
        GateResult(
            gate="census",
            status="fail",
            failures=[Failure(file="t.py::test_a", code="removed-test")],
        ),
    ]
    assert suite_drift(head, baseline) == []
    assert [n.gate for n in subtract_baseline(head, baseline)] == ["census"]


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

    results = {
        r["gate"]: r
        for r in json.loads((tmp_path / "out" / "SY-1" / "baseline.json").read_text())
    }
    assert results["scope"]["status"] == "pass"
    assert results["scope"]["failures"] == []
    assert results["scope"]["summary"] == "0 changed files within touches"
    # The default test policy ("gates: {}") declares no integrity patterns,
    # so integrity has nothing to check and skips — same as census, nothing
    # for the subtraction to cancel a real escape against.
    assert results["integrity"]["status"] == "skip"
    assert results["census"]["status"] == "skip"

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
    # A clean tree has nothing to checkpoint — the host must not commit an
    # empty no-op just because a turn was cut.
    assert cell.checkpointed == []


def test_a_repair_turn_cut_mid_edit_gets_a_host_checkpoint_commit(
    monkeypatch, tmp_path
):
    """The agent's own "commit as you go" is a prompt, and a prompt is not the
    boundary (§0). Real edits left dirty when a turn is cut are host-committed
    so they survive into the next attempt's gate check instead of vanishing
    with the container."""
    failing = Failure(file="a.py", code="E501", message="too long")
    cell = _stub_the_runtime(monkeypatch, suites=([], _results(failing), []))

    def _dirty_paths(_container):
        # Dirty exactly once: right after the repair turn is cut, before the
        # host checkpoints it. Clean on the baseline and every other check —
        # a mock that stayed dirty forever would fail `committed` on the
        # *next* suite too and corrupt the scripted `suites=` sequence above.
        return (
            ["scheduler.py"] if len(cell.turns) == 3 and not cell.checkpointed else []
        )

    monkeypatch.setattr("saffron.cell.worktree.dirty_paths", _dirty_paths)

    outcome, _ledger = _drive(
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
    assert len(cell.checkpointed) == 1
    assert "checkpoint" in cell.checkpointed[0]


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
    _stub_the_export(monkeypatch, repo)
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


def _rejected(resets_at=1755800000, cost=0.0):
    """What a closed window actually looks like coming back: the CLI reports the
    rejection and the turn errors."""
    return implement.AttemptResult(
        session_id="sess-1",
        subtype="success",
        terminal_reason="api_error",
        num_turns=0,
        cost_usd_est=cost,
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


def test_a_tunnel_the_proxy_could_not_open_reaches_the_operator(monkeypatch, tmp_path):
    """The failure that shipped: nothing was denied, so the denial report was
    correctly silent, and a proxy with no route out looked like an API outage
    for a whole run."""
    cell = _stub_the_runtime(monkeypatch)
    cell.failed = [
        "1755800001.2 35022 10.88.0.3 TCP_TUNNEL/503 0 CONNECT api.anthropic.com:443 - HIER_NONE/- -"
    ]
    _drive(monkeypatch, tmp_path, cell=cell, turns=[_turn(_block(_PLAN)), _turn()])
    assert any(
        "proxy FAILED" in line and "api.anthropic.com" in line for line in cell.watched
    )


def test_a_plan_turn_that_failed_reports_what_it_spent(monkeypatch, tmp_path):
    """The cost is measured — it is on the watch line — and then dropped from
    the outcome. `CellOutcome` is the seam v1's supervisor inherits, and one
    summing `spent_usd` across tasks would book every plan failure at zero."""
    cell = _stub_the_runtime(monkeypatch)
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[implement.AgentFailed("max turns", _turn(cost=0.4))],
    )
    assert outcome.state == "NOT_IMPLEMENTED"
    assert outcome.spent_usd == 0.4
    assert any("$0.40 spent" in line for line in cell.watched)


def test_a_plan_rejected_on_shape_reports_both_turns_it_spent(monkeypatch, tmp_path):
    """The checkpoint's other exit. A shape rejection is final only after the
    one re-prompt has also run, so two turns are paid for before the plan is
    refused — and `PlanRejected`'s "no implementation token is spent" is about
    implementation, not about the checkpoint."""
    cell = _stub_the_runtime(monkeypatch)
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        # Neither turn returns the schema: the first is re-prompted, the second
        # is final.
        turns=[_turn("not a plan", cost=0.4), _turn("still not a plan", cost=0.4)],
    )
    assert outcome.state == "PLAN_REJECTED"
    assert outcome.spent_usd == 0.8
    assert any("$0.80 spent" in line for line in cell.watched)


# Not a path _ANCHORING_DIFF touches, so it cannot anchor however real it reads.
_UNANCHORABLE = {
    "findings": [
        {
            "file": "src/never-touched.py",
            "line": 4,
            "severity": "concern",
            "claim": "a claim about a file the diff does not contain",
        }
    ]
}


def test_a_review_records_the_findings_it_dropped_as_well_as_the_ones_it_kept(
    monkeypatch, tmp_path
):
    """§4.1: dropped findings are kept, because the drop rate is the signal that
    a lens is badly prompted — and it is a SQL question, not a JSON one."""
    cell = _stub_the_runtime(monkeypatch, patch=_ANCHORING_DIFF)
    _rebuttable(monkeypatch, cell, rebut_commits=0)
    _outcome, ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[
            _turn(_block(_PLAN)),
            _turn(),
            _turn(_block(_BLOCKER)),
            _turn(_block(_UNANCHORABLE)),
            _turn("I have addressed the findings."),
            _turn(_block(_CLAIMED_FIX)),
        ],
    )
    (task_id,) = [row["task_id"] for row in ledger.queue_lines()]
    rows = ledger.findings(task_id)
    assert [(r["lens"], r["claim"], r["anchored"]) for r in rows] == [
        ("correctness", "x returns nothing", 1),
        ("contract", "a claim about a file the diff does not contain", 0),
    ]


def test_a_verdict_lands_on_the_finding_the_review_recorded(monkeypatch, tmp_path):
    """`verdict` and `rebuttal` had nowhere to go but `rebuttal.json` (§4.1)."""
    cell = _stub_the_runtime(monkeypatch, patch=_ANCHORING_DIFF)
    _rebuttable(monkeypatch, cell, rebut_commits=1)
    _outcome, ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=_through_rebut(
            _turn("It is intentional."),
            _turn(
                _block(
                    {
                        "rebuttals": [
                            {"finding": 1, "action": "argued", "argument": "by design"}
                        ]
                    }
                )
            ),
            _turn(
                _block(
                    {
                        "verdicts": [
                            {"finding": 1, "verdict": "withdrawn", "reason": "fair"}
                        ]
                    }
                )
            ),
        ),
    )
    (task_id,) = [row["task_id"] for row in ledger.queue_lines()]
    (row,) = ledger.findings(task_id)
    # The action rides along: "fixed" and "argued" are the difference §4.6 asks
    # about, and the column is the only place left holding it.
    assert (row["verdict"], row["rebuttal"]) == ("withdrawn", "argued: by design")


def test_a_successful_outcome_carries_its_attempts_failures_reviews_and_rebuttal(
    monkeypatch, tmp_path
):
    """No test exercises these four on `CellOutcome`'s success path."""
    cell = _stub_the_runtime(monkeypatch, patch=_ANCHORING_DIFF)
    _rebuttable(monkeypatch, cell, rebut_commits=1)
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=_through_rebut(
            _turn("It is intentional."),
            _turn(
                _block(
                    {
                        "rebuttals": [
                            {"finding": 1, "action": "argued", "argument": "by design"}
                        ]
                    }
                )
            ),
            _turn(
                _block(
                    {
                        "verdicts": [
                            {"finding": 1, "verdict": "withdrawn", "reason": "fair"}
                        ]
                    }
                )
            ),
        ),
    )
    assert outcome.state == "READY_FOR_REVIEW"
    assert outcome.attempts >= 1
    assert outcome.new_failures == []
    assert outcome.reviews
    assert outcome.rebut_result is not None


def test_a_rebuttal_numbered_badly_records_the_answer_that_was_asked_for(
    monkeypatch, tmp_path
):
    """Nothing validates the rebuttal turn's numbering the way `run_verdict`
    validates a verdict set, so the write does: the first answer to a blocker
    stands, and a number nobody asked about is dropped. Letting a duplicate
    overwrite is how a *later* blocker ends up reading as unanswered when the
    implementer's own `rebuttal.json` says otherwise."""
    cell = _stub_the_runtime(monkeypatch, patch=_ANCHORING_DIFF)
    _rebuttable(monkeypatch, cell, rebut_commits=1)
    _outcome, ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=_through_rebut(
            _turn("It is intentional."),
            _turn(
                _block(
                    {
                        "rebuttals": [
                            {"finding": 1, "action": "argued", "argument": "first"},
                            {"finding": 1, "action": "fixed", "argument": "second"},
                            {"finding": 7, "action": "fixed", "argument": "nobody"},
                        ]
                    }
                )
            ),
            _turn(
                _block(
                    {
                        "verdicts": [
                            {"finding": 1, "verdict": "withdrawn", "reason": "fair"}
                        ]
                    }
                )
            ),
        ),
    )
    (task_id,) = [row["task_id"] for row in ledger.queue_lines()]
    (row,) = ledger.findings(task_id)
    assert row["rebuttal"] == "argued: first"


def test_what_the_task_spent_is_the_sum_of_the_turns_it_ran(monkeypatch, tmp_path):
    """The equality is the point: `spent_usd_est` is derived from `attempts`, so
    a turn that spends without opening a row makes the two disagree. Every
    phase's turns are counted here — plan, implement, both lenses, rebuttal."""
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
    (line,) = ledger.queue_lines()
    assert line["spent_usd_est"] == pytest.approx(outcome.spent_usd)
    assert line["spent_usd_est"] > 0
    assert [row["phase"] for row in ledger.attempts(outcome.task_id)] == [
        "IMPLEMENTING",
        "IMPLEMENTING",
        "REVIEWING",
        "REVIEWING",
        "REBUTTING",
        "REBUTTING",
    ]


def test_a_walled_turn_that_spent_is_still_charged(monkeypatch, tmp_path):
    """The raise comes from outside the turn — `stop_on_rejected` wraps
    `record_attempts` — so it lands past the `spent +=` and the in-frame tally
    loses the walled turn. The attempt was written before the raise, so the
    outcome reads the roll-up rather than reporting the gap."""
    cell = _stub_the_runtime(monkeypatch)
    outcome, ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn(), _rejected(cost=0.07)],
    )
    assert outcome.state == "RATE_LIMITED"
    # Plan, implement, and the lens turn the provider walled.
    assert outcome.spent_usd == pytest.approx(0.27)
    (line,) = ledger.queue_lines()
    assert line["spent_usd_est"] == pytest.approx(outcome.spent_usd)


def test_the_suite_runs_the_gates_base_sha_declares_not_the_working_copys(
    monkeypatch, tmp_path
):
    """Item 13: the executables came from `base_sha` while the policy naming
    them came from the operator's checkout, so the two diverged on any branch
    touching `.saffron/`. Both trees hold both executables here — only the
    declaration differs, so nothing but the policy's source can decide this."""
    cell = _stub_the_runtime(monkeypatch)
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn()],
        policy="gates:\n  lint: {}\n",
        base_policy="gates:\n  tests: {}\n",
        gates=("lint", "tests"),
    )
    assert outcome.state == "READY_FOR_REVIEW"
    assert cell.gate_paths == [["/gates/.saffron/gates/tests"]] * 2


def test_policy_sha_records_the_policy_that_governed_not_the_one_on_disk(
    monkeypatch, tmp_path
):
    """The ledger's record of what ran has to be the record of what was
    declared, or `policy_sha` names a file no gate was resolved against."""
    base_policy = "gates: {}\nprotected:\n  - DESIGN.md\n"
    cell = _stub_the_runtime(monkeypatch)
    _outcome, ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn()],
        policy="gates: {}\n",
        base_policy=base_policy,
    )
    (row,) = ledger._db.execute("SELECT policy_sha FROM repos").fetchall()
    assert row["policy_sha"] == hashlib.sha256(base_policy.encode()).hexdigest()


def test_the_stale_container_is_gone_before_the_export_clears_its_mount_source(
    monkeypatch, tmp_path
):
    """The export rmtrees `<task_dir>/gates`, which is the bind mount a
    SIGKILLed run of the same spec can still have live at `/gates`. Deleting a
    mount source out from under a running container is what the pre-clean
    ordering exists to prevent, and position is the only thing enforcing it."""
    cell = _stub_the_runtime(monkeypatch)
    _drive(monkeypatch, tmp_path, cell=cell, turns=[_turn(_block(_PLAN)), _turn()])
    kinds = [kind for kind, _name in cell.removed]
    assert kinds.index("container") < kinds.index("export")


def test_a_base_with_no_saffron_dir_never_reaches_the_image_build(
    monkeypatch, tmp_path
):
    """The hoist's claim, which nothing else pins: the export runs before the
    image build, the host probe and the proxy, and before the ledger has a run
    to leave behind. Sunk back into the try and this goes red."""
    repo = tmp_path / "repo"
    (repo / ".saffron" / "gates").mkdir(parents=True)
    (repo / ".saffron" / "policy.yaml").write_text("gates: {}\n")

    built = []
    cell = _stub_the_runtime(monkeypatch)
    monkeypatch.setattr(
        "saffron.repos.image.build_cell_image", lambda repo: built.append(repo)
    )

    def _unonboarded(*_args, **_kwargs):
        raise mirror.GitError("deadbeefcafe has no .saffron for the cell to run")

    monkeypatch.setattr("saffron.repos.mirror.export_saffron_dir", _unonboarded)

    ledger = Ledger(tmp_path / "ledger.db")
    with pytest.raises(mirror.GitError, match="has no .saffron"):
        session.run_one_cell(
            _spec(),
            repo=repo,
            mirror=tmp_path / "m.git",
            ledger=ledger,
            out_dir=tmp_path / "out",
        )
    assert built == []
    assert ledger._db.execute("SELECT * FROM runs").fetchall() == []
    # The stale-container pre-clean is the only thing that ran, and it creates
    # nothing: no network, no volume, nothing for teardown to report.
    assert cell.removed == [("container", "saffron-cell-SY-1")]


def test_a_policy_fault_at_base_sha_names_base_sha(monkeypatch, tmp_path):
    """`load_policy` reports the path it read, which is now a batch-tree
    directory the operator has never opened. Left bare, the operator checks
    their own `policy.yaml`, finds it correct, and is back to the wrong
    diagnosis this whole change exists to remove."""
    repo = tmp_path / "repo"
    (repo / ".saffron" / "gates").mkdir(parents=True)
    (repo / ".saffron" / "policy.yaml").write_text("gates: {}\n")

    _stub_the_runtime(monkeypatch)
    _stub_the_export(monkeypatch, repo, policy="gates: [not, a, mapping]\n")

    with pytest.raises(policy_mod.PolicyError, match=r"at base b{12}: "):
        session.run_one_cell(
            _spec(),
            repo=repo,
            mirror=tmp_path / "m.git",
            ledger=Ledger(tmp_path / "ledger.db"),
            out_dir=tmp_path / "out",
        )


def test_the_criteria_gate_reads_both_suites_and_invokes_nothing(monkeypatch, tmp_path):
    """`census_gate(base, head)` is the shape, not `scope_gate`'s single tree.
    The baseline call hands `prior=[]`, so the gate skips there and no task
    reaches `PREFLIGHT_FAILED` because of it."""
    from saffron.intake import Criterion

    base = [
        GateResult(
            gate="tests", status="pass", tool="pytest 8", collected=["t.py::test_a"]
        )
    ]
    head = [
        GateResult(
            gate="tests",
            status="pass",
            tool="pytest 8",
            collected=["t.py::test_a", "t.py::test_new"],
        )
    ]
    cell = _stub_the_runtime(monkeypatch, suites=(base, head, head))
    outcome, _ledger = _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn()],
        spec=_spec(
            acceptance=[
                Criterion(claim="it works", witness="t.py::test_new"),
            ]
        ),
    )
    result = next(r for r in outcome.gates if r.gate == "criteria")
    assert result.status == "pass"
    assert result.tool is None


def test_the_criteria_gate_skips_for_a_spec_that_declares_no_witnesses(
    monkeypatch, tmp_path
):
    """Ten specs predate this key. `skip` is what they get, and every existing
    behaviour is unchanged."""
    cell = _stub_the_runtime(monkeypatch)
    outcome, _ledger = _drive(
        monkeypatch, tmp_path, cell=cell, turns=[_turn(_block(_PLAN)), _turn()]
    )
    result = next(r for r in outcome.gates if r.gate == "criteria")
    assert result.status == "skip"


def test_the_implement_prompt_names_the_witnesses_it_is_judged_against(
    monkeypatch, tmp_path
):
    """Only `spec.body` — the markdown, not the frontmatter — was ever
    substituted, and the witnesses live in frontmatter."""
    from saffron.intake import Criterion

    cell = _stub_the_runtime(monkeypatch)
    _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn()],
        spec=_spec(
            acceptance=[
                Criterion(claim="the box ticks", witness="tests/test_x.py::test_ticks")
            ]
        ),
    )
    prompt = cell.system_prompts[0]
    assert "tests/test_x.py::test_ticks" in prompt
    assert "the box ticks" in prompt


def test_a_spec_with_no_witnesses_shows_no_witness_heading(monkeypatch, tmp_path):
    cell = _stub_the_runtime(monkeypatch)
    _drive(monkeypatch, tmp_path, cell=cell, turns=[_turn(_block(_PLAN)), _turn()])
    assert "witnesses you are judged against" not in cell.system_prompts[0]


def test_the_review_lens_prompt_carries_the_claim_for_a_witnessed_spec(
    monkeypatch, tmp_path
):
    """Finding 1, PR #48 review: intake requires the markdown section absent
    when `acceptance:` is declared, and both REVIEW and REBUT substituted only
    `spec.body` — so a spec that opts into witnesses showed the critic no
    acceptance criteria at all. The IMPLEMENT prompt is `system_prompts[0]`;
    REVIEW invokes one session per lens straight after."""
    from saffron.intake import Criterion

    cell = _stub_the_runtime(monkeypatch)
    _drive(
        monkeypatch,
        tmp_path,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn()],
        spec=_spec(
            acceptance=[
                Criterion(claim="the box ticks", witness="tests/test_x.py::test_ticks")
            ]
        ),
    )
    review_prompts = cell.system_prompts[1:]
    assert review_prompts
    assert all("the box ticks" in p for p in review_prompts)


def test_a_proposed_scope_keeps_the_specs_declared_touches(monkeypatch, tmp_path):
    """The ratified set is a superset, not a replacement. The prompt asks the
    model for every path "inside or outside" the declared `touches`, but a
    prompt is not the boundary — the same argument the host-added spec path
    beside it already makes. A proposal of `["infra/deploy.tf"]` that replaced
    `touches` would ratify a scope omitting every file the task must edit, and
    the ratified attempt would then fail `scope` on its own work."""
    cell = _stub_the_runtime(monkeypatch)
    outcome, _ledger = _drive(
        monkeypatch, tmp_path, cell=cell, turns=[_turn(_block(_PROPOSAL))]
    )
    assert set(outcome.proposed_touches) >= {"src/**", "tests/**"}


def test_the_recorded_spec_path_is_the_real_file_not_a_name_guess(
    monkeypatch, tmp_path
):
    """Nothing ties a spec file's name to its `id` — `discover_specs` globs
    `*.md` and reads `id` from frontmatter — so a repo whose specs are not
    named `<id>-<slug>.md` got a glob matching no file, and the ratification's
    first commit would fail the `scope` gate it exists to satisfy."""
    specs = tmp_path / "repo" / ".saffron" / "specs"
    specs.mkdir(parents=True)
    (specs / "no-id-in-this-name.md").write_text(
        "---\nid: SY-1\ntitle: a filename that says nothing about its id\n"
        "type: feature\n---\n\n## Context\nx\n"
    )
    cell = _stub_the_runtime(monkeypatch)
    outcome, _ledger = _drive(
        monkeypatch, tmp_path, cell=cell, turns=[_turn(_block(_PROPOSAL))]
    )
    assert ".saffron/specs/no-id-in-this-name.md" in outcome.proposed_touches


def test_the_recorded_proposal_carries_the_hash_of_its_own_raw_block(
    monkeypatch, tmp_path
):
    """`plan.json` is the raw block verbatim, so `sha256sum plan.json` matches
    the watch line it was announced with. The proposal is wrapped in an
    envelope instead, so unless the envelope carries the hash the printed
    sha256 matches nothing on disk and the record cannot be re-derived."""
    cell = _stub_the_runtime(monkeypatch)
    outcome, _ledger = _drive(
        monkeypatch, tmp_path, cell=cell, turns=[_turn(_block(_PROPOSAL))]
    )
    record = json.loads((outcome.task_dir / "scope_proposal.json").read_text())
    assert record["sha256"] == artifacts.hash_artifact(record["raw"])
