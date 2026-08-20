"""Host-invoked gate execution.

The agent never runs the gates and never reports its own gate status — it only
ever receives gate output as input (DESIGN.md §5.4). In v0 there is no agent at
all, and this module is what proves the contract survives real tool output.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from saffron.gates.contract import GateResult, parse_gate_json

_STDERR_TAIL = 800

# Saffron runs under `uv run`, which exports VIRTUAL_ENV and puts its own
# .venv/bin first on PATH. A gate resolving its toolchain (`poetry env info`,
# a bare `python`) then finds Saffron's interpreter, where the repo's tools do
# not exist — and a gate script that swallows "command not found" reports a
# false `pass`. Language-agnostic: core un-declares its own activation, it does
# not know what the gate will do with the environment.
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


def run_gate(
    name: str,
    executable: Path,
    cwd: Path,
    *,
    timeout_s: float = 900,
    subset: list[str] | None = None,
) -> GateResult:
    """Run one gate and return its result.

    A gate whose stdout parses as the contract is believed whatever its exit
    code — a failing linter exits nonzero and is still reporting `fail`, not
    breaking. Anything else is `error`: the gate itself broke, which never
    counts as a task failure (DESIGN.md §5.4).
    """
    argv = [str(executable), *(subset or [])]
    started = time.monotonic()

    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
            env=_gate_env(),
        )
    except subprocess.TimeoutExpired:
        return _error(name, f"gate timed out after {timeout_s}s", started)
    except OSError as exc:
        return _error(name, f"gate could not be executed: {exc}", started)

    try:
        result = parse_gate_json(completed.stdout, expected_gate=name)
    except Exception as exc:
        detail = (completed.stderr or completed.stdout or "").strip()[-_STDERR_TAIL:]
        return _error(name, f"gate emitted no usable contract ({exc}): {detail}", started)

    result.duration_ms = _elapsed_ms(started)
    return result


def run_suite(
    gates: dict[str, Path], cwd: Path, *, timeout_s: float = 900
) -> list[GateResult]:
    """Run every declared gate in declaration order."""
    return [
        run_gate(name, executable, cwd, timeout_s=timeout_s)
        for name, executable in gates.items()
    ]


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _error(gate: str, summary: str, started: float) -> GateResult:
    return GateResult(
        gate=gate, status="error", summary=summary, duration_ms=_elapsed_ms(started)
    )
