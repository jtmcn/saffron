#!/usr/bin/env python3
"""vulture -> the gate contract: code that no production caller reaches.

Design: `docs/superpowers/specs/2026-09-18-dead-code-gate-design.md`. `tests/`
is not scanned, so a symbol only a test calls is dead. An open spec defers a
symbol it will bring into use by listing it under `pending_symbols`.
"""

from __future__ import annotations

import importlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

GATE = "dead"
ROOTS = (
    "saffron",
    "harness",
    "images",
    "records",
    "ontology",
    "hooks",
    ".saffron/gates",
)
# ponytail: vulture matches names globally, so a new function named like any
# attribute used anywhere, or listed in `__all__`, is not reported.
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
# Every message in vulture 2.16's `reachability.py`.
_UNREACHABLE = re.compile(
    r"^(unreachable code after|unreachable 'else' (block|expression)"
    r"|unsatisfiable '\w+' condition|redundant if-condition) "
)
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
        elif _UNREACHABLE.match(message):
            code, name = "unreachable-code", None
        else:
            raise ValueError(f"cannot read vulture line: {raw[:200]}")
        found.append(Unused(line["file"], int(line["line"]), code, message, name))
    return found


def entries(text: str) -> list[str]:
    """One spec's `pending_symbols`, validated as `saffron.intake` validates it."""
    import yaml  # `main` probes it after the version probe

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
        isinstance(e, str) and _ENTRY.fullmatch(e) for e in listed
    ):
        raise ValueError(f"pending_symbols is not a list of <path>::<name>: {listed!r}")
    return listed


def pending(specs_dir: Path) -> tuple[dict[str, str], list[str]]:
    """Each open spec's entries mapped to the spec naming it, and the specs skipped.

    A spec that does not parse defers nothing: intake refuses it, so no task runs it.
    """
    found: dict[str, str] = {}
    skipped: list[str] = []
    for path in sorted(specs_dir.glob("*.md")):
        try:
            listed = entries(path.read_text(encoding="utf-8"))
        except ValueError:
            skipped.append(path.name)
            continue
        found.update(dict.fromkeys(listed, path.name))
    return found, skipped


def _emit(payload: dict[str, object]) -> int:
    print(json.dumps(payload))
    return 0


def _error(summary: str, tool: str | None = None) -> int:
    return _emit({"gate": GATE, "status": "error", "tool": tool, "summary": summary})


def main(argv: list[str]) -> int:
    report = argv == ["--report"]
    if argv and not report:
        print("usage: dead.py [--report]", file=sys.stderr)
        return 2
    try:
        version = subprocess.run(
            ["vulture", "--version"], capture_output=True, text=True
        )
    # Not just FileNotFoundError: a present-but-unrunnable binary raises PermissionError.
    except OSError as exc:
        return _error(f"vulture could not be run: {exc}")
    tool = version.stdout.strip()
    if version.returncode != 0 or not tool:
        return _error("vulture reported no version")
    # Probed here, not only where a spec is read, so no open spec still reports `error`.
    try:
        importlib.import_module("yaml")
    except ImportError as exc:
        return _error(f"{type(exc).__name__}: {exc}", tool)
    if not WHITELIST.is_file():
        return _error(f"no whitelist at {WHITELIST}", tool)
    roots = [r for r in ROOTS if Path(r).is_dir()]
    if not roots:
        return _error(
            f"none of {', '.join(ROOTS)} is here, so nothing was scanned", tool
        )
    # `--config` names an empty file so the scanned tree's `pyproject.toml` cannot hide a name.
    argv = ["vulture", *roots, str(WHITELIST), "--min-confidence", MIN_CONFIDENCE]
    try:
        scan = subprocess.run(
            [*argv, "--config", os.devnull], capture_output=True, text=True
        )
    except OSError as exc:
        return _error(f"vulture could not be run: {exc}", tool)
    if scan.returncode not in OK_EXITS:
        detail = (scan.stderr or scan.stdout).strip()[-400:]
        return _error(f"vulture exited {scan.returncode}: {detail}", tool)
    try:
        found = parse(scan.stdout)
        deferred, skipped = pending(SPECS)
    except (ImportError, OSError, ValueError) as exc:
        return _error(f"{type(exc).__name__}: {exc}", tool)

    failures = [u for u in found if u.symbol not in deferred]
    reported = {u.symbol for u in found}
    stale = sorted(e for e in deferred if e not in reported)
    summary = (
        f"{len(failures)} unused, {len(found) - len(failures)} deferred by open specs, "
        f"{len(stale)} stale pending entries"
    )
    if skipped:
        summary += f", skipped unreadable specs: {', '.join(skipped)}"
    if report:
        for u in failures:
            print(f"{u.file}:{u.line}: {u.message}")
        for entry in stale:
            print(f"stale: {entry} ({deferred[entry]})")
        print(summary)
        return 0
    return _emit(
        {
            "gate": GATE,
            "status": "fail" if failures else "pass",
            "tool": tool,
            "failures": [
                {"file": u.file, "line": u.line, "code": u.code, "message": u.message}
                for u in failures
            ],
            "summary": summary,
        }
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
