"""Baseline subtraction: only new failures are a task's problem.

Failures on `base_sha` are pre-existing and not this task's fault. Without the
subtraction every task inherits the repo's flaky tests and burns its budget on
them (DESIGN.md §5.4).
"""

from __future__ import annotations

from collections import Counter
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


def is_no_progress(current: list[NewFailure], previous: list[NewFailure]) -> bool:
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
