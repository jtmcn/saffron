import contextlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from harness import corpus, lens_scoring, probe_check, recovery
from harness.lens_scoring import LensReview
from saffron.agents.findings import Finding
from saffron.cell.runtime import CellRuntimeError
from saffron.gates import runner
from saffron.gates.contract import GateResult
from saffron.intake import Mutant
from saffron.ledger import Ledger
from saffron.phases import review
from saffron.phases.review import LENSES
from saffron.repos.policy import Policy

REPO = Path(__file__).parent.parent
FIXTURES = REPO / "docs" / "evidence" / "fixtures"
BASELINE = REPO / "docs" / "evidence" / "passes" / "2026-09-09-lens-corpus-baseline"
RECORD = REPO / "docs" / "evidence" / "2026-09-09-lens-corpus-baseline.md"


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
    first would throw one away, and the corpus is deliberately uneven — four
    fixtures carry one defect and four carry two."""
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
    performs (`revert.py:244`, `:350`/`:370`), so the lookup by its own name would miss."""
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


def test_every_shipped_fixture_is_ready_for_a_probe_pass():
    """The spec's own precondition, as a test rather than a sentence.

    Every change that moves the baseline — the schema field, the prompt
    paragraph, the `Defect` locations — lands before pass 2 or not at all.
    This asserts the state a pass-2 run requires, so a half-landed change
    fails here rather than producing a number nobody can compare.
    """
    assert review.reported_model("adequacy") is not review.reported_model("correctness")
    prompt = REPO / "saffron" / "agents" / "prompts" / "review-adequacy.md"
    assert "`probe` (object)" in prompt.read_text()
    for fixture in corpus.load_corpus(FIXTURES):
        for defect in fixture.defects:
            assert defect.locations, (
                f"{fixture.spec_id}/{defect.id} declares no location"
            )


def test_the_predicate_reproduces_every_fixture_s_recorded_answer():
    """`calibrate`'s guard, over all eight. Every declared defect is one a lens
    should have raised and did not, so every fixture's recorded answer is
    0 seen / 0 graded — and a predicate loosened until a missed defect starts
    scoring fails here before any money is spent."""
    corpus.calibrate_corpus(corpus.load_corpus(FIXTURES))


def test_the_second_number_counts_probes_not_findings():
    """A finding with no probe is not a probe that failed — it is a finding
    from a lens that was never asked for one. Contract and correctness
    findings are 10 of pass 1's 18 unmatched, and none of them owes an edit."""
    results = {
        "SA-0063": [
            probe_check.ProbeResult("survived", ""),
            probe_check.ProbeResult("killed", "", ("t",)),
        ],
        "SA-0045": [probe_check.ProbeResult("unproven", "find text not found")],
    }
    score = corpus.score_probes(results, runs=1)
    assert (score.survived, score.killed, score.unproven) == (1, 1, 1)


def test_the_rendered_table_says_what_the_second_number_is_not():
    """A capability number beside a recall number will be read as comparable
    unless the table says otherwise, and it is not: it covers one lens."""
    results = {"SA-0063": [probe_check.ProbeResult("survived", "")]}
    rendered = corpus.render_probe_summary(corpus.score_probes(results, runs=1))
    assert "1 verified" in rendered
    assert "adequacy" in rendered


def test_one_verified_vacuity_reads_as_one_finding():
    """The noun agrees with the count. "1 verified vacuity — adequacy-lens
    findings whose named edit" is a table a person pastes into an evidence
    record, and half-pluralised prose reads as a number nobody checked."""
    results = {"SA-0063": [probe_check.ProbeResult("survived", "")]}
    rendered = corpus.render_probe_summary(corpus.score_probes(results, runs=1))
    assert "1 verified vacuity** — adequacy-lens finding whose named edit" in rendered


def test_the_second_number_names_how_many_fixtures_it_covered():
    """A resume probes what it ran and re-derives recall from every run JSON on
    disk, so the two lines can cover different sets. A fixture probed with
    nothing to apply is still covered — an empty list is coverage, an absent
    key is not."""
    results = {
        "SA-0045": [probe_check.ProbeResult("survived", "")],
        "SA-0063": [],
    }
    score = corpus.score_probes(results, runs=1)
    assert score.fixtures == 2
    assert "over 2 fixture(s) probed this invocation" in corpus.render_probe_summary(
        score
    )


