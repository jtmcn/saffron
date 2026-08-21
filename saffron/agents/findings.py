"""Critic findings, reconciled against the diff (DESIGN.md §5.5).

A finding is a claim, not a record — the same move as measuring doneness from
git (§4.3). Before a finding counts, the host checks it points at real code with
a real connection to this change. Unanchorable findings are kept with
`anchored = False`, never deleted: the drop rate per lens is the signal that a
lens is badly prompted.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

Severity = Literal["blocker", "concern", "note"]

_HUNK = re.compile(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_WORD = re.compile(r"\w+")


class Finding(BaseModel):
    """One finding from one lens — the `findings` row the critic produces (§4.1).

    `severity` is three levels because `note` must be excludable from the concern
    count that sorts the morning queue (§5.5).
    """

    lens: str
    severity: Severity
    file: str
    line: int
    claim: str
    anchored: bool = False


@dataclass(frozen=True)
class DiffFacts:
    """The host-computed fact set a finding is reconciled against."""

    hunk_lines: dict[str, set[int]]
    """New-file line numbers covered by a hunk, per new-file path."""

    tokens: frozenset[str]
    """Word-boundary tokens of every added, removed or renamed line. Crude by
    specification (§5.5) — no language knowledge, so keywords and digits are in
    here too. That over-admits, which is the safe direction: an over-admitted
    finding is visible in the queue, a wrongly dropped one is invisible."""


def parse_diff(diff: str) -> DiffFacts:
    """Parse unified `git diff` output into the two facts anchoring needs."""
    lines = diff.splitlines()
    hunk_lines: dict[str, set[int]] = {}
    tokens: set[str] = set()
    path = ""
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if line.startswith("+++ "):
            # ponytail: paths git quotes (spaces, non-ASCII) are left as-is —
            # they match no finding, so they drop rather than crash.
            path = line[4:].removeprefix("b/")
        elif line.startswith(("rename from ", "rename to ")):
            # A pure rename has no ± line, but the path itself is an identifier
            # a caller still names — the diff "renamed" it (§5.5).
            tokens.update(_WORD.findall(line.split(" ", 2)[2]))
        elif header := _HUNK.match(line):
            start, count = int(header.group(2)), int(header.group(3) or 1)
            if count:  # zero for a deleted file and for a deletion-only hunk
                hunk_lines.setdefault(path, set()).update(range(start, start + count))
            index = _consume_hunk(
                lines, index, int(header.group(1) or 1), count, tokens
            )
    return DiffFacts(hunk_lines, frozenset(tokens))


def _consume_hunk(
    lines: list[str], index: int, old_left: int, new_left: int, tokens: set[str]
) -> int:
    """Walk one hunk body by its declared counts, collecting changed-line tokens.

    Counted rather than scanned for the next `@@`, so the walk stops where the
    hunk stops: a patch file's preamble and its `-- \\n<version>` epilogue are
    not hunk body, and only the counts say so.
    """
    while index < len(lines) and (old_left > 0 or new_left > 0):
        body = lines[index]
        index += 1
        if body.startswith("\\"):
            # "\ No newline at end of file" annotates the line above and belongs
            # to neither side's count. git emits it constantly (Appendix K).
            continue
        if body.startswith("+"):
            new_left -= 1
        elif body.startswith("-"):
            old_left -= 1
        else:  # context: " ", or "" where a blank line lost its marker
            old_left -= 1
            new_left -= 1
            continue
        tokens.update(_WORD.findall(body[1:]))
    return index


def anchor(
    findings: list[Finding],
    diff: str,
    *,
    read_head: Callable[[str], str | None],
) -> list[Finding]:
    """Reconcile findings against the diff, returning every one of them (§5.5).

    `read_head` returns a file's content at head, or None if there is no such
    file — a callback because the cited line is usually *outside* the diff, so
    the content cannot come from the diff, and REVIEW runs after the cell is torn
    down, so it cannot come from a container either. The host worktree, a
    `git show head:path`, or a dict in a test all satisfy it.
    """
    facts = parse_diff(diff)
    return [
        finding.model_copy(update={"anchored": _is_anchored(finding, facts, read_head)})
        for finding in findings
    ]


def _is_anchored(
    finding: Finding, facts: DiffFacts, read_head: Callable[[str], str | None]
) -> bool:
    if finding.line in facts.hunk_lines.get(finding.file, ()):
        return True
    # The second target is not a nicety: the blast-radius lens is asked what else
    # calls this, so its best findings cite lines the diff never touched. A
    # hunk-only rule zeroes that lens out silently (§5.5, principle 28).
    content = read_head(finding.file)
    if content is None:
        return False
    lines = content.splitlines()
    if not 1 <= finding.line <= len(lines):
        return False
    return bool(facts.tokens & set(_WORD.findall(lines[finding.line - 1])))
