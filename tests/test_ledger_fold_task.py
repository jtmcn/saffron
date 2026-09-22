"""`Ledger._apply`/`fold_task`: the round trip between what a ledger's write
methods put in its own rows and what the same facts, read back, rebuild.

Rows are read through a `sqlite3` connection of its own, never through
`ledger._db`. The round trip is worth nothing if both sides share one path
into SQLite.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import pytest

from saffron.agents.findings import Finding, Severity
from saffron.gates.contract import Failure, GateResult
from saffron.ledger import SCHEMA, Ledger
from saffron.record.contract import Fact
from saffron.record.fold import UnreadableTask, fold
from saffron.record.memory import MemoryRecord


@pytest.fixture
def record():
    return MemoryRecord()


_JOIN_A = "JOIN attempts a USING (attempt_id) JOIN tasks t USING (task_id)"
_JOIN_G = f"JOIN gate_results g USING (gate_result_id) {_JOIN_A}"
_TABLE_SQL = {
    "tasks": "SELECT t.*, r.base_sha FROM tasks t JOIN runs r USING (run_id) WHERE record_key = ?",
    "attempts": "SELECT a.* FROM attempts a JOIN tasks t USING (task_id) WHERE t.record_key = ? ORDER BY a.phase, a.n",
    "gate_results": f"SELECT g.*, a.phase, a.n FROM gate_results g {_JOIN_A} WHERE t.record_key = ? ORDER BY a.phase, a.n, g.gate",
    "failures": f"SELECT f.*, a.phase, a.n, g.gate FROM failures f {_JOIN_G} WHERE t.record_key = ? ORDER BY a.phase, a.n, g.gate, f.file, f.code",
    "findings": "SELECT f.* FROM findings f JOIN tasks t USING (task_id) WHERE t.record_key = ? ORDER BY f.claim",
}
_TASK_SQL = _TABLE_SQL["tasks"]


def _raw_rows(path: Path, sql: str, key: str) -> list[dict]:
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute(sql, (key,))]
    finally:
        con.close()


_KEYS = {"task_id", "run_id", "attempt_id", "gate_result_id", "failure_id"}
_KEYS |= {"finding_id", "repo_id", "batch_id", "row_id"}


def _compact(row: dict) -> dict:
    """Every surrogate key and timestamp column left out. What two
    independently autoincremented ledgers can still be compared on."""
    return {k: v for k, v in row.items() if k not in _KEYS and not k.endswith("_at")}


def _table_rows(path: Path, sql: str, key: str) -> list[dict]:
    return [_compact(r) for r in _raw_rows(path, sql, key)]


def _snapshot(path: Path, key: str) -> dict[str, list[dict]]:
    return {name: _table_rows(path, sql, key) for name, sql in _TABLE_SQL.items()}


def _fact(key: str, kind: str, at: str, **payload) -> Fact:
    return Fact(kind=kind, task_key=key, at=at, repo="saffron", payload=payload)


def _without_finding(record: MemoryRecord, key: str, position: int) -> None:
    """Drop the task's `position`th `finding` fact (1 for the first)."""
    facts = record._facts[key]
    seen = 0
    kept = []
    for f in facts:
        if f.kind == "finding":
            seen += 1
            if seen == position:
                continue
        kept.append(f)
    record._facts[key] = kept


def _key(ledger: Ledger, task_id: int) -> str:
    """Turns `record_key`'s `str | None` back into `str` for a known task."""
    key = ledger.record_key(task_id)
    assert key is not None
    return key


def _fail(file: str, code: str, line: int, msg: str) -> Failure:
    return Failure(file=file, code=code, message=msg, line=line)


def _gate(gate: str, tool: str, *fails: Failure) -> GateResult:
    return GateResult(
        gate=gate,
        status="fail",
        tool=tool,
        duration_ms=1,
        summary="x",
        failures=list(fails),
    )


def _find(
    lens: str, sev: Severity, file: str, line: int, claim: str, anchored: bool = True
) -> Finding:
    return Finding(
        lens=lens, severity=sev, file=file, line=line, claim=claim, anchored=anchored
    )


def _close(
    ledger: Ledger, attempt_id: int, sid: str, model, reason, turns: int, cost: float
) -> None:
    ledger.close_attempt(
        attempt_id,
        session_id=sid,
        model=model,
        subtype="success",
        terminal_reason=reason,
        num_turns=turns,
        cost_usd_est=cost,
    )


