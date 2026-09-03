"""The `revert` gate: does a new test detect the thing it claims to? (§5.4)

The anti-theater gate. Stash the source hunks of the diff, keep the test
hunks, run only the new and changed tests, and require them to **fail**. Ship
the half core can compute: "new" is a set difference over names the host
already holds (`collected(head) - collected(base)`, `census`'s own route);
"changed-body-same-name" needs a hunk-to-node-id mapping, which is language
knowledge §2.1 keeps out of core (`docs/BACKLOG.md`).

The one sanctioned exception to "core executes nothing" (§2.1): it re-invokes
a gate the repo already declared, through the same JSON contract as every
other gate, with one extra argument — never a tool. Both the worktree
mutation (revert, then restore) and the test re-run are handed in rather than
discovered, so every test here runs against a fake and needs no container.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager

from saffron.gates.contract import Failure, GateResult
from saffron.gates.core.scope import matches
from saffron.intake import Criterion

# Revert the given source paths for the `with` block, restoring them after —
# failing and erroring paths alike. `worktree.source_reverted` is the one
# production implementation; a checkout or restore it cannot make raises,
# which this gate turns into `error`, never `fail` (§5.4).
Reverted = Callable[[list[str]], AbstractContextManager[None]]

# Run the repo's declared `tests` gate over exactly this subset — never
# discovered here; core knows nothing about which gate fills the role (§2.1).
RunTests = Callable[[list[str]], GateResult]


def _collected(results: list[GateResult]) -> list[str] | None:
    """`census._collected`'s own route, copied rather than imported: `census`
    is `forbidden` here, and its helper is module-private."""
    reported = [r.collected for r in results if r.collected is not None]
    if not reported:
        return None
    return [name for names in reported for name in names]


def revert_gate(
    *,
    prior: list[GateResult],
    results: list[GateResult],
    acceptance: Sequence[Criterion],
    changed_files: Sequence[str],
    test_paths: Sequence[str],
    reverted: Reverted,
    run_tests: RunTests,
) -> GateResult:
    """New tests, run with their own source reverted, must not pass.

    `skip` is not evidence, and there are three different kinds of nothing to
    revert: no readable enumeration at base (nothing to subtract from), a diff
    that adds no test (the subset is empty), and a diff whose changed files
    are entirely inside the repo's declared test paths (nothing to revert).
    None of the three touches `reverted` or `run_tests`.
    """
    before = _collected(prior)
    after = _collected(results)
    if before is None or after is None:
        return GateResult(
            gate="revert",
            status="skip",
            summary="no readable test enumeration to compare — nothing to revert",
        )

    # Arithmetic on lists the host already holds — never a second enumeration
    # — minus any witness a criterion declared `preserves`: that criterion is
    # specified to be green at base and at head, and requiring it to fail
    # without the source would contradict its own declaration (§5.4).
    preserved = {c.witness for c in acceptance if c.preserves}
    subset = sorted((set(after) - set(before)) - preserved)
    if not subset:
        return GateResult(
            gate="revert", status="skip", summary="the diff adds no new test"
        )

    # File-level, not hunk-level (out of scope, `docs/BACKLOG.md`): a changed
    # file matching none of the repo's declared test paths is source.
    source = [
        p for p in changed_files if not any(matches(p, pat) for pat in test_paths)
    ]
    if not source:
        return GateResult(
            gate="revert",
            status="skip",
            summary="the diff has no source outside the repo's declared test paths",
        )

    try:
        with reverted(source):
            reverted_result = run_tests(subset)
    except Exception as exc:
        # A checkout or a restore that did not happen means this gate never
        # ran — infrastructure, charged to nobody, never the task's `fail`.
        return GateResult(
            gate="revert",
            status="error",
            summary=f"could not revert or restore the source — {exc}",
        )

    if reverted_result.status not in ("pass", "fail"):
        return GateResult(
            gate="revert",
            status="error",
            summary=(
                "the reverted run did not produce a trustworthy result: "
                f"{reverted_result.status}"
            ),
        )

    # The same predicate `criteria._green` computes, in the direction that
    # closes `criteria`'s own documented hole: a name is theater iff it ran
    # (is in `collected`) and did not fail (its code is absent from
    # `failures`). A name that failed, errored, or vanished from collection
    # entirely are three acceptable answers; only a clean pass is the defect.
    collected = set(reverted_result.collected or ())
    failed = {f.code for f in reverted_result.failures}
    passed = sorted(name for name in subset if name in collected and name not in failed)

    if passed:
        return GateResult(
            gate="revert",
            status="fail",
            failures=[
                Failure(
                    file=name,
                    code="passed-without-source",
                    message="ran and passed with its own source reverted",
                )
                for name in passed
            ],
            summary=f"{len(passed)} of {len(subset)} new test(s) passed without their source",
        )
    return GateResult(
        gate="revert",
        status="pass",
        summary=f"{len(subset)} new test(s) failed without their source, as required",
    )
