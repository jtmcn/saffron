"""Where `CONTEXT.md` and the ontology both close a set, they close it the same.

Not a generated vocabulary: `CONTEXT.md` names the whole system and the ontology
names only the run record, so most of that file has no term here and would fail
the dead-term test if it did. This checks the overlap alone — six sets both
documents already enumerate — because that overlap is where they have measurably
drifted. `CONTEXT.md` §6 listed six terminal states, `DESIGN.md` §3.3 listed
nine, and `saffron/cell/session.py` wrote a tenth state neither called terminal.
"""

import sys

import pytest
import rdflib
from ontology_paths import FIXTURES, NS, ONTOLOGY, VOCABULARY

from ontology import render
from ontology.spans import definition_sentence

CONTEXT = ONTOLOGY.parent / "CONTEXT.md"

# term in CONTEXT.md -> the class in the ontology whose members it should match
CLOSED_SETS = {
    "In-flight state": "InFlightState",
    "End state": "EndState",
    "Terminal state": "TerminalState",
    "Batch stop reason": "BatchStopReason",
    "Severity": "Severity",
    "Risk tier": "RiskTier",
    "Gate role": "GateRole",
    "Core gates": "CoreGate",
    "Preflight outcome": "PreflightOutcome",
    "Event kind": "EventKind",
    "Fact kind": "FactKind",
}


def context_enumeration(term: str) -> set[str]:
    """The backticked tokens in a definition's first sentence.

    The span comes from the renderer's own function, `definition_sentence`,
    so this reader and `render_context` rewrite the same bytes.

    The token pattern is imported rather than repeated: `ontology.render`
    locates its write span from the same matches, so the span it rewrites cannot
    reach a token this rejects. Two copies let it, and `DESIGN.md` in a first
    sentence made the renderer delete the prose after it while this stayed green.
    """
    body = CONTEXT.read_text()
    start, end = definition_sentence(body, term)
    return set(render.MEMBER_TOKEN.findall(body[start:end]))


def ontology_members(class_name: str) -> set[str]:
    """Instances of the class or any subclass. rdflib infers neither."""
    graph = rdflib.Graph().parse(VOCABULARY, format="turtle")
    classes = graph.transitive_subjects(
        rdflib.RDFS.subClassOf, rdflib.URIRef(f"{NS}{class_name}")
    )
    return {
        str(s).removeprefix(NS)
        for cls in classes
        for s in graph.subjects(rdflib.RDF.type, cls)
    }


@pytest.mark.parametrize("term,class_name", CLOSED_SETS.items())
def test_the_two_documents_close_the_set_the_same_way(term, class_name):
    from_context = context_enumeration(term)
    from_ontology = ontology_members(class_name)
    assert from_context, f"parsed no members out of CONTEXT.md's {term!r}"
    assert from_ontology, f"the ontology declares no {class_name}"
    assert from_context == from_ontology, (
        f"{term}: CONTEXT.md says {sorted(from_context)}, "
        f"factory:{class_name} says {sorted(from_ontology)}"
    )


def test_the_reader_refuses_each_definition_the_renderer_refuses(tmp_path, monkeypatch):
    """A definition the renderer could not rewrite must raise here too.
    One shared function, one reason, over the same text.
    """
    this_module = sys.modules[__name__]
    no_trailing_period = "**Risk tier**: `standard` or `elevated`"
    no_period_before_blank_line = (
        "**Risk tier**: `standard` or `elevated`\n\n"
        "A later paragraph names `elevate_on`.\n"
    )
    defined_twice = "**Risk tier**: `standard`.\n\n**Risk tier**: `elevated`.\n"

    for entry in (
        no_trailing_period,
        no_period_before_blank_line,
        defined_twice,
    ):
        context_path = tmp_path / "CONTEXT.md"
        context_path.write_text(entry)
        monkeypatch.setattr(this_module, "CONTEXT", context_path)
        with pytest.raises(ValueError):
            context_enumeration("Risk tier")
        with pytest.raises(ValueError):
            definition_sentence(entry, "Risk tier")

    def _raise_lookup_error(text: str, term: str) -> tuple[int, int]:
        raise LookupError(f"{term}: no span for this stub")

    monkeypatch.setattr(this_module, "definition_sentence", _raise_lookup_error)
    with pytest.raises(LookupError):
        context_enumeration("Risk tier")


def test_the_parser_would_notice_a_changed_set():
    """A parser that silently returns nothing makes every comparison above pass.
    Both halves are asserted non-empty; this pins the shape it reads."""
    assert context_enumeration("Risk tier") == {"standard", "elevated"}
    assert "elevate_on" not in context_enumeration("Risk tier")


def test_the_gate_statuses_are_earl_outcomes_rather_than_saffron_terms():
    """CONTEXT.md §4 closes a fourth set — `pass`, `fail`, `skip`, `error` — and
    the ontology deliberately declares none of them: EARL's outcome values *are*
    those four, and `skip` being `inapplicable` and `error` being `cantTell` is
    the alignment that states "`error` is not `fail`" in a vendored vocabulary
    rather than in our own prose.

    The check is that each status has an outcome standing for it *in the fixture
    graph*, not merely in this docstring — a mapping nothing exercises is the
    part that is cheap to fake — and that nobody quietly adds a competing
    `factory:` term for a status.
    """
    statuses = context_enumeration("Status")
    assert statuses == {"pass", "fail", "skip", "error"}

    vocabulary = rdflib.Graph().parse(VOCABULARY, format="turtle")
    for status in statuses:
        assert (rdflib.URIRef(f"{NS}{status}"), None, None) not in vocabulary, (
            f"factory:{status} duplicates an EARL outcome"
        )

    earl = rdflib.Namespace("http://www.w3.org/ns/earl#")
    graph = rdflib.Graph()
    for path in [VOCABULARY, FIXTURES / "lifecycle.ttl"]:
        graph.parse(path, format="turtle")
    for status, outcome in (
        ("pass", earl.passed),
        ("fail", earl.failed),
        ("skip", earl.inapplicable),
        ("error", earl.cantTell),
    ):
        assert (None, earl.outcome, outcome) in graph, (
            f"no assertion in the fixture stands for a `{status}` gate result"
        )


def test_every_severity_has_its_own_bullet():
    """`**Severity**`'s first sentence is generated; the bullets under it are a
    second, complete copy — one per member, each carrying what the severity
    *does* (`blocker` routes to REBUT). A new severity would land in the
    sentence and have no bullet, and nothing noticed.

    Terminal states are deliberately not checked this way: only two of the nine
    have their own paragraph, so that list is selective rather than a copy.
    """
    body = CONTEXT.read_text()
    missing = [
        member
        for member in sorted(ontology_members("Severity"))
        if f"- **`{member}`**" not in body
    ]
    assert not missing, (
        f"severities with no bullet in CONTEXT.md: {missing}. Each bullet says "
        "what the severity does, which the generated sentence cannot state."
    )
