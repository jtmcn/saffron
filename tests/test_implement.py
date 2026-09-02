from __future__ import annotations

import json

import pytest

from saffron.cell import runtime
from saffron.events import Agent, Event, describe
from saffron.gates.baseline import NewFailure
from saffron.gates.contract import Failure
from saffron.intake import Spec
from saffron.phases import implement


def test_the_permission_mode_denies_rather_than_asks():
    """In an unattended system, 'ask the operator' is not a fallback, it is a
    hang (DESIGN.md §5.3)."""
    options = implement.agent_options(
        system_prompt="s", cwd="/work", max_turns=40, budget_usd=12.0
    )
    assert options["permission_mode"] == "dontAsk"


def test_permissions_are_never_bypassed():
    options = implement.agent_options(
        system_prompt="s", cwd="/work", max_turns=40, budget_usd=12.0
    )
    assert options["permission_mode"] != "bypassPermissions"


def test_every_host_side_bound_is_set():
    options = implement.agent_options(
        system_prompt="s", cwd="/work", max_turns=40, budget_usd=12.0
    )
    assert options["max_turns"] == 40
    assert options["max_budget_usd"] == 12.0


def test_the_plan_prompt_names_the_scope_proposal_alternative():
    """SA-0018: the door plan_checkpoint opens must be named where the agent
    is asked for the plan, or nothing tells it the alternative exists."""
    assert "propose scope" in implement.PLAN_PROMPT


def test_the_salvage_prompt_asks_to_commit_not_implement():
    """SA-0028: the salvage turn's only job is a commit of what already
    exists — asking it to keep working is the defect this prompt exists to
    not repeat."""
    assert "commit" in implement.SALVAGE_PROMPT.lower()
    assert "do not keep implementing" in implement.SALVAGE_PROMPT.lower()
    assert implement.IMPLEMENT_PROMPT != implement.SALVAGE_PROMPT


def test_the_salvage_ceiling_is_far_below_an_ordinary_implement_turn():
    """A salvage that can itself run to 140 turns is the defect again
    (SA-0025: 141 turns, $11.68, zero commits)."""
    # Read off `intake`'s own default rather than a literal this test wrote:
    # a ratio against a number the assertion constructed proves nothing, and
    # it is the real default that decides whether five turns is "far below".
    ordinary = Spec.model_fields["max_turns"].default
    assert ordinary / 4 > implement.SALVAGE_MAX_TURNS
    # An absolute bound as well as a ratio: the ratio alone is satisfied by a
    # 14-turn salvage against this fixture's 60, and 14 turns is a second
    # implementation attempt however it compares to the first.
    assert implement.SALVAGE_MAX_TURNS <= 8


def test_the_cache_ttl_outlives_a_gate_suite():
    """The repair loop resumes across a gate suite, and a suite is minutes.
    The five-minute default expires every time (DESIGN.md §7.1)."""
    options = implement.agent_options(
        system_prompt="s", cwd="/work", max_turns=40, budget_usd=12.0
    )
    assert options["env"]["ENABLE_PROMPT_CACHING_1H"] == "1"


def test_agent_state_is_not_under_the_worktree():
    options = implement.agent_options(
        system_prompt="s", cwd="/work", max_turns=40, budget_usd=12.0
    )
    assert not options["env"]["CLAUDE_CONFIG_DIR"].startswith("/work")


def test_the_tools_are_withheld_and_not_merely_denied():
    """`allowed_tools` auto-approves; only `tools` decides what exists.
    Measured: with `allowed_tools` alone the model was offered every built-in."""
    options = implement.agent_options(
        system_prompt="s", cwd="/work", max_turns=40, budget_usd=12.0
    )
    assert options["tools"] == ["Read", "Write", "Edit", "Glob", "Grep", "Bash"]
    assert options["allowed_tools"] == options["tools"]


