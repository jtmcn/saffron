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
