"""The gate suite (§5.4): every gate executed as one unit against one tree, and the
**suite comparison** judging it against its baseline yields (`CONTEXT.md` §4).

One module for what GATE ⇄ REPAIR, REBUT and PACKAGE each assembled by hand:
the core-gate order, the blocking levels and the comparison's three outcomes
have one home, and a second caller cannot get a nearly-right copy (principle 54).
The module invokes declared gates and the core gates, never a tool (§2.1).
"""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from saffron.cell import worktree
from saffron.gates import runner
from saffron.gates.baseline import NewFailure, subtract_baseline, suite_drift
from saffron.gates.contract import GateResult, witness_blocking
from saffron.gates.core.census import census_gate
from saffron.gates.core.committed import committed_gate
from saffron.gates.core.criteria import criteria_gate
from saffron.gates.core.integrity import integrity_gate
from saffron.gates.core.revert import revert_gate
from saffron.gates.core.scope import scope_gate
from saffron.gates.core.size import size_gate
from saffron.intake import Criterion, Mutant, RiskTier
from saffron.repos.policy import Policy, effective_risk


def aborted_gates(results: Sequence[GateResult]) -> list[str]:
    """Gates that `error`ed: the gate broke, the attempt aborts, and nothing is
    charged to the task (§5.4)."""
    return [r.gate for r in results if r.status == "error"]


class SuiteSpec(Protocol):
    """What the suite reads off a spec."""

    @property
    def risk(self) -> str: ...
    @property
    def touches(self) -> list[str]: ...
    @property
    def forbidden(self) -> list[str]: ...
    @property
    def acceptance(self) -> list[Criterion]: ...
    @property
    def spec_type(self) -> str: ...


class Tree(Protocol):
    """The seam: where the suite's gates run, and the worktree it reads."""

    @property
    def cwd(self) -> Path: ...
    @property
    def executor(self) -> runner.GateExecutor: ...
    def changed_files(self, base: str) -> list[str]: ...
    def patch(self, base: str) -> str: ...
    def dirty_paths(self) -> list[str]: ...
    def reverted(
        self, base: str, paths: Sequence[str]
    ) -> AbstractContextManager[None]: ...
    def mutated(self, mutant: Mutant) -> AbstractContextManager[str | None]: ...


@dataclass(frozen=True)
class CellTree:
    """A running cell's worktree — the production adapter. `cwd` is the host
    path `run_suite` is handed and `CellExecutor` ignores."""

    container: str
    cwd: Path

    @property
    def executor(self) -> runner.GateExecutor:
        return runner.CellExecutor(self.container)

    def changed_files(self, base: str) -> list[str]:
        return worktree.changed_files(self.container, base)

    def patch(self, base: str) -> str:
        return worktree.export_patch(self.container, base)

    def dirty_paths(self) -> list[str]:
        return worktree.dirty_paths(self.container)

    def reverted(self, base: str, paths: Sequence[str]) -> AbstractContextManager[None]:
        return worktree.source_reverted(self.container, base, paths)

    def mutated(self, mutant: Mutant) -> AbstractContextManager[str | None]:
        return worktree.source_mutated(self.container, mutant)


@dataclass(frozen=True)
class SuiteRun:
    """One gate suite's results, and §5.6's two answers it was run under."""

    results: list[GateResult]
    effective_risk: str
    advisory_gates: frozenset[str]

    @property
    def aborted(self) -> list[str]:
        return aborted_gates(self.results)


@dataclass(frozen=True)
class SuiteComparison:
    """At most one of the three outcomes is non-empty, checked in the order
    below; all three empty is green."""

    run: SuiteRun
    aborted: tuple[str, ...] = ()
    drift: tuple[str, ...] = ()
    new_failures: tuple[NewFailure, ...] = ()


