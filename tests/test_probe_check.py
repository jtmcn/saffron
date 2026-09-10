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

from harness import probe_check
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
        test_paths=("tests/",),
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
        test_paths=("tests/",),
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


TEST_PATHS = ("tests/",)


def _check(probe=PROBE, **kwargs):
    """`check_probe` with the now-required `test_paths` supplied.

    The default lives here and never in the code under test: a caller that
    forgets the test-file refusal must get a `TypeError`, not a silent pass.
    """
    kwargs.setdefault("test_paths", TEST_PATHS)
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
