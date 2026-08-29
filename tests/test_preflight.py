from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from saffron import preflight
from saffron.cell import runtime

LSOF = (Path(__file__).parent / "fixtures" / "lsof-listen.txt").read_text()


NONE: frozenset[str] = frozenset()


def _ports(lsof_output: str, tolerated: frozenset[str] = NONE) -> list[int]:
    return preflight.probed_ports(preflight.listening_sockets(lsof_output), tolerated)[
        0
    ]


def test_real_lsof_output_yields_the_ports_a_cell_can_reach():
    """Captured from the machine v0.5 ran on. Its redis, its postgres and its
    six python servers are loopback-bound; four macOS services are not."""
    assert _ports(LSOF) == [3283, 5000, 7000, 49152, 60215, 60216]
    # The guessed list would have reported a clean probe against every one.
    assert not {5432, 6379, 8000}.intersection(_ports(LSOF))


def test_a_command_name_holding_a_space_still_parses():
    """lsof truncates COMMAND to nine characters, spaces included, so the row
    is read from the right."""
    row = (
        "COMMAND     PID USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME\n"
        "Google Ch  1234 joel   30u  IPv4 0x0000000000000001      0t0  "
        "TCP *:9222 (LISTEN)\n"
    )
    assert preflight.listening_sockets(row) == [("Google Ch", 9222)]


def test_a_listing_with_only_loopback_listeners_is_a_real_empty():
    """The floor: enumeration ran, and nothing it found is reachable."""
    rows = [
        line for line in LSOF.splitlines() if "127.0.0.1" in line or "[::1]" in line
    ]
    assert rows
    assert _ports(LSOF.splitlines()[0] + "\n" + "\n".join(rows)) == []


def test_lsof_missing_raises_rather_than_narrowing_the_probe_to_nothing(monkeypatch):
    """The `_lan_address` defect, one function over: an enumeration that fails
    silently makes the probe cover nothing and report green."""

    def _no_lsof(*_a, **_k):
        raise FileNotFoundError("lsof")

    monkeypatch.setattr(subprocess, "run", _no_lsof)
    with pytest.raises(runtime.CellRuntimeError, match="could not be enumerated"):
        preflight.host_probe_ports()


@pytest.mark.parametrize(
    "returncode,stdout,stderr",
    [
        (1, "", "lsof: WARNING: can't stat() ..."),  # nothing listed at all
        (0, "some other tool's output\n", ""),  # not lsof's listing
    ],
)
def test_a_listing_that_is_not_lsofs_raises(monkeypatch, returncode, stdout, stderr):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, returncode, stdout, stderr),
    )
    with pytest.raises(runtime.CellRuntimeError, match="produced no listing"):
        preflight.host_probe_ports()


def test_the_probe_script_carries_the_enumerated_ports():
    script = preflight._probe_script(["10.88.0.1"], [8000, 8001])
    assert "ports=[8000, 8001]" in script
    assert "addrs=['10.88.0.1']" in script


def test_nothing_is_tolerated_unless_it_is_named(monkeypatch):
    """The default, and the whole point of it: an unnamed listener is probed."""
    monkeypatch.delenv("SAFFRON_ALLOW_HOST_PROCESS", raising=False)
    assert preflight.tolerated_processes() == NONE
    ports, tolerated = preflight.probed_ports(
        preflight.listening_sockets(LSOF), preflight.tolerated_processes()
    )
    assert 49152 in ports and tolerated == []


def test_a_named_process_drops_out_of_the_probe(monkeypatch):
    """rapportd's three sockets, accepted by name — and only its three."""
    monkeypatch.setenv("SAFFRON_ALLOW_HOST_PROCESS", " rapportd , ")
    assert preflight.tolerated_processes() == {"rapportd"}
    ports, tolerated = preflight.probed_ports(
        preflight.listening_sockets(LSOF), preflight.tolerated_processes()
    )
    assert ports == [3283, 5000, 7000]
    assert tolerated == ["rapportd:49152", "rapportd:60215", "rapportd:60216"]


def test_a_different_process_on_a_tolerated_port_is_still_probed():
    """The name is what was accepted, not the number it happened to hold —
    rapportd's ports are dynamic, so the next thing on 49152 is a stranger."""
    assert preflight.probed_ports([("nc", 49152)], frozenset({"rapportd"}))[0] == [
        49152
    ]
    # Sharing a port with a tolerated process does not launder it, and it takes
    # the tolerated one back into the probe with it.
    ports, tolerated = preflight.probed_ports(
        [("nc", 49152), ("rapportd", 49152)], frozenset({"rapportd"})
    )
    assert ports == [49152] and tolerated == []