def test_the_offered_set_excludes_the_network_and_the_fan_out():
    """The offered set is what the model sees. Re-adding any of these puts it
    back in context, whatever the permission mode then does about it."""
    offered = set(
        implement.agent_options(
            system_prompt="s", cwd="/work", max_turns=40, budget_usd=12.0
        )["tools"]
    )
    withheld = {
        "WebFetch",
        "WebSearch",
        "Task",
        "Skill",
        "Workflow",
        "CronCreate",
        "ScheduleWakeup",
        "SendMessage",
    }
    assert not offered & withheld


def test_the_target_repo_cannot_configure_the_agent_working_on_it():
    """/work is the checkout the task itself can edit, so a repo's
    .claude/settings.json, agents and skills would reach its own reviewer (§2).
    Measured: a planted agent and skill loaded until this was pinned."""
    options = implement.agent_options(
        system_prompt="s", cwd="/work", max_turns=40, budget_usd=12.0
    )
    assert options["setting_sources"] == []


def test_a_crashed_attempt_falls_back_to_the_last_good_cost():
    """The runtime may report every cost field as zero on crash (§4.1)."""
    result = implement._reconcile_cost(reported=0.0, last_good=4.12, failed=True)
    assert result == 4.12


def test_a_clean_finish_keeps_its_reported_cost():
    assert implement._reconcile_cost(reported=3.5, last_good=2.0, failed=False) == 3.5


def _no_reap(container, **_kwargs):
    """These tests are about which bound ended the turn, not about the reap.

    Injected rather than left to the default: `reap_cell` execs `container`,
    which a unit test must not, and `tests/conftest.py` now refuses it.
    """
    return runtime.Completed(0, "", "")


class _stream:
    """A fake in-cell runner: the lines it prints, and how it exited.

    A callable object rather than a closure with attributes hung off it: an
    attribute assigned to a function is invisible to the `types` gate."""

    def __init__(self, *lines, returncode=0, stderr="", timed_out=False, bound=""):
        self._lines = lines
        self._returncode = returncode
        self._stderr = stderr
        self._timed_out = timed_out
        self._bound = bound
        self.request: dict = {}
        self.command: list[str] = []

    def __call__(self, container, command, *, stdin_data, on_line, **kwargs):
        self.request = json.loads(stdin_data)
        self.command = list(command)
        for line in self._lines:
            on_line(line)
        return runtime.Completed(
            self._returncode,
            "",
            self._stderr,
            timed_out=self._timed_out,
            bound=self._bound,
        )


def _recording_reap(reaped: list[str]):
    """Returns what the real `reap_cell` returns — `run_agent` declares the
    injection point as returning `Completed`, and a fake that returns None
    is a fake of a different function."""

    def _reap(container, **_kwargs):
        reaped.append(container)
        return runtime.Completed(0, "", "")

    return _reap


def _result_line(**overrides):
    event = {
        "type": "result",
        "subtype": "success",
        "num_turns": 5,
        "total_cost_usd": 0.75,
        "session_id": "sess-9",
        "terminal_reason": "completed",
        "is_error": False,
    }
    return json.dumps(event | overrides)


def test_the_stream_becomes_an_attempt_result():
    watched: list[Event] = []
    result = implement.run_agent(
        "cell",
        prompt="plan please",
        options={"max_turns": 3},
        spec_id="SY-1",
        emit=watched.append,
        exec_stream=_stream(
            json.dumps({"type": "system", "subtype": "init", "data": {}}),
            json.dumps({"type": "text", "text": "<output>{}"}),
            json.dumps({"type": "text", "text": "</output>"}),
            _result_line(),
        ),
    )
    assert result.session_id == "sess-9"
    assert result.num_turns == 5
    assert result.cost_usd_est == 0.75
    assert result.text == "<output>{}</output>"
    # Per event, so the operator sees the session as it happens, not at its end.
    assert len(watched) == 4


def test_an_absent_result_event_is_an_error_not_a_success():
    """A green result and an absent result are the same bytes unless something
    refuses to conflate them (DESIGN.md Appendix H, principle 34)."""
    with pytest.raises(implement.AgentFailed):
        implement.run_agent(
            "cell",
            prompt="p",
            options={},
            spec_id="SY-1",
            exec_stream=_stream(
                json.dumps({"type": "text", "text": "all done!"}), returncode=0
            ),
        )


