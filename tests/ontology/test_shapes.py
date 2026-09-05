"""The shapes accept the lifecycle graph and reject one graph each."""

import pytest
import rdflib
import rdflib.collection
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
        seen = set()
        frontier: list[rdflib.BNode | rdflib.URIRef] = [named]
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
    """The vendored vocabularies are loaded here and not by the `shacl` gate,
    which validates only what this repo owns. Nothing in the shapes targets a
    PROV or EARL class, so the two agree today; the gate is the blocking reader
    and is authoritative if they ever stop agreeing."""
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
    assert violated == {f"{NS}{fixture.stem}"}, f"{fixture.name} fired {violated}"


def test_every_shape_has_a_negative_fixture(shapes_graph):
    named = {
        str(s).removeprefix(NS)
        for s in shapes_graph.subjects(rdflib.RDF.type, SH.NodeShape)
        if isinstance(s, rdflib.URIRef)
    }
    assert named == {p.stem for p in NEGATIVE}


def test_every_core_gate_declares_a_blocking_level(shapes_graph):
    """Generating `CoreGateShape`'s `sh:in` removed a check that was catching
    this by accident. `CoreGateBlockingShape` holds a fourth copy of the core
    gates as `sh:targetNode`, and it cannot be generated: it targets the
    always-blocking gates and asserts they are always-blocking, so rendering it
    from the vocabulary would make it vacuous. Before the generator existed, a
    core gate missing from it was rejected by `CoreGateShape`'s `sh:in`, which
    forced a human into this file; now that list writes itself, and an advisory
    core gate conforms with the §5.4 axiom silently not applying to it.

    Read from the shapes rather than through `ontology.render`, deliberately:
    the generator is what endangered this invariant.
    """
    vocabulary = rdflib.Graph().parse(VOCABULARY, format="turtle")
    declared = set(vocabulary.subjects(rdflib.RDF.type, rdflib.URIRef(f"{NS}CoreGate")))
    covered: set = set()
    for shape in ("CoreGateBlockingShape", "SizeTierShape"):
        covered |= set(
            shapes_graph.objects(rdflib.URIRef(f"{NS}{shape}"), SH.targetNode)
        )
    missing = sorted(str(gate).removeprefix(NS) for gate in declared - covered)
    assert not missing, (
        f"core gates with no declared blocking level: {missing}. §5.4 fixes "
        "these core-side, so add each to saffron:CoreGateBlockingShape (or "
        "saffron:SizeTierShape if a risk tier moves it) in saffron-shapes.ttl."
    )


def test_every_terminal_state_is_a_state_a_task_can_end_in(shapes_graph):
    """`TaskShape`'s endedInState list is a hand-maintained *superset* of the
    now-generated `TerminalStateShape` list, and nothing held the generated
    subset inside it. Measured: declaring `saffron:BUDGET_SPENT` and running the
    renderer left `tests/ontology/` and the `shacl` gate green while a one-task
    graph was rejected — the shapes file saying a state reaches the operator and
    that no task may end in it. endedInState closes over `EndState`, a superset,
    so it is correctly not generated; that makes it a hole to route to a person,
    which is the argument `CoreGateBlockingShape` already carries one shape over.
    """
    vocabulary = rdflib.Graph().parse(VOCABULARY, format="turtle")
    terminal = set(
        vocabulary.subjects(rdflib.RDF.type, rdflib.URIRef(f"{NS}TerminalState"))
    )
    accepted: set = set()
    for shape in shapes_graph.subjects(SH.path, rdflib.URIRef(f"{NS}endedInState")):
        for lst in shapes_graph.objects(shape, SH["in"]):
            accepted |= set(rdflib.collection.Collection(shapes_graph, lst))
    missing = sorted(str(state).removeprefix(NS) for state in terminal - accepted)
    assert not missing, (
        f"terminal states no task may end in: {missing}. Add each to "
        "saffron:TaskShape's endedInState sh:in list in saffron-shapes.ttl — it "
        "closes over EndState, a superset, so the generator cannot write it."
    )


@pytest.mark.parametrize(
    ("reason", "accepted"),
    [
        ("DRAINED", True),
        ("BUDGET", True),
        ("UNTIL", True),
        ("INFRASTRUCTURE", True),
        # A fifth reason invented in SQL, where the set used to live alone.
        ("CANCELLED", False),
        # A *task's* terminal state. This is the confusion the class exists to
        # prevent: `EXHAUSTED` is a task that could not pass its gates, and a
        # night is not a task. `saffron batch` maps three of the four stop
        # reasons to exit 0, so reading one set as the other misreports a night.
        ("EXHAUSTED", False),
        ("ORPHANED", False),
    ],
)
def test_a_night_stops_for_one_of_four_reasons_and_no_others(
    reason, accepted, shapes_graph
):
    """The enumeration, exercised. `batches.status` carries a CHECK constraint
    saying the same thing, and the two are not redundant: the constraint refuses
    a bad write, and this says the four are a closed set with a meaning — one
    that does not overlap the task end states despite sharing a column type and
    a naming style."""
    data = rdflib.Graph()
    data.parse(VOCABULARY, format="turtle")
    data.parse(
        data=f"""@prefix saffron: <{NS}> .
        @prefix : <https://saffron.dev/data/> .
        :b a saffron:Batch ; saffron:budgetUsd 50.0 ;
           saffron:endedBecause saffron:{reason} .""",
        format="turtle",
    )
    conforms, _, text = validate(data, shacl_graph=shapes_graph, advanced=True)
    assert conforms is accepted, text


def test_a_batch_still_running_has_no_stop_reason_and_that_is_legal(shapes_graph):
    """`minCount 0`, and it is the axiom rather than an omission. `batches.status`
    is nullable and NULL means *still running* — the one state §6's morning queue
    must tell apart from a night that stopped, and the thing a CHECK constraint
    cannot say, since it can only name which strings are legal."""
    data = rdflib.Graph()
    data.parse(VOCABULARY, format="turtle")
    data.parse(
        data=f"""@prefix saffron: <{NS}> .
        @prefix : <https://saffron.dev/data/> .
        :b a saffron:Batch ; saffron:budgetUsd 50.0 .""",
        format="turtle",
    )
    conforms, _, text = validate(data, shacl_graph=shapes_graph, advanced=True)
    assert conforms, text
