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


def test_tasks_by_spec_id_carries_branch_and_pushed_sha_beside_state(tmp_path):
    """The query `SA-0026`'s resolver needs and nothing before it returns:
    `tasks_by_spec` stops at `task_id`/`spec_id`/`spec_sha`/`state`,
    `tasks_by_repo` is `reconcile`'s three columns, `queue_lines` is the
    printer's — none carries `branch` and `pushed_sha` beside `spec_id`."""
    ledger = Ledger(tmp_path / "l.db")
    repo_id = ledger.upsert_repo("r", "/o", "/m.git", policy_sha="p" * 64)
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    task_id = ledger.create_task(
        run_id, spec_id="SA-0001", spec_sha="s" * 40, branch="saffron/SA-0001"
    )
    ledger.record_push(task_id, "c" * 40)
    ledger.set_task_state(task_id, "READY_FOR_REVIEW")

    (row,) = ledger.tasks_by_spec_id(repo_id, "SA-0001")

    assert row["task_id"] == task_id
    assert row["spec_id"] == "SA-0001"
    assert row["spec_sha"] == "s" * 40
    assert row["state"] == "READY_FOR_REVIEW"
    assert row["branch"] == "saffron/SA-0001"
    assert row["pushed_sha"] == "c" * 40
    ledger.close()


def test_tasks_by_spec_id_is_scoped_to_one_repo(tmp_path):
    ledger = Ledger(tmp_path / "l.db")
    repo_a = ledger.upsert_repo("a", "/a", "/m.git", policy_sha="p" * 64)
    repo_b = ledger.upsert_repo("b", "/b", "/m.git", policy_sha="p" * 64)
    for repo_id in (repo_a, repo_b):
        run_id = ledger.create_run(repo_id, base_sha="a" * 40)
        ledger.create_task(
            run_id, spec_id="SA-0001", spec_sha="s" * 40, branch="saffron/SA-0001"
        )

    assert len(ledger.tasks_by_spec_id(repo_a, "SA-0001")) == 1
    ledger.close()


def test_tasks_by_spec_id_spans_every_spec_sha_oldest_first(tmp_path):
    """Merging is permanent and the parent's spec text may have moved since
    — the same "every sha" reach `scheduler.build_queue`'s `merged_anywhere`
    takes, and for the same reason: this attended path never reads the
    parent's file, so it has no current sha to filter rows to."""
    ledger = Ledger(tmp_path / "l.db")
    repo_id = ledger.upsert_repo("r", "/o", "/m.git", policy_sha="p" * 64)
    first_run = ledger.create_run(repo_id, base_sha="a" * 40)
    first = ledger.create_task(
        first_run, spec_id="SA-0001", spec_sha="1" * 40, branch="saffron/SA-0001"
    )
    second_run = ledger.create_run(repo_id, base_sha="a" * 40)
    second = ledger.create_task(
        second_run, spec_id="SA-0001", spec_sha="2" * 40, branch="saffron/SA-0001"
    )

    rows = ledger.tasks_by_spec_id(repo_id, "SA-0001")

    assert [row["task_id"] for row in rows] == [first, second]
    assert [row["spec_sha"] for row in rows] == ["1" * 40, "2" * 40]
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
    tasks_columns = before.split("CREATE TABLE IF NOT EXISTS tasks")[1].split(");")[0]
    assert "spent_usd_est" not in tasks_columns  # otherwise this test proves nothing
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


