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
    try:
        # Never raises, and never stalls teardown: this runs from a `finally`,
        # and `call` raises when the runtime binary itself cannot be executed.
        done = runtime.call([runtime.RUNTIME, "logs", PROXY_NAME], timeout_s=10)
    except runtime.CellRuntimeError:
        return []
    lines = (done.stdout + done.stderr).splitlines()
    return [line.strip() for line in lines if "TCP_DENIED" in line][:limit]


def stop_proxy() -> None:
    runtime.remove_container(PROXY_NAME)


def proxy_env(address: str) -> dict[str, str]:
    url = f"http://{address}:{PROXY_PORT}"
    return {"HTTPS_PROXY": url, "HTTP_PROXY": url, "NO_PROXY": ""}
