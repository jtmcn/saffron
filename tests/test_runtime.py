"""The runtime seam. Command construction is unit-tested; the four assertions
that actually chose this runtime live in spikes/cell-runtime.sh."""

from __future__ import annotations

import subprocess
import sys
import time

import pytest

from saffron.cell import runtime
from saffron.cell.runtimes import apple, podman


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


def test_the_apple_dialect_states_what_was_measured_of_it():
    """Every member of the dialect, pinned as a literal — which is the only way
    to pin it. A test that read `apple.DIALECT.exec_workdir_flag` and compared
    it to itself passes against any value, including a nonsense one: measured,
    that is exactly what the first version of this test did.

    These four are the differences a second runtime was observed to spell
    differently (`docs/evidence/2026-09-11-podman-as-a-second-cell-runtime.md`).
    A second runtime gets its own copy of this test, against its own values;
    they are claims about a product, so they do not generalise.

    `container` and `--cpus` appear here as literals because `tests/**` is out
    of the structure rule's scope on purpose — a test that pins what a runtime
    is called must be able to say it.
    """
    assert apple.DIALECT.binary == "container"
    assert apple.DIALECT.cpu_offset == 1
    assert apple.DIALECT.exec_workdir_flag == "--cwd"
    assert apple.DIALECT.cpu_flags(2) == ["--cpus", "2"]


def test_the_podman_dialect_states_what_was_measured_of_it():
    """podman's own values, pinned as literals for the reason apple's are: a test
    that reads the dialect and compares it to itself passes against anything.

    Each is measured in
    `docs/evidence/2026-09-11-podman-as-a-second-cell-runtime.md`. The CPU flag
    is a mask and not a quota because the quota left the cell reporting all four
    of the host's CPUs, which is §5.1's oversubscription mode exactly. The
    offset is 0 because there is no VM to be allocated a spare vCPU.
    """
    assert podman.DIALECT.binary == "podman"
    assert podman.DIALECT.cpu_offset == 0
    assert podman.DIALECT.exec_workdir_flag == "-w"
    assert podman.DIALECT.cpu_flags(2) == ["--cpuset-cpus", "0-1"]
    assert podman.DIALECT.cpu_flags(1) == ["--cpuset-cpus", "0-0"]


def test_only_the_runtime_without_a_vm_asks_for_in_guest_hardening():
    """§5.1 declines `no-new-privileges` and seccomp under a VM-per-cell runtime
    *because* the private kernel is the boundary offered instead. A shared-kernel
    runtime has no such offer, so the flags come back — measured, `NoNewPrivs` is
    1 inside a podman cell with the flag and 0 without it.

    Asserted as a pair. Either half alone passes while the other silently agrees
    with it, and the whole point is that the two runtimes differ here.
    """
    assert apple.DIALECT.security_flags == []
    assert podman.DIALECT.security_flags == ["--security-opt", "no-new-privileges"]


def test_a_runtime_nobody_named_is_the_default_and_an_unknown_one_raises():
    """Declared, never detected (§5.1.2). An unknown name must raise rather than
    fall back: a fallback reports the default's calibration for a runtime nobody
    chose, and `CPU_OFFSET` wrong by one surfaces as flaky gate timings rather
    than as an error."""
    assert runtime.select_dialect(None) is apple.DIALECT
    assert runtime.select_dialect("") is apple.DIALECT
    assert runtime.select_dialect("  ") is apple.DIALECT
    assert runtime.select_dialect("podman") is podman.DIALECT
    assert runtime.select_dialect(" podman ") is podman.DIALECT
    with pytest.raises(runtime.CellRuntimeError) as raised:
        runtime.select_dialect("containerd")
    # The message names what it does know, or the operator's next move is a grep.
    assert "apple" in str(raised.value) and "podman" in str(raised.value)


def test_every_declared_runtime_satisfies_the_dialect():
    """A dialect member added to the protocol and to one implementation only is
    an `AttributeError` on whichever runtime the operator picked second."""
    for name, dialect in runtime.DIALECTS.items():
        assert dialect.binary, name
        assert isinstance(dialect.cpu_offset, int), name
        assert dialect.exec_workdir_flag.startswith("-"), name
        assert isinstance(dialect.security_flags, list), name
        assert dialect.cpu_flags(2), name


def test_exec_is_told_its_working_directory_before_the_container():
    """The wiring, as against the spelling above. `exec_` and `exec_stream`
    share one builder because the flag is the dialect's to name and two copies
    are two things to miss; what this pins is that the flag and its value land
    together, ahead of the container name, so the command is not handed its own
    workdir as an argument.
    """
    argv = runtime.exec_argv("cell-1", ["true"], workdir="/work")
    assert argv == [runtime.RUNTIME, "exec", "--cwd", "/work", "cell-1", "true"]


def test_exec_without_a_workdir_names_no_directory():
    argv = runtime.exec_argv("cell-1", ["true"], workdir=None)
    assert argv == [runtime.RUNTIME, "exec", "cell-1", "true"]


