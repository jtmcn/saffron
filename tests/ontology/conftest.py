"""The ontology tests read files and nothing else — no network, by construction:
PROV-O and EARL are vendored, and pyoxigraph resolves no IRI it is not given.
"""

import pyoxigraph as ox
import pytest
import rdflib
from ontology_paths import FIXTURES, SHAPES, VENDOR, VOCABULARY


@pytest.fixture(scope="session")
def store() -> ox.Store:
    """The vocabulary, its vendored imports, and the one lifecycle fixture."""
    s = ox.Store()
    for path in [VOCABULARY, FIXTURES / "lifecycle.ttl", *VENDOR]:
        s.bulk_load(path=str(path), format=ox.RdfFormat.TURTLE)
    return s


@pytest.fixture(scope="session")
def shapes_graph() -> rdflib.Graph:
    g = rdflib.Graph()
    for path in SHAPES:
        g.parse(path, format="turtle")
    return g
