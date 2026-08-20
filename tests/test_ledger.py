import pytest
import sqlite3

from saffron.gates.contract import Failure, GateResult
from saffron.ledger import Ledger


@pytest.fixture
def ledger(tmp_path):
    made = Ledger(tmp_path / "ledger.db")
    yield made
    made.close()


@pytest.fixture
def task(ledger):
    repo_id = ledger.upsert_repo("thermal-edge", "/o", "/m.git", policy_sha="p" * 64)
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    task_id = ledger.create_task(
        run_id, spec_id="TE-9001", spec_sha="s" * 64, branch="saffron/TE-9001",
        risk="standard", budget_usd=12,
    )
    return run_id, task_id


def test_upsert_repo_is_idempotent(ledger):
    first = ledger.upsert_repo("thermal-edge", "/o", "/m.git", policy_sha="p")
    second = ledger.upsert_repo("thermal-edge", "/o", "/m.git", policy_sha="q")
    assert first == second


def test_a_baseline_result_belongs_to_a_run(ledger, task):
    run_id, _ = task
    ledger.record_gate_result(
        GateResult(gate="lint", status="fail",
                   failures=[Failure(file="a.py", line=1, code="E501", message="long")]),
        run_id=run_id,
    )
    results = ledger.baseline_results(run_id)
    assert [r.gate for r in results] == ["lint"]
    assert results[0].failures[0].code == "E501"
    assert results[0].failures[0].line == 1


def test_a_task_result_belongs_to_an_attempt(ledger, task):
    _, task_id = task
    ledger.record_gate_result(GateResult(gate="types", status="pass"), attempt_id=task_id)
    assert [r.gate for r in ledger.task_results(task_id)] == ["types"]


def test_a_baseline_result_is_not_a_task_result(ledger, task):
    run_id, task_id = task
    ledger.record_gate_result(GateResult(gate="lint", status="pass"), run_id=run_id)
    assert ledger.task_results(task_id) == []


def test_a_gate_result_must_belong_to_exactly_one_of_them(ledger, task):
    run_id, task_id = task
    with pytest.raises(sqlite3.IntegrityError):
        ledger.record_gate_result(
            GateResult(gate="lint", status="pass"), run_id=run_id, attempt_id=task_id
        )
    with pytest.raises(sqlite3.IntegrityError):
        ledger.record_gate_result(GateResult(gate="lint", status="pass"))


def test_failures_round_trip_in_order(ledger, task):
    run_id, _ = task
    ledger.record_gate_result(
        GateResult(
            gate="types",
            status="fail",
            failures=[
                Failure(file="a.py", line=8, code="arg-type", message="first"),
                Failure(file="b.py", line=2, code="return-value", message="second"),
            ],
            summary="2 errors",
        ),
        run_id=run_id,
    )
    (result,) = ledger.baseline_results(run_id)
    assert [f.message for f in result.failures] == ["first", "second"]
    assert result.summary == "2 errors"


def test_a_failure_with_no_line_round_trips_as_none(ledger, task):
    run_id, _ = task
    ledger.record_gate_result(
        GateResult(gate="format", status="fail",
                   failures=[Failure(file="a.py", code="format", message="would reformat")]),
        run_id=run_id,
    )
    assert ledger.baseline_results(run_id)[0].failures[0].line is None


def test_an_errored_gate_stores_its_summary(ledger, task):
    run_id, _ = task
    ledger.record_gate_result(
        GateResult(gate="types", status="error", summary="toolchain missing"), run_id=run_id
    )
    (result,) = ledger.baseline_results(run_id)
    assert result.status == "error"
    assert result.summary == "toolchain missing"


def test_task_state_moves(ledger, task):
    _, task_id = task
    ledger.set_task_state(task_id, "READY_FOR_REVIEW")
    (line,) = ledger.queue_lines()
    assert line["state"] == "READY_FOR_REVIEW"
    assert line["spec_id"] == "TE-9001"
    assert line["repo"] == "thermal-edge"


def test_the_ledger_survives_being_reopened(tmp_path):
    path = tmp_path / "ledger.db"
    first = Ledger(path)
    repo_id = first.upsert_repo("r", "/o", "/m", policy_sha="p")
    run_id = first.create_run(repo_id, base_sha="a" * 40)
    first.record_gate_result(GateResult(gate="lint", status="pass"), run_id=run_id)
    first.close()

    second = Ledger(path)
    assert [r.gate for r in second.baseline_results(run_id)] == ["lint"]
    second.close()
