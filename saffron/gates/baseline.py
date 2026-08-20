"""Baseline subtraction: only new failures are a task's problem.

Failures on `base_sha` are pre-existing and not this task's fault. Without the
subtraction every task inherits the repo's flaky tests and burns its budget on
them (DESIGN.md §5.4).
"""

from __future__ import annotations

from typing import NamedTuple

from saffron.gates.contract import Failure, GateResult, identity


class NewFailure(NamedTuple):
    gate: str
    failure: Failure


def _identities(results: list[GateResult]) -> set[tuple[str, str, str, str]]:
    return {
        identity(result.gate, failure)
        for result in results
        for failure in result.failures
    }


def subtract_baseline(
    head: list[GateResult], base: list[GateResult]
) -> list[NewFailure]:
    """Failures present at head and absent from the baseline.

    Compared on `(gate, file, code, normalized message)` — never on line
    number, which the diff moves.
    """
    baseline = _identities(base)
    return [
        NewFailure(result.gate, failure)
        for result in head
        for failure in result.failures
        if identity(result.gate, failure) not in baseline
    ]


def is_no_progress(current: list[NewFailure], previous: list[NewFailure]) -> bool:
    """An identical new-failure set across two attempts: stop paying.

    No caller in v0 — there is no repair loop yet. It lives beside the
    subtraction because both key on the same identity, and §5.4's argument is
    that they must not drift apart.
    """
    return {identity(n.gate, n.failure) for n in current} == {
        identity(n.gate, n.failure) for n in previous
    }
