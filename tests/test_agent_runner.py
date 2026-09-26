"""The in-cell runner, without the SDK and without a key.

Most tests feed the event mapping fake message objects. The system-prompt
witnesses drive `main` in-process against a stub `claude_agent_sdk`.
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
from tests.test_implement import _no_reap
from tests.test_rebut import CONTEXT_MD, PROMPTS, _blocker

RUNNER_PATH = Path(__file__).resolve().parents[1] / "images" / "agent_runner.py"


def _load():
    spec = importlib.util.spec_from_file_location("agent_runner", RUNNER_PATH)
    assert spec and spec.loader, f"no import spec for {RUNNER_PATH}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = _load()


@pytest.fixture(autouse=True)
def _forget_seen_message_ids():
    """One runner process is one `run_agent` call, but this module loads the
    runner once for the whole session, so the set would outlive every test.
    Absence is tolerated: under `revert` the source is the base runner, which
    has no such set, and a fixture that raised there would error every test
    in the file instead of failing the new ones."""
    getattr(runner, "_seen_assistant_message_ids", set()).clear()


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
        usage={
            "input_tokens": 200,
            "output_tokens": 80,
            "cache_read_input_tokens": 500,
            "cache_creation_input_tokens": 25,
        },
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
        "structured_output": None,
        "input_tokens": 200,
        "output_tokens": 80,
        "cache_read_input_tokens": 500,
        "cache_creation_input_tokens": 25,
    }


def test_the_result_event_carries_structured_output_whole():
    """`structured_output` reaches `run_agent` exactly as the SDK reported it,
    never through `_clip`, which would cut a 200-char string mid-value."""
    nested = {"argument": "x" * 500}
    with_value = SimpleNamespace(
        subtype="success",
        num_turns=1,
        session_id="s1",
        total_cost_usd=0.1,
        terminal_reason="completed",
        is_error=False,
        structured_output=nested,
    )
    with_none = SimpleNamespace(
        subtype="success",
        num_turns=1,
        session_id="s2",
        total_cost_usd=0.1,
        terminal_reason="completed",
        is_error=False,
        structured_output=None,
    )
    without_attr = SimpleNamespace(
        subtype="success",
        num_turns=1,
        session_id="s3",
        total_cost_usd=0.1,
        terminal_reason="completed",
        is_error=False,
    )
    for message, expected in (
        (with_value, nested),
        (with_none, None),
        (without_attr, None),
    ):
        (event,) = runner.events(message)
        assert "structured_output" in event
        assert event["structured_output"] == expected

    (event,) = runner.events(with_value)
    line = json.dumps(event)

    def _exec_stream(container, command, *, stdin_data, on_line, **_kwargs):
        on_line(line)
        return runtime.Completed(0, "", "")

    attempt = implement.run_agent(
        "cell",
        prompt="p",
        options={"system_prompt": "s", "max_turns": 1},
        spec_id="SY-1",
        exec_stream=_exec_stream,
        reap_cell=_no_reap,
        exec_=_no_exec,
    )
    assert attempt.structured_output == nested


def test_the_result_event_carries_the_sessions_token_counts():
    """The four counts the Messages API names, exactly as reported, a zero
    included — not summed, not reconciled, just carried (`SA-0090`)."""
    message = SimpleNamespace(
        subtype="success",
        num_turns=3,
        session_id="sess-tokens",
        total_cost_usd=0.42,
        terminal_reason="completed",
        is_error=False,
        usage={
            "input_tokens": 120,
            "output_tokens": 45,
            "cache_read_input_tokens": 300,
            "cache_creation_input_tokens": 0,
        },
    )
    (event,) = runner.events(message)
    assert event["input_tokens"] == 120
    assert event["output_tokens"] == 45
    assert event["cache_read_input_tokens"] == 300
    assert event["cache_creation_input_tokens"] == 0


def test_a_result_that_reports_no_usage_has_null_token_counts_not_zero():
    """Absent is null; a reported zero (above) stays zero. `in` is asserted
    too, not only the value, so a reverted runner with no such keys at all
    cannot pass this by accident."""
    message = SimpleNamespace(
        subtype="success",
        num_turns=1,
        session_id="sess-no-usage",
        total_cost_usd=0.1,
        terminal_reason="completed",
        is_error=False,
    )
    (event,) = runner.events(message)
    for key in (
        "input_tokens",
        "output_tokens",
        "cache_read_input_tokens",
        "cache_creation_input_tokens",
    ):
        assert key in event
        assert event[key] is None


def test_the_counts_for_one_message_id_reach_the_log_once():
    """One unit of work can be delivered as several assistant messages
    sharing a message_id, each reporting the same usage. Only the first such
    message's event carries the per-step counts."""
    usage = {
        "input_tokens": 50,
        "output_tokens": 999,
        "cache_read_input_tokens": 10,
        "cache_creation_input_tokens": 5,
    }
    first = SimpleNamespace(
        content=[SimpleNamespace(text="hello")],
        model="claude-test",
        message_id="shared-msg-1",
        usage=usage,
    )
    second = SimpleNamespace(
        content=[SimpleNamespace(text="world")],
        model="claude-test",
        message_id="shared-msg-1",
        usage=usage,
    )

    (first_event,) = runner.events(first)
    assert first_event["input_tokens"] == 50
    assert first_event["cache_read_input_tokens"] == 10
    assert first_event["cache_creation_input_tokens"] == 5
    # Out of scope by name: the SDK's own docs call it inaccurate per turn, and
    # a real `usage` mapping does carry the key, so absence has to be asserted.
    assert "output_tokens" not in first_event

    (second_event,) = runner.events(second)
    assert "input_tokens" not in second_event
    assert "cache_read_input_tokens" not in second_event
    assert "cache_creation_input_tokens" not in second_event


