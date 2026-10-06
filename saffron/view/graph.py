"""The second projection, read-only, built for `saffron serve` (ADR 9).

Q4's `saffron/projection.py` keeps only ended, attributable tasks. This
module states the run record as it stands right now: every batch, run,
task, phase and attempt the ledger holds, including a task still in
flight. `SA-0216` adds gate results, diffs and findings to the same
`build`. `SA-0217` serves the pages this feeds.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from saffron.projection import DATA_NS, DEFAULT_SHAPES, NS, VOCABULARY

_ROOT = Path(__file__).resolve().parent.parent.parent
_VENDOR_DIR = _ROOT / "ontology" / "vendor"

_SHACL_NS = "http://www.w3.org/ns/shacl#"
_PROV_NS = "http://www.w3.org/ns/prov#"
_RDFS_NS = "http://www.w3.org/2000/01/rdf-schema#"

_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass(frozen=True)
class LeftOut:
    """A task the graph states nothing about, and why."""

    task_id: int
    spec_id: str
    reason: str


@dataclass(frozen=True)
class ViewGraph:
    """What one `build` call found: the serialized graph, and every task
    it left out."""

    turtle: bytes
    left_out: list[LeftOut]


class ViewGraphError(Exception):
    """The graph failed `shapes_path`. The message is pyshacl's own report."""


def open_read_only(path: Path) -> sqlite3.Connection:
    """A connection on `path` that cannot write, named by URI. This module
    reads the file. It does not own the file's schema."""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _sh_in_by_path(shapes_path: Path, path: str) -> frozenset[str]:
    """The `sh:in` of every property shape whose `sh:path` is `path`."""
    import rdflib
    import rdflib.collection

    g = rdflib.Graph().parse(shapes_path, format="turtle")
    sh_in = rdflib.URIRef(f"{_SHACL_NS}in")
    sh_path = rdflib.URIRef(f"{_SHACL_NS}path")
    accepted: set[str] = set()
    for shape in g.subjects(sh_path, rdflib.URIRef(path)):
        for lst in g.objects(shape, sh_in):
            for node in rdflib.collection.Collection(g, lst):
                accepted.add(str(node))
    return frozenset(accepted)


def _sh_in_by_target_class(shapes_path: Path, target_class: str) -> frozenset[str]:
    """The `sh:in` of the node shape whose `sh:targetClass` is `target_class`."""
    import rdflib
    import rdflib.collection

    g = rdflib.Graph().parse(shapes_path, format="turtle")
    sh_in = rdflib.URIRef(f"{_SHACL_NS}in")
    sh_target_class = rdflib.URIRef(f"{_SHACL_NS}targetClass")
    accepted: set[str] = set()
    for shape in g.subjects(sh_target_class, rdflib.URIRef(target_class)):
        for lst in g.objects(shape, sh_in):
            for node in rdflib.collection.Collection(g, lst):
                accepted.add(str(node))
    return frozenset(accepted)


def _decimal(value: float):
    import rdflib

    return rdflib.Literal(Decimal(str(value)), datatype=rdflib.namespace.XSD.decimal)


def _utc_time(text: str):
    import rdflib

    when = datetime.strptime(text, _TIME_FORMAT).replace(tzinfo=UTC)
    return rdflib.Literal(when, datatype=rdflib.namespace.XSD.dateTime)


