"""Jev's observer: the findings block, the questions each loop asks, and the
Turtle it writes. A fake client stands in for Jev, so nothing calls the network."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import cast

import pyoxigraph as ox
import pytest

from harness import jev_observe as jo

EARL = "http://www.w3.org/ns/earl#"


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


def test_findings_round_trip_through_their_file():
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
    assert jo.load_findings(jo.dump_findings(pairs)) == pairs


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


def _round(
    kind="spec-review", findings=1, prior=0, criteria=("it parses", "it saves")
) -> jo.Round:
    made = [
        (
            jo.finding_id(kind, "SA-0001", 2, i),
            jo.Finding("blocker", 1, "a.py", 3, f"claim {i}"),
        )
        for i in range(findings)
    ]
    earlier = [
        (
            jo.finding_id(kind, "SA-0001", 1, i),
            jo.Finding("note", None, None, None, f"old {i}"),
        )
        for i in range(prior)
    ]
    return jo.Round(
        kind,
        "SA-0001",
        2,
        "abc123",
        "spec text",
        list(criteria),
        made,
        earlier,
        "diff text",
    )


def _codes(asks: dict) -> set[str]:
    return {key.split("_", 1)[0] for key in asks}


def test_a_spec_review_with_an_earlier_round_asks_every_question():
    assert _codes(jo.build_asks(_round("spec-review", prior=1))) == {
        f"Q{n}" for n in range(1, 10)
    }


def test_a_pr_review_asks_no_criterion_questions():
    assert _codes(jo.build_asks(_round("pr-review", prior=1))) == {
        "Q1",
        "Q2",
        "Q3",
        "Q4",
        "Q5",
        "Q6",
    }


def test_a_cell_asks_nothing_about_earlier_rounds():
    assert _codes(jo.build_asks(_round("cell"))) == {"Q1", "Q2", "Q3", "Q6"}


def test_the_first_round_asks_nothing_about_newness():
    assert "Q4" not in _codes(jo.build_asks(_round("pr-review", prior=0)))


def test_q1_chooses_among_the_criteria_and_nomatch():
    r = _round()
    q1 = jo.build_asks(r)[f"Q1_{r.findings[0][0]}"]
    assert q1["type"] == "choice"
    assert list(q1["criteria"]) == ["c1", "c2", "noMatch"]


def test_q2_is_a_four_level_score_from_noise_to_blocking():
    r = _round()
    q2 = jo.build_asks(r)[f"Q2_{r.findings[0][0]}"]
    assert q2["type"] == "score" and len(q2["criteria"]) == 4
    assert q2["criteria"][0].startswith("noise") and q2["criteria"][3].startswith(
        "blocking"
    )


def test_a_spec_with_no_criteria_asks_no_criterion_choice():
    assert "Q1" not in _codes(jo.build_asks(_round("pr-review", criteria=())))


def test_a_spec_with_one_criterion_asks_no_conflict_question():
    assert "Q9" not in _codes(jo.build_asks(_round("spec-review", criteria=("only",))))


def test_every_question_is_a_dict_the_sdk_accepts():
    for ask in jo.build_asks(_round("spec-review", prior=1)).values():
        assert ask["type"] in {"noul", "choice", "score"} and isinstance(
            ask["instructions"], str
        )


def test_the_state_carries_what_the_design_names():
    r = _round(prior=1)
    s = jo.state(r)
    assert s["spec"] == "spec text" and s["diff"] == "diff text"
    assert s["criteria"] == {"c1": "it parses", "c2": "it saves"}
    assert [f["id"] for f in s["findings"]] == [r.findings[0][0]]
    assert [f["id"] for f in s["earlier_findings"]] == [r.prior[0][0]]


class FakeClient:
    """Answers every question with a fixed, uneven distribution."""

    def __init__(self) -> None:
        self.questions: dict = {}
        self.state: dict = {}
        self.model: str | None = None

    def system_one(self, state, questions, *, model=None):
        self.questions, self.state, self.model = dict(questions), state, model
        answers = {}
        for key, q in questions.items():
            if q["type"] == "noul":
                answers[key] = SimpleNamespace(type="noul", noul=0.25)
            elif q["type"] == "choice":
                names = list(q["criteria"])
                rest = 0.3 / max(len(names) - 1, 1)
                answers[key] = SimpleNamespace(
                    type="choice",
                    probabilities={
                        n: 0.7 if i == 0 else rest for i, n in enumerate(names)
                    },
                )
            else:
                answers[key] = SimpleNamespace(
                    type="score",
                    probabilities={i: 0.25 for i in range(len(q["criteria"]))},
                )
        return SimpleNamespace(model="jev-test-model", answers=answers)


def test_a_noul_answer_keeps_both_sides_of_its_probability():
    assert jo.distribution(SimpleNamespace(type="noul", noul=0.25)) == {
        "true": 0.25,
        "false": 0.75,
    }


def test_a_score_answer_keys_its_levels_as_strings():
    answer = SimpleNamespace(type="score", probabilities={0: 0.1, 3: 0.9})
    assert jo.distribution(answer) == {"0": 0.1, "3": 0.9}


def test_observe_asks_once_with_the_pinned_model():
    client = FakeClient()
    model, answers = jo.observe(_round(prior=1), client, model="jev-pinned")
    assert client.model == "jev-pinned" and model == "jev-test-model"
    assert len(answers) == len(client.questions)


_QUERY = """
PREFIX earl: <http://www.w3.org/ns/earl#>
PREFIX jev: <urn:software-factory:jev#>
SELECT ?outcome ?dist ?model ?round ?commit WHERE {
  ?a a earl:Assertion ; earl:assertedBy jev:jev ; earl:test ?test ;
     earl:subject ?subject ; earl:mode earl:automatic ; earl:result ?r ;
     jev:model ?model ; jev:round ?round ; jev:commit ?commit .
  ?r earl:outcome ?outcome ; jev:distribution ?dist .
}
"""


def test_every_answer_becomes_one_assertion_carrying_its_distribution():
    r = _round("spec-review", findings=2, prior=1)
    model, answers = jo.observe(r, FakeClient())
    store = ox.Store()
    store.load(jo.to_turtle(r, model, answers).encode(), ox.RdfFormat.TURTLE)
    result = store.query(_QUERY)
    rows = list(cast(ox.QuerySolutions, result))
    assert len(rows) == len(answers)
    assert {row["outcome"].value for row in rows} == {EARL + "cantTell"}
    assert {row["model"].value for row in rows} == {"jev-test-model"}
    assert {row["round"].value for row in rows} == {"2"}
    assert {row["commit"].value for row in rows} == {"abc123"}
    stored = sorted(
        json.dumps(json.loads(row["dist"].value), sort_keys=True) for row in rows
    )
    expected = sorted(json.dumps(a.distribution, sort_keys=True) for a in answers)
    assert stored == expected
