"""Does a lens's vacuity probe survive the suite? (the design spec of 2026-09-09)

**A green suite is the positive result** — the inversion of `witness_gate`,
which applies a mutant a criterion declared and reads a `fail` as the answer it
wanted. Here the edit comes from a lens's finding, and a suite that stays green
under it is the finding confirmed: the tests do not notice the behaviour
breaking, which is what the finding said.

This module holds the verdict and no I/O. `mutate` and `run_tests` are injected
exactly as `witness_gate` takes them, so every branch below is reachable without
a container — and so the host never holds a path into a cell.

**Three verdicts, and a fourth that is not this module's to give.** A `killed`
probe may be a test doing its job or a probe that broke the program; nothing
here can tell that from a real kill, so `killed` carries its failure identities
and a person annotates the ones that are collateral. A heuristic in this spot
would be a silently-wrong step inside the one number that exists because
reading is not running.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Literal

from saffron.gates.baseline import subtract_baseline
from saffron.gates.contract import GateResult
from saffron.intake import Mutant

# Redeclared rather than imported from `witness`/`revert`, which each redeclare
# it from the other for the same reason: this module owes them a precedent, not
# a dependency.
RunTests = Callable[[list[str]], GateResult]
Mutated = Callable[[Mutant], AbstractContextManager[str | None]]

Verdict = Literal["survived", "killed", "unproven"]


def _no_longer_collected(baseline: GateResult, mutated: GateResult) -> list[str]:
    """Node ids the baseline collected and the mutated run did not.

    A **set** difference, and deliberately not `subtract_baseline`'s counting
    rule: a node id is unique in a suite, so a name that stopped collecting is
    a removal, where two failures can share an identity legitimately. `census`
    draws the same distinction on the same field. One-directional for the same
    reason it is there — a name that *appeared* is not breakage.

    `None` is not `[]` (`GateResult.collected`): a runner that does not
    enumerate has said nothing about which tests exist, which is not evidence
    that a probe removed one.

    Not `suite_drift`, which answers a different question — whether a *gate*
    stopped running or changed tool between two suites — and never reads
    `collected`.
    """
    if baseline.collected is None or mutated.collected is None:
        return []
    return sorted(set(baseline.collected) - set(mutated.collected))


@dataclass(frozen=True)
class ProbeResult:
    """One probe, applied and asked."""

    verdict: Verdict
    reason: str
    """Why, in the lens's own terms where there is one. Always populated for
    `unproven`, where the reason is the whole content of the result."""
    failures: tuple[str, ...] = ()
    """The new failure identities behind a `killed`. Itemised rather than
    counted: telling a real kill from program breakage is a person's call and
    they cannot make it from a number."""


def check_probe(
    mutant: Mutant,
    *,
    baseline: GateResult,
    mutate: Mutated,
    run_tests: RunTests,
    test_paths: Sequence[str] = (),
) -> ProbeResult:
    """Apply one vacuity probe at the head tree and ask the repo's declared
    `tests` gate."""
    if test_paths and any(mutant.file.startswith(p) for p in test_paths):
        # The number is otherwise satisfiable by construction: the adequacy
        # prompt offers an edit "to the source or to the test", and deleting an
        # assertion survives trivially. Refused before `mutate`, so nothing is
        # written for a question that must not be asked.
        return ProbeResult(
            "unproven", f"{mutant.file} is a test; a probe must target source"
        )
    if baseline.status == "error":
        return ProbeResult(
            "unproven",
            "the baseline tests gate errored, so there is nothing to subtract from",
        )

    with mutate(mutant) as refusal:
        if refusal is not None:
            # One of `source_mutated`'s six refusals. None is evidence about
            # the lens, and the tree is untouched.
            return ProbeResult("unproven", refusal)
        # The whole suite, never a subset, unlike `witness_gate`'s one named
        # witness: a probe's question is whether *anything* notices. A
        # function-local list, not a module-level constant handed to a
        # callable this module does not control.
        mutated = run_tests([])

    if mutated.status == "error":
        # `error` is not `fail`, and here it is not `pass` either: reading a
        # gate that could not start as `survived` would count a broken
        # toolchain as a verified vacuity.
        return ProbeResult(
            "unproven", f"the tests gate errored under the probe: {mutated.summary}"
        )
    gone = _no_longer_collected(baseline, mutated)
    if gone:
        # Broke the program at import time. The subtraction below is
        # untrustworthy rather than merely non-empty.
        return ProbeResult(
            "unproven", f"the probe stopped these collecting: {', '.join(gone)}"
        )

    new = subtract_baseline([mutated], [baseline])
    if not new:
        return ProbeResult("survived", "no new failure against the baseline")
    return ProbeResult(
        "killed",
        f"{len(new)} new failure(s) against the baseline",
        tuple(n.failure.code for n in new),
    )
