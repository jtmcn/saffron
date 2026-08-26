"""The shapes accept the lifecycle graph and reject one graph each."""

import pytest
import rdflib
from ontology_paths import FIXTURES, NEGATIVE, NS, VENDOR, VOCABULARY
from pyshacl import validate

SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")


def _named_shape_of(shapes_graph: rdflib.Graph, node) -> set[str]:
    """Which named node shape a reported sh:sourceShape belongs to.

    Property shapes are blank nodes nested inside their node shape, and that is
    what a violation names — so a test that asserted on sh:sourceShape directly
    could not tell which shape did the rejecting.
    """
    owners = set()
    for named in shapes_graph.subjects(rdflib.RDF.type, SH.NodeShape):
        if not isinstance(named, rdflib.URIRef):
            continue
        seen, frontier = set(), [named]
        while frontier:
            current = frontier.pop()
            if current in seen:
                continue
            seen.add(current)
            for _, _, o in shapes_graph.triples((current, None, None)):
                if isinstance(o, (rdflib.BNode, rdflib.URIRef)):
                    frontier.append(o)
        if node in seen:
            owners.add(str(named))
    return owners


def test_the_lifecycle_graph_conforms(shapes_graph):
    data = rdflib.Graph()
    for path in [VOCABULARY, FIXTURES / "lifecycle.ttl", *VENDOR]:
        data.parse(path, format="turtle")
    conforms, _, text = validate(data, shacl_graph=shapes_graph, advanced=True)
    assert conforms, text


@pytest.mark.parametrize("fixture", NEGATIVE, ids=lambda p: p.stem)
def test_each_shape_rejects_its_negative_fixture(fixture, shapes_graph):
    """A shape that no committed graph violates has not been shown to constrain
    anything. Each fixture is self-contained and the assertion is equality, not
    membership: a fixture that also trips a second shape is not isolating the
    constraint it claims to, and membership would hide that."""
    data = rdflib.Graph().parse(fixture, format="turtle")
    conforms, results, text = validate(data, shacl_graph=shapes_graph, advanced=True)
    assert not conforms, f"{fixture.name} was accepted"

    violated = set()
    for _, _, source in results.triples((None, SH.sourceShape, None)):
        violated |= _named_shape_of(shapes_graph, source)
    assert f"{NS}{fixture.stem}" in violated, (
        f"{fixture.name} fired {violated}, not itself"
    )


def test_every_shape_has_a_negative_fixture(shapes_graph):
    named = {
        str(s).removeprefix(NS)
        for s in shapes_graph.subjects(rdflib.RDF.type, SH.NodeShape)
        if isinstance(s, rdflib.URIRef)
    }
    assert named == {p.stem for p in NEGATIVE}
