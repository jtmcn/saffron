"""`apple/container` — the cell runtime, chosen in rev 10 (DESIGN.md Appendix G).

**The only module in `saffron/` permitted to name the product**, enforced by
`.saffron/rules/container-runtime-is-runtime-only.yml`. Everything a caller
touches is in `saffron/cell/runtime.py`, which names no runtime at all.

Decided against the four assertions in `spikes/cell-runtime.sh` rather than left
to taste, and the decision is re-makeable the same way it was made.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from saffron.cell.runtime import Completed


@dataclass(frozen=True)
class Apple:
    """apple/container's dialect. Every value here is measured, not read."""

    @property
    def binary(self) -> str:
        return "container"

    @property
    def cpu_offset(self) -> int:
        # apple/container 1.2.2 gives the VM one vCPU beyond --cpus: measured 1->2,
        # 2->3, 4->5, 6->7. Re-measure with the spike on any upgrade (DESIGN.md §5.1).
        return 1

    @property
    def exec_workdir_flag(self) -> str:
        return "--cwd"

    @property
    def security_flags(self) -> list[str]:
        """None, and deliberately (§5.1). `no-new-privileges` and seccomp have
        no equivalent here; the per-cell VM is the boundary offered instead."""
        return []

    def cpu_flags(self, cpus: int) -> list[str]:
        """A per-cell VM configured with N vCPUs simply *has* N CPUs, so `nproc`
        is honest with no affinity flag at all — the structural form of §5.1's
        requirement, and the single largest point in this runtime's favour.
        """
        return ["--cpus", str(cpus)]

    @property
    def unattended(self) -> bool:
        return True

    def host_refusal(self, call: Callable[[Sequence[str]], Completed]) -> str | None:
        """None: root in the guest is root in a VM holding one cell (§5.1)."""
        return None


DIALECT = Apple()
