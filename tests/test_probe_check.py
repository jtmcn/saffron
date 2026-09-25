"""The verdict half of the corpus's second number (the design spec of 2026-09-09).

`probe_check` is where a lens's claim becomes a measurement, so it is where a
wrong answer would be invisible: a probe wrongly read as `survived` inflates
the number the whole exercise exists to produce, and one wrongly read as
`killed` charges a lens for a real vacuity. No cell here — `mutate` and
`run_tests` are the two injected callables, exactly as `witness_gate` takes
them, so every branch is reachable without a container.
"""

from __future__ import annotations

import contextlib
import inspect

import pytest

from saffron import probe as probe_check
from saffron.gates.contract import Failure, GateResult, GateStatus
from saffron.intake import Mutant

PROBE = Mutant(
    file="saffron/report/pr_body.py",
    find="safe = neutralize(text)",
    replace="safe = text",
)


def _result(status: GateStatus, failures: tuple[Failure, ...] = ()) -> GateResult:
    return GateResult(
        gate="tests",
        status=status,
        summary="",
        failures=list(failures),
        tool="pytest 8.0.0",
    )


def test_a_verdict_records_which_suite_answered_it():
    """`survived` means "no new failure against the baseline" — and a suite
    that collected almost nothing is green too.

    Measured, and the reason this exists: the first end-to-end run put the
    in-cell suite at ~14s where the same tree at `f9f007c4` takes 78-87s on
    the host, three times over (`docs/evidence/2026-09-09-adequacy-probe-spike.md`
    and a clean run during review). Nothing in the record could adjudicate
    that, because the verdict kept none of what the gate returned. The gate
    hands back `tool`, `collected` and its own `summary` — pytest's
    "N passed in Xs" line — and the verdict dropped all three.

    Kept from the *mutated* run, not the baseline: it is the run the verdict
    is about, and a probe whose suite shrank between the two is already
    `unproven`.
    """
    answered = GateResult(
        gate="tests",
        status="pass",
        summary="1250 passed, 20 deselected in 13.9s",
        tool="pytest 8.4.1",
        collected=[f"tests/test_x.py::test_{n}" for n in range(1250)],
    )
    got = probe_check.check_probe(
        PROBE,
        baseline=answered,
        mutate=_applies(),
        run_tests=lambda subset: answered,
        test_paths=("tests/**",),
        counted=(),
    )
    assert got.verdict == "survived"
    assert got.tool == "pytest 8.4.1"
    assert got.collected == 1250
    assert got.summary == "1250 passed, 20 deselected in 13.9s"


def test_a_verdict_reached_without_a_suite_records_no_count():
    """`None` is not `0`. A probe refused before any gate ran has no suite to
    describe, and a `collected` of 0 would read as a suite that enumerated
    nothing — which `GateResult`'s own docstring says is a different fact."""
    got = probe_check.check_probe(
        Mutant(file="tests/test_x.py", find="assert x", replace=""),
        baseline=_result("pass"),
        mutate=_applies(),
        run_tests=lambda subset: pytest.fail("must not run"),
        test_paths=("tests/**",),
        counted=(),
    )
    assert got.verdict == "unproven"
    assert (got.tool, got.collected, got.summary) == (None, None, "")


def _fail(name: str) -> Failure:
    return Failure(file="tests/test_report.py", line=1, code=name, message="boom")


def _applies():
    @contextlib.contextmanager
    def mutate(mutant):
        yield None

    return mutate


def _refuses(reason: str):
    @contextlib.contextmanager
    def mutate(mutant):
        yield reason

    return mutate


TEST_PATHS = ("tests/**",)


def _check(probe=PROBE, **kwargs):
    """`check_probe` with the now-required `test_paths` and `counted`
    supplied.

    The defaults live here and never in the code under test: a caller that
    forgets the test-file refusal, or the counted set, must get a
    `TypeError`, not a silent pass. `counted=()` is harmless for every test
    below that does not itself pass one: it only matters once a new failure
    exists, and a test asserting `killed` supplies its own."""
    kwargs.setdefault("test_paths", TEST_PATHS)
    kwargs.setdefault("counted", ())
    return probe_check.check_probe(probe, **kwargs)


def test_a_probe_that_leaves_the_suite_as_it_was_survived():
    """The positive result, and the inversion this module exists for: the tests
    did not notice, which is what the finding claimed."""
    got = _check(
        PROBE,
        baseline=_result("pass"),
        mutate=_applies(),
        run_tests=lambda subset: _result("pass"),
    )
    assert got.verdict == "survived"