def test_the_second_number_names_the_run_count_it_totals_over():
    """A total, where recall beside it is a rate. `--runs 3` files three
    chances to name a distinct edge and only byte-identical edits collapse, so
    a summary that omits the run count invites a comparison between passes
    that were not asked the same question."""
    results = {"SA-0045": [probe_check.ProbeResult("survived", "")]}
    assert "at 3 run(s) each" in corpus.render_probe_summary(
        corpus.score_probes(results, runs=3)
    )


def test_an_unproven_probe_is_in_no_denominator():
    """The same rule as a dropped run one level out. A probe that never applied
    says nothing about the lens, so counting it against the lens would report
    the harness's own refusals as a capability score."""
    results = {"SA-0045": [probe_check.ProbeResult("unproven", "not tracked at HEAD")]}
    rendered = corpus.render_probe_summary(corpus.score_probes(results, runs=1))
    assert "0 of 0" in rendered
    assert "1 unproven" in rendered


DRIVER = REPO / "docs" / "evidence" / "scripts" / "2026-09-08-lens-corpus.py"


def _load_driver():
    """The dated driver, imported by path — `tests/test_agent_runner.py`'s
    idiom for the same reason: the filename is not an identifier."""
    spec = importlib.util.spec_from_file_location("lens_corpus_driver", DRIVER)
    assert spec and spec.loader, f"no import spec for {DRIVER}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PROBE = Mutant(file="saffron/gates/core/scope.py", find="== 0", replace="== 1")
# A second, distinct probe on a second file. Distinct on all three fields so
# `_distinct` cannot collapse the pair into one.
PROBE_2 = Mutant(file="saffron/gates/core/census.py", find="!= 1", replace="!= 2")


def _saffron_dir_without_a_tests_gate(root):
    """A `.saffron/` export declaring one gate that is not `tests`.

    `load_policy` checks every declared gate exists and is executable, so this
    is a real policy over a real executable — the point is only that `tests` is
    not among its roles.
    """
    gates = root / ".saffron" / "gates"
    gates.mkdir(parents=True, exist_ok=True)
    (root / ".saffron" / "policy.yaml").write_text(
        "gates:\n  lint: { blocking: true }\n"
    )
    (gates / "lint").write_text("#!/bin/sh\nexit 0\n")
    (gates / "lint").chmod(0o755)
    return root


def _drive(
    tmp_path,
    monkeypatch,
    *extra_argv,
    saffron_dir=None,
    fixture_ids=("SA-0045",),
    mutate_raises=None,
    baseline_raises=None,
    probes=(PROBE,),
):
    """One fixture through the driver's `main`, with every path into a cell
    replaced: no container, no token, no spend.

    Returns the rendered table, the `run_gate` calls, the containers `cell_up`
    was asked for, what was mutated where, and the output root. The calls are
    the assertion that matters — a probe is answered by the repo's *declared*
    gate through the runner, in the cell it was applied in, or it is not
    answered at all.

    `mutate_raises` makes `source_mutated` raise instead of yielding on its
    *first* call, which is the one thing in this path that a real cell does
    routinely. First call rather than every call so a later probe in the same
    fixture can be observed being attempted — or, once the tree's state is
    unknown, observed not being.

    `baseline_raises` makes the first `run_gate` call — the baseline — raise.

    `probes` is one adequacy finding each, so a fixture can file more than one.
    """
    driver = _load_driver()

    fixtures = tmp_path / "fixtures"
    for spec_id in fixture_ids:
        shutil.copytree(FIXTURES / spec_id, fixtures / spec_id, dirs_exist_ok=True)
    out = tmp_path / "out"

    reviews = [
        LensReview(
            lens=lens,
            findings=[
                Finding(
                    lens="adequacy",
                    severity="concern",
                    file=probe.file,
                    line=1,
                    claim="nothing in the suite would notice this",
                    anchored=True,
                    probe=probe,
                )
                for probe in probes
            ]
            if lens == "adequacy"
            else [],
        )
        for lens in LENSES
    ]

    calls, cells, mutated = [], [], []

    def gate(name, executable, cwd, *, subset=None, executor=None, **_unused):
        calls.append((name, executable, subset, executor))
        if baseline_raises is not None and len(calls) == 1:
            raise baseline_raises
        return GateResult(gate=name, status="pass", tool="stub tests gate")

    @contextlib.contextmanager
    def mutate(container, mutant):
        """`source_mutated`'s clean case — applied, nothing refused. The one
        call in this path that writes inside a cell, so which cell it was
        handed is recorded rather than assumed."""
        mutated.append((container, mutant))
        if mutate_raises is not None and len(mutated) == 1:
            raise mutate_raises
        yield None

    monkeypatch.setattr(driver.mirror_ops, "ensure_mirror", lambda repo, dest: dest)
    # The worktree's own `.saffron/` by default, so `load_policy` reads a real
    # policy declaring real gates rather than a stub that could not be wrong;
    # `saffron_dir` swaps in another real export to vary what it declares.
    monkeypatch.setattr(
        driver.mirror_ops,
        "export_saffron_dir",
        lambda mirror, sha, dest: saffron_dir or REPO,
    )
    monkeypatch.setattr(
        driver.session, "cell_up", lambda **kwargs: cells.append(kwargs["container"])
    )
    monkeypatch.setattr(driver.session, "cell_down", lambda **kwargs: None)
    monkeypatch.setattr(review, "run_review", lambda *a, **kwargs: reviews)
    monkeypatch.setattr(driver.worktree, "source_mutated", mutate)
    monkeypatch.setattr(driver.runner, "run_gate", gate)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "lens-corpus",
            "--fixtures",
            str(fixtures),
            "--out",
            str(out),
            "--repo",
            str(REPO),
            *extra_argv,
        ],
    )

    assert driver.main() == 0
    return SimpleNamespace(
        table=(out / "table.md").read_text(),
        calls=calls,
        cells=cells,
        mutated=mutated,
        out=out,
    )


