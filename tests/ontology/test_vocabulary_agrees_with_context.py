"""Where `CONTEXT.md` and the ontology close the same set, or name the same
class, they agree.

Not a generated vocabulary. `CONTEXT.md` names the whole system. The ontology
names only the run record, so most of that file has no term here and would
fail the dead-term test if it did. The parametrized test below checks the
eleven closed sets both documents already enumerate, because that overlap is
where they have measurably drifted: `CONTEXT.md` once listed six terminal
states against `DESIGN.md`'s nine. The class check below instead asks
whether every `factory:` class carries its `CONTEXT.md` headword as a label,
or a stated exclusion.
"""

import re
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

# local class name -> why no CONTEXT.md headword stands for it. Each is a
# bullet or a member list inside another entry, never a headword of its own.
EXCLUSIONS = {
    "CoreGate": "a bullet inside the Gate entry, not its own headword",
    "ContractGate": "a bullet inside the Gate entry, not its own headword",
    "RepoDefinedGate": "a bullet inside the Gate entry, not its own headword",
    "BlockingLevel": (
        "its members come from the Blocking / advisory entry, which names "
        "two of three and has no headword for the class itself"
    ),
    "Role": (
        "its members are the Verdict, Adjudication and Rebuttal entries' "
        "own terms; the class carries no headword of its own"
    ),
    "SpecType": (
        "three of six frontmatter types intake knows; no CONTEXT.md entry "
        "defines the class (backlog item b-60d804)"
    ),
}

# Anchored at the line start, so a bullet and a mid-line aside do not
# count, and the colon excludes a bold phrase opening a paragraph.
HEADWORD_RE = re.compile(r"^\*\*([^*\n]+)\*\*:", re.MULTILINE)


def headwords(context_text: str) -> set[str]:
    """Every bold term that opens its own line with a colon."""
    return {m.group(1) for m in HEADWORD_RE.finditer(context_text)}


def ontology_classes(ttl_text: str) -> dict[str, str | None]:
    """Local name -> `rdfs:label` text (or `None`) for every `factory:` class."""
    graph = rdflib.Graph().parse(data=ttl_text, format="turtle")
    classes: dict[str, str | None] = {}
    for s in graph.subjects(rdflib.RDF.type, rdflib.OWL.Class):
        if not str(s).startswith(NS):
            continue
        label = graph.value(s, rdflib.RDFS.label)
        classes[str(s).removeprefix(NS)] = None if label is None else str(label)
    return classes


def class_headword_problems(
    ttl_text: str, context_text: str, exclusions: dict[str, str]
) -> list[str]:
    """One problem per non-excluded class with no label, or a label that
    matches zero or more than one `CONTEXT.md` headword, after casefolding."""
    heads = headwords(context_text)
    problems = []
    for name, label in sorted(ontology_classes(ttl_text).items()):
        if name in exclusions:
            continue
        if label is None:
            problems.append(f"{name}: no rdfs:label")
            continue
        matches = sorted(h for h in heads if h.casefold() == label.casefold())
        if not matches:
            problems.append(f"{name}: label {label!r} matches no CONTEXT.md headword")
        elif len(matches) > 1:
            problems.append(
                f"{name}: label {label!r} matches {len(matches)} "
                f"CONTEXT.md headwords: {matches}"
            )
    return problems


def exclusion_problems(
    ttl_text: str, context_text: str, exclusions: dict[str, str]
) -> list[str]:
    """One problem per exclusion entry that names no class, gives a blank
    reason, or excludes a class whose label does match a headword."""
    classes = ontology_classes(ttl_text)
    heads = headwords(context_text)
    problems = []
    for name, reason in exclusions.items():
        if name not in classes:
            problems.append(f"{name}: exclusion names no declared class")
            continue
        if not reason or not reason.strip():
            problems.append(f"{name}: exclusion reason is blank")
        label = classes[name]
        if label is not None and any(h.casefold() == label.casefold() for h in heads):
            problems.append(
                f"{name}: exclusion's class has a label equal to a headword {label!r}"
            )
    return problems


def context_enumeration(term: str) -> set[str]:
    """The backticked tokens in a definition's first sentence.

    The span comes from the renderer's own function, `definition_sentence`,
    so this reader takes the same span `render_context` rewrites within.

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


# The seven classes with an entry but no CLOSED_SETS member, and the
# headword each one's label must now carry.
SEVEN_HEADWORDS = {
    "TerminalState": "Terminal state",
    "RiskTier": "Risk tier",
    "BatchStopReason": "Batch stop reason",
    "PreflightOutcome": "Preflight outcome",
    "EventKind": "Event kind",
    "FactKind": "Fact kind",
    "Severity": "Severity",
}

_INLINE_TTL = """
@prefix factory: <urn:software-factory:ns#> .
@prefix ex:      <urn:other:ns#> .
@prefix owl:     <http://www.w3.org/2002/07/owl#> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .

