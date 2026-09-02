"""The egress proxy — a sibling container on both networks (DESIGN.md §5.1).

Addressed by IP, always: an internal network has no DNS, so a hostname in
HTTPS_PROXY resolves to nothing and the failure reads as an API outage
(Appendix G).
"""

from __future__ import annotations

import time

from saffron.cell import runtime

PROXY_TAG = "saffron/proxy"
PROXY_NAME = "saffron-proxy"
PROXY_PORT = 3128
# The one host the allowlist admits. `images/squid.conf` has to agree and a test
# asserts it: this is what preflight probes, that is what lets it through.
UPSTREAM_HOST = "api.anthropic.com"
EGRESS_NETWORK = "saffron-egress"
EGRESS_SUBNET = "10.89.0.0/24"


def _ensure_egress_network() -> None:
    """A real (non-internal) network, created once and reused (DESIGN.md §5.1).

    `--internal` networks have no route to the internet at all (measured) —
    the proxy needs one leg on such a network to reach api.anthropic.com.
    """
    done = runtime.call(
        [
            runtime.RUNTIME,
            "network",
            "create",
            "--subnet",
            EGRESS_SUBNET,
            EGRESS_NETWORK,
        ]
    )
    # Left over from a prior run is the one tolerable failure; anything else
    # means the proxy is about to start with no route out.
    if done.returncode != 0 and "already exists" not in done.stderr:
        raise runtime.CellRuntimeError(
            f"creating {EGRESS_NETWORK} failed: {done.stderr.strip()}"
        )


def start_proxy(internal_network: str, *, timeout_s: float = 30) -> str:
    """Start the proxy, dual-homed on the cells network and the egress
    network, and return its address on the cells network."""
    runtime.remove_container(PROXY_NAME)
    _ensure_egress_network()
    # Runs as the squid user from the start, not root: squid's own privilege
    # drop needs CAP_SETUID/CAP_SETGID, which this sibling doesn't need (R6).
    # Egress network first: apple/container routes the default gateway
    # through the first --network flag, and only the egress leg has one.
    runtime.run_detached(
        PROXY_NAME,
        PROXY_TAG,
        network=(EGRESS_NETWORK, internal_network),
        user="squid:squid",
    )

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        address = runtime.container_ip(PROXY_NAME)
        if address:
            return address
        time.sleep(0.5)
    runtime.remove_container(PROXY_NAME)
    raise runtime.CellRuntimeError(
        f"the proxy took an address longer than {timeout_s}s — a cell addressed "
        "by hostname would fail here with a DNS error instead"
    )


def denied_egress(limit: int = 10) -> list[str]:
    """What the proxy refused, read before `stop_proxy` or not at all: the log
    is the container's stdout (squid.conf), so it dies with the container.

    A denied CONNECT otherwise reaches the operator as an unexplained API
    error — the allowlist is a hostname list, and the host it is missing is
    exactly the one nobody thought to put there."""
    return [line for line in _proxy_log() if _status(line)[0] == "TCP_DENIED"][:limit]


def failed_egress(limit: int = 10) -> list[str]:
    """What the proxy allowed and could not open, read on the same terms as
    `denied_egress` and never merged into it.

    Squid answers an allowed CONNECT it cannot complete with a 5xx and
    `HIER_NONE` — a route out that is missing rather than a hostname that is —
    and the operator meets it as the same unexplained API error. Kept apart
    from the denials because the fix is not: one is a line in the allowlist,
    the other is the network the proxy is on."""
    return [line for line in _proxy_log() if _is_failure(line)][:limit]


def _proxy_log() -> list[str]:
    """The proxy's log, or nothing at all.

    Both readers run from teardown's `finally`, so neither may raise: `call`
    raises when the runtime binary cannot be executed, and a proxy that is
    already gone exits nonzero with a message that is not a log."""
    try:
        done = runtime.call([runtime.RUNTIME, "logs", PROXY_NAME], timeout_s=10)
    except runtime.CellRuntimeError:
        return []
    if done.returncode != 0:
        return []
    return [line.strip() for line in (done.stdout + done.stderr).splitlines()]


def _status(line: str) -> tuple[str, str]:
    """Squid's `TAG/CODE` column, by position — field 3 of the default
    logformat, and never "whichever field happens to hold a slash".

    The request URL is a field too, and the cell chooses it. Scanning for a
    slash lets a cell fetching `/TCP_DENIED` suppress its own route failures
    here and forge denials in `denied_egress`, both measured."""
    fields = line.split()
    if len(fields) < 4:
        return "", ""
    tag, _, code = fields[3].partition("/")
    return tag, code


def _is_failure(line: str) -> bool:
    """A row squid could not satisfy, as opposed to one it carried an answer for.

    5xx is squid answering for an upstream it could not reach and `000` is squid
    writing no reply at all. A 4xx is the *upstream* answering — `squid.conf`
    allows plain HTTP to the allowlisted host, so a 404 or a 429 is the proxy
    working, and reporting it would point the operator at the network when the
    answer came back. Denials carry their own report and are left to it."""
    tag, code = _status(line)
    if not tag or tag == "TCP_DENIED":
        return False
    return code == "000" or (code.isdigit() and int(code) >= 500)


def stop_proxy() -> None:
    runtime.remove_container(PROXY_NAME)


def proxy_env(address: str) -> dict[str, str]:
    url = f"http://{address}:{PROXY_PORT}"
    # Loopback is the cell talking to itself, and squid denies it: a test that
    # binds a socket failed at baseline on every run (backlog item 41). These
    # variables bound nothing anyway — the cells network is `--internal`.
    return {
        "HTTPS_PROXY": url,
        "HTTP_PROXY": url,
        "NO_PROXY": "127.0.0.1,localhost",
    }
