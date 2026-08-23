import sqlite3

import pytest

from saffron.agents.findings import Finding
from saffron.gates.contract import Failure, GateResult
from saffron.ledger import SCHEMA, Ledger


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
        run_id,
        spec_id="TE-9001",
        spec_sha="s" * 64,
        branch="saffron/TE-9001",
        risk="standard",
        budget_usd=12,
    )
    return run_id, task_id


def test_upsert_repo_is_idempotent(ledger):
    first = ledger.upsert_repo("thermal-edge", "/o", "/m.git", policy_sha="p")
    second = ledger.upsert_repo("thermal-edge", "/o", "/m.git", policy_sha="q")
    assert first == second


def test_a_baseline_result_belongs_to_a_run(ledger, task):
    run_id, _ = task
    ledger.record_gate_result(
        GateResult(
            gate="lint",
            status="fail",
            failures=[Failure(file="a.py", line=1, code="E501", message="long")],
        ),
        run_id=run_id,
    )
    results = ledger.baseline_results(run_id)
    assert [r.gate for r in results] == ["lint"]
    assert results[0].failures[0].code == "E501"
    assert results[0].failures[0].line == 1


def test_a_task_result_belongs_to_an_attempt(ledger, task):
    _, task_id = task
    ledger.record_gate_result(
        GateResult(gate="types", status="pass"),
        attempt_id=ledger.open_attempt(task_id),
    )
    assert [r.gate for r in ledger.task_results(task_id)] == ["types"]


def test_a_baseline_result_is_not_a_task_result(ledger, task):
    run_id, task_id = task
    ledger.record_gate_result(GateResult(gate="lint", status="pass"), run_id=run_id)
    assert ledger.task_results(task_id) == []


def test_a_gate_result_must_belong_to_exactly_one_of_them(ledger, task):
    run_id, task_id = task
    with pytest.raises(sqlite3.IntegrityError):
        ledger.record_gate_result(
            GateResult(gate="lint", status="pass"),
            run_id=run_id,
            attempt_id=ledger.open_attempt(task_id),
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
        GateResult(
            gate="format",
            status="fail",
            failures=[Failure(file="a.py", code="format", message="would reformat")],
        ),
        run_id=run_id,
    )
    assert ledger.baseline_results(run_id)[0].failures[0].line is None


