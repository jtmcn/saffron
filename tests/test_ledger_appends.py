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


def test_an_attempts_gate_result_keeps_only_its_new_failures(ledger, record, task):
    repo_id = ledger.upsert_repo("other", "/o2", "/m2.git", policy_sha="p" * 64)
    run_id, task_id = task

    # Member 5: a baseline failure stored on another run must never cancel
    # this task's own head failure of the same identity.
    other_run = ledger.create_run(repo_id, base_sha="z" * 40)
    ledger.record_gate_result(
        GateResult(
            gate="lint",
            status="fail",
            failures=[Failure(file="r.py", code="E3", message="other run", line=1)],
        ),
        run_id=other_run,
    )

    # The task's own run's baseline: a lint suite, a tests suite and a
    # witness suite, each with one failure.
    ledger.record_gate_result(
        GateResult(
            gate="lint",
            status="fail",
            failures=[
                Failure(file="a.py", code="E1", message="boom", line=3),
                Failure(file="c.py", code="E2", message="dup", line=5),
            ],
        ),
        run_id=run_id,
    )
    ledger.record_gate_result(
        GateResult(
            gate="tests",
            status="fail",
            failures=[Failure(file="m.py", code="T1", message="shared", line=7)],
        ),
        run_id=run_id,
    )
    ledger.record_gate_result(
        GateResult(
            gate="witness",
            status="fail",
            failures=[
                Failure(
                    file="w.py", code="survived-mutant", message="mutant lived", line=9
                )
            ],
        ),
        run_id=run_id,
    )

    a1 = ledger.open_attempt(task_id)

    # Member 1: the baseline's match at a different line still cancels.
    ledger.record_gate_result(
        GateResult(
            gate="lint",
            status="fail",
            failures=[Failure(file="a.py", code="E1", message="boom", line=99)],
        ),
        attempt_id=a1,
    )
    # Member 2: two head copies of one baseline failure, one cancels, one new.
    ledger.record_gate_result(
        GateResult(
            gate="lint",
            status="fail",
            failures=[
                Failure(file="c.py", code="E2", message="dup", line=5),
                Failure(file="c.py", code="E2", message="dup", line=5),
            ],
        ),
        attempt_id=a1,
    )
    # Member 4: identical file/code/message to the `tests` baseline failure,
    # but under `lint`, and the gate is part of the identity, so this is new.
    ledger.record_gate_result(
        GateResult(
            gate="lint",
            status="fail",
            failures=[Failure(file="m.py", code="T1", message="shared", line=7)],
        ),
        attempt_id=a1,
    )
    # Member 5 (head side): identical to the other run's baseline failure.
    ledger.record_gate_result(
        GateResult(
            gate="lint",
            status="fail",
            failures=[Failure(file="r.py", code="E3", message="other run", line=1)],
        ),
        attempt_id=a1,
    )
    # Member 3: a `witness` failure coded `survived-mutant` at base never
    # cancels its match at head.
    ledger.record_gate_result(
        GateResult(
            gate="witness",
            status="fail",
            failures=[
                Failure(
                    file="w.py", code="survived-mutant", message="mutant lived", line=9
                )
            ],
        ),
        attempt_id=a1,
    )
    # Member 6: a gate with no failures.
    ledger.record_gate_result(GateResult(gate="types", status="pass"), attempt_id=a1)

    results = ledger.attempt_results(a1)
    by_gate: dict[str, list[GateResult]] = {}
    for result in results:
        by_gate.setdefault(result.gate, []).append(result)

    lint_results = by_gate["lint"]
    assert [r.failures for r in lint_results] == [
        [],
        [Failure(file="c.py", code="E2", message="dup", line=5)],
        [Failure(file="m.py", code="T1", message="shared", line=7)],
        [Failure(file="r.py", code="E3", message="other run", line=1)],
    ]
    witness_result = by_gate["witness"][0]
    assert witness_result.failures == [
        Failure(file="w.py", code="survived-mutant", message="mutant lived", line=9)
    ]
    types_result = by_gate["types"][0]
    assert types_result.failures == []

    head_counts = [
        row["failures_at_head"]
        for row in ledger._db.execute(
            "SELECT failures_at_head FROM gate_results WHERE attempt_id = ? ORDER BY gate_result_id",
            (a1,),
        )
    ]
    assert head_counts == [1, 2, 1, 1, 1, 0]

    # The fact itself carries the same failures and the same count.
    fact = record.read(ledger.record_key(task_id))[-1]
    assert fact.payload["failures"] == []
    assert fact.payload["failures_at_head"] == 0

    # The baseline results are untouched: full failure lists, null counts.
    baseline = ledger.baseline_results(run_id)
    assert {r.gate: [f.code for f in r.failures] for r in baseline} == {
        "lint": ["E1", "E2"],
        "tests": ["T1"],
        "witness": ["survived-mutant"],
    }
    baseline_counts = [
        row["failures_at_head"]
        for row in ledger._db.execute(
            "SELECT failures_at_head FROM gate_results WHERE run_id = ? ORDER BY gate_result_id",
            (run_id,),
        )
    ]
    assert baseline_counts == [None, None, None]

    # Member 7 & 8: an explicit `baseline` is what is subtracted, not
    # whatever else is stored for the run.
    third_run = ledger.create_run(repo_id, base_sha="y" * 40)
    third_task = ledger.create_task(
        third_run, spec_id="SA-0100", spec_sha="s" * 64, branch="b3"
    )
    one_copy = GateResult(
        gate="lint",
        status="fail",
        failures=[Failure(file="d.py", code="E4", message="twice", line=1)],
    )
    # Two stored suites, each holding the failure once.
    ledger.record_gate_result(one_copy, run_id=third_run)
    ledger.record_gate_result(one_copy, run_id=third_run)
    a3 = ledger.open_attempt(third_task)
    two_copies = GateResult(
        gate="lint",
        status="fail",
        failures=[
            Failure(file="d.py", code="E4", message="twice", line=1),
            Failure(file="d.py", code="E4", message="twice", line=1),
        ],
    )
    ledger.record_gate_result(two_copies, attempt_id=a3, baseline=[one_copy])
    ledger.record_gate_result(one_copy, attempt_id=a3, baseline=[])
    third_results = ledger.attempt_results(a3)
    assert third_results[0].failures == [
        Failure(file="d.py", code="E4", message="twice", line=1)
    ]
    assert third_results[1].failures == [
        Failure(file="d.py", code="E4", message="twice", line=1)
    ]

    # Member 9: a run with no stored baseline cancels nothing.
    fourth_run = ledger.create_run(repo_id, base_sha="x" * 40)
    fourth_task = ledger.create_task(
        fourth_run, spec_id="SA-0101", spec_sha="s" * 64, branch="b4"
    )
    a4 = ledger.open_attempt(fourth_task)
    ledger.record_gate_result(
        GateResult(
            gate="lint",
            status="fail",
            failures=[
                Failure(file="e.py", code="E5", message="none stored", line=1),
                Failure(file="e.py", code="E5", message="none stored", line=1),
            ],
        ),
        attempt_id=a4,
    )
    (fourth_result,) = ledger.attempt_results(a4)
    assert len(fourth_result.failures) == 2
    fourth_fact = record.read(ledger.record_key(fourth_task))[-1]
    assert fourth_fact.payload["failures_at_head"] == 2


