# Jev review observer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Jev scores every spec review, PR review and cell REVIEW round and writes its answers as EARL Turtle that nothing reads yet.

**Architecture:** `harness/jev_observe.py` is pure: it parses a reviewer's findings block, builds the questions as plain dicts the SDK accepts, turns answers into distributions and writes Turtle. The spec loop driver gains one `jev` command that owns files, git and the live client. `saffron/` is untouched.

**Tech Stack:** Python 3.12, `typesafe-sdk==0.7.1` (`TypeSafeClient.system_one`), pyoxigraph for the Turtle tests, pytest.

**Spec:** `docs/superpowers/specs/2026-09-21-jev-review-observer-design.md`

## Global Constraints

- No file under `saffron/` changes.
- No test calls the network. Tests pass a fake client.
- Jev scores never change a gate result, a verdict, a queue order or a stop decision.
- `TYPESAFE_API_KEY` reaches only the `jev` command, never `.envrc`, `.env` or a cell.
- Exit codes: `0` scored, `1` a usage or findings-block error, `2` no key or Jev failed.
- New comments and docstrings: no em-dash, semicolon, contraction, perfect tense, hedge, or sentence over 25 words. A docstring stays within ten lines.
- Commit subjects are lowercase `type(scope): <the defect, as a sentence>`. No co-author trailer.
- Every new test runs once against a mutant it must catch before it is trusted (CLAUDE.md).
- Run `make fmt` before every commit. The code blocks here are not wrapped to ruff's width, and the `format` gate checks it.

## Deviations from the design, decided while planning

Task 5 writes these into the design doc.

1. **Jev terms use their own namespace, `urn:saffron:jev#`, not `factory:`.** `tests/ontology/test_no_dead_terms.py` requires every `factory:` term to have a query or shape that reads it. The design says nothing reads these scores yet, so a `factory:` term would fail that test. The `.ttl` files live under `~/.saffron/`, outside the `shacl` gate's tree. T6 (pyshacl) is dropped. T1's SPARQL query checks the shape instead.
2. **`typesafe-sdk` goes in the `dev` group, not a new `harness` group.** `ty` checks every file, including `.claude/`. An import from a group `make install` does not sync would fail the `types` gate. The dev group never ships in the `saffron` wheel.
3. **One Jev call per round, not one per question group.** TypeSafe's parallel-questions cookbook measured one batched call as 12.2x cheaper and 10x faster, with no change to each answer.
4. **Q4 is skipped in a round with no earlier round.** Every finding in round 1 is new by definition.
5. **Q1 is skipped when the spec has no criteria, and Q9 when it has only one.** A choice with one option carries no information.
6. **`--commit` is passed by the delegate.** It is the commit the reviewer read. For `cell` it comes from `patch.json`'s `head_sha`.

## File map

| File | Change | Responsibility |
|---|---|---|
| `harness/jev_observe.py` | create | Findings block, finding ids, questions, state, answers, Turtle |
| `tests/test_jev_observe.py` | create | T1, T2, T3 (parser) against a fake client |
| `.claude/skills/run-saffron-spec-loop/driver.py` | modify | `jev` command, round directories, git diff, live client |
| `tests/test_jev_driver.py` | create | T3 (exit 1), T4, T5, cell scoring, seats |
| `pyproject.toml`, `uv.lock` | modify | `typesafe-sdk==0.7.1` in `dev` |
| `.saffron/deadcode-allow.py` | modify | Harness names only the driver calls |
| `.claude/agents/spec-reviewer.md` | modify | Report item 4: the JSON block |
| `.claude/skills/run-saffron-spec-loop/REVIEW-PROMPT.md` | modify | Report item 5: the JSON block |
| `.claude/skills/run-saffron-spec-loop/SKILL.md` | modify | Three `jev` lines |
| `docs/superpowers/specs/2026-09-21-jev-review-observer-design.md` | modify | The six deviations |
| `docs/evidence/2026-09-21-jev-first-call.md` | create | What the first live call returned |

---

### Task 1: The findings block, finding ids and the SDK dependency

**Files:**
- Create: `harness/jev_observe.py`
- Create: `tests/test_jev_observe.py`
- Modify: `pyproject.toml` (the `dev` list), `uv.lock`

**Interfaces:**
- Produces: `Kind`, `Finding(severity, criterion, file, line, claim)`, `BlockError(ValueError)`, `parse_block(report: str) -> list[Finding]`, `lens_findings(lenses: list) -> list[Finding]`, `finding_id(kind, spec_id, number, index) -> str`, `dump_findings(pairs) -> str`, `load_findings(text) -> list[tuple[str, Finding]]`.

- [ ] **Step 1: Add the dependency**

In `pyproject.toml`, add to the end of the `dev` list, with this comment above it:

```toml
    # The spec loop's `jev` command calls it. Pinned because Jev launched 2026-09-15 and its API moves.
    "typesafe-sdk==0.7.1",
```

Run: `uv lock && uv sync`
Expected: `typesafe-sdk==0.7.1` in the resolved set. `uv run python -c "import typesafe_sdk; print(typesafe_sdk.__version__)"` prints `0.7.1`.

- [ ] **Step 2: Write the failing tests**

Create `tests/test_jev_observe.py`:

```python
"""Jev's observer: the findings block, the questions each loop asks, and the
Turtle it writes. A fake client stands in for Jev, so nothing calls the network."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pyoxigraph as ox
import pytest

from harness import jev_observe as jo

EARL = "http://www.w3.org/ns/earl#"


def _report(findings: object) -> str:
    return "## Findings\n\n- prose\n\n```json\n" + json.dumps({"findings": findings}) + "\n```\n"


def _finding(**over: object) -> dict:
    return {"severity": "blocker", "criterion": 1, "file": "a.py", "line": 3, "claim": "wrong", **over}


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
        (jo.finding_id("pr-review", "SA-0001", 1, 0), jo.Finding("blocker", 1, "a.py", 3, "wrong")),
        (jo.finding_id("pr-review", "SA-0001", 1, 1), jo.Finding("note", None, None, None, "fine")),
    ]
    assert jo.load_findings(jo.dump_findings(pairs)) == pairs


def test_lens_findings_flatten_every_lens():
    lenses = [
        {"lens": "correctness", "findings": []},
        {
            "lens": "adequacy",
            "findings": [
                {"lens": "adequacy", "severity": "note", "file": "t.py", "line": 5, "claim": "weak"}
            ],
        },
    ]
    assert jo.lens_findings(lenses) == [jo.Finding("note", None, "t.py", 5, "weak")]
```

