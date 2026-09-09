"""`DESIGN.md`'s own principles, as a graph, and the index rendered back from it.

The drift this exists to catch is the one `docs/agents/domain.md` names and a grep
cannot decide: *a stale list has no string to match*. An index maintained by hand
goes wrong the first time someone adds a principle and stops at the appendix — and
nothing would say so, because both documents still parse.

So the index is generated, and these tests hold the two things generation does not:
that the graph it renders from is well-formed, and that what is committed equals
what the appendices currently say.
"""

from __future__ import annotations

import pytest
import rdflib
from ontology_paths import ONTOLOGY, SHAPES, VOCABULARY
from pyshacl import validate

from ontology import design_record

DESIGN = ONTOLOGY.parent / "DESIGN.md"


def _graph() -> rdflib.Graph:
    return design_record.parse(DESIGN.read_text())


def _numbers(graph: rdflib.Graph) -> list[int]:
    return sorted(n for n, _, _ in design_record.principles(graph))


def test_the_parsed_design_record_conforms_to_the_shapes():
    """Every principle has a number, a claim and exactly one contributing
    appendix; every appendix has a letter and at least one revision."""
    data = _graph()
    data.parse(VOCABULARY, format="turtle")
    shapes = rdflib.Graph()
    for path in SHAPES:
        shapes.parse(path, format="turtle")
    conforms, _, text = validate(data, shacl_graph=shapes, advanced=True)
    assert conforms, text


def test_the_principle_sequence_is_contiguous():
    """SHACL constrains a focus node, not a set, so "1..N with no gaps" has no
    shape form and lives here instead.

    Contiguity is what makes a principle number an address: `DESIGN.md`,
    `CONTEXT.md`, `docs/BACKLOG.md` and `docs/evidence/` all cite one, and a gap
    means an appendix allocated a block that overlaps or skips a neighbour's.
    """
    numbers = _numbers(_graph())
    assert numbers == list(range(1, len(numbers) + 1)), (
        f"the principle sequence is not 1..{len(numbers)}: "
        f"{[n for i, n in enumerate(numbers, 1) if n != i][:5]}"
    )


def test_the_contiguity_check_would_catch_a_gap():
    """The property above is already true, so the check is trusted by a mutant
    rather than by a red run (`CLAUDE.md`, and principle 34's habit)."""
    graph = _graph()
    node = design_record.SAFFRON["principle-30"]
    graph.remove((node, None, None))
    numbers = _numbers(graph)
    assert numbers != list(range(1, len(numbers) + 1))


def test_each_appendix_contributed_a_contiguous_block():
    """A block, not a scatter. This is why the sequence stays contiguous with no
    registry: an appendix claims its numbers when it is written, in one run.
    """
    graph = _graph()
    blocks: dict[str, list[int]] = {}
    for number, _, letter in design_record.principles(graph):
        blocks.setdefault(letter, []).append(number)
    scattered = {
        letter: numbers
        for letter, numbers in blocks.items()
        if numbers != list(range(numbers[0], numbers[-1] + 1))
    }
    assert not scattered, f"appendices contributed non-contiguous blocks: {scattered}"


def test_the_committed_index_is_current_with_the_appendices():
    committed = DESIGN.read_text()
    assert design_record.render_principles(committed) == committed, (
        "DESIGN.md's principle index and its appendices disagree. The appendices "
        "are authoritative: run `uv run python -m ontology.render`. An edit made "
        "in the table is discarded — make it in the appendix that owns the prose."
    )


def test_the_currency_check_would_catch_a_dropped_row():
    """A hand-edited index is the failure this whole surface exists to prevent,
    so the check is shown removing a row rather than assumed to."""
    committed = DESIGN.read_text()
    lines = committed.splitlines(keepends=True)
    without = "".join(ln for ln in lines if not ln.startswith("| 12 | "))
    assert without != committed, "the fixture row was not found — has the index moved?"
    assert design_record.render_principles(without) != without


# An appendix that contributes no principle is well-formed — `RevisionAppendixShape`
# asks for a letter and a revision, not a lesson — so the check below cannot simply
# equate the two sets. Naming one here is the decision; an empty set is not a
# weaker test, it is the claim that no appendix has needed the exemption yet.
CONTRIBUTES_NO_PRINCIPLE: frozenset[str] = frozenset()


def test_the_index_reaches_every_appendix():
    """A parser that silently stopped early would leave a shorter index that is
    internally consistent and wrong — the absent-result shape of principle 34.

    Against the headings rather than a count: a floor is satisfied by the very
    drop it is watching for, and this one was — 16 appendices passed `>= 15`.
    """
    source = DESIGN.read_text()
    headings = {
        m.group(1) for m in map(design_record.APPENDIX.match, source.splitlines()) if m
    }
    letters = {letter for _, _, letter in design_record.principles(_graph())}
    assert headings - letters == CONTRIBUTES_NO_PRINCIPLE, (
        "appendices the parser did not reach: "
        f"{sorted(headings - letters - CONTRIBUTES_NO_PRINCIPLE)}"
    )
    assert not letters - headings, (
        f"principles credited to no heading: {letters - headings}"
    )


@pytest.mark.parametrize(
    "typo",
    ["## Appendix P - ", "### Appendix P — ", "##  Appendix P — ", "## Appendix P\n"],
    ids=["hyphen", "heading level", "double space", "no title"],
)
def test_a_heading_it_cannot_read_is_refused(typo: str):
    """The property above is already true, so the check is trusted by mutants.

    An em dash typed as a hyphen used to credit Appendix P's principles to O,
    leaving 1..57 contiguous, 15 letters, and only the index reading stale —
    which `ontology.render` then rewrote to say O. The other three break the
    heading in ways `APPENDIX` also cannot read, which is why `APPENDIX_OPENS`
    reaches past the level and spacing it accepts.
    """
    committed = DESIGN.read_text()
    mutant = committed.replace("## Appendix P — ", typo, 1)
    assert mutant != committed, (
        "the fixture heading was not found — has Appendix P moved?"
    )
    with pytest.raises(ValueError, match="an appendix heading this cannot read"):
        design_record.parse(mutant)
