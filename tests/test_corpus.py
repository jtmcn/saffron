import subprocess
from pathlib import Path

import pytest

from harness import corpus, lens_scoring, recovery
from harness.lens_scoring import LensReview
from saffron.agents.findings import Finding
from saffron.gates.contract import GateResult
from saffron.ledger import Ledger
from saffron.phases.review import LENSES

REPO = Path(__file__).parent.parent
FIXTURES = REPO / "docs" / "evidence" / "fixtures"


@pytest.fixture
def sa0062():
    return lens_scoring.load_fixture(FIXTURES / "SA-0062")


@pytest.fixture
def one_defect_fixture(sa0062, tmp_path):
    """SA-0062 with its second defect removed — a one-defect fixture built from
    a real one, so the uneven-corpus test is not scoring a hand-built stub."""
    for name in (
        "diff.patch",
        "spec_body.md",
        "gates.txt",
        "context.md",
        "recorded-findings.json",
    ):
        (tmp_path / name).write_text((sa0062.root / name).read_text())
    text = (sa0062.root / "fixture.toml").read_text()
    first, second = text.index("[[defects]]"), text.rindex("[[defects]]")
    assert first != second  # otherwise this fixture is the whole thing
    (tmp_path / "fixture.toml").write_text(
        text[:second].replace('spec_id = "SA-0062"', 'spec_id = "SA-0062-one"')
    )
    return lens_scoring.load_fixture(tmp_path)


def _run(findings=()):
    return [
        LensReview(lens=lens, findings=list(findings) if lens == "correctness" else [])
        for lens in LENSES
    ]


def _finding(file, line, claim):
    return Finding(
        lens="correctness",
        severity="blocker",
        file=file,
        line=line,
        claim=claim,
        anchored=True,
    )


def test_the_aggregate_counts_defects_and_not_fixtures(sa0062, one_defect_fixture):
    """A fixture carrying two defects is two observations. Averaging within it
    first would throw one away, and the corpus is deliberately uneven — five
    fixtures carry one defect and three carry two."""
    scored = corpus.score_corpus(
        [sa0062, one_defect_fixture],
        {sa0062.spec_id: [_run()], one_defect_fixture.spec_id: [_run()]},
    )
    assert scored.declared == 3
    assert scored.graded == 0


def test_a_fixture_whose_lens_errored_leaves_the_denominator(
    sa0062, one_defect_fixture
):
    """At n=3 an errored lens costs a third of a fixture; at n=1 it costs the
    fixture. Counting its defects as misses reports a lens miss for an error,
    which is the distinction `LensErrored` exists to keep."""
    errored = [LensReview(lens="correctness", findings=[], error="boom")]
    scored = corpus.score_corpus(
        [sa0062, one_defect_fixture],
        {sa0062.spec_id: [errored], one_defect_fixture.spec_id: [_run()]},
    )
    assert scored.dropped == (sa0062.spec_id,)
    assert scored.declared == 1  # only the fixture that produced a scored run


def test_a_corpus_where_every_fixture_dropped_is_not_a_table_of_zeroes(sa0062):
    errored = [LensReview(lens="correctness", findings=[], error="boom")]
    with pytest.raises(lens_scoring.LensErrored, match="no fixture"):
        corpus.score_corpus([sa0062], {sa0062.spec_id: [errored]})


def test_the_corpus_is_every_fixture_directory_under_the_root():
    """A directory, not a list in code: adding a fixture is a directory, and
    the harness is not edited to admit it."""
    loaded = corpus.load_corpus(FIXTURES)
    assert [f.spec_id for f in loaded] == sorted(f.spec_id for f in loaded)
    assert "SA-0062" in {f.spec_id for f in loaded}


def test_a_directory_without_a_fixture_toml_is_not_a_fixture(tmp_path):
    """`docs/evidence/fixtures/` may hold a README or a stray export; only a
    directory declaring itself is loaded."""
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "README.md").write_text("not a fixture")
    assert corpus.load_corpus(tmp_path) == []


def test_anchored_blockers_are_counted_per_run_not_per_pass(sa0062):
    """The number item 88 showed is stable across passes, and the only one
    production can be compared against. Per run, because §5.5 routes any single
    anchored blocker to REBUT — a total hides which runs would have blocked."""
    blocking = _finding("saffron/cell/worktree.py", 418, "truncating write")
    counts = corpus.anchored_blockers({sa0062.spec_id: [_run([blocking]), _run()]})
    assert counts == {sa0062.spec_id: [1, 0]}