- [ ] **Step 3: Run them to see them fail**

Run: `uv run pytest tests/test_jev_observe.py -q`
Expected: collection error, `ModuleNotFoundError: No module named 'harness.jev_observe'`.

- [ ] **Step 4: Write the module's first half**

Create `harness/jev_observe.py`:

```python
"""Jev observes one review round and writes its answers as EARL Turtle.

Nothing reads these scores yet. The design is
`docs/superpowers/specs/2026-09-21-jev-review-observer-design.md`.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Literal

Kind = Literal["spec-review", "pr-review", "cell"]
SEVERITIES = ("blocker", "concern", "note")
# The last fenced json block in a report. Reviewers write prose above it.
_BLOCK = re.compile(r"^```json[ \t]*\n(.*?)^```[ \t]*$", re.MULTILINE | re.DOTALL)


class BlockError(ValueError):
    """A report whose findings block is missing or malformed."""


@dataclass(frozen=True)
class Finding:
    severity: str
    criterion: int | None
    file: str | None
    line: int | None
    claim: str


def parse_block(report: str) -> list[Finding]:
    """The findings a reviewer's report ends with, from its last json block."""
    blocks = _BLOCK.findall(report)
    if not blocks:
        raise BlockError("the report has no fenced json block of findings")
    try:
        items = json.loads(blocks[-1])["findings"]
    except (json.JSONDecodeError, TypeError, KeyError) as exc:
        raise BlockError(f'the block is not {{"findings": [...]}}: {exc}') from exc
    if not isinstance(items, list):
        raise BlockError("`findings` is not a list")
    return [_finding(item, n) for n, item in enumerate(items, 1)]


def _finding(item: Any, n: int) -> Finding:
    if not isinstance(item, dict) or item.get("severity") not in SEVERITIES:
        raise BlockError(f"finding {n} needs a severity in {SEVERITIES}")
    if not isinstance(item.get("claim"), str):
        raise BlockError(f"finding {n} needs a claim")
    for name in ("criterion", "line"):
        value = item.get(name)
        # bool is an int subclass, and `true` is no criterion number.
        if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
            raise BlockError(f"finding {n}'s {name} is not an integer or null")
    if item.get("file") is not None and not isinstance(item["file"], str):
        raise BlockError(f"finding {n}'s file is not a string or null")
    return Finding(item["severity"], item.get("criterion"), item.get("file"), item.get("line"), item["claim"])


def lens_findings(lenses: list) -> list[Finding]:
    """Every lens finding in a cell's `findings.json`. Lenses name no criterion."""
    return [
        Finding(f["severity"], None, f.get("file"), f.get("line"), f["claim"])
        for lens in lenses
        for f in lens["findings"]
    ]


def finding_id(kind: Kind, spec_id: str, number: int, index: int) -> str:
    """Stable across re-scores, because nothing in it changes when a round is scored again."""
    return hashlib.sha256(f"{kind}|{spec_id}|{number}|{index}".encode()).hexdigest()[:16]


def dump_findings(pairs: list[tuple[str, Finding]]) -> str:
    return json.dumps([{"id": fid, **asdict(f)} for fid, f in pairs], indent=2) + "\n"


def load_findings(text: str) -> list[tuple[str, Finding]]:
    rows = json.loads(text)
    return [(row.pop("id"), Finding(**row)) for row in rows]
```

The prose rule counts the apostrophe in `finding {n}'s` inside a string, not a comment, so it is not a contraction hit. Confirm in Step 6.

- [ ] **Step 5: Run the tests to see them pass**

Run: `uv run pytest tests/test_jev_observe.py -q`
Expected: `12 passed`.

- [ ] **Step 6: Mutants, then the prose check**

Mutant A: in `parse_block`, change `blocks[-1]` to `blocks[0]`. Run the tests. `test_the_last_json_block_is_the_findings` must fail. Restore.
Mutant B: in `_finding`, delete `isinstance(value, bool) or `. `test_a_missing_or_malformed_block_is_refused[...criterion=True...]` must fail. Restore.

Run: `python3 hooks/prose_limit.py --file harness/jev_observe.py && python3 hooks/prose_limit.py --file tests/test_jev_observe.py`
Expected: no hits. Rewrite any comment it flags.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock harness/jev_observe.py tests/test_jev_observe.py
git commit -m "feat(harness): a reviewer's findings had no machine-readable form for Jev to score, so the observer parses a json block"
```

---

### Task 2: The questions each loop asks, and the state Jev reads

**Files:**
- Modify: `harness/jev_observe.py`
- Modify: `tests/test_jev_observe.py`

**Interfaces:**
- Consumes: `Kind`, `Finding`, `finding_id` from Task 1.
- Produces: `Round(kind, spec_id, number, commit, spec_text, criteria, findings, prior, diff)` where `findings` and `prior` are `list[tuple[str, Finding]]`. `build_asks(r: Round) -> dict[str, dict]` keyed `"Q<n>_<subject>"`, each value a dict the SDK accepts (`{"type": "noul"|"choice"|"score", "instructions": str, "criteria": ...}`). `state(r: Round) -> dict`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_jev_observe.py`:

```python
def _round(kind="spec-review", findings=1, prior=0, criteria=("it parses", "it saves")) -> jo.Round:
    made = [
        (jo.finding_id(kind, "SA-0001", 2, i), jo.Finding("blocker", 1, "a.py", 3, f"claim {i}"))
        for i in range(findings)
    ]
    earlier = [
        (jo.finding_id(kind, "SA-0001", 1, i), jo.Finding("note", None, None, None, f"old {i}"))
        for i in range(prior)
    ]
    return jo.Round(kind, "SA-0001", 2, "abc123", "spec text", list(criteria), made, earlier, "diff text")


def _codes(asks: dict) -> set[str]:
    return {key.split("_", 1)[0] for key in asks}


def test_a_spec_review_with_an_earlier_round_asks_every_question():
    assert _codes(jo.build_asks(_round("spec-review", prior=1))) == {f"Q{n}" for n in range(1, 10)}


def test_a_pr_review_asks_no_criterion_questions():
    assert _codes(jo.build_asks(_round("pr-review", prior=1))) == {"Q1", "Q2", "Q3", "Q4", "Q5", "Q6"}


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
    assert q2["criteria"][0].startswith("noise") and q2["criteria"][3].startswith("blocking")


def test_a_spec_with_no_criteria_asks_no_criterion_choice():
    assert "Q1" not in _codes(jo.build_asks(_round("pr-review", criteria=())))


def test_a_spec_with_one_criterion_asks_no_conflict_question():
    assert "Q9" not in _codes(jo.build_asks(_round("spec-review", criteria=("only",))))


def test_every_question_is_a_dict_the_sdk_accepts():
    for ask in jo.build_asks(_round("spec-review", prior=1)).values():
        assert ask["type"] in {"noul", "choice", "score"} and isinstance(ask["instructions"], str)


def test_the_state_carries_what_the_design_names():
    r = _round(prior=1)
    s = jo.state(r)
    assert s["spec"] == "spec text" and s["diff"] == "diff text"
    assert s["criteria"] == {"c1": "it parses", "c2": "it saves"}
    assert [f["id"] for f in s["findings"]] == [r.findings[0][0]]
    assert [f["id"] for f in s["earlier_findings"]] == [r.prior[0][0]]
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/test_jev_observe.py -q`
Expected: failures with `AttributeError: module 'harness.jev_observe' has no attribute 'Round'`.

- [ ] **Step 3: Implement**

Append to `harness/jev_observe.py`:

```python
SCORE_LEVELS = (
    "noise: not a real defect",
    "nit: true but trivial",
    "should-fix: a real defect that does not block",
    "blocking: the work is wrong until it is fixed",
)


@dataclass(frozen=True)
class Round:
    kind: Kind
    spec_id: str
    number: int
    commit: str
    spec_text: str
    criteria: list[str]
    findings: list[tuple[str, Finding]]
    prior: list[tuple[str, Finding]]
    diff: str


def _noul(instructions: str) -> dict:
    return {"type": "noul", "instructions": instructions}


def build_asks(r: Round) -> dict[str, dict]:
    """Every question this round's kind asks, keyed `Q<n>_<subject>`.

    Plain dicts, which `system_one` accepts, so this module never imports the SDK.
    """
    labels = {f"c{i}": text for i, text in enumerate(r.criteria, 1)}
    asks: dict[str, dict] = {}
    for fid, _ in r.findings:
        if labels:
            asks[f"Q1_{fid}"] = {
                "type": "choice",
                "instructions": f"Which acceptance criterion does finding {fid} affect?",
                "criteria": {**labels, "noMatch": "It affects none of the criteria."},
            }
        asks[f"Q2_{fid}"] = {
            "type": "score",
            "instructions": f"How severe is finding {fid}?",
            "criteria": list(SCORE_LEVELS),
        }
        asks[f"Q3_{fid}"] = _noul(f"Would fixing finding {fid} change whether its criterion is met?")
        if r.kind != "cell" and r.prior:
            asks[f"Q4_{fid}"] = _noul(f"Is finding {fid} materially new against every earlier finding?")
    if r.kind != "cell":
        for pid, _ in r.prior:
            asks[f"Q5_{pid}"] = _noul(f"Does this round's diff address earlier finding {pid}?")
    asks["Q6_round"] = _noul("Would another review round surface a blocking finding?")
    if r.kind == "spec-review":
        for label in labels:
            asks[f"Q7_{label}"] = _noul(f"Is criterion {label} testable as written?")
            asks[f"Q8_{label}"] = _noul(f"Does criterion {label} name the evidence that shows it is met?")
            others = {o: text for o, text in labels.items() if o != label}
            if others:
                asks[f"Q9_{label}"] = {
                    "type": "choice",
                    "instructions": f"Does criterion {label} conflict with another criterion?",
                    "criteria": {"none": "It conflicts with no other criterion.", **others},
                }
    return asks


def state(r: Round) -> dict[str, Any]:
    """What Jev reads: the spec, this round's findings, the earlier ones, and the diff."""

    def rows(pairs: list[tuple[str, Finding]]) -> list[dict]:
        return [{"id": fid, **asdict(f)} for fid, f in pairs]

    return {
        "kind": r.kind,
        "round": r.number,
        "spec": r.spec_text,
        "criteria": {f"c{i}": text for i, text in enumerate(r.criteria, 1)},
        "findings": rows(r.findings),
        "earlier_findings": rows(r.prior),
        "diff": r.diff,
    }
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `uv run pytest tests/test_jev_observe.py -q`
Expected: `22 passed`.

- [ ] **Step 5: Mutants, then the prose check**

Mutant A: delete `and r.prior` from the Q4 condition. `test_the_first_round_asks_nothing_about_newness` must fail. Restore.
Mutant B: change `if r.kind == "spec-review":` to `if r.kind != "cell":`. `test_a_pr_review_asks_no_criterion_questions` must fail. Restore.

Run: `python3 hooks/prose_limit.py --file harness/jev_observe.py && python3 hooks/prose_limit.py --file tests/test_jev_observe.py`
Expected: no hits.

- [ ] **Step 6: Commit**

```bash
git add harness/jev_observe.py tests/test_jev_observe.py
git commit -m "feat(harness): each loop asks Jev only the questions its round can answer"
```

---

### Task 3: Answers become distributions, and distributions become Turtle

**Files:**
- Modify: `harness/jev_observe.py`
- Modify: `tests/test_jev_observe.py`

**Interfaces:**
- Consumes: `Round`, `build_asks`, `state` from Task 2.
- Produces: `MODEL: str`, `Answer(question, subject, distribution)`, `distribution(answer) -> dict[str, float]`, `observe(r: Round, client, model: str = MODEL) -> tuple[str, list[Answer]]`, `to_turtle(r: Round, model: str, answers: list[Answer]) -> str`. `client` is anything with `system_one(state, questions, *, model)` returning an object with `.model: str` and `.answers: dict[str, answer]`, where an answer has `.type` and either `.noul: float` or `.probabilities: dict`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_jev_observe.py`:

```python
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
                    type="choice", probabilities={n: 0.7 if i == 0 else rest for i, n in enumerate(names)}
                )
            else:
                answers[key] = SimpleNamespace(
                    type="score", probabilities={i: 0.25 for i in range(len(q["criteria"]))}
                )
        return SimpleNamespace(model="jev-test-model", answers=answers)


def test_a_noul_answer_keeps_both_sides_of_its_probability():
    assert jo.distribution(SimpleNamespace(type="noul", noul=0.25)) == {"true": 0.25, "false": 0.75}


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
PREFIX jev: <urn:saffron:jev#>
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
    rows = list(store.query(_QUERY))
    assert len(rows) == len(answers)
    assert {row["outcome"].value for row in rows} == {EARL + "cantTell"}
    assert {row["model"].value for row in rows} == {"jev-test-model"}
    assert {row["round"].value for row in rows} == {"2"}
    assert {row["commit"].value for row in rows} == {"abc123"}
    stored = sorted(json.dumps(json.loads(row["dist"].value), sort_keys=True) for row in rows)
    expected = sorted(json.dumps(a.distribution, sort_keys=True) for a in answers)
    assert stored == expected
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/test_jev_observe.py -q`
Expected: 4 failures, `AttributeError: ... has no attribute 'distribution'` and `'observe'`.

- [ ] **Step 3: Implement**

Append to `harness/jev_observe.py`:

```python
# Task 6 replaces this with the dated name `models.list()` reports, so a record names the model that answered.
MODEL = "jev-latest"
_PREFIXES = """@prefix earl: <http://www.w3.org/ns/earl#> .
@prefix jev: <urn:saffron:jev#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
"""


@dataclass(frozen=True)
class Answer:
    question: str
    subject: str
    distribution: dict[str, float]


def distribution(answer: Any) -> dict[str, float]:
    """The whole distribution. A flat split says the question was ambiguous, which the top answer hides."""
    if answer.type == "noul":
        return {"true": answer.noul, "false": 1 - answer.noul}
    return {str(k): v for k, v in answer.probabilities.items()}


def observe(r: Round, client: Any, model: str = MODEL) -> tuple[str, list[Answer]]:
    """One call per round, which TypeSafe measured as 12x cheaper than one per question."""
    asks = build_asks(r)
    response = client.system_one(state(r), asks, model=model)
    answers = []
    for key in asks:
        question, subject = key.split("_", 1)
        answers.append(Answer(question, subject, distribution(response.answers[key])))
    return response.model, answers


def to_turtle(r: Round, model: str, answers: list[Answer]) -> str:
    """One earl:Assertion per answer. The outcome is always cantTell, because a score has no pass."""
    # json.dumps output is a valid Turtle string literal, since every escape it writes is one Turtle reads.
    lit = json.dumps
    parts = [_PREFIXES]
    for a in answers:
        subject = f"round-{r.number}" if a.subject == "round" else a.subject
        parts.append(
            "[] a earl:Assertion ;\n"
            "  earl:assertedBy jev:jev ;\n"
            f"  earl:subject <urn:saffron:jev:{r.kind}:{r.spec_id}:{subject}> ;\n"
            f"  earl:test jev:{a.question} ;\n"
            "  earl:mode earl:automatic ;\n"
            "  earl:result [ a earl:TestResult ; earl:outcome earl:cantTell ;\n"
            f"    jev:distribution {lit(json.dumps(a.distribution, sort_keys=True))}^^rdf:JSON ] ;\n"
            f"  jev:model {lit(model)} ;\n"
            f"  jev:round {r.number} ;\n"
            f"  jev:commit {lit(r.commit)} .\n"
        )
    return "\n".join(parts)
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `uv run pytest tests/test_jev_observe.py -q`
Expected: `26 passed`.

- [ ] **Step 5: Mutants, then the prose check**

Mutant A (T1's named mutant): delete the `jev:distribution ...` line from `to_turtle`, keeping `] ;` on the line above. `test_every_answer_becomes_one_assertion_carrying_its_distribution` must fail. Restore.
Mutant B: in `distribution`, return `{"true": answer.noul}` for a noul. `test_a_noul_answer_keeps_both_sides_of_its_probability` must fail. Restore.

Run: `python3 hooks/prose_limit.py --file harness/jev_observe.py && python3 hooks/prose_limit.py --file tests/test_jev_observe.py`
Expected: no hits. If the `json.dumps` comment runs over 25 words, shorten it.

- [ ] **Step 6: Commit**

```bash
git add harness/jev_observe.py tests/test_jev_observe.py
git commit -m "feat(harness): Jev's answers had nowhere to land, so each becomes an EARL assertion with its whole distribution"
```

---

### Task 4: The driver's `jev` command

**Files:**
- Modify: `.claude/skills/run-saffron-spec-loop/driver.py` (constants near line 42, `TYPE_CHECKING` block at line 33, new functions after `cmd_record` ending line 1109, parser in `main` before the `# Split by hand` comment at line 2511)
- Create: `tests/test_jev_driver.py`