def test_a_probe_the_tests_notice_is_killed_and_names_what_failed():
    """A count is not enough. The record has to carry which tests died, because
    telling a real kill from program breakage is a person's call and they
    cannot make it from a number."""
    got = _check(
        PROBE,
        baseline=_result("pass"),
        mutate=_applies(),
        run_tests=lambda subset: _result("fail", (_fail("test_a"), _fail("test_b"))),
        counted={"test_a", "test_b"},
    )
    assert got.verdict == "killed"
    assert got.failures == ("test_a", "test_b")


def test_a_failure_already_at_the_baseline_is_not_a_kill():
    """Baseline subtraction counts. A fixture head carrying one pre-existing
    failure would otherwise read every probe as killed."""
    pre_existing = _result("fail", (_fail("test_flaky"),))
    got = _check(
        PROBE,
        baseline=pre_existing,
        mutate=_applies(),
        run_tests=lambda subset: pre_existing,
    )
    assert got.verdict == "survived"


def test_one_baseline_failure_cancels_one_head_failure_not_all_of_them():
    """Identities collide legitimately, so the subtraction counts rather than
    comparing sets — the opposite rule to `census`, and they sit beside each
    other in `baseline.py` for exactly this reason."""
    got = _check(
        PROBE,
        baseline=_result("fail", (_fail("test_a"),)),
        mutate=_applies(),
        run_tests=lambda subset: _result("fail", (_fail("test_a"), _fail("test_a"))),
        counted={"test_a"},
    )
    assert got.verdict == "killed"
    assert got.failures == ("test_a",)


def test_a_probe_that_did_not_apply_is_unproven_and_says_why():
    """`source_mutated` yields a reason rather than raising for the six cases it
    refuses. None of them is evidence about the lens."""
    got = _check(
        PROBE,
        baseline=_result("pass"),
        mutate=_refuses("find text not found: 'safe = neutralize(text)'"),
        run_tests=lambda subset: pytest.fail(
            "must not run the suite over an unapplied probe"
        ),
    )
    assert got.verdict == "unproven"
    assert "find text not found" in got.reason


def test_a_tests_gate_that_errored_is_unproven_never_survived():
    """`error` is not `fail`, and here it is not `pass` either. A gate that could
    not start has said nothing — and reading it as `survived` would count a
    broken toolchain as a verified vacuity, which is the number inflating
    itself."""
    got = _check(
        PROBE,
        baseline=_result("pass"),
        mutate=_applies(),
        run_tests=lambda subset: _result("error"),
    )
    assert got.verdict == "unproven"


def test_a_baseline_that_errored_is_unproven_without_running_the_probe():
    """Nothing to subtract from. Running the probe anyway would compare a real
    result against a non-result."""
    got = _check(
        PROBE,
        baseline=_result("error"),
        mutate=_applies(),
        run_tests=lambda subset: pytest.fail("must not run without a baseline"),
    )
    assert got.verdict == "unproven"


def test_a_probe_that_moves_the_collection_is_unproven_not_killed():
    """The one mechanical half of the collateral problem. A probe that changes
    what the suite *collects* broke the program at import time, so the
    subtraction is untrustworthy rather than merely non-empty.

    A `fail`, not an `error`, so this reaches the collection check rather than
    stopping at the errored-gate branch above it — otherwise the test would
    pass for the wrong reason and prove nothing about collection at all.
    """
    baseline = _result("pass")
    baseline.collected = ["t.py::a", "t.py::b"]
    mutated = _result("fail", (_fail("t.py::a"),))
    mutated.collected = ["t.py::a"]
    got = _check(
        PROBE, baseline=baseline, mutate=_applies(), run_tests=lambda subset: mutated
    )
    assert got.verdict == "unproven"
    assert "t.py::b" in got.reason


def test_a_suite_that_collected_more_is_not_drift():
    """One-directional, like `census`: a name that stopped being collected is a
    removal, a name that appeared is not. A probe cannot add a test, but a
    parametrised id can shift, and reading that as breakage would report the
    harness's own noise as a refusal."""
    baseline = _result("pass")
    baseline.collected = ["t.py::a"]
    mutated = _result("pass")
    mutated.collected = ["t.py::a", "t.py::b"]
    got = _check(
        PROBE, baseline=baseline, mutate=_applies(), run_tests=lambda subset: mutated
    )
    assert got.verdict == "survived"