def test_two_assistant_messages_with_no_id_each_carry_their_own_counts():
    """`message_id` is `str | None`, and absence is not a key. Keyed on `None`
    or on `""`, only the first id-less message would carry counts — and it
    would fail that way in silence, because the fakes never notice."""
    usage = {
        "input_tokens": 7,
        "cache_read_input_tokens": 1,
        "cache_creation_input_tokens": 2,
    }
    made = [
        SimpleNamespace(
            content=[SimpleNamespace(text=text)], model="claude-test", usage=usage
        )
        for text in ("a", "b")
    ]

    for message in made:
        (event,) = runner.events(message)
        assert event["input_tokens"] == 7
        assert event["cache_read_input_tokens"] == 1
        assert event["cache_creation_input_tokens"] == 2


def test_a_count_the_sdk_stops_sending_is_null_not_zero():
    """ "An SDK that renames or drops a count must give nulls, never a crash"
    — and never a silent zero, which reads as a measured fact."""
    message = SimpleNamespace(
        subtype="success",
        num_turns=1,
        session_id="sess-partial",
        total_cost_usd=0.1,
        usage={"input_tokens": 11},
    )

    (event,) = runner.events(message)
    assert event["input_tokens"] == 11
    for dropped in ("output_tokens", "cache_read_input_tokens"):
        assert dropped in event
        assert event[dropped] is None


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


@pytest.mark.cell
def test_a_verdict_sized_system_prompt_reaches_the_cli_without_an_argument_list_error():
    """The real argument list, not a stub (backlog b-8487de). A system prompt
    this size used to make the agent CLI fail to spawn. `init` shows it
    parsed its arguments and began a session instead. Whether the CLI emits
    `init` before it fails for want of a credential is unmeasured until this
    runs."""
    network = "saffron-test-runner-net-prompt"
    container = "saffron-test-runner-cell-prompt"
    runtime.remove_container(container)
    runtime.remove_network(network)
    runtime.create_network(network)
    watched: list = []
    try:
        runtime.run_detached(
            container,
            image.BASE_TAG,
            command=["sleep", "infinity"],
            network=network,
            env={"CLAUDE_CONFIG_DIR": "/agent-state"},
        )
        with pytest.raises(implement.AgentFailed) as raised:
            implement.run_agent(
                container,
                prompt="say hello",
                options={"max_turns": 1, "system_prompt": "s" * (1024 * 1024)},
                spec_id="SY-1",
                emit=watched.append,
                timeout_s=180,
            )
    finally:
        runtime.remove_container(container)
        runtime.remove_network(network)
    assert "Argument list too long" not in str(raised.value)
    assert "Failed to start" not in str(raised.value)
    inits = [
        e.event
        for e in watched
        if getattr(e, "event", None)
        and e.event.get("type") == "system"
        and e.event.get("subtype") == "init"
    ]
    assert inits, "no init system event seen"


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