def test_a_gate_result_carries_the_tier_its_suite_ran_at(ledger, record, task):
    _, task_id = task
    a1 = ledger.open_attempt(task_id)
    ledger.record_gate_result(
        GateResult(gate="lint", status="pass"), attempt_id=a1, earned_risk="standard"
    )
    assert record.read(ledger.record_key(task_id))[-1].payload["earned_risk"] == (
        "standard"
    )
    assert ledger.attempts(task_id)[0]["earned_risk"] == "standard"

    a2 = ledger.open_attempt(task_id)
    ledger.record_gate_result(
        GateResult(gate="lint", status="pass"), attempt_id=a2, earned_risk="elevated"
    )
    assert ledger.attempts(task_id)[1]["earned_risk"] == "elevated"

    # A null tier leaves the column as it was, and the fact still carries
    # the key, a null value included.
    a3 = ledger.open_attempt(task_id)
    ledger.record_gate_result(GateResult(gate="lint", status="pass"), attempt_id=a3)
    assert "earned_risk" in record.read(ledger.record_key(task_id))[-1].payload
    attempts = ledger.attempts(task_id)
    assert [a["earned_risk"] for a in attempts] == ["standard", "elevated", None]

    # A second result against the same attempt overwrites with the last
    # non-null value, never clears, and touches only this attempt.
    ledger.record_gate_result(
        GateResult(gate="types", status="pass"), attempt_id=a1, earned_risk="elevated"
    )
    attempts = ledger.attempts(task_id)
    assert [a["earned_risk"] for a in attempts] == ["elevated", "elevated", None]

    # A third result against `a1`, this time with no `earned_risk` at all,
    # must leave its already-set tier alone rather than clearing it to null.
    ledger.record_gate_result(GateResult(gate="format", status="pass"), attempt_id=a1)
    attempts = ledger.attempts(task_id)
    assert [a["earned_risk"] for a in attempts] == ["elevated", "elevated", None]


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
    # Name kept for `census`: a backfilled task files under its new key.
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