**Interfaces:**
- Consumes: everything `harness.jev_observe` produces in Tasks 1 to 3.
- Produces: `driver.JEV_ROOT: Path`, `driver._jev_client() -> TypeSafeClient`, `driver.cmd_jev(args) -> int`. Round directories at `JEV_ROOT / "spec-loop" / spec_id / kind / f"round-{n}"` holding `report-<i>.md`, `round.json` (`{"commit", "since"}`), `findings.json`, `jev.ttl`. A cell writes `jev.ttl` into `JEV_ROOT / "v0" / spec_id`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_jev_driver.py`:

```python
"""The spec loop driver's `jev` command: round numbering, the diff between
rounds, re-scoring, and the exits that keep a failed call off the loop."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from typesafe_sdk import TypeSafeError

from tests.test_jev_observe import FakeClient

REPO = Path(__file__).resolve().parents[1]
DRIVER = REPO / ".claude" / "skills" / "run-saffron-spec-loop" / "driver.py"
if "spec_loop_driver" in sys.modules:
    driver = sys.modules["spec_loop_driver"]
else:
    _SPEC = importlib.util.spec_from_file_location("spec_loop_driver", DRIVER)
    assert _SPEC is not None and _SPEC.loader is not None
    driver = importlib.util.module_from_spec(_SPEC)
    sys.modules[_SPEC.name] = driver
    _SPEC.loader.exec_module(driver)

SPEC = """---
id: SA-0901
title: a spec the jev tests score
type: feature
---

## Acceptance criteria

