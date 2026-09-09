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


def test_a_probe_that_leaves_the_suite_as_it_was_survived():
    """The positive result, and the inversion this module exists for: the tests
    did not notice, which is what the finding claimed."""
    got = probe_check.check_probe(
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
    got = probe_check.check_probe(
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
    got = probe_check.check_probe(
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
    got = probe_check.check_probe(
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
    got = probe_check.check_probe(
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
    got = probe_check.check_probe(
        PROBE,
        baseline=_result("pass"),
        mutate=_applies(),
        run_tests=lambda subset: _result("error"),
    )
    assert got.verdict == "unproven"


def test_a_baseline_that_errored_is_unproven_without_running_the_probe():
    """Nothing to subtract from. Running the probe anyway would compare a real
    result against a non-result."""
    got = probe_check.check_probe(
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
    got = probe_check.check_probe(
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
    got = probe_check.check_probe(
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
    got = probe_check.check_probe(
        PROBE, baseline=baseline, mutate=_applies(), run_tests=lambda subset: mutated
    )
    assert got.verdict == "survived"


def test_a_probe_aimed_at_a_test_file_is_refused_before_it_is_applied():
    """The number would otherwise be satisfiable by construction: the adequacy
    prompt offers an edit "to the source or to the test", and deleting an
    assertion survives trivially. Refused before `mutate`, so nothing is
    written for a question that must not be asked."""
    got = probe_check.check_probe(
        Mutant(file="tests/test_report.py", find="assert head == plain", replace=""),
        baseline=_result("pass"),
        mutate=_applies(),
        run_tests=lambda subset: pytest.fail("must not run a probe aimed at a test"),
        test_paths=("tests/",),
    )
    assert got.verdict == "unproven"
    assert "test" in got.reason


def test_the_whole_suite_is_asked_not_a_subset():
    """A probe's question is whether *anything* notices, unlike `witness_gate`,
    which asks one named witness. A subset here would answer a narrower
    question and read as the broader one."""
    asked: list[list[str]] = []
    probe_check.check_probe(
        PROBE,
        baseline=_result("pass"),
        mutate=_applies(),
        run_tests=lambda subset: (asked.append(subset), _result("pass"))[1],
    )
    assert asked == [[]]
