"""Baseline subtraction: only new failures are a task's problem.

Failures on `base_sha` are pre-existing and not this task's fault. Without the
subtraction every task inherits the repo's flaky tests and burns its budget on
them (DESIGN.md §5.4).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from typing import NamedTuple

from saffron.gates.contract import Failure, GateResult, identity


class NewFailure(NamedTuple):
    gate: str
    failure: Failure


def _counts(results: list[GateResult]) -> Counter[tuple[str, str, str, str]]:
    return Counter(
        identity(result.gate, failure)
        for result in results
        for failure in result.failures
    )


def subtract_baseline(
    head: list[GateResult], base: list[GateResult]
) -> list[NewFailure]:
    """Failures present at head and absent from the baseline.

    Compared on `(gate, file, code, normalized message)` — never on line
    number, which the diff moves.

    Count-aware: one pre-existing failure cancels one failure at head, not
    every head failure sharing its identity. `normalize_message` turns digit
    runs into `N`, and the digits are exactly what tells sibling failures of
    one rule in one file apart, so a set-based subtraction hid genuinely new
    ones. Known consequence: when N of M identical-identity failures are new,
    the ones *reported* may name a pre-existing line — acceptable, `line` is
    display-only by design.
    """
    remaining = _counts(base)
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

    ponytail: compared in memory, over this run's two suites. `gate_results` has
    no `tool` column, so a later reconstruction from the ledger cannot do it.
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

    No caller in v0 — there is no repair loop yet. It lives beside the
    subtraction because both key on the same identity, and §5.4's argument is
    that they must not drift apart. Counted, for the same reason the
    subtraction is: fixing three of four identical-identity failures is
    progress, and a set could not see it.
    """
    return Counter(identity(n.gate, n.failure) for n in current) == Counter(
        identity(n.gate, n.failure) for n in previous
    )
