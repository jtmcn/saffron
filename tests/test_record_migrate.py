"""`saffron/record/migrate.py`. It appends a stored ledger's tasks, attempts,
gate results and findings as the facts a live run would have written. A fold
then gives them back (backlog item 170, the record design's §7)."""

from __future__ import annotations

import hashlib
import re
import sqlite3
import time
from collections import Counter
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from saffron.agents.findings import Finding
from saffron.gates.contract import Failure, GateResult
from saffron.ledger import Ledger
from saffron.record.contract import Fact
from saffron.record.memory import MemoryRecord


def _set(ledger: Ledger, sql: str, params: tuple) -> None:
    ledger._db.execute(sql, params)
    ledger._db.commit()


def _source(path: Path) -> Ledger:
    """A fresh `Ledger` at `path`, the shape every scenario below is built
    on top of."""
    return Ledger(path)


def _task(
    ledger: Ledger, repo_id: int, spec_id: str, *, risk: str | None = None
) -> tuple[int, int]:
    """A run and the one task on it, before any attempt or gate result."""
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    task_id = ledger.create_task(
        run_id,
        spec_id=spec_id,
        spec_sha="s" * 64,
        branch=f"saffron/{spec_id}",
        risk=risk,
    )
    return run_id, task_id


def _close(ledger: Ledger) -> None:
    ledger.close()


def _migrated(source_path: Path):
    from saffron.record.migrate import migrate

    record = MemoryRecord()
    return migrate(source_path, record), record