def _minimal(ledger: Ledger, spec_id: str) -> int:
    """A task with nothing but `task_created`, under its own repo and run."""
    repo_id = ledger.upsert_repo("s", f"https://{spec_id}", "/m", policy_sha="p")
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    return ledger.create_task(run_id, spec_id=spec_id, spec_sha="s" * 64, branch="b")


def _seed_unrelated_task(tmp_path: Path, into: Ledger) -> None:
    """A task folded in before the tracked one, so no attempt or finding id
    the fold mints for the tracked task can equal one its own writer chose."""
    other = MemoryRecord()
    writer = Ledger(tmp_path / "unrelated.db", record=other)
    task_id = _minimal(writer, "SA-0")
    attempt_id = writer.open_attempt(task_id, phase="IMPLEMENT")
    writer.record_findings(task_id, [_find("a", "note", "z", 1, "u", False)])
    _close(writer, attempt_id, "u", None, None, 1, 0.1)
    writer.close()
    key = other.task_keys()[0]
    into.fold_task(key, other.read(key))


def _drive_eleven_kinds(source: Ledger, after) -> tuple[str, int]:
    """Every task fact kind once. `after(key)` runs once per write."""
    repo_id = source.upsert_repo("saffron", "https://o", "/m.git", policy_sha="p" * 64)
    run_id = source.create_run(repo_id, base_sha="a" * 40)
    task_id = source.create_task(
        run_id,
        spec_id="SA1",
        spec_sha="s" * 64,
        branch="br",
        risk="elevated",
        budget_usd=17.5,
        policy_sha="c" * 64,
        prompt_sha="g" * 64,
    )
    key = _key(source, task_id)
    after(key)
    a1 = source.open_attempt(task_id, phase="IMPLEMENT")
    after(key)
    gate1 = _gate("lint", "ruff", _fail("a", "E1", 3, "m1"), _fail("b", "E2", 9, "m2"))
    source.record_gate_result(gate1, attempt_id=a1)
    after(key)
    _close(source, a1, "s1", "m1", "done", 7, 3.25)
    after(key)
    source.set_task_state(task_id, "REVIEWING")
    after(key)
    (f1,) = source.record_findings(task_id, [_find("a", "blocker", "x", 4, "c1")])
    after(key)
    (f2,) = source.record_findings(task_id, [_find("s", "note", "y", 8, "c2", False)])
    after(key)
    source.record_rebuttal(f2, verdict="withdrawn", rebuttal="rebut two")
    after(key)
    source.record_rebuttal(f1, verdict="confirmed", rebuttal="rebut one")
    after(key)
    source.record_policy(task_id, "f" * 64)
    after(key)
    source.record_push(task_id, "d" * 40)
    after(key)
    source.set_task_package(task_id, "READY_FOR_REVIEW", "pkg", "e" * 40, "https://x/9")
    after(key)
    source.record_merged_head(task_id, "h" * 40)
    after(key)
    a2 = source.open_attempt(task_id, phase="IMPLEMENT")
    after(key)
    gate2 = _gate("types", "ty", _fail("c", "T1", 4, "m3"), _fail("d", "T2", 8, "m4"))
    source.record_gate_result(gate2, attempt_id=a2)
    after(key)
    _close(source, a2, "s2", "m2", "budget", 3, 1.10)
    after(key)
    return key, repo_id


def test_every_task_fact_kind_folds_back_to_the_rows_its_write_made(tmp_path, record):
    source_path, fold_path = tmp_path / "source.db", tmp_path / "fold.db"
    source = Ledger(source_path, record=record)
    into = Ledger(fold_path)
    _seed_unrelated_task(tmp_path, into)

    def check(key):
        into.fold_task(key, record.read(key))
        assert _snapshot(fold_path, key) == _snapshot(source_path, key)

    key, repo_id = _drive_eleven_kinds(source, check)

    final = _snapshot(fold_path, key)
    for table, rows in final.items():
        for row in rows:
            for column, value in row.items():
                if (table, column) != ("findings", "adjudication"):
                    assert value is not None, (table, column)
    assert final["failures"]

    prun = source.create_run(repo_id, base_sha="b" * 40)
    plain_id = source.create_task(prun, spec_id="S2", spec_sha="t" * 64, branch="pl")
    plain_key = _key(source, plain_id)
    into.fold_task(plain_key, record.read(plain_key))
    plain = _table_rows(fold_path, _TASK_SQL, plain_key)
    assert plain == _table_rows(source_path, _TASK_SQL, plain_key)
    assert plain[0]["risk"] == "standard"
    source.close()
    into.close()


