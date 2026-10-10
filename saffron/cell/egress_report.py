"""Four reads taken before teardown removes the cell or stops the proxy.

Run only when the plan turn's first call was not served (`SA-0235`,
`DESIGN.md` §5.1.1). Nothing here raises: a read that fails is reported,
never hidden, and never stops the read after it.
"""

from __future__ import annotations

from collections.abc import Callable

from saffron.cell import proxy, runtime

_HEAD_ARGS = ("head", "-c", "65536")
_EXEC_TIMEOUT_S = 30.0


def _from_call(label: str, call: Callable[[], runtime.Completed]) -> tuple[bool, str]:
    """One read, reported as `(ok, detail)` and never raised out."""
    try:
        done = call()
    except runtime.CellRuntimeError as exc:
        return False, f"{label}: {exc}"
    if done.timed_out:
        return False, f"{label}: timed out"
    if done.returncode != 0:
        return False, f"{label}: {done.stderr.strip()}"
    return True, f"{label}: {done.stdout}{done.stderr}"


def read_egress(container: str) -> list[tuple[bool, str]]:
    """Proxy state, proxy log, cell resolver, cell route, in that order."""
    return [
        _from_call("proxy state", lambda: runtime.inspect_container(proxy.PROXY_NAME)),
        _from_call("proxy log", lambda: runtime.container_logs(proxy.PROXY_NAME)),
        _from_call(
            "cell resolver",
            lambda: runtime.exec_(
                container,
                [*_HEAD_ARGS, "/etc/resolv.conf"],
                timeout_s=_EXEC_TIMEOUT_S,
            ),
        ),
        _from_call(
            "cell route",
            lambda: runtime.exec_(
                container,
                [*_HEAD_ARGS, "/proc/net/route"],
                timeout_s=_EXEC_TIMEOUT_S,
            ),
        ),
    ]