- [ ] it parses
- [ ] it saves
"""
FINDING = {"severity": "blocker", "criterion": 1, "file": "a.py", "line": 1, "claim": "wrong"}


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def _commit(root: Path, name: str, text: str) -> str:
    (root / name).write_text(text)
    _git(root, "add", ".")
    _git(root, "commit", "-qm", name)
    return _git(root, "rev-parse", "HEAD")


@pytest.fixture
def loop(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    commits = (_commit(root, "spec.md", SPEC), _commit(root, "a.py", "x = 1\n"), _commit(root, "b.py", "y = 2\n"))
    client = FakeClient()
    monkeypatch.setattr(driver, "JEV_ROOT", tmp_path / "batches")
    monkeypatch.setattr(driver, "_jev_client", lambda: client)
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    return SimpleNamespace(root=root, commits=commits, client=client, batches=tmp_path / "batches", tmp=tmp_path)


def _report(loop, name: str, findings: list) -> str:
    path = loop.tmp / name
    path.write_text("prose\n\n```json\n" + json.dumps({"findings": findings}) + "\n```\n")
    return str(path)


def _run(monkeypatch, *argv: str) -> int:
    monkeypatch.setattr(sys, "argv", ["driver.py", *argv])
    return driver.main()


def _review(monkeypatch, loop, *extra: str) -> int:
    common = ("jev", "SA-0901", "--kind", "pr-review", "--spec", str(loop.root / "spec.md"))
    return _run(monkeypatch, *common, "--root", str(loop.root), *extra)


def _two_rounds(monkeypatch, loop) -> Path:
    first, second, third = loop.commits
    one = _report(loop, "r1.md", [FINDING])
    assert _review(monkeypatch, loop, "--report", one, "--commit", second, "--base", first) == 0
    two = _report(loop, "r2.md", [])
    assert _review(monkeypatch, loop, "--report", two, "--commit", third) == 0
    return loop.batches / "spec-loop" / "SA-0901" / "pr-review"


def test_rounds_number_themselves_and_each_diff_starts_at_the_last_round(monkeypatch, loop):
    base = _two_rounds(monkeypatch, loop)
    assert sorted(p.name for p in base.iterdir()) == ["round-1", "round-2"]
    assert "b.py" in loop.client.state["diff"] and "a.py" not in loop.client.state["diff"]
    assert [f["claim"] for f in loop.client.state["earlier_findings"]] == ["wrong"]
    assert (base / "round-2" / "jev.ttl").is_file()


def test_the_first_round_diffs_from_base(monkeypatch, loop):
    first, second, _ = loop.commits
    one = _report(loop, "r1.md", [FINDING])
    assert _review(monkeypatch, loop, "--report", one, "--commit", second, "--base", first) == 0
    assert "a.py" in loop.client.state["diff"] and "b.py" not in loop.client.state["diff"]


def test_scoring_a_round_again_keeps_its_ids_and_its_diff(monkeypatch, loop):
    base = _two_rounds(monkeypatch, loop)
    ids = [row["id"] for row in json.loads((base / "round-1" / "findings.json").read_text())]
    before = (base / "round-1" / "jev.ttl").read_text()
    assert _review(monkeypatch, loop, "--round", "1") == 0
    assert [row["id"] for row in json.loads((base / "round-1" / "findings.json").read_text())] == ids
    assert "a.py" in loop.client.state["diff"]
    assert (base / "round-1" / "jev.ttl").read_text() == before
    assert sorted(p.name for p in base.iterdir()) == ["round-1", "round-2"]


def test_both_seats_share_one_round(monkeypatch, loop):
    first, second, _ = loop.commits
    spec_seat = _report(loop, "spec-seat.md", [FINDING])
    standards = _report(loop, "standards.md", [{**FINDING, "claim": "other"}])
    assert _review(
        monkeypatch, loop, "--report", spec_seat, "--report", standards, "--commit", second, "--base", first
    ) == 0
    d = loop.batches / "spec-loop" / "SA-0901" / "pr-review" / "round-1"
    assert sorted(p.name for p in d.glob("report-*.md")) == ["report-1.md", "report-2.md"]
    assert [r["claim"] for r in json.loads((d / "findings.json").read_text())] == ["wrong", "other"]


def test_a_malformed_block_exits_1_and_writes_no_round(monkeypatch, loop):
    bad = loop.tmp / "bad.md"
    bad.write_text("no block here\n")
    assert _review(monkeypatch, loop, "--report", str(bad), "--commit", loop.commits[1]) == 1
    assert not loop.batches.exists() and loop.client.questions == {}


def test_no_key_exits_2_before_any_call(monkeypatch, loop):
    monkeypatch.delenv("TYPESAFE_API_KEY")
    one = _report(loop, "r1.md", [FINDING])
    assert _review(monkeypatch, loop, "--report", one, "--commit", loop.commits[1]) == 2
    assert not loop.batches.exists() and loop.client.questions == {}


def test_a_failed_call_exits_2_and_leaves_the_round_to_score_again(monkeypatch, loop):
    class Down:
        def system_one(self, *args, **kwargs):
            raise TypeSafeError("down")

    monkeypatch.setattr(driver, "_jev_client", Down)
    first, second, _ = loop.commits
    one = _report(loop, "r1.md", [FINDING])
    assert _review(monkeypatch, loop, "--report", one, "--commit", second, "--base", first) == 2
    d = loop.batches / "spec-loop" / "SA-0901" / "pr-review" / "round-1"
    assert (d / "findings.json").is_file() and not (d / "jev.ttl").exists()


def test_a_cell_is_scored_from_its_batch_directory(monkeypatch, loop):
    cell = loop.batches / "v0" / "SA-0901"
    cell.mkdir(parents=True)
    lens = {"lens": "adequacy", "severity": "note", "file": "t.py", "line": 5, "claim": "weak"}
    (cell / "findings.json").write_text(json.dumps([{"lens": "adequacy", "findings": [lens]}]))
    (cell / "patch.json").write_text(json.dumps({"head_sha": "feedbeef"}))
    (cell / "patch.diff").write_text("diff --git a/t.py b/t.py\n")
    assert _run(monkeypatch, "jev", "SA-0901", "--kind", "cell", "--spec", str(loop.root / "spec.md")) == 0
    assert '"feedbeef"' in (cell / "jev.ttl").read_text()
    assert {k.split("_", 1)[0] for k in loop.client.questions} == {"Q1", "Q2", "Q3", "Q6"}


def test_the_spec_is_found_by_its_id(monkeypatch, loop, tmp_path):
    specs = tmp_path / "specs" / "done"
    specs.mkdir(parents=True)
    (specs / "SA-0901-a-spec.md").write_text(SPEC)
    monkeypatch.setattr(driver, "SPECS_DIR", tmp_path / "specs")
    first, second, _ = loop.commits
    one = _report(loop, "r1.md", [FINDING])
    argv = ("jev", "SA-0901", "--kind", "pr-review", "--root", str(loop.root))
    assert _run(monkeypatch, *argv, "--report", one, "--commit", second, "--base", first) == 0


def test_other_commands_run_without_the_sdk():
    code = (
        "import runpy, sys; sys.modules['typesafe_sdk'] = None; "
        f"sys.argv = ['driver.py', 'pattern']; runpy.run_path({str(DRIVER)!r}, run_name='__main__')"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/test_jev_driver.py -q`
Expected: every test except `test_other_commands_run_without_the_sdk` fails, with `AttributeError: ... has no attribute 'JEV_ROOT'` from the fixture or `invalid choice: 'jev'` from argparse.

- [ ] **Step 3: Implement the constants and the type import**

In `driver.py`, extend the `TYPE_CHECKING` block at line 33:

```python
if TYPE_CHECKING:
    from harness.jev_observe import Round
    from saffron.gates.contract import GateResult
    from saffron.intake import Spec
```

After `ONTOLOGY_NS` (line 43), add:

```python
# Where `jev` writes. A cell's own batch directory sits under `v0/`, as `saffron/cli.py` puts it.
JEV_ROOT = Path.home() / ".saffron" / "batches"
```

- [ ] **Step 4: Implement the command**

Insert after `cmd_record` (after line 1109):

```python
def _jev_client():
    """The live client. Built only here, so no other command needs the SDK."""
    from typesafe_sdk import TypeSafeClient

    return TypeSafeClient(timeout=120.0)


def _spec_path(spec_id: str, given: str | None) -> Path | None:
    if given:
        return Path(given)
    found = sorted(SPECS_DIR.rglob(f"{spec_id}-*.md"))
    return found[0] if len(found) == 1 else None


def cmd_jev(args) -> int:
    """Score one review round with Jev and write `jev.ttl`. Nothing reads it yet."""
    if not os.environ.get("TYPESAFE_API_KEY"):
        print("error: TYPESAFE_API_KEY is not set for this command", file=sys.stderr)
        return 2
    # `harness` is not in the saffron wheel, so it is imported from the checkout.
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from typesafe_sdk import TypeSafeError

    from harness import jev_observe
    from saffron.intake import SpecError, load_spec

    path = _spec_path(args.spec_id, args.spec)
    if path is None:
        return _fail(f"no single spec file for {args.spec_id}, so pass --spec")
    try:
        spec, _sha = load_spec(path)
    except SpecError as exc:
        return _fail(str(exc))
    criteria = [c.claim for c in spec.acceptance] or spec.acceptance_criteria
    prepared = (
        _jev_cell(spec.id, path.read_text(), criteria)
        if args.kind == "cell"
        else _jev_review(args, spec.id, path.read_text(), criteria)
    )
    if isinstance(prepared, int):
        return prepared
    directory, round_ = prepared
    try:
        model, answers = jev_observe.observe(round_, _jev_client())
    # KeyError is an answer missing from the response, which is Jev failing too.
    except (TypeSafeError, KeyError) as exc:
        print(f"error: Jev did not answer round {round_.number}: {exc}", file=sys.stderr)
        return 2
    (directory / "jev.ttl").write_text(jev_observe.to_turtle(round_, model, answers))
    print(f"{spec.id}  {args.kind} round {round_.number}  {len(answers)} answers  {directory}")
    return 0


def _jev_review(args, spec_id: str, spec_text: str, criteria: list[str]) -> tuple[Path, Round] | int:
    """A spec or PR review round: numbered, diffed from the last round, saved before the call."""
    from harness import jev_observe

    base = JEV_ROOT / "spec-loop" / spec_id / args.kind
    done = sorted(int(p.name.removeprefix("round-")) for p in base.glob("round-*"))
    if args.round is not None:
        number = args.round
        directory = base / f"round-{number}"
        if not (directory / "round.json").is_file():
            return _fail(f"no saved round {number} at {base}")
        saved = json.loads((directory / "round.json").read_text())
        commit, since = saved["commit"], saved["since"]
        reports = [p.read_text() for p in sorted(directory.glob("report-*.md"))]
    else:
        if not args.report or not args.commit:
            return _fail("a new round needs --report and --commit")
        number = (done[-1] if done else 0) + 1
        directory = base / f"round-{number}"
        commit = args.commit
        previous = base / f"round-{number - 1}" / "round.json"
        since = json.loads(previous.read_text())["commit"] if number > 1 else args.base
        reports = [Path(p).read_text() for p in args.report]
    try:
        findings = [f for text in reports for f in jev_observe.parse_block(text)]
    except jev_observe.BlockError as exc:
        return _fail(str(exc))
    prior: list = []
    for n in (n for n in done if n < number):
        prior += jev_observe.load_findings((base / f"round-{n}" / "findings.json").read_text())
    # Round 1 reads the whole PR from its merge base. Later rounds read only what changed.
    span = f"{since}...{commit}" if number == 1 else f"{since}..{commit}"
    try:
        diff = _git("diff", span, cwd=args.root)
    except GitError as exc:
        return _fail(str(exc))
    pairs = [(jev_observe.finding_id(args.kind, spec_id, number, i), f) for i, f in enumerate(findings)]
    directory.mkdir(parents=True, exist_ok=True)
    for i, text in enumerate(reports, 1):
        (directory / f"report-{i}.md").write_text(text)
    (directory / "round.json").write_text(json.dumps({"commit": commit, "since": since}) + "\n")
    (directory / "findings.json").write_text(jev_observe.dump_findings(pairs))
    return directory, jev_observe.Round(
        args.kind, spec_id, number, commit, spec_text, criteria, pairs, prior, diff
    )


def _jev_cell(spec_id: str, spec_text: str, criteria: list[str]) -> tuple[Path, Round] | int:
    """The cell's REVIEW, read from its batch directory after the task ends."""
    from harness import jev_observe

    directory = JEV_ROOT / "v0" / spec_id
    try:
        lenses = json.loads((directory / "findings.json").read_text())
        commit = json.loads((directory / "patch.json").read_text())["head_sha"]
        diff = (directory / "patch.diff").read_text()
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        return _fail(f"no finished cell to score at {directory}: {exc}")
    findings = jev_observe.lens_findings(lenses)
    pairs = [(jev_observe.finding_id("cell", spec_id, 1, i), f) for i, f in enumerate(findings)]
    return directory, jev_observe.Round("cell", spec_id, 1, commit, spec_text, criteria, pairs, [], diff)
