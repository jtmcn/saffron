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
        dirty=lambda: [],
        reverted=lambda paths: _reverted(paths, log=log),
        run_tests=run_tests,
        exempt=[],
        diff="",
    )
    assert result.status == "fail"
    assert [f.file for f in result.failures] == ["t.py::test_new"]
    assert result.failures[0].code == "passed-without-source"
    # §5.4 / Appendix H: obtained from the run that happened, on this branch as
    # much as on the passing one — a verdict without it reads as a gate that
    # never ran.
    assert result.tool == "pytest 8.3.2"
    # Pinned to the exact string, not a substring: with no `uncollected`
    # reported, nothing here appends to it (backlog items 50/51).
    assert result.summary == "1 of 1 new test(s) passed without their source"
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
        dirty=lambda: [],
        reverted=lambda paths: _reverted(paths, log=[]),
        run_tests=run_tests,
        exempt=[],
        diff="",
    )
    assert captured == [["t.py::test_new"]]


def test_a_collected_name_that_reads_as_an_option_never_reaches_the_runner():
    """This gate is the one place a `collected` name is *executed* rather than
    compared: `run_gate` builds `argv = [executable, *subset]` with no `--`.
    This repo's own `tests` gate calls any collection line holding `::` a name,
    so a line printed at import time can read as an option — and
    `--deselect=t.py::test_new` is new at head, joins the subset, and deselects
    the one test the gate is asking about. The theater case then reports
    `pass`, silently, at the hands of the thing the gate is watching.

    Dropped rather than skipped on: a `skip` is what one such line would be
    buying, and disabling the gate outright is worth more to an agent than
    hiding one test."""
    captured: list[list[str]] = []

    def run_tests(subset):
        captured.append(subset)
        return _tests(*subset, failed=tuple(subset))

    result = revert_gate(
        prior=[_tests("t.py::test_a")],
        results=[_tests("t.py::test_a", "t.py::test_new", "--deselect=t.py::test_new")],
        acceptance=[],
        changed_files=["pkg/a.py"],
        test_paths=[_TESTS],
        dirty=lambda: [],
        reverted=lambda paths: _reverted(paths, log=[]),
        run_tests=run_tests,
        exempt=[],
        diff="",
    )
    assert captured == [["t.py::test_new"]]
    # And the real name is still judged — the drop narrows the subset, it does
    # not cost the gate its verdict.
    assert result.status == "pass"
    # Reported, not silently swallowed: a name shaped like an option is the one
    # sign the operator gets that something in the cell printed a collection
    # line it had no business printing, and the verdict alone does not carry it.
    assert "--deselect=t.py::test_new" in result.summary


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
        dirty=lambda: [],
        reverted=lambda paths: _reverted(paths, log=log),
        run_tests=run_tests,
        exempt=[],
        diff="",
    )
    assert result.status == "error"
    assert result.status != "fail"
    # A run that raised and a checkout that never happened are both `error`,
    # and the operator is sent to a different subsystem by each. The messages
    # are the only thing that distinguishes them, so they are asserted rather
    # than assumed — the code spends its longest comment on keeping them apart.
    assert "could not be executed" in result.summary
    # And the exception itself, not only the prefix: dropping what was caught
    # leaves the prefix standing and the operator holding "— None".
    assert "the reverted run crashed" in result.summary
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
        dirty=lambda: [],
        reverted=lambda paths: _reverted(paths, log=[], fail_on_exit=True),
        run_tests=lambda subset: _tests(*subset, failed=tuple(subset)),
        exempt=[],
        diff="",
    )
    assert result.status == "error"


def test_a_checkout_that_failed_is_an_error_not_a_failure():
    result = revert_gate(
        prior=[_tests("t.py::test_a")],
        results=[_tests("t.py::test_a", "t.py::test_new")],
        acceptance=[],
        changed_files=["pkg/a.py"],
        test_paths=[_TESTS],
        dirty=lambda: [],
        reverted=lambda paths: _reverted(paths, log=[], fail_on_enter=True),
        run_tests=_refuse_run,
        exempt=[],
        diff="",
    )
    assert result.status == "error"
    assert result.status != "fail"
    assert "could not revert or restore" in result.summary
    assert "checkout failed" in result.summary


def test_each_kind_of_nothing_to_revert_is_a_skip():
    """Four different nothings, none of them evidence: no names at base, none
    at head, a diff that adds no test, and a diff with no source side outside
    the repo's declared test paths. Not `pytest.mark.parametrize` — the witness
    the host checks is this literal node id, and a parametrized test is
    collected only under `[id]`-suffixed names, never the bare one."""
    cases = [
        # No names at base: nothing to subtract from.
        ([], [_tests("t.py::test_a")], ["pkg/a.py"], "no readable test enumeration"),
        # None at head, which is not symmetry for its own sake: this repo's
        # `tests` gate reports `collected: null` on every one of its `error`
        # paths, and `run_gate` synthesizes the same for its own failures. The
        # gate is called inside `_suite` before `aborted_gates` is consulted,
        # so a head `tests` error reaches it — and without this half of the
        # guard `set(None)` raises out of the supervisor and exits 2.
        (
            [_tests("t.py::test_a")],
            [GateResult(gate="tests", status="error", summary="pytest exploded")],
            ["pkg/a.py"],
            "no readable test enumeration",
        ),
        # A diff that adds no test: the subset is empty.
        (
            [_tests("t.py::test_a")],
            [_tests("t.py::test_a")],
            ["pkg/a.py"],
            "adds no new test",
        ),
        # A diff with no source side outside the repo's declared test paths.
        (
            [_tests("t.py::test_a")],
            [_tests("t.py::test_a", "t.py::test_new")],
            ["tests/test_a.py"],
            "no source outside",
        ),
    ]
    # Each case is asserted on its own summary as well as its status: `skip` is
    # the answer to all three, so a status alone cannot tell a case reaching the
    # right verdict by the wrong route from one reaching it by the right one.
    for prior, results, changed_files, summary in cases:
        result = revert_gate(
            prior=prior,
            results=results,
            acceptance=[],
            changed_files=changed_files,
            test_paths=[_TESTS],
            dirty=lambda: [],
            reverted=_refuse,
            run_tests=_refuse_run,
            exempt=[],
            diff="",
        )
        assert result.status == "skip", result
        assert summary in result.summary, result


