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

# Read lazily, like the two above: the early skips must not cost the caller a
# container round trip, and the baseline pass takes one of them every time.
DirtyPaths = Callable[[], Sequence[str]]


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
    dirty: DirtyPaths = tuple,
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
    # The union, not the difference alone: a criterion's witness is declared to
    # be *not* green at base (`criteria._judge` enforces that for anything not
    # `preserves`), so it is a name this change is claiming to make pass — and
    # a name whose source dependence is exactly what this gate asks about. A
    # witness that already appears at head joins by set union anyway; one the
    # runner did not enumerate at head is dropped below rather than asserted.
    # No `preserves` filter here: the `- preserved` below already removes them,
    # and a second guard for the same thing is a branch no test can kill.
    declared = {c.witness for c in acceptance}
    subset = sorted(((set(after) - set(before)) | (declared & set(after))) - preserved)
    if not subset:
        return GateResult(
            gate="revert", status="skip", summary="the diff adds no new test"
        )

    # File-level, not hunk-level (out of scope, `docs/BACKLOG.md`): a changed
    # file matching none of the repo's declared test paths is source.
    if not test_paths:
        # A fourth kind of nothing, and it must be caught before the worktree is
        # touched: with no declared test paths every changed file reads as
        # source, so the gate would revert the very tests it is about to run.
        # `policy.integrity.test_paths` defaults to `[]`, so this is every repo
        # that has not declared them.
        return GateResult(
            gate="revert",
            status="skip",
            summary="the repo declares no test paths, so source cannot be told from test",
        )
    source = [
        p for p in changed_files if not any(matches(p, pat) for pat in test_paths)
    ]
    if not source:
        return GateResult(
            gate="revert",
            status="skip",
            summary="the diff has no source outside the repo's declared test paths",
        )

    # The restore checks out `HEAD`, not the tree as it stood a moment ago, so
    # an uncommitted edit to a source path does not survive this gate — and
    # `committed` runs next and would report the tree clean, which is the one
    # gate whose whole job is to notice that it is not. Refusing to run is the
    # only honest answer: no evidence about theatre is worth destroying the
    # agent's uncommitted work and blinding the gate that would have caught it.
    if collides := sorted(set(dirty()) & set(source)):
        return GateResult(
            gate="revert",
            status="skip",
            summary=(
                "uncommitted changes to source this gate would revert: "
                f"{', '.join(collides[:3])} — restoring to HEAD would destroy "
                "them and hide them from `committed`"
            ),
        )

    reverted_result: GateResult | None = None
    run_failed: Exception | None = None
    try:
        with reverted(source):
            # Recorded rather than raised, so the `with` unwinds normally and
            # the restore in its `finally` still runs — then reported on its
            # own below. An exception out of the repo's `tests` gate is not a
            # failed checkout, and one message for both sends the operator to
            # the wrong subsystem.
            try:
                reverted_result = run_tests(subset)
            except Exception as exc:  # noqa: BLE001 — reported below, not swallowed
                run_failed = exc
    except Exception as exc:
        # A checkout or a restore that did not happen means this gate never
        # ran — infrastructure, charged to nobody, never the task's `fail`.
        return GateResult(
            gate="revert",
            status="error",
            summary=f"could not revert or restore the source — {exc}",
        )

    if run_failed is not None or reverted_result is None:
        # The tool could not be executed at all. Unlike a result it *did*
        # return (below), this is the gate breaking, so it stays `error`.
        return GateResult(
            gate="revert",
            status="error",
            summary=f"the reverted run could not be executed — {run_failed}",
        )
    if reverted_result.status not in ("pass", "fail"):
        # **Not `error`, and this is the whole gate's usability.** `error` ends
        # the attempt through `session.aborted_gates` — so mapping this here
        # killed the task in the gate's own canonical case. Measured: a spec
        # that lands a module and its tests together has its module removed by
        # `_revert_source`, the tests then fail to *import*, and this repo's
        # `tests` gate reports `error` ("pytest exited N with no parsed
        # failures") rather than `fail`, because a collection error prints no
        # line its regex or its `FAILED ` fallback can read. `DESIGN.md` §5.4
        # says that exact case must report green.
        #
        # `skip` rather than `pass`, for the reason the three nothings above
        # are skips: a run that produced no trustworthy result is not evidence
        # that these tests failed without their source, only that none of them
        # was *seen* to pass. Non-blocking either way, and honest about which.
        return GateResult(
            gate="revert",
            status="skip",
            summary=(
                "the reverted run produced no trustworthy result "
                f"({reverted_result.status}) — the new tests could not run "
                "without their source, which is not evidence either way"
            ),
        )

    # `criteria._side`'s readability guard, which the naive form of this
    # verdict drops. Both halves are `_side`'s, for `_side`'s measured reason:
    # this repo's own `tests` gate keys `failures[].code` on the caught
    # exception type on its common path and reaches node ids only through a
    # fallback, so `failed` can be a set of strings no node id ever equals.
    # Read that way, every genuinely-failing reverted test stays out of
    # `failed` while remaining in `collected` and reads as a clean pass — a
    # false `fail` on a correct, source-dependent test, which is the expensive
    # direction. `criteria` degrades to `skip` rather than report `pass` on a
    # field it could not read; this gate degrades the same way rather than
    # report `fail`.
    #
    # `collected is None` (did not enumerate), not `not collected`: a run that
    # enumerated and found nothing is readable, and it is the ordinary answer
    # when every reverted test fails at import — which is a `pass` here, not a
    # skip.
    if reverted_result.collected is None:
        return GateResult(
            gate="revert",
            status="skip",
            summary="the reverted run reported no collected tests — nothing to read",
        )
    collected = set(reverted_result.collected)
    failed = {f.code for f in reverted_result.failures}
    # ponytail: "at least one overlap", not "every code is a node id" — the
    # same ceiling `criteria._side` names, and the same upgrade path
    # (per-failure membership) once a runner mixes the two keyings in one run.
    if failed and not (failed & collected):
        return GateResult(
            gate="revert",
            status="skip",
            summary=(
                "the reverted run keyed its failures on something other than a "
                "node id, so a failing test cannot be told from a passing one"
            ),
        )

    # A name is theater iff it ran (is in `collected`) and did not fail (its
    # code is absent from `failures`). A name that failed, errored, or vanished
    # from collection entirely are three acceptable answers; only a clean pass
    # is the defect.
    passed = sorted(name for name in subset if name in collected and name not in failed)

    if passed:
        return GateResult(
            gate="revert",
            status="fail",
            tool=reverted_result.tool,
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
        # The tool that actually ran, never a literal (§5.4, Appendix H): this
        # gate is unlike `census`/`criteria` in that it does execute one, and a
        # pass without it is indistinguishable from a gate that never ran.
        tool=reverted_result.tool,
        summary=f"{len(subset)} new test(s) failed without their source, as required",
    )
