"""The scoring predicate for Track A's lens harness (BACKLOG item 79).

The predicate is the part of the harness that can be silently wrong: a paid
pass produces free-text claims, and something has to say whether a claim is the
declared defect. These tests are that something's guard, and the first of them
is the one that matters — it scores the real recorded output of the run item 79
is about, whose answer is already written down.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from harness import lens_scoring
from saffron.agents.findings import Finding, Severity
from saffron.phases.review import LensReview

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
    return [LensReview(lens="correctness", findings=list(findings))]


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
    concern at worktree.py:379 — inside `truncating-write`'s 366-382 — saying
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
    passes = lens_scoring.score_passes(sa0062, [twice, silent, silent])
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
