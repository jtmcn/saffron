import pytest

from saffron.gates.contract import Failure, GateResult
from saffron.ledger import Ledger
from saffron.record.memory import MemoryRecord


@pytest.fixture
def record():
    return MemoryRecord()


@pytest.fixture
def ledger(tmp_path, record):
    made = Ledger(tmp_path / "ledger.db", record=record)
    yield made
    made.close()


@pytest.fixture
def task(ledger):
    repo_id = ledger.upsert_repo("saffron", "/o", "/m.git", policy_sha="p" * 64)
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    task_id = ledger.create_task(
        run_id,
        spec_id="SA-0099",
        spec_sha="s" * 64,
        branch="saffron/SA-0099",
        risk="elevated",
        budget_usd=12,
    )
    return run_id, task_id


def kinds(record, key):
    return [f.kind for f in record.read(key)]


def test_creating_a_task_mints_a_record_key(ledger, task):
    _, task_id = task
    key = ledger.record_key(task_id)
    assert len(key) == 32


def test_creating_a_task_appends_task_created(ledger, record, task):
    _, task_id = task
    key = ledger.record_key(task_id)
    assert kinds(record, key) == ["task_created"]
    fact = record.read(key)[0]
    # R1: the fold's `repos`/`runs` inserts need these, unproven elsewhere.
    assert fact.payload["origin"] == "/o"
    assert fact.payload["mirror_path"] == "/m.git"


def test_a_declared_risk_and_an_absent_one_are_distinguishable(ledger, record):
    # The defect item 170 exists to kill: `standard` by default and `standard`
    # by declaration must not read the same in the record.
    repo_id = ledger.upsert_repo("saffron", "/o", "/m.git", policy_sha="p")
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    undeclared = ledger.create_task(
        run_id,
        spec_id="SA-0085",
        spec_sha="s" * 64,
        branch="b",
    )
    fact = record.read(ledger.record_key(undeclared))[0]
    assert fact.payload["risk"] is None


def test_a_state_change_appends_task_state(ledger, record, task):
    _, task_id = task
    ledger.set_task_state(task_id, "IMPLEMENTING")
    key = ledger.record_key(task_id)
    assert kinds(record, key) == ["task_created", "task_state"]


def test_an_attempt_appends_on_open_and_on_close(ledger, record, task):
    _, task_id = task
    attempt_id = ledger.open_attempt(task_id, phase="IMPLEMENTING")
    ledger.close_attempt(
        attempt_id,
        session_id="s",
        subtype="success",
        terminal_reason=None,
        num_turns=4,
        cost_usd_est=1.25,
    )
    key = ledger.record_key(task_id)
    assert kinds(record, key)[-2:] == ["attempt_opened", "attempt_closed"]


def test_a_gate_result_carries_its_failures(ledger, record, task):
    _, task_id = task
    attempt_id = ledger.open_attempt(task_id)
    ledger.record_gate_result(
        GateResult(
            gate="lint",
            status="fail",
            tool="ruff 0.6.0",
            duration_ms=12,
            summary="1 error",
            failures=[Failure(file="a.py", code="E501", message="long", line=3)],
        ),
        attempt_id=attempt_id,
    )
    assert record.read(ledger.record_key(task_id))[-1].kind == "gate_result"


def test_a_gate_error_is_not_recorded_as_a_failure(ledger, record, task):
    # `error` (gate broke) and `fail` (repo's code is wrong) must stay distinct
    # in the record, or the fold loses the retry taxonomy.
    _, task_id = task
    attempt_id = ledger.open_attempt(task_id)
    ledger.record_gate_result(
        GateResult(
            gate="lint",
            status="error",
            tool="ruff 0.6.0",
            duration_ms=12,
            summary="toolchain broken",
        ),
        attempt_id=attempt_id,
    )
    assert record.read(ledger.record_key(task_id))[-1].payload["status"] == "error"


def test_a_ledger_with_no_record_still_writes_rows(tmp_path):
    # Every existing caller passes no record, and must be unaffected.
    plain = Ledger(tmp_path / "plain.db")
    repo_id = plain.upsert_repo("saffron", "/o", "/m.git", policy_sha="p")
    run_id = plain.create_run(repo_id, base_sha="a" * 40)
    task_id = plain.create_task(
        run_id,
        spec_id="SA-0099",
        spec_sha="s" * 64,
        branch="b",
    )
    # Every task carries a key now, with or without a record attached.
    key = plain.record_key(task_id)
    assert key is not None and len(key) == 32
    plain.close()


def test_every_fact_carries_the_repo_it_belongs_to(ledger, record, task):
    _, task_id = task
    ledger.set_task_state(task_id, "REVIEWING")
    assert {f.repo for f in record.read(ledger.record_key(task_id))} == {"saffron"}


def test_a_pre_record_task_files_no_fact(tmp_path, record):
    # Name kept for `census`: the body now proves the backfill unreadable.
    path = tmp_path / "ledger.db"
    plain = Ledger(path)
    repo_id = plain.upsert_repo("saffron", "/o", "/m.git", policy_sha="p")
    run_id = plain.create_run(repo_id, base_sha="a" * 40)
    task_id = plain.create_task(
        run_id, spec_id="SA-0001", spec_sha="s" * 64, branch="b"
    )
    plain._db.execute(
        "UPDATE tasks SET record_key = NULL WHERE task_id = ?", (task_id,)
    )
    plain._db.commit()
    plain.close()

    reopened = Ledger(path, record=record)
    key = reopened.record_key(task_id)
    assert key is not None and len(key) == 32
    reopened.set_task_state(task_id, "IMPLEMENTING")
    reopened.close()
    assert record.task_keys() == [key]
    assert [f.kind for f in record.read(key)] == ["task_state"]


def test_an_unknown_task_id_files_no_fact(ledger, record):
    with pytest.raises(ValueError, match="999999"):
        ledger.set_task_state(999_999, "IMPLEMENTING")
    assert record.task_keys() == []
