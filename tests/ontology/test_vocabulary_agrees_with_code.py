"""Where the vocabulary and the shipped code both close a set, they close it the same.

Only one set is closed in both places. `Severity` is a `Literal` in
`saffron/agents/findings.py`, so a severity declared in the vocabulary that the
code cannot represent is a run record that cannot be written — pydantic rejects
it. Core gates have no Python registry (they are discovered), and the terminal
states the code names fall through to a documented default rather than a raise,
so neither is a closed set on the code side and neither is checked here.

This reads the code; it does not make the code read the ontology. Nothing under
`saffron/` imports a graph library or the generator, and `pyproject.toml` says so.
"""

from typing import get_args

import rdflib
from ontology_paths import NS, VOCABULARY

from saffron.agents.findings import Severity


def test_the_severities_the_code_accepts_are_the_ones_the_vocabulary_declares():
    graph = rdflib.Graph().parse(VOCABULARY, format="turtle")
    declared = {
        str(s).removeprefix(NS)
        for s in graph.subjects(rdflib.RDF.type, rdflib.URIRef(f"{NS}Severity"))
    }
    assert declared == set(get_args(Severity)), (
        "saffron:Severity and saffron/agents/findings.py disagree. A severity "
        "the vocabulary declares and the Literal omits cannot be written to the "
        "run record at all; the generator cannot reach Python, so this is a "
        "hand edit in findings.py."
    )