def test_the_streaming_exec_is_the_same_command_with_stdin_attached():
    """`exec_stream` gains no capability `exec_` lacks (§5.1) — the only
    difference is `-i`, and it precedes the workdir flag so that the first three
    fields stay the shape the read-loop tests assert against."""
    streamed = runtime.exec_argv("c", ["x"], workdir="/work", interactive=True)
    collected = runtime.exec_argv("c", ["x"], workdir="/work")
    assert streamed[:3] == [runtime.RUNTIME, "exec", "-i"]
    assert streamed[:2] + streamed[3:] == collected


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


def test_a_bare_carriage_return_in_stdout_survives_the_call():
    """`text=True` applies universal-newline translation and would silently
    rewrite a bare "\\r" into "\\n" before any caller saw it — the mechanism
    that let a suppression hide inside a diff `integrity_gate` was handed."""
    done = runtime.call(
        [sys.executable, "-c", "import sys; sys.stdout.write('a\\rb\\n')"],
        timeout_s=10,
    )
    assert done.stdout == "a\rb\n"


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


def test_the_completion_window_does_not_restart_on_every_line(monkeypatch):
    """The window is fixed when the result event lands. Recomputed per line, a
    child writing steadily holds the loop open past every bound there is —
    the unbounded wait §4.3's five bounds exist to prevent."""
    _script(
        monkeypatch,
        "import sys, time\nprint('done')\nsys.stdout.flush()\n"
        "for _ in range(250):\n    print('tick')\n"
        "    sys.stdout.flush()\n    time.sleep(0.02)\n",
    )
    lines: list[str] = []
    started = time.monotonic()
    done = runtime.exec_stream(
        "cell",
        ["runner"],
        stdin_data="{}",
        on_line=lambda line: bool(lines.append(line)) or line == "done",
        timeout_s=30,
        idle_s=10,
        completion_s=0.3,
    )
    # The child writes for five seconds; the window closes after a third of one.
    assert time.monotonic() - started < 3
    assert done.bound == "completion"
    assert done.timed_out is False


def test_the_network_address_is_not_mistaken_for_the_cell(monkeypatch):
    """`inspect` printing the subnet first would otherwise hand out 10.88.0.0 as
    the cell's own, and every proxied call would fail as an upstream outage."""
    inspected = '{"network":"10.88.0.0/24","gateway":"10.88.0.1","address":"10.88.0.4"}'
    assert runtime._first_address(inspected, "10.88.0.") == "10.88.0.4"


def test_an_overlapping_network_names_the_one_already_holding_the_subnet(
    monkeypatch,
):
    """A SIGKILLed run leaves a network behind, and the next create fails on
    the subnet rather than the name. The runtime's own message says which
    subnet and not which network, so the operator is told to go look."""
    listing = "NETWORK         SUBNET\nsaffron-cells   10.88.0.0/24\n"

    def fake_call(argv, timeout_s=120):
        if "create" in argv:
            return runtime.Completed(
                1, "", "Error: IPv4 subnet 10.88.0.0/24 overlaps an existing network"
            )
        return runtime.Completed(0, listing, "")

    monkeypatch.setattr(runtime, "_call", fake_call)
    try:
        runtime.create_network("saffron-test-cells")
    except runtime.CellRuntimeError as exc:
        assert "saffron-cells" in str(exc), exc
    else:
        raise AssertionError("an overlapping subnet must raise")


def test_a_partial_overlap_names_the_holder_too(monkeypatch):
    """The runtime rejects `10.89.0.128/25` against a holder on `10.89.0.0/24`
    with the same wording, and that is the case an operator cannot work out by
    eye — an equality test would name nobody in exactly the one that needs it."""
    listing = "NETWORK         SUBNET\nsaffron-egress  10.89.0.0/24\n"

    def fake_call(argv, timeout_s=120):
        if "create" in argv:
            return runtime.Completed(
                1, "", "Error: IPv4 subnet overlaps an existing network"
            )
        return runtime.Completed(0, listing, "")

    monkeypatch.setattr(runtime, "_call", fake_call)
    assert runtime.networks_on_subnet("10.89.0.128/25") == ["saffron-egress"]


def test_a_listing_that_could_not_be_read_adds_no_detail_and_still_raises(monkeypatch):
    """`networks_on_subnet` only ever decorates an error already being raised,
    so a failed listing must not become a second failure."""

    def fake_call(argv, timeout_s=120):
        if "create" in argv:
            return runtime.Completed(
                1, "", "Error: IPv4 subnet overlaps an existing network"
            )
        return runtime.Completed(1, "", "Error: the daemon is not running")

    monkeypatch.setattr(runtime, "_call", fake_call)
    assert runtime.networks_on_subnet("10.88.0.0/24") == []
    try:
        runtime.create_network("saffron-test-cells")
    except runtime.CellRuntimeError as exc:
        assert "overlaps" in str(exc)
    else:
        raise AssertionError("an overlapping subnet must raise")