def test_a_ledger_that_predates_attempts_does_not_reattach_its_results(tmp_path):
    """The collision this backfill exists for: `attempt_id` held a *task_id*,
    and a new attempt's id starts at 1 in that same namespace. Left alone,
    task 1's v0.5 results read as belonging to whoever draws attempt 1."""
    path = tmp_path / "old.db"
    before = SCHEMA.replace(
        "attempt_id     INTEGER REFERENCES attempts(attempt_id),",
        "attempt_id     INTEGER,",
    )
    assert "REFERENCES attempts" not in before  # otherwise this proves nothing
    old = sqlite3.connect(path)
    old.executescript(before)
    old.execute("DROP TABLE attempts")
    old.execute("INSERT INTO repos (name, origin, mirror_path) VALUES ('r','o','/m')")
    old.execute("INSERT INTO runs (repo_id, base_sha) VALUES (1, 'a')")
    old.execute(
        """INSERT INTO tasks (run_id, spec_id, spec_sha, state, branch)
           VALUES (1, 'SA-0001', 's', 'READY_FOR_REVIEW', 'saffron/SA-0001')"""
    )
    old.execute(
        "INSERT INTO gate_results (attempt_id, gate, status) VALUES (1, 'tests', 'pass')"
    )
    old.commit()
    old.close()

    ledger = Ledger(path)
    run_id = ledger.create_run(1, "b" * 40)
    fresh = ledger.create_task(run_id, "SA-0009", "s", branch="saffron/SA-0009")
    ledger.set_task_state(fresh, "IMPLEMENTING")
    ledger.record_gate_result(
        GateResult(gate="lint", status="pass"), attempt_id=ledger.open_attempt(fresh)
    )
    # The old result stays with the task it was always about, and the new task
    # sees only its own — nothing lost, nothing moved.
    assert [r.gate for r in ledger.task_results(1)] == ["tests"]
    assert [r.gate for r in ledger.task_results(fresh)] == ["lint"]
    ledger.close()


def test_a_ledger_that_predates_attempts_gains_the_reference(tmp_path):
    """The backfill protects the data; it does not deliver the constraint.
    `CREATE TABLE IF NOT EXISTS` is a no-op on a v0.5 `gate_results`, so without
    the rebuild the old convention stays representable on the one ledger that
    actually exists — and the test above passes only because it starts fresh."""
    path = tmp_path / "old.db"
    before = SCHEMA.replace(
        "attempt_id     INTEGER REFERENCES attempts(attempt_id),",
        "attempt_id     INTEGER,",
    )
    assert "REFERENCES attempts" not in before  # otherwise this proves nothing
    old = sqlite3.connect(path)
    old.executescript(before)
    old.execute("DROP TABLE attempts")
    old.execute("INSERT INTO repos (name, origin, mirror_path) VALUES ('r','o','/m')")
    old.execute("INSERT INTO runs (repo_id, base_sha) VALUES (1, 'a')")
    old.execute(
        """INSERT INTO tasks (run_id, spec_id, spec_sha, state, branch)
           VALUES (1, 'SA-0001', 's', 'READY_FOR_REVIEW', 'saffron/SA-0001')"""
    )
    old.execute(
        "INSERT INTO gate_results (attempt_id, gate, status) VALUES (1, 'tests', 'pass')"
    )
    old.commit()
    old.close()

    ledger = Ledger(path)
    with pytest.raises(sqlite3.IntegrityError):
        ledger.record_gate_result(
            GateResult(gate="lint", status="pass"), attempt_id=90210
        )
    # The rebuild copied, it did not lose — and the index the DROP took is back.
    assert [r.gate for r in ledger.task_results(1)] == ["tests"]
    assert ledger._db.execute(
        "SELECT 1 FROM sqlite_master WHERE name = 'gate_results_by_attempt'"
    ).fetchone()
    ledger.close()


def test_the_batches_table_carries_exactly_the_fields_4_2_1_names(ledger):
    """§4.2.1: `(batch_id, started_at, ended_at, budget_usd, spent_usd_est,
    until_ts, status)` and no others — `concurrency` waits until K has a
    second position."""
    columns = {
        row["name"]
        for row in ledger._db.execute("PRAGMA table_info(batches)").fetchall()
    }
    assert columns == {
        "batch_id",
        "started_at",
        "ended_at",
        "budget_usd",
        "spent_usd_est",
        "until_ts",
        "status",
    }


def test_a_batch_status_outside_the_four_stop_reasons_is_rejected(ledger):
    """One row per stop condition — `DRAINED`, `BUDGET`, `UNTIL`,
    `INFRASTRUCTURE` — and nothing else. No `create_batch` method exists yet
    (the spec that adds the loop adds it with its caller), so this goes
    through `ledger._db` directly."""
    for status in ("DRAINED", "BUDGET", "UNTIL", "INFRASTRUCTURE"):
        ledger._db.execute(
            "INSERT INTO batches (budget_usd, status) VALUES (50, ?)", (status,)
        )
    with pytest.raises(sqlite3.IntegrityError):
        ledger._db.execute(
            "INSERT INTO batches (budget_usd, status) VALUES (50, 'CRASHED')"
        )


