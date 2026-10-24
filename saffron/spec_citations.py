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
from saffron.repos.policy import parse_policy

_POLICY_PATH = ".saffron/policy.yaml"


@dataclass
class _Citation:
    """One `file:line` a spec quotes. `path` is `None` for a bare citation
    with no path named earlier in its own paragraph."""

    path: str | None
    start: int
    end: int
    names: list[str]  # this citation's own clause's identifier names


_BACKTICK = re.compile(r"`([^`]+)`")
_CITE_CONTENT = re.compile(r"^([^:\s]*):(\d+)(?:-(\d+))?$")
# Approximate: a wrong split can cost a false refusal or a false pass.
_SENTENCE_END = re.compile(
    r'[.!?](?=\s+[A-Z0-9`"]|\s*$)' r'|[.!?]\*\*(?=\s+[A-Z0-9`"*])'
)
_LIST_ITEM = re.compile(r"^(?:[-*]|\d+\.)\s")
_NAME_CALL = re.compile(r"^(?:[A-Za-z_]\w*\.)*([A-Za-z_]\w*)\(.*\)$")
_NAME_PLAIN = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*$")


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


def _read_name(candidate: str, suffixes: set[str]) -> str | None:
    """A backtick's name, read as its last dotted part, for a bare `x`, a
    dotted `a.b`, a no-argument call `f()` or a dotted call `a.f(x)`. A
    path, or any other token, names nothing."""
    if _is_path_shaped(candidate, suffixes):
        return None
    call = _NAME_CALL.match(candidate)
    if call:
        return call.group(1)
    if _NAME_PLAIN.match(candidate):
        return candidate.rsplit(".", 1)[-1]
    return None


def _join_paragraph(paragraph: str) -> tuple[str, list[int]]:
    """A paragraph's lines joined with single spaces, and where each line
    starting `-`, `*` or `N.` then whitespace begins in the joined text:
    such a line starts a fresh sentence there."""
    pieces: list[str] = []
    breaks: list[int] = []
    pos = 0
    for i, raw in enumerate(paragraph.strip().splitlines()):
        stripped = raw.strip()
        line = re.sub(r"\s+", " ", stripped)
        if i > 0:
            pieces.append(" ")
            pos += 1
        if _LIST_ITEM.match(stripped):
            breaks.append(pos)
        pieces.append(line)
        pos += len(line)
    return "".join(pieces), breaks


def _sentence_spans(joined: str, forced_breaks: list[int]) -> list[tuple[int, int]]:
    ends = {m.end() for m in _SENTENCE_END.finditer(joined)}
    boundaries = sorted(b for b in {0, *forced_breaks, *ends} if 0 <= b <= len(joined))
    spans = []
    for i, start in enumerate(boundaries):
        end = boundaries[i + 1] if i + 1 < len(boundaries) else len(joined)
        if end > start:
            spans.append((start, end))
    return spans


def _paragraph_citations(paragraph: str, suffixes: set[str]) -> list[_Citation]:
    """Every citation in one paragraph. A bare one anchors to the last path
    named earlier in it, which is a citation of its own or a plain backticked
    path. A citation's names are its own clause's identifiers. Its clause
    runs from the previous citation in its sentence, or the sentence's
    start, to itself. An empty clause takes the names of the one before it
    in the same sentence."""
    joined, forced_breaks = _join_paragraph(paragraph)
    spans = _sentence_spans(joined, forced_breaks)
    backticks = list(_BACKTICK.finditer(joined))
    last_path: str | None = None
    citations: list[_Citation] = []
    sentence = -1
    clause_names: list[str] = []
    prev_clause_names: list[str] = []
    for bt in backticks:
        content = bt.group(1)
        this_sentence = next(i for i, (a, b) in enumerate(spans) if a <= bt.start() < b)
        if this_sentence != sentence:
            sentence = this_sentence
            clause_names = []
            prev_clause_names = []
        match = _CITE_CONTENT.match(content)
        is_citation = False
        cite_path: str | None = None
        cite_start = cite_end = 0
        if match:
            path_part, n, m = match.group(1), int(match.group(2)), match.group(3)
            end = int(m) if m else n
            if path_part:
                if _is_path_shaped(path_part, suffixes):
                    last_path = path_part
                    is_citation = True
                    cite_path, cite_start, cite_end = path_part, n, end
            else:
                is_citation = True
                cite_path, cite_start, cite_end = last_path, n, end
        elif _is_path_shaped(content, suffixes):
            last_path = content
        if is_citation:
            names = clause_names if clause_names else prev_clause_names
            citations.append(
                _Citation(
                    path=cite_path, start=cite_start, end=cite_end, names=list(names)
                )
            )
            prev_clause_names = names
            clause_names = []
        else:
            name = _read_name(content, suffixes)
            if name is not None:
                clause_names.append(name)
    return citations


def _extract_citations(text: str, suffixes: set[str]) -> list[_Citation]:
    citations = []
    for paragraph in re.split(r"\n\s*\n", text):
        if paragraph.strip():
            citations.extend(_paragraph_citations(paragraph, suffixes))
    return citations