def test_a_reverted_run_keyed_on_exception_types_is_a_skip_not_a_failure():
    """The blocker `criteria._side` exists to prevent, in this gate's own
    direction. The reverted test *did* fail — correctly, it depends on its
    source — but the runner keyed the failure on `AssertionError`, so the
    naive membership test finds the node id in `collected`, does not find it
    in `failed`, and reports theater. A false `fail` here calls a correct test
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
        dirty=lambda: [],
        reverted=lambda paths: _reverted(paths, log=[]),
        run_tests=run_tests,
        exempt=[],
        diff="",
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
        dirty=lambda: [],
        reverted=lambda paths: _reverted(paths, log=[]),
        run_tests=run_tests,
        exempt=[],
        diff="",
    )
    assert result.status == "skip", result
    assert "no collected tests" in result.summary


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
        dirty=lambda: [],
        reverted=lambda paths: _reverted(paths, log=[]),
        run_tests=run_tests,
        exempt=[],
        diff="",
    )
    assert result.status == "pass", result
    # Pinned to the exact string, not a substring: with no `uncollected`
    # reported, nothing here appends to it (backlog items 50/51).
    assert result.summary == "1 new test(s) failed without their source, as required"


def test_a_reverted_run_that_could_not_produce_a_result_is_a_skip_not_an_error():
    """The gate's own canonical case, and `error` here ended the whole task.

    `DESIGN.md` §5.4: *"a spec that lands source and tests together makes every
    new test fail for the trivial reason and `revert` reports green."* Measured
    on this repo's own `.saffron/gates/tests.py`: removing the module makes the
    new tests fail to *import*, pytest exits on a collection error, no line
    matches the gate's `path:line: word: message` regex and none carries the
    `FAILED ` its fallback reads — so the gate reports `error`, not `fail`.
    Mapped to `error` here it reached `suite.aborted_gates`, which ends the
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
        dirty=lambda: [],
        reverted=lambda paths: _reverted(paths, log=[]),
        run_tests=run_tests,
        exempt=[],
        diff="",
    )
    assert result.status == "skip", result
    assert result.status != "error", "an untrustworthy result ends the attempt"
    # The summary, not only the status: three skips sit between this branch and
    # the verdict, and a mutant reaching one of the others reaches `skip` too.
    assert "no readable verdict" in result.summary


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
        dirty=lambda: [],
        reverted=lambda paths: _reverted(paths, log=log),
        run_tests=lambda _s: _tests(),
        exempt=[],
        diff="",
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
        dirty=lambda: [],
        reverted=lambda paths: _reverted(paths, log=[]),
        run_tests=run_tests,
        exempt=[],
        diff="",
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
        dirty=lambda: [],
        reverted=lambda paths: _reverted(paths, log=[]),
        run_tests=run_tests,
        exempt=[],
        diff="",
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
        dirty=lambda: [],
        reverted=lambda paths: _reverted(paths, log=[]),
        run_tests=run_tests,
        exempt=[],
        diff="",
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
        dirty=lambda: [],
        reverted=lambda paths: _reverted(paths, log=log),
        run_tests=lambda _s: _tests(),
        exempt=[],
        diff="",
    )
    assert result.status == "skip", result
    assert log == [], "an unenumerated witness must not reach the worktree"


def test_uncommitted_work_on_a_path_this_would_revert_is_a_skip():
    """The guard's own witness, and the reason it exists is destruction rather
    than a wrong verdict. The restore checks out `HEAD`, not the tree as it
    stood a moment ago, so an uncommitted edit to a source path does not
    survive this gate — and `committed` runs immediately after and would then
    report the tree clean, which is the one gate whose whole job is noticing
    that it is not. No evidence about theater is worth that trade."""

    result = revert_gate(
        prior=[_tests("t.py::test_a")],
        results=[_tests("t.py::test_a", "t.py::test_new")],
        acceptance=[],
        changed_files=["pkg/a.py"],
        test_paths=[_TESTS],
        dirty=lambda: ["pkg/a.py"],
        # Never entered: refusing is how this proves the worktree was untouched.
        reverted=_refuse,
        run_tests=_refuse_run,
        exempt=[],
        diff="",
    )
    assert result.status == "skip", result
    assert "pkg/a.py" in result.summary


def test_uncommitted_work_somewhere_else_does_not_stop_the_gate():
    """The other side of the same operator. A guard that skipped on *any* dirty
    path would silence the gate on almost every attempt — the agent's tree is
    dirty by construction while it works — and inverting the set operation is a
    one-character slip that leaves the whole suite green."""
    log: list = []

    def run_tests(subset):
        return _tests(*subset, failed=tuple(subset))

    result = revert_gate(
        prior=[_tests("t.py::test_a")],
        results=[_tests("t.py::test_a", "t.py::test_new")],
        acceptance=[],
        changed_files=["pkg/a.py"],
        test_paths=[_TESTS],
        dirty=lambda: ["docs/unrelated.md", "tests/test_new.py"],
        reverted=lambda paths: _reverted(paths, log=log),
        run_tests=run_tests,
        exempt=[],
        diff="",
    )
    assert result.status == "pass", result
    assert ("revert", ["pkg/a.py"]) in log


def test_the_dirty_read_happens_before_anything_is_reverted():
    """Ordering, not just presence: read after the restore and it always sees a
    clean tree, so the guard would be dead code that still passes both tests
    above."""
    order: list = []

    def dirty():
        order.append("dirty")
        return []

    def reverted(paths):
        order.append("revert")
        return _reverted(paths, log=[])

    revert_gate(
        prior=[_tests("t.py::test_a")],
        results=[_tests("t.py::test_a", "t.py::test_new")],
        acceptance=[],
        changed_files=["pkg/a.py"],
        test_paths=[_TESTS],
        dirty=dirty,
        reverted=reverted,
        run_tests=lambda subset: _tests(*subset, failed=tuple(subset)),
        exempt=[],
        diff="",
    )
    assert order == ["dirty", "revert"]


def test_a_witness_whose_subject_the_diff_never_touched_is_skipped():
    """BACKLOG item 84, and the first finding this repo received through the
    notes channel rather than from a lens or a person.

    `SA-0064`'s criterion 2 was a deliberate coverage backfill for a predicate
    in `saffron/cell/session.py`, a file that spec `forbids`; only
    `saffron/phases/package.py` was in `touches`. The new test therefore
    depended on none of the diff's own source, `revert` called that theater,
    and the workaround shipped: the test now stands up a real git remote so it
    depends on both, leaving a test of one boolean predicate driving a network
    to satisfy a gate.

    "This diff could not have made that test pass, because it never touched the
    code the claim is about" is unproven, not theater, and `skip` already means
    that. The mutant's file is compared against `source`, the exact set about
    to be reverted, rather than against `touches`. A spec permitted to change
    a file it then left alone leaves `revert` equally unable to answer. A
    criterion with no mutant names no subject and stays judged as before. A
    criterion whose declared `subject` reaches `source` stays judged too."""
    witness = "tests/test_report.py::test_effective_tier"
    criterion = Criterion(
        claim="a task that recorded nothing packages the body it packages today",
        witness=witness,
        mutant={"file": "saffron/cell/session.py", "find": "a", "replace": "b"},
    )

    result = revert_gate(
        prior=[_tests("t.py::test_a")],
        results=[_tests("t.py::test_a", witness)],
        acceptance=[criterion],
        changed_files=["saffron/phases/package.py"],
        test_paths=[_TESTS],
        dirty=lambda: [],
        reverted=_refuse,
        run_tests=_refuse_run,
        exempt=[],
        diff="",
    )
    assert result.status == "skip"
    assert "session.py" in result.summary


def test_a_witness_whose_subject_the_diff_did_touch_is_still_judged():
    """The guard above must not swallow the case the gate exists for."""
    log: list = []
    witness = "t.py::test_new"
    criterion = Criterion(
        claim="the total is clamped",
        witness=witness,
        mutant={"file": "pkg/a.py", "find": "a", "replace": "b"},
    )

    result = revert_gate(
        prior=[_tests("t.py::test_a")],
        results=[_tests("t.py::test_a", witness)],
        acceptance=[criterion],
        changed_files=["pkg/a.py"],
        test_paths=[_TESTS],
        dirty=lambda: [],
        reverted=lambda paths: _reverted(paths, log=log),
        run_tests=lambda subset: _tests(*subset),
        exempt=[],
        diff="",
    )
    assert result.status == "fail"
    assert [f.file for f in result.failures] == [witness]