def test_a_gate_that_enumerates_nothing_is_not_read_as_a_removal():
    """`None` means the runner does not enumerate; `[]` means it enumerated
    nothing, and `GateResult`'s own docstring says those are not the same fact.
    Neither is evidence that a probe removed a test."""
    baseline = _result("pass")
    baseline.collected = ["t.py::a"]
    mutated = _result("pass")
    mutated.collected = None
    got = _check(
        PROBE, baseline=baseline, mutate=_applies(), run_tests=lambda subset: mutated
    )
    assert got.verdict == "survived"


@pytest.mark.parametrize(
    "spelling",
    [
        "tests/test_report.py",
        "./tests/test_report.py",
        "saffron/../tests/test_report.py",
    ],
)
def test_a_probe_aimed_at_a_test_file_is_refused_before_it_is_applied(spelling):
    """The number would otherwise be satisfiable by construction: the adequacy
    prompt offers an edit "to the source or to the test", and deleting an
    assertion survives trivially. Refused before `mutate`, so nothing is
    written for a question that must not be asked.

    Three spellings, because the path is model-authored and a raw prefix test
    refused only the first. Measured, not reasoned: `ls-tree HEAD -- <path>`
    returns the same blob for all three, so `source_mutated` applies the edit
    either way and a deleted assertion is counted as a verified vacuity.
    """
    got = _check(
        Mutant(file=spelling, find="assert head == plain", replace=""),
        baseline=_result("pass"),
        mutate=_applies(),
        run_tests=lambda subset: pytest.fail("must not run a probe aimed at a test"),
    )
    assert got.verdict == "unproven"
    assert "test" in got.reason


def test_a_probe_naming_a_path_outside_the_tree_never_reaches_the_cell():
    """`_confined`'s refusal, made here so the normalisation above cannot be
    read as a way in: a path that escapes normalises to nothing this module
    can compare against a prefix, so it is `unproven` rather than compared."""
    got = _check(
        Mutant(file="../etc/passwd", find="root", replace="x"),
        baseline=_result("pass"),
        mutate=_applies(),
        run_tests=lambda subset: pytest.fail("must not run an escaping probe"),
    )
    assert got.verdict == "unproven"
    assert "inside the tree" in got.reason


def test_check_probe_refuses_by_reverts_glob_rule_and_on_no_test_paths():
    """`check_probe` refuses on the one rule `revert` uses: `scope.matches`
    over declared globs, on the normalised path, never a prefix and never
    `fnmatch`. It also refuses an empty declaration, in `probe_refusal`'s own
    order. Both are asked before `mutate`, on one call."""
    applied: list[str] = []

    @contextlib.contextmanager
    def _applies_and_records(mutant):
        applied.append(mutant.file)
        yield None

    baseline = _result("pass")

    # `**` covers every spelling of one file beneath it.
    for spelling in (
        "tests/test_report.py",
        "./tests/test_report.py",
        "saffron/../tests/test_report.py",
    ):
        got = probe_check.check_probe(
            Mutant(file=spelling, find="assert x", replace=""),
            baseline=baseline,
            mutate=_applies_and_records,
            run_tests=lambda subset: pytest.fail("must not run"),
            test_paths=("tests/**",),
            counted=(),
        )
        assert got.verdict == "unproven"
        assert "test" in got.reason
    assert applied == []

    # `*` stops at a slash: one directory deeper is not covered, unlike
    # `fnmatch`, which would wrongly refuse it (measured at base).
    got = probe_check.check_probe(
        Mutant(file="tests/sub/x.py", find="a", replace="b"),
        baseline=baseline,
        mutate=_applies_and_records,
        run_tests=lambda subset: _result("pass"),
        test_paths=("tests/*.py",),
        counted=(),
    )
    assert got.verdict == "survived"
    assert applied == ["tests/sub/x.py"]

    # Outside the tree wins over an empty declaration when both are true:
    # the order `probe_refusal` checks them in, pinned rather than incidental.
    got = probe_check.check_probe(
        Mutant(file="../outside.py", find="a", replace="b"),
        baseline=baseline,
        mutate=_applies_and_records,
        run_tests=lambda subset: pytest.fail("must not run"),
        test_paths=(),
        counted=(),
    )
    assert got.verdict == "unproven"
    assert got.reason == "../outside.py is not a relative path inside the tree"
    assert applied == ["tests/sub/x.py"]

    # No declared test paths at all: `revert`'s own refusal, word for word,
    # and every path inside the tree is refused without entering the mutator.
    got = probe_check.check_probe(
        Mutant(file="saffron/x.py", find="a", replace="b"),
        baseline=baseline,
        mutate=_applies_and_records,
        run_tests=lambda subset: pytest.fail("must not run"),
        test_paths=(),
        counted=(),
    )
    assert got.verdict == "unproven"
    assert got.reason == (
        "the repo declares no test paths, so source cannot be told from test"
    )
    assert applied == ["tests/sub/x.py"]

    # A bare `tests` matches only the literal path `tests`, nothing beneath.
    # It refuses nothing there for `revert` either.
    got = probe_check.check_probe(
        Mutant(file="tests/test_report.py", find="a", replace="b"),
        baseline=baseline,
        mutate=_applies_and_records,
        run_tests=lambda subset: _result("pass"),
        test_paths=("tests",),
        counted=(),
    )
    assert got.verdict == "survived"
    assert applied == ["tests/sub/x.py", "tests/test_report.py"]


