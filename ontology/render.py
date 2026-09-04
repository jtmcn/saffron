"""Renders the surfaces derived from `ontology/saffron.ttl`.

Dev-only and deliberately outside `saffron/`: `pyproject.toml` states that
nothing under `saffron/` imports a graph library, and this module imports two.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

import rdflib

NS = "https://saffron.dev/ns#"

# What counts as a member, and the *only* definition of it: the cross-check in
# `test_vocabulary_agrees_with_context` imports this rather than keeping its own
# copy, so "the write span cannot exceed the read span" holds by construction.
# It rejects a token carrying a `.` or a `/`, which is why locating the span
# from raw backticks let `` `DESIGN.md` `` start it and swallow the prose after.
MEMBER_TOKEN = re.compile(r"`([A-Za-z_][A-Za-z0-9_-]*)`")


def members(class_name: str, *, vocabulary: Path) -> list[str]:
    """Local names of every instance of `saffron:<class_name>`, in the order
    they first appear in the vocabulary's own text.

    Source order, not graph order: rdflib iterates unordered, and the committed
    enumerations are in an order a reader chose. Sorting would rewrite them.
    """
    text = vocabulary.read_text()
    graph = rdflib.Graph().parse(vocabulary, format="turtle")
    names = [
        str(s).removeprefix(NS)
        for s in graph.subjects(rdflib.RDF.type, rdflib.URIRef(f"{NS}{class_name}"))
    ]

    def first_offset(name: str) -> int:
        found = re.search(rf"saffron:{re.escape(name)}\b", text)
        return found.start() if found else len(text)

    return sorted(names, key=first_offset)


# Measured, not chosen: greedy-wrapping the five spans reproduces the committed
# bytes at 82, 83 and 84 and at no other width (76-92 searched).
_WIDTH = 83

# CONTEXT.md bold term -> (ontology class, join style). The join styles are the
# ones already committed; a generator that normalised them would rewrite prose
# it does not own.
SETS = {
    "Terminal state": ("TerminalState", "comma"),
    "Severity": ("Severity", "or-comma"),
    "Risk tier": ("RiskTier", "or-plain"),
    "Gate role": ("GateRole", "comma"),
    "Core gates": ("CoreGate", "comma"),
}


def _join(names: list[str], style: str) -> str:
    # A closed set that renders to nothing is a generator bug, not an output:
    # `**Terminal state**: A state that reaches the operator — .` would pass
    # every assertion below and be silently wrong.
    if not names:
        raise ValueError("a closed set rendered to no members")
    ticked = [f"`{n}`" for n in names]
    if len(ticked) == 1:
        return ticked[0]
    if style == "comma":
        return ", ".join(ticked)
    if style == "or-comma":
        return ", ".join(ticked[:-1]) + f", or {ticked[-1]}"
    if style == "or-plain":
        return " or ".join(ticked)
    raise ValueError(f"unknown join style: {style}")


def _continuation_indent(text: str, span_start: int, span_end: int) -> str:
    """The indent the committed continuation lines carry. A span that already
    wraps shows it directly; one that does not inherits its own line's indent."""
    newline = text.find("\n", span_start, span_end)
    at = newline + 1 if newline != -1 else text.rfind("\n", 0, span_start) + 1
    # Sliced rather than `re.match(...).group()`: that match is `Match | None` to
    # `ty`, and the blocking `types` gate does not take "this pattern always
    # matches" for an answer.
    rest = text[at:]
    return rest[: len(rest) - len(rest.lstrip(" \t"))]