def test_the_driver_answers_a_probe_through_the_declared_tests_gate(
    tmp_path, monkeypatch
):
    """The wiring, not the shape of a mock: an adequacy finding carrying a
    probe must be applied in the container REVIEW just ran in, and reach
    `run_gate` twice — a baseline and the probe — naming the repo's declared
    `tests` gate at its cell-side path, over the whole suite."""
    pass_ = _drive(tmp_path, monkeypatch)
    cell = "saffron-cell-lenscorpus-sa-0045"

    assert pass_.cells == [cell]
    # The cell was brought up at `tree_base=fixture.head_sha`, so this is the
    # only tree the edit means anything against.
    assert pass_.mutated == [(cell, PROBE)]
    assert [name for name, _e, _s, _x in pass_.calls] == ["tests", "tests"]
    # `/gates`, never `/work`: an in-cell edit to a gate cannot reach the
    # runner that judges the probe (§5.4).
    assert {e for _n, e, _s, _x in pass_.calls} == {Path("/gates/.saffron/gates/tests")}
    # The whole suite both times — a probe asks whether *anything* notices.
    assert [subset for _n, _e, subset, _x in pass_.calls] == [[], []]
    assert all(isinstance(x, runner.CellExecutor) for _n, _e, _s, x in pass_.calls)
    assert {x.container for _n, _e, _s, x in pass_.calls} == {cell}
    assert "1 verified" in pass_.table


def test_a_fixture_that_files_no_probe_pays_for_no_baseline(tmp_path, monkeypatch):
    """The baseline exists to be subtracted from a probe's result, so with no
    probe to ask there is nothing for it to answer — and it is a whole suite
    run, ~15.6s measured, per fixture that files none. Still probed, though:
    `probes.json` is written `[]`, which is what separates a fixture that had
    nothing to apply from one nobody asked."""
    pass_ = _drive(tmp_path, monkeypatch, probes=())

    assert pass_.calls == []
    assert pass_.mutated == []
    assert json.loads((pass_.out / "SA-0045" / "probes.json").read_text()) == []
    # Probed, so it is in the fixture count the second number covers.
    assert "over 1 fixture(s) probed" in pass_.table


def test_skip_probes_runs_the_lenses_and_reaches_no_gate(tmp_path, monkeypatch):
    """A recall-only re-run still costs a cell — the lenses are the spend —
    but applies nothing and reports no second number. Absent, not zero: a pass
    that asked no probe found nothing out about the adequacy lens."""
    pass_ = _drive(tmp_path, monkeypatch, "--skip-probes")

    assert pass_.cells == ["saffron-cell-lenscorpus-sa-0045"]
    assert (pass_.calls, pass_.mutated) == ([], [])
    assert "verified vacuit" not in pass_.table


