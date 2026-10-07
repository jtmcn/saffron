"""Tests for `saffron.view.graph`.

Every test imports `saffron.view.graph` inside its own body, never at
module scope. A reverted run's missing module then reads as a `skip`
for the whole file, rather than a collection error (`DESIGN.md` Appendix H).
"""

from __future__ import annotations

import sqlite3
import time
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import rdflib

from saffron.ledger import Ledger
from saffron.projection import DATA_NS, DEFAULT_SHAPES, NS

DATA = DATA_NS
FACTORY = NS
PROV = "http://www.w3.org/ns/prov#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
EARL = "http://www.w3.org/ns/earl#"


def _ledger(tmp_path: Path) -> tuple[Ledger, int]:
    ledger = Ledger(tmp_path / "ledger.db")
    repo_id = ledger.upsert_repo("r", "origin", str(tmp_path / "mirror"), None)
    return ledger, repo_id


def _set_task(ledger: Ledger, task_id: int, **columns: object) -> None:
    names = ", ".join(f"{name} = ?" for name in columns)
    ledger._db.execute(
        f"UPDATE tasks SET {names} WHERE task_id = ?",
        (*columns.values(), task_id),
    )
    ledger._db.commit()


def _parse(view) -> rdflib.Graph:
    import rdflib

    g = rdflib.Graph()
    g.parse(data=view.turtle, format="turtle")
    return g


def _expected_utc(text: str):
    from datetime import UTC, datetime

    return datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)


def _triples(g: rdflib.Graph, s=None, p=None, o=None) -> set:
    import rdflib

    def ref(x):
        if x is None:
            return None
        return rdflib.URIRef(x)

    return set(g.triples((ref(s), ref(p), ref(o))))


def _absent(g: rdflib.Graph, node: str) -> None:
    """`node` names nothing, as subject or as object. A left-out task's
    own nodes must pass this check."""
    uri = _uri(node)
    assert not list(g.triples((uri, None, None)))
    assert not list(g.triples((None, None, uri)))


def test_an_in_flight_task_is_stated_with_its_state(tmp_path: Path) -> None:
    from saffron.view.graph import build, open_read_only

    ledger, repo_id = _ledger(tmp_path)
    run_id = ledger.create_run(repo_id, "base1")
    states = [
        "DRAFT",
        "QUEUED",
        "DIAGNOSING",
        "IMPLEMENTING",
        "GATING",
        "REPAIRING",
        "REVIEWING",
        "REBUTTING",
    ]
    task_ids = {}
    spec_ids = {}
    for i, state in enumerate(states):
        spec_id = f"SA-{i:04d}"
        task_id = ledger.create_task(run_id, spec_id, f"sha{i}", f"b{i}")
        _set_task(ledger, task_id, state=state)
        task_ids[state] = task_id
        spec_ids[state] = spec_id
    _set_task(ledger, task_ids["REPAIRING"], pr_url="https://example.com/pr/9")
    _set_task(ledger, task_ids["GATING"], risk="elevated")
    ledger.close()

    conn = open_read_only(tmp_path / "ledger.db")
    view = build(conn)
    assert view.left_out == []
    g = _parse(view)

    run_node = f"{DATA}run-{run_id}"
    for state, task_id in task_ids.items():
        task_node = f"{DATA}task-{task_id}"
        assert _triples(g, task_node, RDF_TYPE, f"{FACTORY}Task")
        assert _triples(g, task_node, f"{FACTORY}inState", f"{FACTORY}{state}")
        assert not _triples(g, task_node, f"{FACTORY}endedInState")
        risk = "elevated" if state == "GATING" else "standard"
        assert _triples(g, task_node, f"{FACTORY}riskTier", f"{FACTORY}{risk}")
        label = _literal(g, task_node, f"{RDFS}label")
        assert label.toPython() == spec_ids[state]
        assert _triples(g, task_node, f"{PROV}wasInformedBy", run_node)
        if state == "REPAIRING":
            assert _triples(g, task_node, f"{RDFS}seeAlso", "https://example.com/pr/9")
        else:
            assert not _triples(g, task_node, f"{RDFS}seeAlso")


def test_an_ended_task_states_both_its_state_and_its_end(tmp_path: Path) -> None:
    from saffron.view.graph import build, open_read_only

    ledger, repo_id = _ledger(tmp_path)
    run_id = ledger.create_run(repo_id, "base1")
    end_states = [
        "SCOPE_REVIEW",
        "PLAN_REJECTED",
        "EXHAUSTED",
        "READY_FOR_REVIEW",
        "MERGE_FAILED",
        "PREFLIGHT_FAILED",
        "NOT_IMPLEMENTED",
        "GATE_ERROR",
        "RATE_LIMITED",
        "SPEC_WITHHELD",
        "PROVIDER_UNREACHABLE",
        "APPROVED",
        "CHANGES_REQUESTED",
        "REJECTED",
        "MERGED",
        "ORPHANED",
        "MERGE_TRAIN",
    ]
    task_ids = {}
    for i, state in enumerate(end_states):
        task_id = ledger.create_task(run_id, f"SA-{i:04d}", f"sha{i}", f"b{i}")
        _set_task(ledger, task_id, state=state, risk="elevated")
        task_ids[state] = task_id
    extra = ledger.create_task(run_id, "SA-9999", "shax", "bx")
    _set_task(ledger, extra, state="MERGED", risk="standard")
    ledger.close()

    conn = open_read_only(tmp_path / "ledger.db")
    view = build(conn)
    assert view.left_out == []
    g = _parse(view)

    for state, task_id in task_ids.items():
        task_node = f"{DATA}task-{task_id}"
        assert _triples(g, task_node, f"{FACTORY}inState", f"{FACTORY}{state}")
        assert _triples(g, task_node, f"{FACTORY}endedInState", f"{FACTORY}{state}")
        assert _triples(g, task_node, f"{FACTORY}riskTier", f"{FACTORY}elevated")

    extra_node = f"{DATA}task-{extra}"
    assert _triples(g, extra_node, f"{FACTORY}inState", f"{FACTORY}MERGED")
    assert _triples(g, extra_node, f"{FACTORY}endedInState", f"{FACTORY}MERGED")
    assert _triples(g, extra_node, f"{FACTORY}riskTier", f"{FACTORY}standard")


