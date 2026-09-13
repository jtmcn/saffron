"""The cell runtime — every caller's whole view of it (DESIGN.md Appendix G).

This module holds the surface: create a network and a volume, run a container on
it with limits, exec, inspect, destroy. It names no runtime. Which one is
running is a `Dialect` (`saffron/cell/runtimes/`), selected below and reached
only for the handful of spellings that are not universal — so nothing here
changes if the answer changes, which is what Appendix G bought and what the
`structure` gate keeps.

`dialect()` is the selection — `apple` by default, `podman` when
`SAFFRON_CELL_RUNTIME` says so, and never a `shutil.which`: a runtime detected
from the host is the proper noun standing in for a decision all over again
(principle 32, backlog item 103).
"""

from __future__ import annotations

import ipaddress
import os
import queue
import re
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from saffron.cell.runtimes import Dialect
from saffron.cell.runtimes import apple as _apple
from saffron.cell.runtimes import podman as _podman


class CellRuntimeError(RuntimeError):
    """The runtime itself failed — not the thing running inside it."""


# The runtimes this build can drive, by the name an operator writes.
DIALECTS: dict[str, Dialect] = {"apple": _apple.DIALECT, "podman": _podman.DIALECT}
DEFAULT_DIALECT = "apple"
RUNTIME_ENV = "SAFFRON_CELL_RUNTIME"


def select_dialect(name: str | None) -> Dialect:
    """The named runtime, or the default when nothing was named.

    **Declared, never detected.** Choosing by what happens to be on
    `PATH` would make the runtime a property of the machine rather than a
    decision, which is Appendix G's principle 32 restaged with a `shutil.which`
    in place of the proper noun — and it would silently swap the safety argument
    with it, since the two runtimes do not offer the same boundary.

    An unknown name raises rather than falling back. A fallback here reports the
    default's calibration for a runtime nobody chose, and `CPU_OFFSET` being
    wrong by one surfaces as flaky gate timings rather than as an error (§5.1).
    """
    if name is None or not name.strip():
        return DIALECTS[DEFAULT_DIALECT]
    try:
        return DIALECTS[name.strip()]
    except KeyError:
        raise CellRuntimeError(
            f"{RUNTIME_ENV}={name!r} names no runtime this build can drive; "
            f"it knows {', '.join(sorted(DIALECTS))}"
        ) from None


_selected: Dialect | None = None


def dialect() -> Dialect:
    """The selected runtime, chosen on first use and fixed for the process.

    Fixed because a task that created its network with one runtime and its
    container with another is not a thing to make reachable. On first use and
    not at import, because `saffron.cli` imports this module: an unknown name
    raised at import exits 1 with a traceback before `main` can map it to 2.
    """
    global _selected
    if _selected is None:
        _selected = select_dialect(os.environ.get(RUNTIME_ENV))
    return _selected


# `RUNTIME` and `CPU_OFFSET` stay module attributes for callers outside this
# package — `proxy.py` reads the proxy's log, `image.py` builds with the binary —
# but resolve through `dialect()` so that reading one is a use, not an import.
if TYPE_CHECKING:
    RUNTIME: str
    CPU_OFFSET: int


def __getattr__(name: str) -> object:
    if name == "RUNTIME":
        return dialect().binary
    if name == "CPU_OFFSET":
        return dialect().cpu_offset
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


_admitted = False


def _admit() -> None:
    """Refuse a host the selected runtime cannot safely run cells on.

    Once per process, ahead of the first network or container, so no path
    starts one without passing it — `saffron cell`, a batch, and preflight's own
    probes alike.
    """
    global _admitted
    if _admitted:
        return
    refusal = dialect().host_refusal(call)
    if refusal is not None:
        raise CellRuntimeError(refusal)
    _admitted = True


def unattended_refusal() -> str | None:
    """Why a night must not run on the selected runtime, or None."""
    selected = dialect()
    if selected.unattended:
        return None
    return (
        f"{RUNTIME_ENV} selects {selected.binary}, which has not yet started a "
        "cell end to end; run it attended with `saffron cell` (backlog item 103)"
    )


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
    argv = [dialect().binary, "run"]
    argv += ["-d"] if detach else ["--rm"]
    # No capabilities. §5.1: a cell that could install firewall rules could
    # rewrite its own, which is why egress is a proxy and not iptables.
    argv += ["--cap-drop", "ALL"]
    # Whatever in-guest hardening this runtime has to offer. Empty under a
    # VM-per-cell runtime, which offers the kernel instead (§5.1).
    argv += dialect().security_flags
    if user:
        argv += ["--user", user]
    if name:
        argv += ["--name", name]
    # The proxy is dual-homed (cells network + egress network); a cell is not.
    for net in [network] if isinstance(network, str) else network or ():
        argv += ["--network", net]
    if cpus is not None:
        argv += dialect().cpu_flags(cpus)
    if memory:
        argv += ["--memory", memory]
    for mount in mounts:
        argv += ["--mount", mount.to_flag()]
    for key, value in (env or {}).items():
        argv += ["-e", f"{key}={value}"]
    argv.append(image)
    argv += list(command)
    return argv


