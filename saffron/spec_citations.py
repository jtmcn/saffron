"""Checking a spec's `file:line` citations against a git commit.

Ported from the spec loop driver's `cite` command
(`.claude/skills/run-saffron-spec-loop/driver.py`), which a delegate runs by
hand. `SA-0295` builds the callable a stack batch runs here instead, before
each spec review pays for a session (`DESIGN.md` §4.2.1). This module knows
git and spec text, and nothing about any repo's language or tools.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from saffron.repos.mirror import _git, file_at


@dataclass
class _Citation:
    """One `file:line` a spec quotes. `path` is `None` for a bare citation
    with no path named earlier in its own paragraph."""

    path: str | None
    start: int
    end: int
    candidates: list[str]  # sentence's other backticked strings, moved-text check


_BACKTICK = re.compile(r"`([^`]+)`")
_CITE_CONTENT = re.compile(r"^([^:\s]*):(\d+)(?:-(\d+))?$")
# Approximate, on purpose: this costs a moved-text report, never a false one.
_SENTENCE_END = re.compile(r'[.!?](?=\s+[A-Z0-9`"]|\s*$)')


def _is_path_shaped(candidate: str, suffixes: set[str]) -> bool:
    """A backticked `<text>` is a path where it holds `/`, or where it carries
    a dot and a suffix the commit's tree carries. The empty suffix never
    counts, or `06:30` and `localhost:8080` would be citations, because
    `Makefile` sits at no extension in the tree."""
    if not candidate:
        return False
    if "/" in candidate:
        return True
    suffix = Path(candidate).suffix
    return bool(suffix) and suffix in suffixes


def _sentence_spans(joined: str) -> list[tuple[int, int]]:
    spans = []
    start = 0
    for m in _SENTENCE_END.finditer(joined):
        spans.append((start, m.end()))
        start = m.end()
    spans.append((start, len(joined)))
    return spans


def _paragraph_citations(paragraph: str, suffixes: set[str]) -> list[_Citation]:
    """Every citation in one paragraph. A bare one anchors to the last path
    named earlier in it, which is a citation of its own or a plain backticked
    path."""
    joined = re.sub(r"\s+", " ", paragraph.strip())
    spans = _sentence_spans(joined)
    backticks = list(_BACKTICK.finditer(joined))
    tagged: list[tuple[int, str, bool]] = []  # sentence idx, text, is a citation
    raw: list[tuple[int, str | None, int, int]] = []  # sentence idx, path, n, m
    last_path: str | None = None
    for bt in backticks:
        content = bt.group(1)
        sentence = next(i for i, (a, b) in enumerate(spans) if a <= bt.start() < b)
        match = _CITE_CONTENT.match(content)
        is_citation = False
        if match:
            path_part, n, m = match.group(1), int(match.group(2)), match.group(3)
            end = int(m) if m else n
            if path_part:
                if _is_path_shaped(path_part, suffixes):
                    last_path = path_part
                    is_citation = True
                    raw.append((sentence, path_part, n, end))
            else:
                is_citation = True
                raw.append((sentence, last_path, n, end))
        elif _is_path_shaped(content, suffixes):
            last_path = content
        tagged.append((sentence, content, is_citation))
    return [
        _Citation(
            path=path,
            start=n,
            end=m,
            candidates=[c for s, c, cite in tagged if s == sentence and not cite],
        )
        for sentence, path, n, m in raw
    ]


def _extract_citations(text: str, suffixes: set[str]) -> list[_Citation]:
    citations = []
    for paragraph in re.split(r"\n\s*\n", text):
        if paragraph.strip():
            citations.extend(_paragraph_citations(paragraph, suffixes))
    return citations


def _range(cite: _Citation) -> str:
    return str(cite.start) if cite.start == cite.end else f"{cite.start}-{cite.end}"


def _moved_lines(cite: _Citation, lines: list[str]) -> list[int]:
    """Where the sentence's other quoted text sits, when none of it sits in
    `cite`'s own range. It returns nothing where the range carries one, or
    where the file carries none of them, so only a proven move reports."""
    if not cite.candidates:
        return []
    ranged = lines[cite.start - 1 : cite.end]
    if any(c in line for c in cite.candidates for line in ranged):
        return []
    found = {
        i for i, line in enumerate(lines, start=1) for c in cite.candidates if c in line
    }
    return sorted(found)


def citation_defects(mirror: Path, commit: str, text: str) -> list[str]:
    """Every `file:line` citation in `text` that does not resolve at `commit`
    in `mirror`, in text order. `mirror` is any git repository holding
    `commit`, bare or not. A citation resolves when its path is a regular
    file at `commit` and its range sits inside that file. Its sentence's
    other quoted text, if any, must sit inside the range too. A commit
    `mirror` lacks raises `GitError`."""
    names = set(_git(mirror, "ls-tree", "-r", "--name-only", commit).splitlines())
    suffixes = {Path(n).suffix for n in names if Path(n).suffix}
    citations = _extract_citations(text, suffixes)

    cache: dict[str, list[str] | None] = {}

    def lines_of(path: str) -> list[str] | None:
        if path not in cache:
            if path in names:
                blob = file_at(mirror, commit, path)
                cache[path] = blob.splitlines() if blob is not None else []
            else:
                cache[path] = None
        return cache[path]

    defects = []
    for cite in citations:
        if cite.path is None:
            defects.append(f":{_range(cite)}: no path named earlier in its paragraph")
            continue
        lines = lines_of(cite.path)
        if lines is None:
            defects.append(f"{cite.path}:{_range(cite)}: no such file at {commit}")
        elif cite.end > len(lines):
            defects.append(
                f"{cite.path}:{_range(cite)}: {cite.path} has {len(lines)} lines "
                f"at {commit}"
            )
        elif moved := _moved_lines(cite, lines):
            where = ", ".join(str(n) for n in moved)
            defects.append(
                f"{cite.path}:{_range(cite)}: quoted text sits at "
                f"{cite.path}:{where} instead"
            )
    return defects