def test_score_only_re_scores_a_finished_pass_and_starts_no_cell(tmp_path, monkeypatch):
    """`--score-only`'s existing promise, now that it also decides whether the
    second number is rendered: it must start no cell and apply no probe, and
    the table it re-renders from the run JSON must not claim `0 of 0`."""
    _drive(tmp_path, monkeypatch)  # a pass, so there is a run-1.json to score
    pass_ = _drive(tmp_path, monkeypatch, "--score-only")

    assert (pass_.cells, pass_.calls, pass_.mutated) == ([], [], [])
    assert "verified vacuit" not in pass_.table


def test_a_resume_that_ran_no_fixture_renders_no_second_number(tmp_path, monkeypatch):
    """`table.md` is the artifact pasted into `docs/evidence/`, and a resume
    rewrites it. Skipping every fixture applies no probe, so the second number
    is absent — where "0 verified vacuities" would overwrite a real
    measurement with a zero nobody measured, and recall (re-derived from the
    run JSON on disk) would still be there beside it to make it look earned."""
    first = _drive(tmp_path, monkeypatch)
    assert "1 verified vacuity" in first.table

    resumed = _drive(tmp_path, monkeypatch, "--skip-existing")
    assert (resumed.cells, resumed.calls, resumed.mutated) == ([], [], [])
    assert "verified vacuit" not in resumed.table
    assert "declared defects graded" in resumed.table  # recall still rendered


def test_a_partial_resume_says_how_many_fixtures_its_number_covers(
    tmp_path, monkeypatch
):
    """The half-covered case: recall over two fixtures, probes over the one
    this invocation ran. Both numbers are real; only their denominators
    differ, and the rendered table has to say so rather than leave two
    aggregates side by side looking comparable."""
    _drive(tmp_path, monkeypatch)  # SA-0045 alone, so its run-1.json exists
    resumed = _drive(
        tmp_path,
        monkeypatch,
        "--skip-existing",
        fixture_ids=("SA-0045", "SA-0063"),
    )

    assert resumed.cells == ["saffron-cell-lenscorpus-sa-0063"]
    assert "across 2 fixture(s)" in resumed.table  # the recall line
    assert "over 1 fixture(s) probed this invocation" in resumed.table


def test_the_same_probe_filed_by_every_run_is_applied_once(tmp_path, monkeypatch):
    """`--runs 3` files the same probe three times. Applying it three times
    would put a raw total beside a recall line the run count normalises, and
    buy three identical suite runs of the same tree, wasteful at any price."""
    pass_ = _drive(tmp_path, monkeypatch, "--runs", "2")

    assert len(pass_.mutated) == 1
    # A baseline and one probe, never a baseline and two.
    assert [name for name, _e, _s, _x in pass_.calls] == ["tests", "tests"]
    assert "1 of 1 probe(s)" in pass_.table


def test_every_probe_verdict_is_written_beside_the_run_json(tmp_path, monkeypatch):
    """A pass costs roughly $13 and an hour — scaled from the one fixture
    measured end to end, at $1.58 and 500s. Recall survives a crash because the
    run JSON is on disk and `--score-only` re-derives it; a verdict that was
    only printed goes with the process."""
    pass_ = _drive(tmp_path, monkeypatch)

    recorded = json.loads((pass_.out / "SA-0045" / "probes.json").read_text())
    assert [entry["verdict"] for entry in recorded] == ["survived"]
    assert recorded[0]["probe"] == PROBE.model_dump()
    assert recorded[0]["reason"]


def test_a_written_verdict_carries_the_baseline_it_was_subtracted_from(
    tmp_path, monkeypatch
):
    """Item 94, at the JSON boundary where `None` and `()` could collapse: a
    baseline read and green writes `[]`."""
    pass_ = _drive(tmp_path, monkeypatch)

    recorded = json.loads((pass_.out / "SA-0045" / "probes.json").read_text())
    assert [entry["verdict"] for entry in recorded] == ["survived"]
    assert recorded[0]["baseline_failures"] == []
    assert recorded[0]["baseline_tool"] == "stub tests gate"


