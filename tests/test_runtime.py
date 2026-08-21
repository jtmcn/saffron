"""The runtime seam. Command construction is unit-tested; the four assertions
that actually chose this runtime live in spikes/cell-runtime.sh."""

from __future__ import annotations

import subprocess
import sys

from saffron.cell import runtime


def test_mount_renders_the_runtime_flag():
    m = runtime.Mount(kind="volume", source="saffron-wt-x", target="/work")
    assert m.to_flag() == "type=volume,source=saffron-wt-x,target=/work"


def test_readonly_mount_carries_the_suffix():
    m = runtime.Mount(kind="volume", source="s", target="/t", readonly=True)
    assert m.to_flag() == "type=volume,source=s,target=/t,readonly"


def test_run_argv_carries_every_control():
    argv = runtime._run_argv(
        image="saffron/cell:saffron",
        command=["nproc"],
        name="cell-1",
        network="saffron-cells",
        env={"HTTPS_PROXY": "http://10.88.0.2:3128"},
        cpus=1,
        memory="4g",
        mounts=[runtime.Mount("volume", "saffron-wt-1", "/work")],
        detach=False,
    )
    assert argv[:2] == ["container", "run"]
    assert "--rm" in argv
    assert "--cap-drop" in argv and "ALL" in argv
    assert "--network" in argv and "saffron-cells" in argv
    assert "--cpus" in argv and "1" in argv
    assert "--memory" in argv and "4g" in argv
    assert "type=volume,source=saffron-wt-1,target=/work" in argv
    assert "HTTPS_PROXY=http://10.88.0.2:3128" in argv
    assert argv[-2:] == ["saffron/cell:saffron", "nproc"]


def test_detached_run_is_not_removed_on_exit():
    argv = runtime._run_argv(
        image="i",
        command=[],
        name="c",
        network=None,
        env=None,
        cpus=None,
        memory=None,
        mounts=[],
        detach=True,
    )
    assert "-d" in argv
    assert "--rm" not in argv


def test_container_ip_ignores_the_gateway():
    inspected = '{"networks":[{"gateway":"10.88.0.1","address":"10.88.0.4/24"}]}'
    assert runtime._first_address(inspected, "10.88.0.") == "10.88.0.4"


def test_container_ip_is_none_when_absent():
    assert runtime._first_address('{"networks":[]}', "10.88.0.") is None


def test_call_is_the_public_form_of_the_private_helper():
    done = runtime.call(["true"], timeout_s=10)
    assert done.returncode == 0
    assert done.timed_out is False


def test_the_subnet_is_the_only_place_the_network_is_written():
    """Derived, not re-typed: a stale second copy probes an address that no
    longer exists and reports 'unreachable' having reached nothing."""
    assert runtime.SUBNET_PREFIX == "10.88.0."
    assert runtime.GATEWAY == "10.88.0.1"
    assert runtime.GATEWAY.startswith(runtime.SUBNET_PREFIX)


def _script(monkeypatch, body: str) -> None:
    """Run a real subprocess in place of `container exec`.

    The read loop is all timing and pipes, so a fake process would only test
    the fake. This substitutes the program, never the plumbing.
    """
    real = subprocess.Popen

    def _popen(argv, **kwargs):
        assert argv[:3] == [runtime.RUNTIME, "exec", "-i"]
        return real([sys.executable, "-c", body], **kwargs)

    monkeypatch.setattr(subprocess, "Popen", _popen)


def test_a_runner_that_exits_on_its_own_names_no_bound(monkeypatch):
    """Also the proof that the request reaches the process on stdin."""
    _script(monkeypatch, "import sys; print(sys.stdin.read().strip()); print('bye')")
    lines: list[str] = []
    done = runtime.exec_stream(
        "cell", ["runner"], stdin_data="hello\n", on_line=lines.append
    )
    assert lines == ["hello", "bye"]
    assert done.bound == ""
    assert done.timed_out is False
    assert done.returncode == 0


def test_a_stream_that_goes_silent_mid_turn_is_cut_by_the_idle_bound(monkeypatch):
    """§4.3's idle axis: silence *before* the payload says it is done."""
    _script(
        monkeypatch,
        "import sys, time; print('working'); sys.stdout.flush(); time.sleep(30)",
    )
    lines: list[str] = []
    done = runtime.exec_stream(
        "cell",
        ["runner"],
        stdin_data="{}",
        on_line=lines.append,  # never signals done
        timeout_s=30,
        idle_s=0.3,
    )
    assert lines == ["working"]
    assert done.bound == "idle"
    assert done.timed_out is True
    assert done.returncode == 124


def test_a_held_pipe_after_the_done_signal_is_a_success(monkeypatch):
    """The one §4.3 says people get wrong: the payload emitted its result and a
    child process is holding stdout open, so EOF never arrives. That turn
    finished — closing the pipe must not make it a timeout."""
    _script(
        monkeypatch,
        "import sys, time; print('event'); print('done'); "
        "sys.stdout.flush(); time.sleep(30)",
    )
    lines: list[str] = []
    done = runtime.exec_stream(
        "cell",
        ["runner"],
        stdin_data="{}",
        on_line=lambda line: bool(lines.append(line)) or line == "done",
        timeout_s=30,
        idle_s=10,
        completion_s=0.3,
    )
    assert lines == ["event", "done"]
    assert done.bound == "completion"
    assert done.timed_out is False
    assert done.returncode == 0


def test_a_productive_but_endless_stream_still_hits_the_wall_clock(monkeypatch):
    """Never idle for a moment, and never finished either — the axis the other
    two cannot catch."""
    _script(
        monkeypatch,
        "import sys, time\nwhile True:\n    print('tick')\n"
        "    sys.stdout.flush()\n    time.sleep(0.02)\n",
    )
    lines: list[str] = []
    done = runtime.exec_stream(
        "cell",
        ["runner"],
        stdin_data="{}",
        on_line=lines.append,
        timeout_s=0.4,
        idle_s=10,
    )
    assert len(lines) > 1
    assert done.bound == "wall"
    assert done.timed_out is True
    assert done.returncode == 124
