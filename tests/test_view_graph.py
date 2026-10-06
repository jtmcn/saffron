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