def test_test_paths_has_no_default_so_forgetting_it_is_a_typeerror():
    """The one guard the design spec calls non-optional. A default of `()`
    turns a caller that forgets it into a pass with no refusal at all, which
    is indistinguishable from a pass where nothing aimed at a test."""
    parameter = inspect.signature(probe_check.check_probe).parameters["test_paths"]
    assert parameter.default is inspect.Parameter.empty


def test_a_tests_gate_that_skipped_is_unproven_never_survived():
    """`skip` is not `pass`. A `tests` gate that skipped ran no suite, so
    reading it as `survived` counts a suite that never executed as a verified
    vacuity — the same inflation the errored-gate branch refuses, and what
    `witness_gate` already says about every status that is not a verdict."""
    got = _check(
        PROBE,
        baseline=_result("pass"),
        mutate=_applies(),
        run_tests=lambda subset: _result("skip"),
    )
    assert got.verdict == "unproven"
    assert "skip" in got.reason


def test_a_baseline_that_skipped_is_unproven_without_running_the_probe():
    """Nothing to subtract from, for the same reason an errored baseline is
    nothing to subtract from: a skipped suite measured no failures, so every
    probe against it would read as a kill of tests that never ran."""
    got = _check(
        PROBE,
        baseline=_result("skip"),
        mutate=_applies(),
        run_tests=lambda subset: pytest.fail("must not run without a baseline"),
    )
    assert got.verdict == "unproven"
    assert "skip" in got.reason


def test_the_whole_suite_is_asked_not_a_subset():
    """A probe's question is whether *anything* notices, unlike `witness_gate`,
    which asks one named witness. A subset here would answer a narrower
    question and read as the broader one."""
    asked: list[list[str]] = []
    _check(
        PROBE,
        baseline=_result("pass"),
        mutate=_applies(),
        run_tests=lambda subset: (asked.append(subset), _result("pass"))[1],
    )
    assert asked == [[]]


def test_a_verdict_records_the_baseline_it_was_subtracted_from():
    """Item 94: a baseline red or skipping in the cell cancels failures a
    record of only the survivors cannot name. The shape is `SA-0063`'s."""
    baseline = GateResult(
        gate="tests",
        status="fail",
        summary="1 failed, 1499 passed, 2 skipped in 14.02s",
        tool="pytest 8.4.1",
        collected=[f"tests/test_x.py::test_{n}" for n in range(1502)],
        failures=[_fail("test_only_red_in_the_cell")],
    )
    got = _check(
        PROBE,
        baseline=baseline,
        mutate=_applies(),
        run_tests=lambda subset: baseline,
    )
    assert got.verdict == "survived"
    assert got.baseline == probe_check.BaselineRecord(
        failures=("test_only_red_in_the_cell",),
        tool="pytest 8.4.1",
        collected=1502,
        summary="1 failed, 1499 passed, 2 skipped in 14.02s",
    )


def test_a_kill_names_the_baselines_failures_beside_the_new_ones():
    """`failures` is what the probe added and the baseline's what was already
    red; item 94 asks whether a cancelled one would have caught the probe."""
    got = _check(
        PROBE,
        baseline=_result("fail", (_fail("test_a"),)),
        mutate=_applies(),
        run_tests=lambda subset: _result("fail", (_fail("test_a"), _fail("test_b"))),
        counted={"test_b"},
    )
    assert got.verdict == "killed"
    assert got.failures == ("test_b",)
    assert got.baseline == probe_check.BaselineRecord(
        ("test_a",), "pytest 8.0.0", None, ""
    )


