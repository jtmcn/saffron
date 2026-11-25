"""A review round's findings block, the ids that keep each label on its
finding, and the file the spec loop saves them in."""

from __future__ import annotations

import json

import pytest

from harness import review_round as jo


def _report(findings: object) -> str:
    return (
        "## Findings\n\n- prose\n\n```json\n"
        + json.dumps({"findings": findings})
        + "\n```\n"
    )


def _finding(**over: object) -> dict:
    return {
        "severity": "blocker",
        "criterion": 1,
        "file": "a.py",
        "line": 3,
        "claim": "wrong",
        **over,
    }


def test_the_last_json_block_is_the_findings():
    text = '```json\n{"findings": []}\n```\n' + _report([_finding()])
    assert jo.parse_block(text) == [jo.Finding("blocker", 1, "a.py", 3, "wrong")]


def test_a_criterion_written_as_a_digit_string_is_its_number():
    """#544's Standards seat wrote `"1"`, and the round was lost (b-0e3528)."""
    assert jo.parse_block(_report([_finding(criterion="1")]))[0].criterion == 1
    with pytest.raises(jo.BlockError):
        jo.parse_block(_report([_finding(criterion="one")]))


def test_an_empty_list_is_a_report_with_no_findings():
    assert jo.parse_block(_report([])) == []


@pytest.mark.parametrize(
    "text",
    [
        "## Findings\n\nno block here\n",
        "```json\n{not json\n```\n",
        _report("not a list"),
        _report([_finding(severity="fatal")]),
        _report([_finding(line="3")]),
        _report([_finding(criterion=True)]),
        _report([_finding(claim=None)]),
    ],
)
def test_a_missing_or_malformed_block_is_refused(text):
    with pytest.raises(jo.BlockError):
        jo.parse_block(text)


def test_a_finding_id_depends_only_on_where_the_finding_sits():
    a = jo.finding_id("pr-review", "SA-0001", 2, 0)
    assert a == jo.finding_id("pr-review", "SA-0001", 2, 0)
    others = {
        jo.finding_id("pr-review", "SA-0001", 2, 1),
        jo.finding_id("pr-review", "SA-0001", 3, 0),
        jo.finding_id("spec-review", "SA-0001", 2, 0),
        jo.finding_id("pr-review", "SA-0002", 2, 0),
    }
    assert a not in others and len(others) == 4


def test_number_findings_pairs_each_finding_with_its_stable_id():
    findings = [
        jo.Finding("blocker", 1, "a.py", 3, "wrong"),
        jo.Finding("note", None, None, None, "fine"),
    ]
    pairs = jo.number_findings("pr-review", "SA-0001", 2, findings)
    assert pairs == [
        (jo.finding_id("pr-review", "SA-0001", 2, 0), findings[0]),
        (jo.finding_id("pr-review", "SA-0001", 2, 1), findings[1]),
    ]


def test_findings_are_saved_with_their_ids():
    pairs = [
        (
            jo.finding_id("pr-review", "SA-0001", 1, 0),
            jo.Finding("blocker", 1, "a.py", 3, "wrong"),
        ),
        (
            jo.finding_id("pr-review", "SA-0001", 1, 1),
            jo.Finding("note", None, None, None, "fine"),
        ),
    ]
    rows = json.loads(jo.dump_findings(pairs))
    assert [(r["id"], r["claim"], r["criterion"]) for r in rows] == [
        (pairs[0][0], "wrong", 1),
        (pairs[1][0], "fine", None),
    ]


def test_lens_findings_flatten_every_lens():
    lenses = [
        {"lens": "correctness", "findings": []},
        {
            "lens": "adequacy",
            "findings": [
                {
                    "lens": "adequacy",
                    "severity": "note",
                    "file": "t.py",
                    "line": 5,
                    "claim": "weak",
                }
            ],
        },
    ]
    assert jo.lens_findings(lenses) == [jo.Finding("note", None, "t.py", 5, "weak")]
