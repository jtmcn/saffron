"""Where the vocabulary and the shipped code both close a set, they close it the same.

Two sets are closed in both places. `Severity` is a `Literal` in
`saffron/agents/findings.py`, so a severity declared in the vocabulary that the
code cannot represent is a run record that cannot be written — pydantic rejects
it. `BatchStopReason` is closed *twice* on the code side — a `Literal` in
`saffron/batch.py` and a SQL `CHECK` on `batches.status` — and both are checked,
because they can drift from each other as easily as from the vocabulary.

Core gates were once excluded here on the grounds that they "have no Python
registry (they are discovered)". That was true of the registry and false of the
set: `saffron/gates/core/` is a directory, and reading it is what the last test
below does. The sentence cost three pull requests with `witness` built and
undeclared (docs/BACKLOG.md item 72). The terminal states the code names do
still fall through to a documented default rather than a raise, so they are not
a closed set on the code side and are not checked here.

This reads the code; it does not make the code read the ontology. Nothing under
`saffron/` imports a graph library or the generator, and `pyproject.toml` says so.
"""

import re
from typing import get_args

import rdflib
from ontology_paths import NS, ONTOLOGY, VOCABULARY

from saffron.agents.findings import Severity
from saffron.batch import StopReason
from saffron.ledger import SCHEMA


def _declared(class_name: str) -> set[str]:
    graph = rdflib.Graph().parse(VOCABULARY, format="turtle")
    return {
        str(s).removeprefix(NS)
        for s in graph.subjects(rdflib.RDF.type, rdflib.URIRef(f"{NS}{class_name}"))
    }


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


def test_the_stop_reasons_the_loop_can_return_are_the_ones_the_vocabulary_declares():
    """`batch.StopReason` is what `run_batch` returns and what the command maps
    to an exit code. A fifth reason here that the vocabulary does not know is a
    night whose ending has no name in `CONTEXT.md`."""
    assert _declared("BatchStopReason") == set(get_args(StopReason)), (
        "saffron:BatchStopReason and saffron/batch.py disagree. The generator "
        "cannot reach Python, so this is a hand edit in batch.py."
    )


def test_the_stop_reasons_the_ledger_will_store_are_the_ones_the_vocabulary_declares():
    """The `CHECK` on `batches.status` is the only thing that refuses a bad
    write, and it is where this set used to live *alone* — no vocabulary entry,
    no `CONTEXT.md` line, nothing to stop a fifth reason being added in SQL and
    nowhere else (backlog item 65).

    Parsed from `SCHEMA` rather than restated: a copy of the four here would
    drift from the constraint exactly the way the constraint drifted from the
    vocabulary."""
    found = re.search(r"status\s+TEXT CHECK \(status IN \(([^)]*)\)\)", SCHEMA)
    assert found is not None, (
        "no CHECK on batches.status in SCHEMA — if the constraint moved or was "
        "dropped, this test is the thing that noticed"
    )
    in_sql = set(re.findall(r"'([A-Z_]+)'", found.group(1)))
    assert in_sql == _declared("BatchStopReason"), (
        "saffron:BatchStopReason and the CHECK on batches.status disagree"
    )


# `saffron/gates/core/` has no registry object — `session._suite` imports the
# gates by name — but the directory is a closed set all the same. Treating it as
# one is what this file previously declined to do, and `witness` shipped built
# and undeclared for three pull requests as a result (docs/BACKLOG.md item 72).
CORE_GATES = ONTOLOGY.parent / "saffron" / "gates" / "core"


def _core_gate_modules() -> set[str]:
    return {p.stem for p in CORE_GATES.glob("*.py") if not p.stem.startswith("_")}


def test_every_core_gate_that_exists_is_declared_in_the_vocabulary():
    """A core gate that is built and undeclared is invisible to its own guard.

    Subset, not equality: `secrets` is declared and not yet built, which is the
    ordinary direction — a gate specified before it exists. The direction this
    rejects is the other one.
    """
    built = _core_gate_modules()
    # A glob that finds nothing would satisfy the subset assertion trivially,
    # which is the exact failure mode this test exists to end.
    assert built, (
        f"no core gate modules under {CORE_GATES} — if the package moved, this "
        "assertion is the thing that noticed, and everything below it was "
        "about to pass by measuring nothing"
    )
    undeclared = sorted(built - _declared("CoreGate"))
    assert not undeclared, (
        f"core gates that exist and the vocabulary does not declare: "
        f"{undeclared}. A gate absent from ontology/saffron.ttl is absent from "
        "vocabulary.subjects(rdf:type, saffron:CoreGate), so test_shapes walks "
        "past it and CoreGateShape's sh:in does not reject it — the guard "
        "CLAUDE.md promises cannot fire for precisely the case it exists to "
        "catch. Declare the gate, give it a blocking level in "
        "saffron:CoreGateBlockingShape (or saffron:SizeTierShape if a risk tier "
        "moves it), and run `uv run python -m ontology.render`."
    )