def test_a_run_created_outside_a_batch_has_a_null_batch_id(ledger):
    """`runs.batch_id` is nullable, and a run minted with no `batch_id`
    argument leaves it NULL rather than inventing a batch that did not
    happen."""
    repo_id = ledger.upsert_repo("r", "/o", "/m.git", policy_sha="p" * 64)
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    row = ledger._db.execute(
        "SELECT batch_id FROM runs WHERE run_id = ?", (run_id,)
    ).fetchone()
    assert row["batch_id"] is None


def test_a_run_created_inside_a_batch_carries_its_batch_id(ledger):
    """The other half, and the one that makes the parameter load-bearing.
    Without it, discarding the caller's `batch_id` at the INSERT — binding
    `None` unconditionally — keeps every other test in this change green while
    defeating the only reason the column exists: grouping a run into the batch
    that ran it (§4.2.1). Raw `batches` insert because no `create_batch` method
    exists yet; the spec that adds the loop adds it with its caller."""
    repo_id = ledger.upsert_repo("r", "/o", "/m.git", policy_sha="p" * 64)
    cursor = ledger._db.execute("INSERT INTO batches (budget_usd) VALUES (50)")
    batch_id = cursor.lastrowid
    run_id = ledger.create_run(repo_id, base_sha="a" * 40, batch_id=batch_id)
    row = ledger._db.execute(
        "SELECT batch_id FROM runs WHERE run_id = ?", (run_id,)
    ).fetchone()
    assert row["batch_id"] == batch_id


def test_a_batch_still_running_has_no_status_yet(ledger):
    """The schema comment says the CHECK is satisfied by NULL, so a row for a
    batch that has not stopped is neither a violation nor a fifth reason.
    Nothing asserted it, and `NOT NULL` on `status` would keep every other
    test here green while making an in-flight batch unrecordable — which is
    the row `SA-0049` writes at start and completes at stop."""
    ledger._db.execute("INSERT INTO batches (budget_usd) VALUES (50)")
    row = ledger._db.execute(
        "SELECT status, ended_at, spent_usd_est FROM batches"
    ).fetchone()
    assert row["status"] is None
    assert row["ended_at"] is None


def test_a_ledger_built_by_the_previous_schema_gains_batch_id(tmp_path):
    """`CREATE TABLE IF NOT EXISTS` does not alter, so a database that already
    holds `runs` needs the guarded `ALTER TABLE` this module already uses for
    `pushed_sha` and `pr_url` — this time on `runs`, not `tasks`."""
    path = tmp_path / "old.db"
    before = SCHEMA.replace(
        "    batch_id   INTEGER REFERENCES batches(batch_id),\n", ""
    )
    runs_columns = before.split("CREATE TABLE IF NOT EXISTS runs")[1].split(");")[0]
    assert "batch_id" not in runs_columns  # otherwise this test proves nothing
    old = sqlite3.connect(path)
    old.executescript(before)
    old.execute("DROP TABLE batches")  # the previous schema never had it either
    old.commit()
    old.close()

    ledger = Ledger(path)
    columns = {
        row["name"] for row in ledger._db.execute("PRAGMA table_info(runs)").fetchall()
    }
    assert "batch_id" in columns
    ledger.close()


def test_a_ledger_built_by_the_previous_schema_still_opens_and_writes(tmp_path):
    """The property that makes this safe to land on a database holding every
    task this repo has run: a ledger written before `batches` existed opens,
    reads, and accepts a new run."""
    path = tmp_path / "old.db"
    before = SCHEMA.replace(
        "    batch_id   INTEGER REFERENCES batches(batch_id),\n", ""
    )
    runs_columns = before.split("CREATE TABLE IF NOT EXISTS runs")[1].split(");")[0]
    assert "batch_id" not in runs_columns  # otherwise this test proves nothing
    old = sqlite3.connect(path)
    old.executescript(before)
    old.execute("DROP TABLE batches")
    old.execute("INSERT INTO repos (name, origin, mirror_path) VALUES ('r', 'o', '/m')")
    old.execute("INSERT INTO runs (repo_id, base_sha) VALUES (1, 'a')")
    old.commit()
    old.close()

    ledger = Ledger(path)
    run_id = ledger.create_run(1, base_sha="b" * 40)
    row = ledger._db.execute(
        "SELECT batch_id FROM runs WHERE run_id = ?", (run_id,)
    ).fetchone()
    assert row["batch_id"] is None
    ledger.close()


