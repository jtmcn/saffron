"""What differs between cell runtimes — and deliberately nothing else.

`saffron/cell/runtime.py` holds the whole surface above this: create a network
and a volume, run a container on it with limits, exec, inspect, destroy. None of
that changes with the product. What changes is a small dialect — the binary's
name, how a CPU ceiling is spelled, how `exec` is told where to run — and this
is the contract a second runtime satisfies.

**Minimal on purpose, and it grows by measurement.** Appendix G's mistake was a
proper noun standing in for a contract; the opposite mistake is a contract
standing in for a product nobody has run. Every member below is a difference
actually observed between two runtimes
(`docs/evidence/2026-09-11-podman-as-a-second-cell-runtime.md`). A difference
that has not been measured does not get an entry here in advance — it gets one
when a spike arm finds it.
"""

from __future__ import annotations

from typing import Protocol


class Dialect(Protocol):
    """One cell runtime's spelling of the things that are not universal."""

    @property
    def binary(self) -> str:
        """The executable. The one name `saffron/` may not spell anywhere else."""

    @property
    def cpu_offset(self) -> int:
        """vCPUs the runtime allocates beyond what a CPU ceiling asks for.

        A calibration, never a guess: the supervisor requests `n - offset` and
        asserts the result (§5.1). Measured per runtime, and re-measured with
        the spike on any upgrade.
        """

    @property
    def exec_workdir_flag(self) -> str:
        """How `exec` is told which directory to run in."""

    def cpu_flags(self, cpus: int) -> list[str]:
        """The ceiling that makes `nproc` honest inside the cell.

        §5.1 writes the requirement rather than the flag, because the flag is
        the half that moves: a quota leaves the visible core count untouched and
        thread pools size themselves from it, which is the oversubscription mode
        the requirement exists to prevent. What a runtime must supply is
        whatever makes the guest see only the CPUs it has.
        """