def test_a_result_that_says_success_but_flags_an_error_is_not_a_success():
    """Measured against a real cell with no credential: the session reports
    `subtype="success"` with `is_error=true` and terminal_reason `api_error`.
    Keying on the subtype would call a session that did nothing a clean run."""
    with pytest.raises(implement.AgentFailed, match="api_error"):
        implement.run_agent(
            "cell",
            prompt="p",
            options={},
            spec_id="SY-1",
            exec_stream=_stream(
                _result_line(
                    subtype="success",
                    is_error=True,
                    terminal_reason="api_error",
                    total_cost_usd=0.0,
                ),
                returncode=1,
            ),
        )


def test_a_failed_turn_still_reports_what_it_spent():
    """A budget that drops a crashed attempt's cost silently stops counting."""
    with pytest.raises(implement.AgentFailed) as raised:
        implement.run_agent(
            "cell",
            prompt="p",
            options={},
            spec_id="SY-1",
            last_cost_usd=2.0,
            exec_stream=_stream(
                _result_line(subtype="error_max_turns", is_error=True, total_cost_usd=0)
            ),
        )
    attempt = raised.value.attempt
    assert attempt is not None
    assert attempt.cost_usd_est == 2.0


def test_a_turn_ceiling_is_named_rather_than_left_to_the_exit_code():
    """Measured on `SA-0005`: the session did correct work for 61 turns, was
    cut mid-edit, and the whole account of it was "exited 1". A turn ceiling is
    a bound like the other three and the exit code cannot show it."""
    with pytest.raises(implement.AgentFailed, match="ceiling of 60 turns"):
        implement.run_agent(
            "cell",
            prompt="p",
            options={"max_turns": 60},
            spec_id="SY-1",
            exec_stream=_stream(
                _result_line(subtype="error_max_turns", is_error=True), returncode=1
            ),
        )


def test_a_runner_killed_after_emitting_its_result_is_not_a_clean_turn():
    """§4.3's completion axis: a runner can emit a clean result event and then
    be killed holding stdout open. `is_error` is False and the subtype says
    success, so only `timed_out` tells this from a turn that finished."""
    with pytest.raises(implement.AgentFailed, match="timed out"):
        implement.run_agent(
            "cell",
            prompt="p",
            options={},
            spec_id="SY-1",
            exec_stream=_stream(_result_line(), timed_out=True),
            reap_cell=_no_reap,
        )


def test_a_clean_result_from_a_runner_that_exited_non_zero_is_not_a_success():
    """The other half of the same predicate: the result says success and
    nothing flags an error, but the process itself failed."""
    with pytest.raises(implement.AgentFailed, match="exited 1"):
        implement.run_agent(
            "cell",
            prompt="p",
            options={},
            spec_id="SY-1",
            exec_stream=_stream(_result_line(), returncode=1),
        )


def test_a_crash_reports_the_runners_own_error():
    with pytest.raises(implement.AgentFailed, match="CLIConnectionError"):
        implement.run_agent(
            "cell",
            prompt="p",
            options={},
            spec_id="SY-1",
            exec_stream=_stream(
                json.dumps({"type": "error", "error": "CLIConnectionError: no key"}),
                returncode=1,
            ),
        )


def test_a_line_that_is_not_an_event_is_shown_and_not_parsed():
    """Anything sharing the runner's stdout must not be read as an event."""
    watched: list[Event] = []
    result = implement.run_agent(
        "cell",
        prompt="p",
        options={},
        spec_id="SY-1",
        emit=watched.append,
        exec_stream=_stream("npm WARN something", "", _result_line()),
    )
    assert result.subtype == "success"
    assert any("(raw) npm WARN" in describe(e) for e in watched)


