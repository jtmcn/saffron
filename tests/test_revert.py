from __future__ import annotations

import contextlib

from saffron.gates.contract import Failure, GateResult
from saffron.gates.core.revert import revert_gate
from saffron.intake import Criterion

_TESTS = "tests/**"


def _tests(*names: str, failed: tuple[str, ...] = ()) -> GateResult:
    """A `tests` gate result keyed the way the repo's runner keys one on its
    *fallback* path: `failures[].code` is the failing test's node id.

    This is the shape every fixture here used to build, and building only it
    is why a missing readability guard passed the whole suite. `_tests_keyed_
    elsewhere` below is the runner's common path, which is the one that
    breaks the naive verdict.
    """
    return GateResult(
        gate="tests",
        status="fail" if failed else "pass",
        tool="pytest 8.3.2",
        collected=list(names),
        failures=[Failure(file=n, code=n, message="assert") for n in failed],
    )


def _tests_keyed_elsewhere(*names: str, failed: tuple[str, ...] = ()) -> GateResult:
    """The same run as `_tests`, reported the way this repo's own `tests` gate
    reports it on its *common* path: one `path:line: word: message` line
    anywhere in the output satisfies its regex, and every `failures[].code` is
    then the caught exception type rather than a node id. `test_criteria.py`'s
    `keyed_elsewhere` fixture is the same shape, for the same reason."""
    return GateResult(
        gate="tests",
        status="fail" if failed else "pass",
        tool="pytest 8.3.2",
        collected=list(names),
        failures=[
            Failure(file=n, code="AssertionError", message="assert") for n in failed
        ],
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


def test_a_reverted_run_keyed_on_exception_types_is_a_skip_not_a_failure():
    """The blocker `criteria._side` exists to prevent, in this gate's own
    direction. The reverted test *did* fail — correctly, it depends on its
    source — but the runner keyed the failure on `AssertionError`, so the
    naive membership test finds the node id in `collected`, does not find it
    in `failed`, and reports theatre. A false `fail` here calls a correct test
    fraudulent and blocks the spec that shipped it, which is the expensive
    direction; `skip` is what `criteria` degrades to on the same unreadable
    field, and it is what this must do."""

    def run_tests(subset):
        return _tests_keyed_elsewhere(*subset, failed=tuple(subset))

    result = revert_gate(
        prior=[_tests("t.py::test_a")],
        results=[_tests("t.py::test_a", "t.py::test_new")],
        acceptance=[],
        changed_files=["pkg/a.py"],
        test_paths=[_TESTS],
        reverted=lambda paths: _reverted(paths, log=[]),
        run_tests=run_tests,
    )
    assert result.status == "skip", result
    assert "node id" in result.summary


def test_a_reverted_run_that_did_not_enumerate_is_a_skip():
    """`collected is None` is the runner not enumerating at all, which is
    unreadable. It is not the same fact as enumerating and finding nothing —
    that is the ordinary answer when every reverted test dies at import, and
    it stays a `pass`."""

    def run_tests(subset):
        return GateResult(
            gate="tests", status="pass", tool="pytest 8.3.2", collected=None
        )

    result = revert_gate(
        prior=[_tests("t.py::test_a")],
        results=[_tests("t.py::test_a", "t.py::test_new")],
        acceptance=[],
        changed_files=["pkg/a.py"],
        test_paths=[_TESTS],
        reverted=lambda paths: _reverted(paths, log=[]),
        run_tests=run_tests,
    )
    assert result.status == "skip", result


def test_a_reverted_run_that_enumerated_nothing_still_passes():
    """The distinction the guard must not collapse: `collected == []` is
    readable. Every new test vanishing from collection is exactly what a
    reverted source produces when the tests cannot import, and it is the
    gate's own success condition — not something to skip."""

    def run_tests(subset):
        return GateResult(
            gate="tests", status="fail", tool="pytest 8.3.2", collected=[]
        )

    result = revert_gate(
        prior=[_tests("t.py::test_a")],
        results=[_tests("t.py::test_a", "t.py::test_new")],
        acceptance=[],
        changed_files=["pkg/a.py"],
        test_paths=[_TESTS],
        reverted=lambda paths: _reverted(paths, log=[]),
        run_tests=run_tests,
    )
    assert result.status == "pass", result


def test_a_reverted_run_that_could_not_produce_a_result_is_a_skip_not_an_error():
    """The gate's own canonical case, and `error` here ended the whole task.

    `DESIGN.md` §5.4: *"a spec that lands source and tests together makes every
    new test fail for the trivial reason and `revert` reports green."* Measured
    on this repo's own `.saffron/gates/tests.py`: removing the module makes the
    new tests fail to *import*, pytest exits on a collection error, no line
    matches the gate's `path:line: word: message` regex and none carries the
    `FAILED ` its fallback reads — so the gate reports `error`, not `fail`.
    Mapped to `error` here it reached `session.aborted_gates`, which ends the
    attempt: the gate would have killed every spec that ships a module with its
    tests, which is most of them, and this one.
    """

    def run_tests(_subset):
        return GateResult(
            gate="tests",
            status="error",
            tool="pytest 8.3.2",
            summary="pytest exited 2 with no parsed failures",
        )

    result = revert_gate(
        prior=[_tests("t.py::test_a")],
        results=[_tests("t.py::test_a", "t.py::test_new")],
        acceptance=[],
        changed_files=["pkg/a.py"],
        test_paths=[_TESTS],
        reverted=lambda paths: _reverted(paths, log=[]),
        run_tests=run_tests,
    )
    assert result.status == "skip", result
    assert result.status != "error", "an untrustworthy result ends the attempt"


def test_a_repo_that_declares_no_test_paths_is_a_skip_and_never_reverts():
    """`policy.integrity.test_paths` defaults to `[]`. With none declared every
    changed file reads as source, so the gate would revert the very tests it is
    about to run — and must not touch the worktree at all."""
    log: list = []

    result = revert_gate(
        prior=[_tests("t.py::test_a")],
        results=[_tests("t.py::test_a", "t.py::test_new")],
        acceptance=[],
        changed_files=["pkg/a.py", "t.py"],
        test_paths=[],
        reverted=lambda paths: _reverted(paths, log=log),
        run_tests=lambda _s: _tests(),
    )
    assert result.status == "skip", result
    assert log == [], "nothing may be reverted when source cannot be identified"


def test_the_verdict_is_scoped_to_the_subset_not_the_whole_enumeration():
    """A repo's `tests` gate is contractually asked for a subset, but nothing
    stops it running the whole suite. The verdict must still be about the new
    names only — judging every collected name would fail the task for every
    pre-existing test that passes, which is all of them."""

    def run_tests(_subset):
        # Ignores its argument, as a mis-implemented repo gate would.
        return _tests("t.py::test_a", "t.py::test_new", failed=("t.py::test_new",))

    result = revert_gate(
        prior=[_tests("t.py::test_a")],
        results=[_tests("t.py::test_a", "t.py::test_new")],
        acceptance=[],
        changed_files=["pkg/a.py"],
        test_paths=[_TESTS],
        reverted=lambda paths: _reverted(paths, log=[]),
        run_tests=run_tests,
    )
    assert result.status == "pass", result


def test_the_tool_is_the_one_that_actually_ran():
    """§5.4 and Appendix H: a pass without `tool` is indistinguishable from a
    gate that never ran, and this gate — unlike `census`/`criteria` — does
    execute one."""

    def run_tests(subset):
        return _tests(*subset, failed=tuple(subset))

    result = revert_gate(
        prior=[_tests("t.py::test_a")],
        results=[_tests("t.py::test_a", "t.py::test_new")],
        acceptance=[],
        changed_files=["pkg/a.py"],
        test_paths=[_TESTS],
        reverted=lambda paths: _reverted(paths, log=[]),
        run_tests=run_tests,
    )
    assert result.status == "pass"
    assert result.tool == "pytest 8.3.2"


def test_a_declared_witness_joins_the_subset_even_when_it_existed_at_base():
    """The second half of the spec's subset claim. `criteria._judge` requires a
    non-`preserves` witness to be *not* green at base, so a criterion naming a
    test that already existed there is claiming this change is what makes it
    pass — and whether it passes without the source is exactly this gate's
    question. The set difference alone never reaches it, because the name is on
    both sides."""

    def run_tests(subset):
        # Theatre: the declared witness passes with its source reverted.
        return _tests(*subset)

    result = revert_gate(
        prior=[_tests("t.py::test_w")],
        results=[_tests("t.py::test_w")],
        acceptance=[Criterion(claim="it works", witness="t.py::test_w")],
        changed_files=["pkg/a.py"],
        test_paths=[_TESTS],
        reverted=lambda paths: _reverted(paths, log=[]),
        run_tests=run_tests,
    )
    assert result.status == "fail", result
    assert [f.file for f in result.failures] == ["t.py::test_w"]


def test_a_declared_witness_the_head_run_never_collected_is_not_asserted():
    """`declared & set(after)`, not `declared`: a witness no runner enumerated
    at head is a `criteria` failure to report, not a name this gate may claim
    ran and passed. Reverting for it would ask the runner about a test that
    does not exist."""
    log: list = []

    result = revert_gate(
        prior=[_tests("t.py::test_a")],
        results=[_tests("t.py::test_a")],
        acceptance=[Criterion(claim="it works", witness="t.py::nonexistent")],
        changed_files=["pkg/a.py"],
        test_paths=[_TESTS],
        reverted=lambda paths: _reverted(paths, log=log),
        run_tests=lambda _s: _tests(),
    )
    assert result.status == "skip", result
    assert log == [], "an unenumerated witness must not reach the worktree"