def test_an_errored_gate_stores_its_summary(ledger, task):
    run_id, _ = task
    ledger.record_gate_result(
        GateResult(gate="types", status="error", summary="toolchain missing"),
        run_id=run_id,
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


def test_a_failed_write_leaves_no_partial_gate_result(ledger, task):
    run_id, _ = task
    # model_construct bypasses pydantic validation to force a NOT NULL
    # violation on the second failure row, after the gate_results row exists.
    broken = Failure.model_construct(file=None, line=1, code="E001", message="boom")
    with pytest.raises(sqlite3.IntegrityError):
        ledger.record_gate_result(
            GateResult(
                gate="lint",
                status="fail",
                failures=[Failure(file="a.py", line=1, code="E001"), broken],
            ),
            run_id=run_id,
        )
    assert ledger._db.in_transaction is False

    ledger.record_gate_result(GateResult(gate="types", status="pass"), run_id=run_id)
    assert [r.gate for r in ledger.baseline_results(run_id)] == ["types"]


def test_duration_ms_round_trips(ledger, task):
    run_id, _ = task
    ledger.record_gate_result(
        GateResult(gate="lint", status="pass", duration_ms=1234), run_id=run_id
    )
    (result,) = ledger.baseline_results(run_id)
    assert result.duration_ms == 1234


def test_two_repos_of_the_same_name_are_two_rows(ledger):
    """The directory basename is not an identity — the origin is."""
    first = ledger.upsert_repo("service", "/a/service", "/m/a.git", policy_sha="p")
    second = ledger.upsert_repo("service", "/b/service", "/m/b.git", policy_sha="p")
    assert first != second


def test_package_writes_back_a_state_the_run_had_already_closed(tmp_path):
    """run_one_cell has already set READY_FOR_REVIEW and finished the run
    COMPLETE before PACKAGE runs (session.py:734-735). Left alone, a
    MERGE_FAILED task reads READY_FOR_REVIEW forever and the failure exists
    nowhere but stdout."""
    ledger = Ledger(tmp_path / "l.db")
    repo_id = ledger.upsert_repo("r", "git@github.com:o/r.git", "/m", "sha")
    run_id = ledger.create_run(repo_id, "a" * 40)
    task_id = ledger.create_task(run_id, "SA-0005", "s" * 40, branch="saffron/SA-0005")
    ledger.set_task_state(task_id, "READY_FOR_REVIEW")
    ledger.finish_run(run_id, "COMPLETE")

    ledger.set_task_package(
        task_id,
        "MERGE_FAILED",
        "saffron/SA-0005",
        "c" * 40,
        "https://github.com/o/r/pull/7",
    )
    row = next(r for r in ledger.queue_lines() if r["task_id"] == task_id)
    assert row["state"] == "MERGE_FAILED"
    assert row["pushed_sha"] == "c" * 40
    assert row["pr_url"] == "https://github.com/o/r/pull/7"
    ledger.close()


def test_a_ledger_that_predates_the_package_columns_keeps_its_rows(tmp_path):
    """`CREATE TABLE IF NOT EXISTS` does not alter, so an existing
    ~/.saffron/ledger.db has neither column. The migration is additive: the
    rows that were already there must still be there, and readable."""
    path = tmp_path / "old.db"
    before = SCHEMA.replace("    pushed_sha TEXT,\n    pr_url     TEXT,\n", "")
    assert "pushed_sha" not in before  # otherwise this test proves nothing
    old = sqlite3.connect(path)
    old.executescript(before)
    old.execute("INSERT INTO repos (name, origin, mirror_path) VALUES ('r', 'o', '/m')")
    old.execute("INSERT INTO runs (repo_id, base_sha) VALUES (1, 'a')")
    old.execute(
        """INSERT INTO tasks (run_id, spec_id, spec_sha, state, branch)
           VALUES (1, 'SA-0001', 's', 'READY_FOR_REVIEW', 'saffron/SA-0001')"""
    )
    old.commit()
    old.close()

    ledger = Ledger(path)
    (row,) = ledger.queue_lines()
    assert row["spec_id"] == "SA-0001"
    assert row["pushed_sha"] is None and row["pr_url"] is None
    ledger.set_task_package(row["task_id"], "MERGE_FAILED", "b", "c" * 40, "")
    (row,) = ledger.queue_lines()
    assert (row["state"], row["pushed_sha"]) == ("MERGE_FAILED", "c" * 40)
    ledger.close()


def test_an_attempt_records_what_the_turn_was(ledger, task):
    _, task_id = task
    ledger.set_task_state(task_id, "IMPLEMENTING")
    attempt_id = ledger.open_attempt(task_id)
    ledger.close_attempt(
        attempt_id,
        session_id="s-1",
        subtype="success",
        terminal_reason=None,
        num_turns=4,
        cost_usd_est=0.31,
    )
    (row,) = ledger.attempts(task_id)
    assert (row["phase"], row["n"], row["session_id"]) == ("IMPLEMENTING", 1, "s-1")
    assert (row["subtype"], row["num_turns"], row["cost_usd_est"]) == (
        "success",
        4,
        0.31,
    )
    assert row["ended_at"] is not None


def test_the_phase_an_attempt_belongs_to_is_the_state_the_task_is_in(ledger, task):
    """`n` is numbered within a phase, so the two repair turns are 1 and 2
    while the implement turn before them is its own 1 (§4.1)."""
    _, task_id = task
    ledger.set_task_state(task_id, "IMPLEMENTING")
    ledger.open_attempt(task_id)
    ledger.set_task_state(task_id, "REPAIRING")
    ledger.open_attempt(task_id)
    ledger.open_attempt(task_id)
    assert [(r["phase"], r["n"]) for r in ledger.attempts(task_id)] == [
        ("IMPLEMENTING", 1),
        ("REPAIRING", 1),
        ("REPAIRING", 2),
    ]


def test_a_gate_result_belongs_to_the_attempt_that_produced_it(ledger, task):
    """Every attempt's results shared one id while `attempt_id` held the task's
    own — the join §5.4's no-progress rule and §8 both assume."""
    _, task_id = task
    ledger.set_task_state(task_id, "REPAIRING")
    first = ledger.open_attempt(task_id)
    ledger.record_gate_result(GateResult(gate="tests", status="fail"), attempt_id=first)
    second = ledger.open_attempt(task_id)
    ledger.record_gate_result(
        GateResult(gate="tests", status="pass"), attempt_id=second
    )

    assert [r.status for r in ledger.attempt_results(first)] == ["fail"]
    assert [r.status for r in ledger.attempt_results(second)] == ["pass"]
    assert [r.status for r in ledger.task_results(task_id)] == ["fail", "pass"]


def test_a_gate_result_cannot_name_an_attempt_that_does_not_exist(ledger, task):
    """What made `attempt_id = task_id` possible: the column had no reference."""
    _, task_id = task
    with pytest.raises(sqlite3.IntegrityError):
        ledger.record_gate_result(
            GateResult(gate="lint", status="pass"), attempt_id=90210
        )


def test_a_task_spends_the_sum_of_its_attempts(ledger, task):
    _, task_id = task
    ledger.set_task_state(task_id, "IMPLEMENTING")
    for cost in (0.25, 0.50):
        attempt_id = ledger.open_attempt(task_id)
        ledger.close_attempt(
            attempt_id,
            session_id="s-1",
            subtype="success",
            terminal_reason=None,
            num_turns=1,
            cost_usd_est=cost,
        )
    ledger.set_task_state(task_id, "READY_FOR_REVIEW")
    (line,) = ledger.queue_lines()
    assert line["spent_usd_est"] == 0.75


def test_a_task_whose_attempts_all_crashed_spends_zero_not_null(ledger, task):
    """A crashed session may report every cost field as zero (§4.1); a run that
    ends with no persisted figure at all is the defect this column closes."""
    _, task_id = task
    ledger.set_task_state(task_id, "NOT_IMPLEMENTED")
    (line,) = ledger.queue_lines()
    assert line["spent_usd_est"] == 0.0


def test_a_dropped_finding_is_kept_and_marked(ledger, task):
    """Dropped findings are kept, not deleted: the drop rate is the signal that
    a lens is badly prompted (§4.1, §5.5)."""
    _, task_id = task
    ledger.record_findings(
        task_id,
        [
            Finding(
                lens="correctness",
                severity="blocker",
                file="a.py",
                line=3,
                claim="off by one",
                anchored=True,
            ),
            Finding(
                lens="correctness",
                severity="concern",
                file="ghost.py",
                line=9,
                claim="not in the diff",
                anchored=False,
            ),
        ],
    )
    rows = ledger.findings(task_id)
    assert [(r["claim"], r["anchored"]) for r in rows] == [
        ("off by one", 1),
        ("not in the diff", 0),
    ]
    assert rows[0]["verdict"] is None and rows[0]["adjudication"] is None


def test_a_verdict_and_a_rebuttal_land_on_the_finding_review_inserted(ledger, task):
    """Three distinct judgements that must not collapse into one column (§4.1):
    the critic's verdict, the implementer's rebuttal, and the operator's
    adjudication — which has no producer yet and stays null."""
    _, task_id = task
    (finding_id,) = ledger.record_findings(
        task_id,
        [
            Finding(
                lens="schema",
                severity="blocker",
                file="m.py",
                line=1,
                claim="drops a column",
                anchored=True,
            )
        ],
    )
    ledger.record_rebuttal(
        finding_id, verdict="withdrawn", rebuttal="the column is added in the migration"
    )
    (row,) = ledger.findings(task_id)
    assert row["verdict"] == "withdrawn"
    assert row["rebuttal"] == "the column is added in the migration"
    assert row["adjudication"] is None


def test_the_drop_rate_per_lens_is_one_query(ledger, task):
    """§5.5's signal, and item 3's own acceptance criterion."""
    _, task_id = task
    ledger.record_findings(
        task_id,
        [
            Finding(
                lens="correctness",
                severity="blocker",
                file="a.py",
                line=1,
                claim="one",
                anchored=True,
            ),
            Finding(
                lens="correctness",
                severity="note",
                file="b.py",
                line=2,
                claim="two",
                anchored=False,
            ),
            Finding(
                lens="schema",
                severity="blocker",
                file="c.py",
                line=3,
                claim="three",
                anchored=False,
            ),
        ],
    )
    rows = ledger._db.execute(
        """SELECT lens, AVG(1 - anchored) AS drop_rate
             FROM findings GROUP BY lens ORDER BY lens"""
    ).fetchall()
    assert [(r["lens"], r["drop_rate"]) for r in rows] == [
        ("correctness", 0.5),
        ("schema", 1.0),
    ]


def test_a_ledger_that_predates_spent_usd_est_keeps_its_rows(tmp_path):
    """The same additive rule the package columns follow: `CREATE TABLE IF NOT
    EXISTS` does not alter, and no migration may lose a row."""
    path = tmp_path / "old.db"
    before = SCHEMA.replace("    spent_usd_est REAL NOT NULL DEFAULT 0.0,\n", "")
    assert "spent_usd_est" not in before  # otherwise this test proves nothing
    old = sqlite3.connect(path)
    old.executescript(before)
    old.execute("INSERT INTO repos (name, origin, mirror_path) VALUES ('r', 'o', '/m')")
    old.execute("INSERT INTO runs (repo_id, base_sha) VALUES (1, 'a')")
    old.execute(
        """INSERT INTO tasks (run_id, spec_id, spec_sha, state, branch)
           VALUES (1, 'SA-0001', 's', 'READY_FOR_REVIEW', 'saffron/SA-0001')"""
    )
    old.commit()
    old.close()

    ledger = Ledger(path)
    (row,) = ledger.queue_lines()
    assert row["spec_id"] == "SA-0001" and row["spent_usd_est"] == 0.0
    ledger.close()