def _range(cite: _Citation) -> str:
    return str(cite.start) if cite.start == cite.end else f"{cite.start}-{cite.end}"


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _construct_span(lines: list[str], start_idx: int) -> tuple[int, int]:
    """The construct opening at `lines[start_idx]`, as a 1-based inclusive
    line range. It runs to the last later non-blank line indented past the
    opener, or level with it and opening with `)`, `]` or `}`. A blank line
    does not end it."""
    indent = _indent(lines[start_idx])
    last = start_idx
    for i in range(start_idx + 1, len(lines)):
        line = lines[i]
        if not line.strip():
            continue
        cur = _indent(line)
        text = line.lstrip()
        if cur > indent or (cur == indent and text[:1] in ")]}"):
            last = i
        else:
            break
    return start_idx + 1, last + 1


def _name_spans(
    names: list[str], lines: list[str], patterns: list[str]
) -> list[tuple[int, int]]:
    """Every construct any of `names` opens, through any declared pattern,
    deduplicated and ordered by its starting line."""
    seen: set[tuple[int, int]] = set()
    for name in names:
        for pattern in patterns:
            regex = re.compile(pattern.replace("{name}", re.escape(name)))
            for i, line in enumerate(lines):
                if regex.match(line):
                    seen.add(_construct_span(lines, i))
    return sorted(seen)


def _construct_defect(
    cite: _Citation, lines: list[str], patterns: list[str]
) -> str | None:
    """`None` when `cite` passes the construct check. A citation passes
    when its names find no construct, or its range sits inside one, or
    holds one whole. It also passes when a range line outside every found
    construct still quotes one of its names as a whole word. Otherwise the
    defect names where each construct sits."""
    spans = _name_spans(cite.names, lines, patterns)
    if not spans:
        return None
    if any(
        (s <= cite.start and cite.end <= e) or (cite.start <= s and e <= cite.end)
        for s, e in spans
    ):
        return None
    outside = [
        ln
        for ln in range(cite.start, cite.end + 1)
        if not any(s <= ln <= e for s, e in spans)
    ]
    if any(
        re.search(rf"\b{re.escape(name)}\b", lines[ln - 1])
        for ln in outside
        for name in cite.names
    ):
        return None
    where = ", ".join(str(s) if s == e else f"{s}-{e}" for s, e in spans)
    return (
        f"{cite.path}:{_range(cite)}: the construct it names sits at "
        f"{cite.path}:{where}"
    )


def _citation_patterns(mirror: Path, commit: str, names_in_tree: set[str]) -> list[str]:
    """The `citations.definitions` patterns `.saffron/policy.yaml` declares
    at `commit`, or none when `commit`'s tree holds no such file."""
    if _POLICY_PATH not in names_in_tree:
        return []
    raw = file_at(mirror, commit, _POLICY_PATH)
    if raw is None:
        return []
    return parse_policy(raw.encode()).citations.definitions


def citation_count_and_defects(
    mirror: Path, commit: str, text: str
) -> tuple[int, list[str]]:
    """How many `file:line` citations `text` makes, and the defects among
    them, in text order. `mirror` is any git repository holding `commit`,
    bare or not. A range's shape is checked before any file: no path, then
    a start below line 1, then an end before its start. A citation that
    passes those is then refused for a missing file or a range past its
    end. Otherwise it is judged against the constructs its own clause's
    names open, read from `.saffron/policy.yaml` at `commit`. A commit
    `mirror` lacks raises `GitError`. An invalid policy at `commit` raises
    `PolicyError`.
    """
    names_in_tree = set(
        _git(mirror, "ls-tree", "-r", "--name-only", commit).splitlines()
    )
    suffixes = {Path(n).suffix for n in names_in_tree if Path(n).suffix}
    citations = _extract_citations(text, suffixes)
    patterns = _citation_patterns(mirror, commit, names_in_tree)

    cache: dict[str, list[str] | None] = {}

    def lines_of(path: str) -> list[str] | None:
        if path not in cache:
            if path in names_in_tree:
                blob = file_at(mirror, commit, path)
                cache[path] = blob.splitlines() if blob is not None else []
            else:
                cache[path] = None
        return cache[path]

    defects = []
    for cite in citations:
        range_str = _range(cite)
        if cite.path is None:
            defects.append(f":{range_str}: no path named earlier in its paragraph")
            continue
        if cite.start < 1:
            defects.append(f"{cite.path}:{range_str}: starts before line 1")
            continue
        if cite.end < cite.start:
            defects.append(f"{cite.path}:{range_str}: ends before it starts")
            continue
        lines = lines_of(cite.path)
        if lines is None:
            defects.append(f"{cite.path}:{range_str}: no such file at {commit}")
        elif cite.end > len(lines):
            defects.append(
                f"{cite.path}:{range_str}: {cite.path} has {len(lines)} lines "
                f"at {commit}"
            )
        else:
            defect = _construct_defect(cite, lines, patterns)
            if defect:
                defects.append(defect)
    return len(citations), defects


def citation_defects(mirror: Path, commit: str, text: str) -> list[str]:
    """`citation_count_and_defects`'s defects half, which judges each
    citation by the construct its clause names."""
    return citation_count_and_defects(mirror, commit, text)[1]
