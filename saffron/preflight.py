"""Per-run readiness. In v0.5 it is one probe, and N1 rests on it.

An `--internal` network still routes to the host gateway, so a host service
bound to 0.0.0.0 — a Postgres, a dev server — is reachable from inside a cell
without ever traversing the proxy. Measured, not assumed (Appendix G).
"""

from __future__ import annotations

import subprocess

from saffron.cell import runtime

# Ports worth asking about: the ones a developer machine actually listens on.
PROBED_PORTS = (5432, 5433, 3306, 6379, 8000, 8080, 27017)


def _lan_address() -> str | None:
    out = subprocess.run(
        ["ipconfig", "getifaddr", "en0"], capture_output=True, text=True
    )
    return out.stdout.strip() or None


def _gateway(subnet_prefix: str = "10.88.0.") -> str:
    return f"{subnet_prefix}1"


def _probe_script(addresses: list[str]) -> str:
    return (
        "import socket,sys\n"
        f"addrs={addresses!r}\n"
        f"ports={list(PROBED_PORTS)!r}\n"
        "hit=[]\n"
        "for a in addrs:\n"
        "    for p in ports:\n"
        "        s=socket.socket(); s.settimeout(1.5)\n"
        "        try:\n"
        "            s.connect((a,p)); hit.append(f'{a}:{p}')\n"
        "        except OSError: pass\n"
        "        finally: s.close()\n"
        "print('|'.join(hit))\n"
    )


def probe_host_bindings(image_tag: str, network: str) -> list[str]:
    """Addresses at which a host service answered from inside a cell.

    An empty list is the passing result. Anything else is a service bound to
    0.0.0.0 that a cell can reach, and the fix is on the host — bind it to
    127.0.0.1 — never in the cell.
    """
    addresses = [a for a in (_gateway(), _lan_address()) if a]
    done = runtime.run_ephemeral(
        image_tag,
        ["python", "-c", _probe_script(addresses)],
        network=network,
        timeout_s=180,
    )
    if done.returncode != 0:
        raise runtime.CellRuntimeError(
            f"the host-binding probe did not run: {done.stderr.strip()}. "
            "A probe that did not run is not a probe that passed."
        )
    return [hit for hit in done.stdout.strip().split("|") if hit]


def assert_host_is_unreachable(image_tag: str, network: str) -> None:
    reachable = probe_host_bindings(image_tag, network)
    if reachable:
        raise runtime.CellRuntimeError(
            "host services answered from inside a cell at "
            + ", ".join(reachable)
            + " — bind them to 127.0.0.1. N1 is not satisfied until this is empty."
        )
