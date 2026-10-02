"""The pre-registered grade of Jev's noise score on review notes."""

from __future__ import annotations

import json

from harness import jev_grade as jg
from harness import jev_observe as jo


def _notes(verified: str, disposition: str, n: int, noise: float | None) -> list:
    return [jg.Note(verified, disposition, noise)] * n


def test_forty_noise_notes_half_caught_and_one_in_twenty_acted_on_passes():
    notes = (
        _notes("not-a-defect", "no-action", 20, 0.5)
        + _notes("not-a-defect", "no-action", 20, 0.1)
        + _notes("real", "fixed-in-review", 1, 0.9)
        + _notes("real", "fixed-in-review", 19, 0.1)
    )
    assert jg.grade(notes).verdict == "pass"


def test_one_noise_note_short_of_half_caught_fails():
    notes = _notes("not-a-defect", "no-action", 19, 0.5) + _notes(
        "not-a-defect", "no-action", 21, 0.1
    )
    assert jg.grade(notes).verdict == "fail"


def test_two_acted_on_notes_flagged_in_twenty_fails():
    notes = (
        _notes("not-a-defect", "no-action", 40, 0.9)
        + _notes("real", "operator-decided", 2, 0.5)
        + _notes("real", "operator-decided", 18, 0.1)
    )
    assert jg.grade(notes).verdict == "fail"


def test_under_forty_noise_notes_decides_nothing():
    notes = _notes("not-a-defect", "no-action", 39, 0.9)
    assert jg.grade(notes).verdict == "inconclusive"


def test_a_note_with_no_score_counts_unflagged():
    notes = _notes("not-a-defect", "no-action", 40, None)
    grade = jg.grade(notes)
    assert (grade.noise, grade.caught) == (40, 0)


def test_a_real_note_left_alone_and_an_unverified_note_count_in_neither_class():
    notes = _notes("real", "no-action", 3, 0.9) + _notes(
        "unverified", "fixed-pre-cell", 3, 0.9
    )
    grade = jg.grade(notes)
    assert (grade.noise, grade.acted, grade.flagged_acted) == (0, 0, 0)


def _round_files(schema: int | None) -> tuple[str, str, str]:
    findings = [
        {"id": "aa", "severity": "note"},
        {"id": "bb", "severity": "concern"},
    ]
    label = {"verified": "not-a-defect", "disposition": "no-action"}
    labels: dict = {"findings": {"aa": label, "bb": label}}
    if schema is not None:
        labels["schema"] = schema
    answers = [jo.Answer("Q2", fid, {"0": 0.6, "1": 0.4}) for fid in ("aa", "bb")]
    r = jo.ReviewRound("pr-review", "SA-0901", 1, "abc", "", [], [], [], "")
    return json.dumps(findings), json.dumps(labels), jo.to_turtle(r, "m", answers)


def test_a_schema_2_round_yields_its_notes_with_their_noise_score():
    assert jg.round_notes(*_round_files(2)) == [
        jg.Note("not-a-defect", "no-action", 0.6)
    ]


def test_a_schema_1_round_yields_nothing():
    assert jg.round_notes(*_round_files(None)) == []


def test_a_round_jev_never_scored_yields_its_notes_unscored():
    findings, labels, _ = _round_files(2)
    assert jg.round_notes(findings, labels, None) == [
        jg.Note("not-a-defect", "no-action", None)
    ]


def test_a_review_round_counts_only_when_saved_on_or_after_the_start():
    assert not jg.counts(json.dumps({"commit": "abc"}))
    assert not jg.counts(json.dumps({"saved_at": "2026-10-02T23:59:59+00:00"}))
    assert jg.counts(json.dumps({"saved_at": jg.STARTS}))
