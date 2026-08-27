"""Where `CONTEXT.md` and the ontology both close a set, they close it the same.

Not a generated vocabulary: `CONTEXT.md` names the whole system and the ontology
names only the run record, so most of that file has no term here and would fail
the dead-term test if it did. This checks the overlap alone — three sets both
documents already enumerate — because that overlap is where they have measurably
drifted. `CONTEXT.md` §6 listed six terminal states, `DESIGN.md` §3.3 listed
nine, and `saffron/cell/session.py` wrote a tenth state neither called terminal.
"""

import re

import pytest
import rdflib
from ontology_paths import NS, ONTOLOGY, VOCABULARY

CONTEXT = ONTOLOGY.parent / "CONTEXT.md"

# term in CONTEXT.md -> the class in the ontology whose members it should match
CLOSED_SETS = {
    "Terminal state": "TerminalState",
    "Severity": "Severity",
    "Risk tier": "RiskTier",
}


def context_enumeration(term: str) -> set[str]:
    """The backticked tokens in a definition's first sentence.

    First sentence only: every one of these definitions goes on to mention other
    backticked names — `elevate_on`, `coverage`, `DESIGN.md` — that are prose
    about the set rather than members of it.
    """
    body = CONTEXT.read_text()
    start = body.index(f"**{term}**:") + len(f"**{term}**:")
    sentence = re.split(r"\.(?:\s|$)", body[start:], maxsplit=1)[0]
    return set(re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`", sentence))


def ontology_members(class_name: str) -> set[str]:
    graph = rdflib.Graph().parse(VOCABULARY, format="turtle")
    return {
        str(s).removeprefix(NS)
        for s in graph.subjects(rdflib.RDF.type, rdflib.URIRef(f"{NS}{class_name}"))
    }


@pytest.mark.parametrize("term,class_name", CLOSED_SETS.items())
def test_the_two_documents_close_the_set_the_same_way(term, class_name):
    from_context = context_enumeration(term)
    from_ontology = ontology_members(class_name)
    assert from_context, f"parsed no members out of CONTEXT.md's {term!r}"
    assert from_ontology, f"the ontology declares no {class_name}"
    assert from_context == from_ontology, (
        f"{term}: CONTEXT.md says {sorted(from_context)}, "
        f"saffron:{class_name} says {sorted(from_ontology)}"
    )


def test_the_parser_would_notice_a_changed_set():
    """A parser that silently returns nothing makes every comparison above pass.
    Both halves are asserted non-empty; this pins the shape it reads."""
    assert context_enumeration("Risk tier") == {"standard", "elevated"}
    assert "elevate_on" not in context_enumeration("Risk tier")
