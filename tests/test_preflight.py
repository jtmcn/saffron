from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from saffron import preflight
from saffron.cell import runtime

LSOF = (Path(__file__).parent / "fixtures" / "lsof-listen.txt").read_text()


def test_real_lsof_output_yields_the_ports_a_cell_can_reach():
    """Captured from the machine v0.5 ran on. Its redis, its postgres and its
    six python servers are loopback-bound; four macOS services are not."""
    assert preflight.listening_ports(LSOF) == [3283, 5000, 7000, 49152, 60215, 60216]
    # The guessed list would have reported a clean probe against every one.
    assert not {5432, 6379, 8000}.intersection(preflight.listening_ports(LSOF))


def test_a_command_name_holding_a_space_still_parses():
    """lsof truncates COMMAND to nine characters, spaces included, so the row
    is read from the right."""
    row = (
        "COMMAND     PID USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME\n"
        "Google Ch  1234 joel   30u  IPv4 0x0000000000000001      0t0  "
        "TCP *:9222 (LISTEN)\n"
    )
    assert preflight.listening_ports(row) == [9222]


def test_a_listing_with_only_loopback_listeners_is_a_real_empty():
    """The floor: enumeration ran, and nothing it found is reachable."""
    rows = [
        line for line in LSOF.splitlines() if "127.0.0.1" in line or "[::1]" in line
    ]
    assert rows
    assert (
        preflight.listening_ports(LSOF.splitlines()[0] + "\n" + "\n".join(rows)) == []
    )


def test_lsof_missing_raises_rather_than_narrowing_the_probe_to_nothing(monkeypatch):
    """The `_lan_address` defect, one function over: an enumeration that fails
    silently makes the probe cover nothing and report green."""

    def _no_lsof(*_a, **_k):
        raise FileNotFoundError("lsof")

    monkeypatch.setattr(subprocess, "run", _no_lsof)
    with pytest.raises(runtime.CellRuntimeError, match="could not be enumerated"):
        preflight.host_listening_ports()


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
        preflight.host_listening_ports()


def test_the_probe_script_carries_the_enumerated_ports():
    script = preflight._probe_script(["10.88.0.1"], [8000, 8001])
    assert "ports=[8000, 8001]" in script
    assert "addrs=['10.88.0.1']" in script
