"""podman — the second cell runtime, for a host `apple/container` cannot run on.

**The only module in `saffron/` permitted to name this product**, enforced by
`.saffron/rules/podman-runtime-is-runtime-only.yml`, which is this rule's own
copy of the one guarding `apple.py`. One rule cannot serve both: the binary is a
different word and each exemption is asserted by value, so that widening either
is a decision somebody made (backlog items 107, 108).

Daemonless, which is why it is this and not Appendix G's Architecture A: a
container-hosted Linux runner has no socket to offer and no way to start one.
The interaction is the shell-out and structured `inspect` the seam was already
written for.

**What it gives up is the per-cell VM, and that is the whole of the trade.**
Every value below is measured, in
`docs/evidence/2026-09-11-podman-as-a-second-cell-runtime.md`.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from saffron.cell.runtime import Completed


@dataclass(frozen=True)
class Podman:
    """podman's dialect. Measured against 4.9.3; re-measure with the spike."""

    @property
    def binary(self) -> str:
        return "podman"

    @property
    def cpu_offset(self) -> int:
        # No VM to allocate a spare vCPU: measured 1->1 and 2->2.
        return 0

    @property
    def exec_workdir_flag(self) -> str:
        return "-w"

    @property
    def security_flags(self) -> list[str]:
        """The compensation for the missing VM, and the reason §5.1's refusal to
        replace them does not carry over here.

        Measured: with the flag, `NoNewPrivs` is 1 inside the cell and 0
        without it. Seccomp is already in filter mode by default (`Seccomp: 2`)
        and is not asked for again — a flag that restates a default reads as a
        control and is not one.
        """
        return ["--security-opt", "no-new-privileges"]

    def cpu_flags(self, cpus: int) -> list[str]:
        """A mask, because the quota does not satisfy the requirement.

        Measured: `--cpus 2` leaves the cell reporting all four of the host's
        CPUs — §5.1's oversubscription mode exactly — while `--cpuset-cpus 0-1`
        reports two.

        **It is the weaker half of the requirement, and the gap has an owner.**
        The mask reaches `sched_getaffinity`, so `nproc` is honest; it does not
        reach `sysconf` or `/proc/cpuinfo`, so `os.cpu_count()` and a BLAS
        sizing itself that way still see the machine (measured: 2 by affinity, 4
        by both others). Under a per-cell VM `policy.thread_env` is belt and
        braces; under this runtime it is the control, and a repo onboarded here
        that declares none has an uncapped thread pool.

        ponytail: every cell gets the same mask, `0..n-1`, so K concurrent cells
        contend for one set of cores rather than being spread across them. The
        dialect is handed a count and cannot know which cores are free — that is
        §4.2's concurrency question, filed on backlog item 108, and it is why
        this runtime is for one attended task before it is for a night.
        """
        return ["--cpuset-cpus", f"0-{cpus - 1}"]

    @property
    def unattended(self) -> bool:
        # No cell has started end to end here: the measured host refused
        # `DEFAULT_SUBNET`, and `--memory` went unenforced (backlog item 108).
        return False

    def host_refusal(self, call: Callable[[Sequence[str]], Completed]) -> str | None:
        """Rootful podman is refused, because no image sets a `USER`.

        The cell runs as root, and with no user namespace that is root on the
        host kernel, with only `--cap-drop ALL`, `no-new-privileges` and seccomp
        between them. Rootless maps it to the invoking user. The measured host
        ran podman as root (the evidence record's first line).
        """
        done = call([self.binary, "info", "--format", "{{.Host.Security.Rootless}}"])
        if done.returncode != 0:
            return f"could not ask podman whether it is rootless: {done.stderr.strip()}"
        if done.stdout.strip() != "true":
            return (
                "podman is running rootful, so root in a cell would be root on the "
                "host kernel; run it as an unprivileged user (DESIGN.md §5.1)"
            )
        return None


DIALECT = Podman()
