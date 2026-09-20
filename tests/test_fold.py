import subprocess
from dataclasses import replace

import pytest

from saffron.agents.findings import Finding
from saffron.gates.contract import GateResult
from saffron.ledger import Ledger
from saffron.record.fold import fold
from saffron.record.memory import MemoryRecord
from saffron.record.refs import RefsRecord


@pytest.fixture
def record():
    return MemoryRecord()


def a_night(tmp_path, record):
    """One task through every write a real one makes: creation, an attempt, a
    gate result, a state, a policy, a finding and its rebuttal, a push, a
    package and a merged head."""
    source = Ledger(tmp_path / "source.db", record=record)
    repo_id = source.upsert_repo("saffron", "/o", "/m.git", policy_sha="p" * 64)
    run_id = source.create_run(repo_id, base_sha="a" * 40)
    task_id = source.create_task(
        run_id,
        spec_id="SA-0099",
        spec_sha="s" * 64,
        branch="saffron/SA-0099",
        risk="elevated",
        budget_usd=12,
    )
    attempt_id = source.open_attempt(task_id, phase="IMPLEMENTING")
    source.record_gate_result(
        GateResult(
            gate="lint",
            status="pass",
            tool="ruff 0.6.0",
            duration_ms=9,
            summary="clean",
        ),
        attempt_id=attempt_id,
    )
    source.close_attempt(
        attempt_id,
        session_id="s",
        subtype="success",
        terminal_reason=None,
        num_turns=4,
        cost_usd_est=1.25,
    )
    source.set_task_state(task_id, "READY_FOR_REVIEW")
    source.record_policy(task_id, "c" * 64)
    finding_id = source.record_findings(
        task_id,
        [
            Finding(
                lens="adequacy",
                severity="blocker",
                file="saffron/task.py",
                line=3,
                claim="no witness guards the new branch",
                anchored=True,
            )
        ],
    )[0]
    source.record_rebuttal(finding_id, verdict="withdrawn", rebuttal="fair")
    source.record_push(task_id, "d" * 40)
    source.set_task_package(
        task_id, "READY_FOR_REVIEW", "saffron/SA-0099", "d" * 40, "https://x/1"
    )
    source.record_merged_head(task_id, "e" * 40)
    return source


def rows(ledger):
    """Every row that describes the night, with the autoincrement ids left
    out — the fold mints those, so they are not what has to match. The columns
    `queue_lines` and `reconcile` read are in here deliberately: a criterion
    that excludes them cannot show the fold dropping them."""
    tasks = [
        dict(r)
        for r in ledger._db.execute(
            "SELECT spec_id, spec_sha, state, risk, branch, budget_usd,"
            "       spent_usd_est, record_key, pushed_sha, pr_url, policy_sha,"
            "       merged_head_sha FROM tasks ORDER BY record_key"
        )
    ]
    attempts = [
        dict(r)
        for r in ledger._db.execute(
            "SELECT phase, n, session_id, subtype, num_turns, cost_usd_est"
            "  FROM attempts ORDER BY phase, n"
        )
    ]
    gates = [
        dict(r)
        for r in ledger._db.execute(
            "SELECT gate, status, tool, summary FROM gate_results ORDER BY gate"
        )
    ]
    found = [
        dict(r)
        for r in ledger._db.execute(
            "SELECT lens, severity, file, line, claim, anchored, verdict,"
            "       rebuttal FROM findings ORDER BY finding_id"
        )
    ]
    return tasks, attempts, gates, found


def test_folding_an_empty_record_makes_no_rows(tmp_path, record):
    into = Ledger(tmp_path / "into.db")
    assert fold(record, into) == 0
    assert rows(into)[0] == []
    into.close()


def test_the_fold_reproduces_the_task(tmp_path, record):
    source = a_night(tmp_path, record)
    into = Ledger(tmp_path / "into.db")
    assert fold(record, into) == 1
    assert rows(into)[0] == rows(source)[0]
    source.close()
    into.close()


def test_the_fold_reproduces_attempts_and_gate_results(tmp_path, record):
    source = a_night(tmp_path, record)
    into = Ledger(tmp_path / "into.db")
    fold(record, into)
    _, attempts, gates, found = rows(into)
    _, want_attempts, want_gates, want_found = rows(source)
    assert attempts == want_attempts
    assert gates == want_gates
    assert found == want_found
    source.close()
    into.close()


def test_delete_the_index_rebuild_it_and_get_the_same_rows(tmp_path, record):
    # Spec §4's acceptance criterion, and the reason the ledger may be deleted
    # at any time.
    source = a_night(tmp_path, record)
    first = Ledger(tmp_path / "a.db")
    fold(record, first)
    want = rows(first)
    first.close()
    (tmp_path / "a.db").unlink()

    second = Ledger(tmp_path / "a.db")
    fold(record, second)
    assert rows(second) == want
    second.close()
    source.close()


def test_folding_twice_into_one_ledger_does_not_double_the_rows(tmp_path, record):
    # The fold is an upsert keyed on `record_key`, not an append: a rebuild
    # that runs twice must be indistinguishable from one that ran once.
    source = a_night(tmp_path, record)
    into = Ledger(tmp_path / "into.db")
    fold(record, into)
    once = rows(into)
    fold(record, into)
    assert rows(into) == once
    source.close()
    into.close()