def test_a_task_whose_run_has_no_batch_is_still_stated(tmp_path: Path) -> None:
    from saffron.view.graph import build, open_read_only

    ledger, repo_id = _ledger(tmp_path)
    # Throwaway rows, enough that a batch, its run and its task never share
    # an id by accident (CLAUDE.md's notes on this spec).
    for _n in range(2):
        throwaway_batch = ledger.create_batch(1.0)
        ledger.close_batch(throwaway_batch, "DRAINED")
    throwaway_run = ledger.create_run(repo_id, "throwaway")
    for n in range(3):
        throwaway_task = ledger.create_task(
            throwaway_run, f"SA-000{n}", f"shat{n}", f"bt{n}"
        )
        _set_task(ledger, throwaway_task, state="DRAFT")

    batch_id = ledger.create_batch(20.0)
    batched_run = ledger.create_run(repo_id, "based", batch_id=batch_id)
    batched_task = ledger.create_task(batched_run, "SA-0001", "sha1", "b1")
    _set_task(ledger, batched_task, state="DRAFT")

    unbatched_run = ledger.create_run(repo_id, "baseu")
    unbatched_task = ledger.create_task(unbatched_run, "SA-0002", "sha2", "b2")
    _set_task(ledger, unbatched_task, state="DRAFT")
    ledger.close()

    assert batch_id != batched_run
    assert batched_run != batched_task
    assert unbatched_run != unbatched_task

    conn = open_read_only(tmp_path / "ledger.db")
    view = build(conn)
    g = _parse(view)

    batch_node = f"{DATA}batch-{batch_id}"
    batched_run_node = f"{DATA}run-{batched_run}"
    unbatched_run_node = f"{DATA}run-{unbatched_run}"

    assert _triples(g, batched_run_node, RDF_TYPE, f"{FACTORY}Run")
    assert _triples(g, batched_run_node, f"{PROV}wasInformedBy", batch_node)
    assert not _triples(g, unbatched_run_node, f"{PROV}wasInformedBy")
    assert _literal(g, batched_run_node, f"{FACTORY}baseSha").toPython() == "based"
    assert _literal(g, unbatched_run_node, f"{FACTORY}baseSha").toPython() == "baseu"

    batched_task_node = f"{DATA}task-{batched_task}"
    unbatched_task_node = f"{DATA}task-{unbatched_task}"
    assert _triples(g, batched_task_node, f"{PROV}wasInformedBy", batched_run_node)
    assert _triples(g, unbatched_task_node, f"{PROV}wasInformedBy", unbatched_run_node)


def test_a_batch_states_its_budget_spend_window_and_stop_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from saffron.view.graph import build, open_read_only

    ledger, repo_id = _ledger(tmp_path)
    reasons = ["DRAINED", "BUDGET", "UNTIL", "INFRASTRUCTURE", "INCOMPLETE"]
    closed_ids = {}
    for i, reason in enumerate(reasons):
        batch_id = ledger.create_batch(10.0 + i)
        ledger.close_batch(batch_id, reason)
        ledger._db.execute(
            "UPDATE batches SET spent_usd_est = ? WHERE batch_id = ?",
            (12.4 + i, batch_id),
        )
        ledger._db.commit()
        closed_ids[reason] = batch_id
    running_id = ledger.create_batch(99.0)
    raw_times = {}
    for batch_id in closed_ids.values():
        row = ledger._db.execute(
            "SELECT started_at, ended_at FROM batches WHERE batch_id = ?", (batch_id,)
        ).fetchone()
        raw_times[batch_id] = (row["started_at"], row["ended_at"])
    ledger.close()

    monkeypatch.setenv("TZ", "JST-9")
    time.tzset()
    try:
        conn = open_read_only(tmp_path / "ledger.db")
        view = build(conn)
    finally:
        monkeypatch.delenv("TZ", raising=False)
        time.tzset()

    g = _parse(view)

    for i, (reason, batch_id) in enumerate(closed_ids.items()):
        batch_node = f"{DATA}batch-{batch_id}"
        budget = _literal(g, batch_node, f"{FACTORY}budgetUsd")
        assert budget.toPython() == Decimal(str(10.0 + i))
        assert str(budget.datatype) == "http://www.w3.org/2001/XMLSchema#decimal"
        spent = _literal(g, batch_node, f"{FACTORY}spentUsdEst")
        assert spent.toPython() == Decimal(str(12.4 + i))
        started_text, ended_text = raw_times[batch_id]
        started = _literal(g, batch_node, f"{PROV}startedAtTime")
        assert started.toPython() == _expected_utc(started_text)
        ended = _literal(g, batch_node, f"{PROV}endedAtTime")
        assert ended.toPython() == _expected_utc(ended_text)
        assert _triples(g, batch_node, RDF_TYPE, f"{FACTORY}Batch")
        assert _triples(g, batch_node, f"{FACTORY}endedBecause", f"{FACTORY}{reason}")

    running_node = f"{DATA}batch-{running_id}"
    assert not _triples(g, running_node, f"{FACTORY}spentUsdEst")
    assert not _triples(g, running_node, f"{PROV}endedAtTime")
    assert not _triples(g, running_node, f"{FACTORY}endedBecause")


def _uri(value: str) -> rdflib.URIRef:
    import rdflib

    return rdflib.URIRef(value)


def _literal(g: rdflib.Graph, subject: str, predicate: str) -> rdflib.Literal:
    import rdflib

    found = next(g.objects(_uri(subject), _uri(predicate)))
    assert isinstance(found, rdflib.Literal)
    return found


