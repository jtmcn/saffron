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

import posixpath
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Literal

from saffron.gates.baseline import subtract_baseline
from saffron.gates.contract import GateResult
from saffron.intake import Mutant

# Redeclared rather than imported from `witness`/`revert`: this module owes
# them a precedent, not a dependency.
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
    tool: str | None = None
    """What the gate ran, as it reported it. `None` when no gate answered."""
    collected: int | None = None
    """How many node ids the gate enumerated on the mutated run. `None` when
    no gate answered, or when the gate does not enumerate — never `0` for
    either, because `GateResult.collected` makes `None` and `[]` different
    facts and this count inherits that."""
    summary: str = ""
    """The gate's own one-line summary of the run — for this repo's `tests`
    gate, pytest's "N passed in Xs".

    These three exist because a `survived` verdict means "no new failure
    against the baseline", and a suite that collected almost nothing is green
    too. Without them nothing in the record can tell those apart: the first
    end-to-end pass put the in-cell suite at ~14s where the same tree takes
    78-87s on the host, and the verdict kept nothing that could adjudicate it
    (`docs/superpowers/specs/2026-09-09-mutation-verified-capability-design.md`).
    Taken from the *mutated* run, which is the one the verdict is about."""
    baseline_failures: tuple[str, ...] | None = None
    """What was already red in the suite the verdict was subtracted from.

    **`None` is not `()`**, and the pair is what makes a verdict auditable:
    `()` is a baseline that was read and was green, `None` a baseline nothing
    consulted — including every `probes.json` written before this field
    existed. Collapsing them reads the baseline pass's eight files as eight
    green baselines, which is the claim item 94 exists to refuse.

    Measured (`docs/BACKLOG.md` item 94): `SA-0063`'s head runs `1502 passed`
    on the host and `1 failed, 1499 passed, 2 skipped` in the cell at the same
    1502 collected. The subtraction cancels that failure correctly — no *new*
    failure — but whether it is the very test that would have caught the
    mutation is undecidable from a record keeping only what survived it."""
    baseline_tool: str | None = None
    """What ran the baseline, as it reported it. `None` when none was read."""
    baseline_collected: int | None = None
    """How many node ids the baseline enumerated, on `collected`'s own terms —
    `None` for a gate that does not enumerate, never `0`."""
    baseline_summary: str = ""
    """The baseline suite's own one-line summary. The skip count lives here and
    nowhere else: a `survived` over a baseline that *skipped* the relevant test
    is the same defect as one over a baseline that failed it, and only this
    line distinguishes either from a green run."""


def _repo_relative(file: str) -> str | None:
    """`file` normalised, or `None` when it names nothing inside the tree.

    The path is model-authored, so it is normalised before anything compares
    it: `ls-tree HEAD --` resolves `tests/x.py`, `./tests/x.py` and
    `a/../tests/x.py` to the same blob (measured 2026-09-09), so a raw prefix
    test refuses one spelling of a test file and applies the other two.
    """
    normalised = posixpath.normpath(file)
    escapes = normalised == ".." or normalised.startswith("../")
    return None if posixpath.isabs(normalised) or escapes else normalised


def _under(path: str, prefix: str) -> bool:
    """Segment-wise containment: `tests/` covers `tests/test_x.py` and not
    `tests_helpers/x.py`. Both sides normalised, or `tests/` would match
    nothing after the left side lost its trailing slash."""
    prefix = posixpath.normpath(prefix)
    return path == prefix or path.startswith(prefix + "/")


def check_probe(
    probe: Mutant,
    *,
    baseline: GateResult,
    mutate: Mutated,
    run_tests: RunTests,
    test_paths: Sequence[str],
) -> ProbeResult:
    """Apply one vacuity probe at the head tree and ask the repo's declared
    `tests` gate.

    `test_paths` carries no default: the refusal below is the one guard the
    design spec calls non-optional, and a default would let a caller that
    forgot it measure with no refusal at all, silently.
    """
    target = _repo_relative(probe.file)
    if target is None:
        return ProbeResult(
            "unproven", f"{probe.file} is not a relative path inside the tree"
        )
    if any(_under(target, prefix) for prefix in test_paths):
        # Otherwise satisfiable by construction — deleting an assertion
        # survives trivially. Refused before `mutate`, so nothing is written.
        return ProbeResult(
            "unproven", f"{probe.file} is a test; a probe must target source"
        )
    if baseline.status not in ("pass", "fail"):
        # `error` or `skip`: a baseline that measured no failures would read
        # every probe against it as a kill of tests that never ran.
        return ProbeResult(
            "unproven",
            f"the baseline tests gate reported `{baseline.status}`, so there "
            "is nothing to subtract from",
        )

    # From here the baseline is a verdict, so every result below carries the
    # suite it will be subtracted from (item 94). Above here it does not: an
    # `error` or `skip` measured no failures, and an empty tuple there would
    # read as a baseline that was green.
    base_failures = tuple(failure.code for failure in baseline.failures)
    base_collected = None if baseline.collected is None else len(baseline.collected)

    with mutate(probe) as refusal:
        if refusal is not None:
            # One of `source_mutated`'s six refusals. None is evidence about
            # the lens, and the tree is untouched.
            return ProbeResult(
                "unproven",
                refusal,
                baseline_failures=base_failures,
                baseline_tool=baseline.tool,
                baseline_collected=base_collected,
                baseline_summary=baseline.summary,
            )
        # The whole suite, never a subset, unlike `witness_gate`'s one named
        # witness: a probe's question is whether *anything* notices.
        mutated = run_tests([])

    if mutated.status not in ("pass", "fail"):
        # `error` is not `fail`, and here not `pass` either. `skip` the same:
        # a suite that never ran is not a suite that failed to notice.
        return ProbeResult(
            "unproven",
            f"the tests gate reported `{mutated.status}` under the probe: "
            f"{mutated.summary}",
            baseline_failures=base_failures,
            baseline_tool=baseline.tool,
            baseline_collected=base_collected,
            baseline_summary=baseline.summary,
        )
    # From here a gate answered, so every verdict below carries what answered
    # it. By name, not splatted: `ty` reads a splat as filling `failures`.
    tool = mutated.tool
    collected = None if mutated.collected is None else len(mutated.collected)
    summary = mutated.summary

    gone = _no_longer_collected(baseline, mutated)
    if gone:
        # Broke the program at import time. The subtraction below is
        # untrustworthy rather than merely non-empty.
        return ProbeResult(
            "unproven",
            f"the probe stopped these collecting: {', '.join(gone)}",
            tool=tool,
            collected=collected,
            summary=summary,
            baseline_failures=base_failures,
            baseline_tool=baseline.tool,
            baseline_collected=base_collected,
            baseline_summary=baseline.summary,
        )

    new = subtract_baseline([mutated], [baseline])
    if not new:
        return ProbeResult(
            "survived",
            "no new failure against the baseline",
            tool=tool,
            collected=collected,
            summary=summary,
            baseline_failures=base_failures,
            baseline_tool=baseline.tool,
            baseline_collected=base_collected,
            baseline_summary=baseline.summary,
        )
    return ProbeResult(
        "killed",
        f"{len(new)} new failure(s) against the baseline",
        tuple(n.failure.code for n in new),
        tool=tool,
        collected=collected,
        summary=summary,
        baseline_failures=base_failures,
        baseline_tool=baseline.tool,
        baseline_collected=base_collected,
        baseline_summary=baseline.summary,
    )
