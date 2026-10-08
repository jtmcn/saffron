"""`saffron/record/migrate.py`. It appends a stored ledger's tasks, attempts,
gate results and findings as the facts a live run would have written. A fold
then gives them back (backlog item 170, the record design's §7)."""

from __future__ import annotations

import hashlib
import re
import sqlite3
import subprocess
import time
from collections import Counter
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from saffron.agents.findings import Finding
from saffron.gates.contract import Failure, GateResult
from saffron.ledger import Ledger
from saffron.record.contract import Fact
from saffron.record.memory import MemoryRecord


def _set(ledger: Ledger, sql: str, params: tuple) -> None:
    ledger._db.execute(sql, params)
    ledger._db.commit()


def _key(ledger: Ledger, task_id: int) -> str:
    return ledger._db.execute(
        "SELECT record_key FROM tasks WHERE task_id = ?", (task_id,)
    ).fetchone()["record_key"]


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


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=check
    )


def _bare(path: Path) -> Path:
    """A fresh bare repository. Every origin and every "other writer"'s own
    repository in the command's witnesses is one of these."""
    subprocess.run(["git", "init", "-q", "--bare", str(path)], check=True)
    return path


def _scratch_with_branch(path: Path) -> Path:
    """A non-bare repository holding one commit on `main`. A mirror cloned
    from it carries a branch, and its own `origin` remote is never the
    row's declared `origin`."""
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    (path / "README").write_text("scratch\n")
    _git(path, "add", "README")
    _git(
        path,
        "-c",
        "user.email=scratch@localhost",
        "-c",
        "user.name=Scratch",
        "commit",
        "-q",
        "-m",
        "init",
    )
    _git(path, "branch", "-M", "main")
    return path


def _mirror_of(scratch: Path, dest: Path) -> Path:
    subprocess.run(
        ["git", "clone", "-q", "--mirror", str(scratch), str(dest)], check=True
    )
    return dest


def _logging_hook(origin: Path, name: str, log: Path) -> None:
    """A hook that appends whatever git feeds it to `log` and exits 0."""
    hook = origin / "hooks" / name
    hook.write_text(f"#!/bin/sh\ncat >> {str(log)!r}\nexit 0\n")
    hook.chmod(0o755)


def _declining_hook(origin: Path, name: str, needle: str) -> None:
    """A hook that fails only when its stdin names `needle`, so one ref in a
    push can be declined while the rest land."""
    hook = origin / "hooks" / name
    hook.write_text(f"#!/bin/sh\nif grep -q {needle!r} -; then exit 1; fi\nexit 0\n")
    hook.chmod(0o755)


def _rev_parse(repo: Path, ref: str) -> str | None:
    done = _git(repo, "rev-parse", "--verify", "-q", ref, check=False)
    return done.stdout.strip() if done.returncode == 0 else None


def _ref_lines(log: Path, ref: str) -> list[str]:
    if not log.exists():
        return []
    return [line for line in log.read_text().splitlines() if ref in line]


def _spy_on_pushes(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Every `git push` argv issued while active. A push that always lands
    would hide a `--force` added back in. This checks the argv itself,
    never the push's own outcome."""
    calls: list[list[str]] = []
    real_run = subprocess.run

    def _spy(cmd: Any, *args: Any, **kwargs: Any) -> subprocess.CompletedProcess[Any]:
        if isinstance(cmd, list) and "push" in cmd:
            calls.append(list(cmd))
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _spy)
    return calls


_REPORT_PREFIXES = ("migrated ", "refused ", "push failed ")


