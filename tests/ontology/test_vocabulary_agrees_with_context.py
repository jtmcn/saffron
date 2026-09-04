"""Where `CONTEXT.md` and the ontology both close a set, they close it the same.

Not a generated vocabulary: `CONTEXT.md` names the whole system and the ontology
names only the run record, so most of that file has no term here and would fail
the dead-term test if it did. This checks the overlap alone — five sets both
documents already enumerate — because that overlap is where they have measurably
drifted. `CONTEXT.md` §6 listed six terminal states, `DESIGN.md` §3.3 listed
nine, and `saffron/cell/session.py` wrote a tenth state neither called terminal.
"""

import re

import pytest
import rdflib
from ontology_paths import FIXTURES, NS, ONTOLOGY, VOCABULARY

from ontology import render

CONTEXT = ONTOLOGY.parent / "CONTEXT.md"

# term in CONTEXT.md -> the class in the ontology whose members it should match
CLOSED_SETS = {
    "Terminal state": "TerminalState",
    "Severity": "Severity",
    "Risk tier": "RiskTier",
    "Gate role": "GateRole",
    "Core gates": "CoreGate",
}


def context_enumeration(term: str) -> set[str]:
    """The backticked tokens in a definition's first sentence.

    First sentence only: every one of these definitions goes on to mention other
    backticked names — `elevate_on`, `coverage`, `DESIGN.md` — that are prose
    about the set rather than members of it.

    The token pattern is imported rather than repeated: `ontology.render`
    locates its write span from the same matches, so the span it rewrites cannot
    reach a token this rejects. Two copies let it, and `DESIGN.md` in a first
    sentence made the renderer delete the prose after it while this stayed green.
    """
    body = CONTEXT.read_text()
    # The marker, not the marker plus a colon: `Core gates` is a bullet that
    # introduces its members with an em dash instead.
    start = body.index(f"**{term}**") + len(f"**{term}**")
    sentence = re.split(r"\.(?:\s|$)", body[start:], maxsplit=1)[0]
    return set(render.MEMBER_TOKEN.findall(sentence))


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


def test_the_gate_statuses_are_earl_outcomes_rather_than_saffron_terms():
    """CONTEXT.md §4 closes a fourth set — `pass`, `fail`, `skip`, `error` — and
    the ontology deliberately declares none of them: EARL's outcome values *are*
    those four, and `skip` being `inapplicable` and `error` being `cantTell` is
    the alignment that states "`error` is not `fail`" in a vendored vocabulary
    rather than in our own prose.

    The check is that each status has an outcome standing for it *in the fixture
    graph*, not merely in this docstring — a mapping nothing exercises is the
    part that is cheap to fake — and that nobody quietly adds a competing
    `saffron:` term for a status.
    """
    statuses = context_enumeration("Status")
    assert statuses == {"pass", "fail", "skip", "error"}

    vocabulary = rdflib.Graph().parse(VOCABULARY, format="turtle")
    for status in statuses:
        assert (rdflib.URIRef(f"{NS}{status}"), None, None) not in vocabulary, (
            f"saffron:{status} duplicates an EARL outcome"
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
