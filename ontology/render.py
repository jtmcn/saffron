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


def render_context(text: str, *, vocabulary: Path, _members=None) -> str:
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
        start = text.index(f"**{term}**")
        # First sentence: up to a period followed by whitespace or end of text.
        # Guarded, not asserted: a definition with no sentence end is a real
        # input, and `ty` rejects `.start()` on `Match | None` regardless.
        stop = re.search(r"\.(?:\s|$)", text[start:])
        if stop is None:
            raise ValueError(f"{term}'s definition has no first sentence to rewrite")
        end = stop.start() + start
        sentence = text[start:end]
        first, last = sentence.index("`"), sentence.rindex("`") + 1
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


# Shape name -> ontology class whose members fill its sh:in list.
SHAPE_SETS = {"CoreGateShape": "CoreGate", "GateRoleShape": "GateRole"}
_PER_LINE = 3
_INDENT = " " * 12


def render_shapes(text: str, *, vocabulary: Path, _members=None) -> str:
    """Rewrite each `sh:in ( … )` list from the vocabulary.

    Three terms per line with a twelve-space continuation indent, which is what
    is committed. The `shacl` gate reads this file, so a reflow is a gate diff.
    """
    for shape, class_name in SHAPE_SETS.items():
        # Same rules as `render_context`: a fixture names the sets it is about,
        # and an empty list is looked up by `in` rather than falling through.
        if _members is not None and class_name not in _members:
            continue
        names = (
            _members[class_name]
            if _members is not None
            else members(class_name, vocabulary=vocabulary)
        )
        rows = [
            " ".join(f"saffron:{n}" for n in names[i : i + _PER_LINE])
            for i in range(0, len(names), _PER_LINE)
        ]
        body = f"\n{_INDENT}".join(rows)
        start = text.index(f"saffron:{shape}")
        open_at = text.index("sh:in (", start)
        close_at = text.index(")", open_at)
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
