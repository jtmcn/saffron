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

# The hyphen is load-bearing: `no-network` is a gate role, and a regex that
# stopped at the hyphen read its shape reference as a mention of `no`.
TERM = re.compile(r"saffron:([A-Za-z_][A-Za-z0-9_-]*)")


def terms_in(text: str) -> set[str]:
    """Terms named in code, with comment lines stripped. A term named only in
    prose has exactly the reader this test rejects.

    ponytail: whole-line comments only. A trailing comment after a triple still
    counts; splitting on `#` mid-line would break on every IRI, which all contain
    one. Reach for a real Turtle/SPARQL lexer only if that case shows up.
    """
    code = [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]
    return set(TERM.findall("\n".join(code)))


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
        names |= terms_in(path.read_text())
    return names


def dead_terms(declared: set[str], referenced: set[str]) -> list[str]:
    return sorted(declared - referenced)


def test_no_term_exists_without_a_reader():
    dead = dead_terms(declared_terms(), referenced_terms())
    assert not dead, f"unjustified terms — delete them, do not comment them: {dead}"


def test_the_check_would_catch_a_new_dead_term():
    """Through the same comparison the real test uses, not a restatement of it —
    a guard that only re-derives set difference stays green even if the check
    above is gutted."""
    assert dead_terms(declared_terms() | {"DecorativeTerm"}, referenced_terms()) == [
        "DecorativeTerm"
    ]


def test_a_term_named_only_in_a_comment_is_still_dead():
    assert terms_in("# saffron:Ghost is genuinely useful, honest") == set()
    assert terms_in("saffron:Ghost a owl:Class .") == {"Ghost"}