# --- backlog b-8487de: the system prompt travels as a file, and a verdict
# session that never started is told apart from one that ran ---


def _stub_module(query):
    """A fake `claude_agent_sdk`, recording what it was constructed with.
    A `SimpleNamespace`, not a real module: `sys.modules` accepts anything
    with the right attributes, and needs none of a module's own."""

    class _Options:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    return SimpleNamespace(ClaudeAgentOptions=_Options, query=query)


def _run_runner_in_process(monkeypatch, stub, stdin_data, on_line):
    """Feeds `runner.main()` a request on stdin, and each printed line to
    `on_line`. Stands in for a real `exec -i` across the three witnesses
    below, all of which run the same runner code the base image installs."""
    import io

    monkeypatch.setitem(sys.modules, "claude_agent_sdk", stub)
    old_stdin, old_stdout = sys.stdin, sys.stdout
    sys.stdin = io.StringIO(stdin_data)
    captured = io.StringIO()
    sys.stdout = captured
    try:
        returncode = runner.main()
    finally:
        sys.stdin, sys.stdout = old_stdin, old_stdout
    for line in captured.getvalue().splitlines():
        on_line(line)
    return runtime.Completed(returncode, captured.getvalue(), "")


def _exec_stream_via_runner(monkeypatch, stub):
    def _exec_stream(container, command, *, stdin_data, on_line, **_kwargs):
        return _run_runner_in_process(monkeypatch, stub, stdin_data, on_line)

    return _exec_stream


def _no_exec(container, command, **_kwargs):
    return runtime.Completed(0, "", "")


def test_the_runner_hands_the_sdk_a_system_prompt_file_never_a_string(
    monkeypatch, tmp_path
):
    import copy

    from saffron.phases import rebut

    cwd = tmp_path / "work"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    blocker = _blocker()
    big_diff = "diff --git a/x b/x\n" + ("+" + "é" * 100 + "\n") * 3000
    big_prompt = rebut.verdict_prompt(
        "correctness",
        blockers=[(1, blocker)],
        rebuttal=rebut.RebuttalTurn(),
        context_md=CONTEXT_MD,
        claude_md=None,
        prompts_dir=PROMPTS,
        spec_body="fix it",
        reviewed_diff=big_diff,
        diff=big_diff,
    )
    assert len(big_prompt.encode("utf-8")) >= 200_000
    assert not big_prompt.isascii()

    options = implement.agent_options(
        system_prompt=big_prompt, cwd=str(cwd), max_turns=3, budget_usd=1.0
    )

    def _recorder():
        record: dict = {}

        async def _query(prompt, options):
            record["kwargs"] = options.kwargs
            sp = options.kwargs.get("system_prompt")
            if isinstance(sp, dict):
                record["bytes_while_running"] = Path(sp["path"]).read_bytes()
            yield SimpleNamespace(
                subtype="success",
                num_turns=1,
                session_id="sess-out",
                total_cost_usd=0.05,
                terminal_reason="completed",
                is_error=False,
            )

        return record, _query

    # Session 1: no resume, the huge non-ASCII prompt as the turn text too.
    record1, query1 = _recorder()
    before1 = copy.deepcopy(options)
    implement.run_agent(
        "cell",
        prompt=big_prompt,
        options=options,
        spec_id="SY-1",
        exec_stream=_exec_stream_via_runner(monkeypatch, _stub_module(query1)),
    )
    assert options == before1
    assert isinstance(record1["kwargs"]["system_prompt"], dict)
    path1 = record1["kwargs"]["system_prompt"]["path"]
    assert isinstance(path1, str)
    assert Path(path1).is_absolute()
    assert not Path(path1).is_relative_to(cwd)
    assert record1["kwargs"] == before1 | {
        "system_prompt": {"type": "file", "path": path1}
    }
    assert record1["bytes_while_running"].decode("utf-8") == big_prompt
    assert not Path(path1).exists()

    # Session 2: resumed, with a one-character system prompt and turn prompt,
    # so a file written only for a large prompt fails here.
    options2 = {**options, "system_prompt": "é"}
    record2, query2 = _recorder()
    before2 = copy.deepcopy(options2)
    implement.run_agent(
        "cell",
        prompt="x",
        options=options2,
        resume="sess-old",
        spec_id="SY-1",
        exec_stream=_exec_stream_via_runner(monkeypatch, _stub_module(query2)),
    )
    assert options2 == before2
    assert isinstance(record2["kwargs"]["system_prompt"], dict)
    path2 = record2["kwargs"]["system_prompt"]["path"]
    assert path2 != path1
    assert record2["kwargs"] == before2 | {
        "system_prompt": {"type": "file", "path": path2},
        "resume": "sess-old",
    }
    assert record2["bytes_while_running"].decode("utf-8") == "é"
    assert not Path(path2).exists()

    # Session 3: no system prompt at all. Nothing new reaches the SDK.
    options3 = {k: v for k, v in options.items() if k != "system_prompt"}
    record3, query3 = _recorder()
    before3 = copy.deepcopy(options3)
    implement.run_agent(
        "cell",
        prompt="p3",
        options=options3,
        spec_id="SY-1",
        exec_stream=_exec_stream_via_runner(monkeypatch, _stub_module(query3)),
    )
    assert options3 == before3
    assert record3["kwargs"] == before3
    assert "system_prompt" not in record3["kwargs"]


