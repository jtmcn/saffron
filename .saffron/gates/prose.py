#!/usr/bin/env python3
"""The `prose` and `terms` gates: Saffron's house style and vocabulary over its living Markdown.

Design: `docs/superpowers/specs/2026-09-16-prose-ratchet-design.md`. Parsing
adapts `strip_code` and `sentences` from AminBlg/SimpleEnglish
(`evals/ste_lint.py`, MIT), changed to keep every newline so that a hit's
line is its source line.

Standard library only: a cell runs this under plain `python3`, from the base
commit's `.saffron/`, against the tree in the cwd.
"""

from __future__ import annotations

import bisect
import functools
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

GATES = ("prose", "terms")

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

# "May 2026" names a month.
HEDGE = re.compile(r"\b(?:should|may(?!\s+\d)|might)\b", re.I)
EM_DASH = re.compile(r"—|(?<!\d)–(?!\d)|(?<=\s)--(?=\s)|(?<=[A-Za-z]) - (?=[A-Za-z])")
SEMICOLON = re.compile(";")
PERFECT = re.compile(r"\b(?:has|have|had)\s+been\b|\b(?:has|have)\s+\w+ed\b", re.I)
# Any other 's reads as a possessive, so only these count.
CONTRACTION = re.compile(
    r"\b\w+(?:n['’]t|['’]ll|['’]re|['’]ve|['’]d)\b"
    r"|\b(?:it|that|there|here|what|who|where|let|he|she)['’]s\b",
    re.I,
)
TRAILING = re.compile(r"\s(?:if|when)\s", re.I)
WORD_RULES = (
    ("hedge", HEDGE),
    ("em-dash", EM_DASH),
    ("semicolon", SEMICOLON),
    ("perfect-tense", PERFECT),
    ("contraction", CONTRACTION),
)

_OLDER = "The line shown can be an older one."
# Fixed per code, so identity stays per file and rule. A REPAIR turn reads the text.
MESSAGES = {
    "sentence-length": f"this file gained a sentence over {SENTENCE_LIMIT} words;"
    f" split one. {_OLDER}",
    "hedge": "this file gained a should/may/might; say must, or state the fact."
    f" {_OLDER}",
    "em-dash": "this file gained an em-dash or spaced hyphen; use two sentences"
    f" or name the relation. {_OLDER}",
    "semicolon": f"this file gained a semicolon in prose; use two sentences. {_OLDER}",
    "filler": f"this file gained a filler word ({', '.join(FILLER[:8])}, ...);"
    f" delete it. {_OLDER}",
    "perfect-tense": "this file gained a has/have/had been or has/have + -ed;"
    f" use the simple past. {_OLDER}",
    "trailing-condition": "a spec instruction gained a mid-sentence if/when;"
    f" put the condition first. {_OLDER}",
    "contraction": f"this file gained a contraction; write the words out. {_OLDER}",
    "rendered-span": "a span ontology.render writes could not be located;"
    " fix the definition or the principle index at its source.",
}

_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
_FENCE = re.compile(r"^[ \t]*(`{3,}|~{3,}).*?^[ \t]*\1[^\n]*$", re.S | re.M)
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_HEADING = re.compile(r"^#{1,6}\s.*$", re.M)
_TABLE_RULE = re.compile(r"^\s*\|[\s:|-]+\|\s*$", re.M)
_TABLE_ROW = re.compile(r"^[ \t]*\|(.*)\|[ \t]*$", re.M)
_CODE_SPAN = re.compile(r"`[^`\n]+`")
_URL = re.compile(r"https?://\S+")
# At most one line break, so a quote can wrap but a stray `"` cannot hide a paragraph.
_QUOTED = re.compile(r'"[^"\n]*(?:\n[^"\n]*)?"|“[^”\n]*(?:\n[^”\n]*)?”')
_BREAK = re.compile(r"(?<=[.!?:])\s+|\n[ \t]*\n\s*|\n(?=[ \t]*(?:[-*+]|\d+\.)[ \t])")
_ITEM = re.compile(r"[ \t]*(?:[-*+]|\d+\.)[ \t]+(?:\[[ xX]\][ \t]+)?")
_BOLD_TERM = re.compile(r"^\*\*([^*]+)\*\*", re.M)

# Phrase -> (the Saffron term, its CONTEXT.md section). An entry is quoted on
# that term's _Avoid_ line, and every hit in scope was a misuse when it entered.
AVOIDED = {
    "sandbox": ("cell", "§1"),
    "ticket": ("spec", "§2"),
    "work item": ("task", "§2"),
    "the denylist": ("protected paths", "§3"),
    "soft fail": ("advisory", "§4"),
    "self-heal": ("repair", "§4"),
    "auto-fix": ("repair", "§4"),
}


@dataclass(frozen=True)
class Hit:
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


def _spaces(text: str) -> str:
    return re.sub(r"[^\n]", " ", text)


def _blank(match: re.Match[str]) -> str:
    return _spaces(match.group(0))


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


_BARE_ORDINAL = re.compile(r"\A\d+\.\Z")


def _at_line_start(body: str, offset: int) -> bool:
    """Only spaces or tabs precede `offset` on its own line."""
    line_start = body.rfind("\n", 0, offset) + 1
    return not body[line_start:offset].strip()