def test_folding_into_a_ledger_with_a_record_appends_nothing(tmp_path, record):
    source = Ledger(tmp_path / "source.db", record=record)
    key, _ = _write_small_task(source, "SA-1")
    by_key = "SELECT task_id FROM tasks WHERE record_key = ?"
    task_id = _raw_rows(tmp_path / "source.db", by_key, key)[0]["task_id"]
    for kind in _UPDATED_AT_KINDS[1:]:
        _set_six_kind(source, task_id, kind)
    before = len(record.read(key))
    assert {f.kind for f in record.read(key)} >= set(_UPDATED_AT_KINDS)
    fold(record, source)
    assert len(record.read(key)) == before
    source.close()


def test_a_fact_the_ledger_cannot_place_leaves_the_ledger_as_it_was(tmp_path, record):
    writer = Ledger(tmp_path / "writer.db", record=record)
    key = _key(writer, _minimal(writer, "SA-2"))
    writer.close()
    good = record.read(key)
    bad = [*good, _fact(key, "decision", "2026-09-19T00:00:00+00:00")]

    fresh = Ledger(tmp_path / "fresh.db")
    with pytest.raises(ValueError, match="decision"):
        fresh.fold_task(key, bad)
    assert _table_rows(tmp_path / "fresh.db", _TASK_SQL, key) == []
    fresh.close()

    held = Ledger(tmp_path / "held.db")
    held.fold_task(key, good)
    before = _snapshot(tmp_path / "held.db", key)
    with pytest.raises(ValueError, match="decision"):
        held.fold_task(key, bad)
    assert _snapshot(tmp_path / "held.db", key) == before
    held.close()


_FOLD_BLIND = (
    "decision",
    "run_created",
    "run_finished",
    "run_preflight",
    "batch_created",
    "batch_closed",
    "repo_upserted",
)


def test_a_kind_the_ledger_cannot_place_aborts_the_fold_in_either_mode(
    tmp_path, record
):
    writer = Ledger(tmp_path / "writer.db", record=record)
    key = _key(writer, _minimal(writer, "SA-3"))
    writer.close()
    good = record.read(key)

    for kind in _FOLD_BLIND:
        bad = MemoryRecord()
        for f in good:
            bad.append(key, f)
        bad.append(key, _fact(key, kind, "2026-09-19T00:00:00+00:00"))
        for strict in (True, False):
            into = Ledger(tmp_path / f"into-{kind}-{strict}.db")
            with pytest.raises(ValueError, match=kind) as raised:
                fold(bad, into, strict=strict)
            assert not isinstance(raised.value, UnreadableTask)
            into.close()


def test_a_rebuttal_with_no_finding_skips_its_whole_task(tmp_path, record):
    writer = Ledger(tmp_path / "writer.db", record=record)
    task_id = _minimal(writer, "SA-4")
    (finding1,) = writer.record_findings(task_id, [_find("a", "blocker", "x", 1, "f1")])
    writer.record_findings(task_id, [_find("a", "concern", "y", 2, "f2")])
    writer.record_rebuttal(finding1, verdict="withdrawn", rebuttal="ok")
    key = _key(writer, task_id)
    next_key = _key(writer, _minimal(writer, "SA-5"))
    writer.close()
    _without_finding(record, key, 1)

    into = Ledger(tmp_path / "into.db")
    with pytest.raises(UnreadableTask, match=key):
        fold(record, into, strict=True)
    into.close()

    into2 = Ledger(tmp_path / "into2.db")
    result = fold(record, into2, strict=False)
    assert result.folded == 1
    assert [k for k, _ in result.skipped] == [key]
    assert _table_rows(tmp_path / "into2.db", _TASK_SQL, key) == []
    assert len(_table_rows(tmp_path / "into2.db", _TASK_SQL, next_key)) == 1
    into2.close()


