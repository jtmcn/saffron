"""`ontology/factory.ttl` exists, is valid Turtle, and parses offline."""

import re
import subprocess

import pyoxigraph as ox
import pytest
from ontology_paths import NS, ONTOLOGY, VENDOR, VOCABULARY


def test_vocabulary_parses_under_pyoxigraph():
    store = ox.Store()
    store.bulk_load(path=str(VOCABULARY), format=ox.RdfFormat.TURTLE)
    assert len(store) > 0


@pytest.mark.parametrize("path", VENDOR, ids=lambda p: p.name)
def test_vendored_vocabularies_parse(path):
    """PROV-O and EARL are read from disk. The cell has no default route (§5.1),
    so a vocabulary that had to be dereferenced could not be validated at all."""
    store = ox.Store()
    store.bulk_load(path=str(path), format=ox.RdfFormat.TURTLE)
    assert len(store) > 0


@pytest.mark.parametrize(
    "term,parent",
    [
        ("Batch", "http://www.w3.org/ns/prov#Activity"),
        ("Attempt", "http://www.w3.org/ns/prov#Activity"),
        ("GateSuite", "http://www.w3.org/ns/prov#Activity"),
        ("Spec", "http://www.w3.org/ns/prov#Entity"),
        ("PullRequest", "http://www.w3.org/ns/prov#Entity"),
        ("Plan", "http://www.w3.org/ns/prov#Plan"),
        ("CriticLens", "http://www.w3.org/ns/prov#SoftwareAgent"),
        ("Operator", "http://www.w3.org/ns/prov#Person"),
        ("Delegate", "http://www.w3.org/ns/prov#SoftwareAgent"),
        ("GateResult", "http://www.w3.org/ns/earl#Assertion"),
        ("Finding", "http://www.w3.org/ns/earl#Assertion"),
        ("AcceptanceCriterion", "http://www.w3.org/ns/earl#TestCriterion"),
        ("Diff", "http://www.w3.org/ns/earl#TestSubject"),
    ],
)
def test_terms_align_with_the_vendored_vocabularies(store, term, parent):
    """Alignment is one of the three ways a term earns its place (§4.6): a
    subclass of a term PROV or EARL already defines works in external tooling.
    A subclass of nothing is a bespoke schema wearing an RDF syntax."""
    ask = f"ASK {{ <{NS}{term}> <http://www.w3.org/2000/01/rdf-schema#subClassOf> <{parent}> }}"
    assert store.query(ask)


def test_gate_result_and_finding_are_one_shape(store):
    """§4.6's first criticism, as a property of the vocabulary rather than prose:
    a mypy failure and a blocker on an acceptance criterion are both an
    assertion, by an assertor, about a subject, with an outcome."""
    rows = list(
        store.query(f"""
        PREFIX earl: <http://www.w3.org/ns/earl#>
        SELECT ?a WHERE {{
          ?a a ?kind ; earl:assertedBy ?who ; earl:subject ?what ;
             earl:result/earl:outcome ?outcome .
          VALUES ?kind {{ <{NS}GateResult> <{NS}Finding> }}
        }}""")
    )
    kinds = {str(r[0]) for r in rows}
    assert len(kinds) >= 2, "both kinds must occur in the fixture under one shape"


def test_rationale_is_within_its_cap_and_covers_every_query():
    """The artifact the whole spec exists to produce, and until now the only one
    nothing checked — deleting it left the suite green. Its 40-line cap is an
    acceptance criterion, and a table row per query is what makes it a challenge
    rather than an opinion."""
    from ontology_paths import ONTOLOGY, QUERIES

    rationale = (ONTOLOGY / "RATIONALE.md").read_text()
    assert len(rationale.splitlines()) <= 40
    for query in QUERIES:
        assert f"| {query.stem[:2]} " in rationale, f"no row for {query.stem}"
    assert "Bottom line" in rationale


def test_the_vocabulary_is_the_factorys_and_nothing_still_names_saffron():
    """The vocabulary describes the arrangement, not the program (CONTEXT.md
    settled naming decision 6). The old names are spelled in halves so this file
    does not find itself. `retired-by` is untouched: it is a marker in source the
    scheduler reads, not a term."""
    assert NS == "urn:software-factory:ns#"
    # No left boundary: in a literal, `\n` glues the prefix to an `n`. A prefix
    # declaration and an f-string field slipped past the letter-only form once.
    old = re.compile(
        "saffron"
        + r"\.dev"
        + "|"
        + "saffron"
        + r":(?!retired\b)[A-Za-z_{]"
        + "|"
        + r"(?i:prefix)\s+"
        + "saffron"
        + ":"
        + "|"
        + "saffron"
        + r"(-shapes)?\.ttl"
    )
    root = ONTOLOGY.parent
    listed = subprocess.run(
        ["git", "ls-files", "-z"], capture_output=True, text=True, cwd=root, check=True
    ).stdout.split("\0")
    # These are history, byte-pinned to `git show <base>` by test_corpus.py's
    # reproduce-from-git test: renaming what they quote would falsify the
    # record and change what the lenses were actually shown.
    frozen_fixture_input = re.compile(
        r"^docs/evidence/fixtures/[^/]+/(claude|context|spec_body)\.md$"
    )
    stale = []
    for name in filter(None, listed):
        if frozen_fixture_input.match(name):
            continue
        try:
            text = (root / name).read_text()
        except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
            continue
        stale += [f"{name}: {m.group()}" for m in old.finditer(text)]
    assert not stale, stale[:20]
