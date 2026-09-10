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
        "these core-side, so add each to factory:CoreGateBlockingShape (or "
        "factory:SizeTierShape if a risk tier moves it) in factory-shapes.ttl."
    )


def test_every_terminal_state_is_a_state_a_task_can_end_in(shapes_graph):
    """`TaskShape`'s endedInState list is a hand-maintained *superset* of the
    now-generated `TerminalStateShape` list, and nothing held the generated
    subset inside it. Measured: declaring `factory:BUDGET_SPENT` and running the
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
        "factory:TaskShape's endedInState sh:in list in factory-shapes.ttl — it "
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
        data=f"""@prefix factory: <{NS}> .
        @prefix : <urn:software-factory:data:> .
        :b a factory:Batch ; factory:budgetUsd 50.0 ;
           factory:endedBecause factory:{reason} .""",
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
        data=f"""@prefix factory: <{NS}> .
        @prefix : <urn:software-factory:data:> .
        :b a factory:Batch ; factory:budgetUsd 50.0 .""",
        format="turtle",
    )
    conforms, _, text = validate(data, shacl_graph=shapes_graph, advanced=True)
    assert conforms, text


def test_a_reason_that_claims_the_class_is_still_refused_by_the_enumeration(
    shapes_graph,
):
    """The one case where `sh:in` is the constraint doing the work. Measured:
    deleting `sh:in` from `BatchShape` left every case above passing, because
    `sh:class` alone rejects them — `CANCELLED` is undeclared, and `EXHAUSTED`
    and `ORPHANED` are typed `EndState`. So the test named for the enumeration
    survived its own mutant. A value that declares itself a `BatchStopReason`
    clears `sh:class`, which leaves the enumeration as the only thing that can
    refuse it — and refusing it is what closes the set.
    """
    data = rdflib.Graph()
    data.parse(VOCABULARY, format="turtle")
    data.parse(
        data=f"""@prefix factory: <{NS}> .
        @prefix : <urn:software-factory:data:> .
        :CANCELLED a factory:BatchStopReason .
        :b a factory:Batch ; factory:budgetUsd 50.0 ;
           factory:endedBecause :CANCELLED .""",
        format="turtle",
    )
    conforms, results, text = validate(data, shacl_graph=shapes_graph, advanced=True)
    assert not conforms, text
    # On the component, not the message: `sh:class` rejecting this would read as
    # a pass to a membership check on the text, which is the trap above.
    components = set(results.objects(None, SH.sourceConstraintComponent))
    assert components == {SH.InConstraintComponent}, text


def _components(graph: str, shapes_graph) -> tuple[bool, set, str]:
    data = rdflib.Graph()
    data.parse(VOCABULARY, format="turtle")
    data.parse(
        data=f"""@prefix factory: <{NS}> .
        @prefix prov: <http://www.w3.org/ns/prov#> .
        @prefix : <urn:software-factory:data:> .
        :operator a factory:Operator . {graph}""",
        format="turtle",
    )
    conforms, results, text = validate(data, shacl_graph=shapes_graph, advanced=True)
    return conforms, set(results.objects(None, SH.sourceConstraintComponent)), text


_ACTING = ":s a factory:Delegate ; prov:actedOnBehalfOf :operator ."
# Valid under AttemptShape, so only DelegateShape can refuse it.
_ATTEMPT = ":ph a factory:Phase . :at a factory:Attempt ; factory:withinPhase :ph ; factory:n 1 ;"


@pytest.mark.parametrize(
    ("graph", "components"),
    [
        (f"{_ACTING} :work prov:qualifiedAssociation [ prov:agent :s ] .", set()),
        (":s a factory:Delegate .", {SH.QualifiedMinCountConstraintComponent}),
        # A subagent acts for the delegate that started it; the chain still ends
        # at the operator.
        (
            ":s a factory:Delegate ; prov:actedOnBehalfOf :t . "
            ":t a factory:Delegate ; prov:actedOnBehalfOf :operator .",
            set(),
        ),
        (
            ":s a factory:Delegate ; prov:actedOnBehalfOf :t . :t a factory:Delegate .",
            {SH.QualifiedMinCountConstraintComponent},
        ),
        # One chain reaching the operator does not excuse another that does not.
        (
            ":s a factory:Delegate ; prov:actedOnBehalfOf :i . "
            ":i a factory:ImplementerSession ; prov:actedOnBehalfOf :operator .",
            {SH.OrConstraintComponent},
        ),
        (
            f"{_ACTING} :s prov:actedOnBehalfOf factory:scope .",
            {SH.OrConstraintComponent},
        ),
        (
            ":s a factory:Delegate, factory:Operator ; prov:actedOnBehalfOf :operator .",
            {SH.NotConstraintComponent},
        ),
        # A delegate may be handed a plan; nothing outside it holds it to one.
        (
            f"{_ACTING} :work prov:qualifiedAssociation "
            "[ prov:agent :s ; prov:hadPlan :plan ] .",
            set(),
        ),
        # Typing the command is not the judgement: ratification stays the operator's.
        (
            f"{_ACTING} :tc a factory:TouchesSet ; factory:ratifiedBy :s .",
            {SH.ClassConstraintComponent},
        ),
        (
            f"{_ACTING} {_ATTEMPT} prov:qualifiedAssociation [ prov:agent :s ] .",
            {SH.QualifiedMaxCountConstraintComponent},
        ),
        (
            f"{_ACTING} {_ATTEMPT} prov:wasAssociatedWith :s .",
            {SH.QualifiedMaxCountConstraintComponent},
        ),
    ],
    ids=[
        "unplanned",
        "no-principal",
        "subagent",
        "chain-without-operator",
        "for-implementer",
        "for-gate-too",
        "is-operator",
        "planned",
        "ratifies",
        "attempt",
        "attempt-unqualified",
    ],
)
def test_a_delegate_acts_for_the_operator_never_as_one_nor_in_an_attempt(
    graph, components, shapes_graph
):
    """Asserted on the component, not on conformance: each case has to be refused
    by the constraint it names, or a sibling constraint rejecting it would hide a
    deleted one — the trap the enumeration test above records."""
    conforms, found, text = _components(graph, shapes_graph)
    assert conforms == (not components), text
    assert found == components, text


_IMPL = ":i a factory:ImplementerSession ; prov:actedOnBehalfOf :operator ."
_WROTE_DIFF = f":df a factory:Diff . {_ATTEMPT} prov:generated :df ;"
_PROPOSED = f":sp a factory:ScopeProposal . {_ATTEMPT} prov:generated :sp ;"
_NOT_ATTEMPT = ":df a factory:Diff . :work prov:generated :df ;"


@pytest.mark.parametrize(
    ("graph", "components"),
    [
        (
            f"{_IMPL} :p a factory:Plan . {_WROTE_DIFF} prov:qualifiedAssociation "
            "[ prov:agent :i ; prov:hadPlan :p ] .",
            set(),
        ),
        # A delegate that runs a cell stands between the implementer and the operator.
        (
            ":i a factory:ImplementerSession ; prov:actedOnBehalfOf :d . "
            ":d a factory:Delegate ; prov:actedOnBehalfOf :operator .",
            set(),
        ),
        # Work outside an attempt is not what the plan governs.
        (
            f"{_IMPL} {_NOT_ATTEMPT} prov:qualifiedAssociation [ prov:agent :i ] .",
            set(),
        ),
        # A scope proposal ends the attempt before any plan exists (§5.3.1).
        (f"{_IMPL} {_PROPOSED} prov:qualifiedAssociation [ prov:agent :i ] .", set()),
        (
            ":i a factory:ImplementerSession .",
            {SH.QualifiedMinCountConstraintComponent},
        ),
        (
            ":i a factory:ImplementerSession ; prov:actedOnBehalfOf :x . "
            ":x a prov:SoftwareAgent .",
            {SH.OrConstraintComponent, SH.QualifiedMinCountConstraintComponent},
        ),
        # The operator is reachable, but through an agent that is no delegate.
        (
            ":i a factory:ImplementerSession ; prov:actedOnBehalfOf :l . "
            ":l a factory:CriticLens ; prov:actedOnBehalfOf :operator .",
            {SH.OrConstraintComponent},
        ),
        (
            f"{_IMPL} {_WROTE_DIFF} prov:qualifiedAssociation [ prov:agent :i ] .",
            {SH.QualifiedMaxCountConstraintComponent},
        ),
        # Any prov:Plan will not do: the plan is the one the host validated.
        (
            f"{_IMPL} :p a prov:Plan . {_WROTE_DIFF} prov:qualifiedAssociation "
            "[ prov:agent :i ; prov:hadPlan :p ] .",
            {SH.QualifiedMaxCountConstraintComponent},
        ),
        # The unqualified shortcut cannot carry a plan.
        (
            f"{_IMPL} {_WROTE_DIFF} prov:wasAssociatedWith :i .",
            {SH.QualifiedMaxCountConstraintComponent},
        ),
        # PROV-O's chain axiom entails the shortcut from the qualified form, so
        # a reasoner's output asserts both.
        (
            f"{_IMPL} :p a factory:Plan . {_WROTE_DIFF} prov:wasAssociatedWith :i ; "
            "prov:qualifiedAssociation [ prov:agent :i ; prov:hadPlan :p ] .",
            set(),
        ),
        # Another agent's association, so only the shortcut's rule reads its plan.
        (
            f"{_IMPL} :p a prov:Plan . {_WROTE_DIFF} prov:wasAssociatedWith :i ; "
            "prov:qualifiedAssociation [ prov:agent :other ; prov:hadPlan :p ] .",
            {SH.QualifiedMaxCountConstraintComponent},
        ),
        (f"{_IMPL} {_NOT_ATTEMPT} prov:wasAssociatedWith :i .", set()),
        (f"{_IMPL} {_PROPOSED} prov:wasAssociatedWith :i .", set()),
    ],
    ids=[
        "planned",
        "through-delegate",
        "non-attempt",
        "scope-proposal",
        "no-principal",
        "non-operator-principal",
        "lens-between",
        "unplanned-diff",
        "unvalidated-plan",
        "unqualified-diff",
        "entailed-shortcut",
        "unqualified-beside-unvalidated-plan",
        "unqualified-non-attempt",
        "unqualified-scope-proposal",
    ],
)
def test_the_implementer_acts_for_the_operator_and_works_each_attempt_to_its_plan(
    graph, components, shapes_graph
):
    """On the component, for the reason the delegate's cases give."""
    conforms, found, text = _components(graph, shapes_graph)
    assert conforms == (not components), text
    assert found == components, text
