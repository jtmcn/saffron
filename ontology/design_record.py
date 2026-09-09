"""The design record as a graph, parsed from `DESIGN.md`.

`CONTEXT.md` §11 names the genres Saffron records a decision in. Two of them are
modelled here — a **principle** and the **revision appendix** that contributed it
— because those two have instances a document already carries and a surface that
reads them. `EvidenceRecord` and `SpikeVerdict` are named in §11 and deliberately
absent from the vocabulary: they have no reader yet, and a term with no reader is
what `tests/ontology/test_no_dead_terms.py` deletes.

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
from pathlib import Path

import rdflib

NS = "https://saffron.dev/ns#"
SAFFRON = rdflib.Namespace(NS)

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
    graph.bind("saffron", SAFFRON)
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
            appendix = SAFFRON[f"Appendix{letter}"]
            graph.add((appendix, rdflib.RDF.type, SAFFRON.RevisionAppendix))
            graph.add((appendix, SAFFRON.appendixLetter, rdflib.Literal(letter)))
            for revision in covers.get(letter, []):
                graph.add((appendix, SAFFRON.coversRevision, rdflib.Literal(revision)))
            continue
        if (found := _PRINCIPLE.match(line)) and appendix is not None:
            index = int(found.group(1))
            node = SAFFRON[f"principle-{index}"]
            graph.add((node, rdflib.RDF.type, SAFFRON.Principle))
            graph.add((node, SAFFRON.principleNumber, rdflib.Literal(index)))
            graph.add((node, SAFFRON.claim, rdflib.Literal(_claim(lines, number))))
            graph.add((node, SAFFRON.contributedBy, appendix))
    return graph


def principles(graph: rdflib.Graph) -> list[tuple[int, str, str]]:
    """(number, claim, appendix letter), in number order."""
    rows = []
    for node in graph.subjects(rdflib.RDF.type, SAFFRON.Principle):
        number = graph.value(node, SAFFRON.principleNumber)
        claim = graph.value(node, SAFFRON.claim)
        appendix = graph.value(node, SAFFRON.contributedBy)
        letter = (
            None if appendix is None else graph.value(appendix, SAFFRON.appendixLetter)
        )
        # Raised rather than ignored: `PrincipleShape` says these are mandatory,
        # but a shape validates a graph someone remembered to validate, and this
        # renderer writes the file every spec cites.
        if number is None or claim is None or letter is None:
            raise ValueError(f"{node}: missing a number, a claim, or an appendix")
        rows.append((int(str(number)), str(claim), str(letter)))
    return sorted(rows)


ANCHOR = "## Principles — an index"
_HEADER = "| # | The claim | From |\n|---|---|---|\n"


def render_principles(text: str) -> str:
    """Rewrite the principle index's table body from `DESIGN.md`'s own appendices.

    The span is the run of table rows after the header, which is why the header
    is emitted rather than matched: a table whose header drifted would otherwise
    have its rows appended below the old ones.
    """
    rows = principles(parse(text))
    if not rows:
        raise ValueError("the design record parsed to no principles")
    if text.count(ANCHOR) != 1:
        raise ValueError(f"{ANCHOR}: expected exactly one occurrence")

    body = "".join(f"| {n} | {claim} | {letter} |\n" for n, claim, letter in rows)
    start = text.index(_HEADER, text.index(ANCHOR))
    end = start + len(_HEADER)
    while end < len(text) and text[end] == "|":
        end = text.index("\n", end) + 1
    # Confirm what is being replaced is a table body before overwriting prose in
    # the document every spec cites.
    replaced = text[start + len(_HEADER) : end]
    if replaced and not all(ln.startswith("| ") for ln in replaced.splitlines()):
        raise ValueError("the span after the principle header is not a table body")
    return text[:start] + _HEADER + body + text[end:]


def main() -> None:  # pragma: no cover - exercised through `ontology.render`
    design = Path(__file__).resolve().parents[1] / "DESIGN.md"
    design.write_text(render_principles(design.read_text()))


if __name__ == "__main__":  # pragma: no cover
    main()
