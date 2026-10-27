"""Checking a spec's `file:line` citations against a git commit.

Ported from the spec loop driver's `cite` command
(`.claude/skills/run-saffron-spec-loop/driver.py`), which a delegate runs by
hand. `SA-0295` builds the callable a stack batch runs here instead, before
each spec review pays for a session (`DESIGN.md` §4.2.1). `SA-0321` adds
`citations_held_at` and `rewrite_moved_citations`, so a citation a parent's
later commits moved can be moved onto its construct rather than refused.
This module knows git and spec text, and nothing about any repo's language
or tools.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from saffron.repos.mirror import _git, file_at
from saffron.repos.policy import parse_policy

_POLICY_PATH = ".saffron/policy.yaml"


@dataclass
class _Citation:
    """One `file:line` a spec quotes. `path` is `None` for a bare citation
    with no path named earlier in its own paragraph. `offset` is its
    content's start in the text read, right after the opening backtick.
    `range_at` is where its range substring sits there."""

    path: str | None
    start: int
    end: int
    names: list[str]  # this citation's own clause's identifier names
    offset: int
    range_at: tuple[int, int]


@dataclass(frozen=True)
class CitationDefect:
    """One citation that fails the check. `str` returns the line the
    checker used to print. `spans` maps a construct defect's clause
    names to the constructs each opens now. Only a construct defect
    carries it. `replace` is where its range substring sits in the text
    read, for that same kind alone."""

    line: str
    path: str | None
    offset: int
    replace: tuple[int, int] | None
    spans: Mapping[str, tuple[tuple[int, int], ...]] | None

    def __str__(self) -> str:
        return self.line


class Rewrite(NamedTuple):
    """One `rewrite_moved_citations` edit: a citation's path, as written,
    and its range before and after the move."""

    path: str | None
    old: str
    new: str


_BACKTICK = re.compile(r"`([^`]+)`")
_CITE_CONTENT = re.compile(r"^([^:\s]*):(\d+)(?:-(\d+))?$")
# Approximate: a wrong split can cost a false refusal or a false pass.
_SENTENCE_END = re.compile(
    r'[.!?](?=\s+[A-Z0-9`"]|\s*$)' r'|[.!?]\*\*(?=\s+[A-Z0-9`"*])'
)
_LIST_ITEM = re.compile(r"^(?:[-*]|\d+\.)\s")
_NAME_CALL = re.compile(r"^(?:[A-Za-z_]\w*\.)*([A-Za-z_]\w*)\(.*\)$")
_NAME_PLAIN = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*$")
_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")


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


def _paragraph_citations(
    paragraph: str, suffixes: set[str], paragraph_start: int
) -> list[_Citation]:
    """Every citation in one paragraph, read at `paragraph_start` in the
    text it came from. A bare one anchors to the last path named earlier in
    it, which is a citation of its own or a plain backticked path. A
    citation's names are its own clause's identifiers. Its clause runs from
    the previous citation in its sentence, or the sentence's start, to
    itself. An empty clause takes the names of the one before it in the
    same sentence."""
    joined, forced_breaks = _join_paragraph(paragraph)
    spans = _sentence_spans(joined, forced_breaks)
    # A citation token holds no whitespace, so joining never moves a backtick pair.
    # The k-th pair here is also the k-th in the raw paragraph, with the same content.
    backticks = list(
        zip(_BACKTICK.finditer(joined), _BACKTICK.finditer(paragraph), strict=True)
    )
    last_path: str | None = None
    citations: list[_Citation] = []
    sentence = -1
    clause_names: list[str] = []
    prev_clause_names: list[str] = []
    for bt, raw in backticks:
        content = bt.group(1)
        content_offset = paragraph_start + raw.start(1)
        this_sentence = next(i for i, (a, b) in enumerate(spans) if a <= bt.start() < b)
        if this_sentence != sentence:
            sentence = this_sentence
            clause_names = []
            prev_clause_names = []
        match = _CITE_CONTENT.match(content)
        is_citation = False
        cite_path: str | None = None
        cite_start = cite_end = 0
        range_at = (content_offset, content_offset)
        if match:
            path_part, n, m = match.group(1), int(match.group(2)), match.group(3)
            end = int(m) if m else n
            range_end = match.end(3) if m else match.end(2)
            range_at = (content_offset + match.start(2), content_offset + range_end)
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
                    path=cite_path,
                    start=cite_start,
                    end=cite_end,
                    names=list(names),
                    offset=content_offset,
                    range_at=range_at,
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
    pos = 0
    parts = re.split(f"({_PARAGRAPH_SPLIT.pattern})", text)
    for i, part in enumerate(parts):
        if i % 2 == 0 and part.strip():
            citations.extend(_paragraph_citations(part, suffixes, pos))
        pos += len(part)
    return citations


def _range(start: int, end: int) -> str:
    return str(start) if start == end else f"{start}-{end}"


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


def _name_spans_by_name(
    names: list[str], lines: list[str], patterns: list[str]
) -> dict[str, list[tuple[int, int]]]:
    """Every construct each of `names` opens on its own, through any
    declared pattern, deduplicated and ordered by its starting line."""
    result: dict[str, list[tuple[int, int]]] = {}
    for name in names:
        seen: set[tuple[int, int]] = set()
        for pattern in patterns:
            regex = re.compile(pattern.replace("{name}", re.escape(name)))
            for i, line in enumerate(lines):
                if regex.match(line):
                    seen.add(_construct_span(lines, i))
        result[name] = sorted(seen)
    return result


def _construct_defect(
    cite: _Citation, lines: list[str], patterns: list[str]
) -> CitationDefect | None:
    """`None` when `cite` passes the construct check. A citation passes
    when its names find no construct, or its range sits inside one, or
    holds one whole. It also passes when a range line outside every found
    construct still quotes one of its names as a whole word. Otherwise the
    defect names where each construct sits, and carries each name's own
    spans for a later rewrite."""
    by_name = _name_spans_by_name(cite.names, lines, patterns)
    spans = sorted({span for found in by_name.values() for span in found})
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
    where = ", ".join(_range(s, e) for s, e in spans)
    line = (
        f"{cite.path}:{_range(cite.start, cite.end)}: the construct it names sits "
        f"at {cite.path}:{where}"
    )
    spans_map = {name: tuple(found) for name, found in by_name.items() if found}
    return CitationDefect(
        line=line,
        path=cite.path,
        offset=cite.offset,
        replace=cite.range_at,
        spans=spans_map,
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


def _tree_names(mirror: Path, commit: str) -> set[str]:
    return set(_git(mirror, "ls-tree", "-r", "--name-only", commit).splitlines())


def _lines_reader(mirror: Path, commit: str, names_in_tree: set[str]):
    cache: dict[str, list[str] | None] = {}

    def lines_of(path: str) -> list[str] | None:
        if path not in cache:
            if path in names_in_tree:
                blob = file_at(mirror, commit, path)
                cache[path] = blob.splitlines() if blob is not None else []
            else:
                cache[path] = None
        return cache[path]

    return lines_of


def citation_count_and_defects(
    mirror: Path, commit: str, text: str
) -> tuple[int, list[CitationDefect]]:
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
    names_in_tree = _tree_names(mirror, commit)
    suffixes = {Path(n).suffix for n in names_in_tree if Path(n).suffix}
    citations = _extract_citations(text, suffixes)
    patterns = _citation_patterns(mirror, commit, names_in_tree)
    lines_of = _lines_reader(mirror, commit, names_in_tree)

    defects: list[CitationDefect] = []
    for cite in citations:
        range_str = _range(cite.start, cite.end)
        if cite.path is None:
            defects.append(
                CitationDefect(
                    line=f":{range_str}: no path named earlier in its paragraph",
                    path=None,
                    offset=cite.offset,
                    replace=None,
                    spans=None,
                )
            )
            continue
        if cite.start < 1:
            defects.append(
                CitationDefect(
                    line=f"{cite.path}:{range_str}: starts before line 1",
                    path=cite.path,
                    offset=cite.offset,
                    replace=None,
                    spans=None,
                )
            )
            continue
        if cite.end < cite.start:
            defects.append(
                CitationDefect(
                    line=f"{cite.path}:{range_str}: ends before it starts",
                    path=cite.path,
                    offset=cite.offset,
                    replace=None,
                    spans=None,
                )
            )
            continue
        lines = lines_of(cite.path)
        if lines is None:
            defects.append(
                CitationDefect(
                    line=f"{cite.path}:{range_str}: no such file at {commit}",
                    path=cite.path,
                    offset=cite.offset,
                    replace=None,
                    spans=None,
                )
            )
        elif cite.end > len(lines):
            defects.append(
                CitationDefect(
                    line=f"{cite.path}:{range_str}: {cite.path} has {len(lines)} "
                    f"lines at {commit}",
                    path=cite.path,
                    offset=cite.offset,
                    replace=None,
                    spans=None,
                )
            )
        else:
            defect = _construct_defect(cite, lines, patterns)
            if defect:
                defects.append(defect)
    return len(citations), defects


def citation_defects(mirror: Path, commit: str, text: str) -> list[CitationDefect]:
    """`citation_count_and_defects`'s defects half, which judges each
    citation by the construct its clause names."""
    return citation_count_and_defects(mirror, commit, text)[1]


def _holds(span: tuple[int, int], start: int, end: int) -> bool:
    s, e = span
    return (s <= start and end <= e) or (start <= s and e <= end)


def _sole_holder(holders: list[tuple[str, tuple[int, int]]]) -> str | None:
    """Among names that each hold a citation on their own, the one name
    whose span sits inside every other, and is strictly shorter than each.
    `None` when no single name qualifies: two disjoint spans, or two of
    equal length, hold nothing."""
    best: str | None = None
    for name, span in holders:
        others = [s for n, s in holders if n != name]
        nested = all(o[0] <= span[0] and span[1] <= o[1] for o in others)
        shorter = all((span[1] - span[0]) < (o[1] - o[0]) for o in others)
        if nested and shorter:
            if best is not None:
                return None
            best = name
    return best


def citations_held_at(mirror: Path, commit: str, text: str) -> dict[int, str]:
    """For each citation `text` makes, the one clause name that holds it at
    `commit`, keyed by that citation's `offset`. A name holds a citation
    when it opens exactly one construct at `commit`, with the range
    inside that construct or holding it whole. When more than one name
    holds it and the constructs nest, the inner name holds it. Two
    disjoint constructs, or two of equal length, hold nothing. A
    citation whose path, range or earlier anchor does not resolve at
    `commit` holds nothing too, with no raise for that.
    """
    names_in_tree = _tree_names(mirror, commit)
    suffixes = {Path(n).suffix for n in names_in_tree if Path(n).suffix}
    citations = _extract_citations(text, suffixes)
    patterns = _citation_patterns(mirror, commit, names_in_tree)
    lines_of = _lines_reader(mirror, commit, names_in_tree)

    held: dict[int, str] = {}
    for cite in citations:
        if cite.path is None or cite.start < 1 or cite.end < cite.start:
            continue
        lines = lines_of(cite.path)
        if lines is None or cite.end > len(lines):
            continue
        by_name = _name_spans_by_name(cite.names, lines, patterns)
        holders = [
            (name, spans[0])
            for name, spans in by_name.items()
            if len(spans) == 1 and _holds(spans[0], cite.start, cite.end)
        ]
        if len(holders) == 1:
            held[cite.offset] = holders[0][0]
        elif len(holders) > 1:
            name = _sole_holder(holders)
            if name is not None:
                held[cite.offset] = name
    return held


def rewrite_moved_citations(
    text: str, defects: Sequence[CitationDefect], held: Mapping[int, str]
) -> tuple[str, list[Rewrite], list[CitationDefect]]:
    """Move each `defect` whose held name now opens exactly one construct
    onto that construct's range, in `text`, leaving every other character
    as written. A defect with no spans is left as it stands. So is one
    whose held name opens no construct, or more than one, or that `held`
    does not name. Returns the new text, the rewrites made and the
    defects left, both in the order `defects` came in.
    """
    edits: list[tuple[int, int, str, Rewrite]] = []
    left: list[CitationDefect] = []
    for defect in defects:
        name = held.get(defect.offset)
        spans = defect.spans.get(name) if defect.spans and name is not None else None
        if spans is not None and len(spans) == 1 and defect.replace is not None:
            start, end = spans[0]
            new_range = _range(start, end)
            old_start, old_end = defect.replace
            old_range = text[old_start:old_end]
            edits.append(
                (
                    old_start,
                    old_end,
                    new_range,
                    Rewrite(defect.path, old_range, new_range),
                )
            )
        else:
            left.append(defect)
    new_text = text
    for old_start, old_end, new_range, _rewrite in sorted(
        edits, key=lambda e: e[0], reverse=True
    ):
        new_text = new_text[:old_start] + new_range + new_text[old_end:]
    rewrites = [e[3] for e in sorted(edits, key=lambda e: e[0])]
    return new_text, rewrites, left
