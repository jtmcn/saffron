"""The `witness` gate: does a claim's witness notice its own mutant? (§5.4.1)

**A failing test is the passing result** — the same inversion `revert`
already makes, at a granularity `revert` cannot reach: `revert` reverts whole
files and asks whether the new tests test *anything*, this reverts one named
edit and asks whether one witness tests *that thing*. A criterion may declare a `mutant` — the smallest edit
that would falsify its `claim`. This gate applies that edit to the head tree,
invokes the repo's declared `tests` gate over exactly the one witness node id
the criterion names, and reads a `fail` as the answer it wanted: the witness
noticed the mutant and died. A witness that stays green under its own mutant
is asserting nothing, and that is the finding, not a pass.

It is `revert`'s exception, not a new one (§2.1). This gate executes no
tool: it applies a text edit the *spec* supplied — data, not code — via
`saffron.mutation`, and then invokes a gate the repo already declared,
through the same JSON contract every gate uses, with the subset argument
`revert` established. It runs no runner, knows no framework, and parses no
node id.

**`error` is not `fail`.** A `tests` gate that could not start under the
mutant — collection crashed, the toolchain broke — has answered nothing
about whether the witness guards its claim. It aborts this gate as `error`,
charged to nobody, exactly the collapse `DESIGN.md` refuses everywhere else.

A mutant that does not apply — `find` absent or ambiguous in the tree the
spec anticipated a different implementation for — is the ordinary case, not
a defect: it is named in the summary and counted toward nothing, never
silently bought as a `pass`.

Every mutant is applied to a clean tree and restored before the next is
touched, and restoration is attempted on every exit path — `error`, `skip`,
`pass` and `fail` alike. A restore that itself fails is reported as `error`
with the tree left mutated: nothing further here can fix that, and reporting
anything else would be the false `pass` this gate exists to refuse.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from saffron.gates.contract import Failure, GateResult
from saffron.intake import Criterion
from saffron.mutation import MutationError, apply_mutant, restore_mutant

# Run the repo's declared `tests` gate over exactly this subset — never
# discovered here; core knows nothing about which gate fills the role (§2.1).
# The same shape `revert.py` declares, redeclared rather than imported: this
# module owes `revert` a precedent, not a dependency.
RunTests = Callable[[list[str]], GateResult]


def _named(criterion: Criterion, reason: str) -> str:
    return f"{criterion.witness} ({reason})"


def witness_gate(
    *,
    acceptance: Sequence[Criterion],
    tree: Path,
    run_tests: RunTests,
) -> GateResult:
    """Each criterion's mutant, applied, tested alone, and undone.

    `skip` is the answer for a spec that declares no mutants — every spec
    that exists today, and this gate must not fail a task for a field its
    own spec predates — and for one whose every declared mutant failed to
    apply: named in the summary, never counted as a witness that did its
    job. `error` ends the attempt the moment the repo's `tests` gate could
    not answer for one mutant; nothing already restored is undone, and
    nothing not yet touched is applied.
    """
    declared = [c for c in acceptance if c.mutant is not None]
    if not declared:
        return GateResult(
            gate="witness", status="skip", summary="the spec declares no mutants"
        )

    died: list[str] = []
    survived: list[Failure] = []
    unproven: list[str] = []
    tool: str | None = None

    for criterion in declared:
        mutant = criterion.mutant
        assert mutant is not None  # narrowed by the `declared` filter above
        applied = apply_mutant(tree, mutant)
        if not applied.ok:
            unproven.append(_named(criterion, applied.reason))
            continue

        # No `return` inside the `finally` below. One there discards whatever
        # was in flight — measured: a `KeyboardInterrupt` raised by `run_tests`
        # was swallowed and this gate returned an ordinary `GateResult`, so an
        # operator's Ctrl-C during a mutated test run went nowhere. `except
        # Exception` does not cover a `BaseException`, and ruff's B012 does not
        # see a `return` nested inside a `try` inside a `finally`, so neither
        # the type nor the linter catches it. `revert` uses this same
        # record-then-return shape for the same reason.
        failed_to_run: Exception | None = None
        failed_to_restore: MutationError | None = None
        tests_result = None
        try:
            try:
                tests_result = run_tests([criterion.witness])
            except Exception as exc:  # recorded, reported below, not swallowed
                failed_to_run = exc
        finally:
            try:
                restore_mutant(tree, mutant, applied)
            except MutationError as exc:
                failed_to_restore = exc

        # Restoration first: a tree left mutated is the worse fact, and it is
        # the one that ships in the diff if nothing says so.
        if failed_to_restore is not None:
            return GateResult(
                gate="witness",
                status="error",
                summary=(
                    f"could not restore {mutant.file} after its mutant — "
                    f"{failed_to_restore}"
                ),
            )
        if failed_to_run is not None:
            return GateResult(
                gate="witness",
                status="error",
                summary=(
                    f"the `tests` gate could not be executed for "
                    f"{criterion.witness}'s mutant — {failed_to_run}"
                ),
            )
        assert tests_result is not None  # both failure paths returned above

        # ponytail: an inner `error` ends the attempt through
        # `session.aborted_gates`, and a mutant that kills its witness by making
        # a fixture raise produces exactly that — `.saffron/gates/tests.py`
        # reports `error` when pytest exits non-zero with no `FAILED ` line to
        # parse. `revert.py` met the identical trap and chose `fail` for its
        # canonical case; this spec asked for `error`. Left as asked, and the
        # disagreement is deliberate rather than overlooked — resolve it in
        # `SA-0058` or the backlog, not by editing one of the two to match.
        if tests_result.status == "error":
            # Not `fail`: a runner that could not start under the mutant has
            # answered nothing about whether the witness guards its claim.
            return GateResult(
                gate="witness",
                status="error",
                tool=tests_result.tool,
                summary=(
                    f"the `tests` gate errored under {criterion.witness}'s "
                    f"mutant — {tests_result.summary}"
                ),
            )
        if tests_result.status == "fail":
            died.append(criterion.witness)
            tool = tool or tests_result.tool
            continue
        if tests_result.status == "pass":
            survived.append(
                Failure(
                    file=criterion.witness,
                    code="survived-mutant",
                    message=(
                        f"ran and passed with its mutant applied — {criterion.claim} "
                        f"(mutant: {mutant.find!r} -> {mutant.replace!r} in {mutant.file})"
                    ),
                )
            )
            tool = tool or tests_result.tool
            continue
        # `skip`, or any other status: no trustworthy verdict was produced,
        # which is not evidence the witness guards its claim — the same
        # non-answer as a mutant that never applied.
        unproven.append(
            _named(criterion, f"the `tests` gate reported {tests_result.status}")
        )

    note = (
        f" — {len(unproven)} mutant(s) not proven: {', '.join(unproven)}"
        if unproven
        else ""
    )

    if survived:
        return GateResult(
            gate="witness",
            status="fail",
            tool=tool,
            failures=survived,
            summary=(
                f"{len(survived)} of {len(declared)} witness(es) survived their "
                f"own mutant{note}"
            ),
        )
    if died:
        return GateResult(
            gate="witness",
            status="pass",
            tool=tool,
            summary=(
                f"{len(died)} of {len(declared)} witness(es) died under their "
                f"own mutant{note}"
            ),
        )
    return GateResult(
        gate="witness",
        status="skip",
        summary=f"no declared mutant produced a trustworthy verdict{note}",
    )