def build(db: sqlite3.Connection, *, shapes_path: Path = DEFAULT_SHAPES) -> ViewGraph:
    """State every batch, run, task, phase and attempt `db` holds, as
    `DATA_NS` nodes, and validate the result against `shapes_path`. A task
    at an unknown state or risk is left out with a reason, and the rest
    are still stated."""
    import rdflib

    factory = rdflib.Namespace(NS)
    data = rdflib.Namespace(DATA_NS)
    prov = rdflib.Namespace(_PROV_NS)
    rdfs = rdflib.Namespace(_RDFS_NS)
    xsd = rdflib.namespace.XSD

    end_states = _sh_in_by_path(shapes_path, f"{NS}endedInState")
    in_flight_states = _sh_in_by_target_class(shapes_path, f"{NS}InFlightState")
    risks = _sh_in_by_path(shapes_path, f"{NS}riskTier")

    g = rdflib.Graph()

    for row in db.execute("SELECT * FROM batches ORDER BY batch_id").fetchall():
        batch_node = data[f"batch-{row['batch_id']}"]
        g.add((batch_node, rdflib.RDF.type, factory.Batch))
        g.add((batch_node, factory.budgetUsd, _decimal(row["budget_usd"])))
        g.add((batch_node, prov.startedAtTime, _utc_time(row["started_at"])))
        if row["spent_usd_est"] is not None:
            g.add((batch_node, factory.spentUsdEst, _decimal(row["spent_usd_est"])))
        if row["ended_at"] is not None:
            g.add((batch_node, prov.endedAtTime, _utc_time(row["ended_at"])))
        if row["status"] is not None:
            g.add((batch_node, factory.endedBecause, factory[row["status"]]))

    for row in db.execute("SELECT * FROM runs ORDER BY run_id").fetchall():
        run_node = data[f"run-{row['run_id']}"]
        g.add((run_node, rdflib.RDF.type, factory.Run))
        g.add((run_node, factory.baseSha, rdflib.Literal(row["base_sha"])))
        if row["batch_id"] is not None:
            g.add((run_node, prov.wasInformedBy, data[f"batch-{row['batch_id']}"]))

    left_out: list[LeftOut] = []
    task_nodes: dict[int, rdflib.URIRef] = {}

    for row in db.execute("SELECT * FROM tasks ORDER BY task_id").fetchall():
        state_term = f"{NS}{row['state']}"
        is_end = state_term in end_states
        is_in_flight = state_term in in_flight_states
        if not is_end and not is_in_flight:
            left_out.append(LeftOut(row["task_id"], row["spec_id"], "unknown_state"))
            continue
        risk_term = f"{NS}{row['risk']}"
        if risk_term not in risks:
            left_out.append(LeftOut(row["task_id"], row["spec_id"], "unknown_risk"))
            continue

        task_node = data[f"task-{row['task_id']}"]
        g.add((task_node, rdflib.RDF.type, factory.Task))
        g.add((task_node, factory.inState, factory[row["state"]]))
        if is_end:
            g.add((task_node, factory.endedInState, factory[row["state"]]))
        g.add((task_node, factory.riskTier, factory[row["risk"]]))
        g.add((task_node, rdfs.label, rdflib.Literal(row["spec_id"])))
        g.add((task_node, prov.wasInformedBy, data[f"run-{row['run_id']}"]))
        if row["pr_url"] is not None:
            g.add((task_node, rdfs.seeAlso, rdflib.URIRef(row["pr_url"])))
        task_nodes[row["task_id"]] = task_node

    phases_seen: set[tuple[int, str]] = set()
    for row in db.execute("SELECT * FROM attempts ORDER BY attempt_id").fetchall():
        task_node = task_nodes.get(row["task_id"])
        if task_node is None:
            continue
        phase_key = (row["task_id"], row["phase"])
        phase_node = data[f"phase-{row['task_id']}-{row['phase']}"]
        if phase_key not in phases_seen:
            g.add((phase_node, rdflib.RDF.type, factory.Phase))
            g.add((phase_node, rdfs.label, rdflib.Literal(row["phase"])))
            g.add((phase_node, prov.wasInformedBy, task_node))
            phases_seen.add(phase_key)

        attempt_node = data[f"attempt-{row['attempt_id']}"]
        g.add((attempt_node, rdflib.RDF.type, factory.Attempt))
        g.add((attempt_node, factory.withinPhase, phase_node))
        g.add((attempt_node, factory.n, rdflib.Literal(row["n"], datatype=xsd.integer)))
        g.add((attempt_node, prov.startedAtTime, _utc_time(row["started_at"])))
        if row["num_turns"] is not None:
            g.add(
                (
                    attempt_node,
                    factory.numTurns,
                    rdflib.Literal(row["num_turns"], datatype=xsd.integer),
                )
            )
        if row["cost_usd_est"] is not None:
            g.add((attempt_node, factory.costUsdEst, _decimal(row["cost_usd_est"])))
        if row["ended_at"] is not None:
            g.add((attempt_node, prov.endedAtTime, _utc_time(row["ended_at"])))

    _validate(g, shapes_path)
    return ViewGraph(
        turtle=g.serialize(format="turtle").encode("utf-8"), left_out=left_out
    )


def _validate(graph, shapes_path: Path) -> None:
    import pyshacl
    import rdflib

    data_graph = rdflib.Graph()
    data_graph += graph
    data_graph.parse(VOCABULARY, format="turtle")
    for vendor_path in sorted(_VENDOR_DIR.glob("*.ttl")):
        data_graph.parse(vendor_path, format="turtle")

    shapes_graph = rdflib.Graph().parse(shapes_path, format="turtle")
    conforms, _, report_text = pyshacl.validate(
        data_graph, shacl_graph=shapes_graph, advanced=True
    )
    if not conforms:
        raise ViewGraphError(report_text)
