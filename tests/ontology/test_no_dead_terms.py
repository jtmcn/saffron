"""Every term in the `saffron:` namespace is referenced by a query or a shape.

The failure this exists to catch is an isomorphic re-encoding of the §4.1 ledger
— one class per table, one property per column — which parses, validates, and is
worth nothing. A term with no reader has not been shown to deliver alignment,
qualification, or an axiom the schema cannot state (§4.6), and an rdfs:comment
saying otherwise is the part that is cheap to fake. Delete it; do not comment it.
"""

import re

import pyoxigraph as ox
from ontology_paths import NS, QUERIES, SHAPES, VOCABULARY

TERM = re.compile(r"saffron:([A-Za-z_][A-Za-z0-9_]*)")


def declared_terms() -> set[str]:
    store = ox.Store()
    store.bulk_load(path=str(VOCABULARY), format=ox.RdfFormat.TURTLE)
    terms = set()
    for quad in store:
        for node in (quad.subject, quad.predicate, quad.object):
            if isinstance(node, ox.NamedNode) and node.value.startswith(NS):
                name = node.value[len(NS) :]
                if name:  # the ontology IRI itself is not a term
                    terms.add(name)
    return terms


def referenced_terms() -> set[str]:
    names = set()
    for path in [*QUERIES, *SHAPES]:
        names |= set(TERM.findall(path.read_text()))
    return names


def test_no_term_exists_without_a_reader():
    dead = sorted(declared_terms() - referenced_terms())
    assert not dead, f"unjustified terms — delete them, do not comment them: {dead}"


def test_the_check_would_catch_a_new_dead_term():
    """A dead-term test that could never fire would pass against a vocabulary of
    pure decoration, which is the shape it exists to reject."""
    invented = declared_terms() | {"DecorativeTerm"}
    assert "DecorativeTerm" in invented - referenced_terms()