GREEN = probe_check.BaselineRecord(
    failures=(), tool="pytest 8.0.0", collected=None, summary=""
)


def test_a_green_baseline_records_no_failures_rather_than_none():
    """`()` is a baseline read and green, `None` no baseline in hand.
    Collapsing them reads the baseline pass's ten verdicts as ten green ones."""
    got = _check(
        PROBE,
        baseline=_result("pass"),
        mutate=_applies(),
        run_tests=lambda subset: _result("pass"),
    )
    assert got.verdict == "survived"
    assert got.baseline == GREEN


@pytest.mark.parametrize(
    "probe",
    [
        Mutant(file="tests/test_report.py", find="assert x", replace=""),
        Mutant(file="../outside.py", find="x", replace="y"),
    ],
    ids=["a test file", "outside the tree"],
)
def test_a_probe_refused_before_mutation_still_records_the_baseline_in_hand(probe):
    """`None` means no baseline was in hand, on every path — a refusal that
    dropped one would write a green baseline as never read."""
    got = _check(
        probe,
        baseline=_result("pass"),
        mutate=_applies(),
        run_tests=lambda subset: pytest.fail("must not run a refused probe"),
    )
    assert got.verdict == "unproven"
    assert got.baseline == GREEN


@pytest.mark.parametrize("status", ["error", "skip"])
def test_a_baseline_that_measured_nothing_records_none(status):
    """`error` is not `fail`: a gate that did not run measured no failures,
    so an empty tuple here would read as a baseline that was green."""
    got = _check(
        PROBE,
        baseline=_result(status),
        mutate=_applies(),
        run_tests=lambda subset: pytest.fail("must not run without a baseline"),
    )
    assert got.verdict == "unproven"
    assert got.baseline is None


def test_the_baseline_field_is_additive_and_a_result_built_without_it_stands():
    """`harness/corpus.py`'s callers build a `ProbeResult` positionally from
    three values, and a pass already on disk is re-read that way."""
    built = probe_check.ProbeResult("killed", "2 new failure(s)", ("test_a",))
    assert (built.verdict, built.reason, built.failures) == (
        "killed",
        "2 new failure(s)",
        ("test_a",),
    )
    assert built.baseline is None
    assert built.uncounted == ()


# --- b-19b255: a kill is counted, never any new failure ---

_FORMAT = (
    "tests/test_saffron_gates.py::"
    "test_the_fast_gates_name_their_tool_and_pass_on_a_clean_tree[format]"
)
_ADDED = "tests/test_new_thing.py::test_added"


def _named(status, *codes, collected=(_FORMAT, _ADDED)):
    return GateResult(
        gate="tests",
        status=status,
        tool="pytest 8.0",
        collected=list(collected),
        failures=[Failure(file="t.py", code=code, message="boom") for code in codes],
    )


def test_a_probe_only_an_unadded_test_notices_survives_with_that_failure_beside_it():
    """`check_probe` counts a probe `killed` only when a new failure's `code`
    is one of the names its `counted` argument holds (b-19b255): the format
    test lengthening a probe's line trips is never one of them."""
    counted = {_ADDED}

    only_format = _check(
        PROBE,
        baseline=_named("pass"),
        mutate=_applies(),
        run_tests=lambda subset: _named("fail", _FORMAT),
        counted=counted,
    )
    assert only_format.verdict == "survived"
    assert only_format.failures == ()
    assert only_format.uncounted == (_FORMAT,)

    both_fail = _check(
        PROBE,
        baseline=_named("pass"),
        mutate=_applies(),
        run_tests=lambda subset: _named("fail", _FORMAT, _ADDED),
        counted=counted,
    )
    assert both_fail.verdict == "killed"
    assert both_fail.failures == (_ADDED,)
    assert both_fail.uncounted == (_FORMAT,)

    # The added test was already red at the baseline. The subtraction
    # cancels it, so only the format test is new, and it still survives.
    added_already_red = _check(
        PROBE,
        baseline=_named("fail", _ADDED),
        mutate=_applies(),
        run_tests=lambda subset: _named("fail", _FORMAT, _ADDED),
        counted=counted,
    )
    assert added_already_red.verdict == "survived"
    assert _FORMAT in added_already_red.uncounted