def _reports(out: str) -> list[str]:
    """The command's own report lines, one per task. A `RecordError`'s own
    message can carry git's multi-line stderr, so a continuation line is
    dropped rather than read as a report of its own."""
    return [line for line in out.splitlines() if line.startswith(_REPORT_PREFIXES)]


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
            n: _key(source, tid)
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
            tuple(r) for r in _rows(reread, f"SELECT {task_cols}, {spend} FROM tasks t")
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
            for r in _rows(
                reread,
                f"SELECT {attempt_cols} FROM attempts a"
                " JOIN tasks t ON t.task_id = a.task_id",
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
            for r in _rows(
                reread,
                f"SELECT {finding_cols} FROM findings f"
                " JOIN tasks t ON t.task_id = f.task_id",
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
    keys = [_key(source, tid) for tid in task_ids]
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
    attempt closed anywhere in `facts`, `attempt_opened` otherwise. A closed attempt's own `gate_result` facts must follow
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

    source = Ledger(tmp_path / "source.db")
    repo_id = source.upsert_repo("saffron", "/o", "/m.git", None)

    # Another run, made first, whose "types" baseline failure shares attempt
    # 1's exactly: reading the wrong run's baseline would cancel it.
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
            duration_ms=101,
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
            duration_ms=102,
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
            duration_ms=103,
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
            duration_ms=104,
            gate="format",
            status="pass",
            tool="black 1.0",
            summary="",
            failures=[],
        ),
        attempt_id=a1,
        baseline=[],
    )

    # Attempt 2 (closed): three lint copies of one baseline failure.
    # A one-copy baseline leaves two, and earned_risk is stored elevated.
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
            duration_ms=201,
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

    # Attempts 3-6: never closed. Five results sit on the two closed
    # attempts above, seven on these four open ones.
    a3 = source.open_attempt(task1, phase="GATING")
    source.record_gate_result(
        GateResult(
            duration_ms=301,
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
            duration_ms=302,
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
            duration_ms=401,
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
        GateResult(
            duration_ms=501,
            gate="revert",
            status="pass",
            tool="revert-tool 1.0",
            summary="reverted clean",
            failures=[],
        ),
        attempt_id=a5,
        baseline=[],
    )
    source.record_gate_result(
        GateResult(
            duration_ms=502,
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
        GateResult(
            duration_ms=601,
            gate="types",
            status="skip",
            tool=None,
            summary="not configured",
            failures=[],
        ),
        attempt_id=a6,
        baseline=[],
    )
    source.record_gate_result(
        GateResult(
            duration_ms=602,
            gate="lint",
            status="fail",
            tool="ruff 1.0",
            failures=[Failure(file="a.py", line=10, code="E1", message="bad one")],
        ),
        attempt_id=a6,
        baseline=[],
    )

    # Null every count but attempt 2's, plus the "types" failure's message
    # and "format"'s summary, which must round trip null.
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
    # earned_risk stays null, never defaulted from the task's risk.
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
        GateResult(
            duration_ms=701,
            gate="lint",
            status="pass",
            tool="ruff 1.0",
            summary="clean",
            failures=[],
        ),
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

    key1 = _key(source, task1)
    key2 = _key(source, task2)
    source_path = tmp_path / "source.db"
    source.close()

    result, record = _migrated(source_path)
    assert result.migrated == [key1, key2]
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
    attempt_sql = (
        "SELECT t.record_key, a.phase, a.n, a.session_id, a.model, a.started_at,"
        " a.ended_at, a.subtype, a.terminal_reason, a.num_turns, a.cost_usd_est,"
        " a.cost_floor_usd_est, a.earned_risk"
        " FROM attempts a JOIN tasks t ON t.task_id = a.task_id"
        " ORDER BY a.attempt_id"
    )
    reread = sqlite3.connect(source_path)
    before = [tuple(r) for r in _rows(reread, attempt_sql)]
    after = [tuple(r) for r in _rows(rebuilt._db, attempt_sql)]
    assert len(before) == 7
    assert before == after

    results_sql = (
        "SELECT t.record_key, a.phase, a.n, g.gate, g.status, g.tool,"
        " g.duration_ms, g.summary, g.failures_at_head"
        " FROM gate_results g JOIN attempts a ON a.attempt_id = g.attempt_id"
        " JOIN tasks t ON t.task_id = a.task_id ORDER BY g.gate_result_id"
    )
    impl, rep, gate = "IMPLEMENTING", "REPAIRING", "GATING"
    assert [tuple(r) for r in _rows(rebuilt._db, results_sql)] == [
        (key1, impl, 1, "lint", "fail", "ruff 1.0", 101, "", 4),
        (key1, impl, 1, "witness", "fail", "pytest 8.0", 102, "", 1),
        (key1, impl, 1, "types", "fail", "mypy 1.0", 103, "", 1),
        (key1, impl, 1, "format", "pass", "black 1.0", 104, None, 0),
        (key1, rep, 1, "lint", "fail", "ruff 1.0", 201, "", 3),
        (key1, gate, 1, "lint", "fail", "ruff 1.0", 301, "", 1),
        (key1, gate, 1, "tests", "error", "pytest 8.0", 302, "collection crashed", 0),
        (key1, gate, 2, "lint", "fail", "ruff 2.0", 401, "", 1),
        (key1, gate, 3, "revert", "pass", "revert-tool 1.0", 501, "reverted clean", 0),
        (key1, gate, 3, "lint", "fail", "ruff 1.0", 502, "", 1),
        (key1, gate, 4, "types", "skip", None, 601, "not configured", 0),
        (key1, gate, 4, "lint", "fail", "ruff 1.0", 602, "", 1),
        (key2, impl, 1, "lint", "pass", "ruff 1.0", 701, "clean", 0),
    ]

    failures_sql = (
        "SELECT t.record_key, a.phase, a.n, g.gate, f.file, f.line, f.code, f.message"
        " FROM failures f JOIN gate_results g ON g.gate_result_id = f.gate_result_id"
        " JOIN attempts a ON a.attempt_id = g.attempt_id"
        " JOIN tasks t ON t.task_id = a.task_id ORDER BY f.failure_id"
    )
    assert [tuple(r) for r in _rows(rebuilt._db, failures_sql)] == [
        (key1, impl, 1, "lint", "b.py", 21, "E2", "bad two"),
        (key1, impl, 1, "lint", "shared.py", 9, "SAME", ""),
        (key1, impl, 1, "witness", "w.py", 5, "survived-mutant", "mutant lived"),
        (key1, impl, 1, "types", "n.py", 3, "N1", None),
        (key1, rep, 1, "lint", "a.py", 11, "E1", "bad one"),
        (key1, rep, 1, "lint", "a.py", 12, "E1", "bad one"),
        (key1, gate, 1, "lint", "a.py", 10, "E1", "bad one"),
        (key1, gate, 2, "lint", "a.py", 10, "E1", "bad one"),
        (key1, gate, 4, "lint", "a.py", 10, "E1", "bad one"),
    ]
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

    source = Ledger(tmp_path / "source.db")
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
        n: _key(source, tid)
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
    source.close()

    result, record = _migrated(source_path)
    assert result.migrated == [keys[1], keys[4], keys[6]]
    assert result.refused == [
        (keys[2], "gate 'lint' stored twice in the run's baseline"),
        (keys[3], "gate 'lint' stored twice in the run's baseline"),
        (keys[5], "gate 'lint' stored twice on attempt IMPLEMENTING 1"),
    ]

    assert record.read(keys[2]) == []
    assert record.read(keys[3]) == []
    assert record.read(keys[5]) == []

    results6 = [f for f in record.read(keys[6]) if f.kind == "gate_result"]
    assert len(results6) == 2
    assert [f.payload["status"] for f in results6] == ["pass", "fail"]


def _predating_source(
    path: Path,
    spec_id: str,
    old: Failure,
    new: Failure,
    *,
    earned_risk: str | None,
    drop_earned_risk: bool,
) -> str:
    """A ledger with `old` in its run's baseline and an attempt storing `old`
    and `new`, its `failures_at_head` column dropped. Returns the task's key."""
    source = Ledger(path)
    repo_id = source.upsert_repo("saffron", "/o", "/m.git", None)
    run_id, task_id = _task(source, repo_id, spec_id)
    source.record_gate_result(
        GateResult(gate="lint", status="fail", tool="ruff 1.0", failures=[old]),
        run_id=run_id,
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
    source.record_gate_result(
        GateResult(gate="lint", status="fail", tool="ruff 1.0", failures=[old, new]),
        attempt_id=attempt_id,
        baseline=[],
        earned_risk=earned_risk,
    )
    key = _key(source, task_id)
    source._db.execute("ALTER TABLE gate_results DROP COLUMN failures_at_head")
    if drop_earned_risk:
        source._db.execute("ALTER TABLE attempts DROP COLUMN earned_risk")
    source._db.commit()
    source.close()
    return key


def test_a_ledger_that_predates_the_head_count_subtracts_its_stored_failures(
    tmp_path: Path,
) -> None:
    from saffron.record.fold import fold

    # Source A: predates both failures_at_head and earned_risk entirely.
    source_a_path = tmp_path / "a" / "source.db"
    key_a = _predating_source(
        source_a_path,
        "SA-0301",
        Failure(file="a.py", line=1, code="E1", message="bad"),
        Failure(file="b.py", line=2, code="E2", message="new"),
        earned_risk=None,
        drop_earned_risk=True,
    )

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
    key_b = _predating_source(
        source_b_path,
        "SA-0302",
        Failure(file="c.py", line=1, code="E3", message="old"),
        Failure(file="d.py", line=2, code="E4", message="new"),
        earned_risk="elevated",
        drop_earned_risk=False,
    )

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


_KEY_FILED_KINDS = (
    "stack_layer",
    "end_review",
    "qualification",
    "spec_review",
    "spec_text",
    "stack_finish",
)

_KEY_FILED_COLUMNS = {
    "stack_layers": "task_key, batch_key, position, spec_id, predecessor_key,"
    " predecessor_head, generation",
    "end_reviews": "task_key, lens, status, cost_usd, error",
    "qualifications": "task_key, position, lens, severity, file, line, claim,"
    " probe_verdict, outcome, reason",
    "spec_reviews": "task_key, n, route, block, block_sha256, error",
    "spec_texts": "task_key, n, origin, spec_id, path, text, spec_sha",
    "stack_finishes": "batch_key, task_key, branch, head_sha, pr_url",
}


def test_a_migrated_stack_folds_back_to_its_key_filed_rows(tmp_path: Path) -> None:
    from saffron.record.fold import fold
    from saffron.record.migrate import migrate

    source = Ledger(tmp_path / "source.db")
    repo_id = source.upsert_repo("saffron", "/o", "/m.git", None)

    batch1 = source.create_batch(budget_usd=20.0)
    run1 = source.create_run(repo_id, base_sha="a" * 40)
    run2 = source.create_run(repo_id, base_sha="a" * 40)
    source.attach_run_to_batch(run1, batch1)
    source.attach_run_to_batch(run2, batch1)
    _set(
        source,
        "UPDATE runs SET started_at = ? WHERE run_id = ?",
        ("2020-01-01 08:00:00", run1),
    )
    _set(
        source,
        "UPDATE runs SET started_at = ? WHERE run_id = ?",
        ("2020-01-01 09:00:00", run2),
    )

    task1 = source.create_task(
        run1, spec_id="SA-1001", spec_sha="s" * 64, branch="saffron/SA-1001"
    )
    task2 = source.create_task(
        run2, spec_id="SA-1002", spec_sha="s" * 64, branch="saffron/SA-1002"
    )

    # Two layers: task1 has no predecessor, task2's is task1.
    source.record_stack_layer(task1, position=1, predecessor_task_id=None, generation=1)
    source.record_stack_layer(
        task2, position=2, predecessor_task_id=task1, generation=1
    )

    # Every one of the other four key-filed tables, both rows on task1.
    source.record_end_review(
        task1, lens="l1", status="reviewed", cost_usd=1.5, error=None
    )
    source.record_end_review(
        task1, lens="l2", status="error", cost_usd=0.0, error="boom"
    )

    f1 = Finding(
        lens="l1", severity="blocker", file="a.py", line=1, claim="c1", anchored=True
    )
    f2 = Finding(
        lens="l2",
        severity="concern",
        file="b.py",
        line=2,
        claim="c2",
        anchored=False,
        probe_verdict="survived",
    )
    source.record_qualification(
        task1, finding=f1, filed="blocker", outcome="kept", reason="r1"
    )
    source.record_qualification(
        task1, finding=f2, filed="concern", outcome="dropped", reason="r2"
    )

    source.record_spec_review(
        task1, route="revise", block=None, block_sha256=None, error=None, findings=[]
    )
    source.record_spec_review(
        task1,
        route="run",
        block="b" * 10,
        block_sha256="c" * 64,
        error=None,
        findings=[],
    )

    source.record_spec_text(
        task1,
        origin="revision",
        spec_id="SA-1001",
        path=".saffron/specs/SA-1001-foo.md",
        text="hello",
    )
    source.record_spec_text(
        task1,
        origin="follow_up",
        spec_id="SA-1001",
        path=".saffron/specs/SA-1001-bar.md",
        text="world",
    )

    source.record_stack_finish(
        batch1, branch="saffron/SA-1002", head_sha="d" * 40, pr_url=None
    )

    key1 = _key(source, task1)
    key2 = _key(source, task2)

    # Numbered 1 and 3, not 1 and 2: `migrate` must keep whatever is stored.
    _set(
        source,
        "UPDATE spec_reviews SET n = 3 WHERE task_key = ? AND n = 2",
        (key1,),
    )
    _set(
        source,
        "UPDATE qualifications SET position = 3 WHERE task_key = ? AND position = 2",
        (key1,),
    )

    source.set_task_state(task1, "READY_FOR_REVIEW")
    source.set_task_state(task2, "READY_FOR_REVIEW")

    # The runs move to another batch after the stack's rows are written.
    batch2 = source.create_batch(budget_usd=10.0)
    source.attach_run_to_batch(run1, batch2)
    source.attach_run_to_batch(run2, batch2)

    updated_at = {
        1: source._db.execute(
            "SELECT updated_at FROM tasks WHERE task_id = ?", (task1,)
        ).fetchone()["updated_at"],
        2: source._db.execute(
            "SELECT updated_at FROM tasks WHERE task_id = ?", (task2,)
        ).fetchone()["updated_at"],
    }

    source_path = tmp_path / "source.db"
    source.close()

    result, record = _migrated(source_path)
    assert sorted(result.migrated) == sorted([key1, key2])
    assert result.refused == []

    rebuilt = Ledger(tmp_path / "rebuilt.db")
    fold(record, rebuilt)

    reread = sqlite3.connect(source_path)
    reread.row_factory = sqlite3.Row
    for table, cols in _KEY_FILED_COLUMNS.items():
        before_rows = _rows(reread, f"SELECT {cols} FROM {table}")
        after_rows = _rows(rebuilt._db, f"SELECT {cols} FROM {table}")
        assert before_rows, f"{table} holds no rows to compare"
        before = Counter(tuple(r) for r in before_rows)
        after = Counter(tuple(r) for r in after_rows)
        assert before == after, table

    expected_tail = {
        key1: [
            "stack_layer",
            "end_review",
            "end_review",
            "qualification",
            "qualification",
            "spec_review",
            "spec_review",
            "spec_text",
            "spec_text",
        ],
        key2: ["stack_layer", "stack_finish"],
    }
    # Each key column's stored values, in the order its rows were read.
    expected_numbers = {
        key1: [
            ("stack_layer", "position", [1]),
            ("qualification", "position", [1, 3]),
            ("spec_review", "n", [1, 3]),
        ],
        key2: [("stack_layer", "position", [2])],
    }
    frozen_batch_key = {key1: str(batch1), key2: str(batch1)}
    task_batch_key = {key1: str(batch2), key2: str(batch2)}

    for n, key in ((1, key1), (2, key2)):
        facts = record.read(key)
        state_index = next(i for i, f in enumerate(facts) if f.kind == "task_state")
        tail = facts[state_index + 1 :]
        assert [f.kind for f in tail] == expected_tail[key]
        for kind, column, numbers in expected_numbers[key]:
            assert [f.payload[column] for f in tail if f.kind == kind] == numbers, kind
        for fact in tail:
            assert fact.at == _iso(updated_at[n])
            assert fact.repo == "saffron"
            if fact.kind in ("stack_layer", "stack_finish"):
                assert fact.batch_key == frozen_batch_key[key]
            else:
                assert fact.batch_key == task_batch_key[key]

    # A record holding each key's facts up to its task_state is completed by
    # a rerun, with no key refused.
    seeded = MemoryRecord()
    for key in (key1, key2):
        full = record.read(key)
        state_index = next(i for i, f in enumerate(full) if f.kind == "task_state")
        for fact in full[: state_index + 1]:
            seeded.append(key, Fact.from_json(fact.to_json()))
    rerun = migrate(source_path, seeded)
    assert sorted(rerun.migrated) == sorted([key1, key2])
    assert rerun.refused == []
    for key in (key1, key2):
        assert seeded.read(key) == record.read(key)

    rebuilt.close()
    reread.close()


def test_migrate_writes_each_repos_tasks_to_its_own_origin_and_refuses_a_disagreeing_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from saffron import cli
    from saffron.record.migrate import migrate
    from saffron.record.refs import RefsRecord

    origin1 = _bare(tmp_path / "origin1.git")
    origin2 = _bare(tmp_path / "origin2.git")
    scratch = _scratch_with_branch(tmp_path / "scratch")
    mirror1 = _mirror_of(scratch, tmp_path / "mirror1.git")
    mirror2 = _mirror_of(scratch, tmp_path / "mirror2.git")

    source = Ledger(tmp_path / "source.db")
    repo1 = source.upsert_repo("repo-a", str(origin1), str(mirror1), None)
    repo2 = source.upsert_repo("repo-b", str(origin2), str(mirror2), None)

    run_good, task_good = _task(source, repo1, "SA-2001")
    source.open_attempt(task_good, phase="IMPLEMENTING")
    run_bad, task_bad = _task(source, repo1, "SA-2002")
    run_other, task_other = _task(source, repo2, "SA-2003")

    good_key = _key(source, task_good)
    bad_key = _key(source, task_bad)
    other_key = _key(source, task_other)

    source_path = tmp_path / "source.db"
    source.close()

    _, truth = _migrated(source_path)
    expected = {key: truth.read(key) for key in (good_key, other_key)}
    assert len(expected[good_key]) > 2

    # The other writer pushes the good task's first two true facts and the
    # bad task's disagreeing first fact to origin1, under its own date.
    writer_repo = _bare(tmp_path / "writer.git")
    writer_record = RefsRecord(writer_repo, remote=str(origin1))
    bad_fact = Fact(
        kind="task_created",
        task_key=bad_key,
        at="2020-01-01T00:00:00+00:00",
        repo="repo-a",
        batch_key=None,
        payload={"spec_id": "SA-2002", "spec_sha": "x" * 64},
    )
    with monkeypatch.context() as patched:
        patched.setenv("GIT_COMMITTER_DATE", "2020-01-01T00:00:00Z")
        writer_record.append(good_key, expected[good_key][0])
        writer_record.append(good_key, expected[good_key][1])
        writer_record.append(bad_key, bad_fact)
    writer_commits = _git(
        origin1, "rev-list", f"refs/saffron/tasks/{good_key}"
    ).stdout.split()
    assert len(writer_commits) == 2
    bad_sha_before = _rev_parse(origin1, f"refs/saffron/tasks/{bad_key}")
    assert bad_sha_before is not None

    # The mirror already carries local-only state the fetch must leave alone.
    RefsRecord(mirror1).compare_and_swap("some-value", None, "v1")
    values_sha_before = _rev_parse(mirror1, "refs/saffron/values/some-value")
    branch_sha_before = _rev_parse(mirror1, "refs/heads/main")
    assert values_sha_before is not None
    assert branch_sha_before is not None

    log1 = tmp_path / "origin1.log"
    log2 = tmp_path / "origin2.log"
    _logging_hook(origin1, "pre-receive", log1)
    _logging_hook(origin2, "pre-receive", log2)

    seeded = MemoryRecord()
    seeded.append(bad_key, bad_fact)
    reason = dict(migrate(source_path, seeded).refused)[bad_key]
    assert reason != ""

    home = tmp_path / "home"
    push_calls = _spy_on_pushes(monkeypatch)
    rc = cli.main(["--home", str(home), "migrate", "--from", str(source_path)])
    out = capsys.readouterr().out

    # Never opens the home ledger: the dispatch runs before `Ledger` does.
    assert not home.exists()

    # No ref moves by overwriting history, only by a fast-forward.
    assert push_calls
    assert not any("--force" in call for call in push_calls)

    assert sorted(out.splitlines()) == sorted(
        [
            f"migrated {good_key}",
            f"migrated {other_key}",
            f"refused {bad_key}: {reason}",
        ]
    )
    assert rc == 1

    # The other writer's prefix is completed on top of its own commits.
    assert RefsRecord(origin1).read(good_key) == expected[good_key]
    for sha in writer_commits:
        ancestry = _git(
            origin1,
            "merge-base",
            "--is-ancestor",
            sha,
            f"refs/saffron/tasks/{good_key}",
            check=False,
        )
        assert ancestry.returncode == 0, sha
    assert RefsRecord(origin2).read(other_key) == expected[other_key]

    # A push of a ref the origin already holds sends nothing and runs no
    # hook. The refused key's ref is asserted by its sha, never the log.
    assert _rev_parse(origin1, f"refs/saffron/tasks/{bad_key}") == bad_sha_before

    assert set(RefsRecord(origin1).task_keys()) == {good_key, bad_key}
    assert RefsRecord(origin2).task_keys() == [other_key]
    assert RefsRecord(mirror2).task_keys() == [other_key]

    assert len(_ref_lines(log1, f"refs/saffron/tasks/{good_key}")) == 1
    assert _ref_lines(log1, f"refs/saffron/tasks/{bad_key}") == []
    assert len(_ref_lines(log2, f"refs/saffron/tasks/{other_key}")) == 1

    assert _rev_parse(mirror1, "refs/saffron/values/some-value") == values_sha_before
    assert _rev_parse(mirror1, "refs/heads/main") == branch_sha_before


def test_a_refused_push_is_reported_per_task_and_a_rerun_completes_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from saffron import cli
    from saffron.record.refs import RefsRecord

    origin = _bare(tmp_path / "origin.git")
    scratch = _scratch_with_branch(tmp_path / "scratch")
    mirror = _mirror_of(scratch, tmp_path / "mirror.git")

    # A ref the mirror holds and the origin never will, so the fetch's own
    # prune is what removes it rather than anything the migration writes.
    stray_key = "f" * 32
    stray_fact = Fact(
        kind="task_created",
        task_key=stray_key,
        at="2020-01-01T00:00:00+00:00",
        repo="saffron",
        batch_key=None,
        payload={"spec_id": "SA-9999", "spec_sha": "z" * 64},
    )
    RefsRecord(mirror).append(stray_key, stray_fact)
    assert _rev_parse(mirror, f"refs/saffron/tasks/{stray_key}") is not None

    source = Ledger(tmp_path / "source.db")
    repo_id = source.upsert_repo("saffron", str(origin), str(mirror), None)
    _, task1 = _task(source, repo_id, "SA-3001")
    _, task2 = _task(source, repo_id, "SA-3002")
    _, task3 = _task(source, repo_id, "SA-3003")
    key1 = _key(source, task1)
    key2 = _key(source, task2)
    key3 = _key(source, task3)
    source_path = tmp_path / "source.db"
    source.close()

    _, truth = _migrated(source_path)
    expected = {key: truth.read(key) for key in (key1, key2, key3)}

    # The second task's own first fact, already on the origin under another
    # writer's committer date, hidden from fetch so our push cannot know it.
    writer_repo = _bare(tmp_path / "writer.git")
    writer_record = RefsRecord(writer_repo, remote=str(origin))
    with monkeypatch.context() as patched:
        patched.setenv("GIT_COMMITTER_DATE", "2019-06-01T00:00:00Z")
        writer_record.append(key2, expected[key2][0])
    stale_sha_before = _rev_parse(origin, f"refs/saffron/tasks/{key2}")
    assert stale_sha_before is not None
    _git(origin, "config", "uploadpack.hideRefs", f"refs/saffron/tasks/{key2}")

    _declining_hook(origin, "pre-receive", key1)

    rc1 = cli.main(
        ["--home", str(tmp_path / "home"), "migrate", "--from", str(source_path)]
    )
    out1 = capsys.readouterr().out
    lines1 = sorted(_reports(out1))
    assert [line.split(":", 1)[0] for line in lines1] == sorted(
        [f"push failed {key1}", f"push failed {key2}", f"migrated {key3}"]
    )
    decline_line = next(
        line for line in lines1 if line.startswith(f"push failed {key1}")
    )
    stale_line = next(line for line in lines1 if line.startswith(f"push failed {key2}"))
    assert decline_line.startswith(f"push failed {key1}: RecordError: ")
    assert stale_line.startswith(f"push failed {key2}: StaleWriter: ")
    assert rc1 == 1

    # Neither failed push moved the origin's own ref for its key.
    assert _rev_parse(origin, f"refs/saffron/tasks/{key1}") is None
    assert _rev_parse(origin, f"refs/saffron/tasks/{key2}") == stale_sha_before
    assert RefsRecord(origin).read(key3) == expected[key3]

    # The fetch drops a ref the origin lacks outright, this repo's own key
    # included: the origin never held it, so only the prune removes it.
    assert _rev_parse(mirror, f"refs/saffron/tasks/{stray_key}") is None

    # Remove both causes, and give the mirror a fact the origin never took.
    (origin / "hooks" / "pre-receive").unlink()
    _git(origin, "config", "--unset", "uploadpack.hideRefs")
    RefsRecord(mirror).append(key1, expected[key1][-1])
    assert RefsRecord(mirror).read(key1) == [*expected[key1], expected[key1][-1]]

    rc2 = cli.main(
        ["--home", str(tmp_path / "home"), "migrate", "--from", str(source_path)]
    )
    out2 = capsys.readouterr().out
    lines2 = sorted(_reports(out2))
    assert [line.split(":", 1)[0] for line in lines2] == sorted(
        [f"migrated {key1}", f"migrated {key2}", f"migrated {key3}"]
    )
    assert rc2 == 0

    # After the rerun, every key's ref on the origin and the mirror reads
    # as the facts a fresh `migrate` into a `MemoryRecord` gives back.
    for key in (key1, key2, key3):
        assert RefsRecord(origin).read(key) == expected[key]
        assert RefsRecord(mirror).read(key) == expected[key]


def _moving_post_receive(origin: Path, moved_to: Path) -> None:
    """Moves `origin`'s own directory away once a push lands, so the next
    push to the same path finds no repository."""
    hook = origin / "hooks" / "post-receive"
    hook.write_text(f"#!/bin/sh\nmv {str(origin)!r} {str(moved_to)!r}\nexit 0\n")
    hook.chmod(0o755)


def test_migrate_exits_two_when_infrastructure_fails_and_keeps_what_it_printed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from saffron import cli
    from saffron.record.refs import RefsRecord

    # Arm 1: a second row's dead origin shares the first row's mirror.
    # Every repo is fetched before any write, so the first still buys nothing.
    origin_a = _bare(tmp_path / "a" / "origin.git")
    scratch_a = _scratch_with_branch(tmp_path / "a" / "scratch")
    mirror_a = _mirror_of(scratch_a, tmp_path / "a" / "mirror.git")
    ghost_origin = tmp_path / "a" / "ghost-origin.git"

    source_a = Ledger(tmp_path / "a" / "source.db")
    repo_a1 = source_a.upsert_repo("repo-a1", str(origin_a), str(mirror_a), None)
    repo_a2 = source_a.upsert_repo("repo-a2", str(ghost_origin), str(mirror_a), None)
    _task(source_a, repo_a1, "SA-4001")
    _task(source_a, repo_a2, "SA-4002")
    source_a_path = tmp_path / "a" / "source.db"
    source_a.close()

    home_a = tmp_path / "a" / "home"
    rc_a = cli.main(["--home", str(home_a), "migrate", "--from", str(source_a_path)])
    out_a = capsys.readouterr().out
    assert rc_a == 2
    assert _reports(out_a) == []
    assert out_a.strip().startswith("saffron:")
    assert RefsRecord(mirror_a).task_keys() == []
    assert RefsRecord(origin_a).task_keys() == []
    assert not home_a.exists()

    # Arm 2: a source path that does not exist.
    missing = tmp_path / "missing.db"
    rc_b = cli.main(
        ["--home", str(tmp_path / "b" / "home"), "migrate", "--from", str(missing)]
    )
    out_b = capsys.readouterr().out
    assert rc_b == 2
    assert _reports(out_b) == []
    assert out_b.strip().startswith("saffron:")
    assert not missing.exists()
    assert not (tmp_path / "b" / "home").exists()

    # Arm 3: the origin moves away after the first push lands, so the
    # second push finds no repository at all.
    origin_c = _bare(tmp_path / "c" / "origin.git")
    moved_origin_c = tmp_path / "c" / "origin-moved.git"
    scratch_c = _scratch_with_branch(tmp_path / "c" / "scratch")
    mirror_c = _mirror_of(scratch_c, tmp_path / "c" / "mirror.git")
    _moving_post_receive(origin_c, moved_origin_c)

    source_c = Ledger(tmp_path / "c" / "source.db")
    repo_c = source_c.upsert_repo("repo-c", str(origin_c), str(mirror_c), None)
    _, task_c1 = _task(source_c, repo_c, "SA-4003")
    _, task_c2 = _task(source_c, repo_c, "SA-4004")
    key_c1 = _key(source_c, task_c1)
    source_c_path = tmp_path / "c" / "source.db"
    source_c.close()

    rc_c = cli.main(
        [
            "--home",
            str(tmp_path / "c" / "home"),
            "migrate",
            "--from",
            str(source_c_path),
        ]
    )
    out_c = capsys.readouterr().out
    out_lines_c = out_c.splitlines()
    assert out_lines_c[0] == f"migrated {key_c1}"
    assert out_lines_c[1].startswith("saffron: RecordError: ")
    assert rc_c == 2
    assert RefsRecord(moved_origin_c).read(key_c1)