def render_context(
    text: str, *, vocabulary: Path, _members: dict[str, list[str]] | None = None
) -> str:
    """Rewrite each closed set's backticked span in place.

    The span is first-backtick to last-backtick within the definition's first
    sentence — the same span `context_enumeration` reads. Everything outside it,
    including the em dash, the connective prose and the sentences after, is
    left exactly as committed.

    Three of the five sets wrap across source lines, so the rewritten span is
    re-wrapped at the committed width and continuation indent. Emitting it on
    one line reproduces the members correctly and the bytes wrongly.
    """
    for term, (class_name, style) in SETS.items():
        # A fixture that supplies `_members` names the sets it is about; the
        # others are not in its text and indexing for them would raise.
        if _members is not None and class_name not in _members:
            continue
        # `in`, not `or`: an empty member list is falsy, and falling through to
        # the real vocabulary would make an empty-set fixture silently pass.
        # `_members` is keyed by ontology class in both renderers, never by the
        # CONTEXT.md term — one key space, so a test reads the same either side.
        names = (
            _members[class_name]
            if _members is not None
            else members(class_name, vocabulary=vocabulary)
        )
        if text.count(f"**{term}**") != 1:
            raise ValueError(
                f"{term}: expected exactly one definition, found "
                f"{text.count(f'**{term}**')}"
            )
        start = text.index(f"**{term}**")
        # Bounded at the definition's own blank line. Unbounded, a definition
        # left without a trailing period matched a period paragraphs away and
        # `main()` deleted everything between — and `main()` is what the
        # currency test tells the operator to run.
        block_end = text.find("\n\n", start)
        if block_end == -1:
            block_end = len(text)
        # First sentence: up to a period followed by whitespace or end of text.
        # Guarded, not asserted: a definition with no sentence end is a real
        # input, and `ty` rejects `.start()` on `Match | None` regardless.
        stop = re.search(r"\.(?:\s|$)", text[start:block_end])
        if stop is None:
            raise ValueError(f"{term}'s definition has no first sentence to rewrite")
        end = stop.start() + start
        sentence = text[start:end]
        # From the tokens the reader accepts, never from raw backticks.
        found = list(MEMBER_TOKEN.finditer(sentence))
        if not found:
            raise ValueError(f"{term}: no backticked members to rewrite")
        first, last = found[0].start(), found[-1].end()
        # Prose before the list is now safe; a rejected token *between* two
        # members is still inside the span, so refuse rather than overwrite it.
        if sentence.count("`", first, last) != 2 * len(found):
            raise ValueError(f"{term}: a backticked non-member sits inside the span")
        # `rfind`, not `rindex`: a one-line fixture has no preceding newline.
        column = start + first - (text.rfind("\n", 0, start + first) + 1)
        indent = _continuation_indent(text, start + first, start + last)
        body = textwrap.fill(
            _join(names, style),
            width=_WIDTH,
            initial_indent=" " * column,
            subsequent_indent=indent,
            break_long_words=False,
            break_on_hyphens=False,
        )[column:]
        text = text[:start] + sentence[:first] + body + sentence[last:] + text[end:]
    return text


# Anchor in saffron-shapes.ttl -> the ontology class whose members fill the
# first `sh:in ( … )` after it. Anchored on text, not on a shape name, because
# two of these lists are nested inside `sh:property [ … ]` blocks and
# `TaskShape`'s own first `sh:in` is endedInState — a superset of the terminal
# states, hand-maintained, which a shape-name anchor would have rewritten.
SHAPE_SETS = {
    "saffron:CoreGateShape": "CoreGate",
    "saffron:GateRoleShape": "GateRole",
    "saffron:TerminalStateShape": "TerminalState",
    "sh:path saffron:riskTier": "RiskTier",
    "sh:path saffron:severity": "Severity",
}
_PER_LINE = 3
_INDENT = " " * 12


def render_shapes(
    text: str, *, vocabulary: Path, _members: dict[str, list[str]] | None = None
) -> str:
    """Rewrite each `sh:in ( … )` list from the vocabulary.

    Three terms per line with a twelve-space continuation indent, which is what
    is committed. The `shacl` gate reads this file, so a reflow is a gate diff.
    """
    for anchor, class_name in SHAPE_SETS.items():
        # Same rules as `render_context`: a fixture names the sets it is about,
        # and an empty list is looked up by `in` rather than falling through.
        if _members is not None and class_name not in _members:
            continue
        names = (
            _members[class_name]
            if _members is not None
            else members(class_name, vocabulary=vocabulary)
        )
        # `_join` guards the CONTEXT.md path; this one emitted `sh:in (  )`,
        # which parses as rdf:nil — a constraint nothing can satisfy.
        if not names:
            raise ValueError(f"{anchor}: a closed set rendered to no members")
        rows = [
            " ".join(f"saffron:{n}" for n in names[i : i + _PER_LINE])
            for i in range(0, len(names), _PER_LINE)
        ]
        body = f"\n{_INDENT}".join(rows)
        if text.count(anchor) != 1:
            raise ValueError(f"{anchor}: expected exactly one occurrence")
        start = text.index(anchor)
        open_at = text.index("sh:in (", start)
        close_at = text.index(")", open_at)
        # The anchors are text, so confirm what is being replaced is a list of
        # `saffron:` IRIs before overwriting it in a file a blocking gate reads.
        replaced = text[open_at + len("sh:in (") : close_at].split()
        if not replaced or any(not w.startswith("saffron:") for w in replaced):
            raise ValueError(f"{anchor}: the list after it is not saffron: IRIs")
        text = text[:open_at] + f"sh:in ( {body} " + text[close_at:]
    return text


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    vocabulary = root / "ontology" / "saffron.ttl"
    for path, fn in (
        (root / "CONTEXT.md", render_context),
        (root / "ontology" / "shapes" / "saffron-shapes.ttl", render_shapes),
    ):
        path.write_text(fn(path.read_text(), vocabulary=vocabulary))


if __name__ == "__main__":
    main()
