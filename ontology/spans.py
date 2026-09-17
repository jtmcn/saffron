"""Where `ontology.render` writes, located without a graph library.

`.saffron/gates/prose.py` exempts these spans and runs under a cell's plain
`python3`, so this module imports only the standard library.
"""

from __future__ import annotations

import re

# What counts as a member, and the only definition of it: `render` and the
# CONTEXT.md cross-check both import it, so the write span cannot exceed the
# read span. It rejects a token carrying a `.` or a `/`.
MEMBER_TOKEN = re.compile(r"`([A-Za-z_][A-Za-z0-9_-]*)`")

# CONTEXT.md bold term -> (ontology class, join style). The join styles are the
# ones already committed; a generator that normalised them would rewrite prose
# it does not own.
SETS = {
    "Terminal state": ("TerminalState", "comma"),
    "Batch stop reason": ("BatchStopReason", "or-comma"),
    "Severity": ("Severity", "or-comma"),
    "Risk tier": ("RiskTier", "or-plain"),
    "Gate role": ("GateRole", "comma"),
    "Core gates": ("CoreGate", "comma"),
}

PRINCIPLE_ANCHOR = "## Principles — an index"
PRINCIPLE_HEADER = "| # | The claim | From |\n|---|---|---|\n"


def definition_sentence(text: str, term: str) -> tuple[int, int]:
    """`(start, end)` of `**term**`'s first sentence, the span `render_context` rewrites within."""
    count = text.count(f"**{term}**")
    if count != 1:
        raise ValueError(f"{term}: expected exactly one definition, found {count}")
    start = text.index(f"**{term}**")
    # Bounded at the definition's own blank line. Unbounded, a definition
    # without a trailing period matched a period paragraphs away.
    block_end = text.find("\n\n", start)
    if block_end == -1:
        block_end = len(text)
    stop = re.search(r"\.(?:\s|$)", text[start:block_end])
    if stop is None:
        raise ValueError(f"{term}'s definition has no first sentence to rewrite")
    return start, start + stop.start()


def principle_index(text: str) -> tuple[int, int]:
    """`(start, end)` of the principle index table, its header included."""
    if text.count(PRINCIPLE_ANCHOR) != 1:
        raise ValueError(f"{PRINCIPLE_ANCHOR}: expected exactly one occurrence")
    start = text.find(PRINCIPLE_HEADER, text.index(PRINCIPLE_ANCHOR))
    if start == -1:
        header = PRINCIPLE_HEADER.splitlines()[0]
        raise ValueError(f"{PRINCIPLE_ANCHOR}: no `{header}` header under it")
    end = start + len(PRINCIPLE_HEADER)
    while end < len(text) and text[end] == "|":
        end = text.index("\n", end) + 1
    return start, end