def test_an_unanchored_blocker_is_not_counted(sa0062):
    """Unanchored means reconciliation could not place it in the diff. It is
    kept in the record because the drop rate is signal, but it would not have
    routed the pull request anywhere."""
    dropped = Finding(
        lens="correctness",
        severity="blocker",
        file="x.py",
        line=1,
        claim="c",
        anchored=False,
    )
    assert corpus.anchored_blockers({sa0062.spec_id: [_run([dropped])]}) == {
        sa0062.spec_id: [0]
    }


def test_splice_tools_takes_a_gate_s_tool_from_the_same_named_baseline_row():
    results = [GateResult(gate="tests", status="pass")]
    baseline = [{"gate": "tests", "tool": "pytest 8.0.0"}]
    spliced = recovery.splice_tools(results, baseline)
    assert spliced[0].tool == "pytest 8.0.0"


def test_splice_tools_gives_revert_the_tests_tool():
    """`revert` skips at base and inherits the tool of the `tests` re-run it
    performs (`revert.py:307`), so the lookup by its own name would miss."""
    results = [GateResult(gate="revert", status="pass")]
    baseline = [{"gate": "tests", "tool": "pytest 8.0.0"}]
    spliced = recovery.splice_tools(results, baseline)
    assert spliced[0].tool == "pytest 8.0.0"


def test_splice_tools_leaves_a_host_side_gate_s_tool_none():
    """A host-side core gate present in neither keeps `tool=None` — `None` is
    what `gate_summary` renders as "no tool reported"; `""` is not the same
    fact."""
    results = [GateResult(gate="scope", status="pass")]
    baseline = [{"gate": "tests", "tool": "pytest 8.0.0"}]
    spliced = recovery.splice_tools(results, baseline)
    assert spliced[0].tool is None


def test_task_row_picks_the_run_that_pushed_a_branch_over_a_failed_requeue(
    tmp_path,
):
    """I4's case, built hermetically rather than against `~/.saffron`:
    `SA-0064`-shaped history is two task rows for one spec — an earlier
    `PREFLIGHT_FAILED` attempt with `pushed_sha` NULL, and the `MERGED` retry
    that actually pushed one. `_task_row` must return the second, not choke
    on there being two."""
    ledger = Ledger(tmp_path / "ledger.db")
    repo_id = ledger.upsert_repo("r", "o", "/m.git", policy_sha="p" * 64)
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)

    failed = ledger.create_task(run_id, "SA-0064", "s" * 40, branch="saffron/SA-0064")
    ledger.set_task_state(failed, "PREFLIGHT_FAILED")

    merged = ledger.create_task(run_id, "SA-0064", "s" * 40, branch="saffron/SA-0064")
    ledger.record_push(merged, "b" * 40)
    ledger.set_task_state(merged, "MERGED")

    row = recovery._task_row(ledger, "SA-0064")
    assert row["task_id"] == merged
    assert row["pushed_sha"] == "b" * 40
    ledger.close()


def test_task_row_refuses_two_rows_that_both_pushed(tmp_path):
    """Ambiguous on purpose: two real pushes for one spec is not a shape
    `_task_row` has ever seen, and guessing which one REVIEW actually saw
    would be exactly the "approximate range" this corpus refuses to ship."""
    ledger = Ledger(tmp_path / "ledger.db")
    repo_id = ledger.upsert_repo("r", "o", "/m.git", policy_sha="p" * 64)
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)

    first = ledger.create_task(run_id, "SA-9999", "s" * 40, branch="saffron/SA-9999")
    ledger.record_push(first, "b" * 40)
    second = ledger.create_task(run_id, "SA-9999", "s" * 40, branch="saffron/SA-9999")
    ledger.record_push(second, "c" * 40)

    with pytest.raises(recovery.RecoveryError, match="2 tasks with a pushed_sha"):
        recovery._task_row(ledger, "SA-9999")
    ledger.close()


def test_the_table_reports_the_aggregate_and_every_fixture(sa0062, one_defect_fixture):
    fixtures = [sa0062, one_defect_fixture]
    runs = {f.spec_id: [_run()] for f in fixtures}
    table = corpus.render_corpus_table(
        fixtures, corpus.score_corpus(fixtures, runs), corpus.anchored_blockers(runs)
    )
    assert "0/3" in table  # graded / declared, per defect
    assert sa0062.spec_id in table and one_defect_fixture.spec_id in table