def test_a_mutant_naming_a_test_file_does_not_exempt_its_witness():
    """The exemption above must not be buyable with one line of frontmatter.

    `source` excludes the repo's declared test paths wholesale, so a subject
    inside them is outside `source` for every diff there will ever be. Read
    naively that makes such a witness permanently unreachable and permanently
    skipped — a standing pass from the anti-theater gate, bought by pointing
    `mutant.file` at a test. `_argv_safe` above names the same buyable-`skip`
    shape from the other direction. The subject being a test says nothing
    about whether the witness leans on the source being reverted, so it is
    still judged, and here it is theater and reported as such.
    """
    witness = "t.py::test_new"
    criterion = Criterion(
        claim="the total is clamped",
        witness=witness,
        mutant={"file": "tests/test_thing.py", "find": "a", "replace": "b"},
    )

    result = revert_gate(
        prior=[_tests("t.py::test_a")],
        results=[_tests("t.py::test_a", witness)],
        acceptance=[criterion],
        changed_files=["pkg/a.py"],
        test_paths=[_TESTS],
        dirty=lambda: [],
        reverted=lambda paths: _reverted(paths, log=[]),
        run_tests=lambda subset: _tests(*subset),
        exempt=[],
        diff="",
    )
    assert result.status == "fail"
    assert [f.file for f in result.failures] == [witness]


_CHANGED = "pkg/a.py"
_UNTOUCHED = "pkg/untouched.py"
_UNTOUCHED_2 = "pkg/other_untouched.py"
_TEST_FILE = "tests/test_thing.py"


def _subject_criterion(witness, *, mutant_file, find, subject=None):
    kwargs = {"file": mutant_file, "find": find, "replace": "y"}
    return Criterion(claim="c", witness=witness, mutant=kwargs, subject=subject)


def test_a_witness_whose_declared_subject_the_diff_changed_is_judged_and_named():
    """Backlog item b-000d04, narrowing item 84. A mutant sitting outside
    the diff no longer sets a witness aside on its own. A declared
    `subject` reaching the source keeps it judged."""
    witness = "t.py::test_new"

    def run(*, subject, failed):
        criterion = _subject_criterion(
            witness, mutant_file=_UNTOUCHED, find="m1", subject=subject
        )
        return revert_gate(
            prior=[_tests("t.py::test_a")],
            results=[_tests("t.py::test_a", witness)],
            acceptance=[criterion],
            changed_files=[_CHANGED],
            test_paths=[_TESTS],
            dirty=lambda: [],
            reverted=lambda paths: _reverted(paths, log=[]),
            run_tests=lambda subset: _tests(*subset, failed=failed),
            exempt=[],
            diff="",
        )

    # A subject the diff changed keeps the witness judged, and theater here
    # is still theater: the reverted run passes it.
    result = run(subject=_CHANGED, failed=())
    assert result.status == "fail"
    assert [f.file for f in result.failures] == [witness]
    assert witness in result.summary and _CHANGED in result.summary

    # A subject under the repo's own test paths reaches the source too.
    result = run(subject=_TEST_FILE, failed=())
    assert result.status == "fail"
    assert _TEST_FILE in result.summary

    # The same witness truly depends on its subject here. The reverted run
    # fails it, and the subject is still named on a pass verdict.
    result = run(subject=_CHANGED, failed=(witness,))
    assert result.status == "pass"
    assert witness in result.summary and _CHANGED in result.summary

    # A lone criterion with no subject at all is set aside as at base, and
    # names no "subject" anywhere in its summary.
    lone = Criterion(
        claim="c", witness=witness, mutant={"file": _UNTOUCHED, "find": "m2"}
    )
    result = revert_gate(
        prior=[_tests("t.py::test_a")],
        results=[_tests("t.py::test_a", witness)],
        acceptance=[lone],
        changed_files=[_CHANGED],
        test_paths=[_TESTS],
        dirty=lambda: [],
        reverted=_refuse,
        run_tests=_refuse_run,
        exempt=[],
        diff="",
    )
    assert result.status == "skip"
    assert witness in result.summary and _UNTOUCHED in result.summary
    assert "subject" not in result.summary

    # Only the first is kept by its subject and named. The fifth is never
    # collected, and the sixth is named by its mutant's file.
    w = [f"t.py::test_c{i}" for i in range(1, 7)]
    criteria = [
        _subject_criterion(w[0], mutant_file=_UNTOUCHED, find="a1", subject=_CHANGED),
        _subject_criterion(w[1], mutant_file=_CHANGED, find="a2", subject=_CHANGED),
        _subject_criterion(w[2], mutant_file=_TEST_FILE, find="a3", subject=_CHANGED),
        _subject_criterion(w[3], mutant_file=_CHANGED, find="a4"),
        _subject_criterion(w[4], mutant_file=_UNTOUCHED, find="a5", subject=_CHANGED),
        _subject_criterion(
            w[5], mutant_file=_UNTOUCHED, find="a6", subject=_UNTOUCHED_2
        ),
    ]
    collected = [w[0], w[1], w[2], w[3], w[5]]
    result = revert_gate(
        prior=[_tests("t.py::test_a")],
        results=[_tests("t.py::test_a", *collected)],
        acceptance=criteria,
        changed_files=[_CHANGED],
        test_paths=[_TESTS],
        dirty=lambda: [],
        reverted=lambda paths: _reverted(paths, log=[]),
        run_tests=lambda subset: _tests(*subset),
        exempt=[],
        diff="",
    )
    assert result.status == "fail"
    assert sorted(f.file for f in result.failures) == sorted(w[:4])
    assert w[0] in result.summary
    for name in w[1:5]:
        assert name not in result.summary
    assert _UNTOUCHED_2 not in result.summary


def test_a_witness_is_set_aside_only_when_its_mutant_and_its_subject_lie_outside_the_source():
    """The full twelve-pair grid (backlog item b-000d04). Only a mutant
    outside `source` and the test paths is set aside, and only when its
    `subject` is absent or also outside both."""
    mutant_files = {"source": _CHANGED, "outside": _UNTOUCHED, "tests": _TEST_FILE}
    subjects = {
        "absent": None,
        "source": _CHANGED,
        "outside": _UNTOUCHED_2,
        "tests": _TEST_FILE,
    }
    aside_pairs = {("outside", "absent"), ("outside", "outside")}
    for mutant_key, mutant_file in mutant_files.items():
        for subject_key, subject in subjects.items():
            witness = f"t.py::test_{mutant_key}_{subject_key}"
            criterion = _subject_criterion(
                witness,
                mutant_file=mutant_file,
                find=f"m_{mutant_key}_{subject_key}",
                subject=subject,
            )
            result = revert_gate(
                prior=[_tests("t.py::test_a")],
                results=[_tests("t.py::test_a", witness)],
                acceptance=[criterion],
                changed_files=[_CHANGED],
                test_paths=[_TESTS],
                dirty=lambda: [],
                reverted=lambda paths: _reverted(paths, log=[]),
                run_tests=lambda subset: _tests(*subset),
                exempt=[],
                diff="",
            )
            pair = (mutant_key, subject_key)
            if pair in aside_pairs:
                assert result.status == "skip", pair
                assert witness in result.summary
            else:
                assert result.status == "fail", pair
                assert [f.file for f in result.failures] == [witness]


def test_a_witness_two_criteria_disagree_on_stays_set_aside():
    """A witness any criterion sets aside is never named as kept, even
    where another of its criteria declares a `subject` in `source`."""
    witness = "t.py::test_shared"
    aside_criterion = _subject_criterion(witness, mutant_file=_UNTOUCHED, find="s1")
    kept_criterion = _subject_criterion(
        witness, mutant_file=_UNTOUCHED, find="s2", subject=_CHANGED
    )

    result = revert_gate(
        prior=[_tests("t.py::test_a")],
        results=[_tests("t.py::test_a", witness)],
        acceptance=[aside_criterion, kept_criterion],
        changed_files=[_CHANGED],
        test_paths=[_TESTS],
        dirty=lambda: [],
        reverted=_refuse,
        run_tests=_refuse_run,
        exempt=[],
        diff="",
    )
    assert result.status == "skip"
    assert witness in result.summary
    assert _CHANGED not in result.summary