def test_enumeration_that_cannot_run_still_raises_when_a_process_is_named(monkeypatch):
    """Tolerating a listener must not become tolerating a probe that covered
    nothing — the `_lan_address` defect, wearing an allowlist."""
    monkeypatch.setenv("SAFFRON_ALLOW_HOST_PROCESS", "rapportd")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 1, "", "lsof: no listing"),
    )
    with pytest.raises(runtime.CellRuntimeError, match="produced no listing"):
        preflight.host_probe_ports()


def test_the_probe_checks_the_ports_it_was_given(monkeypatch):
    """One enumeration per run: probing a second, freshly-taken list means the
    line the operator read is not the one that was checked."""
    seen: dict = {}

    def _run_ephemeral(image, command, **kwargs):
        seen["script"] = command[-1]
        return runtime.Completed(0, "", "")

    monkeypatch.setattr("saffron.cell.runtime.run_ephemeral", _run_ephemeral)

    def _boom():
        raise AssertionError("the probe re-enumerated instead of using its argument")

    monkeypatch.setattr("saffron.preflight.host_probe_ports", _boom)
    preflight.probe_host_bindings("img", "net", [4242])
    assert "ports=[4242]" in seen["script"]
    # And the connects are concurrent, or ~100 listeners exhaust the 300s cap.
    assert "ThreadPoolExecutor" in seen["script"]


def test_any_http_status_from_the_upstream_is_reachability(monkeypatch):
    """401 is the expected answer and it is a pass: what is established is the
    route, and no credential is being tested (DESIGN.md §5.1.1)."""
    seen = {}

    def fake(image, command, *, network=None, env=None, timeout_s=120, **kw):
        seen["env"] = env
        seen["network"] = network
        return runtime.Completed(0, "STATUS 401\n", "")

    monkeypatch.setattr(preflight.runtime, "run_ephemeral", fake)
    preflight.assert_proxy_reaches_upstream("img", "saffron-cells", "10.88.0.2")
    # Through the proxy, by IP: an internal network has no DNS to resolve a name.
    assert seen["env"]["HTTPS_PROXY"] == "http://10.88.0.2:3128"
    assert seen["network"] == "saffron-cells"


def test_a_proxy_that_cannot_reach_the_upstream_aborts_before_the_cell(monkeypatch):
    """The failure that shipped: squid answered, and answered 503. An abort
    here is `error` — the repo's code is not what is wrong."""
    monkeypatch.setattr(
        preflight.runtime,
        "run_ephemeral",
        lambda *a, **k: runtime.Completed(
            1, "", "urllib.error.URLError: tunnel failed"
        ),
    )
    with pytest.raises(runtime.CellRuntimeError, match="could not reach"):
        preflight.assert_proxy_reaches_upstream("img", "saffron-cells", "10.88.0.2")


def test_a_probe_that_printed_nothing_is_not_a_pass(monkeypatch):
    """Exit 0 with no STATUS line is a container that started and did not run
    the probe — the same shape as the vacuous pass Appendix H is about."""
    monkeypatch.setattr(
        preflight.runtime, "run_ephemeral", lambda *a, **k: runtime.Completed(0, "", "")
    )
    with pytest.raises(runtime.CellRuntimeError, match="could not reach"):
        preflight.assert_proxy_reaches_upstream("img", "saffron-cells", "10.88.0.2")


def test_the_abort_reports_the_exception_not_the_runtimes_progress_output(monkeypatch):
    """`container run` prints image-pull progress to stderr before the container
    says anything, so a head-truncated message reports the pull and not the
    failure — which is the one line an operator needs."""
    noise = "\n".join(
        [
            "[0/6] [0s]",
            "[1/6] Fetching image [0s]",
            "[6/6] Starting container [0s]",
            "Traceback (most recent call last):",
            '  File "<string>", line 3, in <module>',
            "urllib.error.URLError: <urlopen error timed out>",
        ]
    )
    monkeypatch.setattr(
        preflight.runtime,
        "run_ephemeral",
        lambda *a, **k: runtime.Completed(1, "", noise),
    )
    with pytest.raises(runtime.CellRuntimeError) as raised:
        preflight.assert_proxy_reaches_upstream("img", "saffron-cells", "10.88.0.2")
    assert "urlopen error timed out" in str(raised.value)
    assert "Fetching image" not in str(raised.value)
