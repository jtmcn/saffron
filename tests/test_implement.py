from __future__ import annotations

import json

import pytest

from saffron.cell import runtime
from saffron.gates.baseline import NewFailure
from saffron.gates.contract import Failure
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


def test_the_cache_ttl_outlives_a_gate_run():
    """The repair loop resumes across a gate run, and a gate run is minutes.
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


def test_the_tool_list_is_explicit_and_excludes_the_network():
    assert "WebFetch" not in implement.IMPLEMENT_TOOLS
    assert "WebSearch" not in implement.IMPLEMENT_TOOLS
    assert {"Read", "Write", "Edit", "Bash", "Glob", "Grep"} <= set(
        implement.IMPLEMENT_TOOLS
    )


def test_a_crashed_attempt_falls_back_to_the_last_good_cost():
    """The runtime may report every cost field as zero on crash (§4.1)."""
    result = implement._reconcile_cost(reported=0.0, last_good=4.12, failed=True)
    assert result == 4.12


def test_a_clean_finish_keeps_its_reported_cost():
    assert implement._reconcile_cost(reported=3.5, last_good=2.0, failed=False) == 3.5


def _stream(*lines, returncode=0, stderr="", timed_out=False):
    """A fake in-cell runner: the lines it prints, and how it exited."""

    def _exec_stream(container, command, *, stdin_data, on_line, **kwargs):
        _exec_stream.request = json.loads(stdin_data)
        _exec_stream.command = list(command)
        for line in lines:
            on_line(line)
        return runtime.Completed(returncode, "", stderr, timed_out=timed_out)

    return _exec_stream


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
    watched = []
    result = implement.run_agent(
        "cell",
        prompt="plan please",
        options={"max_turns": 3},
        watch=watched.append,
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
            watch=lambda _line: None,
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
            watch=lambda _line: None,
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
            watch=lambda _line: None,
            last_cost_usd=2.0,
            exec_stream=_stream(
                _result_line(subtype="error_max_turns", is_error=True, total_cost_usd=0)
            ),
        )
    assert raised.value.attempt.cost_usd_est == 2.0


def test_a_runner_killed_after_emitting_its_result_is_not_a_clean_turn():
    """§4.3's completion axis: a runner can emit a clean result event and then
    be killed holding stdout open. `is_error` is False and the subtype says
    success, so only `timed_out` tells this from a turn that finished."""
    with pytest.raises(implement.AgentFailed, match="timed out"):
        implement.run_agent(
            "cell",
            prompt="p",
            options={},
            watch=lambda _line: None,
            exec_stream=_stream(_result_line(), timed_out=True),
        )


def test_a_clean_result_from_a_runner_that_exited_non_zero_is_not_a_success():
    """The other half of the same predicate: the result says success and
    nothing flags an error, but the process itself failed."""
    with pytest.raises(implement.AgentFailed, match="exited 1"):
        implement.run_agent(
            "cell",
            prompt="p",
            options={},
            watch=lambda _line: None,
            exec_stream=_stream(_result_line(), returncode=1),
        )


def test_a_crash_reports_the_runners_own_error():
    with pytest.raises(implement.AgentFailed, match="CLIConnectionError"):
        implement.run_agent(
            "cell",
            prompt="p",
            options={},
            watch=lambda _line: None,
            exec_stream=_stream(
                json.dumps({"type": "error", "error": "CLIConnectionError: no key"}),
                returncode=1,
            ),
        )


def test_a_line_that_is_not_an_event_is_shown_and_not_parsed():
    """Anything sharing the runner's stdout must not be read as an event."""
    watched = []
    result = implement.run_agent(
        "cell",
        prompt="p",
        options={},
        watch=watched.append,
        exec_stream=_stream("npm WARN something", "", _result_line()),
    )
    assert result.subtype == "success"
    assert any("(raw) npm WARN" in line for line in watched)


def test_a_crashed_attempt_keeps_the_last_good_cost():
    """A non-success subtype raises and carries its cost: the accounting and the
    control flow read one predicate, or a charged turn returns as a clean one."""
    with pytest.raises(implement.AgentFailed) as raised:
        implement.run_agent(
            "cell",
            prompt="p",
            options={},
            watch=lambda _line: None,
            last_cost_usd=4.12,
            exec_stream=_stream(
                _result_line(subtype="error_during_execution", total_cost_usd=0)
            ),
        )
    assert raised.value.attempt.cost_usd_est == 4.12


def test_the_request_carries_the_prompt_the_options_and_the_resume():
    stream = _stream(_result_line())
    implement.run_agent(
        "cell",
        prompt="fix these",
        options={"max_turns": 3},
        resume="sess-1",
        watch=lambda _line: None,
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


def test_telemetry_is_off_because_the_proxy_would_deny_it_anyway():
    """The allowlist permits api.anthropic.com and nothing else, so statsig
    traffic becomes denied CONNECTs and startup latency that reads as a hang."""
    options = implement.agent_options(
        system_prompt="s", cwd="/work", max_turns=40, budget_usd=12.0
    )
    assert options["env"]["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] == "1"