def test_a_witness_two_subjects_keep_is_counted_once():
    """One witness kept through two declared subjects counts as one
    witness, the way the set-aside note counts, and names both."""
    witness = "t.py::test_shared"
    criteria = [
        _subject_criterion(witness, mutant_file=_UNTOUCHED, find="k1", subject=s)
        for s in (_CHANGED, _TEST_FILE)
    ]

    result = revert_gate(
        prior=[_tests("t.py::test_a")],
        results=[_tests("t.py::test_a", witness)],
        acceptance=criteria,
        changed_files=[_CHANGED],
        test_paths=[_TESTS],
        dirty=lambda: [],
        reverted=lambda paths: _reverted(paths, log=[]),
        run_tests=lambda subset: _tests(*subset),
        exempt=[],
        diff="",
    )
    assert "1 witness(es) a declared subject kept" in result.summary
    assert f"{witness} ({_CHANGED})" in result.summary
    assert f"{witness} ({_TEST_FILE})" in result.summary


def test_an_exempt_new_test_is_left_out_of_the_reverted_run_and_named():
    """A name a post-rebuttal probe already killed is dropped from the reverted run, the same way a
    `preserves` witness is. `t.py::test_a` names a test exempt but never a
    candidate, so it is neither handed nor named."""
    captured: list[list[str]] = []

    def run_tests(subset):
        captured.append(subset)
        return _tests(*subset, failed=tuple(subset))

    result = revert_gate(
        prior=[_tests("t.py::test_a")],
        results=[_tests("t.py::test_a", "t.py::test_new", "t.py::test_rebut")],
        acceptance=[],
        changed_files=["pkg/a.py"],
        test_paths=[_TESTS],
        dirty=lambda: [],
        reverted=lambda paths: _reverted(paths, log=[]),
        run_tests=run_tests,
        exempt=["t.py::test_rebut", "t.py::test_a"],
        diff="",
    )
    assert captured == [["t.py::test_new"]]
    assert result.status == "pass"
    assert "t.py::test_rebut" in result.summary
    assert "t.py::test_a" not in result.summary


def test_a_diff_whose_every_new_test_is_exempt_skips_saying_so_and_names_each():
    """Review of SA-0273: an all-exempt diff did add tests, so the skip must
    not say it added none, and every exempt name is spelled out."""
    from saffron.gates.core.revert import revert_gate

    rebut = [f"t.py::test_r{i}" for i in range(5)]
    result = revert_gate(
        prior=[_tests("t.py::test_a")],
        results=[_tests("t.py::test_a", *rebut)],
        acceptance=[],
        changed_files=["pkg/a.py"],
        test_paths=[_TESTS],
        dirty=lambda: [],
        reverted=lambda paths: _reverted(paths, log=[]),
        run_tests=lambda subset: _tests(*subset),
        exempt=rebut,
        diff="",
    )
    assert result.status == "skip"
    assert result.summary.startswith("every new test is exempt")
    assert all(name in result.summary for name in rebut)


def _tests_uncollected(*, collected=(), uncollected=None, failed=()):
    """A `tests` gate result that also fills `uncollected`, the shape
    backlog item 50 asks a runner for."""
    return GateResult(
        gate="tests",
        status="fail" if failed else "pass",
        tool="pytest 8.3.2",
        collected=list(collected),
        uncollected=None if uncollected is None else list(uncollected),
        failures=[Failure(file=n, code=n, message="assert") for n in failed],
    )


def _revert(run_tests, *, acceptance=(), results=None, changed_files=("pkg/a.py",)):
    return revert_gate(
        prior=[_tests("t.py::test_a")],
        results=results or [_tests("t.py::test_a", "t.py::test_new")],
        acceptance=list(acceptance),
        changed_files=list(changed_files),
        test_paths=[_TESTS],
        dirty=lambda: [],
        reverted=lambda paths: _reverted(paths, log=[]),
        run_tests=run_tests,
        exempt=[],
        diff="",
    )


def test_a_handed_name_the_reverted_run_does_not_account_for_is_an_error():
    """Backlog item 50's other half. A runner that fills `uncollected` must
    place every handed name in exactly one of `collected` or `uncollected`.
    A name left out, or listed in both, breaks that contract, so this gate
    reports `error`, not `fail` or `skip` (`error` != `fail`). Checked
    against `subset`, never `candidates`: a dropped option name or an
    exempted witness is never handed, so neither is ever asked about."""
    new = "t.py::test_new"

    # Accounted for by `collected` alone, and by `uncollected` alone.
    assert (
        _revert(
            lambda s: _tests_uncollected(collected=s, uncollected=[], failed=s)
        ).status
        == "pass"
    )
    assert _revert(lambda s: _tests_uncollected(uncollected=s)).status == "pass"

    # The two pre-existing skips still fire once `uncollected` is filled.
    keyed_elsewhere = _revert(
        lambda s: GateResult(
            gate="tests",
            status="fail",
            tool="pytest 8.3.2",
            collected=list(s),
            uncollected=[],
            failures=[Failure(file=n, code="AssertionError", message="x") for n in s],
        )
    )
    assert keyed_elsewhere.status == "skip" and "node id" in keyed_elsewhere.summary
    unreadable = _revert(
        lambda s: GateResult(gate="tests", status="error", summary="x")
    )
    assert unreadable.status == "skip"
    # The two earlier skips hold even when the run fills `uncollected`.
    errored_listing = _revert(
        lambda s: GateResult(
            gate="tests", status="error", collected=[], uncollected=list(s)
        )
    )
    assert errored_listing.status == "skip"
    assert "no readable verdict" in errored_listing.summary
    unenumerated_listing = _revert(
        lambda s: GateResult(
            gate="tests",
            status="fail",
            tool="pytest 8.3.2",
            collected=None,
            uncollected=list(s),
            failures=[Failure(file=n, code=n, message="x") for n in s],
        )
    )
    assert unenumerated_listing.status == "skip"
    assert "nothing to read" in unenumerated_listing.summary

    # Listed in both: the run double-answered the same question, so `error`.
    both = _revert(lambda s: _tests_uncollected(collected=s, uncollected=s))
    assert both.status == "error" and new in both.summary

    # Listed in neither, though a failure is keyed on it: still `error`.
    # A failure code alone is not enough to count as accounted for.
    neither = _revert(
        lambda s: GateResult(
            gate="tests",
            status="fail",
            tool="pytest 8.3.2",
            collected=[],
            uncollected=[],
            failures=[Failure(file=n, code=n, message="x") for n in s],
        )
    )
    assert neither.status == "error" and new in neither.summary

    # A dropped option name and an exempted witness are never handed.
    exempt = Criterion(
        claim="unrelated",
        witness="t.py::test_exempt",
        mutant={"file": "elsewhere.py", "find": "a", "replace": "b"},
    )
    dropped_and_exempt = _revert(
        lambda s: _tests_uncollected(collected=s, uncollected=[], failed=s),
        acceptance=[exempt],
        results=[_tests("t.py::test_a", new, "t.py::test_exempt", f"--deselect={new}")],
    )
    assert dropped_and_exempt.status == "pass"

    # A dropped name the run lists in both `collected` and `uncollected`
    # is still never handed. The both-lists rule checks handed names alone.
    dropped_both = _revert(
        lambda s: GateResult(
            gate="tests",
            status="fail",
            tool="pytest 8.3.2",
            collected=[new, f"--deselect={new}"],
            uncollected=[f"--deselect={new}"],
            failures=[Failure(file=new, code=new, message="x")],
        ),
        results=[_tests("t.py::test_a", new, f"--deselect={new}")],
    )
    assert dropped_both.status == "pass"
    assert "could not collect" not in dropped_both.summary

    # A name the gate was never handed, listed and keyed on, is not evidence.
    unhanded_key = _revert(
        lambda s: GateResult(
            gate="tests",
            status="fail",
            tool="pytest 8.3.2",
            collected=list(s),
            uncollected=["AssertionError"],
            failures=[Failure(file="t.py", code="AssertionError", message="x")],
        ),
    )
    assert unhanded_key.status == "skip" and "node id" in unhanded_key.summary

    # With no `uncollected` at all, a `fail` run keyed on the handed name
    # with `collected=[]` is still today's `skip`.
    unchanged = _revert(
        lambda s: GateResult(
            gate="tests",
            status="fail",
            tool="pytest 8.3.2",
            collected=[],
            failures=[Failure(file=n, code=n, message="x") for n in s],
        )
    )
    assert unchanged.status == "skip"


