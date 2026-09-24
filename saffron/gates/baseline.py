"""Baseline subtraction: only new failures are a task's problem.

A failure on `base_sha` is pre-existing and not this task's fault, so the
subtraction cancels it. A `witness` failure coded `survived-mutant` is the
exception. It is not subtracted, because the spec asked this task to kill
that mutant.
Without the subtraction every task inherits the repo's flaky tests and burns
its budget on them (DESIGN.md §5.4).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from typing import NamedTuple

from saffron.gates.contract import Failure, GateResult, identity


class NewFailure(NamedTuple):
    gate: str
    failure: Failure


def _cancels(gate: str, failure: Failure) -> bool:
    """Whether a baseline failure cancels its match at head.

    A `witness` failure coded `survived-mutant` never does. It is not
    subtracted, because the spec asked this task to kill that mutant
    (DESIGN.md §5.4).
    """
    return not (gate == "witness" and failure.code == "survived-mutant")


def _cancelling(results: list[GateResult]) -> Counter[tuple[str, str, str, str]]:
    return Counter(
        identity(result.gate, failure)
        for result in results
        for failure in result.failures
        if _cancels(result.gate, failure)
    )


def subtract_baseline(
    head: list[GateResult], base: list[GateResult]
) -> list[NewFailure]:
    """Failures at head with no cancelling baseline failure.

    Compared on `(gate, file, code, normalized message)`, never on the line
    number the diff moves. Count-aware, because `normalize_message` erases the
    digits that tell sibling failures apart: one baseline failure cancels one
    at head. A `witness` failure coded `survived-mutant` at base never
    cancels, because the spec asked this task to kill that mutant (§5.4).
    """
    remaining = _cancelling(base)
    new = []
    for result in head:
        for failure in result.failures:
            key = identity(result.gate, failure)
            if remaining[key]:
                remaining[key] -= 1
            else:
                new.append(NewFailure(result.gate, failure))
    return new


def suite_drift(head: list[GateResult], base: list[GateResult]) -> list[str]:
    """Differences between the two suites that make the subtraction untrustworthy.

    The subtraction compares failures, and two suites can differ in ways that
    produce no failures at all (§5.4): `tool` is what distinguishes "ran and
    passed" from "didn't run", and a gate that passed at baseline and skipped at
    head stopped running. Either is grounds to distrust the subtraction rather
    than report it.

    `tool` is only compared where the gate ran on *both* sides. A gate that
    exempts itself until its subject exists — no migrations yet, no frontend —
    reports `tool: null` at baseline and a real tool at head the moment the task
    creates one, and that is the task succeeding, not the suite drifting. The
    case the check exists for, a gate that *stopped* running, is the status
    branch and is unaffected.

    A tool version that changes under the run does still fire, including on a
    linter bumped mid-task: §5.4 makes the version part of what the subtraction
    trusts, so the run aborts rather than reporting against two different tools.

    Gates present in one suite only: head-only gates are skipped, base-only
    gates are never examined. Benign while both suites come from the same
    policy-derived map, which is the only caller today.

    ponytail: compared in memory, over this run's two suites. `gate_results`
    carries a `tool` since item 88, so reconstructing this check from a recorded
    run is now possible — it is simply not implemented.
    """
    before = {result.gate: result for result in base}
    drift = []
    for result in head:
        was = before.get(result.gate)
        if was is None:
            continue
        ran_both = was.status in ("pass", "fail") and result.status in (
            "pass",
            "fail",
        )
        if ran_both and was.tool != result.tool:
            drift.append(f"{result.gate}: tool {was.tool!r} -> {result.tool!r}")
        elif was.status != "skip" and result.status == "skip":
            drift.append(f"{result.gate}: {was.status} at baseline, skip at head")
    return drift


def is_no_progress(
    current: Sequence[NewFailure], previous: Sequence[NewFailure]
) -> bool:
    """An identical new-failure set across two attempts: stop paying.

    It lives beside the
    subtraction because both key on the same identity, and §5.4's argument is
    that they must not drift apart. Counted, for the same reason the
    subtraction is: fixing three of four identical-identity failures is
    progress, and a set could not see it.
    """
    return Counter(identity(n.gate, n.failure) for n in current) == Counter(
        identity(n.gate, n.failure) for n in previous
    )
