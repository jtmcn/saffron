from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from saffron.cell import runtime

# The two host tools this codebase uses to leave the machine. `gh` joins the
# cell runtime because §4.2.1's refusals shell out to it: a test that reached
# the real one would depend on the network and on whoever is logged in.
FORBIDDEN_EXECS = frozenset({runtime.RUNTIME, "gh"})


class HostToolExecInTest(BaseException):
    """Not an `Exception`: `session.export_patch` and `gates.runner` both catch
    `Exception` broadly and turn it into a watch line, which would convert this
    tripwire into a green run reporting nothing."""


@pytest.fixture(autouse=True)
def no_host_tool_exec(request, monkeypatch):
    """A test without the `cell` marker must never exec `apple/container` or `gh`.

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
