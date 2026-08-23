"""The `census` gate: which tests existed before, and which exist now? (§5.4)

Core, and it executes nothing. The repo's `tests` gate already runs at
`base_sha` to build the baseline and again at head on every attempt, so the
collected names do not have to be fetched — only reported. Core subtracts two
lists it is already holding, which is §2.1's original rule rather than
`revert`'s exception to it (Appendix M).

Every name is opaque: never split, never parsed, never assumed to contain a
path or a separator. A runner reporting `tests/test_x.py::test_b` and one
reporting `pkg.TestFoo` are read identically, and neither teaches core
anything about a language.
"""

from __future__ import annotations

from saffron.gates.contract import Failure, GateResult


def _collected(results: list[GateResult]) -> list[str] | None:
    """Every name any gate enumerated, or `None` if none reported.

    Core does not name the `tests` role here. A gate reports `collected` or it
    does not; which role it fills is the repo's business (§2.1). Reporting
    gates are unioned, so a repo splitting its suite across two of them needs
    no special case.
    """
    reported = [r.collected for r in results if r.collected is not None]
    if not reported:
        return None
    return [name for names in reported for name in names]


# ponytail: a task that legitimately removes a test cannot pass — the `touches`
# exemption binds `integrity` and deliberately not this gate (§5.4), so there is
# no override. The upgrade path is a spec field (`may_remove_tests`, or a
# per-name allowance); unbuilt because no task has needed one, and schema
# designed against a guess is schema designed wrong.


def census_gate(base: list[GateResult], head: list[GateResult]) -> GateResult:
    """Names collected at `base_sha`, minus names collected at head.

    The two sides are deliberately not symmetric. No names at base is a gate
    with nothing to compare; no names at head after some at base is a suite
    that stopped enumerating, which is infrastructure and charged to nobody
    (§5.4) — never a report that every test was deleted.
    """
    before = _collected(base)
    after = _collected(head)

    if before is None:
        return GateResult(
            gate="census",
            status="skip",
            summary="no gate reported collected tests at base_sha",
        )
    if after is None:
        return GateResult(
            gate="census",
            status="error",
            summary=(
                f"{len(before)} tests were enumerated at base_sha and none at "
                "head; the comparison is not trustworthy"
            ),
        )

    # A set, unlike the baseline subtraction it sits beside: failure identities
    # collide legitimately and must be counted (§5.4), but a name is unique in
    # a suite by construction. Sorted so the failure order does not depend on
    # the runner's.
    removed = sorted(set(before) - set(after))
    if not removed:
        return GateResult(
            gate="census",
            status="pass",
            summary=f"{len(after)} tests collected, none of {len(before)} removed",
        )

    return GateResult(
        gate="census",
        status="fail",
        failures=[
            Failure(
                file=name,
                code="removed-test",
                message="collected at base_sha, absent at head",
            )
            for name in removed
        ],
        summary=f"{len(removed)} of {len(before)} collected tests no longer collected",
    )