def test_the_fold_keeps_error_and_fail_apart(tmp_path, record):
    source = Ledger(tmp_path / "source.db", record=record)
    repo_id = source.upsert_repo("saffron", "/o", "/m.git", policy_sha="p")
    run_id = source.create_run(repo_id, base_sha="a" * 40)
    task_id = source.create_task(
        run_id,
        spec_id="SA-0099",
        spec_sha="s" * 64,
        branch="b",
    )
    attempt_id = source.open_attempt(task_id)
    for status in ("error", "fail"):
        source.record_gate_result(
            GateResult(
                gate=f"g-{status}",
                status=status,
                tool="t",
                duration_ms=1,
                summary=status,
            ),
            attempt_id=attempt_id,
        )
    into = Ledger(tmp_path / "into.db")
    fold(record, into)
    assert [g["status"] for g in rows(into)[2]] == ["error", "fail"]
    source.close()
    into.close()


def test_an_unreadable_task_names_itself_and_folds_the_rest(tmp_path, record):
    # A record one task cannot be read from must still produce an index of
    # the others, or one bad task costs a whole night's page.
    a_night(tmp_path, record)
    record.append("f" * 32, record.read(record.task_keys()[0])[0])
    record._facts["f" * 32] = ["not a fact"]
    into = Ledger(tmp_path / "into.db")
    with pytest.raises(ValueError, match="f" * 32):
        fold(record, into, strict=True)
    assert fold(record, into, strict=False) == 1
    into.close()


def _read(ledger, query):
    return [tuple(r) for r in ledger._db.execute(query)]


def _retimed(fact, key, at, spec_id):
    payload = dict(fact.payload)
    if fact.kind == "task_created":
        payload["spec_id"] = spec_id
    return replace(fact, task_key=key, at=at, payload=payload)


def test_the_fold_restores_the_times_the_facts_carry(tmp_path, record):
    # `projection` ties a task to its ceiling span by `runs.started_at`, so an
    # index carrying the fold's own clock ties every task to one instant.
    a_night(tmp_path, record).close()
    key = record.task_keys()[0]
    record._facts[key] = [
        replace(f, at="2026-09-19T01:02:03+00:00") for f in record._facts[key]
    ]
    into = Ledger(tmp_path / "into.db")
    fold(record, into)
    assert _read(into, "SELECT started_at FROM runs") == [("2026-09-19 01:02:03",)]
    assert _read(into, "SELECT started_at, ended_at FROM attempts") == [
        ("2026-09-19 01:02:03", "2026-09-19 01:02:03")
    ]
    assert _read(into, "SELECT updated_at FROM tasks") == [("2026-09-19 01:02:03",)]
    into.close()


def test_tasks_are_folded_oldest_first(tmp_path, record):
    # `ORDER BY t.task_id` is read as a chronology, and a record key is random
    # hex — so the key sorting first here is the task that happened second.
    a_night(tmp_path, record).close()
    facts = record.read(record.task_keys()[0])
    record._facts.clear()
    for key, at, spec_id in (
        ("a" * 32, "2026-09-19T09:00:00+00:00", "SA-0002"),
        ("b" * 32, "2026-09-18T09:00:00+00:00", "SA-0001"),
    ):
        record._facts[key] = [_retimed(f, key, at, spec_id) for f in facts]
    into = Ledger(tmp_path / "into.db")
    assert fold(record, into) == 2
    assert _read(into, "SELECT spec_id FROM tasks ORDER BY task_id") == [
        ("SA-0001",),
        ("SA-0002",),
    ]
    into.close()


def test_a_task_git_cannot_read_is_skipped_and_the_rest_fold(tmp_path, record):
    # The likeliest unreadable task there is: a fact object git no longer has.
    # `RefsRecord.read` raises `CalledProcessError`, which no named tuple lists.
    repo = tmp_path / "record.git"
    subprocess.run(["git", "init", "-q", "--bare", str(repo)], check=True)
    on_refs = RefsRecord(repo)
    a_night(tmp_path, on_refs).close()
    a_night(tmp_path, on_refs).close()
    broken, whole = sorted(on_refs.task_keys())
    blob = on_refs._blobs(broken)[0][1]
    (repo / "objects" / blob[:2] / blob[2:]).unlink()

    into = Ledger(tmp_path / "into.db")
    with pytest.raises(ValueError, match=broken):
        fold(on_refs, into, strict=True)
    assert fold(on_refs, into, strict=False) == 1
    assert _read(into, "SELECT record_key FROM tasks") == [(whole,)]
    into.close()


def test_a_task_that_fails_mid_replay_leaves_no_rows_behind(tmp_path, record):
    # `Ledger`'s methods commit as they go, so the replay is not one
    # transaction: a task that dies partway is discarded rather than left half.
    a_night(tmp_path, record).close()
    key = record.task_keys()[0]
    record._facts[key] = record._facts[key][:3] + ["not a fact"]
    into = Ledger(tmp_path / "into.db")
    assert fold(record, into, strict=False) == 0
    assert _read(into, "SELECT COUNT(*) FROM tasks") == [(0,)]
    assert _read(into, "SELECT COUNT(*) FROM attempts") == [(0,)]
    assert _read(into, "SELECT COUNT(*) FROM gate_results") == [(0,)]
    into.close()


def test_a_task_that_pushed_without_packaging_keeps_its_sha(tmp_path, record):
    # `record_push` runs where no pull request follows and `reconcile` reads
    # `pushed_sha`, so the push fact is not the package's saying the same thing.
    source = Ledger(tmp_path / "source.db", record=record)
    repo_id = source.upsert_repo("saffron", "/o", "/m.git", policy_sha="p")
    run_id = source.create_run(repo_id, base_sha="a" * 40)
    task_id = source.create_task(
        run_id, spec_id="SA-0099", spec_sha="s" * 64, branch="b"
    )
    source.record_push(task_id, "d" * 40)
    source.set_task_state(task_id, "MERGE_FAILED")
    into = Ledger(tmp_path / "into.db")
    fold(record, into)
    assert _read(into, "SELECT state, pushed_sha, pr_url FROM tasks") == [
        ("MERGE_FAILED", "d" * 40, None)
    ]
    source.close()
    into.close()
