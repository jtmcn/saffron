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
