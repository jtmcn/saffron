"""The gate contract — the whole repo-agnostic surface (DESIGN.md §5.4).

A gate is an executable that emits one JSON object on stdout. Saffron does not
know or care what it ran.
"""

from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, Field

GateStatus = Literal["pass", "fail", "skip", "error"]

_DIGITS = re.compile(r"\d+")
_WHITESPACE = re.compile(r"\s+")


class Failure(BaseModel):
    """One failure reported by one gate.

    `line` is display and anchoring only — never identity. See `identity`.
    """

    file: str
    line: int | None = None
    code: str
    message: str = ""


class GateResult(BaseModel):
    """One execution of one gate. Never called a "gate run" — CONTEXT.md §4."""

    gate: str
    status: GateStatus
    tool: str | None = None
    """What the gate ran, obtained by executing it — `ruff --version`, never a
    string literal. The only thing separating a gate that ran and passed from
    one that never ran (DESIGN.md §5.4, Appendix H). Optional on the model so a
    malformed result still parses into something the runner can reject with a
    useful message; the runner is where it is required."""
    failures: list[Failure] = Field(default_factory=list)
    summary: str = ""
    duration_ms: int | None = Field(default=None, ge=0)


def normalize_message(message: str) -> str:
    """Collapse whitespace and the numbers a diff shifts.

    Messages routinely embed the line and column they were reported at, so a
    raw message carries the coordinate that `identity` exists to exclude.
    """
    return _WHITESPACE.sub(" ", _DIGITS.sub("N", message)).strip()


def identity(gate: str, failure: Failure) -> tuple[str, str, str, str]:
    """The comparable identity of a failure: (gate, file, code, message).

    Deliberately not `line`. A change that inserts thirty lines at the top of a
    file moves every failure below it, so a line-keyed identity stops matching
    and untouched failures read as new — the countermeasure defeating itself on
    nearly every diff that is not append-only (DESIGN.md §5.4).

    The normalized message is the tie-break for one file holding two failures
    with the same code.
    """
    return (gate, failure.file, failure.code, normalize_message(failure.message))


def parse_gate_json(raw: str, expected_gate: str) -> GateResult:
    """Parse one gate's stdout. Raises on anything that is not the contract."""
    result = GateResult.model_validate(json.loads(raw))
    if result.gate != expected_gate:
        raise ValueError(
            f"gate emitted {result.gate!r} but is declared as {expected_gate!r}"
        )
    return result
