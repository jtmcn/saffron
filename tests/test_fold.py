import pytest

from saffron.gates.contract import GateResult
from saffron.ledger import Ledger
from saffron.record.fold import fold
from saffron.record.memory import MemoryRecord


@pytest.fixture
def record():
    return MemoryRecord()


def a_night(tmp_path, record):
    """One task through creation, an attempt, a gate result and a state."""
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
    return source


def rows(ledger):
    """Every row that describes the night, with the autoincrement ids left
    out — the fold mints those, so they are not what has to match."""
    tasks = [
        dict(r)
        for r in ledger._db.execute(
            "SELECT spec_id, spec_sha, state, risk, branch, budget_usd,"
            "       spent_usd_est, record_key FROM tasks ORDER BY record_key"
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
    return tasks, attempts, gates


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
    _, attempts, gates = rows(into)
    _, want_attempts, want_gates = rows(source)
    assert attempts == want_attempts
    assert gates == want_gates
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