def _write_small_task(ledger: Ledger, spec_id: str) -> tuple[str, int]:
    task_id = _minimal(ledger, spec_id)
    attempt_id = ledger.open_attempt(task_id, phase="IMPLEMENT")
    gate = _gate("lint", "ruff", _fail("a", "E1", 1, "m"))
    ledger.record_gate_result(gate, attempt_id=attempt_id)
    _close(ledger, attempt_id, "s", None, None, 1, 0.5)
    (f1,) = ledger.record_findings(task_id, [_find("a", "blocker", "x", 1, spec_id)])
    ledger.record_findings(task_id, [_find("a", "concern", "y", 2, spec_id + "2")])
    ledger.record_rebuttal(f1, verdict="withdrawn", rebuttal="ok")
    return _key(ledger, task_id), f1


_BREAKAGES = ("not-a-fact", "no-task-created", "orphan-rebuttal")


def _break(record: MemoryRecord, breakage: str, key: str, position: int) -> None:
    if breakage == "not-a-fact":
        corrupted: list = ["not a fact"]
        record._facts[key] = corrupted
    elif breakage == "no-task-created":
        record._facts[key] = [f for f in record._facts[key] if f.kind != "task_created"]
    else:
        _without_finding(record, key, position)


def test_a_task_that_became_unreadable_leaves_a_surviving_ledger(tmp_path):
    for breakage in _BREAKAGES:
        for strict in (True, False):
            case = tmp_path / f"{breakage}-{strict}"
            case.mkdir()
            record = MemoryRecord()
            writer = Ledger(case / "writer.db", record=record)
            key_a, _ = _write_small_task(writer, "SA-A")
            key_b, _ = _write_small_task(writer, "SA-B")
            writer.close()

            into_path = case / "into.db"
            into = Ledger(into_path)
            fold(record, into)
            kept = _snapshot(into_path, key_b)
            _break(record, breakage, key_a, 1)  # position 1: the first finding

            if strict:
                with pytest.raises(UnreadableTask):
                    fold(record, into, strict=True)
            else:
                fold(record, into, strict=False)

            for table, sql in _TABLE_SQL.items():
                case_id = (breakage, strict, table)
                assert _table_rows(into_path, sql, key_a) == [], case_id
            assert _snapshot(into_path, key_b) == kept
            into.close()


_UPDATED_AT_KINDS = (
    "task_created",
    "task_state",
    "task_package",
    "task_push",
    "task_merged_head",
    "task_policy",
)


def _set_six_kind(ledger: Ledger, task_id: int, kind: str) -> None:
    """Every kind but `task_created`, which `_minimal` already wrote."""
    if kind == "task_state":
        ledger.set_task_state(task_id, "IMPLEMENTING")
    elif kind == "task_package":
        ledger.set_task_package(task_id, "READY_FOR_REVIEW", "b2", "d" * 40, "u")
    elif kind == "task_push":
        ledger.record_push(task_id, "e" * 40)
    elif kind == "task_merged_head":
        ledger.record_merged_head(task_id, "f" * 40)
    else:
        ledger.record_policy(task_id, "c" * 64)


def _retimed(record: MemoryRecord, key: str) -> None:
    """Every fact for `key`, one minute apart and oldest first. Each column
    is then checked against a value distinct from every other fact's."""
    facts = record.read(key)
    record._facts[key] = [
        replace(f, at=f"2026-09-19T00:{i:02d}:00+00:00") for i, f in enumerate(facts, 1)
    ]


