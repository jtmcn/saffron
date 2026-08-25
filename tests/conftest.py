from __future__ import annotations

import pytest

from saffron.cell import runtime


@pytest.fixture(autouse=True)
def no_container_runtime(request, monkeypatch):
    """A test without the `cell` marker must never exec `apple/container`.

    Four `test_implement` tests reached it through `run_agent`'s reap and were
    green only because the host has the binary; inside a cell, where the repo's
    own suite runs as the baseline every gate result is subtracted from, they
    failed. A unit test whose outcome depends on a host tool is not a unit test.
    """
    if request.node.get_closest_marker("cell"):
        return
    real = runtime._call

    def guarded(argv, *args, **kwargs):
        if list(argv)[:1] == [runtime.RUNTIME]:
            raise AssertionError(
                f"an unmarked test shelled out to {runtime.RUNTIME}: {list(argv)}"
            )
        return real(argv, *args, **kwargs)

    monkeypatch.setattr(runtime, "_call", guarded)
