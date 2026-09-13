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
when a spike arm finds it. The last two members are the exception in kind, not
in rule: what has been *proven* of a runtime differs too, and a runtime not yet
proven must say so rather than inherit the first one's standing.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from saffron.cell.runtime import Completed


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

    @property
    def security_flags(self) -> list[str]:
        """In-guest hardening this runtime exposes, beyond `--cap-drop ALL`.

        Empty is a real answer and not a gap: §5.1 declines `no-new-privileges`
        and seccomp under a VM-per-cell runtime *because* the private kernel is
        offered as the boundary instead. A runtime with no VM has no such offer
        and must supply them — which is why this is a dialect member rather than
        a constant in the argv builder.
        """

    def cpu_flags(self, cpus: int) -> list[str]:
        """The ceiling that makes the cell's visible CPU count honest.

        §5.1 writes the requirement rather than the flag, because the flag is
        the half that moves: a quota leaves the visible core count untouched and
        thread pools size themselves from it, which is the oversubscription mode
        the requirement exists to prevent. What a runtime must supply is
        whatever makes the guest see only the CPUs it has.

        **How completely it can be supplied is a property of the runtime, and
        the two answers are not equal.** A per-cell VM has N CPUs, so every API
        agrees. A shared kernel can only narrow the affinity mask, and a library
        reading `sysconf` or `/proc/cpuinfo` still sees the machine — measured,
        `docs/evidence/2026-09-11-podman-as-a-second-cell-runtime.md`. Each
        implementation says which it gives.
        """

    @property
    def unattended(self) -> bool:
        """Whether a night may run on this runtime: true only once a cell has
        started end to end on it, which is a fact about evidence, not flags."""

    def host_refusal(self, call: Callable[[Sequence[str]], Completed]) -> str | None:
        """Why this host must not run cells under this runtime, or None.

        Asked by running the runtime, never by reading the host around it — the
        answer is whatever the binary says about itself (principle 39).
        """
