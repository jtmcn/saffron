#!/usr/bin/env python3
"""The `retired-vocabulary` pre-commit hook, reading the file rather than the line.

`pygrep` (the previous engine here) matches one line at a time, and every prose
file this hook covers is hard-wrapped, so a retired two-word term that happens
to straddle a line break was invisible to it (docs/BACKLOG.md item 57). This
script reads each file whole, joins the whitespace a line wrap introduced back
into the shape the pattern already recognises on one line, and then runs the
pattern unchanged.

`RETIRED_TERMS` is a list on purpose, so a second retired term has somewhere to
go without anyone having to teach a separator class or a word boundary a
newline case. Which words are retired is CONTEXT.md's decision, not this
script's, and none are added here.

Run as a `language: system` local hook: prek passes the changed filenames as
argv, and a non-zero exit fails the commit.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

# One retired term today: the verb/noun pair CONTEXT.md's "_Avoid_" note under
# "run" and "batch" settles. `[ -]` covers both separator forms that were live
# on one line before this script existed, and `\b` after `runs?` is what keeps
# a near miss like "gate-runner" out (the boundary fails on the trailing "ner").
RETIRED_TERMS = [
    re.compile(r"(?i)gate[ -]runs?\b"),
]

# A maximal run of horizontal-or-vertical whitespace. Whether it joins, or
# stays as a paragraph break, is decided per-run in `normalize` below.
_WHITESPACE_RUN = re.compile(r"[ \t\r\n]+")


def normalize(text: str) -> tuple[str, list[int]]:
    """Join line-wrapped whitespace the way a reader would, leaving paragraph
    breaks alone.

    A whitespace run containing exactly one line break collapses: to nothing
    when the character immediately before it is a hyphen (so a hyphenated
    wrap joins with no inserted space, matching the pattern's hyphen
    separator rather than a hyphen-then-space that no separator class
    matches), otherwise to a single space (matching the pattern's space
    separator). A run containing two or more line breaks — a blank line, or
    more — is copied through unchanged, so a paragraph break never joins the
    words on either side of it into a false hit.

    Returns `(normalized_text, line_of)` where `line_of[i]` is the 1-based
    line number, in the *original* text, that character `i` of
    `normalized_text` came from. A retired term's regex always starts on a
    literal word character copied straight through (never on whitespace this
    function inserts or drops), so `line_of[match.start()]` is always the
    line the hit actually starts on.
    """
    out: list[str] = []
    line_of: list[int] = []
    line = 1
    pos = 0
    length = len(text)
    while pos < length:
        match = _WHITESPACE_RUN.match(text, pos)
        if match is None:
            ch = text[pos]
            out.append(ch)
            line_of.append(line)
            pos += 1
            continue
        run = match.group(0)
        newlines = run.count("\n")
        if newlines == 0:
            # Plain horizontal whitespace: not a wrap, copy through.
            out.append(run)
            line_of.extend([line] * len(run))
        elif newlines == 1:
            hyphen_before = bool(out) and out[-1] == "-"
            if not hyphen_before:
                out.append(" ")
                line_of.append(line)
            # else: drop the whole run, joining the hyphen to the next line's
            # first character with nothing between them.
            line += 1
        else:
            # A blank line (or more): a paragraph break, not a wrap. Leave it.
            out.append(run)
            for ch in run:
                line_of.append(line)
                if ch == "\n":
                    line += 1
        pos = match.end()
    return "".join(out), line_of


def find_hits(text: str) -> list[int]:
    """The 1-based original line numbers a retired term starts on in `text`."""
    normalized, line_of = normalize(text)
    lines = set()
    for pattern in RETIRED_TERMS:
        for match in pattern.finditer(normalized):
            lines.add(line_of[match.start()])
    return sorted(lines)


@dataclass(frozen=True)
class Hit:
    path: Path
    line: int


def check_file(path: str | Path) -> list[Hit]:
    """Every retired-term hit in `path`, read whole rather than line by line.

    Approximates prek's `types: [text]` filter — a file containing a NUL byte,
    or that does not decode as UTF-8, is treated as having no hits rather than
    raising, the same way a non-text file is simply never handed to a pygrep
    hook.
    """
    path = Path(path)
    try:
        raw = path.read_bytes()
    except OSError:
        return []
    if b"\x00" in raw:
        return []
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return []
    return [Hit(path=path, line=line) for line in find_hits(text)]


def main(argv: list[str]) -> int:
    hits: list[Hit] = []
    for name in argv:
        hits.extend(check_file(name))
    for hit in hits:
        print(
            f"{hit.path}:{hit.line}: retired vocabulary term found (line-break spans do not exempt it)"
        )
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
