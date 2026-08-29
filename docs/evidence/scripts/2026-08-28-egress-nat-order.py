"""Attach order on the internal network decides whether the proxy has a route out.

`uv run python docs/evidence/scripts/2026-08-28-egress-nat-order.py`

Two orders, one difference between them, run against a real cell runtime:

  A. create the internal network, start the proxy, probe.
  B. create the internal network, run one container on it, start the proxy, probe.

B is production's order — `assert_host_is_unreachable` runs a probe container
before the proxy starts (`saffron/cell/session.py`). On apple/container 1.3.0 it
leaves the dual-homed proxy with a default route it cannot use.

The probe is a TCP connect to api.anthropic.com's address from inside the proxy,
by IP: what fails is the route, and a hostname would report it as DNS. The host
is checked against the same address first, so an address that has since moved
reads as an unusable control rather than as a reproduction.

Not safe beside a live run: it removes the shared `saffron-proxy` container, and
it leaves `saffron-egress` behind because `start_proxy` creates it.
"""

from __future__ import annotations

import socket

from saffron.cell import proxy, runtime

NETWORK = "saffron-natorder"
# api.anthropic.com at the time of measurement. By IP on purpose: DNS to the
# egress gateway fails the same way, and the resolver error hides the routing one.
UPSTREAM = "160.79.104.10"


def egress_works() -> bool:
    """Can the proxy open TCP 443 upstream? Run inside the proxy, not beside it."""
    done = runtime.call(
        [
            runtime.RUNTIME,
            "exec",
            proxy.PROXY_NAME,
            "nc",
            "-z",
            "-w",
            "5",
            UPSTREAM,
            "443",
        ],
        timeout_s=60,
    )
    return done.returncode == 0


def attempt(*, container_first: bool) -> bool:
    proxy.stop_proxy()
    runtime.remove_network(NETWORK)
    runtime.create_network(NETWORK)
    try:
        if container_first:
            runtime.run_ephemeral("alpine:3", ["true"], network=NETWORK, timeout_s=120)
        proxy.start_proxy(NETWORK)
        return egress_works()
    finally:
        proxy.stop_proxy()
        runtime.remove_network(NETWORK)


def host_reaches_upstream() -> bool:
    """The control. Both arms failing means nothing if the address has moved."""
    with socket.socket() as sock:
        sock.settimeout(5)
        return sock.connect_ex((UPSTREAM, 443)) == 0


if __name__ == "__main__":
    version = runtime.call([runtime.RUNTIME, "--version"], timeout_s=30).stdout.strip()
    print(version)
    if not host_reaches_upstream():
        raise SystemExit(
            f"the host cannot reach {UPSTREAM}:443 either — re-resolve "
            "api.anthropic.com and update UPSTREAM. Nothing below would mean anything."
        )
    # Both sequences: the subject is order-dependent residual state, so a fixed
    # A-then-B would leave the confound the table is meant to remove.
    for first in (False, True):
        for container_first in (first, not first):
            label = "container first" if container_first else "proxy first"
            ok = attempt(container_first=container_first)
            print(f"  {label:16} egress={'OK' if ok else 'FAIL'}")
        print()
