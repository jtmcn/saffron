"""`saffron/record/migrate.py`. It appends a stored ledger's tasks, attempts
and findings as the facts a live run would have written. A fold then gives
them back (backlog item 170, design §7)."""

from __future__ import annotations

import hashlib
import re
import sqlite3
import time
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest

from saffron.agents.findings import Finding
from saffron.ledger import Ledger
from saffron.record.contract import Fact
from saffron.record.memory import MemoryRecord


def _set(ledger: Ledger, sql: str, params: tuple) -> None:
    ledger._db.execute(sql, params)
    ledger._db.commit()


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
            subtype="success",
            terminal_reason=None,
            num_turns=4,
            cost_usd_est=1.5,
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

        source_path = tmp_path / "source.db"
        keys = {
            n: source._db.execute(
                "SELECT record_key FROM tasks WHERE task_id = ?", (tid,)
            ).fetchone()["record_key"]
            for n, tid in [(1, task1), (2, task2), (3, task3), (4, task4)]
        }
        source.close()

        record = MemoryRecord()
        result = migrate(source_path, record)
        assert sorted(result.migrated) == sorted(keys.values())
        assert result.refused == []

        rebuilt = Ledger(tmp_path / "rebuilt.db")
        fold(record, rebuilt)

        reread = sqlite3.connect(source_path)
        reread.row_factory = sqlite3.Row
        task_cols = (
            "record_key, spec_id, spec_sha, state, risk, branch, budget_usd,"
            " policy_sha, prompt_sha, pushed_sha, pr_url, merged_head_sha,"
            " added, removed"
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
        assert ordered == ["SA-0001", "SA-0002", "SA-0003", "SA-0004"]

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

    assert sorted(result.migrated) == sorted([keys[0], keys[1], keys[2]])
    assert sorted(key for key, _ in result.refused) == sorted(
        [keys[3], keys[4], keys[5]]
    )

    for key in (keys[0], keys[1], keys[2]):
        assert seeded.read(key) == expected[key]
    for key in (keys[3], keys[4], keys[5]):
        assert seeded.read(key) == held_before[key]


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
