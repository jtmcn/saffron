"""Per-run readiness. In v0.5 it is one probe, and N1 rests on it.

An `--internal` network still routes to the host gateway, so a host service
bound to 0.0.0.0 — a Postgres, a dev server — is reachable from inside a cell
without ever traversing the proxy. Measured, not assumed (Appendix G).
"""

from __future__ import annotations

import socket
import subprocess

from saffron.cell import runtime

_LSOF = ("lsof", "-nP", "-iTCP", "-sTCP:LISTEN")

# Everything else a listener can be bound to is reachable from a cell, at the
# gateway or at the LAN address.
_LOOPBACK = ("127.", "[::1]", "localhost")


def listening_ports(lsof_output: str) -> list[int]:
    """The host's non-loopback TCP listeners, from `lsof -nP -iTCP -sTCP:LISTEN`.

    The NAME column is the last field before `(LISTEN)`: `*:8000`,
    `0.0.0.0:5432`, `[::]:631`, `127.0.0.1:6379`. COMMAND can hold spaces, so
    the row is read from the right.
    """
    ports = set()
    for line in lsof_output.splitlines():
        fields = line.split()
        if len(fields) < 2 or fields[-1] != "(LISTEN)":
            continue
        address, _, port = fields[-2].rpartition(":")
        if port.isdigit() and not address.startswith(_LOOPBACK):
            ports.add(int(port))
    return sorted(ports)


def host_listening_ports() -> list[int]:
    """What the probe covers, enumerated rather than guessed.

    Seven remembered ports is a spot-check whose result reads as a proof: the
    v0.5 run that found a service on 8000 had four more on 8001+ that no list
    would have named (Appendix L). Enumeration failing must never narrow the
    probe to nothing, so anything short of lsof's own header — a missing lsof,
    a permission problem, silence — raises. An empty *result* is different and
    is a real pass: lsof reported, and every listener was loopback-bound.
    """
    try:
        done = subprocess.run(_LSOF, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        raise runtime.CellRuntimeError(
            f"the host's listening ports could not be enumerated ({exc}) — the "
            "probe would then cover nothing, which is not a probe that passed."
        ) from exc
    if not done.stdout.startswith("COMMAND"):
        raise runtime.CellRuntimeError(
            f"{' '.join(_LSOF)} produced no listing (exit {done.returncode}): "
            f"{(done.stderr or done.stdout).strip()[:200]!r}. A host with no TCP "
            "listener at all is likelier to be lsof failing than to be true."
        )
    return listening_ports(done.stdout)


def _lan_address() -> str:
    """The host's address on its own LAN, whichever interface carries it.

    A UDP socket sends nothing; the kernel just picks the route. `ipconfig
    getifaddr en0` guesses at the interface name and returns empty on a machine
    where the guess is wrong — silently dropping half the probe.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return str(sock.getsockname()[0])
    except OSError as exc:
        raise runtime.CellRuntimeError(
            f"the host's LAN address could not be determined ({exc}) — the probe "
            "would then cover only the gateway, which is not a probe that passed."
        ) from exc


def probe_addresses() -> list[str]:
    """What the probe covers: the cell's gateway and the host on its LAN."""
    return [runtime.GATEWAY, _lan_address()]


def _probe_script(addresses: list[str], ports: list[int]) -> str:
    return (
        "import socket,sys\n"
        f"addrs={addresses!r}\n"
        f"ports={ports!r}\n"
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

    Every port the host is listening on for anything but loopback, tried from
    inside a cell at the gateway and at the LAN address. An empty list is the
    passing result and means what it says: nothing the host had open answered.
    Anything else is a service a cell can reach, and the fix is on the host —
    bind it to 127.0.0.1, or stop it — never in the cell.
    """
    addresses = probe_addresses()
    done = runtime.run_ephemeral(
        image_tag,
        ["python", "-c", _probe_script(addresses, host_listening_ports())],
        network=network,
        timeout_s=300,
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