def test_each_verdict_names_the_tests_the_reverted_run_could_not_collect():
    """A name listed in `uncollected` reads as a test that failed without
    its source. Every verdict's summary names it, whichever status or
    failure keying the run reports."""
    new = "t.py::test_new"

    # `pass`, enumerated, no failures at all.
    no_failures = _revert(lambda s: _tests_uncollected(uncollected=s))
    assert no_failures.status == "pass" and new in no_failures.summary

    # `fail`, enumerated, with a failure keyed on the listed name itself.
    keyed_on_listed = _revert(
        lambda s: GateResult(
            gate="tests",
            status="fail",
            tool="pytest 8.3.2",
            collected=[],
            uncollected=list(s),
            failures=[Failure(file=n, code=n, message="x") for n in s],
        )
    )
    assert keyed_on_listed.status == "pass" and new in keyed_on_listed.summary

    # One handed name uncollected, the other ran and passed cleanly. The
    # summary still names the uncollected one, and the theater is still caught.
    kept = "t.py::test_kept"
    mixed = _revert(
        lambda s: GateResult(
            gate="tests",
            status="fail",
            tool="pytest 8.3.2",
            collected=[kept],
            uncollected=[new],
        ),
        results=[_tests("t.py::test_a", new, kept)],
    )
    assert mixed.status == "fail" and new in mixed.summary
    assert [f.file for f in mixed.failures] == [kept]


def _real_tests_gate(tmp_path):
    """This repo's own `tests` gate, run in `tmp_path` on whatever subset
    `revert` hands it."""
    import subprocess
    from pathlib import Path

    from saffron.gates.contract import parse_gate_json

    gate = Path(__file__).resolve().parent.parent / ".saffron" / "gates" / "tests"

    def run_tests(subset):
        done = subprocess.run(
            [str(gate), *subset],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return parse_gate_json(done.stdout, expected_gate="tests")

    return run_tests


def _one_absent_id_beside(tmp_path, witness_body):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_new.py").write_text(
        "import pytest\n"
        "@pytest.mark.parametrize('lens', ['correctness'])\n"
        "def test_lens(lens):\n    assert lens\n"
        f"def test_witness():\n    {witness_body}\n"
    )
    absent = "tests/test_new.py::test_lens[conventions]"
    witness = "tests/test_new.py::test_witness"
    return revert_gate(
        prior=[_tests("tests/test_a.py::test_a")],
        results=[_tests("tests/test_a.py::test_a", absent, witness)],
        acceptance=[],
        changed_files=["pkg/a.py"],
        test_paths=[_TESTS],
        dirty=lambda: [],
        reverted=lambda paths: _reverted(paths, log=[]),
        run_tests=_real_tests_gate(tmp_path),
        exempt=[],
        diff="",
    )


def test_one_uncollectable_new_id_leaves_a_verdict_on_the_witness_beside_it(tmp_path):
    """b-cf832a: one id absent at base skipped the whole subset. The witness
    beside it failing without its source is now a `pass`."""
    result = _one_absent_id_beside(tmp_path, "assert False")
    assert result.status == "pass", result.summary
    assert "tests/test_new.py::test_lens[conventions]" in result.summary


def test_one_uncollectable_new_id_no_longer_hides_a_witness_that_passes(tmp_path):
    """The same subset with a witness that passes without its source is
    theater, and `revert` names it."""
    result = _one_absent_id_beside(tmp_path, "assert True")
    assert result.status == "fail", result.summary
    assert [f.file for f in result.failures] == ["tests/test_new.py::test_witness"]


# Backlog item 49: the second, rewritten-test subset `locations` drives.
# Every helper below builds a real `git diff`, under the pinned flags.


def _git(repo, *args: str):
    import subprocess

    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


_REWRITE_BASE = (
    "def test_added_inside():\n"
    "    before = 1\n"
    "    assert before == 1\n"
    "\n"
    "\n"
    "def test_removed_last():\n"
    "    before = 1\n"
    "    assert before == 1\n"
    "\n"
    "\n"
    "# marker line directly above test_removed_above\n"
    "def test_removed_above():\n"
    "    before = 1\n"
    "    assert before == 1\n"
    "\n"
    "\n"
    "def test_added_at_first():\n"
    "    before = 1\n"
    "    assert before == 1\n"
    "\n"
    "\n"
    "def test_untouched():\n"
    "    before = 1\n"
    "    assert before == 1\n"
)

_REWRITE_HEAD = (
    "def test_added_inside():\n"
    "    before = 1\n"
    "    added = 2\n"
    "    assert before == 1\n"
    "\n"
    "\n"
    "def test_removed_last():\n"
    "    before = 1\n"
    "\n"
    "\n"
    "def test_removed_above():\n"
    "    before = 1\n"
    "    assert before == 1\n"
    "\n"
    "\n"
    "def test_added_at_first():  # renamed\n"
    "    before = 1\n"
    "    assert before == 1\n"
    "\n"
    "\n"
    "def test_untouched():\n"
    "    before = 1\n"
    "    assert before == 1\n"
)


def _rewrite_fixture(tmp_path) -> str:
    """A real diff rewriting four tests of `tests/test_thing.py` in place.
    One gets an added line inside it. One loses its last line. One loses
    the line directly above it. One gets a changed first line. A fifth
    test stays alone. `src.py` also changes, so a source side exists to
    revert."""
    repo = tmp_path / "rewrite_repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "src.py").write_text("def helper():\n    return 1\n")
    (repo / "tests").mkdir()
    (repo / "tests" / "test_thing.py").write_text(_REWRITE_BASE)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    base_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()

    (repo / "src.py").write_text("def helper():\n    return 2\n")
    (repo / "tests" / "test_thing.py").write_text(_REWRITE_HEAD)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "head")

    from saffron.cell.worktree import DIFF_FLAGS

    return _git(repo, "diff", *DIFF_FLAGS, f"{base_sha}..HEAD").stdout


def _gate_result(names, *, locations=None, failed=()):
    """A `tests` result built through `GateResult.model_validate`, from
    plain dicts, so this module keeps collecting against the base
    contract with the source reverted."""
    payload = {
        "gate": "tests",
        "status": "fail" if failed else "pass",
        "tool": "pytest 8.3.2",
        "collected": list(names),
        "failures": [{"file": n, "code": n, "message": "x"} for n in failed],
    }
    if locations is not None:
        payload["locations"] = locations
    return GateResult.model_validate(payload)


