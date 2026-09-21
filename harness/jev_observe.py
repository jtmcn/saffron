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
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, int)
        ):
            raise BlockError(f"finding {n}'s {name} is not an integer or null")
    if item.get("file") is not None and not isinstance(item["file"], str):
        raise BlockError(f"finding {n}'s file is not a string or null")
    return Finding(
        item["severity"],
        item.get("criterion"),
        item.get("file"),
        item.get("line"),
        item["claim"],
    )


def lens_findings(lenses: list) -> list[Finding]:
    """Every lens finding in a cell's `findings.json`. Lenses name no criterion."""
    return [
        Finding(f["severity"], None, f.get("file"), f.get("line"), f["claim"])
        for lens in lenses
        for f in lens["findings"]
    ]


def finding_id(kind: Kind, spec_id: str, number: int, index: int) -> str:
    """Stable across re-scores, because nothing in it changes when a round is scored again."""
    return hashlib.sha256(f"{kind}|{spec_id}|{number}|{index}".encode()).hexdigest()[
        :16
    ]


def dump_findings(pairs: list[tuple[str, Finding]]) -> str:
    return json.dumps([{"id": fid, **asdict(f)} for fid, f in pairs], indent=2) + "\n"


def load_findings(text: str) -> list[tuple[str, Finding]]:
    rows = json.loads(text)
    return [(row.pop("id"), Finding(**row)) for row in rows]


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
        asks[f"Q3_{fid}"] = _noul(
            f"Would fixing finding {fid} change whether its criterion is met?"
        )
        if r.kind != "cell" and r.prior:
            asks[f"Q4_{fid}"] = _noul(
                f"Is finding {fid} materially new against every earlier finding?"
            )
    if r.kind != "cell":
        for pid, _ in r.prior:
            asks[f"Q5_{pid}"] = _noul(
                f"Does this round's diff address earlier finding {pid}?"
            )
    asks["Q6_round"] = _noul("Would another review round surface a blocking finding?")
    if r.kind == "spec-review":
        for label in labels:
            asks[f"Q7_{label}"] = _noul(f"Is criterion {label} testable as written?")
            asks[f"Q8_{label}"] = _noul(
                f"Does criterion {label} name the evidence that shows it is met?"
            )
            others = {o: text for o, text in labels.items() if o != label}
            if others:
                asks[f"Q9_{label}"] = {
                    "type": "choice",
                    "instructions": f"Does criterion {label} conflict with another criterion?",
                    "criteria": {
                        "none": "It conflicts with no other criterion.",
                        **others,
                    },
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
