"""The in-cell runner's event mapping, without the SDK and without a key.

`query()` is never called here: the mapping is fed fake message objects, which
is the only part of the runner that can be checked on the host at all.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from saffron.cell import runtime
from saffron.phases import implement
from saffron.repos import image

RUNNER_PATH = Path(__file__).resolve().parents[1] / "images" / "agent_runner.py"


def _load():
    spec = importlib.util.spec_from_file_location("agent_runner", RUNNER_PATH)
    assert spec and spec.loader, f"no import spec for {RUNNER_PATH}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = _load()


def _assistant(*blocks):
    return SimpleNamespace(content=list(blocks), model="claude-test")


def test_assistant_text_becomes_a_text_event():
    (event,) = runner.events(_assistant(SimpleNamespace(text="hello")))
    assert event == {"type": "text", "text": "hello"}


def test_a_tool_use_carries_its_name_and_a_clipped_input():
    block = SimpleNamespace(id="t1", name="Write", input={"content": "x" * 500})
    (event,) = runner.events(_assistant(block))
    assert event["type"] == "tool_use"
    assert event["name"] == "Write"
    assert len(event["input"]["content"]) < 300


def test_thinking_is_counted_and_not_transcribed():
    block = SimpleNamespace(thinking="secret reasoning", signature="s")
    (event,) = runner.events(_assistant(block))
    assert event == {"type": "thinking", "chars": len("secret reasoning")}


def test_a_user_message_never_produces_agent_text():
    """The host reads the <output> block out of `text` events. A user turn is
    the host's own prompt coming back, so it must not land there (§5.3)."""
    echoed = SimpleNamespace(content="<output>{}</output>")
    assert [e["type"] for e in runner.events(echoed)] == ["passthrough"]


def test_tool_results_come_back_as_tool_results():
    block = SimpleNamespace(tool_use_id="t1", content="ok", is_error=False)
    user = SimpleNamespace(content=[block])
    (event,) = runner.events(user)
    assert event == {"type": "tool_result", "tool_use_id": "t1", "is_error": False}


def test_the_result_event_carries_what_the_supervisor_bounds_on():
    message = SimpleNamespace(
        subtype="success",
        num_turns=7,
        session_id="sess-1",
        total_cost_usd=1.25,
        terminal_reason="completed",
        is_error=False,
    )
    (event,) = runner.events(message)
    assert event == {
        "type": "result",
        "subtype": "success",
        "num_turns": 7,
        "total_cost_usd": 1.25,
        "session_id": "sess-1",
        "terminal_reason": "completed",
        "is_error": False,
    }


def test_a_result_that_reports_no_cost_is_zero_not_none():
    message = SimpleNamespace(
        subtype="error_during_execution",
        num_turns=2,
        session_id="s",
        total_cost_usd=None,
        is_error=True,
    )
    (event,) = runner.events(message)
    assert event["total_cost_usd"] == 0.0
    assert event["terminal_reason"] is None


def test_a_system_message_keeps_its_subtype():
    (event,) = runner.events(SimpleNamespace(subtype="init", data={"cwd": "/work"}))
    assert event == {"type": "system", "subtype": "init", "data": {"cwd": "/work"}}


def test_an_unknown_message_passes_through_rather_than_crashing():
    """The stream cannot be verified without a key, so the runner degrades
    rather than asserts: a message shape it has never seen is an event."""

    class SomethingNew:
        pass

    (event,) = runner.events(SomethingNew())
    assert event == {"type": "passthrough", "kind": "SomethingNew"}


def test_an_unknown_content_block_passes_through_too():
    (event,) = runner.events(_assistant(SimpleNamespace(mystery=1)))
    assert event["type"] == "passthrough"


def test_a_request_that_is_not_json_is_an_error_event_and_a_nonzero_exit():
    """The no-credential path in miniature: the runner reports rather than
    crashing, and an absent result is never a clean exit."""
    done = subprocess.run(
        [sys.executable, str(RUNNER_PATH)],
        input="not json",
        capture_output=True,
        text=True,
    )
    assert done.returncode != 0
    assert json.loads(done.stdout)["type"] == "error"


@pytest.mark.cell
def test_the_runner_is_installed_in_the_base_image_and_runs():
    """Locating a file proves it exists; only running it proves it works. The
    path is the host's own constant, so the two cannot drift apart."""
    done = runtime.run_ephemeral(
        image.BASE_TAG,
        ["sh", "-c", f"echo 'not json' | python {implement.RUNNER}"],
    )
    assert done.returncode != 0, done.stdout
    assert json.loads(done.stdout.strip().splitlines()[-1])["type"] == "error"


@pytest.mark.cell
def test_without_a_credential_the_agent_fails_rather_than_reporting_success():
    """The transport end to end, on the no-key path: the request reaches the
    runner on stdin inside a real cell, the session cannot start, and the host
    raises instead of returning an attempt that never happened (§4.3).

    Deliberately on an `--internal` network with no proxy, so the cell has no
    route to anything and no request is possible at all.
    """
    network = "saffron-test-runner-net"
    container = "saffron-test-runner-cell"
    runtime.remove_container(container)
    runtime.remove_network(network)
    runtime.create_network(network)
    try:
        runtime.run_detached(
            container,
            image.BASE_TAG,
            command=["sleep", "infinity"],
            network=network,
            env={"CLAUDE_CONFIG_DIR": "/agent-state"},
        )
        with pytest.raises(implement.AgentFailed):
            implement.run_agent(
                container,
                prompt="say hello",
                options={"max_turns": 1},
                spec_id="SY-1",
                timeout_s=180,
            )
    finally:
        runtime.remove_container(container)
        runtime.remove_network(network)


def test_a_rate_limit_event_is_not_a_passthrough():
    """The only ceiling the cell is subject to rather than reporting (§5.1).
    Dropped, a rejected window reaches the host as four failed repair
    attempts and reports EXHAUSTED — §3.3's one-state-for-two-causes."""
    message = SimpleNamespace(
        rate_limit_info=SimpleNamespace(
            status="allowed_warning", utilization=0.82, resets_at=1755800000
        ),
        uuid="u",
        session_id="s",
    )
    (event,) = runner.events(message)
    assert event["type"] == "rate_limit"
    assert event["status"] == "allowed_warning"
    assert event["utilization"] == 0.82
    assert event["resets_at"] == 1755800000


def test_a_rate_limit_event_is_not_mistaken_for_a_result():
    """It carries session_id, which the result branch also keys on. Only
    num_turns tells them apart, so the ordering in events() is load-bearing."""
    message = SimpleNamespace(
        rate_limit_info=SimpleNamespace(
            status="rejected", utilization=1.0, resets_at=1
        ),
        uuid="u",
        session_id="s",
    )
    (event,) = runner.events(message)
    assert event["type"] == "rate_limit"