def test_the_second_subset_is_each_old_test_a_changed_line_falls_inside(tmp_path):
    diff = _rewrite_fixture(tmp_path)
    locations = {
        "tests/test_thing.py::test_added_inside": {
            "file": "tests/test_thing.py",
            "first": 1,
            "last": 4,
        },
        "tests/test_thing.py::test_removed_last": {
            "file": "tests/test_thing.py",
            "first": 7,
            "last": 8,
        },
        "tests/test_thing.py::test_removed_above": {
            "file": "tests/test_thing.py",
            "first": 11,
            "last": 13,
        },
        "tests/test_thing.py::test_added_at_first": {
            "file": "tests/test_thing.py",
            "first": 16,
            "last": 18,
        },
        # Located, but a changed line never reaches its own span.
        "tests/test_thing.py::test_untouched": {
            "file": "tests/test_thing.py",
            "first": 21,
            "last": 23,
        },
        # A file the diff left alone, under `test_paths` all the same.
        "tests/test_other.py::test_other": {
            "file": "tests/test_other.py",
            "first": 1,
            "last": 3,
        },
        # A real changed line, outside the repo's declared `test_paths`.
        "src.py::test_as_source": {"file": "src.py", "first": 1, "last": 2},
        # A `preserves` witness, overlapping a changed line all the same.
        "tests/test_thing.py::test_preserved": {
            "file": "tests/test_thing.py",
            "first": 1,
            "last": 4,
        },
        # An exempt name, overlapping a changed line.
        "tests/test_thing.py::test_exempt": {
            "file": "tests/test_thing.py",
            "first": 7,
            "last": 8,
        },
        # A name reading as a command-line option, overlapping a changed line.
        "--deselect=tests/test_thing.py::test_option": {
            "file": "tests/test_thing.py",
            "first": 11,
            "last": 13,
        },
        # The first subset's own candidate, overlapping a changed line too.
        "tests/test_thing.py::test_brand_new": {
            "file": "tests/test_thing.py",
            "first": 16,
            "last": 18,
        },
        # Collected at base alone. A head-only intersection drops it.
        "tests/test_thing.py::test_only_base": {
            "file": "tests/test_thing.py",
            "first": 7,
            "last": 8,
        },
        # The two blank lines after `test_added_inside` sit inside the
        # hunk, but neither is a changed line on its own.
        "tests/test_thing.py::test_context_only": {
            "file": "tests/test_thing.py",
            "first": 5,
            "last": 6,
        },
    }
    both_sides = [
        "tests/test_thing.py::test_added_inside",
        "tests/test_thing.py::test_removed_last",
        "tests/test_thing.py::test_removed_above",
        "tests/test_thing.py::test_added_at_first",
        "tests/test_thing.py::test_untouched",
        "tests/test_thing.py::test_no_location",
        "tests/test_other.py::test_other",
        "src.py::test_as_source",
        "tests/test_thing.py::test_preserved",
        "tests/test_thing.py::test_exempt",
        "--deselect=tests/test_thing.py::test_option",
        "tests/test_thing.py::test_context_only",
    ]
    # A declared witness collected on both sides, reached by a changed line.
    locations["tests/test_thing.py::test_declared"] = {
        "file": "tests/test_thing.py",
        "first": 1,
        "last": 4,
    }
    both_sides.append("tests/test_thing.py::test_declared")
    before = [*both_sides, "tests/test_thing.py::test_only_base"]
    after = [*both_sides, "tests/test_thing.py::test_brand_new"]
    # A location for a name with none at head, read only if the baseline's
    # own map were wrongly consulted too.
    base_locations = {
        "tests/test_thing.py::test_no_location": {
            "file": "tests/test_thing.py",
            "first": 1,
            "last": 4,
        }
    }

    calls: list[list[str]] = []
    log: list = []

    def run_tests(subset):
        calls.append(list(subset))
        log.append(("run", list(subset)))
        return _gate_result(subset, failed=tuple(subset))

    result = revert_gate(
        prior=[_gate_result(before, locations=base_locations)],
        results=[_gate_result(after, locations=locations)],
        acceptance=[
            Criterion(
                claim="preserved",
                witness="tests/test_thing.py::test_preserved",
                preserves=True,
            ),
            Criterion(claim="w", witness="tests/test_thing.py::test_declared"),
        ],
        changed_files=["src.py", "tests/test_thing.py"],
        test_paths=["tests/**"],
        dirty=lambda: [],
        reverted=lambda paths: _reverted(paths, log=log),
        run_tests=run_tests,
        exempt=["tests/test_thing.py::test_exempt"],
        diff=diff,
    )
    assert result is not None
    assert calls[0] == [
        "tests/test_thing.py::test_brand_new",
        "tests/test_thing.py::test_declared",
    ]
    assert calls[1] == [
        "tests/test_thing.py::test_added_at_first",
        "tests/test_thing.py::test_added_inside",
        "tests/test_thing.py::test_removed_above",
        "tests/test_thing.py::test_removed_last",
    ]
    # Both runs fall inside the one revert, never after the restore.
    assert log == [
        ("revert", ["src.py"]),
        ("run", calls[0]),
        ("run", calls[1]),
        ("restore", ["src.py"]),
    ]


_POOL = ["t.py::test_old1", "t.py::test_old2"]
_NEW = "t.py::test_new"
_RAISE = "raise"


