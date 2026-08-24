"""The `committed` gate: is the tree the gates measure the tree the patch
contains? (DESIGN.md §5.4)

Core, and it executes nothing — `session.py` reads the worktree's status the
way it reads the diff for `scope`. The gates run against `/work` while
`export_patch` diffs `base_sha..HEAD`, so an uncommitted change is live for
every gate and absent from the diff `scope`, `integrity` and the reviewer all
read.
"""

from __future__ import annotations

from saffron.gates.contract import Failure, GateResult

_MESSAGE = (
    "changed but not committed; the gates measure the committed tree, and the "
    "patch a reviewer reads is base_sha..HEAD"
)


def committed_gate(dirty: list[str]) -> GateResult:
    """`fail`, never `error`: a dirty tree is the attempt's problem, and an
    `error` would abort it and be charged to nobody (§5.4)."""
    if not dirty:
        return GateResult(gate="committed", status="pass", summary="worktree clean")
    return GateResult(
        gate="committed",
        status="fail",
        # One failure per path: identity is what the no-progress rule counts,
        # so a second dirty attempt over the same paths must look identical.
        failures=[
            Failure(file=path, code="uncommitted-change", message=_MESSAGE)
            for path in dirty
        ],
        summary=f"{len(dirty)} path(s) changed but not committed",
    )