BASELINE_KEYS = (
    "baseline_failures",
    "baseline_tool",
    "baseline_collected",
    "baseline_summary",
)


def test_a_probe_with_no_baseline_in_hand_writes_null_not_an_empty_list(
    tmp_path, monkeypatch
):
    """The other spelling: a baseline suite that raised left nothing to
    record, and every key says so rather than writing the green `[]`."""
    pass_ = _drive(
        tmp_path,
        monkeypatch,
        baseline_raises=CellRuntimeError("exec for the baseline failed"),
    )

    recorded = json.loads((pass_.out / "SA-0045" / "probes.json").read_text())
    assert [entry["verdict"] for entry in recorded] == ["unproven"]
    assert {key: recorded[0][key] for key in BASELINE_KEYS} == dict.fromkeys(
        BASELINE_KEYS
    )


def test_a_probe_that_raised_still_records_the_baseline_it_was_checked_against(
    tmp_path, monkeypatch
):
    """A raise out of `check_probe` comes after the baseline was read, and so
    does every probe it stopped: `null` there would say it never was."""
    pass_ = _drive(
        tmp_path,
        monkeypatch,
        probes=(PROBE, PROBE_2),
        mutate_raises=CellRuntimeError("write for a probe failed"),
    )

    recorded = json.loads((pass_.out / "SA-0045" / "probes.json").read_text())
    assert [entry["verdict"] for entry in recorded] == ["unproven", "unproven"]
    assert [entry["baseline_failures"] for entry in recorded] == [[], []]
    assert {entry["baseline_tool"] for entry in recorded} == {"stub tests gate"}


def test_a_cell_that_failed_under_a_probe_is_unproven_not_the_end_of_the_pass(
    tmp_path, monkeypatch
):
    """`source_mutated` enters through a container exec, which fails routinely
    — a source file near `MAX_ARG_STRLEN` is a named, real trigger. One raise
    at fixture seven of eight must cost that fixture's probes, not every
    verdict of the pass."""
    pass_ = _drive(
        tmp_path,
        monkeypatch,
        mutate_raises=CellRuntimeError(
            "write for a probe failed: argument list too long"
        ),
    )

    assert "0 of 0" in pass_.table
    assert "1 unproven" in pass_.table
    recorded = json.loads((pass_.out / "SA-0045" / "probes.json").read_text())
    assert [entry["verdict"] for entry in recorded] == ["unproven"]
    assert "argument list too long" in recorded[0]["reason"]


def test_a_raise_stops_that_fixture_rather_than_probing_a_tree_it_cannot_trust(
    tmp_path, monkeypatch
):
    """A raise out of `source_mutated` means the cell's tree may be mutated.

    `source_mutated` raises *after* its `finally` when the undo fails, and in
    that case the file is left mutated (`worktree.py`: "mutant undo for
    {file} failed" and "exited 0 and did not restore the file"). A failed
    *apply* is no safer — `_write_file`'s redirect truncates before `base64`
    writes a byte, which is `SA-0062`'s own defect. Either way the tree's
    state is unknown from here, and the two cases are told apart only by an
    exception's message.

    So a later probe scored against that tree could come back `survived` on an
    edit nobody undid — inflating the one number this whole exercise produces,
    with nothing in the record saying the tree was dirty. Stop at the fixture,
    not at the pass: the cell is per-fixture, so the next one is trustworthy
    again.
    """
    pass_ = _drive(
        tmp_path,
        monkeypatch,
        probes=(PROBE, PROBE_2),
        mutate_raises=CellRuntimeError("mutant undo for scope.py failed: no such file"),
    )

    # The second probe was never applied — the assertion that matters, because
    # under the defect it was applied and scored against a dirty tree.
    assert [mutant for _container, mutant in pass_.mutated] == [PROBE]

    recorded = json.loads((pass_.out / "SA-0045" / "probes.json").read_text())
    assert [entry["verdict"] for entry in recorded] == ["unproven", "unproven"]
    assert "mutant undo for scope.py failed" in recorded[0]["reason"]
    assert "unknown state" in recorded[1]["reason"]
    assert "0 of 0" in pass_.table
    assert "2 unproven" in pass_.table


