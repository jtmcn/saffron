from __future__ import annotations

import subprocess

import pytest

from saffron.cell import runtime


class ContainerExecInTest(BaseException):
    """Not an `Exception`: `session.export_patch` and `gates.runner` both catch
    `Exception` broadly and turn it into a watch line, which would convert this
    tripwire into a green run reporting nothing."""


@pytest.fixture(autouse=True)
def no_container_runtime(request, monkeypatch):
    """A test without the `cell` marker must never exec `apple/container`.

    Four `test_implement` tests reached it through `run_agent`'s reap and were
    green only because the host has the binary; inside a cell, where the repo's
    own suite runs as the baseline every gate result is subtracted from, they
    failed. A unit test whose outcome depends on a host tool is not a unit test.

    Patched at `subprocess.Popen` rather than at `runtime._call`, because it is
    the one choke point both routes cross: `_call` reaches it through
    `subprocess.run`, and `exec_stream` — `run_agent`'s other import-time-bound
    default, the same shape as the defect above — calls it directly.
    """
    if request.node.get_closest_marker("cell"):
        return
    real = subprocess.Popen

    def guarded(argv, *args, **kwargs):
        if isinstance(argv, (list, tuple)) and list(argv)[:1] == [runtime.RUNTIME]:
            raise ContainerExecInTest(
                f"an unmarked test shelled out to {runtime.RUNTIME}: {list(argv)}"
            )
        return real(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", guarded)