factory:PrefixOnly      a owl:Class ; rdfs:label "plan" .
factory:NoLabel         a owl:Class .
factory:TwoCase         a owl:Class ; rdfs:label "widget" .
factory:BulletColon     a owl:Class ; rdfs:label "gizmo" .
factory:NoColon         a owl:Class ; rdfs:label "sprocket" .
factory:MidLine         a owl:Class ; rdfs:label "cog" .
factory:CaseInsensitive a owl:Class ; rdfs:label "pull request" .
ex:Other                a owl:Class .
"""

_INLINE_CONTEXT = """\
**Plan checkpoint**: Where a plan is written, before any code.

**Widget**: one thing, the first way it is spelled.

**WIDGET**: the same thing, spelled the other way.

- **Gizmo**: a thing, but written as a bullet rather than its own entry.

**Sprocket** is a thing too, but this line names it with no colon.

See **Cog**: a part, but named only in the middle of a line.

**Pull Request**: a thing opened on GitHub, spelled with different case.
"""


def test_every_factory_class_has_one_context_entry_or_a_stated_exclusion():
    # The real tree: no class turns up a problem, and no exclusion is stale.
    real_ttl = VOCABULARY.read_text()
    real_context = CONTEXT.read_text()
    assert class_headword_problems(real_ttl, real_context, EXCLUSIONS) == []
    assert exclusion_problems(real_ttl, real_context, EXCLUSIONS) == []

    # An inline graph, driven with no exclusions, pins what each near-miss
    # produces, and that CaseInsensitive and ex:Other raise no problem.
    assert class_headword_problems(_INLINE_TTL, _INLINE_CONTEXT, {}) == [
        "BulletColon: label 'gizmo' matches no CONTEXT.md headword",
        "MidLine: label 'cog' matches no CONTEXT.md headword",
        "NoColon: label 'sprocket' matches no CONTEXT.md headword",
        "NoLabel: no rdfs:label",
        "PrefixOnly: label 'plan' matches no CONTEXT.md headword",
        "TwoCase: label 'widget' matches 2 CONTEXT.md headwords: ['WIDGET', 'Widget']",
    ]

    # Three exclusion problems: a name with no class, a class with a blank
    # reason, and a class an operator excluded despite its matching label.
    inline_exclusions = {
        "GhostClass": "not a declared class at all",
        "BulletColon": "",
        "CaseInsensitive": "excluded even though its label matches",
    }
    assert exclusion_problems(_INLINE_TTL, _INLINE_CONTEXT, inline_exclusions) == [
        "GhostClass: exclusion names no declared class",
        "BulletColon: exclusion reason is blank",
        "CaseInsensitive: exclusion's class has a label equal to a headword "
        "'pull request'",
    ]


def test_the_seven_classes_with_an_entry_carry_its_headword_as_label():
    context_text = CONTEXT.read_text()
    heads = headwords(context_text)
    classes = ontology_classes(VOCABULARY.read_text())
    for name, headword in SEVEN_HEADWORDS.items():
        assert headword in heads, f"{headword!r} is no longer a CONTEXT.md headword"
        label = classes.get(name)
        assert label is not None, f"factory:{name} carries no rdfs:label"
        assert label.casefold() == headword.casefold(), (
            f"factory:{name}'s label {label!r} does not match its headword {headword!r}"
        )


def test_no_class_with_an_entry_restates_it_in_a_comment():
    graph = rdflib.Graph().parse(VOCABULARY, format="turtle")
    heads_folded = {h.casefold() for h in headwords(CONTEXT.read_text())}
    offenders = []
    for s in graph.subjects(rdflib.RDF.type, rdflib.OWL.Class):
        if not str(s).startswith(NS):
            continue
        label = graph.value(s, rdflib.RDFS.label)
        if label is None or str(label).casefold() not in heads_folded:
            continue
        if graph.value(s, rdflib.RDFS.comment) is not None:
            offenders.append(str(s).removeprefix(NS))
    assert not offenders, (
        f"classes with a CONTEXT.md entry that still carry a comment: "
        f"{sorted(offenders)}"
    )