def test_a_folded_task_is_dated_by_the_facts_that_set_each_column(tmp_path):
    for target in _UPDATED_AT_KINDS:
        record = MemoryRecord()
        writer = Ledger(tmp_path / f"{target}.db", record=record)
        task_id = _minimal(writer, target)
        key = _key(writer, task_id)
        target_n = 1
        if target != "task_created":
            others = [k for k in _UPDATED_AT_KINDS if k not in ("task_created", target)]
            for kind in others:
                _set_six_kind(writer, task_id, kind)
            _set_six_kind(writer, task_id, target)
            target_n = 1 + len(others) + 1
            attempt_id = writer.open_attempt(task_id, phase="REPAIR")
            writer.record_gate_result(_gate("lint", "ruff"), attempt_id=attempt_id)
            _close(writer, attempt_id, "s", None, None, 1, 0.1)
            (f1,) = writer.record_findings(task_id, [_find("a", "note", "x", 1, "1")])
            (f2,) = writer.record_findings(task_id, [_find("a", "note", "y", 2, "2")])
            writer.record_rebuttal(f2, verdict="withdrawn", rebuttal="r2")
            writer.record_rebuttal(f1, verdict="confirmed", rebuttal="r1")
        writer.close()
        _retimed(record, key)

        into = Ledger(tmp_path / f"{target}-into.db")
        fold(record, into)
        query = "SELECT updated_at FROM tasks WHERE record_key = ?"
        got = _raw_rows(tmp_path / f"{target}-into.db", query, key)
        assert got == [{"updated_at": f"2026-09-19 00:{target_n:02d}:00"}]
        run = "SELECT r.started_at FROM runs r JOIN tasks t USING (run_id) WHERE record_key = ?"
        got = _raw_rows(tmp_path / f"{target}-into.db", run, key)
        assert got == [{"started_at": "2026-09-19 00:01:00"}]
        if target != "task_created":
            times = "SELECT a.started_at, a.ended_at FROM attempts a JOIN tasks t USING (task_id) WHERE record_key = ?"
            got = _raw_rows(tmp_path / f"{target}-into.db", times, key)
            opened, closed = f"00:{target_n + 1:02d}", f"00:{target_n + 3:02d}"
            assert got == [
                {
                    "started_at": f"2026-09-19 {opened}:00",
                    "ended_at": f"2026-09-19 {closed}:00",
                }
            ]
        into.close()


class _Recording:
    """Forwards `fold_task` to a real `Ledger`. Any other attribute is
    recorded and raises, so `fold()` reaching past `fold_task` shows up as
    a raised error rather than a silently swallowed `AttributeError`."""

    def __init__(self, real: Ledger) -> None:
        self._real = real
        self.touched: list[str] = []

    def fold_task(self, key: str, facts) -> None:
        self._real.fold_task(key, facts)

    def __getattr__(self, name: str):
        self.touched.append(name)
        raise RuntimeError(f"fold reached Ledger.{name} directly")


def test_the_fold_reaches_the_ledger_only_through_fold_task(tmp_path, record):
    writer = Ledger(tmp_path / "writer.db", record=record)
    _minimal(writer, "SA-6")
    bad_id = _minimal(writer, "SA-7")
    (finding_id,) = writer.record_findings(bad_id, [_find("a", "note", "x", 1, "c")])
    writer.record_rebuttal(finding_id, verdict="withdrawn", rebuttal="ok")
    bad_key = _key(writer, bad_id)
    writer.close()
    record._facts[bad_key] = [f for f in record._facts[bad_key] if f.kind != "finding"]

    real = Ledger(tmp_path / "real-loose.db")
    stand_in = _Recording(real)
    result = fold(record, cast(Ledger, stand_in), strict=False)
    assert stand_in.touched == []
    assert result.folded == 1
    assert [k for k, _ in result.skipped] == [bad_key]
    real.close()

    real_strict = Ledger(tmp_path / "real-strict.db")
    stand_in_strict = _Recording(real_strict)
    with pytest.raises(UnreadableTask, match=bad_key):
        fold(record, cast(Ledger, stand_in_strict), strict=True)
    assert stand_in_strict.touched == []
    real_strict.close()


def _idless(row: dict) -> dict:
    return {k: v for k, v in row.items() if k not in _KEYS}


_CLOCK_DAY = re.compile(r"^2001-01-01 \d{2}:\d{2}:\d{2}$")


class _MinuteClock(datetime):
    """`datetime.now`: 2001-01-01, a minute later on each call."""

    calls = 0

    @classmethod
    def now(cls, tz=None):
        del tz  # Always UTC. Kept only to match `datetime.now`'s signature.
        cls.calls += 1
        return cls(2001, 1, 1, tzinfo=UTC) + timedelta(minutes=cls.calls - 1)


def _assert_stamped_by_the_clock(path: Path, key: str) -> None:
    for table, sql in _TABLE_SQL.items():
        for row in _raw_rows(path, sql, key):
            for column, value in row.items():
                if column.endswith("_at") and value is not None:
                    assert _CLOCK_DAY.match(value), (table, column, value)