def _decode(data: bytes | None) -> str:
    # errors="replace" so a cell emitting invalid UTF-8 cannot raise out of
    # this function — a broken byte becomes U+FFFD, never an exception.
    return "" if data is None else data.decode("utf-8", errors="replace")


def _call(argv: Sequence[str], timeout_s: float) -> Completed:
    # Bytes, not text=True: Python's universal-newline translation silently
    # rewrites a bare "\r" a cell emits (e.g. inside a diff) into "\n" before
    # any caller sees it, and a gate reading that diff must see what git
    # actually wrote.
    try:
        proc = subprocess.run(list(argv), capture_output=True, timeout=timeout_s)
    except subprocess.TimeoutExpired as exc:
        return Completed(
            returncode=124,
            stdout=_decode(exc.stdout),
            stderr=_decode(exc.stderr),
            timed_out=True,
            bound="wall",
        )
    except OSError as exc:
        raise CellRuntimeError(
            f"{dialect().binary} could not be executed: {exc}"
        ) from exc
    return Completed(proc.returncode, _decode(proc.stdout), _decode(proc.stderr))


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
    _admit()
    argv = [
        dialect().binary,
        "network",
        "create",
        "--internal",
        "--subnet",
        subnet,
        name,
    ]
    done = _call(argv, 120)
    if done.returncode == 0:
        return
    # The runtime names the subnet and not the network holding it, and the
    # holder is what has to go. A SIGKILLed run leaves one behind under a name
    # the next create does not pre-clean, because it is a different name.
    detail = done.stderr.strip()
    if "overlap" in detail:
        holders = networks_on_subnet(subnet, exclude=name)
        if holders:
            detail += f" — held by {', '.join(holders)}"
    raise CellRuntimeError(f"{' '.join(argv)} failed: {detail}")


def networks_on_subnet(subnet: str, exclude: str = "") -> list[str]:
    """Networks whose subnet overlaps this one, by name.

    Overlap and not equality, because that is the failure being explained: the
    runtime rejects `10.89.0.128/25` against a holder on `10.89.0.0/24` with the
    same wording, and an equality test names nobody in exactly the case an
    operator cannot work out by eye. Empty when the listing itself fails — this
    only ever adds detail to an error already being raised."""
    done = _call([dialect().binary, "network", "list"], 60)
    if done.returncode != 0:
        return []
    try:
        wanted = ipaddress.ip_network(subnet)
    except ValueError:
        return []
    found = []
    for line in done.stdout.splitlines():
        fields = line.split()
        if len(fields) < 2 or fields[0] == exclude:
            continue
        try:
            if ipaddress.ip_network(fields[1]).overlaps(wanted):
                found.append(fields[0])
        except ValueError:
            continue  # the header row, and anything else that is not a subnet
    return found


def remove_network(name: str) -> Completed:
    return _call([dialect().binary, "network", "rm", name], timeout_s=60)


def create_volume(name: str) -> None:
    _admit()
    _must([dialect().binary, "volume", "create", name])


def remove_volume(name: str) -> Completed:
    return _call([dialect().binary, "volume", "rm", name], timeout_s=60)


def remove_container(name: str) -> Completed:
    return _call([dialect().binary, "rm", "-f", name], timeout_s=60)


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
    _admit()
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
    _admit()
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


def exec_argv(
    container: str,
    command: Sequence[str],
    *,
    workdir: str | None = None,
    interactive: bool = False,
) -> list[str]:
    """One spelling of `exec`, for both callers.

    Built here rather than twice because the working-directory flag is the
    dialect's to name and a second copy is a second thing to miss: the streaming
    path and the collecting path disagreeing about where a command runs is a
    cell that works and works in the wrong directory.
    """
    argv = [dialect().binary, "exec"]
    if interactive:
        argv.append("-i")
    if workdir:
        argv += [dialect().exec_workdir_flag, workdir]
    argv.append(container)
    return argv + list(command)


def exec_(
    container: str,
    command: Sequence[str],
    *,
    workdir: str | None = None,
    timeout_s: float = 900,
) -> Completed:
    return _call(exec_argv(container, command, workdir=workdir), timeout_s)


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
    return _call([dialect().binary, "exec", container, "sh", "-c", _REAP], timeout_s)


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
    argv = exec_argv(container, command, workdir=workdir, interactive=True)

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
            raise CellRuntimeError(
                f"{dialect().binary} could not be executed: {exc}"
            ) from exc

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
    done = _call([dialect().binary, "inspect", name], timeout_s=60)
    if done.returncode != 0:
        return None
    return _first_address(done.stdout, subnet_prefix)


def visible_cpus(image: str, cpus: int) -> int:
    """What `nproc` reports inside a cell allocated `cpus`. See CPU_OFFSET."""
    done = run_ephemeral(image, ["nproc"], cpus=cpus, timeout_s=120)
    if done.returncode != 0:
        raise CellRuntimeError(f"nproc failed in {image}: {done.stderr.strip()}")
    return int(done.stdout.strip().splitlines()[-1])
