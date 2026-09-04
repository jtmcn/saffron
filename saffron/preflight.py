"""Per-run readiness: two in-cell probes, neither of which trusts a component
that reported success, plus the ordered host-side checks §4.2.1 adds on top.

N1 rests on the first. The second rests on the fact that a proxy which started
is not a proxy which works — one that came up with no route out cost a whole
attempt before anything noticed (DESIGN.md §5.1.1).

An `--internal` network still routes to the host gateway, so a host service
bound to 0.0.0.0 — a Postgres, a dev server — is reachable from inside a cell
without ever traversing the proxy. Measured, not assumed (Appendix G).

A named host process can be tolerated per invocation — an accepted risk, not a
fix, and reported on every run so it cannot go quiet (Appendix G).

`check_readiness` is the third thing here: "preflight is what a task already
does, hoisted, plus two" (§4.2.1) — auth, mirror fetch, origin refusal,
default-branch pin, policy validation, disk headroom, in that order, stopping
at the first failure and naming it. `saffron cell` calls `prepare_mirror`
alone, never `check_readiness` — the auth-validity probe and the disk check
are reached through the readiness entry point, whose first caller is a batch
loop (`SA-0050`), not the attended path.
"""

from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from saffron.cell import proxy, runtime
from saffron.phases import package as package_phase
from saffron.repos import mirror as git_mirror
from saffron.repos.policy import PolicyError, load_policy

_LSOF = ("lsof", "-nP", "-iTCP", "-sTCP:LISTEN")

# Everything else a listener can be bound to is reachable from a cell, at the
# gateway or at the LAN address.
_LOOPBACK = ("127.", "[::1]", "localhost")


# A host listener the operator has decided to accept, named by the COMMAND lsof
# reports, comma-separated. Empty by default: an unnamed listener still fails.
_ALLOW_ENV = "SAFFRON_ALLOW_HOST_PROCESS"


def tolerated_processes() -> frozenset[str]:
    """Host processes this invocation accepts. Read per call, never a constant.

    An environment variable rather than a flag because the probe has two
    entrypoints — `saffron cell` and the `-m cell` suite — and one relaxation
    should not need two knobs. What keeps it from going quiet in a shell
    profile is that every run reports what it tolerated (Appendix G).
    """
    named = os.environ.get(_ALLOW_ENV, "").split(",")
    return frozenset(name.strip() for name in named if name.strip())


def listening_sockets(lsof_output: str) -> list[tuple[str, int]]:
    """`(command, port)` per non-loopback TCP listener, from `lsof -nP -iTCP
    -sTCP:LISTEN`.

    The NAME column is the last field before `(LISTEN)`: `*:8000`,
    `0.0.0.0:5432`, `[::]:631`, `127.0.0.1:6379`. COMMAND can hold spaces, so
    the row is read from the right and COMMAND is whatever sits left of the PID.
    """
    found = set()
    for line in lsof_output.splitlines():
        fields = line.split()
        if len(fields) < 3 or fields[-1] != "(LISTEN)":
            continue
        address, _, port = fields[-2].rpartition(":")
        if not port.isdigit() or address.startswith(_LOOPBACK):
            continue
        pid = next((i for i, field in enumerate(fields) if field.isdigit()), 1)
        found.add((" ".join(fields[:pid]), int(port)))
    return sorted(found, key=lambda listener: (listener[1], listener[0]))


def probed_ports(
    sockets: list[tuple[str, int]], tolerated: frozenset[str]
) -> tuple[list[int], list[str]]:
    """The ports the probe covers, and the tolerated listeners left out of them.

    A port drops out only when *every* listener on it is a tolerated process:
    a second process sharing the port is not tolerated by association. The
    exception follows the name, not the number — rapportd's ports are dynamic,
    so a port allowlist would be wrong the next time it restarts.
    """
    by_port: dict[int, set[str]] = {}
    for command, port in sockets:
        by_port.setdefault(port, set()).add(command)
    ports = sorted(port for port, cmds in by_port.items() if not cmds <= tolerated)
    return ports, [f"{c}:{p}" for c, p in sockets if p not in ports]