def test_json_that_is_not_an_object_is_quarantined_too():
    """The other half of the quarantine, and the half nothing covered:
    `json.loads` does not raise for `[1, 2]` or `"hi"`, so those reach the
    `isinstance(event, dict)` branch rather than the `ValueError` one.
    Measured — deleting that branch left all 1156 tests passing, and
    `_describe_agent_event` calls `.get`, so a bare list would raise inside
    the renderer instead of being shown."""
    for payload in ("[1, 2]", '"just a string"', "42"):
        watched: list[Event] = []
        result = implement.run_agent(
            "cell",
            prompt="p",
            options={},
            spec_id="SY-1",
            emit=watched.append,
            exec_stream=_stream(payload, "", _result_line()),
        )
        assert result.subtype == "success"
        quarantined = [e for e in watched if isinstance(e, Agent) and e.raw]
        assert quarantined, payload
        assert quarantined[0].line == payload
        assert quarantined[0].event is None
        assert describe(quarantined[0]) == f"agent: (raw) {payload}"


def test_a_line_that_is_not_an_event_is_bounded_at_capture():
    """`describe` cuts at 160, but the untruncated line used to reach
    `events.jsonl` — an untrusted cell choosing how much control-plane disk it
    writes. Measured on one 5 MB stdout line: 715 bytes written before this
    spec's change, 10 MB after. Bounded at capture now, which is also what
    AC5's own wording says ("shown, truncated")."""
    watched: list[Event] = []
    implement.run_agent(
        "cell",
        prompt="p",
        options={},
        spec_id="SY-1",
        emit=watched.append,
        exec_stream=_stream("z" * 50_000, "", _result_line()),
    )
    (raw,) = [e for e in watched if isinstance(e, Agent) and e.raw]
    assert raw.line is not None
    assert len(raw.line) == implement.QUARANTINE_BYTES
    # Bounded for storage, still cut to 160 for the terminal — the two bounds
    # are separate and a change to either must fail something.
    assert describe(raw) == "agent: (raw) " + "z" * 160


def test_a_raw_line_is_shown_and_never_read_as_an_event():
    """A line that is not JSON came from a process sharing the runner's stdout
    inside an untrusted cell (`test_json_that_is_not_an_object_is_quarantined_
    too` above covers a line that parses but is not a dict — the sibling this
    used to cite feeds `npm WARN something`, which takes the `ValueError`
    branch, so it never proved that at all). Checked here at the event's own shape, not the rendered string
    alone: `raw=True` is the quarantine, `event` stays unset — a raw line
    read as an event would leave `event` populated instead — and `describe()`
    still shows it, truncated, exactly as the operator saw it before this
    migration (SA-0041)."""
    watched: list[Event] = []
    implement.run_agent(
        "cell",
        prompt="p",
        options={},
        spec_id="SY-1",
        emit=watched.append,
        exec_stream=_stream("npm WARN " + "x" * 200, _result_line()),
    )
    (raw,) = [e for e in watched if isinstance(e, Agent) and e.raw]
    assert raw.event is None
    assert raw.line is not None and raw.line.startswith("npm WARN ")
    # Two different bounds, and this used to conflate them: capture keeps
    # `QUARANTINE_BYTES`, render shows 160. Asserted against a literal, because
    # `raw.line[:160]` is a no-op once capture bounds the line and stops
    # distinguishing a renderer that truncates from one that does not.
    assert len(raw.line) == 209
    assert describe(raw) == "agent: (raw) npm WARN " + "x" * 151


def test_a_crashed_attempt_keeps_the_last_good_cost():
    """A non-success subtype raises and carries its cost: the accounting and the
    control flow read one predicate, or a charged turn returns as a clean one."""
    with pytest.raises(implement.AgentFailed) as raised:
        implement.run_agent(
            "cell",
            prompt="p",
            options={},
            spec_id="SY-1",
            last_cost_usd=4.12,
            exec_stream=_stream(
                _result_line(subtype="error_during_execution", total_cost_usd=0)
            ),
        )
    attempt = raised.value.attempt
    assert attempt is not None
    assert attempt.cost_usd_est == 4.12