def _two_old_tests_fixture(tmp_path) -> str:
    """A real diff rewriting both old tests in place, each by one line
    added inside it. A source file changes too, so a side exists to
    revert."""
    repo = tmp_path / "two_repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "src.py").write_text("def helper():\n    return 1\n")
    (repo / "tests").mkdir()
    (repo / "tests" / "t.py").write_text(
        "def test_old1():\n    pass\n\n\ndef test_old2():\n    pass\n"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    base_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()

    (repo / "src.py").write_text("def helper():\n    return 2\n")
    (repo / "tests" / "t.py").write_text(
        "def test_old1():\n    pass\n    pass\n\n\ndef test_old2():\n    pass\n    pass\n"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "head")

    from saffron.cell.worktree import DIFF_FLAGS

    return _git(repo, "diff", *DIFF_FLAGS, f"{base_sha}..HEAD").stdout


_POOL_LOCATIONS = {
    "t.py::test_old1": {"file": "tests/t.py", "first": 1, "last": 3},
    "t.py::test_old2": {"file": "tests/t.py", "first": 6, "last": 8},
}


def _first_outcomes() -> dict:
    """The eight first-run outcomes criteria 3 and 4 share, keyed by name:
    a callable the handed subset is passed, `_RAISE`, or `None` where the
    subset is never handed at all. The second element says whether a new
    name is declared, so `before`/`after` can be built either way."""
    return {
        "pass": (lambda subset: _tests(*subset, failed=tuple(subset)), True),
        "fail": (lambda subset: _tests(*subset), True),
        "skip_unreadable": (
            lambda subset: GateResult(gate="tests", status="skip"),
            True,
        ),
        "skip_unenumerated": (
            lambda subset: GateResult.model_validate(
                {"gate": "tests", "status": "pass", "tool": "pytest 8.3.2"}
            ),
            True,
        ),
        "skip_keyed_elsewhere": (
            lambda subset: _tests_keyed_elsewhere(*subset, failed=tuple(subset)),
            True,
        ),
        "error_unaccounted": (
            lambda subset: GateResult.model_validate(
                {
                    "gate": "tests",
                    "status": "fail",
                    "tool": "pytest 8.3.2",
                    "collected": [],
                    "uncollected": [],
                }
            ),
            True,
        ),
        "error_raised": (_RAISE, True),
        "skip_adds_no_new_test": (None, False),
    }


def _second_outcomes() -> dict:
    """The eight second-run outcomes criteria 3 and 4 share, keyed by name
    the same way `_first_outcomes` is."""
    return {
        "one_passing": (
            lambda subset: GateResult.model_validate(
                {
                    "gate": "tests",
                    "status": "fail",
                    "tool": "pytest 8.3.2",
                    "collected": list(subset),
                    "failures": [
                        {
                            "file": "t.py::test_old2",
                            "code": "t.py::test_old2",
                            "message": "x",
                        }
                    ],
                }
            ),
        ),
        "all_passing": (
            lambda subset: GateResult.model_validate(
                {
                    "gate": "tests",
                    "status": "pass",
                    "tool": "pytest 8.3.2",
                    "collected": list(subset),
                    "failures": [],
                }
            ),
        ),
        "all_failing": (
            lambda subset: GateResult.model_validate(
                {
                    "gate": "tests",
                    "status": "fail",
                    "tool": "pytest 8.3.2",
                    "collected": list(subset),
                    "failures": [
                        {"file": n, "code": n, "message": "x"} for n in subset
                    ],
                }
            ),
        ),
        "errored": (
            lambda subset: GateResult.model_validate(
                {"gate": "tests", "status": "error", "summary": "boom"}
            ),
        ),
        "raised": (_RAISE,),
        "unenumerated": (
            lambda subset: GateResult.model_validate(
                {"gate": "tests", "status": "pass", "tool": "pytest 8.3.2"}
            ),
        ),
        "keyed_elsewhere": (
            lambda subset: GateResult.model_validate(
                {
                    "gate": "tests",
                    "status": "fail",
                    "tool": "pytest 8.3.2",
                    "collected": list(subset),
                    "failures": [
                        {"file": n, "code": "AssertionError", "message": "x"}
                        for n in subset
                    ],
                }
            ),
        ),
        "uncollected": (
            lambda subset: GateResult.model_validate(
                {
                    "gate": "tests",
                    "status": "pass",
                    "tool": "pytest 8.3.2",
                    "collected": [],
                    "failures": [],
                }
            ),
        ),
    }


def _crossed_run_tests(first_behavior, second_behavior, calls=None):
    """One `run_tests` fake, dispatched on whether `_NEW` is in the handed
    subset: the shared helper criteria 3 and 4 both build their calls
    from."""

    def run_tests(subset):
        if calls is not None:
            calls.append(list(subset))
        behavior = first_behavior if _NEW in subset else second_behavior
        if behavior == _RAISE:
            raise RuntimeError("the reverted run crashed")
        return behavior(subset)

    return run_tests


def test_the_second_subset_never_changes_what_revert_decides(tmp_path):
    diff = _two_old_tests_fixture(tmp_path)
    first_outcomes = _first_outcomes()
    second_outcomes = _second_outcomes()

    for first_key, (first_behavior, subset_present) in first_outcomes.items():
        after = [*_POOL, _NEW] if subset_present else list(_POOL)
        for second_key, (second_behavior,) in second_outcomes.items():
            with_calls: list[list[str]] = []
            without_calls: list[list[str]] = []
            with_second = revert_gate(
                prior=[_gate_result(_POOL)],
                results=[_gate_result(after, locations=_POOL_LOCATIONS)],
                acceptance=[],
                changed_files=["src.py", "tests/t.py"],
                test_paths=["tests/**"],
                dirty=lambda: [],
                reverted=lambda paths: _reverted(paths, log=[]),
                run_tests=_crossed_run_tests(
                    first_behavior, second_behavior, calls=with_calls
                ),
                exempt=[],
                diff=diff,
            )
            without_second = revert_gate(
                prior=[_gate_result(_POOL)],
                results=[_gate_result(after)],
                acceptance=[],
                changed_files=["src.py", "tests/t.py"],
                test_paths=["tests/**"],
                dirty=lambda: [],
                reverted=lambda paths: _reverted(paths, log=[]),
                run_tests=_crossed_run_tests(
                    first_behavior, second_behavior, calls=without_calls
                ),
                exempt=[],
                diff=diff,
            )
            case = f"{first_key} x {second_key}"
            first_calls = [[_NEW]] if subset_present else []
            # Two runs, never one union, and the second runs with no new test.
            assert with_calls == [*first_calls, _POOL], case
            assert without_calls == first_calls, case
            assert with_second.status == without_second.status, case
            assert with_second.failures == without_second.failures, case
            assert with_second.tool == without_second.tool, case

    # The second run happens inside the same revert, never after the
    # restore.
    log: list = []
    run_tests = _crossed_run_tests(
        first_outcomes["pass"][0], second_outcomes["all_passing"][0], calls=log
    )
    revert_gate(
        prior=[_gate_result(_POOL)],
        results=[_gate_result([*_POOL, _NEW], locations=_POOL_LOCATIONS)],
        acceptance=[],
        changed_files=["src.py", "tests/t.py"],
        test_paths=["tests/**"],
        dirty=lambda: [],
        reverted=lambda paths: _reverted(paths, log=log),
        run_tests=run_tests,
        exempt=[],
        diff=diff,
    )
    revert_index = log.index(("revert", ["src.py"]))
    restore_index = log.index(("restore", ["src.py"]))
    run_indices = [i for i, entry in enumerate(log) if isinstance(entry, list)]
    assert run_indices
    assert all(revert_index < i < restore_index for i in run_indices)

    # A checkout or restore that fails is `error`, with a first subset and
    # without one.
    for after in ([*_POOL, _NEW], list(_POOL)):
        for fails in ({"fail_on_enter": True}, {"fail_on_exit": True}):
            broken = revert_gate(
                prior=[_gate_result(_POOL)],
                results=[_gate_result(after, locations=_POOL_LOCATIONS)],
                acceptance=[],
                changed_files=["src.py", "tests/t.py"],
                test_paths=["tests/**"],
                dirty=lambda: [],
                reverted=lambda paths, fails=fails: _reverted(paths, log=[], **fails),
                run_tests=_crossed_run_tests(
                    first_outcomes["pass"][0], second_outcomes["all_passing"][0]
                ),
                exempt=[],
                diff=diff,
            )
            case = f"{after} {fails}"
            assert broken.status == "error", case
            assert broken.failures == [], case
            assert broken.tool is None, case

    # A first subset that exemption empties still runs the second subset.
    exempt_calls: dict[bool, list[list[str]]] = {True: [], False: []}
    exempt_runs = {}
    for located in (True, False):
        exempt_runs[located] = revert_gate(
            prior=[_gate_result(_POOL)],
            results=[
                _gate_result(
                    [*_POOL, _NEW], locations=_POOL_LOCATIONS if located else None
                )
            ],
            acceptance=[],
            changed_files=["src.py", "tests/t.py"],
            test_paths=["tests/**"],
            dirty=lambda: [],
            reverted=lambda paths: _reverted(paths, log=[]),
            run_tests=_crossed_run_tests(
                first_outcomes["pass"][0],
                second_outcomes["all_passing"][0],
                calls=exempt_calls[located],
            ),
            exempt=[_NEW],
            diff=diff,
        )
    assert exempt_calls == {True: [_POOL], False: []}
    with_exempt, without_exempt = exempt_runs[True], exempt_runs[False]
    assert with_exempt.status == without_exempt.status
    assert with_exempt.failures == without_exempt.failures
    assert with_exempt.tool == without_exempt.tool
    assert with_exempt.summary == without_exempt.summary + (
        " — advisory, does not block: 2 of 2 rewritten test(s) passed "
        "without their source: t.py::test_old1, t.py::test_old2"
    )


def test_each_verdict_after_the_reverted_run_carries_the_advisory(tmp_path):
    diff = _two_old_tests_fixture(tmp_path)
    first_outcomes = _first_outcomes()
    second_outcomes = _second_outcomes()
    unreadable_clause = (
        " — advisory, does not block: no readable verdict for the rewritten test(s)"
    )
    clause_text = {
        "one_passing": (
            " — advisory, does not block: 1 of 2 rewritten test(s) passed "
            "without their source: t.py::test_old1"
        ),
        "all_passing": (
            " — advisory, does not block: 2 of 2 rewritten test(s) passed "
            "without their source: t.py::test_old1, t.py::test_old2"
        ),
        "all_failing": (
            " — advisory, does not block: 0 of 2 rewritten test(s) passed "
            "without their source"
        ),
        "errored": unreadable_clause,
        "raised": unreadable_clause,
        "unenumerated": unreadable_clause,
        "keyed_elsewhere": unreadable_clause,
        "uncollected": (
            " — advisory, does not block: 0 of 2 rewritten test(s) passed "
            "without their source"
        ),
    }
    main_keys = (
        "pass",
        "fail",
        "skip_unreadable",
        "skip_unenumerated",
        "skip_keyed_elsewhere",
        "skip_adds_no_new_test",
    )
    for first_key in main_keys:
        first_behavior, subset_present = first_outcomes[first_key]
        after = [*_POOL, _NEW] if subset_present else list(_POOL)
        baseline = revert_gate(
            prior=[_gate_result(_POOL)],
            results=[_gate_result(after)],
            acceptance=[],
            changed_files=["src.py", "tests/t.py"],
            test_paths=["tests/**"],
            dirty=lambda: [],
            reverted=lambda paths: _reverted(paths, log=[]),
            run_tests=_crossed_run_tests(
                first_behavior, second_outcomes["all_passing"][0]
            ),
            exempt=[],
            diff=diff,
        )
        for second_key, (second_behavior,) in second_outcomes.items():
            result = revert_gate(
                prior=[_gate_result(_POOL)],
                results=[_gate_result(after, locations=_POOL_LOCATIONS)],
                acceptance=[],
                changed_files=["src.py", "tests/t.py"],
                test_paths=["tests/**"],
                dirty=lambda: [],
                reverted=lambda paths: _reverted(paths, log=[]),
                run_tests=_crossed_run_tests(first_behavior, second_behavior),
                exempt=[],
                diff=diff,
            )
            case = f"{first_key} x {second_key}"
            assert result.summary == baseline.summary + clause_text[second_key], case

    # Five rewritten tests passing: named, but only the first three.
    pool5 = [f"t.py::test_r{i}" for i in range(5)]
    locations5 = {name: {"file": "tests/t.py", "first": 1, "last": 3} for name in pool5}

    def run_tests5(subset):
        return GateResult.model_validate(
            {
                "gate": "tests",
                "status": "pass",
                "tool": "pytest 8.3.2",
                "collected": list(subset),
                "failures": [],
            }
        )

    result5 = revert_gate(
        prior=[_gate_result(pool5)],
        results=[_gate_result(pool5, locations=locations5)],
        acceptance=[],
        changed_files=["src.py", "tests/t.py"],
        test_paths=["tests/**"],
        dirty=lambda: [],
        reverted=lambda paths: _reverted(paths, log=[]),
        run_tests=run_tests5,
        exempt=[],
        diff=diff,
    )
    assert result5.summary == (
        "the diff adds no new test"
        " — advisory, does not block: 5 of 5 rewritten test(s) passed without "
        "their source: t.py::test_r0, t.py::test_r1, t.py::test_r2"
    )


def test_with_no_locations_the_rewritten_tests_are_never_run(tmp_path):
    readable_diff = _two_old_tests_fixture(tmp_path)
    unreadable_diff = "diff --git a/x.py c/x.py\n"

    # A diff with a first subset: one run, no second, for a readable diff
    # and for one `revert` cannot read alike. Nothing reads either.
    for diff in (readable_diff, unreadable_diff):
        for locations in (None, {}):
            calls: list[list[str]] = []

            def run_tests(subset, calls=calls):
                calls.append(list(subset))
                return _tests(*subset, failed=tuple(subset))

            result = revert_gate(
                prior=[_gate_result(_POOL)],
                results=[_gate_result([*_POOL, _NEW], locations=locations)],
                acceptance=[],
                changed_files=["src.py", "tests/t.py"],
                test_paths=["tests/**"],
                dirty=lambda: [],
                reverted=lambda paths: _reverted(paths, log=[]),
                run_tests=run_tests,
                exempt=[],
                diff=diff,
            )
            assert calls == [[_NEW]], (diff, locations)
            assert result.status == "pass", (diff, locations)
            assert (
                result.summary
                == "1 new test(s) failed without their source, as required"
            )

    # A diff with neither subset: today's skip, with today's own summary.
    # Nothing here touches the worktree.
    def _refuse_dirty():
        raise AssertionError("locations=None/{} must never read dirty paths")

    for diff in (readable_diff, unreadable_diff):
        for locations in (None, {}):
            result = revert_gate(
                prior=[_gate_result(_POOL)],
                results=[_gate_result(_POOL, locations=locations)],
                acceptance=[],
                changed_files=["tests/t.py"],
                test_paths=["tests/**"],
                dirty=_refuse_dirty,
                reverted=_refuse,
                run_tests=_refuse_run,
                exempt=[],
                diff=diff,
            )
            assert result.status == "skip", (diff, locations)
            assert result.summary == "the diff adds no new test", (diff, locations)


def test_a_diff_revert_cannot_read_leaves_the_second_subset_unrun_and_says_so():
    # One diff `_split_blocks` rejects, and one block `_parse_block` rejects.
    for bad_diff in (
        "diff --git a/x.py c/x.py\n",
        "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ bogus @@\n+x\n",
    ):
        _assert_unreadable_diff_unrun(bad_diff)


def _assert_unreadable_diff_unrun(bad_diff):
    unreadable_clause = (
        " — advisory, does not block: the diff could not be read, so no "
        "rewritten test could be checked"
    )

    # With a first subset: its verdict stands, and the clause still rides.
    def run_tests(subset):
        return _tests(*subset, failed=tuple(subset))

    with_first = revert_gate(
        prior=[_gate_result(_POOL)],
        results=[_gate_result([*_POOL, _NEW], locations=_POOL_LOCATIONS)],
        acceptance=[],
        changed_files=["src.py", "tests/t.py"],
        test_paths=["tests/**"],
        dirty=lambda: [],
        reverted=lambda paths: _reverted(paths, log=[]),
        run_tests=run_tests,
        exempt=[],
        diff=bad_diff,
    )
    assert with_first.status == "pass"
    assert with_first.summary == (
        "1 new test(s) failed without their source, as required" + unreadable_clause
    )

    # Without one: today's skip for a diff that adds no new test, and
    # nothing here is ever touched.
    without_first = revert_gate(
        prior=[_gate_result(_POOL)],
        results=[_gate_result(_POOL, locations=_POOL_LOCATIONS)],
        acceptance=[],
        changed_files=["src.py", "tests/t.py"],
        test_paths=["tests/**"],
        dirty=lambda: [],
        reverted=_refuse,
        run_tests=_refuse_run,
        exempt=[],
        diff=bad_diff,
    )
    assert without_first.status == "skip"
    assert without_first.summary == "the diff adds no new test" + unreadable_clause