def _schema_without_policy_sha() -> str:
    """`tasks` minus `policy_sha` — the shape a ledger written before this
    change actually has. Shared by the migration test below and the
    no-backfill test, rather than building the fixture twice."""
    before = SCHEMA.replace("    policy_sha TEXT,\n", "")
    # `repos` carries its own, unrelated `policy_sha` column (§4.1), so scope
    # the check to `tasks`. Asserting absence of the literal `replace` just
    # searched for cannot fail — `repos` spells it with two spaces and `tasks`
    # with one, so a reflow of either would make the replace a silent no-op.
    tasks_columns = before.split("CREATE TABLE IF NOT EXISTS tasks")[1].split(");")[0]
    assert "policy_sha" not in tasks_columns  # otherwise this test proves nothing
    return before


def test_a_ledger_built_by_the_previous_schema_gains_policy_sha(tmp_path):
    """`tasks` carries a nullable `policy_sha`, added the way a column on an
    existing table has to be — the guarded `ALTER TABLE` this module already
    uses, never `CREATE TABLE IF NOT EXISTS`, which does not alter."""
    path = tmp_path / "old.db"
    old = sqlite3.connect(path)
    old.executescript(_schema_without_policy_sha())
    old.commit()
    old.close()

    ledger = Ledger(path)
    columns = {
        row["name"] for row in ledger._db.execute("PRAGMA table_info(tasks)").fetchall()
    }
    assert "policy_sha" in columns
    ledger.close()


def test_an_existing_task_is_not_backfilled_with_a_policy_sha(tmp_path):
    """A task row created before this change reads back with a NULL
    `policy_sha`, never a value invented for a task nobody observed."""
    path = tmp_path / "old.db"
    old = sqlite3.connect(path)
    old.executescript(_schema_without_policy_sha())
    old.execute("INSERT INTO repos (name, origin, mirror_path) VALUES ('r', 'o', '/m')")
    old.execute("INSERT INTO runs (repo_id, base_sha) VALUES (1, 'a')")
    old.execute(
        "INSERT INTO tasks (run_id, spec_id, spec_sha, state) "
        "VALUES (1, 'SA-0016', 's', 'QUEUED')"
    )
    old.commit()
    old.close()

    ledger = Ledger(path)
    row = ledger._db.execute("SELECT policy_sha FROM tasks").fetchone()
    assert row["policy_sha"] is None
    ledger.close()


def test_the_schema_adds_no_column_that_nothing_reads(ledger):
    """§4.2.1's two explicit cuts: `batches` has no `concurrency`, and `tasks`
    gains no `priority` — both would be item 18's pattern wearing a schema, a
    column written at scan and read by nobody."""
    batches_columns = {
        row["name"]
        for row in ledger._db.execute("PRAGMA table_info(batches)").fetchall()
    }
    tasks_columns = {
        row["name"] for row in ledger._db.execute("PRAGMA table_info(tasks)").fetchall()
    }
    # A table that doesn't exist trivially satisfies "has no such column" —
    # assert `batches` actually landed before asserting what it left out, or
    # this passes just as well against the schema this spec starts from.
    assert batches_columns == {
        "batch_id",
        "started_at",
        "ended_at",
        "budget_usd",
        "spent_usd_est",
        "until_ts",
        "status",
    }
    assert "concurrency" not in batches_columns
    assert "priority" not in tasks_columns


def test_an_attempt_against_no_task_raises_rather_than_naming_another(ledger, task):
    """`lastrowid` reports the connection's previous insert, so a select that
    matched nothing still hands back an id — one that exists, belongs to another
    attempt, and satisfies the foreign key."""
    _, task_id = task
    real = ledger.open_attempt(task_id)
    with pytest.raises(ValueError):
        ledger.open_attempt(90210)
    assert [row["attempt_id"] for row in ledger.attempts(task_id)] == [real]