@dataclass(frozen=True)
class GateSuite:
    """One task's gate suite: its declared gates, spec and policy, with every
    diff-reading gate measured from `diff_base`."""

    gates: dict[str, Path]
    spec: SuiteSpec
    policy: Policy
    diff_base: str

    def baseline(self, tree: Tree) -> SuiteRun:
        """At the base the diff is empty, so `scope` and `integrity` pass, and
        `revert`, `census` and `criteria` have no baseline of their own and skip."""
        return self._run(tree, prior=[])

    def against(self, tree: Tree, baseline: SuiteRun) -> SuiteComparison:
        return _compare(self._run(tree, prior=baseline.results), baseline)

    def _run(self, tree: Tree, *, prior: list[GateResult]) -> SuiteRun:
        spec, policy = self.spec, self.policy
        changed = tree.changed_files(self.diff_base)
        diff = tree.patch(self.diff_base)
        # §5.6: from this run's own changed files, never a second read of the diff.
        tier = effective_risk(spec.risk, changed, policy.elevate_on)
        advisory = _advisory(tier, policy)
        # Declared gates run before `dirty_paths` is read, on both calls, so an
        # artifact a gate writes is dirty on both sides and cancels (item 14).
        # `mutate` is what turns `witness` on; `run_suite` places it after `tests`.
        declared = runner.run_suite(
            self.gates,
            cwd=tree.cwd,
            executor=tree.executor,
            acceptance=spec.acceptance,
            mutate=tree.mutated,
        )
        # After the declared gates (real `collected`/`failures` at head), before
        # `committed`, which must see the tree `revert` restored (§5.4). No
        # `tests` role is no runner to re-invoke, so it is left out entirely.
        reverted = (
            [
                revert_gate(
                    prior=prior,
                    results=declared,
                    acceptance=spec.acceptance,
                    changed_files=changed,
                    test_paths=policy.integrity.test_paths,
                    dirty=tree.dirty_paths,
                    reverted=lambda paths: tree.reverted(self.diff_base, paths),
                    run_tests=lambda subset: runner.run_gate(
                        "tests",
                        self.gates["tests"],
                        cwd=tree.cwd,
                        subset=subset,
                        executor=tree.executor,
                    ),
                )
            ]
            if "tests" in self.gates
            else []
        )
        results = [
            scope_gate(
                changed,
                spec.touches,
                diff=diff,
                forbidden=spec.forbidden,
                protected=policy.protected,
            ),
            integrity_gate(diff, policy.integrity, spec.touches),
            # An unreadable diff refused here aborts the attempt, which no
            # advisory filter can soften — so it refuses only where it blocks.
            size_gate(
                diff, spec.spec_type, spec.touches, blocking="size" not in advisory
            ),
            *declared,
            *reverted,
            committed_gate(tree.dirty_paths()),
        ]
        # Last: both read `collected` off the whole suite, and skip at baseline.
        return SuiteRun(
            results=[
                *results,
                census_gate(prior, results),
                criteria_gate(spec.acceptance, prior, results),
            ],
            effective_risk=tier,
            advisory_gates=advisory,
        )


def _advisory(tier: str, policy: Policy) -> frozenset[str]:
    """`blocking: false` is advisory at every tier; `size` and `witness` are
    advisory unless the tier is elevated (§5.4, §5.4.1, §5.6)."""
    advisory = {name for name, decl in policy.gates.items() if not decl.blocking}
    if tier != "elevated":
        advisory.add("size")
    if not witness_blocking(cast(RiskTier, tier)):
        advisory.add("witness")
    return frozenset(advisory)


def _compare(head: SuiteRun, baseline: SuiteRun) -> SuiteComparison:
    if aborted := aborted_gates(head.results):
        return SuiteComparison(head, aborted=tuple(aborted))
    if drift := suite_drift(head.results, baseline.results):
        # The suites differ in a way no failure can express, so the
        # subtraction is not to be trusted, let alone reported (§5.4).
        return SuiteComparison(head, drift=tuple(drift))
    return SuiteComparison(
        head,
        new_failures=tuple(
            nf
            for nf in subtract_baseline(head.results, baseline.results)
            if nf.gate not in head.advisory_gates
        ),
    )
