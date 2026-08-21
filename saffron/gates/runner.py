"""Host-invoked gate execution.

The agent never runs the gates and never reports its own gate status — it only
ever receives gate output as input (DESIGN.md §5.4). In v0 there is no agent at
all, and this module is what proves the contract survives real tool output.
"""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from saffron.cell import runtime as cell_runtime
from saffron.cell.worktree import WORKTREE_MOUNT
from saffron.gates.contract import GateResult, parse_gate_json

_STDERR_TAIL = 800

# Saffron's own `uv run` activation, un-declared: a gate resolving its toolchain
# through VIRTUAL_ENV/PATH would find Saffron's interpreter, not the repo's.
_LEAKED = ("VIRTUAL_ENV", "PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP")


def _gate_env() -> dict[str, str]:
    """A gate inherits the operator's environment, never Saffron's own runtime."""
    env = {k: v for k, v in os.environ.items() if k not in _LEAKED}
    if sys.prefix != sys.base_prefix:  # Saffron is running in a venv
        bin_dir = str(Path(sys.prefix) / "bin")
        env["PATH"] = os.pathsep.join(
            p for p in env.get("PATH", "").split(os.pathsep) if p != bin_dir
        )
    return env


class GateExecutor(Protocol):
    """How a gate's process is started. The only thing that differs between
    running gates on the host (v0's replay) and inside a cell (v0.5)."""

    def run(
        self, argv: Sequence[str], cwd: Path, timeout_s: float
    ) -> cell_runtime.Completed: ...


class LocalExecutor:
    """Run the gate as a host subprocess, in its own process group."""

    def run(
        self, argv: Sequence[str], cwd: Path, timeout_s: float
    ) -> cell_runtime.Completed:
        # start_new_session: the gate gets its own process group, so a timeout
        # can kill the tool the script launched. subprocess's own timeout kill
        # reaches only the shell, leaving pytest and its workers running
        # inside a worktree the caller is about to remove.
        try:
            with subprocess.Popen(
                list(argv),
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
                env=_gate_env(),
            ) as proc:
                try:
                    stdout, stderr = proc.communicate(timeout=timeout_s)
                except subprocess.TimeoutExpired:
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(proc.pid, signal.SIGKILL)
                    proc.communicate()
                    return cell_runtime.Completed(124, "", "", timed_out=True)
        except OSError as exc:
            raise GateNotExecutable(str(exc)) from exc
        return cell_runtime.Completed(proc.returncode, stdout, stderr)


class CellExecutor:
    """Run the gate inside a cell. Host-invoked, exactly as on the host —
    the agent never starts a gate and never sees its status (§5.4)."""

    def __init__(self, container: str, workdir: str = WORKTREE_MOUNT):
        self.container = container
        self.workdir = workdir

    def run(
        self, argv: Sequence[str], cwd: Path, timeout_s: float
    ) -> cell_runtime.Completed:
        # cwd is a host path (the caller's worktree) and does not exist inside
        # the cell; the caller is responsible for passing cell-side argv paths.
        return cell_runtime.exec_(
            self.container, list(argv), workdir=self.workdir, timeout_s=timeout_s
        )


class GateNotExecutable(Exception):
    """The gate binary could not be started at all."""


def run_gate(
    name: str,
    executable: Path,
    cwd: Path,
    *,
    timeout_s: float = 900,
    subset: list[str] | None = None,
    executor: GateExecutor | None = None,
) -> GateResult:
    """Run one gate and return its result.

    A gate whose stdout parses as the contract is believed whatever its exit
    code — a failing linter exits nonzero and is still reporting `fail`, not
    breaking. Anything else is `error`: the gate itself broke, which never
    counts as a task failure (DESIGN.md §5.4).

    `skip` is the deliberate exemption from the error rules below — it names no
    tool and carries no failures because it did not run, and it must exit 0. A
    gate that used `skip` as its own failure path would read here as passing.
    """
    executor = executor or LocalExecutor()
    argv = [str(executable), *(subset or [])]
    started = time.monotonic()

    try:
        done = executor.run(argv, cwd, timeout_s)
    except GateNotExecutable as exc:
        return _error(name, f"gate could not be executed: {exc}", started)

    if done.timed_out:
        return _error(name, f"gate timed out after {timeout_s}s", started)

    try:
        result = parse_gate_json(done.stdout, expected_gate=name)
    except Exception as exc:
        detail = (done.stderr or done.stdout or "").strip()[-_STDERR_TAIL:]
        return _error(
            name, f"gate emitted no usable contract ({exc}): {detail}", started
        )

    # Three ways a gate reports a result it did not produce. All are `error`:
    # the gate itself broke, which is never charged to the task (§5.4).
    if result.status in ("pass", "fail") and not result.tool:
        return _error(
            name,
            "gate reported a result without naming its tool — cannot tell "
            "'ran and passed' from 'did not run'",
            started,
        )
    if done.returncode != 0 and not result.failures:
        return _error(
            name,
            f"gate exited {done.returncode} but parsed no failures — its "
            "output shape probably changed",
            started,
        )

    result.duration_ms = _elapsed_ms(started)
    return result


def run_suite(
    gates: dict[str, Path],
    cwd: Path,
    *,
    timeout_s: float = 900,
    executor: GateExecutor | None = None,
) -> list[GateResult]:
    """Run every declared gate in declaration order."""
    return [
        run_gate(name, executable, cwd, timeout_s=timeout_s, executor=executor)
        for name, executable in gates.items()
    ]


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _error(gate: str, summary: str, started: float) -> GateResult:
    return GateResult(
        gate=gate, status="error", summary=summary, duration_ms=_elapsed_ms(started)
    )
