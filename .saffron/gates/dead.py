#!/usr/bin/env python3
"""vulture -> the gate contract: code that no production caller reaches.

Design: `docs/superpowers/specs/2026-09-18-dead-code-gate-design.md`. `tests/`
is not scanned, so a symbol only a test calls is dead. An open spec defers a
symbol it will bring into use by listing it under `pending_symbols`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

GATE = "dead"
ROOTS = ("saffron", "harness", "images", ".saffron/gates")
MIN_CONFIDENCE = "60"
# Anchored on this file, as `structure.py` anchors its config: a cell runs the base's copy.
SAFFRON_DIR = Path(__file__).resolve().parent.parent
WHITELIST = SAFFRON_DIR / "deadcode-allow.py"
SPECS = SAFFRON_DIR / "specs"
# Measured on vulture 2.16: 3 means it reported dead code, 1 a syntax error or a missing path.
OK_EXITS = (0, 3)

_LINE = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+): (?P<message>.+ \(\d+% confidence\))$"
)
_UNUSED = re.compile(r"^unused (?P<kind>\w+) '(?P<name>[^']+)'")
_FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", re.DOTALL)
# The same pattern as `saffron.intake.PENDING_SYMBOL`; a test holds the two readers together.
_ENTRY = re.compile(r"^[^\s:]+::[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class Unused:
    file: str
    line: int
    code: str
    message: str
    name: str | None

    # ponytail: vulture names no class, so an entry for a method defers every
    # method of that name in the file.
    @property
    def symbol(self) -> str | None:
        return None if self.name is None else f"{self.file}::{self.name}"


def parse(stdout: str) -> list[Unused]:
    """One `Unused` per vulture line. A line it cannot read raises `ValueError`."""
    found = []
    for raw in stdout.splitlines():
        if not raw.strip():
            continue
        line = _LINE.match(raw)
        if line is None:
            raise ValueError(f"cannot read vulture line: {raw[:200]}")
        message = line["message"]
        unused = _UNUSED.match(message)
        if unused:
            code, name = f"unused-{unused['kind']}", unused["name"]
        elif message.startswith("unreachable code"):
            code, name = "unreachable-code", None
        else:
            raise ValueError(f"cannot read vulture line: {raw[:200]}")
        found.append(Unused(line["file"], int(line["line"]), code, message, name))
    return found


def entries(text: str) -> list[str]:
    """One spec's `pending_symbols`, validated as `saffron.intake` validates it."""
    import yaml  # here, so a cell without pyyaml reports `error` after the version probe

    match = _FRONTMATTER.match(text)
    if match is None:
        raise ValueError("no YAML frontmatter block")
    try:
        fields = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"frontmatter is not valid YAML: {exc}") from exc
    if not isinstance(fields, dict):
        raise ValueError("frontmatter is not a mapping")
    listed = fields.get("pending_symbols") or []
    if not isinstance(listed, list) or not all(
        isinstance(e, str) and _ENTRY.match(e) for e in listed
    ):
        raise ValueError(f"pending_symbols is not a list of <path>::<name>: {listed!r}")
    return listed


def pending(specs_dir: Path) -> dict[str, str]:
    """Each open spec's entries, mapped to the spec file that names it."""
    found: dict[str, str] = {}
    for path in sorted(specs_dir.glob("*.md")):
        try:
            listed = entries(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise ValueError(f"{path.name}: {exc}") from exc
        found.update(dict.fromkeys(listed, path.name))
    return found