def test_a_written_task_folds_back_with_the_times_its_facts_carry(
    tmp_path, record, monkeypatch
):
    monkeypatch.setattr("saffron.ledger.datetime", _MinuteClock)
    _MinuteClock.calls = 0
    source_path, fold_path = tmp_path / "source.db", tmp_path / "fold.db"
    source = Ledger(source_path, record=record)
    into = Ledger(fold_path)

    def check(key):
        into.fold_task(key, record.read(key))
        for sql in _TABLE_SQL.values():
            fold_rows = [_idless(r) for r in _raw_rows(fold_path, sql, key)]
            assert fold_rows == [_idless(r) for r in _raw_rows(source_path, sql, key)]
        _assert_stamped_by_the_clock(fold_path, key)

    _drive_eleven_kinds(source, check)
    source.close()
    into.close()

    # The same writes, no record attached: still stamped by the clock.
    _MinuteClock.calls = 0
    plain_path = tmp_path / "plain.db"
    plain = Ledger(plain_path)
    _drive_eleven_kinds(plain, lambda k: _assert_stamped_by_the_clock(plain_path, k))
    plain.close()


def test_each_fact_lands_on_the_attempt_or_finding_it_names(tmp_path, record):
    source_path, fold_path = tmp_path / "source.db", tmp_path / "fold.db"
    source = Ledger(source_path, record=record)
    into = Ledger(fold_path)
    # An unrelated IMPLEMENT-1 attempt and finding in both, to catch scoping.
    _seed_unrelated_task(tmp_path / "src-seed", source)
    _seed_unrelated_task(tmp_path / "dst-seed", into)

    task_id = _minimal(source, "SA-9")
    key = _key(source, task_id)

    i1 = source.open_attempt(task_id, phase="IMPLEMENT")
    i2 = source.open_attempt(task_id, phase="IMPLEMENT")
    r1 = source.open_attempt(task_id, phase="REPAIR")

    def gate_and_close(attempt_id: int, gate: str, turns: int) -> None:
        source.record_gate_result(_gate(gate, "tool"), attempt_id=attempt_id)
        _close(source, attempt_id, f"s{attempt_id}", None, None, turns, 0.1)

    # Written out of open order: 2, then REPAIR 1, then 1.
    gate_and_close(i2, "types", 11)
    gate_and_close(r1, "tests", 22)
    gate_and_close(i1, "lint", 33)

    f1, f2 = source.record_findings(
        task_id,
        [_find("a", "blocker", "x", 1, "c1"), _find("a", "concern", "y", 2, "c2")],
    )
    (f3,) = source.record_findings(task_id, [_find("a", "note", "z", 3, "c3")])
    source.record_rebuttal(f3, verdict="confirmed", rebuttal="third")
    source.record_rebuttal(f1, verdict="withdrawn", rebuttal="first")
    source.record_rebuttal(f2, verdict="confirmed", rebuttal="second")

    into.fold_task(key, record.read(key))

    for path in (source_path, fold_path):
        turns = {
            (r["phase"], r["n"]): r["num_turns"]
            for r in _raw_rows(path, _TABLE_SQL["attempts"], key)
        }
        got = {
            (r["phase"], r["n"]): (turns[r["phase"], r["n"]], r["gate"])
            for r in _raw_rows(path, _TABLE_SQL["gate_results"], key)
        }
        assert got == {
            ("IMPLEMENT", 1): (33, "lint"),
            ("IMPLEMENT", 2): (11, "types"),
            ("REPAIR", 1): (22, "tests"),
        }
        claims = {
            r["claim"]: r["rebuttal"]
            for r in _raw_rows(path, _TABLE_SQL["findings"], key)
        }
        assert claims == {"c1": "first", "c2": "second", "c3": "third"}

    source.close()
    into.close()


def _compact_facts(facts: list[Fact]) -> list[tuple[str, dict]]:
    """Kind and payload alone, never the independently minted `task_key`/`at`."""
    return [(f.kind, f.payload) for f in facts]