def test_an_attempt_states_its_phase_number_turns_cost_and_times(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from saffron.view.graph import build, open_read_only

    ledger, repo_id = _ledger(tmp_path)
    run_id = ledger.create_run(repo_id, "base1")
    throwaway_task = ledger.create_task(run_id, "SA-0000", "shax", "bx")
    _set_task(ledger, throwaway_task, state="DRAFT")
    task_id = ledger.create_task(run_id, "SA-0001", "sha1", "b1")
    _set_task(ledger, task_id, state="REVIEWING")

    implement_attempt = ledger.open_attempt(task_id, "IMPLEMENTING")
    ledger.close_attempt(
        implement_attempt,
        session_id=None,
        subtype="x",
        terminal_reason=None,
        num_turns=5,
        cost_usd_est=0.1,
    )
    review_attempt = ledger.open_attempt(task_id, "REVIEWING")
    second_implement = ledger.open_attempt(task_id, "IMPLEMENTING")
    raw_started = ledger._db.execute(
        "SELECT started_at FROM attempts WHERE attempt_id = ?", (implement_attempt,)
    ).fetchone()["started_at"]
    ledger.close()

    monkeypatch.setenv("TZ", "JST-9")
    time.tzset()
    try:
        conn = open_read_only(tmp_path / "ledger.db")
        view = build(conn)
    finally:
        monkeypatch.delenv("TZ", raising=False)
        time.tzset()

    g = _parse(view)
    task_node = f"{DATA}task-{task_id}"
    implement_phase = f"{DATA}phase-{task_id}-IMPLEMENTING"
    review_phase = f"{DATA}phase-{task_id}-REVIEWING"
    assert _triples(g, implement_phase, RDF_TYPE, f"{FACTORY}Phase")
    assert _triples(g, implement_phase, f"{PROV}wasInformedBy", task_node)
    assert _triples(g, review_phase, f"{PROV}wasInformedBy", task_node)
    implement_label = _literal(g, implement_phase, f"{RDFS}label")
    assert implement_label.toPython() == "IMPLEMENTING"
    review_label = _literal(g, review_phase, f"{RDFS}label")
    assert review_label.toPython() == "REVIEWING"

    implement_node = f"{DATA}attempt-{implement_attempt}"
    review_node = f"{DATA}attempt-{review_attempt}"
    second_node = f"{DATA}attempt-{second_implement}"

    assert _triples(g, implement_node, RDF_TYPE, f"{FACTORY}Attempt")
    assert _triples(g, implement_node, f"{FACTORY}withinPhase", implement_phase)
    assert _triples(g, second_node, f"{FACTORY}withinPhase", implement_phase)
    assert _triples(g, review_node, f"{FACTORY}withinPhase", review_phase)

    n_1 = _literal(g, implement_node, f"{FACTORY}n")
    assert n_1.toPython() == 1
    n_review = _literal(g, review_node, f"{FACTORY}n")
    assert n_review.toPython() == 1
    n_second = _literal(g, second_node, f"{FACTORY}n")
    assert n_second.toPython() == 2

    cost = _literal(g, implement_node, f"{FACTORY}costUsdEst")
    assert cost.toPython() == Decimal("0.1")
    turns = _literal(g, implement_node, f"{FACTORY}numTurns")
    assert turns.toPython() == 5
    assert _triples(g, implement_node, f"{PROV}endedAtTime")
    assert not _triples(g, review_node, f"{PROV}endedAtTime")
    assert not _triples(g, review_node, f"{FACTORY}costUsdEst")
    assert not _triples(g, review_node, f"{FACTORY}numTurns")
    started = _literal(g, implement_node, f"{PROV}startedAtTime")
    assert started.toPython() == _expected_utc(raw_started)


def test_a_task_in_an_unknown_state_is_left_out_and_the_rest_are_stated(
    tmp_path: Path,
) -> None:
    from saffron.view.graph import LeftOut, build, open_read_only

    ledger, repo_id = _ledger(tmp_path)
    run_id = ledger.create_run(repo_id, "base1")
    unknown_task = ledger.create_task(run_id, "SA-0001", "sha1", "b1")
    _set_task(ledger, unknown_task, state="PAUSED")
    unknown_attempt = ledger.open_attempt(unknown_task, "PAUSED")
    known_task = ledger.create_task(run_id, "SA-0002", "sha2", "b2")
    _set_task(ledger, known_task, state="IMPLEMENTING")
    second_unknown = ledger.create_task(run_id, "SA-0003", "sha3", "b3")
    _set_task(ledger, second_unknown, state="PAUSED", risk="reckless")
    ledger.close()

    conn = open_read_only(tmp_path / "ledger.db")
    view = build(conn)
    # Keyword-built, so a swap of the dataclass's own field order cannot
    # make a wrongly bound expected value match a wrongly bound actual one.
    assert set(view.left_out) == {
        LeftOut(task_id=unknown_task, spec_id="SA-0001", reason="unknown_state"),
        LeftOut(task_id=second_unknown, spec_id="SA-0003", reason="unknown_state"),
    }

    g = _parse(view)
    unknown_node = _uri(f"{DATA}task-{unknown_task}")
    unknown_attempt_node = _uri(f"{DATA}attempt-{unknown_attempt}")
    unknown_phase_node = _uri(f"{DATA}phase-{unknown_task}-PAUSED")
    for node in (unknown_node, unknown_attempt_node, unknown_phase_node):
        assert not list(g.triples((node, None, None)))
        assert not list(g.triples((None, None, node)))

    known_node = f"{DATA}task-{known_task}"
    assert _triples(g, known_node, f"{FACTORY}inState", f"{FACTORY}IMPLEMENTING")


def test_a_task_at_an_unknown_risk_is_left_out_and_the_rest_are_stated(
    tmp_path: Path,
) -> None:
    from saffron.view.graph import LeftOut, build, open_read_only

    ledger, repo_id = _ledger(tmp_path)
    run_id = ledger.create_run(repo_id, "base1")
    unknown_task = ledger.create_task(run_id, "SA-0001", "sha1", "b1")
    _set_task(ledger, unknown_task, state="IMPLEMENTING", risk="reckless")
    unknown_attempt = ledger.open_attempt(unknown_task, "IMPLEMENTING")
    known_task = ledger.create_task(run_id, "SA-0002", "sha2", "b2")
    _set_task(ledger, known_task, state="REVIEWING")
    ledger.close()

    conn = open_read_only(tmp_path / "ledger.db")
    view = build(conn)
    assert view.left_out == [
        LeftOut(task_id=unknown_task, spec_id="SA-0001", reason="unknown_risk")
    ]
    assert view.left_out[0].task_id == unknown_task
    assert view.left_out[0].spec_id == "SA-0001"
    assert view.left_out[0].reason == "unknown_risk"

    g = _parse(view)
    unknown_node = _uri(f"{DATA}task-{unknown_task}")
    unknown_attempt_node = _uri(f"{DATA}attempt-{unknown_attempt}")
    unknown_phase_node = _uri(f"{DATA}phase-{unknown_task}-IMPLEMENTING")
    for node in (unknown_node, unknown_attempt_node, unknown_phase_node):
        assert not list(g.triples((node, None, None)))
        assert not list(g.triples((None, None, node)))

    known_node = f"{DATA}task-{known_task}"
    assert _triples(g, known_node, f"{FACTORY}inState", f"{FACTORY}REVIEWING")


def test_the_graph_passes_the_shapes(tmp_path: Path) -> None:
    from saffron.view.graph import ViewGraphError, build, open_read_only

    ledger, repo_id = _ledger(tmp_path)
    batch_id = ledger.create_batch(10.0)
    ledger.close_batch(batch_id, "DRAINED")
    ledger._db.execute(
        "UPDATE batches SET spent_usd_est = ? WHERE batch_id = ?", (5.0, batch_id)
    )
    ledger._db.commit()
    batched_run = ledger.create_run(repo_id, "base1", batch_id=batch_id)
    unbatched_run = ledger.create_run(repo_id, "base2")
    ended_task = ledger.create_task(batched_run, "SA-0001", "sha1", "b1")
    _set_task(ledger, ended_task, state="MERGED")
    in_flight_task = ledger.create_task(unbatched_run, "SA-0002", "sha2", "b2")
    _set_task(ledger, in_flight_task, state="IMPLEMENTING")
    attempt_id = ledger.open_attempt(in_flight_task, "IMPLEMENTING")
    ledger.close_attempt(
        attempt_id,
        session_id=None,
        subtype="x",
        terminal_reason=None,
        num_turns=1,
        cost_usd_est=0.5,
    )
    ledger.close()

    conn = open_read_only(tmp_path / "ledger.db")
    view = build(conn)
    assert view.left_out == []
    g = _parse(view)
    assert len(g) > 0
    # The vocabulary's own class declarations carry `factory:Task` as a
    # subject. The view graph never does, only as an object of `rdf:type`.
    assert not list(g.triples((_uri(f"{FACTORY}Task"), None, None)))

    import pyshacl
    import rdflib

    from saffron.projection import _VENDOR_DIR, VOCABULARY

    data_graph = rdflib.Graph()
    data_graph.parse(data=view.turtle, format="turtle")
    data_graph.parse(VOCABULARY, format="turtle")
    for vendor_path in sorted(_VENDOR_DIR.glob("*.ttl")):
        data_graph.parse(vendor_path, format="turtle")
    shapes_graph = rdflib.Graph().parse(DEFAULT_SHAPES, format="turtle")
    conforms, _, _ = pyshacl.validate(
        data_graph, shacl_graph=shapes_graph, advanced=True
    )
    assert conforms

    original = DEFAULT_SHAPES.read_text()
    anchor = "sh:path factory:spentUsdEst ; sh:maxCount 1 ;"
    assert original.count(anchor) == 1
    edited = original.replace(anchor, "sh:path factory:spentUsdEst ; sh:maxCount 0 ;")
    changed = sum(
        1
        for a, b in zip(original.splitlines(), edited.splitlines(), strict=True)
        if a != b
    )
    assert changed == 1

    broken_shapes = tmp_path / "broken-shapes.ttl"
    broken_shapes.write_text(edited)

    conn2 = open_read_only(tmp_path / "ledger.db")
    with pytest.raises(ViewGraphError) as excinfo:
        build(conn2, shapes_path=broken_shapes)
    assert "Conforms: False" in str(excinfo.value)


def test_the_closed_sets_are_read_from_the_shapes_it_is_given(tmp_path: Path) -> None:
    from saffron.view.graph import LeftOut, build, open_read_only

    original = DEFAULT_SHAPES.read_text()

    drop_merged = (
        "factory:CHANGES_REQUESTED factory:REJECTED factory:MERGED\n"
        "            factory:ORPHANED factory:MERGE_TRAIN )"
    )
    assert original.count(drop_merged) == 1
    edited = original.replace(
        drop_merged,
        "factory:CHANGES_REQUESTED factory:REJECTED\n            factory:ORPHANED factory:MERGE_TRAIN )",
    )

    add_paused = "factory:REVIEWING factory:REBUTTING )"
    assert edited.count(add_paused) == 1
    edited = edited.replace(
        add_paused, "factory:REVIEWING factory:REBUTTING factory:PAUSED )"
    )

    drop_class = (
        "sh:path factory:inState ; sh:maxCount 1 ; sh:class factory:TaskState ]"
    )
    assert edited.count(drop_class) == 1
    edited = edited.replace(drop_class, "sh:path factory:inState ; sh:maxCount 1 ]")

    drop_elevated = "factory:standard factory:elevated )"
    assert edited.count(drop_elevated) == 1
    edited = edited.replace(drop_elevated, "factory:standard )")

    edited_shapes = tmp_path / "edited-shapes.ttl"
    edited_shapes.write_text(edited)

    ledger, repo_id = _ledger(tmp_path)
    run_id = ledger.create_run(repo_id, "base1")
    merged_task = ledger.create_task(run_id, "SA-0001", "sha1", "b1")
    _set_task(ledger, merged_task, state="MERGED")
    elevated_exhausted = ledger.create_task(run_id, "SA-0002", "sha2", "b2")
    _set_task(ledger, elevated_exhausted, state="EXHAUSTED", risk="elevated")
    paused_task = ledger.create_task(run_id, "SA-0003", "sha3", "b3")
    _set_task(ledger, paused_task, state="PAUSED")
    ledger.close()

    conn = open_read_only(tmp_path / "ledger.db")
    view = build(conn, shapes_path=edited_shapes)

    assert set(view.left_out) == {
        LeftOut(task_id=merged_task, spec_id="SA-0001", reason="unknown_state"),
        LeftOut(task_id=elevated_exhausted, spec_id="SA-0002", reason="unknown_risk"),
    }

    g = _parse(view)
    paused_node = f"{DATA}task-{paused_task}"
    assert _triples(g, paused_node, f"{FACTORY}inState", f"{FACTORY}PAUSED")
    assert not _triples(g, paused_node, f"{FACTORY}endedInState")


def test_build_reads_a_ledger_another_connection_is_writing(tmp_path: Path) -> None:
    from saffron.view.graph import build, open_read_only

    ledger, repo_id = _ledger(tmp_path)
    run_id = ledger.create_run(repo_id, "base1")
    task_id = ledger.create_task(run_id, "SA-0001", "sha1", "b1")
    _set_task(ledger, task_id, state="DRAFT")
    ledger.close()

    db_path = tmp_path / "ledger.db"
    writer = sqlite3.connect(db_path, isolation_level=None)
    try:
        writer.execute(
            "UPDATE tasks SET state = 'IMPLEMENTING' WHERE task_id = ?", (task_id,)
        )
        writer.execute("BEGIN IMMEDIATE")
        writer.execute(
            "UPDATE tasks SET state = 'REVIEWING' WHERE task_id = ?", (task_id,)
        )

        conn = open_read_only(db_path)
        view = build(conn)
        g = _parse(view)
        task_node = f"{DATA}task-{task_id}"
        assert _triples(g, task_node, f"{FACTORY}inState", f"{FACTORY}IMPLEMENTING")
        assert not _triples(g, task_node, f"{FACTORY}inState", f"{FACTORY}REVIEWING")
    finally:
        writer.rollback()
        writer.close()


def test_build_reads_one_snapshot_while_a_writer_commits_between_its_reads(
    tmp_path: Path,
) -> None:
    from saffron.view.graph import build, open_read_only

    ledger, repo_id = _ledger(tmp_path)
    run_id = ledger.create_run(repo_id, "base1")
    task_id = ledger.create_task(run_id, "SA-0001", "sha1", "b1")
    _set_task(ledger, task_id, state="DRAFT")
    ledger.close()

    db_path = tmp_path / "ledger.db"
    writer = sqlite3.connect(db_path, isolation_level=None)
    late: list[int] = []

    def commit_between_reads(statement: str) -> None:
        # Fires as build starts reading tasks, after it has read the runs.
        if late or "FROM tasks" not in statement:
            return
        late_run = writer.execute(
            "INSERT INTO runs (repo_id, base_sha, status) VALUES (?, 'late', 'RUNNING')",
            (repo_id,),
        ).lastrowid
        assert late_run is not None
        late_task = writer.execute(
            "INSERT INTO tasks (run_id, spec_id, spec_sha, branch, state)"
            " VALUES (?, 'SA-0002', 'sha2', 'b2', 'DRAFT')",
            (late_run,),
        ).lastrowid
        assert late_task is not None
        late.append(late_task)

    conn = open_read_only(db_path)
    conn.set_trace_callback(commit_between_reads)
    try:
        view = build(conn)
    finally:
        writer.close()

    assert late, "the writer never ran"
    g = _parse(view)
    assert not _triples(g, f"{DATA}task-{late[0]}", None, None)
    assert _triples(g, f"{DATA}task-{task_id}", f"{FACTORY}inState", f"{FACTORY}DRAFT")


def test_the_connection_cannot_write(tmp_path: Path) -> None:
    from saffron.view.graph import open_read_only

    ledger, _ = _ledger(tmp_path)
    ledger.close()

    db_path = tmp_path / "ledger.db"
    conn = open_read_only(db_path)
    assert conn.row_factory is sqlite3.Row
    with pytest.raises(sqlite3.OperationalError):
        conn.execute(
            "INSERT INTO repos (name, origin, mirror_path) VALUES ('x', 'y', 'z')"
        )
    conn.close()

    missing = tmp_path / "absent.db"
    with pytest.raises(sqlite3.OperationalError):
        open_read_only(missing)
    assert not missing.exists()


def test_each_gate_status_maps_to_its_own_earl_outcome(tmp_path: Path) -> None:
    from saffron.gates.contract import GateResult, GateStatus
    from saffron.view.graph import build, open_read_only

    ledger, repo_id = _ledger(tmp_path)
    run_id = ledger.create_run(repo_id, "base1")

    # Spare baseline results, recorded first, so no gate result id below
    # equals its position.
    for i in range(3):
        ledger.record_gate_result(
            GateResult(gate="spare", status="pass", tool=f"spare {i}"),
            run_id=run_id,
        )

    task_id = ledger.create_task(run_id, "SA-0001", "sha1", "b1")
    _set_task(ledger, task_id, state="GATING")
    other_task = ledger.create_task(run_id, "SA-0002", "sha2", "b2")
    _set_task(ledger, other_task, state="GATING")

    ungated_attempt = ledger.open_attempt(task_id, "DIAGNOSING")

    gated_attempt = ledger.open_attempt(task_id, "GATING")
    status_outcome: dict[GateStatus, str] = {
        "pass": "passed",
        "fail": "failed",
        "error": "cantTell",
        "skip": "inapplicable",
    }
    result_ids: dict[str, int] = {
        status: ledger.record_gate_result(
            GateResult(gate=f"g-{status}", status=status, tool="t"),
            attempt_id=gated_attempt,
        )
        for status in status_outcome
    }
    outcome_by_status: dict[str, str] = {str(k): v for k, v in status_outcome.items()}

    second_gated_attempt = ledger.open_attempt(task_id, "GATING")
    second_result_id = ledger.record_gate_result(
        GateResult(gate="g-second", status="pass", tool="t"),
        attempt_id=second_gated_attempt,
    )

    other_attempt = ledger.open_attempt(other_task, "GATING")
    other_result_id = ledger.record_gate_result(
        GateResult(gate="g-other", status="pass", tool="t"),
        attempt_id=other_attempt,
    )

    baseline_result_id = ledger.record_gate_result(
        GateResult(gate="g-baseline", status="fail", tool="t"), run_id=run_id
    )
    ledger.close()

    conn = open_read_only(tmp_path / "ledger.db")
    view = build(conn)
    g = _parse(view)

    # An attempt with no gate result states no suite and no diff.
    _absent(g, f"{DATA}gatesuite-{ungated_attempt}")
    _absent(g, f"{DATA}diff-attempt-{ungated_attempt}")

    # A baseline result is never stated.
    _absent(g, f"{DATA}gate-result-{baseline_result_id}")

    def check(attempt_id: int, expected: dict[str, int]) -> None:
        suite_node = f"{DATA}gatesuite-{attempt_id}"
        diff_node = f"{DATA}diff-attempt-{attempt_id}"
        attempt_node = f"{DATA}attempt-{attempt_id}"
        assert _triples(g, suite_node, RDF_TYPE, f"{FACTORY}GateSuite")
        assert _triples(g, suite_node, f"{PROV}wasInformedBy", attempt_node)
        assert _triples(g, diff_node, RDF_TYPE, f"{FACTORY}Diff")
        assert _triples(g, attempt_node, f"{PROV}generated", diff_node)
        for status, result_id in expected.items():
            result_node = f"{DATA}gate-result-{result_id}"
            assert _triples(g, result_node, RDF_TYPE, f"{FACTORY}GateResult")
            assert _triples(g, result_node, f"{PROV}wasGeneratedBy", suite_node)
            assert _triples(g, result_node, f"{EARL}subject", diff_node)
            assert _triples(g, result_node, f"{EARL}mode", f"{EARL}automatic")
            outcomes = list(g.objects(_uri(result_node), _uri(f"{EARL}result")))
            assert len(outcomes) == 1
            found = set(g.objects(outcomes[0], _uri(f"{EARL}outcome")))
            assert found == {_uri(f"{EARL}{outcome_by_status[status]}")}

    check(gated_attempt, result_ids)
    check(second_gated_attempt, {"pass": second_result_id})
    check(other_attempt, {"pass": other_result_id})

    # Each result names its own attempt's suite and subject, never another's.
    first_suite = f"{DATA}gatesuite-{gated_attempt}"
    first_diff = f"{DATA}diff-attempt-{gated_attempt}"
    second_result_node = f"{DATA}gate-result-{second_result_id}"
    assert not _triples(g, second_result_node, f"{PROV}wasGeneratedBy", first_suite)
    assert not _triples(g, second_result_node, f"{EARL}subject", first_diff)
    other_result_node = f"{DATA}gate-result-{other_result_id}"
    assert not _triples(g, other_result_node, f"{EARL}subject", first_diff)
    assert not _triples(g, other_result_node, f"{PROV}wasGeneratedBy", first_suite)


def test_a_gate_result_counts_its_failures_and_states_no_line(tmp_path: Path) -> None:
    from saffron.gates.contract import Failure, GateResult
    from saffron.view.graph import build, open_read_only

    ledger, repo_id = _ledger(tmp_path)
    run_id = ledger.create_run(repo_id, "base1")
    task_id = ledger.create_task(run_id, "SA-0001", "sha1", "b1")
    _set_task(ledger, task_id, state="GATING")
    attempt_id = ledger.open_attempt(task_id, "GATING")

    fail_result_id = ledger.record_gate_result(
        GateResult(
            gate="lint",
            status="fail",
            tool="t",
            summary="zzyzx-summary-fail-9f1a",
            failures=[
                Failure(
                    file="zzyzx-file-1-c3e2.py",
                    code="ZZYZX-CODE-1-77b0",
                    message="zzyzx-message-1-1e44",
                    line=918273,
                ),
                Failure(
                    file="zzyzx-file-2-d4f3.py",
                    code="ZZYZX-CODE-2-88c1",
                    message="zzyzx-message-2-2f55",
                    line=918274,
                ),
                Failure(
                    file="zzyzx-file-3-e5a4.py",
                    code="ZZYZX-CODE-3-99d2",
                    message="zzyzx-message-3-3a66",
                    line=918275,
                ),
            ],
        ),
        attempt_id=attempt_id,
    )
    pass_result_id = ledger.record_gate_result(
        GateResult(
            gate="scope",
            status="pass",
            tool="t",
            summary="zzyzx-summary-pass-a0b1",
            failures=[],
        ),
        attempt_id=attempt_id,
    )
    ledger.close()

    conn = open_read_only(tmp_path / "ledger.db")
    view = build(conn)
    g = _parse(view)

    fail_node = f"{DATA}gate-result-{fail_result_id}"
    pass_node = f"{DATA}gate-result-{pass_result_id}"
    fail_count = _literal(g, fail_node, f"{FACTORY}failureCount")
    assert fail_count.toPython() == 3
    assert str(fail_count.datatype) == "http://www.w3.org/2001/XMLSchema#integer"
    pass_count = _literal(g, pass_node, f"{FACTORY}failureCount")
    assert pass_count.toPython() == 0

    turtle_text = view.turtle.decode("utf-8")
    sentinels = [
        "zzyzx-summary-fail-9f1a",
        "zzyzx-summary-pass-a0b1",
        "zzyzx-file-1-c3e2.py",
        "ZZYZX-CODE-1-77b0",
        "zzyzx-message-1-1e44",
        "918273",
    ]
    for sentinel in sentinels:
        assert sentinel not in turtle_text


def test_a_core_gate_is_its_vocabulary_individual_and_a_repo_gate_is_typed_by_role(
    tmp_path: Path,
) -> None:
    from saffron.gates.contract import GateResult
    from saffron.view.graph import build, open_read_only

    core_gates = [
        "scope",
        "size",
        "secrets",
        "integrity",
        "census",
        "committed",
        "criteria",
        "revert",
        "witness",
    ]
    role_gates = ["format", "lint", "types", "tests", "no-network", "coverage"]
    repo_gates = ["structure"]

    ledger, repo_id = _ledger(tmp_path)
    run_id = ledger.create_run(repo_id, "base1")
    task_id = ledger.create_task(run_id, "SA-0001", "sha1", "b1")
    _set_task(ledger, task_id, state="GATING")
    attempt_id = ledger.open_attempt(task_id, "GATING")

    result_ids: dict[str, int] = {}
    for name in [*core_gates, *role_gates, *repo_gates]:
        result_ids[name] = ledger.record_gate_result(
            GateResult(gate=name, status="pass", tool="t"), attempt_id=attempt_id
        )
    ledger.close()

    conn = open_read_only(tmp_path / "ledger.db")
    view = build(conn)
    g = _parse(view)

    for name in core_gates:
        result_node = f"{DATA}gate-result-{result_ids[name]}"
        assert _triples(g, result_node, f"{EARL}assertedBy", f"{FACTORY}{name}")
        assert not _triples(g, result_node, f"{EARL}assertedBy", f"{DATA}gate-{name}")
        _absent(g, f"{DATA}gate-{name}")

    for name in role_gates:
        result_node = f"{DATA}gate-result-{result_ids[name]}"
        gate_node = f"{DATA}gate-{name}"
        assert _triples(g, result_node, f"{EARL}assertedBy", gate_node)
        types = _triples(g, gate_node, RDF_TYPE)
        assert {o for _, _, o in types} == {_uri(f"{FACTORY}ContractGate")}
        assert _triples(g, gate_node, f"{FACTORY}role", f"{FACTORY}{name}")

    for name in repo_gates:
        result_node = f"{DATA}gate-result-{result_ids[name]}"
        gate_node = f"{DATA}gate-{name}"
        assert _triples(g, result_node, f"{EARL}assertedBy", gate_node)
        types = _triples(g, gate_node, RDF_TYPE)
        assert {o for _, _, o in types} == {_uri(f"{FACTORY}RepoDefinedGate")}
        assert not _triples(g, gate_node, f"{FACTORY}role")


def test_findings_without_a_gated_attempt_are_left_out_and_the_task_kept(
    tmp_path: Path,
) -> None:
    from saffron.agents.findings import Finding
    from saffron.gates.contract import GateResult
    from saffron.view.graph import LeftOut, build, open_read_only

    ledger, repo_id = _ledger(tmp_path)
    run_id = ledger.create_run(repo_id, "base1")

    # The task with a gated attempt is created first. A diff wrongly
    # carried over from it would then show on every later task.
    gated_task = ledger.create_task(run_id, "SA-0001", "sha1", "b1")
    _set_task(ledger, gated_task, state="GATING")
    gated_attempt = ledger.open_attempt(gated_task, "GATING")
    ledger.record_gate_result(
        GateResult(gate="scope", status="pass", tool="t"), attempt_id=gated_attempt
    )
    gated_finding_ids = ledger.record_findings(
        gated_task,
        [Finding(lens="style", severity="note", file="f", line=1, claim="c-gated")],
    )

    ungated_many_task = ledger.create_task(run_id, "SA-0002", "sha2", "b2")
    _set_task(ledger, ungated_many_task, state="REVIEWING")
    ledger.open_attempt(ungated_many_task, "REVIEWING")
    ledger.record_findings(
        ungated_many_task,
        [
            Finding(lens="style", severity="concern", file="f", line=1, claim="c2a"),
            Finding(lens="style", severity="blocker", file="f", line=2, claim="c2b"),
        ],
    )

    no_attempt_task = ledger.create_task(run_id, "SA-0003", "sha3", "b3")
    _set_task(ledger, no_attempt_task, state="REVIEWING")
    ledger.record_findings(
        no_attempt_task,
        [Finding(lens="style", severity="note", file="f", line=1, claim="c3")],
    )

    unknown_state_task = ledger.create_task(run_id, "SA-0004", "sha4", "b4")
    _set_task(ledger, unknown_state_task, state="PAUSED")
    unknown_state_attempt = ledger.open_attempt(unknown_state_task, "PAUSED")
    ledger.record_findings(
        unknown_state_task,
        [Finding(lens="style", severity="note", file="f", line=1, claim="c4")],
    )

    unknown_risk_failing_task = ledger.create_task(run_id, "SA-0005", "sha5", "b5")
    _set_task(ledger, unknown_risk_failing_task, state="GATING", risk="reckless")
    unknown_risk_attempt = ledger.open_attempt(unknown_risk_failing_task, "GATING")
    unknown_risk_result = ledger.record_gate_result(
        GateResult(gate="scope", status="fail", tool="t"),
        attempt_id=unknown_risk_attempt,
    )
    ledger.record_findings(
        unknown_risk_failing_task,
        [Finding(lens="style", severity="note", file="f", line=1, claim="c5")],
    )

    unknown_risk_known_state_task = ledger.create_task(run_id, "SA-0006", "sha6", "b6")
    _set_task(ledger, unknown_risk_known_state_task, state="REVIEWING", risk="reckless")
    unknown_risk_known_state_attempt = ledger.open_attempt(
        unknown_risk_known_state_task, "REVIEWING"
    )
    ledger.record_findings(
        unknown_risk_known_state_task,
        [Finding(lens="style", severity="note", file="f", line=1, claim="c6")],
    )

    ledger.close()

    conn = open_read_only(tmp_path / "ledger.db")
    view = build(conn)
    g = _parse(view)

    expected = sorted(
        [
            (ungated_many_task, "SA-0002", "findings_without_diff"),
            (no_attempt_task, "SA-0003", "findings_without_diff"),
            (unknown_state_task, "SA-0004", "unknown_state"),
            (unknown_risk_failing_task, "SA-0005", "unknown_risk"),
            (unknown_risk_known_state_task, "SA-0006", "unknown_risk"),
        ]
    )
    actual = sorted((lo.task_id, lo.spec_id, lo.reason) for lo in view.left_out)
    assert actual == expected
    assert LeftOut(gated_task, "SA-0001", "findings_without_diff") not in view.left_out

    # The gated task keeps its finding, against its own gated diff.
    gated_diff = f"{DATA}diff-attempt-{gated_attempt}"
    gated_finding_node = f"{DATA}finding-{gated_finding_ids[0]}"
    assert _triples(g, gated_finding_node, RDF_TYPE, f"{FACTORY}Finding")
    assert _triples(g, gated_finding_node, f"{EARL}subject", gated_diff)

    # The two ungated-but-kept tasks still carry their own triples.
    assert _triples(g, f"{DATA}task-{ungated_many_task}", RDF_TYPE, f"{FACTORY}Task")
    assert _triples(g, f"{DATA}task-{no_attempt_task}", RDF_TYPE, f"{FACTORY}Task")
    # ... but none of their findings are stated, whatever their number.
    for claim in ("c2a", "c2b", "c3"):
        assert claim not in view.turtle.decode("utf-8")

    # The three fully left-out tasks state nothing: not their task, their
    # attempt, their suite, their diff, their gate result, their finding.
    _absent(g, f"{DATA}task-{unknown_state_task}")
    _absent(g, f"{DATA}attempt-{unknown_state_attempt}")

    _absent(g, f"{DATA}task-{unknown_risk_failing_task}")
    _absent(g, f"{DATA}attempt-{unknown_risk_attempt}")
    _absent(g, f"{DATA}gatesuite-{unknown_risk_attempt}")
    _absent(g, f"{DATA}diff-attempt-{unknown_risk_attempt}")
    _absent(g, f"{DATA}gate-result-{unknown_risk_result}")

    _absent(g, f"{DATA}task-{unknown_risk_known_state_task}")
    _absent(g, f"{DATA}attempt-{unknown_risk_known_state_attempt}")

    for claim in ("c4", "c5", "c6"):
        assert claim not in view.turtle.decode("utf-8")


def test_a_finding_is_asserted_by_its_lens_against_the_last_gated_diff(
    tmp_path: Path,
) -> None:
    from saffron.agents.findings import Finding
    from saffron.gates.contract import GateResult
    from saffron.view.graph import build, open_read_only

    ledger, repo_id = _ledger(tmp_path)
    run_id = ledger.create_run(repo_id, "base1")

    task_id = ledger.create_task(run_id, "SA-0001", "sha1", "b1")
    _set_task(ledger, task_id, state="REPAIRING")

    first_gated = ledger.open_attempt(task_id, "GATING")
    ledger.record_gate_result(
        GateResult(gate="scope", status="pass", tool="t"), attempt_id=first_gated
    )
    second_gated = ledger.open_attempt(task_id, "GATING")
    ledger.record_gate_result(
        GateResult(gate="scope", status="pass", tool="t"), attempt_id=second_gated
    )
    # A gated attempt in a later phase, with a higher attempt_id than
    # either attempt of the first phase, however their `n` compare.
    last_gated = ledger.open_attempt(task_id, "REPAIRING")
    ledger.record_gate_result(
        GateResult(gate="scope", status="pass", tool="t"), attempt_id=last_gated
    )
    # An ungated attempt after it, which must not become the last diff.
    ledger.open_attempt(task_id, "REPAIRING")

    finding_ids = ledger.record_findings(
        task_id,
        [
            Finding(
                lens="adequacy",
                severity="blocker",
                file="f",
                line=1,
                claim="claim-a",
            ),
            Finding(
                lens="style", severity="concern", file="f", line=2, claim="claim-b"
            ),
        ],
    )
    ledger._db.execute(
        "UPDATE findings SET verdict = ? WHERE finding_id = ?",
        ("confirmed", finding_ids[0]),
    )
    ledger._db.commit()

    other_task = ledger.create_task(run_id, "SA-0002", "sha2", "b2")
    _set_task(ledger, other_task, state="GATING")
    other_gated = ledger.open_attempt(other_task, "GATING")
    ledger.record_gate_result(
        GateResult(gate="scope", status="pass", tool="t"), attempt_id=other_gated
    )
    other_finding_ids = ledger.record_findings(
        other_task,
        [Finding(lens="security", severity="note", file="f", line=3, claim="claim-c")],
    )
    ledger.close()

    conn = open_read_only(tmp_path / "ledger.db")
    view = build(conn)
    g = _parse(view)

    last_diff = f"{DATA}diff-attempt-{last_gated}"
    first_diff = f"{DATA}diff-attempt-{first_gated}"
    second_diff = f"{DATA}diff-attempt-{second_gated}"
    other_diff = f"{DATA}diff-attempt-{other_gated}"

    finding_a = f"{DATA}finding-{finding_ids[0]}"
    finding_b = f"{DATA}finding-{finding_ids[1]}"
    finding_c = f"{DATA}finding-{other_finding_ids[0]}"

    for finding_node, lens, severity in (
        (finding_a, "adequacy", "blocker"),
        (finding_b, "style", "concern"),
        (finding_c, "security", "note"),
    ):
        assert _triples(g, finding_node, RDF_TYPE, f"{FACTORY}Finding")
        assert _triples(g, finding_node, f"{FACTORY}severity", f"{FACTORY}{severity}")
        lens_node = f"{DATA}lens-{lens}"
        assert _triples(g, finding_node, f"{EARL}assertedBy", lens_node)
        assert _triples(g, lens_node, RDF_TYPE, f"{FACTORY}CriticLens")
        assert _triples(g, finding_node, f"{EARL}mode", f"{EARL}semiAuto")
        assert not _triples(g, finding_node, f"{EARL}mode", f"{EARL}automatic")

    # Task 1's findings name task 1's last gated diff, picked by attempt_id
    # and not by phase-local `n` or by first-gated.
    assert _triples(g, finding_a, f"{EARL}subject", last_diff)
    assert not _triples(g, finding_a, f"{EARL}subject", first_diff)
    assert not _triples(g, finding_a, f"{EARL}subject", second_diff)
    assert _triples(g, finding_b, f"{EARL}subject", last_diff)

    # Task 2's own finding names task 2's own diff, not task 1's.
    assert _triples(g, finding_c, f"{EARL}subject", other_diff)
    assert not _triples(g, finding_c, f"{EARL}subject", last_diff)

    claim_a = _literal(g, finding_a, f"{FACTORY}claim")
    assert claim_a.toPython() == "claim-a"
    verdict_a = _literal(g, finding_a, f"{FACTORY}verdict")
    assert verdict_a.toPython() == "confirmed"

    # The finding with no verdict states no verdict triple at all. A null
    # verdict is not the same fact as an empty string.
    assert not _triples(g, finding_b, f"{FACTORY}verdict")


def test_the_gate_sets_are_read_from_the_shapes_it_is_given(tmp_path: Path) -> None:
    from saffron.gates.contract import GateResult
    from saffron.view.graph import build, open_read_only

    original = DEFAULT_SHAPES.read_text()

    core_anchor = (
        "sh:in ( factory:scope factory:size factory:secrets\n"
        "            factory:integrity factory:census factory:committed\n"
        "            factory:criteria factory:revert factory:witness ) ."
    )
    assert original.count(core_anchor) == 1
    edited = original.replace(
        core_anchor,
        core_anchor.replace("factory:witness ) .", "factory:witness factory:dead ) ."),
    )

    role_anchor = (
        "sh:in ( factory:format factory:lint factory:types\n"
        "            factory:tests factory:no-network factory:coverage ) ."
    )
    assert edited.count(role_anchor) == 1
    edited = edited.replace(
        role_anchor,
        role_anchor.replace(
            "factory:coverage ) .", "factory:coverage factory:prose ) ."
        ),
    )

    # `factory:dead` and `factory:prose` are typed nothing in the
    # vocabulary, so a constraint that assumes otherwise must go too.
    gate_result_anchor = (
        "sh:path earl:assertedBy ; sh:minCount 1 ; sh:maxCount 1 ;\n"
        "        sh:class factory:Gate ] ;"
    )
    assert edited.count(gate_result_anchor) == 1
    edited = edited.replace(
        gate_result_anchor,
        "sh:path earl:assertedBy ; sh:minCount 1 ; sh:maxCount 1 ] ;",
    )

    contract_anchor = (
        "sh:path factory:role ; sh:minCount 1 ; sh:maxCount 1 ;\n"
        "        sh:class factory:GateRole ] ."
    )
    assert edited.count(contract_anchor) == 1
    edited = edited.replace(
        contract_anchor,
        "sh:path factory:role ; sh:minCount 1 ; sh:maxCount 1 ] .",
    )

    edited_shapes = tmp_path / "gate-sets-shapes.ttl"
    edited_shapes.write_text(edited)

    ledger, repo_id = _ledger(tmp_path)
    run_id = ledger.create_run(repo_id, "base1")
    task_id = ledger.create_task(run_id, "SA-0001", "sha1", "b1")
    _set_task(ledger, task_id, state="GATING")
    attempt_id = ledger.open_attempt(task_id, "GATING")
    result_ids = {
        name: ledger.record_gate_result(
            GateResult(gate=name, status="pass", tool="t"), attempt_id=attempt_id
        )
        for name in ("dead", "prose", "lint", "scope")
    }
    ledger.close()

    conn1 = open_read_only(tmp_path / "ledger.db")
    default_view = build(conn1)
    g1 = _parse(default_view)

    dead_result = f"{DATA}gate-result-{result_ids['dead']}"
    prose_result = f"{DATA}gate-result-{result_ids['prose']}"
    lint_result = f"{DATA}gate-result-{result_ids['lint']}"
    scope_result = f"{DATA}gate-result-{result_ids['scope']}"

    # With the default shapes, `dead` and `prose` are repo-defined gates.
    assert _triples(g1, dead_result, f"{EARL}assertedBy", f"{DATA}gate-dead")
    assert _triples(g1, f"{DATA}gate-dead", RDF_TYPE, f"{FACTORY}RepoDefinedGate")
    assert _triples(g1, prose_result, f"{EARL}assertedBy", f"{DATA}gate-prose")
    assert _triples(g1, f"{DATA}gate-prose", RDF_TYPE, f"{FACTORY}RepoDefinedGate")

    conn2 = open_read_only(tmp_path / "ledger.db")
    edited_view = build(conn2, shapes_path=edited_shapes)
    g2 = _parse(edited_view)

    # With the edited shapes, `dead` asserts as `factory:dead` and `prose`
    # as a contract gate with role `factory:prose`.
    assert _triples(g2, dead_result, f"{EARL}assertedBy", f"{FACTORY}dead")
    assert not _triples(g2, dead_result, f"{EARL}assertedBy", f"{DATA}gate-dead")
    _absent(g2, f"{DATA}gate-dead")

    assert _triples(g2, prose_result, f"{EARL}assertedBy", f"{DATA}gate-prose")
    assert _triples(g2, f"{DATA}gate-prose", RDF_TYPE, f"{FACTORY}ContractGate")
    assert _triples(g2, f"{DATA}gate-prose", f"{FACTORY}role", f"{FACTORY}prose")

    # `lint` keeps its role and `scope` stays core, whatever the edit adds.
    assert _triples(g2, lint_result, f"{EARL}assertedBy", f"{DATA}gate-lint")
    assert _triples(g2, f"{DATA}gate-lint", f"{FACTORY}role", f"{FACTORY}lint")
    assert _triples(g2, scope_result, f"{EARL}assertedBy", f"{FACTORY}scope")
    _absent(g2, f"{DATA}gate-scope")


def test_each_view_query_reads_what_build_states(tmp_path: Path) -> None:
    import pyoxigraph as ox

    from saffron.agents.findings import Finding
    from saffron.gates.contract import Failure, GateResult
    from saffron.projection import VOCABULARY
    from saffron.view.graph import build, open_read_only

    ledger, repo_id = _ledger(tmp_path)
    batch_id = ledger.create_batch(10.0)
    ledger.close_batch(batch_id, "DRAINED")
    run_id = ledger.create_run(repo_id, "base1", batch_id=batch_id)
    task_id = ledger.create_task(run_id, "SA-0001", "sha1", "b1")
    _set_task(
        ledger,
        task_id,
        state="READY_FOR_REVIEW",
        pr_url="https://example.com/pr/42",
    )
    attempt_id = ledger.open_attempt(task_id, "GATING")
    ledger.record_gate_result(
        GateResult(
            gate="lint",
            status="fail",
            tool="t",
            failures=[
                Failure(file="a.py", code="E1", message="m1", line=1),
                Failure(file="b.py", code="E2", message="m2", line=2),
            ],
        ),
        attempt_id=attempt_id,
    )
    ledger.record_gate_result(
        GateResult(gate="scope", status="pass", tool="t"), attempt_id=attempt_id
    )
    finding_ids = ledger.record_findings(
        task_id,
        [
            Finding(
                lens="style",
                severity="concern",
                file="f",
                line=1,
                claim="the one claim",
            )
        ],
    )

    other_run = ledger.create_run(repo_id, "base2")
    other_task = ledger.create_task(other_run, "SA-0002", "sha2", "b2")
    _set_task(ledger, other_task, state="DRAFT")
    ledger.close()

    conn = open_read_only(tmp_path / "ledger.db")
    view = build(conn)

    store = ox.Store()
    store.load(input=view.turtle, format=ox.RdfFormat.TURTLE)
    store.load(path=str(VOCABULARY), format=ox.RdfFormat.TURTLE)

    queries_dir = (
        Path(__file__).resolve().parent.parent / "ontology" / "queries" / "view"
    )

    def run(stem_prefix: str) -> list:
        (path,) = [
            p for p in queries_dir.glob("*.rq") if p.stem.startswith(stem_prefix)
        ]
        result = store.query(path.read_text())
        assert isinstance(result, ox.QuerySolutions)
        return list(result)

    task_node = ox.NamedNode(f"{DATA}task-{task_id}")
    finding_node = ox.NamedNode(f"{DATA}finding-{finding_ids[0]}")

    v1 = run("V1")
    assert len(v1) == 1
    assert v1[0]["because"] == ox.NamedNode(f"{FACTORY}DRAINED")
    assert int(v1[0]["tasks"].value) == 1

    v2 = run("V2")
    assert len(v2) == 1
    assert v2[0]["spec"].value == "SA-0001"
    assert v2[0]["pr"] == ox.NamedNode("https://example.com/pr/42")

    v3 = run("V3")
    assert len(v3) == 2
    by_gate = {row["gate"]: row for row in v3}
    lint_row = by_gate[ox.NamedNode(f"{DATA}gate-lint")]
    assert lint_row["outcome"] == ox.NamedNode(f"{EARL}failed")
    assert int(lint_row["failures"].value) == 2
    scope_row = by_gate[ox.NamedNode(f"{FACTORY}scope")]
    assert scope_row["outcome"] == ox.NamedNode(f"{EARL}passed")
    assert int(scope_row["failures"].value) == 0

    v4 = run("V4")
    assert len(v4) == 1
    assert v4[0]["task"] == task_node
    assert v4[0]["finding"] == finding_node
    assert v4[0]["lens"] == ox.NamedNode(f"{DATA}lens-style")
    assert v4[0]["severity"] == ox.NamedNode(f"{FACTORY}concern")
    assert v4[0]["claim"].value == "the one claim"

    v5 = run("V5")
    assert len(v5) == 1
    assert v5[0]["task"] == ox.NamedNode(f"{DATA}task-{other_task}")
    assert v5[0]["spec"].value == "SA-0002"
