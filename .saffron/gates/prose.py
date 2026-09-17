#!/usr/bin/env python3
"""The `prose` gate: Saffron's house style over its living Markdown.

Design: `docs/superpowers/specs/2026-09-16-prose-ratchet-design.md`. Parsing
adapts `strip_code` and `sentences` from AminBlg/SimpleEnglish
(`evals/ste_lint.py`, MIT), changed to keep every newline so that a finding's
line is its source line.

A `prose` failure's `message` is its rule code, so baseline subtraction cancels
one pre-existing finding per file and rule (§5.4). `hooks/prose_limit.py`
applies the same limit to a commit.

Standard library only: this executes under a cell's plain `python3`, from the
base commit's `.saffron/`, and reads everything else from the cwd.
"""

from __future__ import annotations

import bisect
import functools
import importlib.util
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

GATES = ("prose",)

ROOT_FILES = ("CONTEXT.md", "CLAUDE.md", "DESIGN.md", "README.md")
INCLUDED_DIRS = (
    "docs/backlog/",
    ".saffron/specs/",
    ".claude/agents/",
    ".claude/skills/",
)
# A finished spec records what a cell was told, so it stays as written.
EXCLUDED_DIRS = (".saffron/specs/done/",)

SENTENCE_LIMIT = 25
# Saffron's own intensifiers, measured. "exactly" and "deliberately" carry meaning here.
FILLER = (
    "actually",
    "genuinely",
    "precisely",
    "merely",
    "simply",
    "just",
    "very",
    "really",
    "obviously",
    "clearly",
    "essentially",
    "basically",
    "quietly",
    "in fact",
    "note that",
)

HEDGE = re.compile(r"\b(?:should|may|might)\b", re.I)
EM_DASH = re.compile(r"—|(?<!\d)–(?!\d)|(?<=\s)--(?=\s)|(?<=[A-Za-z]) - (?=[A-Za-z])")
SEMICOLON = re.compile(";")
PERFECT = re.compile(r"\b(?:has|have|had)\s+been\b|\b(?:has|have)\s+\w+ed\b", re.I)
CONTRACTION = re.compile(
    r"\b\w+(?:n['’]t|['’]ll|['’]re|['’]ve|['’]d)\b|\bit['’]s\b", re.I
)
TRAILING = re.compile(r"\s(?:if|when)\s", re.I)
WORD_RULES = (
    ("hedge", HEDGE),
    ("em-dash", EM_DASH),
    ("semicolon", SEMICOLON),
    ("perfect-tense", PERFECT),
    ("contraction", CONTRACTION),
)

_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
_FENCE = re.compile(r"^[ \t]*(`{3,}|~{3,}).*?^[ \t]*\1[^\n]*$", re.S | re.M)
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_HEADING = re.compile(r"^#{1,6}\s.*$", re.M)
_TABLE_RULE = re.compile(r"^\s*\|[\s:|-]+\|\s*$", re.M)
_TABLE_ROW = re.compile(r"^[ \t]*\|(.*)\|[ \t]*$", re.M)
_CODE_SPAN = re.compile(r"`[^`\n]+`")
_URL = re.compile(r"https?://\S+")
_QUOTED = re.compile(r'"[^"\n]*"|“[^”\n]*”')
_BREAK = re.compile(r"(?<=[.!?:])\s+|\n[ \t]*\n\s*|\n(?=[ \t]*(?:[-*+]|\d+\.)[ \t])")
_ITEM = re.compile(r"[ \t]*(?:[-*+]|\d+\.)[ \t]+(?:\[[ xX]\][ \t]+)?")
_BOLD_TERM = re.compile(r"^\*\*([^*]+)\*\*", re.M)


@dataclass(frozen=True)
class Finding:
    line: int
    code: str
    excerpt: str


@dataclass(frozen=True)
class _Sentence:
    start: int
    text: str
    is_item: bool


class _Text:
    """Prepared Markdown, with line lookups by offset."""

    def __init__(self, body: str) -> None:
        self.body = body
        self._newlines = [m.start() for m in re.finditer("\n", body)]

    def line(self, offset: int) -> int:
        return bisect.bisect_right(self._newlines, offset) + 1

    def line_text(self, offset: int) -> str:
        n = bisect.bisect_right(self._newlines, offset)
        start = self._newlines[n - 1] + 1 if n else 0
        end = self._newlines[n] if n < len(self._newlines) else len(self.body)
        return self.body[start:end]


def in_scope(path: str) -> bool:
    if not path.endswith(".md") or path.startswith(EXCLUDED_DIRS):
        return False
    return path in ROOT_FILES or path.startswith(INCLUDED_DIRS)


def _blank(match: re.Match[str]) -> str:
    return re.sub(r"[^\n]", " ", match.group(0))