def test_an_opened_batch_is_in_flight_with_no_stop_reason(ledger):
    """A batch can be opened. The row carries its budget and its until, and
    is in flight: no status and no end — §4.2.1's four stop reasons describe
    how a batch *ended*, and a batch that has not ended has none of them."""
    batch_id = ledger.create_batch(budget_usd=50, until_ts="2026-09-06T06:00:00")
    row = ledger._db.execute(
        "SELECT budget_usd, until_ts, status, ended_at, spent_usd_est FROM batches"
        " WHERE batch_id = ?",
        (batch_id,),
    ).fetchone()
    assert row["budget_usd"] == 50
    # Normalised, not stored verbatim — see the sortability test below.
    assert row["until_ts"] == "2026-09-06 06:00:00"
    assert row["status"] is None
    assert row["ended_at"] is None
    assert row["spent_usd_est"] is None


def test_an_until_sorts_against_the_timestamps_it_will_be_compared_with(ledger):
    """`until_ts` is the only timestamp a caller supplies, and the schema
    comment promises every one of them is `datetime('now')`-shaped and
    "sortable as text". Stored verbatim it was neither: an ISO `T` string
    sorts *after* a space-separated one for the same night, so an `ended_at`
    of 23:00 compared as text against an `until_ts` of 06:30 says the batch
    ended before its own deadline.

    Nothing compares them in SQL yet — the loop compares in Python — which is
    exactly why this is pinned now rather than after §6 renders the window."""
    batch_id = ledger.create_batch(budget_usd=50, until_ts="2026-09-06T06:30:00")
    ledger.close_batch(batch_id, "UNTIL")
    row = ledger._db.execute(
        "SELECT until_ts, ended_at FROM batches WHERE batch_id = ?", (batch_id,)
    ).fetchone()

    # Both spellings agree, so text order is time order.
    assert row["until_ts"] == "2026-09-06 06:30:00"
    assert row["ended_at"] < row["until_ts"]
    later = ledger._db.execute(
        "SELECT ? < ? AS ordered", ("2026-09-06 06:30:00", "2026-09-06 23:00:00")
    ).fetchone()
    assert later["ordered"] == 1


def test_closing_a_batch_records_its_stop_reason_and_end(ledger):
    """Modelled on `finish_run`, which does the same for a run and is the
    shape this repo already uses."""
    batch_id = ledger.create_batch(budget_usd=50)
    ledger.close_batch(batch_id, "DRAINED")
    row = ledger._db.execute(
        "SELECT status, ended_at FROM batches WHERE batch_id = ?", (batch_id,)
    ).fetchone()
    assert row["status"] == "DRAINED"
    assert row["ended_at"] is not None


def test_closing_a_batch_with_an_invented_stop_reason_is_refused(ledger):
    """The CHECK already says so; this proves the writer surfaces it instead
    of swallowing it."""
    batch_id = ledger.create_batch(budget_usd=50)
    with pytest.raises(sqlite3.IntegrityError):
        ledger.close_batch(batch_id, "CRASHED")


def test_closing_a_batch_derives_and_stores_its_spend(ledger):
    """The spend it writes is the reader's return value bound as a
    parameter, never a second copy of the join: `batches` -> `runs.batch_id`
    -> `tasks.run_id` -> `attempts.cost_usd_est`.

    A second batch's own attempts are also recorded, in the same ledger,
    before the first is closed — the CHECK, the `WHERE r.batch_id = ?`
    filter this exercises, is the only thing standing between one night's
    stored spend and a running total of every night the ledger has ever
    seen. Dropping it would still sum only the rows that exist in a fresh
    fixture; it would not still sum only the first batch's rows."""
    batch_id = ledger.create_batch(budget_usd=50)
    repo_id = ledger.upsert_repo("r", "/o", "/m.git", policy_sha="p" * 64)
    run_id = ledger.create_run(repo_id, base_sha="a" * 40, batch_id=batch_id)
    task_id = ledger.create_task(
        run_id, spec_id="SA-0001", spec_sha="s" * 40, branch="saffron/SA-0001"
    )
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

    other_batch = ledger.create_batch(budget_usd=50)
    other_run = ledger.create_run(repo_id, base_sha="b" * 40, batch_id=other_batch)
    other_task = ledger.create_task(
        other_run, spec_id="SA-0002", spec_sha="t" * 40, branch="saffron/SA-0002"
    )
    other_attempt = ledger.open_attempt(other_task)
    ledger.close_attempt(
        other_attempt,
        session_id="s-2",
        subtype="success",
        terminal_reason=None,
        num_turns=1,
        cost_usd_est=9.00,
    )

    ledger.close_batch(batch_id, "DRAINED")
    row = ledger._db.execute(
        "SELECT spent_usd_est FROM batches WHERE batch_id = ?", (batch_id,)
    ).fetchone()
    assert row["spent_usd_est"] == 0.75


