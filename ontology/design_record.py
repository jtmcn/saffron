"""The design record as a graph, parsed from `DESIGN.md`.

`CONTEXT.md` §11 names the genres the factory records a decision in. Two of them are
modelled here — a **principle** and the **revision appendix** that contributed it
— because those two have instances a document already carries and a surface that
reads them. `EvidenceRecord` and `SpikeVerdict` are named in `CONTEXT.md` §11 and
deliberately absent from the vocabulary: they have no reader yet, and a term with
no reader is what `tests/ontology/test_no_dead_terms.py` deletes.

**`DESIGN.md` stays authoritative.** The prose is not stored in the vocabulary and
is never written back to; this module reads it and renders one index from it. That
is the opposite direction from `render.py`, where the vocabulary is authoritative
and `CONTEXT.md` is its render, and the asymmetry is the point: a closed set is a
decision the vocabulary owns, while a principle is prose an appendix owns.

Dev-only and outside `saffron/`, for `render.py`'s reason: `pyproject.toml` says
nothing under `saffron/` imports a graph library.
"""

from __future__ import annotations

import re

import rdflib

NS = "urn:software-factory:ns#"
FACTORY = rdflib.Namespace(NS)

# The two halves of "an appendix heading", and the *only* definitions of them:
# `tests/test_citations.py` imports these rather than keeping its own copy. They
# diverged once — a hyphen for the em dash matched `OPENS` and not `APPENDIX`,
# and the loop carried the previous letter forward and credited it that
# appendix's principles.
APPENDIX = re.compile(r"^## Appendix ([A-Z]) — .*$")
# Deliberately looser than the heading level and spacing `APPENDIX` accepts: what
# it is for is catching a heading this file cannot read, so it must reach further
# than the reader, not the same distance.
APPENDIX_OPENS = re.compile(r"^#{2,}\s*Appendix\b")
# A principle opens a line and its claim is the bolded lead. Three wrap before
# the closing `**`, so the claim is read to that marker rather than to the end
# of the line.
_PRINCIPLE = re.compile(r"^(\d+)\. \*\*")
# The `Rev` column of the appendix index, which carries what a heading cannot:
# Appendix G covers rev 8 and rev 10, and rev 10 appears in no title.
_INDEX_ROW = re.compile(r"^\| \*\*([A-Z])\*\* \| ([0-9, ]+) \|")
# Every appendix title states a rev, so the hand-written `Rev` cell above has
# a second reading to agree with. It is the row that carries the extra ones.
_HEADING_REVISION = re.compile(r"\brev (\d+)\b")


def _claim(lines: list[str], start: int) -> str:
    """The bolded claim opening a principle, joined across the lines it wraps."""
    text = lines[start]
    while "**" not in text[text.index("**") + 2 :]:
        start += 1
        if start >= len(lines):
            raise ValueError(f"unterminated principle claim: {text[:60]}")
        text += " " + lines[start].strip()
    body = text[text.index("**") + 2 :]
    claim = body[: body.index("**")].strip()
    # Trailing punctuation belongs to the sentence, not the claim, and the
    # committed principles are inconsistent about it.
    return claim.rstrip(".")