def test_a_new_failure_no_counted_test_can_be_matched_to_is_unproven():
    """`unproven`, never `survived` or `killed`, when a new failure exists
    and none can be matched to a counted test: `counted=None`, or no new
    failure's `code` is in `counted` or among the names the probed run
    collected (b-19b255)."""
    collected_x = _named("pass", collected=("t.py::test_x",))
    run1 = _check(
        PROBE,
        baseline=collected_x,
        mutate=_applies(),
        run_tests=lambda subset: GateResult(
            gate="tests",
            status="fail",
            tool="pytest 8.0",
            collected=["t.py::test_x"],
            failures=[Failure(file="t.py", code="t.py::test_x", message="boom")],
        ),
        counted=None,
    )
    assert run1.verdict == "unproven"
    assert run1.uncounted == ("t.py::test_x",)

    unmatched_baseline = _named("pass", collected=("something_else",))
    run2 = _check(
        PROBE,
        baseline=unmatched_baseline,
        mutate=_applies(),
        run_tests=lambda subset: GateResult(
            gate="tests",
            status="fail",
            tool="pytest 8.0",
            collected=["something_else"],
            failures=[Failure(file="t.py", code="t.py::test_y", message="boom")],
        ),
        counted={"other"},
    )
    assert run2.verdict == "unproven"
    assert run2.uncounted == ("t.py::test_y",)

    run3 = _check(
        PROBE,
        baseline=unmatched_baseline,
        mutate=_applies(),
        run_tests=lambda subset: GateResult(
            gate="tests",
            status="fail",
            tool="pytest 8.0",
            collected=None,
            failures=[Failure(file="t.py", code="t.py::test_y", message="boom")],
        ),
        counted={"other"},
    )
    assert run3.verdict == "unproven"
    assert run3.uncounted == ("t.py::test_y",)

    green = _named("pass", collected=("t.py::test_x",))
    run4 = _check(
        PROBE,
        baseline=green,
        mutate=_applies(),
        run_tests=lambda subset: green,
        counted=None,
    )
    assert run4.verdict == "survived"

    # One unmatched failure does not decide a run alone. The other one here
    # is a name the probed run collected, so the run reads `survived`.
    two_failures = GateResult(
        gate="tests",
        status="fail",
        tool="pytest 8.0",
        collected=["t.py::test_x"],
        failures=[
            Failure(file="t.py", code="t.py::test_x", message="boom"),
            Failure(file="t.py", code="t.py::test_unknown", message="boom"),
        ],
    )
    run5 = _check(
        PROBE,
        baseline=green,
        mutate=_applies(),
        run_tests=lambda subset: two_failures,
        counted={"other"},
    )
    assert run5.verdict == "survived"
    assert set(run5.uncounted) == {"t.py::test_x", "t.py::test_unknown"}


def test_added_tests_are_the_names_collected_at_head_and_not_at_base():
    """`probe.added_tests(base, head)` returns, as a frozenset, the names
    `head` collected that the `tests` result in `base` did not (b-19b255)."""
    base_tests = GateResult(
        gate="tests", status="pass", tool="pytest 8.0", collected=["a"]
    )
    head = GateResult(
        gate="tests", status="pass", tool="pytest 8.0", collected=["a", "b"]
    )
    assert probe_check.added_tests([base_tests], head) == frozenset({"b"})

    # A name collected only at base is not in it.
    only_at_base = GateResult(
        gate="tests", status="pass", tool="pytest 8.0", collected=["a", "c"]
    )
    assert probe_check.added_tests([only_at_base], head) == frozenset({"b"})

    # A base `tests` result that collected `[]` makes every head name added.
    empty_base = GateResult(
        gate="tests", status="pass", tool="pytest 8.0", collected=[]
    )
    assert probe_check.added_tests([empty_base], head) == frozenset({"a", "b"})

    # A result in `base` from any other gate is not read.
    other_gate = GateResult(
        gate="lint", status="pass", tool="ruff 1.0", collected=["a"]
    )
    assert probe_check.added_tests([other_gate], head) is None

    # `None` in three cases: no `tests` result in `base`, that result's
    # `collected` is `None`, or `head.collected` is `None`.
    assert probe_check.added_tests([], head) is None
    no_collected = GateResult(gate="tests", status="skip", tool=None, collected=None)
    assert probe_check.added_tests([no_collected], head) is None
    unreadable_head = GateResult(
        gate="tests", status="pass", tool="pytest 8.0", collected=None
    )
    assert probe_check.added_tests([base_tests], unreadable_head) is None
