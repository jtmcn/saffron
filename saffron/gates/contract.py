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


def split_lines(text: str) -> list[str]:
    """Split on `"\\n"` only — git's own separator, and the shell's.

    `str.splitlines()` also splits on `\\r`, `\\x0b`, `\\x0c`, `\\x1c`-`\\x1e`,
    `\\x85`, `U+2028` and `U+2029`, none of which git treats as a line
    terminator: it emits them raw inside a line's content. Splitting on them
    shatters one line into fragments, and a fragment starting with a space is
    then read as a context line — a byte hides a suppression from `integrity`
    that ruff still honours, and hides a credential from the push-time scan
    that the remote would still receive.

    Here rather than beside any one caller: `integrity`, `scope`, the
    credential scan and finding-anchoring all read the same git output, and a
    splitter that is right in three of four places is the defect itself.
    """
    lines = text.split("\n")
    if text.endswith("\n"):
        lines.pop()  # split("\n") artifact splitlines() never produced
    return [line[:-1] if line.endswith("\r") else line for line in lines]


class Failure(BaseModel):
    """One failure reported by one gate.

    `line` is display and anchoring only — never identity. See `identity`.
    """

    file: str
    line: int | None = None
    code: str
    """The gate's own identifier for this failure — a rule id, an exception
    type, or, for a gate that enumerates, the node id of the test that failed.
    `criteria` can read a witness's outcome only where an enumerating gate keys
    its failures that way; where it does not, `criteria` skips (§5.4)."""
    message: str = ""


class GateResult(BaseModel):
    """One execution of one gate against one tree — CONTEXT.md §4."""

    gate: str
    status: GateStatus
    tool: str | None = None
    """What the gate ran, obtained by executing it — `ruff --version`, never a
    string literal. The only thing separating a gate that ran and passed from
    one that never ran (DESIGN.md §5.4, Appendix H). Optional on the model so a
    malformed result still parses into something the runner can reject with a
    useful message; the runner is where it is required."""
    collected: list[str] | None = None
    """Identifiers this gate enumerated — for a test runner, its node ids.

    Opaque to core: never split, never parsed, never assumed to contain a
    path (§2.1). `census` and `criteria` read it. `None` means the runner
    does not enumerate, which is a `skip`; `[]` means it enumerated nothing,
    which is not the same fact (§5.4)."""
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