def _sentences(body: str) -> Iterator[_Sentence]:
    pos = 0
    carry_item = False
    for match in [*_BREAK.finditer(body), None]:
        end = match.start() if match else len(body)
        chunk = body[pos:end]
        item = _ITEM.match(chunk)
        offset = pos + (item.end() if item else len(chunk) - len(chunk.lstrip()))
        text = body[offset:end].strip()
        is_item = item is not None or carry_item
        carry_item = False
        # `_BREAK` splits after a numbered marker's period, so carry the marker to
        # the next chunk. Only at a line start: a mid-sentence "N." is no marker.
        if (
            not is_item
            and match is not None
            and _BARE_ORDINAL.fullmatch(text)
            and _at_line_start(body, offset)
        ):
            carry_item = True
        elif len(text.split()) >= 2:
            yield _Sentence(offset, text, is_item)
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
            try:
                start, end = spans.definition_sentence(text, term)
            except ValueError:
                # `check` reports this file as `rendered-span`.
                continue
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


def _style(text: _Text, path: str, root: Path) -> list[Hit]:
    found = []
    spec = path.startswith(".saffron/specs/")
    for sentence in _sentences(text.body):
        if len(sentence.text.split()) > SENTENCE_LIMIT:
            found.append(
                Hit(
                    text.line(sentence.start),
                    "sentence-length",
                    _excerpt(sentence.text),
                )
            )
        if (
            spec
            and sentence.is_item
            and TRAILING.search(_QUOTED.sub(" ", sentence.text))
            and not re.match(r"(?:if|when)\b", sentence.text, re.I)
        ):
            found.append(
                Hit(
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
            found.append(Hit(line, code, _excerpt(text.line_text(match.start()))))
    return found


def _avoided(text: _Text) -> list[Hit]:
    unquoted = _QUOTED.sub(_blank, text.body)
    found = []
    for phrase, (term, section) in AVOIDED.items():
        spelled = re.escape(phrase).replace(r"\ ", r"\s+")
        message = f'{phrase}: say "{term}" (CONTEXT.md {section})'
        for match in re.finditer(rf"\b{spelled}\b", unquoted, re.I):
            found.append(Hit(text.line(match.start()), "avoided-term", message))
    return found


def check(text: str, path: str, gate: str, *, root: Path) -> list[Hit]:
    """Every hit `gate` reports for `text`, read as the file at `path`."""
    if gate not in GATES:
        raise ValueError(f"unknown gate: {gate}")
    try:
        rendered = _rendered(text, path, root)
    except ValueError as exc:
        # The repo's defect, not the gate's: a `fail` gets a REPAIR turn. The
        # blocking gate reports it once; `terms` reads the file unexempted.
        if gate == "prose":
            return [Hit(1, "rendered-span", _excerpt(str(exc)))]
        rendered = []
    for start, end in rendered:
        text = text[:start] + _spaces(text[start:end]) + text[end:]
    prepared = _Text(_prepare(text))
    found = _style(prepared, path, root) if gate == "prose" else _avoided(prepared)
    return sorted(found, key=lambda f: (f.line, f.code))


def _emit(payload: dict[str, object]) -> int:
    print(json.dumps(payload))
    return 0


def _listed(root: Path) -> subprocess.CompletedProcess[str]:
    # Untracked files count: a cell's edits reach the gates before any commit.
    return subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        capture_output=True,
        text=True,
    )


# ponytail: every hit is one failure row per suite result (about 4,800 here
# today), so rows grow with the prose; the ceiling is the ledger's size.
# ponytail: identity includes the file, so an in-scope rename reads every hit
# as new and fails `prose`, while `hooks/prose_limit.py` follows renames.
def main(argv: list[str]) -> int:
    if argv == ["--version"]:
        # Not `ontology/spans.py`, which this executes: `gate_config` guards it instead.
        digest = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]
        print(f"saffron-prose {digest}")
        return 0
    if len(argv) != 1 or argv[0] not in GATES:
        print(f"usage: prose.py --version | {' | '.join(GATES)}", file=sys.stderr)
        return 2
    gate = argv[0]
    try:
        version = subprocess.run(
            [sys.executable, __file__, "--version"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _emit(
            {"gate": gate, "status": "error", "summary": f"--version failed: {exc}"}
        )
    tool = version.stdout.strip()
    if version.returncode != 0 or not tool:
        return _emit(
            {"gate": gate, "status": "error", "summary": "--version printed nothing"}
        )

    root = Path.cwd()
    listed = _listed(root)
    if listed.returncode != 0:
        summary = f"git ls-files failed: {listed.stderr.strip()}"
        return _emit(
            {"gate": gate, "status": "error", "tool": tool, "summary": summary}
        )
    paths = sorted(
        {
            p
            for p in listed.stdout.split("\0")
            if p and in_scope(p) and (root / p).is_file()
        }
    )
    if not paths:
        summary = "no Markdown file is in scope, so nothing was read"
        return _emit(
            {"gate": gate, "status": "error", "tool": tool, "summary": summary}
        )

    failures: list[dict[str, object]] = []
    counts: Counter[str] = Counter()
    try:
        for path in paths:
            text = (root / path).read_text(encoding="utf-8", errors="replace")
            for hit in check(text, path, gate, root=root):
                message = MESSAGES[hit.code] if gate == "prose" else hit.excerpt
                failures.append(
                    {
                        "file": path,
                        "line": hit.line,
                        "code": hit.code,
                        "message": message,
                    }
                )
                counts[hit.code] += 1
    except (OSError, ValueError) as exc:
        summary = f"{type(exc).__name__}: {exc}"
        return _emit(
            {"gate": gate, "status": "error", "tool": tool, "summary": summary}
        )

    by_code = ", ".join(f"{code} {n}" for code, n in counts.most_common())
    return _emit(
        {
            "gate": gate,
            "status": "fail" if failures else "pass",
            "tool": tool,
            "failures": failures,
            "summary": f"{len(failures)} failures in {len(paths)} files. {by_code}".strip(),
        }
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
