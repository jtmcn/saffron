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
from saffron.gates.core.revert import _argv_safe
from saffron.gates.core.witness import Mutated, witness_gate
from saffron.intake import Criterion

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


# More than one, because a single sample deciding the whole gate is the
# fragile part rather than the sample's identity.
_PROBE_ATTEMPTS = 3


def run_witness(
    *,
    gates: dict[str, Path],
    cwd: Path,
    acceptance: Sequence[Criterion],
    mutate: Mutated,
    tests_result: GateResult | None,
    timeout_s: float = 900,
    executor: GateExecutor | None = None,
) -> GateResult | None:
    """`witness` (§5.4.1), wired to the repo's declared `tests` gate.

    `None` when there is nothing for `witness` to run against: a repo that
    declares no `tests` gate at all has no runner for `witness` to
    re-invoke, and the caller leaves it out of the suite entirely — the same
    shape `revert` already uses for the identical reason.

    When at least one criterion declares a `mutant`, this first re-invokes
    `tests` once on the *unmutated* tree, over a subset of exactly one node
    id, before ever applying anything. That subset argument is `revert`'s
    own contract obligation (`docs/BACKLOG.md`,
    `saffron/gates/core/revert.py`), and a repo may not have met it: a
    `tests` gate that cannot be filtered errors on every subset call,
    indistinguishable — from inside `witness_gate` alone — from the
    mutant-killed-its-own-witness trap that gate deliberately answers with
    `error`. Told apart here, on a clean tree, before any mutant is applied.

    The probe id is drawn from `tests_result.collected` — the plain,
    no-subset run's own enumeration — never from a criterion's declared
    `witness`. A criterion's `witness` is written by the operator and can be
    stale (a typo, a renamed test, a moved file); probing with it cannot
    tell "this repo's `tests` gate cannot be filtered" apart from "this one
    criterion names a test that no longer exists", and reading the second as
    the first would report `skip` for the whole gate on the strength of one
    bad id, discarding every *other* declared criterion's real finding for
    the night. A name `tests_result` itself enumerated carries no such risk:
    it is known to exist whatever any criterion claims.

    No readable enumeration to probe with (`tests_result` absent, or its
    `collected` empty or unset) is its own `skip` — not proof of anything,
    the same as `revert`'s identical "nothing to read" answer. A probe that
    errors reports `witness` as `skip`, not `error`, and no mutant is ever
    touched. A probe that answers (`pass` or `fail`) proves the subset
    works, and only then is `witness_gate` invoked for real, once, over
    every declared criterion — preserved exactly as `SA-0057` wrote it,
    inner-`error`-discards-an-earlier-survivor included.
    """
    if "tests" not in gates:
        return None

    def run_tests(subset: list[str]) -> GateResult:
        return run_gate(
            "tests",
            gates["tests"],
            cwd,
            timeout_s=timeout_s,
            subset=subset,
            executor=executor,
        )

    declared = [c for c in acceptance if c.mutant is not None]
    # Hoisted out of the `if` below because `witness_gate` takes it too: the
    # probe asks whether this repo's `tests` gate honours a subset at all, and
    # the same enumeration answers, per criterion, whether a named witness even
    # exists in this tree (item 83).
    collected = tests_result.collected if tests_result is not None else None
    if declared:
        if not collected:
            return GateResult(
                gate="witness",
                status="skip",
                summary=(
                    "no readable test enumeration to probe subset support "
                    "with — nothing to verify a mutant against"
                ),
            )
        # `_argv_safe`, and more than one candidate. `run_gate` builds
        # `argv = [executable, *subset]` with no `--`, and this repo's own
        # `tests` gate calls any collection line holding `::` a name — so a
        # printed `--deselect=…` line is an option to whatever runs it.
        # `revert` drops those for the same reason. Worse here than there: one
        # sample decided the whole gate, so a single stray line bought a
        # blanket `skip` and discarded every criterion's real finding.
        candidates = [name for name in collected if _argv_safe(name)]
        probe = None
        for candidate in candidates[:_PROBE_ATTEMPTS]:
            probe = run_tests([candidate])
            if probe.status != "error":
                break
        if probe is None or probe.status == "error":
            return GateResult(
                gate="witness",
                status="skip",
                summary=(
                    "the repo's `tests` gate does not accept a subset "
                    "argument, so no mutant was applied — "
                    + (
                        probe.summary
                        if probe is not None
                        else "no usable id to probe with"
                    )
                ),
            )
        # Tolerating the argument is not honouring it. A `tests` gate that
        # accepts a subset and runs everything anyway passes the probe above —
        # and then an unrelated test failing under a mutant reads as "the
        # witness died", which is the false confidence §5.4.1 exists to
        # refuse, wearing a verification.
        probed = probe.collected
        if probed is None or set(probed) - {candidate}:
            return GateResult(
                gate="witness",
                status="skip",
                summary=(
                    "the repo's `tests` gate accepted a subset argument and "
                    "did not honour it, so a mutant's failure could not be "
                    "attributed to its own witness"
                ),
            )

    return witness_gate(
        acceptance=acceptance,
        mutate=mutate,
        run_tests=run_tests,
        collected=collected,
    )


def run_suite(
    gates: dict[str, Path],
    cwd: Path,
    *,
    timeout_s: float = 900,
    executor: GateExecutor | None = None,
    acceptance: Sequence[Criterion] = (),
    mutate: Mutated | None = None,
) -> list[GateResult]:
    """Run every declared gate in declaration order.

    `witness` is not one of the declared gates above — it is a core gate,
    like `revert` — but it belongs in this list rather than beside it,
    because it re-invokes `tests` and so cannot exist before `tests`'s own
    result does (§5.4.1). `mutate` is the one thing that turns it on: omitted,
    `witness` is left out of the suite exactly as it was before this function
    knew about it — no behaviour change for a caller that does not ask for it.
    Two production callers supply one today, `session._suite` and
    `package.reverify`, and both pass `acceptance` beside it; the sentence
    here once said no production caller could, which `SA-0061` falsified and
    `docs/BACKLOG.md` item 75 records.
    """
    results = [
        run_gate(name, executable, cwd, timeout_s=timeout_s, executor=executor)
        for name, executable in gates.items()
    ]
    if mutate is not None:
        tests_result = next((r for r in results if r.gate == "tests"), None)
        witness_result = run_witness(
            gates=gates,
            cwd=cwd,
            acceptance=acceptance,
            mutate=mutate,
            tests_result=tests_result,
            timeout_s=timeout_s,
            executor=executor,
        )
        if witness_result is not None:
            # After `tests`, never beside it — its own result is what
            # `witness` re-invokes, so a result that does not exist yet is
            # one it cannot read. Inserted by position, not appended, so
            # this holds whatever order the repo declared its gates in.
            position = next(i for i, r in enumerate(results) if r.gate == "tests") + 1
            results.insert(position, witness_result)
    return results


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _error(gate: str, summary: str, started: float) -> GateResult:
    return GateResult(
        gate=gate, status="error", summary=summary, duration_ms=_elapsed_ms(started)
    )
