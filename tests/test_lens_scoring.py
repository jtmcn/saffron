"""The scoring predicate for Track A's lens harness (BACKLOG item 79).

The predicate is the part of the harness that can be silently wrong: a paid
pass produces free-text claims, and something has to say whether a claim is the
declared defect. These tests are that something's guard, and the first of them
is the one that matters — it scores the real recorded output of the run item 79
is about, whose answer is already written down.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from harness import lens_scoring
from saffron.agents.findings import Finding, Severity
from saffron.phases.review import LENSES, LensReview

FIXTURE = Path(__file__).parent.parent / "docs" / "evidence" / "fixtures" / "SA-0062"


@pytest.fixture
def sa0062() -> lens_scoring.Fixture:
    return lens_scoring.load_fixture(FIXTURE)


def _finding(
    *,
    lens: str = "correctness",
    severity: Severity = "blocker",
    file: str = "saffron/cell/worktree.py",
    line: int = 422,
    claim: str = "the undo restores HEAD over uncommitted work",
    anchored: bool = True,
) -> Finding:
    """Named parameters rather than `**kwargs` over a dict: a merged dict widens
    `severity` to `str` and the `types` gate fails on the call."""
    return Finding(
        lens=lens,
        severity=severity,
        file=file,
        line=line,
        claim=claim,
        anchored=anchored,
    )


def _reviews(*findings: Finding) -> list[LensReview]:
    """A *complete* run — every lens `score_run` expects, the findings hung on
    the first. Complete because a run missing a lens is refused, and a helper
    that quietly returned one lens would exempt every test below from that."""
    return [
        LensReview(lens=lens, findings=list(findings) if lens == "correctness" else [])
        for lens in LENSES
    ]


def test_the_fixture_carries_its_frozen_inputs(sa0062):
    """A pass varies the prompt and nothing else, so the four inputs are files
    on disk rather than a rebuild from the ledger and the git history."""
    assert sa0062.diff.startswith("diff --git")
    assert "SA-0062" in sa0062.spec_body or sa0062.spec_body.strip()
    assert "witness" in sa0062.gates
    assert sa0062.context_md.strip()
    assert [d.id for d in sa0062.defects] == ["dirty-restore", "truncating-write"]


def test_the_calibration_case_reproduces_the_run_it_was_built_from(sa0062):
    """The one run whose answer is known: 0 of 2, both ways. A predicate that
    cannot reproduce this may not be trusted with a run nobody has read."""
    scores = lens_scoring.score_run(sa0062, sa0062.recorded_reviews())
    assert [s.seen for s in scores.values()] == [False, False]
    assert [s.graded for s in scores.values()] == [False, False]


def test_a_finding_on_the_defects_lines_without_its_words_is_not_the_defect(sa0062):
    """The collision this predicate exists to survive. The adequacy lens filed a
    concern at worktree.py:379 — inside `truncating-write`'s 366-426 — saying
    the raise is untested. That is a claim about the test, not about what the
    raise leaves on disk. Positional matching alone scores it a hit."""
    adequacy = _finding(
        lens="adequacy",
        severity="concern",
        line=379,
        claim=(
            "Deleting the `if done.returncode != 0: raise ...` block at lines "
            "379-382 keeps every test green."
        ),
    )
    scores = lens_scoring.score_run(sa0062, _reviews(adequacy))
    assert scores["truncating-write"].seen is False


def test_a_claim_about_the_write_is_not_credited_to_the_undo(sa0062):
    """Both defects live in one call chain, so their ranges overlap and the
    phrases are the only thing telling them apart. Verbatim from the first
    scoring pass, run 1, where the fixture got this backwards: the contract
    lens filed the truncating write as a blocker at the *call site* (418, not
    `_write_file`'s own lines) and quoted `witness.py`'s "understate a dirty
    tree". A `dirty` phrase on the undo scored that, and the pass reported the
    write missed and the undo raised — both wrong."""
    contract = _finding(
        lens="contract",
        line=418,
        claim=(
            "`source_mutated` writes the mutant via `_write_file`, whose script "
            "(`printf ... | base64 -d > path`, line 377-378) truncates the "
            "destination as part of opening the redirect before `base64 -d` "
            "produces a byte. `witness.py`'s own contract comment (lines 78-85) "
            "calls it the one case that can 'understate a dirty tree'."
        ),
    )
    scores = lens_scoring.score_run(sa0062, _reviews(contract))
    assert scores["truncating-write"].seen is True
    assert scores["dirty-restore"].seen is False


def test_a_claim_about_the_undo_is_not_credited_to_the_write(sa0062):
    """The same boundary from the other side, verbatim from run 2."""
    correctness = _finding(
        line=422,
        claim=(
            "`source_mutated`'s undo is `git checkout HEAD -- <file>`, which "
            "silently discards *any* uncommitted change to that file, not just "
            "the mutation it applied."
        ),
    )
    scores = lens_scoring.score_run(sa0062, _reviews(correctness))
    assert scores["dirty-restore"].seen is True
    assert scores["truncating-write"].seen is False


def test_a_finding_with_the_defects_words_on_its_lines_is_seen(sa0062):
    hit = _finding(
        line=377,
        claim="the `>` redirect truncates the file before base64 -d writes it",
    )
    scores = lens_scoring.score_run(sa0062, _reviews(hit))
    assert scores["truncating-write"].seen is True
    assert scores["truncating-write"].graded is True


def test_seen_ignores_severity_and_graded_does_not(sa0062):
    """Two numbers, because they answer different questions. Track C wants to
    know whether a prompt change made the lens *see* the defect; item 79's exit
    criterion is about the grade it gave. A lens that sees a critical defect and
    files it as a note has moved, and one number would hide that."""
    noted = _finding(severity="note")
    scores = lens_scoring.score_run(sa0062, _reviews(noted))
    assert scores["dirty-restore"].seen is True
    assert scores["dirty-restore"].graded is False


def test_an_unanchored_finding_is_never_seen(sa0062):
    """`anchor` already ruled it points at nothing real (§5.5). Counting it
    would let a hallucinating lens score."""
    scores = lens_scoring.score_run(sa0062, _reviews(_finding(anchored=False)))
    assert scores["dirty-restore"].seen is False


def test_a_finding_in_another_file_is_not_seen(sa0062):
    other = _finding(file="saffron/gates/runner.py", line=422)
    scores = lens_scoring.score_run(sa0062, _reviews(other))
    assert scores["dirty-restore"].seen is False


def test_a_finding_outside_the_line_range_is_not_seen(sa0062):
    """worktree.py:358 is the correctness lens's real UTF-8 concern, eight lines
    above `truncating-write`'s range and a different defect."""
    scores = lens_scoring.score_run(sa0062, _reviews(_finding(line=358)))
    assert scores["dirty-restore"].seen is False
    assert scores["truncating-write"].seen is False


def test_a_pass_counts_runs_that_saw_it_not_findings_that_matched(sa0062):
    """k/n is over runs. Two findings in one run that both match are one run
    that saw it — otherwise a verbose lens outscores an accurate one."""
    twice = _reviews(_finding(line=422), _finding(line=423))
    silent = _reviews()
    passes = lens_scoring.score_pass(sa0062, [twice, silent, silent])
    assert passes["dirty-restore"].seen == 1
    assert passes["dirty-restore"].runs == 3


def test_calibrate_refuses_a_predicate_that_moved(sa0062, monkeypatch):
    """The calibration is a gate on the paid pass, not a comment. Fixture says
    the recorded run scores 0; a predicate that now scores it 1 stops the run."""
    monkeypatch.setattr(sa0062, "recorded_seen", 1)
    with pytest.raises(lens_scoring.CalibrationError, match="recorded"):
        lens_scoring.calibrate(sa0062)


def test_calibrate_passes_on_the_fixture_as_shipped(sa0062):
    lens_scoring.calibrate(sa0062)


def test_an_errored_lens_is_never_scored_as_a_lens_that_found_nothing(sa0062):
    """`error` is not `fail` (§5.4), and `run_lens`'s own comment says a lens
    that did not run must never read as a lens that found nothing. Scoring the
    survivors would land the missing lens's defect as a miss — a number about
    the harness wearing the shape of a number about the prompt."""
    broke = LensReview(lens="correctness", error="not the schema: nope")
    with pytest.raises(lens_scoring.LensErrored, match="not the schema"):
        lens_scoring.score_run(sa0062, [broke])


def test_a_run_with_an_errored_lens_is_dropped_from_n_and_counted(sa0062):
    """Dropped, not fatal: one bad lens must not throw away a paid pass. But n
    falls to what was actually scored and the drop is carried to the table."""
    good = _reviews(_finding(line=422))
    broke = [LensReview(lens="contract", error="max turns")]
    passes = lens_scoring.score_pass(sa0062, [good, broke, good])
    assert passes["dirty-restore"].runs == 2
    assert passes["dirty-restore"].seen == 2
    assert passes["dirty-restore"].errored == 1
    assert "1 run(s) dropped" in lens_scoring.render_table(sa0062, passes)


def test_a_run_missing_a_lens_is_not_a_sample_either(sa0062):
    """`error` is not the only way a lens says nothing about the diff.

    An earlier revision checked `error` alone, so `score_run(fixture, [])`
    scored every defect missed and `score_pass` rendered three of those as a
    complete table of zeroes over n=3 — the measurement its own docstring says
    it refuses, reached by a route that never sets `error`. Unreachable from
    today's driver, which always returns one result per lens; reachable the
    moment `LENSES` changes under Track C, which is what this harness is for.
    """
    with pytest.raises(lens_scoring.LensErrored, match="no result for"):
        lens_scoring.score_run(sa0062, [])
    partial = [LensReview(lens="correctness", findings=[_finding()])]
    with pytest.raises(lens_scoring.LensErrored, match="adequacy, contract"):
        lens_scoring.score_run(sa0062, partial)
    # And the pass drops such a run rather than dying on it, exactly as it
    # drops an errored one.
    dropped = lens_scoring.score_pass(sa0062, [_reviews(_finding()), partial])
    assert dropped["dirty-restore"].runs == 1
    assert dropped["dirty-restore"].errored == 1


def test_a_pass_recorded_before_a_lens_moved_names_the_set_it_ran(sa0062):
    """The escape hatch the default needs. `expect` defaults to today's lens
    set so a caller is guarded without saying anything; a pass recorded under a
    different set is scored against the set it actually ran, or it is refused
    for a change made after it was measured."""
    two_lenses = [
        LensReview(lens="correctness", findings=[_finding()]),
        LensReview(lens="contract", findings=[]),
    ]
    scores = lens_scoring.score_run(
        sa0062, two_lenses, expect=("correctness", "contract")
    )
    assert scores["dirty-restore"].seen is True


def test_a_pass_with_nothing_left_to_score_is_not_a_table_of_zeroes(sa0062):
    """`0/0` renders like a measurement and is not one. Covers `--runs 0` and a
    pass every run of which errored."""
    with pytest.raises(lens_scoring.LensErrored, match="no run survived"):
        lens_scoring.score_pass(sa0062, [])


def test_two_defects_may_not_share_a_phrase(sa0062, tmp_path):
    """A shared phrase credits one claim to both defects, so k/n stops being
    per-defect. Narrow by construction: it catches a copied list, not the
    failure this fixture had — `dirty` was unique and still matched a claim
    about the other defect."""
    declaration = (FIXTURE / "fixture.toml").read_text()
    (tmp_path / "fixture.toml").write_text(
        declaration.replace(
            'must_mention = ["truncat"', 'must_mention = ["uncommitted"'
        )
    )
    with pytest.raises(lens_scoring.FixtureError, match="both declare"):
        lens_scoring.load_fixture(tmp_path)


def test_one_defects_phrase_may_not_contain_anothers(sa0062, tmp_path):
    """The same collision by containment rather than equality. The phrases are
    substrings of a claim, so `committed` on one defect swallows every claim
    matching the other's `uncommitted` — an equality check sees two different
    strings and passes it."""
    declaration = (FIXTURE / "fixture.toml").read_text()
    (tmp_path / "fixture.toml").write_text(
        declaration.replace('must_mention = ["truncat"', 'must_mention = ["committed"')
    )
    with pytest.raises(lens_scoring.FixtureError, match="inside"):
        lens_scoring.load_fixture(tmp_path)


def test_a_defect_id_may_not_be_declared_twice(sa0062, tmp_path):
    """`score_run` keys on `id`, so the second declaration overwrites the first
    and a declared defect is scored by nobody — while `render_table`, which
    walks `fixture.defects`, prints two rows carrying the survivor's numbers
    under names that look different. It also disables the shared-phrase check
    between the two, which skips a defect against itself."""
    declaration = (FIXTURE / "fixture.toml").read_text()
    (tmp_path / "fixture.toml").write_text(
        declaration.replace('id = "truncating-write"', 'id = "dirty-restore"')
    )
    with pytest.raises(lens_scoring.FixtureError, match="declared twice"):
        lens_scoring.load_fixture(tmp_path)


def test_a_fixture_missing_a_key_is_a_fixture_error_not_a_keyerror(sa0062, tmp_path):
    """A `KeyError` out of a loader reads as a bug in the loader."""
    declaration = (FIXTURE / "fixture.toml").read_text()
    (tmp_path / "fixture.toml").write_text(
        declaration.replace('owner = "correctness"', "")
    )
    with pytest.raises(lens_scoring.FixtureError, match="no owner"):
        lens_scoring.load_fixture(tmp_path)


PASS_2026_09_07 = (
    Path(__file__).parent.parent
    / "docs"
    / "evidence"
    / "passes"
    / "2026-09-07-lens-scoring-first-pass"
)


# The three lenses this pass actually ran. Named rather than left to the
# default: if Track C adds or drops one, this record is still a table these
# three produced, and scoring it against a later set would refuse it for a
# change made long after it was measured.
PASS_2026_09_07_LENSES = ("correctness", "contract", "adequacy")


def _recorded_pass() -> list[list[LensReview]]:
    return [
        lens_scoring.reviews_from_json(
            (PASS_2026_09_07 / f"run-{index}.json").read_text()
        )
        for index in (1, 2, 3)
    ]


def test_the_first_pass_s_published_table_is_re_derivable(sa0062):
    """The evidence record's numbers, recomputed from the pass's own JSON.

    The raw runs used to live only under `~/.saffron/`, which made the table in
    `docs/evidence/2026-09-07-lens-scoring-first-pass.md` unreproducible by
    anyone but its author — item 79's own complaint, one level up. With them in
    the repo, a predicate change that silently moves a published number fails
    here instead of being noticed by nobody.
    """
    scores = lens_scoring.score_pass(
        sa0062, _recorded_pass(), expect=PASS_2026_09_07_LENSES
    )
    assert (scores["dirty-restore"].seen, scores["dirty-restore"].graded) == (2, 2)
    assert (scores["truncating-write"].seen, scores["truncating-write"].graded) == (
        3,
        2,
    )
    assert all(s.runs == 3 and s.errored == 0 for s in scores.values())


def test_every_run_of_the_first_pass_filed_an_anchored_blocker(sa0062):
    """The claim the evidence record got wrong, pinned to the data.

    The doc read "two of the three runs would have blocked", taking it from
    `dirty-restore`'s 2/3. Anchored blockers per run are 1, 2, 1: run 1's
    contract lens filed the truncating write as a blocker at 418. §5.5 routes
    any single anchored blocker to REBUT, so no run of this pass was green,
    against 0 blockers on the production run of the same range.
    """
    per_run = [
        sum(
            f.severity == "blocker" and f.anchored
            for review in run
            for f in review.findings
        )
        for run in _recorded_pass()
    ]
    assert per_run == [1, 2, 1]


RECORD_2026_09_07 = (
    Path(__file__).parent.parent
    / "docs"
    / "evidence"
    / "2026-09-07-lens-scoring-first-pass.md"
)


def test_the_first_pass_s_published_costs_are_re_derivable_too(sa0062):
    """The table was pinned to the data and the paragraph beside it was not.

    That asymmetry published a wrong number: the per-lens range read
    $0.36-$0.92, which is run 1's maximum rather than the pass's — run 3's
    adequacy lens spent $1.01. The claim it supports (no lens came near the
    $4.00 ceiling) survived, in the one paragraph whose subject is that the
    budget is not the confound. Both figures now fail here when they drift.
    """
    costs = [r.cost_usd for run in _recorded_pass() for r in run]
    record = RECORD_2026_09_07.read_text()
    assert f"${sum(costs):.2f}" in record
    assert f"${min(costs):.2f}–${max(costs):.2f}" in record


# The gate summary a lens is shown, split the way production splits it: a
# repo's declared gate executes a tool and reports its version (§5.4), while a
# host-side core gate executes nothing and reports none. `revert` is core and
# still names one — it re-invokes the `tests` runner and inherits its tool
# (`revert_gate`). `witness` inherits the same way (`witness_gate`); it is on
# the no-tool list below because it *skipped* on this spec, which declares no
# mutants, not because it executes nothing.
GATES_NAMING_A_TOOL = {
    "format": "ruff",
    "lint": "ruff",
    "types": "ty",
    "tests": "pytest",
    "shacl": "PySHACL",
    "structure": "ast-grep",
    "revert": "pytest",
}
GATES_NAMING_NO_TOOL = frozenset(
    {"scope", "integrity", "size", "witness", "committed", "census", "criteria"}
)


def test_the_frozen_gate_summary_names_the_tools_the_original_run_named(sa0062):
    """Item 88's confound, closed on the fixture that carried it.

    `gates.txt` was rebuilt from `gate_results` rows that had no `tool` column,
    so all 14 lines read `no tool reported` — and §5.4 makes `tool` exactly what
    separates a gate that ran from one that never did. A lens told fourteen
    gates ran and not one of them named a tool has structural reason to distrust
    them and dig harder, which is the direction of every conclusion the first
    pass drew. The tools are restored from `baseline.json` in the batch tree,
    written by the same container in the same run.

    Seven of the fourteen say `no tool reported` in production too, and this
    pins that half as well: a later "fix" that invents a tool for a core gate
    would be a second deviation, not a repair.
    """
    lines = {
        line.split(":", 1)[0].removeprefix("- "): line
        for line in sa0062.gates.splitlines()
    }
    assert set(lines) == set(GATES_NAMING_A_TOOL) | GATES_NAMING_NO_TOOL
    for gate, tool in GATES_NAMING_A_TOOL.items():
        assert f"({tool} " in lines[gate], lines[gate]
    for gate in GATES_NAMING_NO_TOOL:
        assert "(no tool reported)" in lines[gate], lines[gate]


PASS_2026_09_08 = (
    Path(__file__).parent.parent
    / "docs"
    / "evidence"
    / "passes"
    / "2026-09-08-lens-scoring-second-pass"
)

RECORD_2026_09_08 = (
    Path(__file__).parent.parent
    / "docs"
    / "evidence"
    / "2026-09-08-lens-scoring-second-pass.md"
)


def _second_pass() -> list[list[LensReview]]:
    return [
        lens_scoring.reviews_from_json(
            (PASS_2026_09_08 / f"run-{index}.json").read_text()
        )
        for index in (1, 2, 3)
    ]


def test_the_second_pass_s_published_table_is_re_derivable(sa0062):
    """Item 88's pass, scored by the same predicate as the first.

    The fixture it ran against is this repository's shipped one, so a predicate
    change moves both published tables or neither — which is the property that
    makes the two comparable at all.
    """
    scores = lens_scoring.score_pass(
        sa0062, _second_pass(), expect=PASS_2026_09_07_LENSES
    )
    assert (scores["dirty-restore"].seen, scores["dirty-restore"].graded) == (1, 1)
    assert (scores["truncating-write"].seen, scores["truncating-write"].graded) == (
        2,
        2,
    )
    assert all(s.runs == 3 and s.errored == 0 for s in scores.values())


def test_naming_the_gates_tools_moved_the_blocker_count_by_zero():
    """Item 88's answer, and the one number the item turns on.

    The frozen `gates.txt` said `no tool reported` on all 14 lines, which was
    the leading suspect for a harness filing blockers where production filed
    none. With the tools restored the per-run counts are 1, 1, 2 against the
    first pass's 1, 2, 1 — four either way, and every run of both would route to
    REBUT under §5.5 against production's zero. A later pass that reads the
    suspect as still open fails here.
    """

    def per_run(runs):
        return [
            sum(
                f.severity == "blocker" and f.anchored
                for review in run
                for f in review.findings
            )
            for run in runs
        ]

    assert per_run(_second_pass()) == [1, 1, 2]
    assert sum(per_run(_second_pass())) == sum(per_run(_recorded_pass()))
    # Not "most runs": every run of both passes filed at least one.
    assert all(count > 0 for count in per_run(_second_pass()))


# The two figures in the second-pass record that no run JSON can produce: the
# per-lens ceiling both passes gave (declared, `--lens-budget-usd`) and the one
# production gave — which is *derived*, not declared: SA-0062's spec declares
# `budget_usd: 12`, and $3.30 is the remainder `critic_budget()` left at REVIEW
# time. Named here because the record's "no lens came near either ceiling"
# argument compares measured spend against them, and a test that let any
# unrecognised dollar figure through would not be checking that argument at all.
LENS_CEILINGS = frozenset({"$4.00", "$3.30"})


def test_every_dollar_figure_in_the_second_pass_record_is_re_derivable():
    """Stronger than "the total appears somewhere", which is what the first
    pass's equivalent asserts — and measured: mutating this record's headline
    total from $4.84 to $4.85 leaves that assertion passing, because $4.84 also
    sits in the comparison table two sections down. The first pass published a
    wrong per-lens range through exactly that gap: a table pinned to the data
    and the paragraph beside it not.

    So the direction is reversed. Every `$N.NN` the record prints must be one
    this pass's JSON produces, the first pass's JSON produces, or a ceiling
    named above — and a figure that drifts fails whichever sentence it is in.
    """
    costs = [r.cost_usd for run in _second_pass() for r in run]
    per_run = [sum(r.cost_usd for r in run) for run in _second_pass()]
    derivable = {
        f"${sum(costs):.2f}",
        f"${min(costs):.2f}",
        f"${max(costs):.2f}",
        f"${sum(r.cost_usd for run in _recorded_pass() for r in run):.2f}",
        *(f"${cost:.2f}" for cost in per_run),
    } | LENS_CEILINGS

    record = RECORD_2026_09_08.read_text()
    printed = set(re.findall(r"\$\d+\.\d{2}", record))
    assert printed <= derivable, printed - derivable
    # And the ones the readings actually argue from are present, not merely
    # permitted: a record that stopped printing them would satisfy a subset.
    assert {f"${sum(costs):.2f}", f"${min(costs):.2f}", f"${max(costs):.2f}"} <= printed
    assert f"${min(costs):.2f}–${max(costs):.2f}" in record