def test_the_request_carries_the_prompt_the_options_and_the_resume():
    stream = _stream(_result_line())
    implement.run_agent(
        "cell",
        prompt="fix these",
        options={"max_turns": 3},
        resume="sess-1",
        spec_id="SY-1",
        exec_stream=stream,
    )
    assert stream.request == {
        "prompt": "fix these",
        "options": {"max_turns": 3},
        "resume": "sess-1",
    }
    assert stream.command == [implement.PYTHON, implement.RUNNER]


def test_repair_text_carries_failures_and_never_a_gate_status():
    """The agent only ever receives failures[] — never a status, never a
    verdict, and never the knowledge that some other gate passed (§5.4)."""
    new = [
        NewFailure("types", Failure(file="a.py", line=88, code="arg-type", message="x"))
    ]
    preamble, _, listed = implement.repair_prompt(new).partition("\n\n")
    assert listed.splitlines() == ["- [types] a.py:88 arg-type: x"]
    # The whole preamble, not substrings: hunting for "pass" or "status" runs
    # over gate-supplied failure text, where "passed" fails for the wrong reason.
    assert preamble == (
        "These failures are new since the base commit. Failures already "
        "present on the base commit are excluded and are not yours to fix. "
        "Fix these and commit."
    )


def test_a_failure_with_no_path_does_not_render_an_empty_one():
    """`size` fails the diff, not a file. The location is omitted rather than
    rendered as `:?`, which reads as the gate itself having broken."""
    new = [
        NewFailure("size", Failure(file="", code="diff-too-large", message="601 > 600"))
    ]
    _, _, listed = implement.repair_prompt(new).partition("\n\n")
    assert listed.splitlines() == ["- [size] diff-too-large: 601 > 600"]