def test_a_session_a_bound_kills_leaves_no_prompt_file_in_the_cell(monkeypatch):
    import inspect

    assert (
        inspect.signature(implement.run_agent).parameters["exec_"].default
        is runtime.exec_
    )

    options = implement.agent_options(
        system_prompt="p", cwd="/work", max_turns=1, budget_usd=1.0
    )

    def _one_kill(bound: str) -> tuple[list[str], dict]:
        log: list[str] = []
        recorded: dict = {}

        async def _query(prompt, options):
            recorded["path"] = options.kwargs["system_prompt"]["path"]
            if False:  # pragma: no cover, makes this an empty async generator
                yield

        stub = _stub_module(_query)

        def _exec_stream(container, command, *, stdin_data, on_line, **_kwargs):
            # Runs for real, so the runner's own `finally` removes the path.
            # This stands in for a reap that never let that `finally` run.
            _run_runner_in_process(monkeypatch, stub, stdin_data, lambda _l: None)
            Path(recorded["path"]).write_bytes(b"leftover")
            log.append("session")
            return runtime.Completed(124, "", "", timed_out=True, bound=bound)

        def _reap(container, **_kwargs):
            log.append("reap")
            return runtime.Completed(0, "", "")

        def _exec(container, command, **_kwargs):
            log.append("exec")
            return subprocess.run(command, check=True)

        try:
            with pytest.raises(implement.AgentFailed):
                implement.run_agent(
                    "cell",
                    prompt="p",
                    options=options,
                    spec_id="SY-1",
                    exec_stream=_exec_stream,
                    reap_cell=_reap,
                    exec_=_exec,
                )
            assert not Path(recorded["path"]).exists()
        finally:
            if "path" in recorded:
                Path(recorded["path"]).unlink(missing_ok=True)
        return log, recorded

    for bound in ("idle", "wall"):
        log, _recorded = _one_kill(bound)
        assert log == ["session", "reap", "exec"]