def _rows(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    return list(conn.execute(sql, params))


def _iso(stored: str) -> str:
    """A stored ledger time, as the offset form a live fact's `at` carries."""
    return datetime.fromisoformat(stored).replace(tzinfo=UTC).isoformat()


def test_a_migrated_ledger_folds_back_to_the_rows_its_tasks_held(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from saffron.record.fold import fold
    from saffron.record.migrate import migrate

    monkeypatch.setenv("TZ", "America/Los_Angeles")
    time.tzset()
    try:
        source = Ledger(tmp_path / "source.db")
        repo_id = source.upsert_repo("saffron", "/o", "/m.git", None)

        run1 = source.create_run(repo_id, base_sha="a" * 40)
        run2 = source.create_run(repo_id, base_sha="a" * 40)
        run3 = source.create_run(repo_id, base_sha="a" * 40)
        run4 = source.create_run(repo_id, base_sha="a" * 40)
        run5 = source.create_run(repo_id, base_sha="a" * 40)
        _set(
            source,
            "UPDATE runs SET started_at = ? WHERE run_id = ?",
            ("2026-01-01 08:00:00", run1),
        )
        _set(
            source,
            "UPDATE runs SET started_at = ? WHERE run_id = ?",
            ("2026-01-01 09:00:00", run2),
        )
        _set(
            source,
            "UPDATE runs SET started_at = ? WHERE run_id = ?",
            ("2026-01-01 10:00:00", run3),
        )
        _set(
            source,
            "UPDATE runs SET started_at = ? WHERE run_id = ?",
            ("2026-01-01 11:00:00", run4),
        )
        _set(
            source,
            "UPDATE runs SET started_at = ? WHERE run_id = ?",
            ("2026-01-01 12:00:00", run5),
        )

        batch_id = source.create_batch(budget_usd=20.0)
        source.attach_run_to_batch(run1, batch_id)

        # Task 1: standard (undeclared), batched, packaged with a diff stat,
        # merged, four findings in the four verdict/rebuttal shapes.
        task1 = source.create_task(
            run1,
            spec_id="SA-0001",
            spec_sha="s" * 64,
            branch="saffron/SA-0001",
            risk=None,
            budget_usd=12.5,
            policy_sha="p" * 64,
            prompt_sha="q" * 64,
        )
        a1 = source.open_attempt(task1, phase="IMPLEMENTING")
        source.close_attempt(
            a1,
            session_id="sess-1",
            model="m-1",
            subtype="success",
            terminal_reason="max_turns",
            num_turns=4,
            cost_usd_est=1.5,
            cost_floor_usd_est=1.25,
        )
        finding_ids = source.record_findings(
            task1,
            [
                Finding(
                    lens="l1",
                    severity="blocker",
                    file="a.py",
                    line=1,
                    claim="rebutted",
                    anchored=True,
                ),
                Finding(
                    lens="l1",
                    severity="concern",
                    file="a.py",
                    line=2,
                    claim="verdict alone",
                    anchored=True,
                ),
                Finding(
                    lens="l1",
                    severity="note",
                    file="a.py",
                    line=3,
                    claim="rebuttal alone",
                    anchored=True,
                ),
                Finding(
                    lens="l1",
                    severity="note",
                    file="a.py",
                    line=4,
                    claim="neither",
                    anchored=False,
                ),
            ],
        )
        source.record_rebuttal(finding_ids[0], verdict="confirmed", rebuttal="fixed")
        source.record_rebuttal(finding_ids[1], verdict="withdrawn", rebuttal=None)
        source.record_rebuttal(finding_ids[2], verdict=None, rebuttal="disagree")
        source.set_task_package(
            task1,
            "READY_FOR_REVIEW",
            "saffron/SA-0001",
            "b" * 40,
            "https://github.com/o/r/pull/1",
            added=10,
            removed=3,
        )
        source.record_merged_head(task1, "c" * 40)
        source.set_task_state(task1, "MERGED")

        # Task 2: elevated, pushed with no pull request, a closed attempt
        # after its last state (stale spend) and an open attempt.
        task2 = source.create_task(
            run2,
            spec_id="SA-0002",
            spec_sha="s" * 64,
            branch="saffron/SA-0002",
            risk="elevated",
        )
        a2a = source.open_attempt(task2, phase="IMPLEMENTING")
        source.close_attempt(
            a2a,
            session_id="sess-2a",
            subtype="success",
            terminal_reason=None,
            num_turns=2,
            cost_usd_est=2.0,
        )
        source.set_task_state(task2, "GATING")
        a2b = source.open_attempt(task2, phase="REPAIRING")
        source.close_attempt(
            a2b,
            session_id="sess-2b",
            subtype="success",
            terminal_reason=None,
            num_turns=3,
            cost_usd_est=3.0,
        )
        source.open_attempt(task2, phase="REVIEWING")
        source.record_push(task2, "d" * 40)

        # Task 3: no attempt, no push, updated_at set earlier than the rest.
        task3 = source.create_task(
            run3,
            spec_id="SA-0003",
            spec_sha="s" * 64,
            branch="saffron/SA-0003",
            risk=None,
        )
        source.set_task_state(task3, "DIAGNOSING")
        _set(
            source,
            "UPDATE tasks SET updated_at = ? WHERE task_id = ?",
            ("2026-01-01 01:00:00", task3),
        )

        # Task 4: MERGE_FAILED, empty pr_url, branch moved by the package.
        task4 = source.create_task(
            run4,
            spec_id="SA-0004",
            spec_sha="s" * 64,
            branch="saffron/SA-0004",
            risk="elevated",
        )
        source.set_task_package(
            task4, "MERGE_FAILED", "saffron/SA-0004-retry", "e" * 40, ""
        )

        # Task 5: packaged in PACKAGE's exhausted mode, with a pull request.
        task5 = source.create_task(
            run5, spec_id="SA-0005", spec_sha="s" * 64, branch="saffron/SA-0005"
        )
        source.set_task_package(
            task5, "EXHAUSTED", "saffron/SA-0005", "f" * 40, "https://x/pull/5"
        )

        source_path = tmp_path / "source.db"
        keys = {
            n: source._db.execute(
                "SELECT record_key FROM tasks WHERE task_id = ?", (tid,)
            ).fetchone()["record_key"]
            for n, tid in [(1, task1), (2, task2), (3, task3), (4, task4), (5, task5)]
        }
        source.close()

        record = MemoryRecord()
        result = migrate(source_path, record)
        assert result.migrated == [keys[1], keys[2], keys[3], keys[4], keys[5]]
        assert result.refused == []

        rebuilt = Ledger(tmp_path / "rebuilt.db")
        fold(record, rebuilt)

        reread = sqlite3.connect(source_path)
        reread.row_factory = sqlite3.Row
        task_cols = (
            "record_key, spec_id, spec_sha, state, risk, branch, budget_usd,"
            " policy_sha, prompt_sha, pushed_sha, pr_url, merged_head_sha,"
            " added, removed, updated_at"
        )
        spend = (
            "(SELECT COALESCE(SUM(a.cost_usd_est), 0.0) FROM attempts a"
            " WHERE a.task_id = t.task_id) AS spent"
        )
        before = Counter(
            tuple(r)
            for r in reread.execute(f"SELECT {task_cols}, {spend} FROM tasks t")
        )
        after = Counter(
            tuple(r)
            for r in rebuilt._db.execute(f"SELECT {task_cols}, {spend} FROM tasks t")
        )
        assert before == after

        attempt_cols = (
            "t.record_key, a.phase, a.n, a.session_id, a.model, a.subtype,"
            " a.terminal_reason, a.num_turns, a.cost_usd_est, a.started_at,"
            " a.ended_at, a.cost_floor_usd_est"
        )
        before_a = Counter(
            tuple(r)
            for r in reread.execute(
                f"SELECT {attempt_cols} FROM attempts a"
                " JOIN tasks t ON t.task_id = a.task_id"
            )
        )
        after_a = Counter(
            tuple(r)
            for r in rebuilt._db.execute(
                f"SELECT {attempt_cols} FROM attempts a"
                " JOIN tasks t ON t.task_id = a.task_id"
            )
        )
        assert before_a == after_a

        finding_cols = (
            "t.record_key, f.lens, f.severity, f.file, f.line, f.claim,"
            " f.anchored, f.verdict, f.rebuttal"
        )
        before_f = Counter(
            tuple(r)
            for r in reread.execute(
                f"SELECT {finding_cols} FROM findings f"
                " JOIN tasks t ON t.task_id = f.task_id"
            )
        )
        after_f = Counter(
            tuple(r)
            for r in rebuilt._db.execute(
                f"SELECT {finding_cols} FROM findings f"
                " JOIN tasks t ON t.task_id = f.task_id"
            )
        )
        assert before_f == after_f

        ordered = [
            row["spec_id"]
            for row in rebuilt._db.execute("SELECT spec_id FROM tasks ORDER BY task_id")
        ]
        assert ordered == ["SA-0001", "SA-0002", "SA-0003", "SA-0004", "SA-0005"]

        all_facts: list[Fact] = []
        for key in keys.values():
            all_facts.extend(record.read(key))
        assert all_facts
        for fact in all_facts:
            assert fact.repo == "saffron"
            assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+00:00", fact.at)
            if fact.task_key == keys[1]:
                assert fact.batch_key == str(batch_id)
            else:
                assert fact.batch_key is None

        def _created(key: str) -> Fact:
            return next(f for f in record.read(key) if f.kind == "task_created")

        assert _created(keys[1]).payload["risk"] is None
        assert _created(keys[2]).payload["risk"] == "elevated"
        assert _created(keys[3]).payload["risk"] is None
        assert _created(keys[4]).payload["risk"] == "elevated"
        assert _created(keys[1]).at == "2026-01-01T08:00:00+00:00"

        def _package(key: str) -> Fact:
            return next(f for f in record.read(key) if f.kind == "task_package")

        # Packaged state, not the later-reconciled column: task1 reads
        # MERGED, but its package fact must say READY_FOR_REVIEW.
        assert _package(keys[1]).payload["state"] == "READY_FOR_REVIEW"
        assert _package(keys[1]).payload["added"] == 10
        assert _package(keys[1]).payload["removed"] == 3
        assert _package(keys[4]).payload["state"] == "MERGE_FAILED"
        assert _package(keys[4]).payload["added"] is None
        assert _package(keys[4]).payload["removed"] is None
        assert _package(keys[5]).payload["state"] == "EXHAUSTED"

        rebuilt.close()
    finally:
        monkeypatch.undo()
        time.tzset()


def test_a_rerun_completes_a_migration_cut_short_and_refuses_a_record_that_disagrees(
    tmp_path: Path,
) -> None:
    from saffron.record.migrate import migrate

    source = Ledger(tmp_path / "source.db")
    repo_id = source.upsert_repo("saffron", "/o", "/m.git", None)
    task_ids = []
    for i in range(1, 7):
        run_id = source.create_run(repo_id, base_sha="a" * 40)
        task_id = source.create_task(
            run_id,
            spec_id=f"SA-000{i}",
            spec_sha="s" * 64,
            branch=f"saffron/SA-000{i}",
        )
        # attempt_closed is the real third fact, with its own cost_usd_est.
        # `migrate` also appends a trailing task_state, four facts in all.
        attempt_id = source.open_attempt(task_id, phase="IMPLEMENTING")
        source.close_attempt(
            attempt_id,
            session_id=f"sess-{i}",
            subtype="success",
            terminal_reason=None,
            num_turns=1,
            cost_usd_est=float(i),
        )
        task_ids.append(task_id)
    keys = [
        source._db.execute(
            "SELECT record_key FROM tasks WHERE task_id = ?", (tid,)
        ).fetchone()["record_key"]
        for tid in task_ids
    ]
    source_path = tmp_path / "source.db"
    source.close()

    truth = MemoryRecord()
    migrate(source_path, truth)
    expected = {
        key: [Fact.from_json(f.to_json()) for f in truth.read(key)] for key in keys
    }
    for facts in expected.values():
        assert len(facts) == 4

    seeded = MemoryRecord()
    # key 1: holds nothing.
    # key 2: holds the true first two facts only, not the third.
    for fact in expected[keys[1]][:2]:
        seeded.append(keys[1], fact)
    # key 3: holds every true fact.
    for fact in expected[keys[2]]:
        seeded.append(keys[2], fact)
    # key 4: a corrupted first fact, then the true second.
    bad_first = replace(
        expected[keys[3]][0],
        payload={**expected[keys[3]][0].payload, "spec_sha": "x" * 64},
    )
    seeded.append(keys[3], bad_first)
    seeded.append(keys[3], expected[keys[3]][1])
    # key 5: the true first two facts, then a corrupted third.
    seeded.append(keys[4], expected[keys[4]][0])
    seeded.append(keys[4], expected[keys[4]][1])
    bad_third = replace(
        expected[keys[4]][2],
        payload={**expected[keys[4]][2].payload, "cost_usd_est": 999.0},
    )
    seeded.append(keys[4], bad_third)
    # key 6: the true first two facts, then a third that differs in `at` alone.
    seeded.append(keys[5], expected[keys[5]][0])
    seeded.append(keys[5], expected[keys[5]][1])
    bad_at = replace(expected[keys[5]][2], at="2099-01-01T00:00:00+00:00")
    seeded.append(keys[5], bad_at)

    held_before = {key: list(seeded.read(key)) for key in keys}

    result = migrate(source_path, seeded)

    assert result.migrated == [keys[0], keys[1], keys[2]]
    assert [key for key, _ in result.refused] == [keys[3], keys[4], keys[5]]

    for key in (keys[0], keys[1], keys[2]):
        assert seeded.read(key) == expected[key]
    for key in (keys[3], keys[4], keys[5]):
        assert seeded.read(key) == held_before[key]

    # A held fact differing in `batch_key` alone disagrees too: facts compare whole.
    other = MemoryRecord()
    other.append(keys[0], replace(expected[keys[0]][0], batch_key="9"))
    assert [key for key, _ in migrate(source_path, other).refused] == [keys[0]]


def test_a_ledger_that_predates_the_head_count_migrates_and_is_left_unwritten(
    tmp_path: Path,
) -> None:
    from saffron.record.migrate import migrate

    source_path = tmp_path / "source.db"
    source = Ledger(source_path)
    repo_id = source.upsert_repo("saffron", "/o", "/m.git", None)
    run_id = source.create_run(repo_id, base_sha="a" * 40)
    task_id = source.create_task(
        run_id, spec_id="SA-0001", spec_sha="s" * 64, branch="saffron/SA-0001"
    )
    attempt_id = source.open_attempt(task_id, phase="IMPLEMENTING")
    source.close_attempt(
        attempt_id,
        session_id="s",
        subtype="success",
        terminal_reason=None,
        num_turns=1,
        cost_usd_est=1.0,
    )
    source.set_task_state(task_id, "READY_FOR_REVIEW")
    source._db.execute("ALTER TABLE gate_results DROP COLUMN failures_at_head")
    source._db.execute("ALTER TABLE attempts DROP COLUMN earned_risk")
    source._db.commit()
    source.close()

    before_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()

    record = MemoryRecord()
    result = migrate(source_path, record)
    assert len(result.migrated) == 1
    assert result.refused == []

    after_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    assert after_hash == before_hash

    missing = tmp_path / "missing.db"
    with pytest.raises(sqlite3.OperationalError):
        migrate(missing, MemoryRecord())
    assert not missing.exists()


def _assert_gate_results_follow_their_attempt(facts: list[Fact]) -> None:
    """Every `gate_result` fact's immediate predecessor, other `gate_result`
    facts aside, is its own attempt's fact: `attempt_closed` where that
    attempt closed anywhere in `facts`, `attempt_opened` otherwise
    (problem 1). A closed attempt's own `gate_result` facts must follow
    its close, never its open."""
    closed_attempts = {
        (f.payload["phase"], f.payload["n"])
        for f in facts
        if f.kind == "attempt_closed"
    }
    last_non_gate: Fact | None = None
    for fact in facts:
        if fact.kind == "gate_result":
            assert last_non_gate is not None
            key = (fact.payload["phase"], fact.payload["n"])
            expected_kind = (
                "attempt_closed" if key in closed_attempts else "attempt_opened"
            )
            assert last_non_gate.kind == expected_kind
            assert (
                last_non_gate.payload["phase"],
                last_non_gate.payload["n"],
            ) == key
        else:
            last_non_gate = fact


def test_a_migrated_attempt_keeps_only_the_failures_its_runs_baseline_did_not_cancel(
    tmp_path: Path,
) -> None:
    from saffron.record.fold import fold

    source = _source(tmp_path / "source.db")
    repo_id = source.upsert_repo("saffron", "/o", "/m.git", None)

    # Another run, made first, whose "types" baseline failure shares attempt
    # 1's exactly (members 5 and 7): reading the wrong run's baseline would cancel it.
    other_run = source.create_run(repo_id, base_sha="a" * 40)
    source.record_gate_result(
        GateResult(
            gate="types",
            status="fail",
            tool="mypy 1.0",
            failures=[Failure(file="n.py", line=1, code="N1", message="")],
        ),
        run_id=other_run,
    )

    run1, task1 = _task(source, repo_id, "SA-0101")
    batch_id = source.create_batch(budget_usd=50.0)
    source.attach_run_to_batch(run1, batch_id)
    _set(
        source,
        "UPDATE runs SET started_at = ? WHERE run_id = ?",
        ("2026-02-01 08:00:00", run1),
    )

    # The run's own baseline: lint (two distinct failures), tests, witness
    # (a survivor), an empty types, and a revert skipped with no tool.
    source.record_gate_result(
        GateResult(
            gate="lint",
            status="fail",
            tool="ruff 1.0",
            failures=[
                Failure(file="a.py", line=10, code="E1", message="bad one"),
                Failure(file="b.py", line=20, code="E2", message="bad two"),
            ],
        ),
        run_id=run1,
    )
    source.record_gate_result(
        GateResult(
            gate="tests",
            status="fail",
            tool="pytest 8.0",
            failures=[Failure(file="shared.py", line=9, code="SAME", message="")],
        ),
        run_id=run1,
    )
    source.record_gate_result(
        GateResult(
            gate="witness",
            status="fail",
            tool="pytest 8.0",
            failures=[
                Failure(
                    file="w.py", line=5, code="survived-mutant", message="mutant lived"
                )
            ],
        ),
        run_id=run1,
    )
    source.record_gate_result(
        GateResult(gate="types", status="pass", tool="mypy 1.0", failures=[]),
        run_id=run1,
    )
    source.record_gate_result(
        GateResult(gate="revert", status="skip", tool=None, failures=[]),
        run_id=run1,
    )

    # Attempt 1 (closed): lint, witness, types and format, every one
    # uncounted, as a ledger predating SA-0220 would hold them.
    a1 = source.open_attempt(task1, phase="IMPLEMENTING")
    source.close_attempt(
        a1,
        session_id="s1",
        subtype="success",
        terminal_reason=None,
        num_turns=3,
        cost_usd_est=1.0,
    )
    source.record_gate_result(
        GateResult(
            gate="lint",
            status="fail",
            tool="ruff 1.0",
            failures=[
                Failure(file="a.py", line=99, code="E1", message="bad one"),
                Failure(file="b.py", line=20, code="E2", message="bad two"),
                Failure(file="b.py", line=21, code="E2", message="bad two"),
                Failure(file="shared.py", line=9, code="SAME", message=""),
            ],
        ),
        attempt_id=a1,
        baseline=[],
    )
    source.record_gate_result(
        GateResult(
            gate="witness",
            status="fail",
            tool="pytest 8.0",
            failures=[
                Failure(
                    file="w.py", line=5, code="survived-mutant", message="mutant lived"
                )
            ],
        ),
        attempt_id=a1,
        baseline=[],
    )
    source.record_gate_result(
        GateResult(
            gate="types",
            status="fail",
            tool="mypy 1.0",
            failures=[Failure(file="n.py", line=3, code="N1", message="")],
        ),
        attempt_id=a1,
        baseline=[],
    )
    source.record_gate_result(
        GateResult(
            gate="format", status="pass", tool="black 1.0", summary="", failures=[]
        ),
        attempt_id=a1,
        baseline=[],
    )

    # Attempt 2 (closed): three lint copies of one baseline failure.
    # A one-copy baseline leaves two, and earned_risk is stored elevated (member 8).
    a2 = source.open_attempt(task1, phase="REPAIRING")
    source.close_attempt(
        a2,
        session_id="s2",
        subtype="success",
        terminal_reason=None,
        num_turns=2,
        cost_usd_est=2.0,
    )
    source.record_gate_result(
        GateResult(
            gate="lint",
            status="fail",
            tool="ruff 1.0",
            failures=[
                Failure(file="a.py", line=10, code="E1", message="bad one"),
                Failure(file="a.py", line=11, code="E1", message="bad one"),
                Failure(file="a.py", line=12, code="E1", message="bad one"),
            ],
        ),
        attempt_id=a2,
        baseline=[
            GateResult(
                gate="lint",
                status="fail",
                tool="ruff 1.0",
                failures=[Failure(file="a.py", line=10, code="E1", message="bad one")],
            )
        ],
        earned_risk="elevated",
    )

    # Attempts 3-6: never closed (member counts: five results on the two
    # closed attempts above, seven on these four open ones).
    a3 = source.open_attempt(task1, phase="GATING")
    source.record_gate_result(
        GateResult(
            gate="lint",
            status="fail",
            tool="ruff 1.0",
            failures=[Failure(file="a.py", line=10, code="E1", message="bad one")],
        ),
        attempt_id=a3,
        baseline=[],
    )
    source.record_gate_result(
        GateResult(
            gate="tests",
            status="error",
            tool="pytest 8.0",
            summary="collection crashed",
            failures=[],
        ),
        attempt_id=a3,
        baseline=[],
    )

    a4 = source.open_attempt(task1, phase="GATING")
    source.record_gate_result(
        GateResult(
            gate="lint",
            status="fail",
            tool="ruff 2.0",
            failures=[Failure(file="a.py", line=10, code="E1", message="bad one")],
        ),
        attempt_id=a4,
        baseline=[],
    )

    a5 = source.open_attempt(task1, phase="GATING")
    source.record_gate_result(
        GateResult(gate="revert", status="pass", tool="revert-tool 1.0", failures=[]),
        attempt_id=a5,
        baseline=[],
    )
    source.record_gate_result(
        GateResult(
            gate="lint",
            status="fail",
            tool="ruff 1.0",
            failures=[Failure(file="a.py", line=10, code="E1", message="bad one")],
        ),
        attempt_id=a5,
        baseline=[],
    )

    a6 = source.open_attempt(task1, phase="GATING")
    source.record_gate_result(
        GateResult(gate="types", status="skip", tool=None, failures=[]),
        attempt_id=a6,
        baseline=[],
    )
    source.record_gate_result(
        GateResult(
            gate="lint",
            status="fail",
            tool="ruff 1.0",
            failures=[Failure(file="a.py", line=10, code="E1", message="bad one")],
        ),
        attempt_id=a6,
        baseline=[],
    )

    # Null every count but attempt 2's, plus the "types" failure's message
    # and "format"'s summary, which must round trip null (problem 1).
    for attempt_id in (a1, a3, a4, a5, a6):
        _set(
            source,
            "UPDATE gate_results SET failures_at_head = NULL WHERE attempt_id = ?",
            (attempt_id,),
        )
    _set(
        source,
        "UPDATE failures SET message = NULL WHERE file = 'n.py' AND code = 'N1'",
        (),
    )
    _set(
        source,
        "UPDATE gate_results SET summary = NULL WHERE attempt_id = ? AND gate = 'format'",
        (a1,),
    )

    # Distinct times throughout.
    _set(
        source,
        "UPDATE attempts SET started_at = ?, ended_at = ? WHERE attempt_id = ?",
        ("2026-02-01 08:10:00", "2026-02-01 08:20:00", a1),
    )
    _set(
        source,
        "UPDATE attempts SET started_at = ?, ended_at = ? WHERE attempt_id = ?",
        ("2026-02-01 08:30:00", "2026-02-01 08:40:00", a2),
    )
    _set(
        source,
        "UPDATE attempts SET started_at = ? WHERE attempt_id = ?",
        ("2026-02-01 08:50:00", a3),
    )
    _set(
        source,
        "UPDATE attempts SET started_at = ? WHERE attempt_id = ?",
        ("2026-02-01 09:00:00", a4),
    )
    _set(
        source,
        "UPDATE attempts SET started_at = ? WHERE attempt_id = ?",
        ("2026-02-01 09:10:00", a5),
    )
    _set(
        source,
        "UPDATE attempts SET started_at = ? WHERE attempt_id = ?",
        ("2026-02-01 09:20:00", a6),
    )
    _set(
        source,
        "UPDATE tasks SET updated_at = ? WHERE task_id = ?",
        ("2026-02-01 09:30:00", task1),
    )

    # A second, elevated task with one clean, closed attempt. Its own
    # earned_risk stays null, never defaulted from the task's risk (member 14).
    run2, task2 = _task(source, repo_id, "SA-0102", risk="elevated")
    a7 = source.open_attempt(task2, phase="IMPLEMENTING")
    source.close_attempt(
        a7,
        session_id="s7",
        subtype="success",
        terminal_reason=None,
        num_turns=1,
        cost_usd_est=1.0,
    )
    # Left counted (unlike a1/a3-a6): a zero stored count must stay 0, not
    # become null, through the "copy as stored" branch.
    source.record_gate_result(
        GateResult(gate="lint", status="pass", tool="ruff 1.0", failures=[]),
        attempt_id=a7,
        baseline=[],
    )
    _set(
        source,
        "UPDATE attempts SET started_at = ?, ended_at = ? WHERE attempt_id = ?",
        ("2026-02-01 10:00:00", "2026-02-01 10:10:00", a7),
    )
    _set(
        source,
        "UPDATE tasks SET updated_at = ? WHERE task_id = ?",
        ("2026-02-01 10:20:00", task2),
    )

    key1 = source._db.execute(
        "SELECT record_key FROM tasks WHERE task_id = ?", (task1,)
    ).fetchone()["record_key"]
    key2 = source._db.execute(
        "SELECT record_key FROM tasks WHERE task_id = ?", (task2,)
    ).fetchone()["record_key"]
    source_path = tmp_path / "source.db"
    _close(source)

    result, record = _migrated(source_path)
    assert sorted(result.migrated) == sorted([key1, key2])
    assert result.refused == []

    facts1 = record.read(key1)
    facts2 = record.read(key2)
    _assert_gate_results_follow_their_attempt(facts1)
    _assert_gate_results_follow_their_attempt(facts2)

    def _results(facts: list[Fact]) -> list[Fact]:
        return [f for f in facts if f.kind == "gate_result"]

    results1 = _results(facts1)
    results2 = _results(facts2)
    assert len(results1) == 12
    assert len(results2) == 1

    for fact in results1 + results2:
        assert fact.repo == "saffron"
        assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+00:00", fact.at)
    for fact in results1:
        assert fact.batch_key == str(batch_id)
    for fact in results2:
        assert fact.batch_key is None

    def _failures(fact: Fact) -> list[tuple[str, int | None, str, str | None]]:
        return [
            (f["file"], f["line"], f["code"], f["message"])
            for f in fact.payload["failures"]
        ]

    def _at(phase: str, n: int) -> list[Fact]:
        return [
            f for f in results1 if f.payload["phase"] == phase and f.payload["n"] == n
        ]

    lint1, witness1, types1, format1 = _at("IMPLEMENTING", 1)
    # a1 closed at 08:20. Its gate_result facts carry that, not its 08:10
    # start or the task's own 09:30 updated_at.
    for fact in (lint1, witness1, types1, format1):
        assert fact.at == _iso("2026-02-01 08:20:00")
    assert lint1.payload["gate"] == "lint"
    assert _failures(lint1) == [
        ("b.py", 21, "E2", "bad two"),
        ("shared.py", 9, "SAME", ""),
    ]
    assert lint1.payload["failures_at_head"] == 4
    assert lint1.payload["earned_risk"] is None

    assert witness1.payload["gate"] == "witness"
    assert _failures(witness1) == [("w.py", 5, "survived-mutant", "mutant lived")]
    assert witness1.payload["failures_at_head"] == 1

    assert types1.payload["gate"] == "types"
    assert _failures(types1) == [("n.py", 3, "N1", None)]
    assert types1.payload["failures_at_head"] == 1

    assert format1.payload["gate"] == "format"
    assert _failures(format1) == []
    assert format1.payload["failures_at_head"] == 0
    assert format1.payload["summary"] is None

    (lint2,) = _at("REPAIRING", 1)
    assert lint2.at == _iso("2026-02-01 08:40:00")
    assert _failures(lint2) == [
        ("a.py", 11, "E1", "bad one"),
        ("a.py", 12, "E1", "bad one"),
    ]
    assert lint2.payload["failures_at_head"] == 3
    assert lint2.payload["earned_risk"] == "elevated"

    lint3, tests3 = _at("GATING", 1)
    # a3 never closed, so its facts carry its 08:50 start.
    for fact in (lint3, tests3):
        assert fact.at == _iso("2026-02-01 08:50:00")
    assert lint3.payload["gate"] == "lint"
    assert _failures(lint3) == [("a.py", 10, "E1", "bad one")]
    assert lint3.payload["failures_at_head"] == 1
    assert tests3.payload["gate"] == "tests"
    assert tests3.payload["status"] == "error"
    assert _failures(tests3) == []

    (lint4,) = _at("GATING", 2)
    assert lint4.at == _iso("2026-02-01 09:00:00")
    assert lint4.payload["tool"] == "ruff 2.0"
    assert _failures(lint4) == [("a.py", 10, "E1", "bad one")]
    assert lint4.payload["failures_at_head"] == 1

    revert5, lint5 = _at("GATING", 3)
    for fact in (revert5, lint5):
        assert fact.at == _iso("2026-02-01 09:10:00")
    assert revert5.payload["gate"] == "revert"
    assert _failures(revert5) == []
    assert lint5.payload["gate"] == "lint"
    assert _failures(lint5) == []
    assert lint5.payload["failures_at_head"] == 1

    types6, lint6 = _at("GATING", 4)
    for fact in (types6, lint6):
        assert fact.at == _iso("2026-02-01 09:20:00")
    assert types6.payload["gate"] == "types"
    assert types6.payload["status"] == "skip"
    assert lint6.payload["gate"] == "lint"
    assert _failures(lint6) == [("a.py", 10, "E1", "bad one")]
    assert lint6.payload["failures_at_head"] == 1

    (lint7,) = results2
    # a7 closed at 10:10. Its fact carries that, not its 10:00 start or
    # task2's own 10:20 updated_at.
    assert lint7.at == _iso("2026-02-01 10:10:00")
    assert _failures(lint7) == []
    assert lint7.payload["failures_at_head"] == 0
    assert lint7.payload["earned_risk"] is None

    rebuilt = Ledger(tmp_path / "rebuilt.db")
    fold(record, rebuilt)
    attempt_cols = "t.record_key, a.phase, a.n, a.earned_risk"
    reread = sqlite3.connect(source_path)
    reread.row_factory = sqlite3.Row
    before = Counter(
        tuple(r)
        for r in reread.execute(
            f"SELECT {attempt_cols} FROM attempts a JOIN tasks t ON t.task_id = a.task_id"
        )
    )
    after = Counter(
        tuple(r)
        for r in rebuilt._db.execute(
            f"SELECT {attempt_cols} FROM attempts a JOIN tasks t ON t.task_id = a.task_id"
        )
    )
    assert before == after
    rebuilt.close()
    reread.close()


def test_a_task_whose_run_stores_a_gates_baseline_twice_is_refused_where_it_still_needs_subtracting(
    tmp_path: Path,
) -> None:
    def _baseline(ledger: Ledger, run_id: int, lint_count: int) -> None:
        for _ in range(lint_count):
            ledger.record_gate_result(
                GateResult(gate="lint", status="pass", tool="ruff 1.0", failures=[]),
                run_id=run_id,
            )
        ledger.record_gate_result(
            GateResult(gate="tests", status="pass", tool="pytest 8.0", failures=[]),
            run_id=run_id,
        )

    source = _source(tmp_path / "source.db")
    repo_id = source.upsert_repo("saffron", "/o", "/m.git", None)

    # Task 1: doubled baseline, every attempt result counted -> migrates.
    run1, task1 = _task(source, repo_id, "SA-0201")
    _baseline(source, run1, lint_count=2)
    a1 = source.open_attempt(task1, phase="IMPLEMENTING")
    source.record_gate_result(
        GateResult(gate="lint", status="pass", tool="ruff 1.0", failures=[]),
        attempt_id=a1,
        baseline=[],
    )

    # Task 2: doubled baseline, one counted and one uncounted -> refused.
    run2, task2 = _task(source, repo_id, "SA-0202")
    _baseline(source, run2, lint_count=2)
    a2 = source.open_attempt(task2, phase="IMPLEMENTING")
    source.record_gate_result(
        GateResult(gate="lint", status="pass", tool="ruff 1.0", failures=[]),
        attempt_id=a2,
        baseline=[],
    )
    source.record_gate_result(
        GateResult(gate="tests", status="pass", tool="pytest 8.0", failures=[]),
        attempt_id=a2,
        baseline=[],
    )
    _set(
        source,
        "UPDATE gate_results SET failures_at_head = NULL WHERE attempt_id = ? AND gate = 'tests'",
        (a2,),
    )

    # Task 3: doubled baseline, its one uncounted result's suite holds an
    # error. Still refused: an abort exempts nothing.
    run3, task3 = _task(source, repo_id, "SA-0203")
    _baseline(source, run3, lint_count=2)
    a3 = source.open_attempt(task3, phase="IMPLEMENTING")
    source.record_gate_result(
        GateResult(gate="tests", status="error", tool="pytest 8.0", failures=[]),
        attempt_id=a3,
        baseline=[],
    )
    _set(
        source,
        "UPDATE gate_results SET failures_at_head = NULL WHERE attempt_id = ?",
        (a3,),
    )

    # Task 4: no doubling, an uncounted result -> migrates.
    run4, task4 = _task(source, repo_id, "SA-0204")
    _baseline(source, run4, lint_count=1)
    a4 = source.open_attempt(task4, phase="IMPLEMENTING")
    source.record_gate_result(
        GateResult(gate="lint", status="pass", tool="ruff 1.0", failures=[]),
        attempt_id=a4,
        baseline=[],
    )
    _set(
        source,
        "UPDATE gate_results SET failures_at_head = NULL WHERE attempt_id = ?",
        (a4,),
    )

    # Task 5: no baseline doubling, but its one attempt stores two uncounted
    # lint results -> refused.
    run5, task5 = _task(source, repo_id, "SA-0205")
    _baseline(source, run5, lint_count=1)
    a5 = source.open_attempt(task5, phase="IMPLEMENTING")
    source.record_gate_result(
        GateResult(gate="lint", status="pass", tool="ruff 1.0", failures=[]),
        attempt_id=a5,
        baseline=[],
    )
    source.record_gate_result(
        GateResult(gate="lint", status="fail", tool="ruff 1.0", failures=[]),
        attempt_id=a5,
        baseline=[],
    )
    _set(
        source,
        "UPDATE gate_results SET failures_at_head = NULL WHERE attempt_id = ?",
        (a5,),
    )

    # Task 6: task 5's shape, both of the attempt's lint results counted ->
    # migrates, with both stored rows kept.
    run6, task6 = _task(source, repo_id, "SA-0206")
    _baseline(source, run6, lint_count=1)
    a6 = source.open_attempt(task6, phase="IMPLEMENTING")
    source.record_gate_result(
        GateResult(gate="lint", status="pass", tool="ruff 1.0", failures=[]),
        attempt_id=a6,
        baseline=[],
    )
    source.record_gate_result(
        GateResult(gate="lint", status="fail", tool="ruff 1.0", failures=[]),
        attempt_id=a6,
        baseline=[],
    )

    keys = {
        n: source._db.execute(
            "SELECT record_key FROM tasks WHERE task_id = ?", (tid,)
        ).fetchone()["record_key"]
        for n, tid in [
            (1, task1),
            (2, task2),
            (3, task3),
            (4, task4),
            (5, task5),
            (6, task6),
        ]
    }
    source_path = tmp_path / "source.db"
    _close(source)

    result, record = _migrated(source_path)
    assert sorted(result.migrated) == sorted([keys[1], keys[4], keys[6]])
    assert sorted(key for key, _ in result.refused) == sorted(
        [keys[2], keys[3], keys[5]]
    )

    reasons = dict(result.refused)
    assert "lint" in reasons[keys[2]] and "baseline" in reasons[keys[2]]
    assert "lint" in reasons[keys[3]] and "baseline" in reasons[keys[3]]
    assert "lint" in reasons[keys[5]] and "IMPLEMENTING" in reasons[keys[5]]

    assert record.read(keys[2]) == []
    assert record.read(keys[3]) == []
    assert record.read(keys[5]) == []

    results6 = [f for f in record.read(keys[6]) if f.kind == "gate_result"]
    assert len(results6) == 2
    assert [f.payload["status"] for f in results6] == ["pass", "fail"]


def test_a_ledger_that_predates_the_head_count_subtracts_its_stored_failures(
    tmp_path: Path,
) -> None:
    from saffron.record.fold import fold

    # Source A: predates both failures_at_head and earned_risk entirely.
    source_a_path = tmp_path / "a" / "source.db"
    source_a = _source(source_a_path)
    repo_a = source_a.upsert_repo("saffron", "/o", "/m.git", None)
    run_a, task_a = _task(source_a, repo_a, "SA-0301")
    source_a.record_gate_result(
        GateResult(
            gate="lint",
            status="fail",
            tool="ruff 1.0",
            failures=[Failure(file="a.py", line=1, code="E1", message="bad")],
        ),
        run_id=run_a,
    )
    attempt_a = source_a.open_attempt(task_a, phase="IMPLEMENTING")
    source_a.close_attempt(
        attempt_a,
        session_id="sa",
        subtype="success",
        terminal_reason=None,
        num_turns=1,
        cost_usd_est=1.0,
    )
    source_a.record_gate_result(
        GateResult(
            gate="lint",
            status="fail",
            tool="ruff 1.0",
            failures=[
                Failure(file="a.py", line=1, code="E1", message="bad"),
                Failure(file="b.py", line=2, code="E2", message="new"),
            ],
        ),
        attempt_id=attempt_a,
        baseline=[],
    )
    key_a = source_a._db.execute(
        "SELECT record_key FROM tasks WHERE task_id = ?", (task_a,)
    ).fetchone()["record_key"]
    source_a._db.execute("ALTER TABLE gate_results DROP COLUMN failures_at_head")
    source_a._db.execute("ALTER TABLE attempts DROP COLUMN earned_risk")
    source_a._db.commit()
    _close(source_a)

    result_a, record_a = _migrated(source_a_path)
    assert result_a.migrated == [key_a]
    assert result_a.refused == []
    (fact_a,) = [f for f in record_a.read(key_a) if f.kind == "gate_result"]
    assert [(f["file"], f["code"]) for f in fact_a.payload["failures"]] == [
        ("b.py", "E2")
    ]
    assert fact_a.payload["failures_at_head"] == 2
    assert fact_a.payload["earned_risk"] is None

    rebuilt_a = Ledger(tmp_path / "a" / "rebuilt.db")
    fold(record_a, rebuilt_a)
    (row_a,) = _rows(rebuilt_a._db, "SELECT earned_risk FROM attempts")
    assert row_a["earned_risk"] is None
    rebuilt_a.close()

    # Source B: predates failures_at_head alone, and stores an elevated tier.
    source_b_path = tmp_path / "b" / "source.db"
    source_b = _source(source_b_path)
    repo_b = source_b.upsert_repo("saffron", "/o", "/m.git", None)
    run_b, task_b = _task(source_b, repo_b, "SA-0302")
    source_b.record_gate_result(
        GateResult(
            gate="lint",
            status="fail",
            tool="ruff 1.0",
            failures=[Failure(file="c.py", line=1, code="E3", message="old")],
        ),
        run_id=run_b,
    )
    attempt_b = source_b.open_attempt(task_b, phase="IMPLEMENTING")
    source_b.close_attempt(
        attempt_b,
        session_id="sb",
        subtype="success",
        terminal_reason=None,
        num_turns=1,
        cost_usd_est=1.0,
    )
    source_b.record_gate_result(
        GateResult(
            gate="lint",
            status="fail",
            tool="ruff 1.0",
            failures=[
                Failure(file="c.py", line=1, code="E3", message="old"),
                Failure(file="d.py", line=2, code="E4", message="new"),
            ],
        ),
        attempt_id=attempt_b,
        baseline=[],
        earned_risk="elevated",
    )
    key_b = source_b._db.execute(
        "SELECT record_key FROM tasks WHERE task_id = ?", (task_b,)
    ).fetchone()["record_key"]
    source_b._db.execute("ALTER TABLE gate_results DROP COLUMN failures_at_head")
    source_b._db.commit()
    _close(source_b)

    result_b, record_b = _migrated(source_b_path)
    assert result_b.migrated == [key_b]
    assert result_b.refused == []
    (fact_b,) = [f for f in record_b.read(key_b) if f.kind == "gate_result"]
    assert [(f["file"], f["code"]) for f in fact_b.payload["failures"]] == [
        ("d.py", "E4")
    ]
    assert fact_b.payload["failures_at_head"] == 2
    assert fact_b.payload["earned_risk"] == "elevated"

    rebuilt_b = Ledger(tmp_path / "b" / "rebuilt.db")
    fold(record_b, rebuilt_b)
    (row_b,) = _rows(rebuilt_b._db, "SELECT earned_risk FROM attempts")
    assert row_b["earned_risk"] == "elevated"
    rebuilt_b.close()