def test_telemetry_is_off_because_the_proxy_would_deny_it_anyway():
    """The allowlist permits api.anthropic.com and nothing else, so statsig
    traffic becomes denied CONNECTs and startup latency that reads as a hang."""
    options = implement.agent_options(
        system_prompt="s", cwd="/work", max_turns=40, budget_usd=12.0
    )
    assert options["env"]["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] == "1"


def test_only_the_result_event_opens_the_completion_window():
    """The runtime never parses Saffron's events. `run_agent` is what tells it
    the payload signalled done, and nothing before the result does."""
    signals: list[bool] = []

    def _exec_stream(container, command, *, stdin_data, on_line, **kwargs):
        for line in (
            json.dumps({"type": "text", "text": "hi"}),
            _result_line(),
            "npm WARN a child of the runner, still talking",
        ):
            signals.append(bool(on_line(line)))
        return runtime.Completed(0, "", "")

    implement.run_agent(
        "cell",
        prompt="p",
        options={},
        spec_id="SY-1",
        exec_stream=_exec_stream,
    )
    assert signals == [False, True, True]


def test_a_completion_window_close_is_a_finished_turn():
    """§4.3's completion axis, and the mistake splitting it from idle prevents:
    the runner emitted its result and a child held stdout open. That turn is
    done, so it returns rather than raising — and says which bound ended it."""
    watched: list[Event] = []
    result = implement.run_agent(
        "cell",
        prompt="p",
        options={},
        spec_id="SY-1",
        emit=watched.append,
        exec_stream=_stream(_result_line(), bound="completion"),
    )
    assert result.bound == "completion"
    assert result.cost_usd_est == 0.75
    assert any("held stdout open" in describe(e) for e in watched)


def test_an_idle_kill_is_a_failed_turn_that_names_the_bound():
    """The other half: silence before the result is a stall, whatever the
    runner already claimed, and it must not read like the window closing."""
    with pytest.raises(implement.AgentFailed, match="idle bound") as raised:
        implement.run_agent(
            "cell",
            prompt="p",
            options={},
            spec_id="SY-1",
            exec_stream=_stream(
                _result_line(), returncode=124, timed_out=True, bound="idle"
            ),
            reap_cell=_no_reap,
        )
    attempt = raised.value.attempt
    assert attempt is not None
    assert attempt.bound == "idle"


def test_a_wall_clock_kill_before_any_result_names_the_bound_too():
    with pytest.raises(implement.AgentFailed, match="wall bound"):
        implement.run_agent(
            "cell",
            prompt="p",
            options={},
            spec_id="SY-1",
            exec_stream=_stream(returncode=124, timed_out=True, bound="wall"),
            reap_cell=_no_reap,
        )


def test_a_turn_killed_before_its_result_event_still_reports_what_it_spent():
    """The costliest failure of all: an idle or wall kill takes the runner
    mid-stream, so no result event ever carries the cost fields. Charging it
    zero is a ceiling that stops counting while the repair loop keeps going."""
    with pytest.raises(implement.AgentFailed, match="no result event") as raised:
        implement.run_agent(
            "cell",
            prompt="p",
            options={},
            spec_id="SY-1",
            last_cost_usd=4.0,
            exec_stream=_stream(returncode=124, timed_out=True, bound="wall"),
            reap_cell=_no_reap,
        )
    assert raised.value.attempt is not None
    assert raised.value.attempt.cost_usd_est == 4.0
    assert raised.value.attempt.bound == "wall"


def test_a_killed_turn_reaps_the_cell_because_the_kill_does_not_reach_it():
    """Measured against a real `container`: killing the host-side exec client
    leaves the process it started running inside the cell. The driver then
    measures commits, runs the suite and resumes the session in that same
    container, so an abandoned agent would be editing /work underneath all
    three."""
    reaped: list[str] = []

    def _reap(container, **_kwargs):
        reaped.append(container)
        return runtime.Completed(0, "", "")

    with pytest.raises(implement.AgentFailed, match="idle bound"):
        implement.run_agent(
            "cell",
            prompt="p",
            options={},
            spec_id="SY-1",
            exec_stream=_stream(returncode=124, timed_out=True, bound="idle"),
            reap_cell=_reap,
        )
    assert reaped == ["cell"]


def test_a_turn_that_ended_on_its_own_is_not_reaped():
    """The completion window closing is a finished turn, not a kill (§4.3) —
    and nothing is left behind to reap."""
    reaped: list[str] = []
    implement.run_agent(
        "cell",
        prompt="p",
        options={},
        spec_id="SY-1",
        exec_stream=_stream(_result_line(), bound="completion"),
        reap_cell=_recording_reap(reaped),
    )
    assert reaped == []


def test_a_rate_limit_event_reaches_the_attempt_result():
    """The host acts on this, so it has to survive the stream. Untested, the
    supervisor's guard reads a field nothing ever populates."""
    result = implement.run_agent(
        "cell",
        prompt="go",
        options={"max_turns": 3},
        spec_id="SY-1",
        exec_stream=_stream(
            json.dumps(
                {
                    "type": "rate_limit",
                    "status": "rejected",
                    "utilization": 1.0,
                    "resets_at": 1755800000,
                }
            ),
            _result_line(),
        ),
    )
    assert result.rate_limit_status == "rejected"
    assert result.rate_limit_resets_at == 1755800000


def test_the_last_rate_limit_status_wins():
    """The CLI emits on transition; the final state is the one the next turn
    would start under, so a warning must not mask a later rejection."""
    result = implement.run_agent(
        "cell",
        prompt="go",
        options={"max_turns": 3},
        spec_id="SY-1",
        exec_stream=_stream(
            json.dumps({"type": "rate_limit", "status": "allowed_warning"}),
            json.dumps({"type": "rate_limit", "status": "rejected", "resets_at": 7}),
            _result_line(),
        ),
    )
    assert result.rate_limit_status == "rejected"
    assert result.rate_limit_resets_at == 7


def test_a_turn_with_no_rate_limit_event_carries_none():
    result = implement.run_agent(
        "cell",
        prompt="go",
        options={"max_turns": 3},
        spec_id="SY-1",
        exec_stream=_stream(_result_line()),
    )
    assert result.rate_limit_status is None
    assert result.rate_limit_resets_at is None
