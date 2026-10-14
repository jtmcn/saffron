from __future__ import annotations

import ipaddress
import subprocess
from pathlib import Path
from typing import Protocol

import pytest

from saffron.cell import runtime

# Every runtime, not only the selected one, so the guard does not move with the
# environment; `gh` because a real one depends on the network and who is logged in.
FORBIDDEN_EXECS = frozenset({d.binary for d in runtime.DIALECTS.values()} | {"gh"})


class HostToolExecInTest(BaseException):
    """Not an `Exception`: `session.export_patch` and `gates.runner` both catch
    `Exception` broadly and turn it into a watch line, which would convert this
    tripwire into a green run reporting nothing."""


class _Markable(Protocol):
    """What this hook needs of an item — narrower than `pytest.Item` so a
    test can exercise it against a minimal stand-in rather than a live item
    the pytest internals constructed."""

    def get_closest_marker(self, name: str) -> object | None: ...


def pytest_runtest_setup(item: _Markable) -> None:
    """Skip a `cell`-marked test outright when the selected runtime is absent.

    The marker already says *this test needs a cell runtime*; this is the
    other half of that sentence, asked once per session through
    `runtime.probe()` (SA-0077). A plain hook function rather than a fixture:
    it runs ahead of fixture setup, so a skip here means the test's fixtures —
    including `no_host_tool_exec` below — never run at all, and a machine
    without the runtime sees one honest skip instead of a defect-shaped
    failure for every marked test.

    Consulted only for a marked test: this hook runs before the tripwire
    fixture is installed, so nothing but this guard keeps an unmarked test
    from execing the runtime.
    """
    if item.get_closest_marker("cell") is None:
        return
    if runtime.probe() is None:
        pytest.skip(f"no working {runtime.dialect().binary} found on this host")


@pytest.fixture(autouse=True)
def default_cell_runtime(request, monkeypatch):
    """Unmarked tests run under the default runtime, whatever the shell exports.

    They pin `apple/container`'s spellings as literals, and a cloud host sets
    `SAFFRON_CELL_RUNTIME` for every shell (docs/HOST-HARDENING.md §1a). A `cell`
    test drives the runtime the operator actually selected.
    """
    if request.node.get_closest_marker("cell"):
        return
    monkeypatch.setattr(runtime, "_selected", runtime.DIALECTS[runtime.DEFAULT_DIALECT])
    monkeypatch.setattr(runtime, "_admitted", False)


@pytest.fixture(autouse=True)
def no_host_tool_exec(request, monkeypatch):
    """A test without the `cell` marker must never exec a cell runtime or `gh`.

    Four `test_implement` tests reached the runtime through `run_agent`'s reap
    and were green only because the host has the binary; inside a cell, where
    the repo's own suite runs as the baseline every gate result is subtracted
    from, they failed. A unit test whose outcome depends on a host tool is not
    a unit test.

    Patched at `subprocess.Popen` rather than at `runtime._call`, because it is
    the one choke point both routes cross: `_call` reaches it through
    `subprocess.run`, and `exec_stream` — `run_agent`'s other import-time-bound
    default, the same shape as the defect above — calls it directly.

    Matched on the basename, so an absolute path to either tool is caught too.
    """
    if request.node.get_closest_marker("cell"):
        return
    real = subprocess.Popen

    def guarded(argv, *args, **kwargs):
        head = list(argv)[:1] if isinstance(argv, (list, tuple)) else []
        if head and Path(str(head[0])).name in FORBIDDEN_EXECS:
            raise HostToolExecInTest(
                f"an unmarked test shelled out to {head[0]}: {list(argv)}"
            )
        return real(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", guarded)


@pytest.fixture
def network_model(monkeypatch):
    """A model of the runtime's own networks, name to subnet, behind a fake
    `runtime._call`. The real `allocate_network` and `networks_on_subnet`
    run against it, rather than against a flat stub.

    Not autouse: only the handful of tests that bring up two cells, or two
    package runs, at once need the pool walked for real.
    """
    live: dict[str, str] = {}

    def fake_call(argv, timeout_s=120):
        argv = list(argv)
        if argv[1:3] == ["network", "create"]:
            name = argv[-1]
            subnet = argv[argv.index("--subnet") + 1]
            if name in live:
                return runtime.Completed(1, "", f"Error: network {name} already exists")
            wanted = ipaddress.ip_network(subnet)
            for held in live.values():
                if ipaddress.ip_network(held).overlaps(wanted):
                    return runtime.Completed(
                        1,
                        "",
                        f"Error: IPv4 subnet {subnet} overlaps an existing network",
                    )
            live[name] = subnet
            return runtime.Completed(0, "", "")
        if argv[1:3] == ["network", "list"]:
            rows = "\n".join(f"{n} {s}" for n, s in live.items())
            return runtime.Completed(0, f"NETWORK SUBNET\n{rows}\n", "")
        if argv[1:3] == ["network", "rm"]:
            live.pop(argv[-1], None)
            return runtime.Completed(0, "", "")
        return runtime.Completed(0, "", "")

    monkeypatch.setattr(runtime, "_call", fake_call)
    return live