def test_every_shipped_fixture_reproduces_its_own_declared_range():
    """What makes the archaeology auditable rather than claimed. A fixture
    whose `diff.patch` is not `pinned_diff(base, head)` at the range its own
    `fixture.toml` declares is grading a lens against a tree nobody has.

    Goes through `recovery.pinned_diff`, never a bare `git diff`: `core.
    abbrev`, `diff.noprefix`, `diff.algorithm`, `diff.context` and `diff.
    suppressBlankEmpty` each measurably change a bare diff's bytes, so a
    literal `["git", "diff", ...]` here would make this test's own verdict
    depend on whichever machine's `~/.gitconfig` happens to run it."""
    for fixture in corpus.load_corpus(FIXTURES):
        live = recovery.pinned_diff(REPO, fixture.base_sha, fixture.head_sha)
        assert live == fixture.diff, fixture.spec_id


def test_pinned_diff_survives_a_hostile_git_config(tmp_path, monkeypatch):
    """C2's proof, kept as a regression rather than run once and discarded.

    A fake `$HOME` carrying `core.abbrev=12`, `diff.noprefix=true`,
    `diff.algorithm=patience`, `diff.context=5` and
    `diff.suppressBlankEmpty=true` all at once — every host config setting
    measured to move a bare `git diff` on this exact range. `pinned_diff`
    must reproduce the recorded patch anyway; a bare `git diff` must not (the
    failure `pinned_diff` exists to survive, asserted here so a future change
    to the hostile config above cannot quietly stop testing anything)."""
    (tmp_path / ".gitconfig").write_text(
        "[core]\n"
        "\tabbrev = 12\n"
        "[diff]\n"
        "\tnoprefix = true\n"
        "\talgorithm = patience\n"
        "\tcontext = 5\n"
        "\tsuppressBlankEmpty = true\n"
    )
    monkeypatch.setenv("HOME", str(tmp_path))
    # Either would point git at a config file that isn't the fake $HOME
    # above, silently making the hostile settings never take effect and this
    # test pass without testing anything.
    monkeypatch.delenv("GIT_CONFIG_GLOBAL", raising=False)
    monkeypatch.delenv("GIT_CONFIG_SYSTEM", raising=False)

    fixture = lens_scoring.load_fixture(FIXTURES / "SA-0045")

    pinned = recovery.pinned_diff(REPO, fixture.base_sha, fixture.head_sha)
    assert pinned == fixture.diff

    bare = subprocess.run(
        ["git", "-C", str(REPO), "diff", f"{fixture.base_sha}..{fixture.head_sha}"],
        capture_output=True,
        text=True,
    ).stdout
    assert bare != fixture.diff


def test_every_shipped_fixture_s_spec_body_and_context_reproduce_from_git():
    """Hermetic reproduction of two more frozen inputs, the same way the diff
    is reproduced above: `spec_body.md` via `recovery.spec_body_at` (base
    tree, the off-branch fallback, or a disclosed-mutant spec — whichever
    this fixture needed) and `context.md` via a plain `git show`. Both need
    only this repo's git history, so a regression in the spec-body fallback
    fails here rather than shipping silently into a paid lens prompt.

    `gates.txt` and `recorded-findings.json` are NOT covered here and cannot
    be: both are read from `~/.saffron/batches`, which exists on the machine
    that ran the batch and nowhere else. There is no hermetic check for
    those two files beyond the review this fixture already had.
    """
    for fixture in corpus.load_corpus(FIXTURES):
        spec_body = recovery.spec_body_at(
            REPO, fixture.base_sha, fixture.head_sha, fixture.spec_id
        )
        assert spec_body == fixture.spec_body, fixture.spec_id

        context_md = subprocess.run(
            ["git", "show", f"{fixture.base_sha}:CONTEXT.md"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert context_md == fixture.context_md, fixture.spec_id


def test_every_shipped_fixture_declares_a_non_empty_source():
    """`source` is the backlog row a defect's range and phrases came from —
    the same row `recover_fixture` cannot fill in, because it names nothing
    the ledger or batch tree records. `lens_scoring.load_fixture` reads it as
    `raw.get("source", "")`, so nothing short of this test refuses a fixture
    that shipped with the field still blank."""
    for fixture in corpus.load_corpus(FIXTURES):
        assert fixture.source.strip(), fixture.spec_id


def test_the_predicate_reproduces_every_fixture_s_recorded_answer():
    """`calibrate`'s guard, over all eight. Every declared defect is one a lens
    should have raised and did not, so every fixture's recorded answer is
    0 seen / 0 graded — and a predicate loosened until a missed defect starts
    scoring fails here before any money is spent."""
    corpus.calibrate_corpus(corpus.load_corpus(FIXTURES))
