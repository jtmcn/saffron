"""The cell runtime — the only module that knows which one (DESIGN.md Appendix G).

`apple/container`, chosen in rev 10 against the four assertions in
`spikes/cell-runtime.sh`. The surface below is deliberately small: create a
network and a volume, run a container on it with limits, exec, inspect, destroy.
Nothing above this file changes if the answer changes.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

RUNTIME = "container"
DEFAULT_SUBNET = "10.88.0.0/24"

# apple/container 1.2.2 allocates one vCPU more than --cpus requests, measured
# at 1->2, 2->3, 4->5, 6->7. The guest count is honest about the VM it is in;
# the VM just gets one more than asked for. Assert it, never assume it — and
# re-measure with the spike on any runtime upgrade (DESIGN.md §5.1).
CPU_OFFSET = 1


class CellRuntimeError(RuntimeError):
    """The runtime itself failed — not the thing running inside it."""


@dataclass(frozen=True)
class Completed:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


@dataclass(frozen=True)
class Mount:
    kind: str
    source: str
    target: str
    readonly: bool = False

    def to_flag(self) -> str:
        flag = f"type={self.kind},source={self.source},target={self.target}"
        return f"{flag},readonly" if self.readonly else flag


def _run_argv(
    *,
    image: str,
    command: Sequence[str],
    name: str | None,
    network: str | Sequence[str] | None,
    env: Mapping[str, str] | None,
    cpus: int | None,
    memory: str | None,
    mounts: Sequence[Mount],
    detach: bool,
    user: str | None = None,
) -> list[str]:
    argv = [RUNTIME, "run"]
    argv += ["-d"] if detach else ["--rm"]
    # No capabilities. §5.1: a cell that could install firewall rules could
    # rewrite its own, which is why egress is a proxy and not iptables.
    argv += ["--cap-drop", "ALL"]
    if user:
        argv += ["--user", user]
    if name:
        argv += ["--name", name]
    # The proxy is dual-homed (cells network + egress network); a cell is not.
    for net in [network] if isinstance(network, str) else network or ():
        argv += ["--network", net]
    if cpus is not None:
        argv += ["--cpus", str(cpus)]
    if memory:
        argv += ["--memory", memory]
    for mount in mounts:
        argv += ["--mount", mount.to_flag()]
    for key, value in (env or {}).items():
        argv += ["-e", f"{key}={value}"]
    argv.append(image)
    argv += list(command)
    return argv


def _call(argv: Sequence[str], timeout_s: float) -> Completed:
    try:
        proc = subprocess.run(
            list(argv), capture_output=True, text=True, timeout=timeout_s
        )
    except subprocess.TimeoutExpired as exc:
        return Completed(
            returncode=124,
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
            timed_out=True,
        )
    except OSError as exc:
        raise CellRuntimeError(f"{RUNTIME} could not be executed: {exc}") from exc
    return Completed(proc.returncode, proc.stdout, proc.stderr)


def call(argv: Sequence[str], timeout_s: float = 120) -> Completed:
    """Run one runtime command and return its outcome without raising.

    The public form of `_call`, for callers outside this package that need to
    inspect a failure rather than have it raised at them.
    """
    return _call(argv, timeout_s)


def _must(argv: Sequence[str], timeout_s: float = 120) -> Completed:
    done = _call(argv, timeout_s)
    if done.returncode != 0:
        raise CellRuntimeError(f"{' '.join(argv)} failed: {done.stderr.strip()}")
    return done


def create_network(name: str, subnet: str = DEFAULT_SUBNET) -> None:
    _must([RUNTIME, "network", "create", "--internal", "--subnet", subnet, name])


def remove_network(name: str) -> None:
    _call([RUNTIME, "network", "rm", name], timeout_s=60)


def create_volume(name: str) -> None:
    _must([RUNTIME, "volume", "create", name])


def remove_volume(name: str) -> None:
    _call([RUNTIME, "volume", "rm", name], timeout_s=60)


def remove_container(name: str) -> None:
    _call([RUNTIME, "rm", "-f", name], timeout_s=60)


def run_detached(
    name: str,
    image: str,
    *,
    command: Sequence[str] = (),
    network: str | Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
    cpus: int | None = None,
    memory: str | None = None,
    mounts: Sequence[Mount] = (),
    user: str | None = None,
) -> None:
    _must(
        _run_argv(
            image=image,
            command=command,
            name=name,
            network=network,
            env=env,
            cpus=cpus,
            memory=memory,
            mounts=mounts,
            detach=True,
            user=user,
        ),
        timeout_s=300,
    )


def run_ephemeral(
    image: str,
    command: Sequence[str],
    *,
    network: str | None = None,
    env: Mapping[str, str] | None = None,
    cpus: int | None = None,
    memory: str | None = None,
    mounts: Sequence[Mount] = (),
    timeout_s: float = 120,
) -> Completed:
    return _call(
        _run_argv(
            image=image,
            command=command,
            name=None,
            network=network,
            env=env,
            cpus=cpus,
            memory=memory,
            mounts=mounts,
            detach=False,
        ),
        timeout_s,
    )


def exec_(
    container: str,
    command: Sequence[str],
    *,
    workdir: str | None = None,
    timeout_s: float = 900,
) -> Completed:
    argv = [RUNTIME, "exec"]
    if workdir:
        argv += ["--cwd", workdir]
    argv.append(container)
    argv += list(command)
    return _call(argv, timeout_s)


_IPV4 = re.compile(r"\d{1,3}(?:\.\d{1,3}){3}")


def _first_address(inspected: str, subnet_prefix: str) -> str | None:
    """Pull the container's own address out of whatever `inspect` prints.

    ponytail: a regex over the JSON rather than a schema for it. The gateway is
    always `<prefix>1` and is the one address in range that is not the cell's.
    """
    for candidate in _IPV4.findall(inspected):
        if candidate.startswith(subnet_prefix) and not candidate.endswith(".1"):
            return candidate
    return None


def container_ip(name: str, subnet_prefix: str = "10.88.0.") -> str | None:
    done = _call([RUNTIME, "inspect", name], timeout_s=60)
    if done.returncode != 0:
        return None
    return _first_address(done.stdout, subnet_prefix)


def visible_cpus(image: str, cpus: int) -> int:
    """What `nproc` reports inside a cell allocated `cpus`. See CPU_OFFSET."""
    done = run_ephemeral(image, ["nproc"], cpus=cpus, timeout_s=120)
    if done.returncode != 0:
        raise CellRuntimeError(f"nproc failed in {image}: {done.stderr.strip()}")
    return int(done.stdout.strip().splitlines()[-1])