def host_probe_ports() -> tuple[list[int], list[str]]:
    """What the probe covers, enumerated rather than guessed — and what it does
    not cover because the operator named it.

    Seven remembered ports is a spot-check whose result reads as a proof: the
    v0.5 run that found a service on 8000 had four more on 8001+ that no list
    would have named (Appendix L). Enumeration failing must never narrow the
    probe to nothing, so anything short of lsof's own header — a missing lsof,
    a permission problem, silence — raises, tolerance named or not. An empty
    *result* is different and is a real pass: lsof reported, and every listener
    was loopback-bound or accepted.
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
    return probed_ports(listening_sockets(done.stdout), tolerated_processes())


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
        "import socket\n"
        "from concurrent.futures import ThreadPoolExecutor\n"
        f"addrs={addresses!r}\n"
        f"ports={ports!r}\n"
        "def probe(t):\n"
        "    a,p=t\n"
        "    s=socket.socket(); s.settimeout(1.5)\n"
        "    try:\n"
        "        s.connect((a,p)); return f'{a}:{p}'\n"
        "    except OSError: return None\n"
        "    finally: s.close()\n"
        "targets=[(a,p) for a in addrs for p in ports]\n"
        "with ThreadPoolExecutor(max_workers=32) as ex:\n"
        "    hit=[h for h in ex.map(probe, targets) if h]\n"
        "print('|'.join(hit))\n"
    )


def probe_host_bindings(
    image_tag: str, network: str, ports: list[int] | None = None
) -> list[str]:
    """Addresses at which a host service answered from inside a cell.

    Every port the host is listening on for anything but loopback and not held
    solely by a tolerated process, tried from inside a cell at the gateway and
    at the LAN address. An empty list is the passing result and means what it
    says: nothing the host had open, and was not accepted, answered.
    Anything else is a service a cell can reach, and the fix is on the host —
    bind it to 127.0.0.1, or stop it — never in the cell.
    """
    addresses = probe_addresses()
    if ports is None:
        ports = host_probe_ports()[0]
    done = runtime.run_ephemeral(
        image_tag,
        ["python", "-c", _probe_script(addresses, ports)],
        network=network,
        timeout_s=300,
    )
    if done.returncode != 0:
        raise runtime.CellRuntimeError(
            f"the host-binding probe did not run: {done.stderr.strip()}. "
            "A probe that did not run is not a probe that passed."
        )
    return [hit for hit in done.stdout.strip().split("|") if hit]


def assert_host_is_unreachable(
    image_tag: str, network: str, ports: list[int] | None = None
) -> None:
    reachable = probe_host_bindings(image_tag, network, ports)
    if reachable:
        raise runtime.CellRuntimeError(
            "host services answered from inside a cell at "
            + ", ".join(reachable)
            + " — bind them to 127.0.0.1. N1 is not satisfied until this is empty."
        )


# The agent's own first request, made before the agent exists. `HTTPError` is
# caught and its code printed because 401 is the expected answer and is a pass:
# the route is what is being established, not a credential.
_UPSTREAM_PROBE = (
    "import urllib.request as u\n"
    "try:\n"
    "    print('STATUS', u.urlopen({url!r}, timeout=20).status)\n"
    "except u.HTTPError as e:\n"
    "    print('STATUS', e.code)\n"
)


# Anchored, never a substring: `STATUS` is a literal inside the argv this sends,
# so a runtime echoing its own command back — a usage dump on a flag it stopped
# accepting, which 1.2.2 -> 1.3.0 already did once here — would read as a pass.
# That is Appendix H's vacuous pass, inside the check written against it.
_STATUS = re.compile(r"^STATUS (\d{3})$", re.M)


def assert_proxy_reaches_upstream(
    image_tag: str, network: str, proxy_ip: str, timeout_s: float = 120
) -> str:
    """The path, not the parts: through the proxy to the host the allowlist
    names, from a sibling on the cells network (DESIGN.md §5.1.1). Returns the
    status that answered, so the operator's line says what replied and not
    merely that something did.

    A failure is `error` and not `fail`: it aborts before a cell exists and is
    charged to nobody."""
    url = f"https://{proxy.UPSTREAM_HOST}/v1/models"
    done = runtime.run_ephemeral(
        image_tag,
        ["python", "-c", _UPSTREAM_PROBE.format(url=url)],
        network=network,
        env=proxy.proxy_env(proxy_ip),
        timeout_s=timeout_s,
    )
    if answered := _STATUS.search(done.stdout):
        return answered.group(1)
    # A probe that did not run is not a probe that failed, and the two want
    # different fixes. A python traceback is the evidence that it ran at all.
    if done.timed_out or "Traceback" not in done.stderr:
        raise runtime.CellRuntimeError(
            f"the upstream probe did not run ({'timed out' if done.timed_out else 'no output from the probe'}): "
            f"{_last_line(done)}. A probe that did not run is not a probe that passed."
        )
    raise runtime.CellRuntimeError(
        f"the proxy at {proxy_ip} could not reach {proxy.UPSTREAM_HOST}: "
        f"{_last_line(done)}. The cell would meet this as an API error a whole "
        "attempt later — check the proxy's own route out, and the allowlist if "
        "the line above says the tunnel was refused."
    )


def _last_line(done: runtime.Completed) -> str:
    """The exception, not the runtime's throat-clearing.

    Measured: `container run` prints its own image-pull progress to stderr
    ahead of anything the container says, and a traceback's useful line is its
    last — so the front of this stream is noise and a head-truncated message
    reports the pull instead of the diagnosis. stderr before stdout is a
    decision, not an accident: this only runs on the abort path, where the
    exception is what the operator needs."""
    for stream in (done.stderr, done.stdout):
        for line in reversed(stream.splitlines()):
            if line.strip():
                return line.strip()
    return "the probe printed nothing"


# The agent's own credential, checked against the same host `assert_proxy_
# reaches_upstream` probes. `Authorization: Bearer` is how the agent itself
# presents this token once a cell starts (session.py forwards it verbatim).
_TOKEN_PROBE_URL = f"https://{proxy.UPSTREAM_HOST}/v1/models"


def validate_claude_token(token: str, *, timeout_s: float = 20) -> bool:
    """`True` if `token` authenticates against the host the proxy allowlists;
    `False` for anything else, including a host this probe could not reach —
    "could not tell" is not a pass.

    This is the *opposite* verdict from `assert_proxy_reaches_upstream` on
    the very same host: that probe treats a 401 as success, because what it
    establishes is the route, not the credential — "the route is what is
    being established, not a credential" (its own docstring). This probe
    exists precisely because Appendix J found the other side of that coin: a
    cell whose token the route accepts a connection for, and answers 401 to,
    never says so — it returns `subtype: "success"`, `is_error: true`,
    `total_cost_usd: 0.0`, and an expired token at 22:00 buys a night of
    clean-looking nothing. A 401 or 403 here is exactly the failure this
    function exists to catch, not the pass it is one door over.
    """
    request = urllib.request.Request(
        _TOKEN_PROBE_URL, headers={"Authorization": f"Bearer {token}"}
    )
    try:
        urllib.request.urlopen(request, timeout=timeout_s)
        return True
    except urllib.error.HTTPError as exc:
        return exc.code not in (401, 403)
    except urllib.error.URLError:
        return False


# 10 GiB: room for a night's mirrors, worktrees and agent-state volumes for
# K concurrent cells plus one cell-image pull, with slack left over for
# whatever else the same disk is holding. Chosen against §4.5's endgame —
# "two weeks and the disk is full" — not against comfort: `saffron gc`
# reclaims the leak; this only refuses to run blind past it while gc is
# deferred (§4.2.1).
_MIN_FREE_BYTES = 10 * 1024**3


def disk_headroom_ok(path: Path, *, min_free_bytes: int = _MIN_FREE_BYTES) -> bool:
    """Free space on the filesystem holding `path` — the batch tree
    (`--home`), which is where mirrors, worktrees, and the cell runtime's own
    volumes actually accumulate, not `/` and not the checkout being tasked.

    Raises rather than reading as a pass it cannot back up: a headroom check
    that could not run is not a headroom check that passed —
    `host_probe_ports` draws the identical line for a missing `lsof`.
    """
    try:
        usage = shutil.disk_usage(path)
    except OSError as exc:
        raise RuntimeError(
            f"disk headroom at {path} could not be checked ({exc})"
        ) from exc
    return usage.free >= min_free_bytes


def prepare_mirror(repo: Path, mirror_path: Path) -> tuple[Path, str, str]:
    """`ensure_mirror`, the non-forge origin refusal, and the default-branch
    pin — the three per-task reads `_run_cell` already paid for (§4.2.1),
    factored out so `check_readiness` can run them once per run while
    `saffron cell` keeps paying them once per task, in exactly the order and
    with exactly the failure modes it always has: raises, and does not
    recover.
    """
    mirror = git_mirror.ensure_mirror(repo, mirror_path)
    url = package_phase.real_remote(repo)
    # Read for its refusal, not its value: `package` needs the slug and only
    # reaches it after the budget is spent, so a non-GitHub origin fails here
    # for the same reason an unreachable one does (§5.1).
    package_phase.github_slug(url)
    # The remote's default-branch head, not the invoking checkout's: a task's
    # base must not depend on where the operator was standing (§5.7).
    _, base_sha = package_phase.fetch_default_branch(mirror, url)
    return mirror, url, base_sha


@dataclass(frozen=True)
class Readiness:
    """One run's readiness — never a bare boolean, so a caller can skip the
    repo and say why (§4.4 step 1) instead of discovering the reason by
    reading a traceback the first cell raised."""

    ok: bool
    step: str | None = None
    detail: str | None = None
    mirror: Path | None = None
    url: str | None = None
    base_sha: str | None = None


def check_readiness(
    repo: Path,
    mirror_path: Path,
    scratch: Path,
    home: Path,
    *,
    token: str | None,
    validate_token: Callable[[str], bool] = validate_claude_token,
) -> Readiness:
    """§4.2.1, followed to the letter: auth, mirror fetch, origin refusal,
    default-branch pin, policy validation, disk headroom — in that order,
    stopping at the first failure and naming it.

    Not called by `saffron cell` (`_run_cell` calls `prepare_mirror` alone):
    this is the once-per-run entry point a batch loop calls (`SA-0050`), and
    it is the only path that reaches the network-bound `validate_token` probe
    or touches the disk at all.
    """
    stripped_token = (token or "").strip()
    if not stripped_token:
        return Readiness(False, "auth", "CLAUDE_CODE_OAUTH_TOKEN is unset")
    if not validate_token(stripped_token):
        return Readiness(
            False, "auth", "CLAUDE_CODE_OAUTH_TOKEN is present but not valid"
        )

    try:
        mirror = git_mirror.ensure_mirror(repo, mirror_path)
    except git_mirror.GitError as exc:
        return Readiness(False, "mirror", str(exc))

    try:
        url = package_phase.real_remote(repo)
        package_phase.github_slug(url)
    except package_phase.PackageError as exc:
        return Readiness(False, "origin", str(exc))

    try:
        _, base_sha = package_phase.fetch_default_branch(mirror, url)
    except package_phase.PackageError as exc:
        return Readiness(False, "default_branch", str(exc))

    # Best-effort about a repo with no `.saffron/` at this `base_sha` at all —
    # the same absence-is-not-unreadability distinction `cli._protected_paths`
    # and `cli._protected_paths_at` already draw. A policy that is *present*
    # and broken is a different fact and fails readiness (§4.2.1's "plus
    # two"'s other half).
    try:
        exported = git_mirror.export_saffron_dir(mirror, base_sha, scratch)
    except git_mirror.GitError:
        exported = None
    if exported is not None and (exported / ".saffron" / "policy.yaml").is_file():
        try:
            load_policy(exported)
        except PolicyError as exc:
            return Readiness(False, "policy", str(exc))

    # `disk_headroom_ok` raises rather than reading an unrunnable check as a
    # pass, which is right and is not this function's contract: §4.4 step 1
    # skips a repo that fails preflight rather than taking the batch down, so
    # every failure here arrives as a named `Readiness`, never as an exception
    # a caller must know to catch.
    try:
        headroom = disk_headroom_ok(home)
    except RuntimeError as exc:
        return Readiness(False, "disk", str(exc))
    if not headroom:
        return Readiness(
            False,
            "disk",
            f"fewer than {_MIN_FREE_BYTES / 1024**3:g}GiB free on {home}",
        )

    return Readiness(True, mirror=mirror, url=url, base_sha=base_sha)