```

- [ ] **Step 5: Register the parser**

In `main`, before the `# Split by hand` comment at line 2511:

```python
    p = sub.add_parser("jev", help="score one review round with Jev, informational only")
    p.add_argument("spec_id")
    p.add_argument("--kind", required=True, choices=("spec-review", "pr-review", "cell"))
    p.add_argument("--spec", help="the spec file. Default: the one under .saffron/specs")
    p.add_argument(
        "--report", action="append", default=[], help="a saved reviewer report, once per seat"
    )
    p.add_argument("--commit", help="the commit the reviewer read")
    p.add_argument("--base", default="origin/main", help="where round 1's diff starts")
    p.add_argument("--round", type=int, help="score a saved round again")
    p.add_argument("--root", type=Path, default=REPO, help="the checkout git reads")
    p.set_defaults(func=cmd_jev)
```

- [ ] **Step 6: Run the tests to see them pass**

Run: `uv run pytest tests/test_jev_driver.py tests/test_jev_observe.py tests/test_spec_loop_driver.py -q`
Expected: all pass, with the existing driver tests unchanged.

- [ ] **Step 7: Mutants**

Mutant A (T4's named mutant): in `harness/jev_observe.py`, make `finding_id` hash `f"{kind}|{spec_id}|{number}|{index}|{time.time()}"` (add `import time`). `test_scoring_a_round_again_keeps_its_ids_and_its_diff` must fail. Restore.
Mutant B: in `_jev_review`, replace the `since = ... if number > 1 else args.base` line with `since = args.base`. `test_rounds_number_themselves_and_each_diff_starts_at_the_last_round` must fail. Round 2 then diffs from `origin/main`, which the temp repo lacks. Restore.
Mutant C: move `directory.mkdir(...)` above the `parse_block` call. `test_a_malformed_block_exits_1_and_writes_no_round` must fail. Restore.
Mutant D: add `import typesafe_sdk` at the top of `driver.py`. `test_other_commands_run_without_the_sdk` must fail. Restore.

- [ ] **Step 8: Gates**

Run: `make check > /tmp/check.log 2>&1; echo "make exit: $?"; tail -5 /tmp/check.log`
Expected: `make exit: 0`, except the `dead` gate, which reports the harness names only the driver calls. Task 5 whitelists them. If `ty` flags `Round` in the `TYPE_CHECKING` import, confirm `harness` resolves from the repo root the same way `tests/test_lens_scoring.py`'s `from harness import lens_scoring` does.

- [ ] **Step 9: Commit**

```bash
git add .claude/skills/run-saffron-spec-loop/driver.py tests/test_jev_driver.py
git commit -m "feat(spec-loop): review rounds left no record Jev could score, so the driver keeps each round and scores it"
```

---

### Task 5: Reviewers write the block, the skill runs the command, the gates pass

**Files:**
- Modify: `.saffron/deadcode-allow.py`
- Modify: `.claude/agents/spec-reviewer.md` (the `## Report` list, line 134)
- Modify: `.claude/skills/run-saffron-spec-loop/REVIEW-PROMPT.md` (the `Report, in this order:` list, line 105)
- Modify: `.claude/skills/run-saffron-spec-loop/SKILL.md` (after line 99, after line 241, and after the seats in step 2c at line 254)
- Modify: `docs/superpowers/specs/2026-09-21-jev-review-observer-design.md`

**Interfaces:**
- Consumes: the `jev` command from Task 4.

- [ ] **Step 1: Whitelist what the dead gate reports**

Run: `.saffron/gates/dead | python3 -m json.tool | grep -A2 jev_observe`
Add one line per reported name to `.saffron/deadcode-allow.py` under `# Called from outside the scanned roots.`, in this form:

```python
_.parse_block  # .claude/skills/run-saffron-spec-loop/driver.py: `jev`, outside the scanned roots
```

Expected names: `parse_block`, `lens_findings`, `finding_id`, `dump_findings`, `load_findings`, `observe`, `to_turtle`. Add only the names the gate actually reports. Re-run the gate and expect `pass`.

- [ ] **Step 2: The JSON block in both report formats**

In `.claude/agents/spec-reviewer.md`, append item 4 to the `## Report` list:

```markdown
4. **Findings block**, last: a fenced `json` block restating the findings for
   Jev (`driver.py jev`). Write `{"findings": [...]}`, one object per finding,
   with `severity` (`blocker`, `concern` or `note`), `criterion` (its number,
   or `null`), `file`, `line` and `claim`. A review with no findings writes an
   empty list.
```

In `.claude/skills/run-saffron-spec-loop/REVIEW-PROMPT.md`, append item 5 to `Report, in this order:` with the same text, numbered 5.

- [ ] **Step 3: The three SKILL.md lines**

After line 99 of `SKILL.md` (the end of the paragraph that ends `run \`snapshot --force\` after the edit merges.`), add:

````markdown
Save each review's final message to a file and score it with Jev. The scores
are informational and nothing reads them yet. A non-zero exit is noted and the
loop carries on.

```bash
env TYPESAFE_API_KEY="$(bash -c 'source ~/.secrets; printf %s "$TYPESAFE_API_KEY"')" \
  uv run .claude/skills/run-saffron-spec-loop/driver.py jev SA-NNNN --kind spec-review \
  --report <saved review> --commit <the base the reviewer read>
```
````

After line 241 (`to the operator (GOTCHAS, Recording).`), add:

```markdown
Then score the cell's own REVIEW the same way, with `--kind cell` and no
`--report` or `--commit`.
```

After step 2c item 2 (the seats, ending `after three clean lenses.`), add:

```markdown
   Save both seats' reports and score them as one round with `--kind
   pr-review --report <spec seat> --report <standards seat> --commit <PR
   head>`, the same command as step 1b.
```

From a worktree-isolated session, the guard refuses `source ~/.secrets`. The env-file route in GOTCHAS applies, using `TYPESAFE_API_KEY` in place of the OAuth token.

- [ ] **Step 4: Write the deviations into the design doc**

In `docs/superpowers/specs/2026-09-21-jev-review-observer-design.md`, add a `## Changed while planning` section before `## Out of scope`, listing the six deviations from this plan's header, one numbered item each. Also edit the three sentences they contradict: the `factory.ttl` paragraph under "The record", the `harness` group sentence under "The key and the dependency", and T6 in the Testing table.

- [ ] **Step 5: The whole check**

Run: `make check > /tmp/check.log 2>&1; echo "make exit: $?"; tail -5 /tmp/check.log`
Expected: `make exit: 0`.

- [ ] **Step 6: Commit**

```bash
git add .saffron/deadcode-allow.py .claude/agents/spec-reviewer.md .claude/skills/run-saffron-spec-loop/REVIEW-PROMPT.md .claude/skills/run-saffron-spec-loop/SKILL.md docs/superpowers/specs/2026-09-21-jev-review-observer-design.md
git commit -m "docs(spec-loop): no loop step ran Jev, so reviewers write a findings block and the skill scores every round"
```

---

### Task 6: The first live call, and the pinned model

**Files:**
- Modify: `harness/jev_observe.py` (`MODEL`)
- Create: `docs/evidence/2026-09-21-jev-first-call.md`

- [ ] **Step 1: A key-only env file**

The worktree guard refuses `source ~/.secrets`, so write only the Jev key to the scratchpad:

```bash
umask 077
sed -n 's/^export \(TYPESAFE_API_KEY=\)/\1/p' ~/.secrets > "$SCRATCH/jev.env"
```

`$SCRATCH` is the session scratchpad directory. Never pass `~/.secrets` itself to `--env-file`, because it holds other keys.

- [ ] **Step 2: List the models and pin one**

```bash
uv run --env-file "$SCRATCH/jev.env" python -c "from typesafe_sdk import TypeSafeClient; [print(m.name, m.release_date) for m in TypeSafeClient().models.list().models]"
```

Set `MODEL` in `harness/jev_observe.py` to the dated Jev name the list prints, not `jev-latest`. Replace its comment with one line naming the date it was listed.

- [ ] **Step 3: Score SA-0117's cell**

```bash
uv run --env-file "$SCRATCH/jev.env" .claude/skills/run-saffron-spec-loop/driver.py jev SA-0117 --kind cell
```

Expected: `SA-0117  cell round 1  <n> answers  ~/.saffron/batches/v0/SA-0117`, and exit 0. SA-0117 has one lens finding and nine criteria, so `<n>` is 4: Q1, Q2 and Q3 for the finding, and Q6.

- [ ] **Step 4: Record what came back**

Write `docs/evidence/2026-09-21-jev-first-call.md` with: the command, the model name `models.list()` printed, the SDK version, the `jev.ttl` it wrote (copy it in full), each distribution, the input token count if `response.usage.input_tokens` reports one, and any place the response differed from the shape the design assumed. State measured facts only.

Run: `python3 hooks/prose_limit.py --file docs/evidence/2026-09-21-jev-first-call.md`
Expected: no hits.

- [ ] **Step 5: Delete the env file, run the check, commit**

```bash
rm "$SCRATCH/jev.env"
make check > /tmp/check.log 2>&1; echo "make exit: $?"; tail -3 /tmp/check.log
git add harness/jev_observe.py docs/evidence/2026-09-21-jev-first-call.md
git commit -m "docs(evidence): the Jev response shape was read from docs, not measured, so SA-0117's cell is scored live"
```
