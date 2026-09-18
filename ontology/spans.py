"""Where `ontology.render` writes, located without a graph library.

`.saffron/gates/prose.py` exempts these spans and runs under a cell's plain
`python3`, so this module imports only the standard library.
"""

from __future__ import annotations

import re

# The only definition of a member, shared by `render` and the CONTEXT.md
# cross-check so the write span cannot exceed the read span.
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


APPENDIX_ANCHOR = "## Appendices — an index"
APPENDIX_HEADER = (
    "| App. | Rev | The question it settles | Principles |\n|---|---|---|---|\n"
)


def _table(text: str, anchor: str, header: str) -> tuple[int, int]:
    """`(start, end)` of the table under `anchor`, its header included."""
    if text.count(anchor) != 1:
        raise ValueError(f"{anchor}: expected exactly one occurrence")
    start = text.find(header, text.index(anchor))
    if start == -1:
        raise ValueError(f"{anchor}: no `{header.splitlines()[0]}` header under it")
    end = start + len(header)
    while end < len(text) and text[end] == "|":
        end = text.index("\n", end) + 1
    return start, end


def principle_index(text: str) -> tuple[int, int]:
    """`(start, end)` of the principle index table, its header included."""
    return _table(text, PRINCIPLE_ANCHOR, PRINCIPLE_HEADER)


def appendix_index(text: str) -> tuple[int, int]:
    """`(start, end)` of the appendix index table, its header included."""
    return _table(text, APPENDIX_ANCHOR, APPENDIX_HEADER)