def test_two_ledgers_making_the_same_writes_append_the_same_facts(tmp_path):
    busy_record = MemoryRecord()
    busy = Ledger(tmp_path / "busy.db", record=busy_record)
    for spec_id in ("SA-X", "SA-Y"):
        other_id = _minimal(busy, spec_id)
        attempt_id = busy.open_attempt(other_id, phase="IMPLEMENT")
        busy.record_gate_result(
            _gate("lint", "ruff", _fail("a", "E1", 1, "m")), attempt_id=attempt_id
        )
        busy.record_findings(other_id, [_find("a", "note", "x", 1, spec_id)])

    empty_record = MemoryRecord()
    empty = Ledger(tmp_path / "empty.db", record=empty_record)

    def drive(ledger: Ledger) -> str:
        task_id = _minimal(ledger, "SA-T")
        a1 = ledger.open_attempt(task_id, phase="IMPLEMENT")
        ledger.record_gate_result(_gate("lint", "ruff"), attempt_id=a1)
        _close(ledger, a1, "s1", None, None, 1, 0.1)
        f1, f2 = ledger.record_findings(
            task_id,
            [_find("a", "blocker", "x", 1, "c1"), _find("a", "concern", "y", 2, "c2")],
        )
        (f3,) = ledger.record_findings(task_id, [_find("a", "note", "z", 3, "c3")])
        ledger.record_rebuttal(f3, verdict="confirmed", rebuttal="r3")
        ledger.record_rebuttal(f1, verdict="withdrawn", rebuttal="r1")
        ledger.record_rebuttal(f2, verdict="confirmed", rebuttal="r2")
        return _key(ledger, task_id)

    key_busy = drive(busy)
    key_empty = drive(empty)
    busy.close()
    empty.close()

    assert _compact_facts(busy_record.read(key_busy)) == _compact_facts(
        empty_record.read(key_empty)
    )


_KEY_RE = re.compile(r"^[0-9a-f]{32}$")


def _old_file(path: Path, schema: str, spec_ids: tuple[str, ...]) -> None:
    """A pre-record ledger file, built by hand, never through `Ledger`."""
    con = sqlite3.connect(path)
    con.executescript(schema)
    con.execute("INSERT INTO repos (name, origin, mirror_path) VALUES ('r', 'o', '/m')")
    con.execute("INSERT INTO runs (repo_id, base_sha) VALUES (1, 'a')")
    for spec_id in spec_ids:
        con.execute(
            "INSERT INTO tasks (run_id, spec_id, spec_sha, state, branch) "
            "VALUES (1, ?, 's', 'QUEUED', 'b')",
            (spec_id,),
        )
    con.commit()
    con.close()


def _stored_keys(path: Path) -> list[str]:
    con = sqlite3.connect(path)
    try:
        return [r[0] for r in con.execute("SELECT record_key FROM tasks")]
    finally:
        con.close()


def test_every_task_carries_a_record_key_with_or_without_a_record(tmp_path, record):
    with_record = Ledger(tmp_path / "with-record.db", record=record)
    task_a = _minimal(with_record, "SA-A")
    assert _KEY_RE.match(_key(with_record, task_a))
    with_record.close()

    no_record = Ledger(tmp_path / "no-record.db")
    task_b = _minimal(no_record, "SA-B")
    assert _KEY_RE.match(_key(no_record, task_b))
    no_record.close()

    def backfilled(path: Path, schema: str, spec_ids: tuple[str, ...]) -> None:
        _old_file(path, schema, spec_ids)
        opened = Ledger(path)
        keys = _stored_keys(path)
        assert len(keys) == len(spec_ids) == len(set(keys))
        assert all(_KEY_RE.match(k) for k in keys)
        opened.close()

    # A record_key column already there and NULL, the additive ALTER's shape.
    backfilled(tmp_path / "null-column.db", SCHEMA, ("SA-C", "SA-D"))

    # No such column at all, which is older still.
    no_column_schema = SCHEMA.replace("    record_key TEXT,\n", "")
    assert no_column_schema != SCHEMA  # otherwise this proves nothing
    backfilled(tmp_path / "no-column.db", no_column_schema, ("SA-E", "SA-F"))


def test_a_backfilled_task_written_with_a_record_folds_as_unreadable(tmp_path, record):
    path = tmp_path / "old.db"
    _old_file(path, SCHEMA, ("SA-Z",))

    reopened = Ledger(path, record=record)
    task_id = reopened._db.execute("SELECT task_id FROM tasks").fetchone()["task_id"]
    key = _key(reopened, task_id)
    reopened.set_task_state(task_id, "IMPLEMENTING")
    reopened.close()

    assert record.task_keys() == [key]
    assert [f.kind for f in record.read(key)] == ["task_state"]

    into = Ledger(tmp_path / "into.db")
    result = fold(record, into, strict=False)
    assert result.folded == 0
    (skipped_key, reason) = result.skipped[0]
    assert skipped_key == key
    assert "no task_created fact" in reason
    into.close()


