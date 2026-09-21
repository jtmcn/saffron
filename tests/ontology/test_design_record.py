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

import re
from collections.abc import Callable
from dataclasses import replace

import pytest
import rdflib
from ontology_paths import ONTOLOGY, SHAPES, VOCABULARY
from pyshacl import validate

from ontology import design_record
from records.load import Record

REPO = ONTOLOGY.parent
DESIGN = REPO / "DESIGN.md"


def _records() -> list[Record]:
    return design_record.appendices(REPO)


def _graph() -> rdflib.Graph:
    return design_record.add_adrs(
        design_record.parse(_records()), design_record.adrs(REPO)
    )


def _edited(letter: str, edit: Callable[[str], str]) -> list[Record]:
    """The records with one appendix's body edited, for a mutant."""
    out = []
    for r in _records():
        if r.model.id == letter:
            body = edit(r.body)
            assert body != r.body, (
                f"the fixture text was not found in appendix {letter}"
            )
            r = replace(r, body=body)
        out.append(r)
    return out


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
    `CONTEXT.md`, `docs/backlog/` and `docs/evidence/` all cite one, and a gap
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
    node = design_record.FACTORY["principle-30"]
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
    assert design_record.render_principles(committed, _graph()) == committed, (
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
    assert design_record.render_principles(without, _graph()) != without


def test_the_committed_appendix_index_is_current_with_the_records():
    committed = DESIGN.read_text()
    rendered = design_record.render_appendix_index(committed, _records(), _graph())
    assert rendered == committed, (
        "DESIGN.md's appendix index and the appendix records disagree: run "
        "`uv run python -m ontology.render`. Fix a question in its record's frontmatter."
    )


def test_the_appendix_currency_check_would_catch_a_dropped_row():
    committed = DESIGN.read_text()
    without = "".join(
        ln
        for ln in committed.splitlines(keepends=True)
        if not ln.startswith("| **M** | ")
    )
    assert without != committed, "the fixture row was not found — has the index moved?"
    assert design_record.render_appendix_index(without, _records(), _graph()) != without


def test_an_appendix_with_no_principle_renders_an_empty_last_cell():
    """`_principle_cell` returns "" for `[]`, not a stray number or a raise — an
    appendix that lost every principle still gets a row, with a blank cell."""
    numbered = re.compile(r"^\d+\. \*\*")
    mutant = _edited(
        "M", lambda b: "\n".join(ln for ln in b.splitlines() if not numbered.match(ln))
    )
    graph = design_record.parse(mutant)
    rendered = design_record.render_appendix_index(DESIGN.read_text(), mutant, graph)
    row = next(ln for ln in rendered.splitlines() if ln.startswith("| **M** | "))
    assert row.endswith("|  |"), row


# An appendix that contributes no principle is well-formed — `RevisionAppendixShape`
# asks for a letter and a revision, not a lesson — so the check below cannot simply
# equate the two sets. Naming one here is the decision; an empty set is not a
# weaker test, it is the claim that no appendix has needed the exemption yet.
CONTRIBUTES_NO_PRINCIPLE: frozenset[str] = frozenset()


def test_the_index_reaches_every_appendix():
    """A parser that silently stopped early would leave a shorter index that is
    internally consistent and wrong — the absent-result shape of principle 34.

    Against the record ids rather than a count: a floor is satisfied by the very
    drop it is watching for, and this one was — 16 appendices passed `>= 15`.
    """
    headings = {str(r.model.id) for r in _records()}
    letters = {letter for _, _, letter in design_record.principles(_graph())}
    assert headings - letters == CONTRIBUTES_NO_PRINCIPLE, (
        "appendices the parser did not reach: "
        f"{sorted(headings - letters - CONTRIBUTES_NO_PRINCIPLE)}"
    )
    assert not letters - headings, (
        f"principles credited to no heading: {letters - headings}"
    )


def test_a_principle_number_claimed_twice_is_refused():
    """`_PRINCIPLE` reads any numbered list inside an appendix whose first item
    opens bold, so the wrong direction is two claims rather than none — and
    `graph.value` picks one of them without saying it chose.
    """
    mutant = _edited(
        "G",
        lambda b: "\n1. **A numbered list that opens bold**, not a principle.\n" + b,
    )
    with pytest.raises(ValueError, match="2 values for"):
        design_record.principles(design_record.parse(mutant))


def test_revisions_that_contradict_the_title_are_refused():
    """`revisions` is hand-written and the title states a rev, so a typo has a
    second reading. Without this the shapes accept a well-formed wrong triple."""
    records = [
        replace(r, model=r.model.model_copy(update={"revisions": [9, 10]}))
        if r.model.id == "G"
        else r
        for r in _records()
    ]
    with pytest.raises(ValueError, match="the title says rev 8"):
        design_record.parse(records)


def test_a_pipe_in_a_claim_keeps_the_row_three_cells_wide():
    """A `|` would close its cell early, and the currency test compares render to
    render — it stays green over a table that has silently lost a column."""
    mutant = _edited(
        "P",
        lambda b: b.replace(
            "a third decision, and nobody made it.**",
            "a third decision | nobody made it.**",
        ),
    )
    rendered = design_record.render_principles(
        DESIGN.read_text(), design_record.parse(mutant)
    )
    row = next(line for line in rendered.splitlines() if line.startswith("| 57 | "))
    assert r"\|" in row, row
    assert row.count("|") - row.count(r"\|") == 4, row


def test_a_drifted_table_header_is_refused():
    """The header locates the span it rewrites. Matching it loosely would append
    the rows below the stale ones; not matching it at all must say which file."""
    committed = DESIGN.read_text()
    mutant = committed.replace(
        "| # | The claim | From |", "| # | The claim | Appendix |"
    )
    assert mutant != committed, "the fixture header was not found — has it drifted?"
    with pytest.raises(ValueError, match="header under it"):
        design_record.render_principles(mutant, _graph())


def _appendix_headings(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if design_record.APPENDIX_OPENS.match(ln)]


def test_design_md_holds_no_appendix():
    """An appendix written into `DESIGN.md` the old way is read by nothing: its
    principles never reach the index, and every other test stays green."""
    assert _appendix_headings(DESIGN.read_text()) == [], (
        "DESIGN.md has an appendix heading. Appendices are records: "
        "write it under docs/appendices/."
    )


def test_the_guard_would_catch_an_appendix_written_the_old_way():
    mutant = DESIGN.read_text() + "\n## Appendix Q — rev 21: written the old way\n"
    assert _appendix_headings(mutant)


def test_the_committed_adr_index_is_current_with_the_records():
    committed = DESIGN.read_text()
    rendered = design_record.render_adr_index(committed, design_record.adrs(REPO))
    assert rendered == committed, (
        "DESIGN.md's ADR index and the ADR records disagree: run "
        "`uv run python -m ontology.render`."
    )


def test_the_adr_currency_check_would_catch_a_dropped_row():
    committed = DESIGN.read_text()
    without = "".join(
        ln
        for ln in committed.splitlines(keepends=True)
        if not ln.startswith("| 1 | Decisions")
    )
    assert without != committed, "the ADR 1 row was not found"
    assert design_record.render_adr_index(without, design_record.adrs(REPO)) != without


def test_an_adr_rests_on_the_principles_it_lists():
    graph = _graph()
    adr = design_record.FACTORY["adr-1"]
    rests = set(graph.objects(adr, design_record.FACTORY.restsOn))
    assert rests == {design_record.FACTORY["principle-62"]}