def test_a_batch_closed_with_no_runs_stores_zero_not_null(ledger):
    """The empty sum is a real answer about a night that spent nothing, and
    NULL is reserved for the batch still running."""
    batch_id = ledger.create_batch(budget_usd=50)
    ledger.close_batch(batch_id, "DRAINED")
    row = ledger._db.execute(
        "SELECT spent_usd_est FROM batches WHERE batch_id = ?", (batch_id,)
    ).fetchone()
    assert row["spent_usd_est"] == 0.0


def test_a_batchs_runs_are_readable_from_the_batch(ledger):
    """A reader returns the runs a batch is made of, so a night can be
    walked from its own row — through the new reader, never raw SQL."""
    batch_id = ledger.create_batch(budget_usd=50)
    repo_id = ledger.upsert_repo("r", "/o", "/m.git", policy_sha="p" * 64)
    first = ledger.create_run(repo_id, base_sha="a" * 40, batch_id=batch_id)
    second = ledger.create_run(repo_id, base_sha="b" * 40, batch_id=batch_id)
    other_batch = ledger.create_batch(budget_usd=50)
    ledger.create_run(repo_id, base_sha="c" * 40, batch_id=other_batch)

    rows = ledger.batch_runs(batch_id)

    assert [r["run_id"] for r in rows] == [first, second]


def test_a_run_can_be_attached_to_its_batch_after_the_fact(ledger):
    """`create_run` accepts a batch id, but the only call that mints a run
    passes none — this stamps the fact on after the row already exists, the
    shape `record_push` and `set_task_package` already use on `tasks`."""
    repo_id = ledger.upsert_repo("r", "/o", "/m.git", policy_sha="p" * 64)
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    batch_id = ledger.create_batch(budget_usd=50)

    ledger.attach_run_to_batch(run_id, batch_id)

    row = ledger._db.execute(
        "SELECT batch_id FROM runs WHERE run_id = ?", (run_id,)
    ).fetchone()
    assert row["batch_id"] == batch_id
    assert [r["run_id"] for r in ledger.batch_runs(batch_id)] == [run_id]


def test_a_running_batchs_spend_is_readable_before_it_closes(ledger):
    """The same derivation the close performs is readable while the batch is
    still running, so the loop's budget gate reads its spend back rather
    than keeping a tally.

    A second, unrelated batch also has attempts recorded against it in the
    same ledger, so this only passes if `batch_spend` actually filters by
    `batch_id` rather than summing every attempt the ledger has ever seen."""
    batch_id = ledger.create_batch(budget_usd=50)
    repo_id = ledger.upsert_repo("r", "/o", "/m.git", policy_sha="p" * 64)
    run_id = ledger.create_run(repo_id, base_sha="a" * 40, batch_id=batch_id)
    task_id = ledger.create_task(
        run_id, spec_id="SA-0001", spec_sha="s" * 40, branch="saffron/SA-0001"
    )
    attempt_id = ledger.open_attempt(task_id)
    ledger.close_attempt(
        attempt_id,
        session_id="s-1",
        subtype="success",
        terminal_reason=None,
        num_turns=1,
        cost_usd_est=1.25,
    )

    other_batch = ledger.create_batch(budget_usd=50)
    other_run = ledger.create_run(repo_id, base_sha="b" * 40, batch_id=other_batch)
    other_task = ledger.create_task(
        other_run, spec_id="SA-0002", spec_sha="t" * 40, branch="saffron/SA-0002"
    )
    other_attempt = ledger.open_attempt(other_task)
    ledger.close_attempt(
        other_attempt,
        session_id="s-2",
        subtype="success",
        terminal_reason=None,
        num_turns=1,
        cost_usd_est=9.00,
    )

    assert ledger.batch_spend(batch_id) == 1.25
    row = ledger._db.execute(
        "SELECT status, ended_at FROM batches WHERE batch_id = ?", (batch_id,)
    ).fetchone()
    assert row["status"] is None
    assert row["ended_at"] is None


