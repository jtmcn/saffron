from __future__ import annotations

import contextlib

from saffron.gates.contract import Failure, GateResult
from saffron.gates.core.revert import revert_gate
from saffron.intake import Criterion

_TESTS = "tests/**"


def _tests(*names: str, failed: tuple[str, ...] = ()) -> GateResult:
    """A `tests` gate result the way the repo's own runner reports one:
    `collected` names, `failures[].code` keyed on the ones that failed."""
    return GateResult(
        gate="tests",
        status="fail" if failed else "pass",
        tool="pytest 8.3.2",
        collected=list(names),
        failures=[Failure(file=n, code=n, message="assert") for n in failed],
    )


@contextlib.contextmanager
def _reverted(paths, *, log, fail_on_enter=False, fail_on_exit=False):
    """A fake `reverted` callable's context manager — no worktree, no
    container. Logs enter/exit so a test can prove the restore ran."""
    log.append(("revert", list(paths)))
    if fail_on_enter:
        raise RuntimeError("checkout failed")
    try:
        yield
    finally:
        log.append(("restore", list(paths)))
        if fail_on_exit:
            raise RuntimeError("could not restore")


def _refuse(_paths):
    """A `reverted` fake for the skip tests: nothing is skipped that then
    goes on to touch the worktree."""
    raise AssertionError("nothing to revert; must not attempt it")


def _refuse_run(_subset):
    raise AssertionError("nothing to revert; must not run tests")


def test_a_new_test_that_passes_without_the_source_is_a_failure():
    log: list = []

    def run_tests(subset):
        # The theater case: the new test ran and passed with its own source
        # reverted.
        return _tests(*subset)

    result = revert_gate(
        prior=[_tests("t.py::test_a")],
        results=[_tests("t.py::test_a", "t.py::test_new")],
        acceptance=[],
        changed_files=["pkg/a.py"],
        test_paths=[_TESTS],
        reverted=lambda paths: _reverted(paths, log=log),
        run_tests=run_tests,
    )
    assert result.status == "fail"
    assert [f.file for f in result.failures] == ["t.py::test_new"]
    assert result.failures[0].code == "passed-without-source"
    # And the restore still ran on the passing (green) path, not only the
    # exceptional ones.
    assert ("restore", ["pkg/a.py"]) in log


def test_the_subset_is_the_new_names_and_excludes_a_preserved_witness():
    """`test_kept` is new by plain set arithmetic too — present at head,
    absent at base — but a `preserves` criterion declares it green on both
    sides, and requiring it to fail here would contradict that (§5.4)."""
    captured: list[list[str]] = []

    def run_tests(subset):
        captured.append(subset)
        return _tests(*subset, failed=tuple(subset))

    revert_gate(
        prior=[_tests("t.py::test_a")],
        results=[_tests("t.py::test_a", "t.py::test_new", "t.py::test_kept")],
        acceptance=[
            Criterion(claim="unaffected", witness="t.py::test_kept", preserves=True)
        ],
        changed_files=["pkg/a.py"],
        test_paths=[_TESTS],
        reverted=lambda paths: _reverted(paths, log=[]),
        run_tests=run_tests,
    )
    assert captured == [["t.py::test_new"]]


def test_the_source_is_restored_when_the_run_raises():
    log: list = []

    def run_tests(_subset):
        raise RuntimeError("the reverted run crashed")

    result = revert_gate(
        prior=[_tests("t.py::test_a")],
        results=[_tests("t.py::test_a", "t.py::test_new")],
        acceptance=[],
        changed_files=["pkg/a.py"],
        test_paths=[_TESTS],
        reverted=lambda paths: _reverted(paths, log=log),
        run_tests=run_tests,
    )
    assert result.status == "error"
    assert result.status != "fail"
    # The context manager's own `finally` restored the paths even though the
    # body it wrapped raised — worktree.py's guarantee, exercised here
    # through the fake that stands in for it.
    assert ("restore", ["pkg/a.py"]) in log


def test_a_restore_that_failed_is_also_an_error():
    """A tree revert_gate could not restore is `error`, not a quietly dirty
    tree `committed` would blame on the task (§5.4)."""
    result = revert_gate(
        prior=[_tests("t.py::test_a")],
        results=[_tests("t.py::test_a", "t.py::test_new")],
        acceptance=[],
        changed_files=["pkg/a.py"],
        test_paths=[_TESTS],
        reverted=lambda paths: _reverted(paths, log=[], fail_on_exit=True),
        run_tests=lambda subset: _tests(*subset, failed=tuple(subset)),
    )
    assert result.status == "error"


def test_a_checkout_that_failed_is_an_error_not_a_failure():
    result = revert_gate(
        prior=[_tests("t.py::test_a")],
        results=[_tests("t.py::test_a", "t.py::test_new")],
        acceptance=[],
        changed_files=["pkg/a.py"],
        test_paths=[_TESTS],
        reverted=lambda paths: _reverted(paths, log=[], fail_on_enter=True),
        run_tests=_refuse_run,
    )
    assert result.status == "error"
    assert result.status != "fail"


def test_each_kind_of_nothing_to_revert_is_a_skip():
    """Three different nothings, none of them evidence: no names at base, a
    diff that adds no test, and a diff with no source side outside the
    repo's declared test paths. Not `pytest.mark.parametrize` — the witness
    the host checks is this literal node id, and a parametrized test is
    collected only under `[id]`-suffixed names, never the bare one."""
    cases = [
        # No names at base: nothing to subtract from.
        ([], [_tests("t.py::test_a")], ["pkg/a.py"]),
        # A diff that adds no test: the subset is empty.
        ([_tests("t.py::test_a")], [_tests("t.py::test_a")], ["pkg/a.py"]),
        # A diff with no source side outside the repo's declared test paths.
        (
            [_tests("t.py::test_a")],
            [_tests("t.py::test_a", "t.py::test_new")],
            ["tests/test_a.py"],
        ),
    ]
    for prior, results, changed_files in cases:
        result = revert_gate(
            prior=prior,
            results=results,
            acceptance=[],
            changed_files=changed_files,
            test_paths=[_TESTS],
            reverted=_refuse,
            run_tests=_refuse_run,
        )
        assert result.status == "skip"
