"""The cell runtime — the only module that knows which one (DESIGN.md Appendix G).

`apple/container`, chosen in rev 10 against the four assertions in
`spikes/cell-runtime.sh`. The surface below is deliberately small: create a
network and a volume, run a container on it with limits, exec, inspect, destroy.
Nothing above this file changes if the answer changes.
"""

from __future__ import annotations

import ipaddress
import queue
import re
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

RUNTIME = "container"
DEFAULT_SUBNET = "10.88.0.0/24"

# §4.3's idle and completion bounds. Idle has to clear the longest single tool
# call an agent makes — a gate suite runs minutes and emits nothing until it
# returns — so it is the stall bound, not the impatience one. Completion is
# silence *after* the payload said it was done, which is a child process
# holding stdout open; a runner that is really finished exits at once.
IDLE_TIMEOUT_S = 300.0
COMPLETION_TIMEOUT_S = 10.0

# Derived, never re-typed: a second literal of the subnet is a probe that
# silently covers nothing the day the subnet moves.
_NETWORK = ipaddress.ip_network(DEFAULT_SUBNET)
SUBNET_PREFIX = str(_NETWORK.network_address).rsplit(".", 1)[0] + "."
GATEWAY = str(next(_NETWORK.hosts()))

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
    # Which of §4.3's time bounds ended this: "idle", "wall", "completion", or
    # "" for a process that ended on its own. They mean different things to the
    # caller, so one flag cannot carry them.
    bound: str = ""


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
            bound="wall",
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


# The `remove_*` calls never raise: they also pre-clean, where "does not exist"
# is the ordinary case. They return the outcome so a caller tearing down — where
# a failure is a leak, not an expectation — can say so.
def remove_network(name: str) -> Completed:
    return _call([RUNTIME, "network", "rm", name], timeout_s=60)


def create_volume(name: str) -> None:
    _must([RUNTIME, "volume", "create", name])


def remove_volume(name: str) -> Completed:
    return _call([RUNTIME, "volume", "rm", name], timeout_s=60)


def remove_container(name: str) -> Completed:
    return _call([RUNTIME, "rm", "-f", name], timeout_s=60)


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


# Everything but PID 1 and the reaper itself. Measured, not assumed: killing the
# `container exec` client leaves the process it started running inside the cell,
# so an idle or wall kill abandons an agent that goes on editing /work while the
# driver measures commits and runs gates. The cell is single-purpose and its
# turns are sequential, so "nothing from the last turn survives into the next"
# is the whole rule. Shell-only: the image is python:slim and has no procps.
_REAP = (
    "for p in /proc/[0-9]*; do pid=${p#/proc/}; "
    '[ "$pid" = 1 ] || [ "$pid" = "$$" ] || kill -9 "$pid" 2>/dev/null; done; :'
)


def reap_cell(container: str, timeout_s: float = 60) -> Completed:
    """Kill whatever the last turn left running inside the cell."""
    return _call([RUNTIME, "exec", container, "sh", "-c", _REAP], timeout_s)


def exec_stream(
    container: str,
    command: Sequence[str],
    *,
    stdin_data: str,
    on_line: Callable[[str], bool | None],
    workdir: str | None = None,
    timeout_s: float = 3600,
    idle_s: float = IDLE_TIMEOUT_S,
    completion_s: float = COMPLETION_TIMEOUT_S,
) -> Completed:
    """`exec_`, with stdin and with stdout delivered a line at a time.

    The agent session is minutes long and the operator watches it, so its
    output cannot be collected at exit the way a gate's is. The cell gains no
    capability it lacked: this is the same `exec`, with `-i` so the request
    reaches the process on stdin.

    Three of §4.3's five bounds live here because all three are properties of
    this one read loop. `on_line` returning true says the payload signalled it
    is done: silence before that is a stalled agent, silence after it is a
    child process holding stdout open. Once done is signalled the wall clock
    stops applying — there is no work left to bound, only a pipe.

    A reader thread and a queue, not `selectors`: readiness on the fd is not a
    line, so a half-written one would still block `readline` and the fix would
    be reimplementing line splitting over `os.read`.
    """
    argv = [RUNTIME, "exec", "-i"]
    if workdir:
        argv += ["--cwd", workdir]
    argv.append(container)
    argv += list(command)

    # stderr to a file, not a second pipe: nothing drains it while stdout is
    # being read, and a pipe that fills stops the process producing lines.
    with tempfile.TemporaryFile("w+") as errors:
        try:
            proc = subprocess.Popen(  # noqa: SIM115 — closed by the with-block below
                argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=errors,
                text=True,
            )
        except OSError as exc:
            raise CellRuntimeError(f"{RUNTIME} could not be executed: {exc}") from exc

        lines: queue.Queue[str | None] = queue.Queue()

        def _pump() -> None:
            assert proc.stdout
            for line in proc.stdout:
                lines.put(line.rstrip("\n"))
            lines.put(None)  # EOF, and the only clean end of the loop below

        reader = threading.Thread(target=_pump, daemon=True)
        # Names the bound the *current* wait is against; it survives the loop
        # only if that wait is the one that times out.
        bound = ""
        with proc:
            assert proc.stdin
            reader.start()
            try:
                proc.stdin.write(stdin_data)
                proc.stdin.close()
            except OSError:
                pass  # the process died early; its stderr says why
            wall = time.monotonic() + timeout_s
            # Fixed the moment the result event lands, never recomputed: a
            # window that restarts on every line is a child writing steadily
            # enough to hold the loop open forever, which is the unbounded
            # wait §4.3's five bounds exist to prevent.
            completion_until = 0.0
            signalled = False
            while True:
                now = time.monotonic()
                if signalled:
                    bound, until = "completion", completion_until
                elif wall - now <= idle_s:
                    bound, until = "wall", wall
                else:
                    bound, until = "idle", now + idle_s
                try:
                    line = lines.get(timeout=max(0.0, until - now))
                except queue.Empty:
                    proc.kill()
                    break
                if line is None:
                    bound = ""
                    break
                if not signalled and on_line(line):
                    signalled, completion_until = True, time.monotonic() + completion_s
            # Drain before the with-block closes stdout underneath the reader.
            # The kill above, or EOF, has already ended it.
            reader.join(timeout=5)
        errors.seek(0)
        return Completed(
            # A finished turn whose child held the pipe is a finished turn: the
            # exit status after our kill is ours, not the runner's (§4.3).
            returncode=(
                0 if bound == "completion" else 124 if bound else proc.returncode
            ),
            stdout="",
            stderr=errors.read(),
            timed_out=bound in ("idle", "wall"),
            bound=bound,
        )


_IPV4 = re.compile(r"\d{1,3}(?:\.\d{1,3}){3}")


def _first_address(inspected: str, subnet_prefix: str) -> str | None:
    """Pull the container's own address out of whatever `inspect` prints.

    ponytail: a regex over the JSON rather than a schema for it. The gateway is
    always `<prefix>1` and is the one address in range that is not the cell's.
    """
    for candidate in _IPV4.findall(inspected):
        # `.0` as well as `.1`: a subnet printed before the address field
        # (`10.88.0.0/24`) would otherwise be handed out as the cell's own,
        # and every proxied call would fail looking like an upstream outage.
        if candidate.startswith(subnet_prefix) and not candidate.endswith((".0", ".1")):
            return candidate
    return None


def container_ip(name: str, subnet_prefix: str = SUBNET_PREFIX) -> str | None:
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