def _cells(match: re.Match[str]) -> str:
    cells = [cell.strip() for cell in match.group(1).split("|")]
    return ". ".join(cell for cell in cells if cell) + "."


def _prepare(text: str) -> str:
    """Remove what is not prose. Every newline stays where it was."""
    for pattern in (_FRONTMATTER, _FENCE, _COMMENT, _HEADING, _TABLE_RULE):
        text = pattern.sub(_blank, text)
    text = _TABLE_ROW.sub(_cells, text)
    # One word per span, with no padding, so "`a`, `b`" is not read as four words.
    text = _CODE_SPAN.sub("CODESPAN", text)
    return _URL.sub(" URL ", text)


def _sentences(body: str) -> Iterator[_Sentence]:
    pos = 0
    for match in [*_BREAK.finditer(body), None]:
        end = match.start() if match else len(body)
        chunk = body[pos:end]
        item = _ITEM.match(chunk)
        offset = pos + (item.end() if item else len(chunk) - len(chunk.lstrip()))
        text = body[offset:end].strip()
        if len(text.split()) >= 2:
            yield _Sentence(offset, text, item is not None)
        if match:
            pos = match.end()


def _excerpt(text: str) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= 80 else flat[:79] + "…"


@functools.cache
def _spans(root: Path) -> Any:
    """`ontology/spans.py` from the tree under judgement, loaded by path."""
    path = root / "ontology" / "spans.py"
    spec = importlib.util.spec_from_file_location("saffron_ontology_spans", path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rendered(text: str, path: str, root: Path) -> list[tuple[int, int]]:
    """What `ontology.render` writes. A long rendered line is fixed at its source."""
    if path == "DESIGN.md":
        spans = _spans(root)
        return [spans.principle_index(text)] if spans.PRINCIPLE_ANCHOR in text else []
    if path == "CONTEXT.md":
        spans = _spans(root)
        return [
            spans.definition_sentence(text, term)
            for term in spans.SETS
            if f"**{term}**" in text
        ]
    return []


@functools.cache
def protected_words(root: Path) -> frozenset[str]:
    """Defined terms and closed-set members, which no filler list may name."""
    context = root / "CONTEXT.md"
    if not context.exists():
        return frozenset()
    text = context.read_text(encoding="utf-8")
    words = {
        part.strip().lower()
        for term in _BOLD_TERM.findall(text)
        for part in term.split("/")
    }
    spans = _spans(root)
    for term in spans.SETS:
        if f"**{term}**" in text:
            start, end = spans.definition_sentence(text, term)
            words.update(m.lower() for m in spans.MEMBER_TOKEN.findall(text[start:end]))
    return frozenset(words)


@functools.cache
def _filler_pattern(
    filler: tuple[str, ...], protected: frozenset[str]
) -> re.Pattern[str] | None:
    kept = [word for word in filler if word not in protected]
    if not kept:
        return None
    alternation = "|".join(re.escape(word).replace(r"\ ", r"\s+") for word in kept)
    return re.compile(rf"\b(?:{alternation})\b", re.I)


def _style(text: _Text, path: str, root: Path) -> list[Finding]:
    found = []
    spec = path.startswith(".saffron/specs/")
    for sentence in _sentences(text.body):
        if len(sentence.text.split()) > SENTENCE_LIMIT:
            found.append(
                Finding(
                    text.line(sentence.start),
                    "sentence-length",
                    _excerpt(sentence.text),
                )
            )
        if (
            spec
            and sentence.is_item
            and TRAILING.search(sentence.text)
            and not re.match(r"(?:if|when)\b", sentence.text, re.I)
        ):
            found.append(
                Finding(
                    text.line(sentence.start),
                    "trailing-condition",
                    _excerpt(sentence.text),
                )
            )
    # A quoted word is a mention, and CONTEXT.md quotes the words it rules on.
    unquoted = _QUOTED.sub(_blank, text.body)
    rules = list(WORD_RULES)
    filler = _filler_pattern(FILLER, protected_words(root))
    if filler is not None:
        rules.append(("filler", filler))
    for code, pattern in rules:
        for match in pattern.finditer(unquoted):
            line = text.line(match.start())
            found.append(Finding(line, code, _excerpt(text.line_text(match.start()))))
    return found


def check(text: str, path: str, gate: str, *, root: Path) -> list[Finding]:
    """Every finding `gate` reports for `text`, read as the file at `path`."""
    if gate not in GATES:
        raise ValueError(f"unknown gate: {gate}")
    for start, end in _rendered(text, path, root):
        text = text[:start] + re.sub(r"[^\n]", " ", text[start:end]) + text[end:]
    prepared = _Text(_prepare(text))
    found = _style(prepared, path, root)
    return sorted(found, key=lambda f: (f.line, f.code))


def main(argv: list[str]) -> int:
    raise NotImplementedError("Task 3")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