def test_attaching_a_run_that_does_not_exist_raises_rather_than_passing(ledger):
    """The stamp that decides whether a night's spend is measurable at all.

    An unknown `batch_id` already hit the foreign key; an unknown `run_id`
    matched zero rows and returned cleanly. That asymmetry is the shape of the
    failure the method exists to prevent — `runs.batch_id` written by nobody,
    every join through it empty, and `batch_spend` reporting 0.0 for a night
    that really spent, so the budget gate never fires."""
    batch_id = ledger.create_batch(budget_usd=50)
    with pytest.raises(ValueError, match="no run 9999"):
        ledger.attach_run_to_batch(9999, batch_id)


def test_closing_a_batch_that_does_not_exist_raises_rather_than_passing(ledger):
    """Same hole one table over: a silent close leaves the real row open, and
    an open row is the one state that cannot be told from a night still
    running."""
    with pytest.raises(ValueError, match="no batch 9999"):
        ledger.close_batch(9999, "DRAINED")


def test_a_refused_stop_reason_leaves_no_write_lock_behind(ledger, tmp_path):
    """`close_batch` is documented to surface `IntegrityError` on a status
    outside the four stop reasons — and a failed UPDATE has already had
    sqlite3 issue an implicit BEGIN. Without the rollback the connection holds
    the write lock until it next commits, and every other process on the
    ledger gets `database is locked`: `saffron reconcile`, the morning
    `saffron queue`."""
    batch_id = ledger.create_batch(budget_usd=50)
    with pytest.raises(sqlite3.IntegrityError):
        ledger.close_batch(batch_id, "NOT_A_STOP_REASON")

    assert ledger._db.in_transaction is False
    # A second connection can still write, which is the fact that matters.
    other = sqlite3.connect(tmp_path / "ledger.db", timeout=1)
    other.execute("UPDATE batches SET budget_usd = 51 WHERE batch_id = ?", (batch_id,))
    other.commit()
    other.close()


def test_the_high_water_mark_is_the_greatest_run_id(ledger):
    """`saffron/batch.py` reads this immediately before a candidate runs, so a
    run minted by a call that then raised can be told from one that already
    existed. It was reaching into `ledger._db` for it."""
    assert ledger.max_run_id() == 0
    repo_id = ledger.upsert_repo("r", "/o", "/m.git", policy_sha="p" * 64)
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    assert ledger.max_run_id() == run_id


def test_only_runs_minted_after_the_mark_are_swept_into_the_batch(ledger):
    """The sweep is scoped to `run_id > since_run_id`, not to every
    `batch_id IS NULL` row: a ledger accumulates plenty of those from
    `saffron cell` and `replay.py`, and folding them in would charge an
    unrelated past run's spend to tonight's budget."""
    repo_id = ledger.upsert_repo("r", "/o", "/m.git", policy_sha="p" * 64)
    stale = ledger.create_run(repo_id, base_sha="a" * 40)  # an earlier attended run
    batch_id = ledger.create_batch(budget_usd=50)
    high_water = ledger.max_run_id()
    minted = ledger.create_run(repo_id, base_sha="b" * 40)  # what the crash left

    assert ledger.attach_orphan_runs_to_batch(batch_id, high_water) == 1
    attached = {row["run_id"] for row in ledger.batch_runs(batch_id)}
    assert attached == {minted}
    stale_row = ledger._db.execute(
        "SELECT batch_id FROM runs WHERE run_id = ?", (stale,)
    ).fetchone()
    assert stale_row["batch_id"] is None