def test_a_head_declaring_no_tests_gate_is_unproven_and_not_an_abort(
    tmp_path, monkeypatch
):
    """`--fixtures` points wherever it is told, so "every shipped fixture's
    head declares a `tests` gate" does not bound this input. A head that
    declares none has said nothing about the adequacy lens: `unproven`, named
    in the record, in no denominator — and the pass goes on to the next
    fixture, where a `KeyError` would discard every fixture after it and the
    table a paid pass had already earned."""
    pass_ = _drive(
        tmp_path,
        monkeypatch,
        saffron_dir=_saffron_dir_without_a_tests_gate(tmp_path / "no-tests-gate"),
    )

    assert (pass_.calls, pass_.mutated) == ([], [])
    assert "0 of 0" in pass_.table
    assert "1 unproven" in pass_.table
    assert "SA-0045" in pass_.table


def test_every_shipped_fixture_s_head_declares_a_tests_gate():
    """What keeps the driver's `unproven` branch a fallback rather than the
    path every fixture takes. Read from git at each fixture's own `head_sha`,
    the commit the cell is brought up at — the policy the driver itself will
    resolve `tests` from, not this worktree's."""
    for fixture in corpus.load_corpus(FIXTURES):
        raw = subprocess.run(
            ["git", "show", f"{fixture.head_sha}:.saffron/policy.yaml"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        declared = Policy.model_validate(yaml.safe_load(raw)).gates
        assert "tests" in declared, fixture.spec_id


def test_the_baseline_pass_s_published_aggregate_is_re_derivable():
    """The record's headline, re-derived from the runs beside it rather than
    read from the prose. A record whose number nobody can recompute is the
    defect `docs/BACKLOG.md` item 91 was filed for, one level up."""
    fixtures = corpus.load_corpus(FIXTURES)
    runs = {
        f.spec_id: [
            lens_scoring.reviews_from_json(p.read_text())
            for p in sorted((BASELINE / f.spec_id).glob("run-*.json"))
        ]
        for f in fixtures
    }
    scored = corpus.score_corpus(fixtures, runs)
    record = RECORD.read_text()
    table = (BASELINE / "table.md").read_text()

    # The whole rendered headline, not the `graded/declared` substring the plan
    # suggested: this record discusses pass 1's `4/12` too, so a bare `in`
    # matches whichever number is written anywhere and pins neither. Verified
    # against a mutant that rewrote the headline alone and went unnoticed.
    headline = table.splitlines()[0]
    assert f"**{scored.graded}/{scored.declared} declared defects graded**" in headline
    assert headline in record
    assert scored.dropped == ()
    assert (scored.graded, scored.declared) == (3, 12)


def test_the_baseline_s_probe_verdicts_are_re_derivable():
    """The second number, the same way. Hand-aggregated in the record because
    no invocation printed it, which is exactly why it needs pinning: the eight
    `probes.json` files are the source and the prose must agree with them."""
    fixtures = corpus.load_corpus(FIXTURES)
    results = {
        f.spec_id: [
            probe_check.ProbeResult(
                p["verdict"], p["reason"], tuple(p.get("failures") or ())
            )
            for p in json.loads((BASELINE / f.spec_id / "probes.json").read_text())
        ]
        for f in fixtures
    }
    score = corpus.score_probes(results, runs=1)

    assert (score.survived, score.killed, score.unproven) == (8, 2, 0)
    assert score.fixtures == 8
    assert "8 verified vacuities" in RECORD.read_text()


def test_the_baseline_pass_s_verdicts_carry_no_baseline_and_never_will():
    """Item 94's own statement, as a fact of the suite rather than only of the
    prose: adding the field cannot retroactively populate a pass already run.

    A probe is authored by the lens per run — `SA-0054`'s re-run named two
    *different* edits — so re-running yields different probes rather than an
    audit of these. The 2 of 8 verified vacuities that rest on a cell baseline
    nobody can inspect stay that way permanently, and a reader must be able to
    *say so* rather than read the missing key as a baseline that was green.
    """
    unrecorded = 0
    for fixture in corpus.load_corpus(FIXTURES):
        for entry in json.loads(
            (BASELINE / fixture.spec_id / "probes.json").read_text()
        ):
            assert "baseline_failures" not in entry, fixture.spec_id
            unrecorded += 1
    assert unrecorded == 10


def test_every_shipped_fixture_probed_at_baseline_has_a_probe_record():
    """An empty `probes.json` is coverage and an absent one is not, so the
    baseline directory has to carry a file for every fixture — including the
    two that filed nothing, which is item 92.1's fix showing in a pass."""
    empty = set()
    for fixture in corpus.load_corpus(FIXTURES):
        path = BASELINE / fixture.spec_id / "probes.json"
        assert path.is_file(), fixture.spec_id
        if not json.loads(path.read_text()):
            empty.add(fixture.spec_id)
    assert empty == {"SA-0046", "SA-0055"}


def _dirty_restore_seen():
    # SA-0062's `dirty-restore`: correctness-owned, blocker floor, 386-426.
    return _finding("saffron/cell/worktree.py", 400, "restores over uncommitted work")


def test_each_run_is_scored_as_its_own_corpus_pass(sa0062):
    """Item 93. The headline counts a defect graded in any run, so it rises with
    --runs; the per-run totals are the spread, and they disagree here."""
    runs = {sa0062.spec_id: [_run([_dirty_restore_seen()]), _run()]}
    assert corpus.score_corpus([sa0062], runs).graded == 1
    per_run = corpus.graded_per_run([sa0062], runs)
    assert [(s.graded, s.declared) for s in per_run if s is not None] == [
        (1, 2),
        (0, 2),
    ]


def test_the_table_prints_the_per_run_totals_beside_the_best_of_n_headline(sa0062):
    runs = {sa0062.spec_id: [_run([_dirty_restore_seen()]), _run()]}
    table = corpus.render_corpus_table(
        [sa0062],
        corpus.score_corpus([sa0062], runs),
        corpus.anchored_blockers(runs),
        per_run=corpus.graded_per_run([sa0062], runs),
    )
    assert table.splitlines()[0].startswith("**1/2 declared defects graded**")
    assert "Per run, each scored alone: 1/2 · 0/2 graded" in table


def test_a_single_run_pass_prints_no_per_run_line(sa0062):
    """The baseline's `table.md` is pinned; one run has no spread to state."""
    runs = {sa0062.spec_id: [_run()]}
    table = corpus.render_corpus_table(
        [sa0062],
        corpus.score_corpus([sa0062], runs),
        corpus.anchored_blockers(runs),
        per_run=corpus.graded_per_run([sa0062], runs),
    )
    assert "Per run" not in table


def test_a_run_index_no_fixture_survived_reads_as_unscored_not_zero(sa0062):
    errored = [LensReview(lens="correctness", findings=[], error="boom")]
    runs = {sa0062.spec_id: [_run(), errored]}
    assert corpus.graded_per_run([sa0062], runs)[1] is None


def test_every_dollar_figure_in_the_baseline_record_is_one_a_run_produced():
    """The strong form the second pass's record established. Every `$N.NN` the
    record prints must be a per-lens cost from the run JSON, a per-fixture or
    published total over them, a declared budget, or one of the two invocation
    totals the driver printed — never a figure nobody can source."""
    per_lens, per_fixture = set(), set()
    for fixture in corpus.load_corpus(FIXTURES):
        runs = json.loads((BASELINE / fixture.spec_id / "run-1.json").read_text())
        costs = [r.get("cost_usd", r.get("cost_usd_est", 0.0)) for r in runs]
        per_lens.update(f"${c:.2f}" for c in costs)
        per_fixture.add(f"${sum(costs):.2f}")
    published = sum(
        sum(
            r.get("cost_usd", r.get("cost_usd_est", 0.0))
            for r in json.loads((BASELINE / f.spec_id / "run-1.json").read_text())
        )
        for f in corpus.load_corpus(FIXTURES)
    )
    # The two invocation totals the driver printed, and the discarded run's own
    # cost — sourced from the archive outside the repo, so named here as the
    # record names it rather than recomputed.
    printed = {"$17.31", "$2.92", "$20.23", "$3.70", "$13.61"}
    budgets = {"$4.0", "$20.0", "$1.61", "$12.90"}
    allowed = per_lens | per_fixture | printed | budgets | {f"${published:.2f}"}

    found = set(re.findall(r"\$\d+\.\d+", RECORD.read_text()))
    assert found <= allowed, found - allowed
    assert f"${published:.2f}" == "$16.53"
