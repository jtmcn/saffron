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

from collections.abc import Mapping

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


def census_gate(
    base: list[GateResult],
    head: list[GateResult],
    *,
    renames: Mapping[str, str] | None = None,
) -> GateResult:
    """Names collected at `base_sha`, minus names collected at head, with a
    spec's declared `renames` read pair by pair (`DESIGN.md` §5.4, `SA-0387`).

    The two sides are deliberately not symmetric. No names at base is a gate
    with nothing to compare; no names at head after some at base is a suite
    that stopped enumerating, which is infrastructure and charged to nobody
    (§5.4) — never a report that every test was deleted.

    A pair is accepted where its old name is gone at head and its new name
    is collected at head and absent at base."""
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

    pairs = renames or {}
    before_set = set(before)
    after_set = set(after)
    # A set, unlike the baseline subtraction beside it: a name is unique in
    # a suite, so removal is a set difference (§5.4).
    removed = before_set - after_set
    # An accepted pair's old name leaves the removed set below.
    accepted = {
        old
        for old, new in pairs.items()
        if old in removed and new in after_set and new not in before_set
    }
    removed -= accepted

    failures = [
        Failure(
            file=name,
            code="removed-test",
            message="collected at base_sha, absent at head",
        )
        # Sorted so the failure order does not depend on the runner's.
        for name in sorted(removed)
    ]
    # A new name absent at head fails on its own, whatever the old name's
    # own status.
    missing = [
        Failure(
            file=new,
            code="rename-not-collected",
            message=f"declared renamed from {old!r}, not collected at head",
        )
        for old, new in pairs.items()
        if new not in after_set
    ]
    failures += missing

    if not failures:
        return GateResult(
            gate="census",
            status="pass",
            summary=f"{len(after)} tests collected, none of {len(before)} removed",
        )

    return GateResult(
        gate="census",
        status="fail",
        failures=failures,
        # Counted apart, since a missing new name need not be a base name.
        summary=(
            f"{len(removed)} of {len(before)} collected tests removed, "
            f"{len(missing)} declared renames not collected"
        ),
    )
