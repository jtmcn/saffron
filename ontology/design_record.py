"""The design record as a graph, parsed from the appendix records.

`CONTEXT.md` §11 names the genres the factory records a decision in. Two are
modelled here: a **principle**, and the **revision appendix** that contributed
it, read from `docs/appendices/`. `EvidenceRecord` and `SpikeVerdict` are
deliberately absent: they have no reader yet.

**The appendix records are authoritative.** This module reads them and renders
two indexes into `DESIGN.md` from them, the opposite direction from `render.py`'s
vocabulary renders. Dev-only and outside `saffron/`: nothing there imports a
graph library.
"""

import re
from pathlib import Path

import rdflib

from ontology.spans import (
    APPENDIX_HEADER,
    PRINCIPLE_ANCHOR,
    PRINCIPLE_HEADER,
    appendix_index,
    principle_index,
)
from records.kinds import KINDS, Appendix
from records.load import Record, load

NS = "urn:software-factory:ns#"
FACTORY = rdflib.Namespace(NS)

# An appendix heading at any level or spacing. Nothing reads one in `DESIGN.md`
# any more, so the guard test uses this to refuse one written there.
APPENDIX_OPENS = re.compile(r"^#{2,}\s*Appendix\b")
# A principle opens a line and its claim is the bolded lead. Three wrap before
# the closing `**`, so the claim is read to that marker rather than to the end.
_PRINCIPLE = re.compile(r"^(\d+)\. \*\*")
# Most titles state a rev, so the hand-written `revisions` has a second reading.
_TITLE_REVISION = re.compile(r"\brev (\d+)\b")


def appendices(root: Path) -> list[Record]:
    return load(KINDS["appendix"], root)


def _appendix(record: Record) -> Appendix:
    if not isinstance(record.model, Appendix):
        raise TypeError(f"{record.path}: not an appendix record")
    return record.model


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


def parse(records: list[Record]) -> rdflib.Graph:
    """Every principle and revision appendix the appendix records declare."""
    graph = rdflib.Graph()
    graph.bind("factory", FACTORY)
    for record in records:
        m = _appendix(record)
        stated = _TITLE_REVISION.search(m.title)
        if stated and int(stated.group(1)) not in m.revisions:
            raise ValueError(
                f"Appendix {m.id}: the title says rev {stated.group(1)}, "
                f"revisions says {m.revisions}"
            )
        appendix = FACTORY[f"Appendix{m.id}"]
        graph.add((appendix, rdflib.RDF.type, FACTORY.RevisionAppendix))
        graph.add((appendix, FACTORY.appendixLetter, rdflib.Literal(m.id)))
        for revision in m.revisions:
            graph.add((appendix, FACTORY.coversRevision, rdflib.Literal(revision)))
        lines = record.body.splitlines()
        for number, line in enumerate(lines):
            if found := _PRINCIPLE.match(line):
                node = FACTORY[f"principle-{found.group(1)}"]
                graph.add((node, rdflib.RDF.type, FACTORY.Principle))
                graph.add(
                    (node, FACTORY.principleNumber, rdflib.Literal(int(found.group(1))))
                )
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


ANCHOR = PRINCIPLE_ANCHOR
_HEADER = PRINCIPLE_HEADER


def render_principles(text: str, graph: rdflib.Graph) -> str:
    """Rewrite the principle index's table body from the appendix records.

    The header locates the span and is re-emitted rather than left in place, so
    a drifted one is refused by name below. Matching it loosely instead would
    append the new rows underneath the old ones.
    """
    rows = principles(graph)
    if not rows:
        raise ValueError("the design record parsed to no principles")
    body = "".join(
        f"| {n} | {_escaped(claim)} | {letter} |\n" for n, claim, letter in rows
    )
    start, end = principle_index(text)
    # Confirm what is being replaced is a table body before overwriting prose in
    # the document every spec cites.
    replaced = text[start + len(_HEADER) : end]
    if replaced and not all(ln.startswith("| ") for ln in replaced.splitlines()):
        raise ValueError("the span after the principle header is not a table body")
    return text[:start] + _HEADER + body + text[end:]


def _principle_cell(numbers: list[int]) -> str:
    if not numbers:
        return ""
    lo, hi = min(numbers), max(numbers)
    return str(lo) if lo == hi else f"{lo}–{hi}"


def render_appendix_index(text: str, records: list[Record], graph: rdflib.Graph) -> str:
    """Rewrite the appendix index's table body from the appendix records."""
    blocks: dict[str, list[int]] = {}
    for number, _, letter in principles(graph):
        blocks.setdefault(letter, []).append(number)
    body = ""
    for record in records:
        m = _appendix(record)
        revisions = ", ".join(str(n) for n in m.revisions)
        cell = _principle_cell(blocks.get(m.id, []))
        body += f"| **{m.id}** | {revisions} | {_escaped(m.question)} | {cell} |\n"
    start, end = appendix_index(text)
    replaced = text[start + len(APPENDIX_HEADER) : end]
    if replaced and not all(ln.startswith("| ") for ln in replaced.splitlines()):
        raise ValueError("the span after the appendix header is not a table body")
    return text[:start] + APPENDIX_HEADER + body + text[end:]