def parse(design: str) -> rdflib.Graph:
    """Every principle and revision appendix `DESIGN.md` declares."""
    graph = rdflib.Graph()
    graph.bind("factory", FACTORY)
    lines = design.splitlines()

    covers: dict[str, list[int]] = {}
    for line in lines:
        if row := _INDEX_ROW.match(line):
            covers[row.group(1)] = [
                int(n) for n in row.group(2).replace(" ", "").split(",")
            ]

    appendix: rdflib.URIRef | None = None
    for number, line in enumerate(lines):
        if APPENDIX_OPENS.match(line) and not APPENDIX.match(line):
            raise ValueError(f"{line!r}: an appendix heading this cannot read")
        if found := APPENDIX.match(line):
            letter = found.group(1)
            appendix = FACTORY[f"Appendix{letter}"]
            revisions = covers.get(letter, [])
            stated = _HEADING_REVISION.search(line)
            # A row with no letter is `RevisionAppendixShape`'s to refuse; this
            # catches the typo'd cell, which is well-formed and wrong.
            if stated and revisions and int(stated.group(1)) not in revisions:
                raise ValueError(
                    f"Appendix {letter}: the heading says rev {stated.group(1)}, "
                    f"the index row says {revisions}"
                )
            graph.add((appendix, rdflib.RDF.type, FACTORY.RevisionAppendix))
            graph.add((appendix, FACTORY.appendixLetter, rdflib.Literal(letter)))
            for revision in revisions:
                graph.add((appendix, FACTORY.coversRevision, rdflib.Literal(revision)))
            continue
        if (found := _PRINCIPLE.match(line)) and appendix is not None:
            index = int(found.group(1))
            node = FACTORY[f"principle-{index}"]
            graph.add((node, rdflib.RDF.type, FACTORY.Principle))
            graph.add((node, FACTORY.principleNumber, rdflib.Literal(index)))
            graph.add((node, FACTORY.claim, rdflib.Literal(_claim(lines, number))))
            graph.add((node, FACTORY.contributedBy, appendix))
    return graph


def _one(graph: rdflib.Graph, node: rdflib.term.Node, of: rdflib.URIRef) -> str:
    """The single value of a property `PrincipleShape` says occurs exactly once.

    Raised rather than ignored: a shape validates a graph someone remembered to
    validate, and this renderer writes the file every spec cites. Two values is
    the likelier direction — `_PRINCIPLE` reads any numbered list inside an
    appendix whose first item opens bold — and `graph.value` would pick one.
    """
    found = list(graph.objects(node, of))
    if len(found) != 1:
        raise ValueError(f"{node}: {len(found)} values for {of}, expected exactly 1")
    return str(found[0])


def principles(graph: rdflib.Graph) -> list[tuple[int, str, str]]:
    """(number, claim, appendix letter), in number order."""
    rows = []
    for node in graph.subjects(rdflib.RDF.type, FACTORY.Principle):
        number = _one(graph, node, FACTORY.principleNumber)
        claim = _one(graph, node, FACTORY.claim)
        appendix = _one(graph, node, FACTORY.contributedBy)
        letter = _one(graph, rdflib.URIRef(appendix), FACTORY.appendixLetter)
        rows.append((int(number), claim, letter))
    return sorted(rows)


def _escaped(claim: str) -> str:
    """A `|` inside a claim closes its cell early, and the currency test compares
    render to render — it would stay green over a table that had lost a column."""
    return claim.replace("|", r"\|")


ANCHOR = "## Principles — an index"
_HEADER = "| # | The claim | From |\n|---|---|---|\n"


def render_principles(text: str) -> str:
    """Rewrite the principle index's table body from `DESIGN.md`'s own appendices.

    The header locates the span and is re-emitted rather than left in place, so
    a drifted one is refused by name below. Matching it loosely instead would
    append the new rows underneath the old ones.
    """
    rows = principles(parse(text))
    if not rows:
        raise ValueError("the design record parsed to no principles")
    if text.count(ANCHOR) != 1:
        raise ValueError(f"{ANCHOR}: expected exactly one occurrence")

    body = "".join(
        f"| {n} | {_escaped(claim)} | {letter} |\n" for n, claim, letter in rows
    )
    start = text.find(_HEADER, text.index(ANCHOR))
    if start == -1:
        raise ValueError(f"{ANCHOR}: no `{_HEADER.splitlines()[0]}` header under it")
    end = start + len(_HEADER)
    while end < len(text) and text[end] == "|":
        end = text.index("\n", end) + 1
    # Confirm what is being replaced is a table body before overwriting prose in
    # the document every spec cites.
    replaced = text[start + len(_HEADER) : end]
    if replaced and not all(ln.startswith("| ") for ln in replaced.splitlines()):
        raise ValueError("the span after the principle header is not a table body")
    return text[:start] + _HEADER + body + text[end:]
