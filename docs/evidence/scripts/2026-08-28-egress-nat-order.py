"""Attach order on the internal network decides whether the proxy has a route out.

`uv run python docs/evidence/scripts/2026-08-28-egress-nat-order.py`

Two orders, one difference between them, run against a real cell runtime:

  A. create the internal network, start the proxy, probe.
  B. create the internal network, run one container on it, start the proxy, probe.

B is production's order — `assert_host_is_unreachable` runs a probe container
before the proxy starts (`saffron/cell/session.py`). On apple/container 1.3.0 it
leaves the dual-homed proxy with a default route it cannot use.

The probe is a TCP connect to api.anthropic.com's address from inside the proxy,
by IP: what fails is the route, and a hostname would report it as DNS.
"""

from __future__ import annotations

from saffron.cell import proxy, runtime

NETWORK = "saffron-natorder"
# api.anthropic.com at the time of measurement. By IP on purpose: DNS to the
# egress gateway fails the same way, and the resolver error hides the routing one.
UPSTREAM = "160.79.104.10"


def egress_works() -> bool:
    """Can the proxy open TCP 443 upstream? Run inside the proxy, not beside it."""
    done = runtime.call(
        [runtime.RUNTIME, "exec", proxy.PROXY_NAME, "nc", "-z", "-w", "5", UPSTREAM, "443"],
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


if __name__ == "__main__":
    version = runtime.call([runtime.RUNTIME, "--version"], timeout_s=30).stdout.strip()
    print(version)
    for label, container_first in (("A proxy first", False), ("B container first", True)):
        print(f"{label:20} egress={'OK' if attempt(container_first=container_first) else 'FAIL'}")