def test_a_verdict_session_that_never_started_ends_rebut_gate_error(monkeypatch):
    from saffron.phases import rebut

    class _CLIConnectionError(Exception):
        pass

    # Every prompt path a raising session received. Each must be gone after.
    raised_paths: list[str] = []

    def _result_message(structured_output=None):
        return SimpleNamespace(
            subtype="success",
            num_turns=1,
            session_id="sess-v",
            total_cost_usd=0.05,
            terminal_reason="completed",
            is_error=False,
            structured_output=structured_output,
        )

    def _query_valid(finding):
        async def _query(prompt, options):
            payload = {
                "verdicts": [
                    {"finding": finding, "verdict": "withdrawn", "reason": "ok"}
                ]
            }
            yield _assistant(SimpleNamespace(text="Withdrawing."))
            yield _result_message(structured_output=payload)

        return _query

    async def _query_never_started(prompt, options):
        raised_paths.append(options.kwargs["system_prompt"]["path"])
        if False:  # pragma: no cover, raises before any yield
            yield
        raise _CLIConnectionError(
            "Failed to start Claude Code: [Errno 7] Argument list too long"
        )

    async def _query_started_then_raises(prompt, options):
        raised_paths.append(options.kwargs["system_prompt"]["path"])
        yield _assistant()
        raise _CLIConnectionError(
            "Failed to start Claude Code: [Errno 7] Argument list too long"
        )

    def _silent_wall_kill(container, command, *, stdin_data, on_line, **_kwargs):
        return runtime.Completed(124, "", "", timed_out=True, bound="wall")

    def _es(query):
        return _exec_stream_via_runner(monkeypatch, _stub_module(query))

    def _rebuttal_payload(n):
        return {
            "rebuttals": [
                {"finding": i, "action": "argued", "argument": "a"}
                for i in range(1, n + 1)
            ]
        }

    def _agent(rebuttal_payload, verdict_scripts):
        calls = {"n": 0}
        scripts = iter(verdict_scripts)

        def agent(container, *, prompt, options, resume=None, emit, **_kwargs):
            calls["n"] += 1
            if resume is not None:
                # The first resumed call is the rebuttal attempt, sent no
                # `output_format`. The second is its extraction turn.
                return implement.AttemptResult(
                    session_id="sess-1",
                    subtype="success",
                    terminal_reason="completed",
                    num_turns=1,
                    cost_usd_est=0.05,
                    structured_output=rebuttal_payload if calls["n"] == 2 else None,
                )
            exec_stream, reap_cell, exec_ = next(scripts)
            return implement.run_agent(
                container,
                prompt=prompt,
                options=options,
                spec_id="SY-1",
                emit=emit,
                exec_stream=exec_stream,
                reap_cell=reap_cell,
                exec_=exec_,
            )

        return agent

    def _rebut(blockers, verdict_scripts):
        return rebut.run_rebut(
            "cell",
            blockers=blockers,
            options=implement.agent_options(
                system_prompt="s", max_turns=5, budget_usd=2.0
            ),
            session_id="sess-1",
            spec_body="fix the gap",
            context_md=CONTEXT_MD,
            claude_md=None,
            prompts_dir=PROMPTS,
            max_turns=5,
            budget_usd=2.0,
            head_moved=lambda: True,
            rerun_gates=lambda: None,
            critic_container=lambda: "critic-cell",
            diff=lambda _critic: "diff",
            agent=_agent(_rebuttal_payload(len(blockers)), verdict_scripts),
            spec_id="SY-1",
            reviewed_diff="diff",
            emit=lambda _e: None,
        )

    # Case A: correctness valid, contract never started, adequacy started then
    # raised. Only `contract` is named: it is the only one that never started.
    blockers_a = [
        _blocker("correctness", line=1),
        _blocker("contract", line=2),
        _blocker("adequacy", line=3),
    ]
    result_a = _rebut(
        blockers_a,
        [
            (_es(_query_valid(1)), _no_reap, _no_exec),
            (_es(_query_never_started), _no_reap, _no_exec),
            (_es(_query_started_then_raises), _no_reap, _no_exec),
        ],
    )
    assert result_a.state == "GATE_ERROR"
    assert "contract" in result_a.why
    assert "Argument list too long" in result_a.why
    assert "correctness" not in result_a.why
    assert "adequacy" not in result_a.why
    recorded = {
        v["lens"]: v.get("never_started")
        for v in result_a.as_dict(blockers_a)["verdicts"]
    }
    assert recorded == {"correctness": False, "contract": True, "adequacy": False}

    # Case B: correctness reuses A's "started then raised" session, contract is
    # a silent bound kill with no runner output at all. Neither never started.
    result_b = _rebut(
        [_blocker("correctness", line=1), _blocker("contract", line=2)],
        [
            (_es(_query_started_then_raises), _no_reap, _no_exec),
            (_silent_wall_kill, _no_reap, _no_exec),
        ],
    )
    assert result_b.state == "REBUTTING"

    # Case C: correctness reuses A's "started then raised" session again,
    # contract reuses A's own never-started session.
    result_c = _rebut(
        [_blocker("correctness", line=1), _blocker("contract", line=2)],
        [
            (_es(_query_started_then_raises), _no_reap, _no_exec),
            (_es(_query_never_started), _no_reap, _no_exec),
        ],
    )
    assert result_c.state == "GATE_ERROR"
    assert "contract" in result_c.why
    assert "correctness" not in result_c.why
    assert len(raised_paths) == 5
    assert not any(Path(p).exists() for p in raised_paths)