def _table_counts(ledger: Ledger) -> dict[str, int]:
    return {
        table: ledger._db.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
        for table in ("tasks", "attempts", "gate_results", "findings")
    }


def _ten_missing_writes(ledger: Ledger, missing: int) -> None:
    calls = [
        lambda: ledger.set_task_state(missing, "IMPLEMENTING"),
        lambda: ledger.set_task_package(missing, "X", "b", "d" * 40, "u"),
        lambda: ledger.record_push(missing, "d" * 40),
        lambda: ledger.record_merged_head(missing, "h" * 40),
        lambda: ledger.record_policy(missing, "p" * 64),
        lambda: ledger.record_findings(missing, [_find("a", "note", "x", 1, "c")]),
        lambda: ledger.open_attempt(missing, phase="IMPLEMENT"),
        lambda: _close(ledger, missing, "s", None, None, 1, 0.1),
        lambda: ledger.record_gate_result(_gate("lint", "ruff"), attempt_id=missing),
        lambda: ledger.record_rebuttal(missing, verdict="withdrawn", rebuttal="x"),
    ]
    for call in calls:
        with pytest.raises(ValueError):
            call()


_EMPTY_COUNTS = {"tasks": 0, "attempts": 0, "gate_results": 0, "findings": 0}


def test_a_write_naming_nothing_the_ledger_holds_raises_and_files_nothing(
    tmp_path, record
):
    missing = 999_999
    with_record = Ledger(tmp_path / "with-record.db", record=record)
    _ten_missing_writes(with_record, missing)
    assert record.task_keys() == []
    assert _table_counts(with_record) == _EMPTY_COUNTS
    with_record.close()

    no_record = Ledger(tmp_path / "no-record.db")
    _ten_missing_writes(no_record, missing)
    assert _table_counts(no_record) == _EMPTY_COUNTS
    no_record.close()


class _BustedApply(Exception):
    """Never mistaken for one `_apply` can raise on its own."""


def _busted_apply(*_args: object, **_kwargs: object) -> None:
    raise _BustedApply


def _eleven_write_calls(ledger, run_id, task_id, attempt_id, finding_id):
    """Not nested in the test's loop, so ruff sees no captured loop variable."""
    return [
        lambda: ledger.create_task(run_id, spec_id="SA-14", spec_sha="s", branch="b"),
        lambda: ledger.open_attempt(task_id, phase="IMPLEMENT"),
        lambda: _close(ledger, attempt_id, "s", None, None, 1, 0.1),
        lambda: ledger.record_gate_result(_gate("lint", "ruff"), attempt_id=attempt_id),
        lambda: ledger.set_task_state(task_id, "IMPLEMENTING"),
        lambda: ledger.record_findings(task_id, [_find("a", "note", "y", 2, "c2")]),
        lambda: ledger.record_rebuttal(finding_id, verdict="withdrawn", rebuttal="x"),
        lambda: ledger.record_policy(task_id, "p" * 64),
        lambda: ledger.record_push(task_id, "d" * 40),
        lambda: ledger.set_task_package(task_id, "X", "b", "d" * 40, "u"),
        lambda: ledger.record_merged_head(task_id, "h" * 40),
    ]


def test_every_task_write_applies_its_fact_through_apply(tmp_path, record, monkeypatch):
    for suffix, rec in (("with-record", record), ("no-record", None)):
        ledger = Ledger(tmp_path / f"{suffix}.db", record=rec)
        task_id = _minimal(ledger, "SA-13")
        attempt_id = ledger.open_attempt(task_id, phase="IMPLEMENT")
        ledger.record_gate_result(_gate("lint", "ruff"), attempt_id=attempt_id)
        (finding_id,) = ledger.record_findings(
            task_id, [_find("a", "note", "x", 1, "c")]
        )
        run_id = ledger._db.execute(
            "SELECT run_id FROM tasks WHERE task_id = ?", (task_id,)
        ).fetchone()["run_id"]

        monkeypatch.setattr(Ledger, "_apply", _busted_apply)
        for call in _eleven_write_calls(
            ledger, run_id, task_id, attempt_id, finding_id
        ):
            with pytest.raises(_BustedApply):
                call()
        monkeypatch.undo()
        ledger.close()
