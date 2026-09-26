"""`Ledger.record_qualification` and the `qualifications` table it writes.

Rows are read through a `sqlite3` connection of its own, never through
`ledger._db`, the way `test_ledger_fold_task.py` reads every other table.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from saffron.agents.findings import Finding, Severity
from saffron.ledger import Ledger
from saffron.probe import Verdict
from saffron.record.fold import fold
from saffron.record.memory import MemoryRecord


@pytest.fixture
def record():
    return MemoryRecord()


def _find(
    lens: str,
    sev: Severity,
    file: str,
    line: int,
    claim: str,
    verdict: Verdict | None,
) -> Finding:
    return Finding(
        lens=lens,
        severity=sev,
        file=file,
        line=line,
        claim=claim,
        probe_verdict=verdict,
    )


def _key(ledger: Ledger, task_id: int) -> str:
    key = ledger.record_key(task_id)
    assert key is not None
    return key


def _task(ledger: Ledger, spec_id: str) -> int:
    repo_id = ledger.upsert_repo("s", f"https://{spec_id}", "/m", policy_sha="p")
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    return ledger.create_task(run_id, spec_id=spec_id, spec_sha="s" * 64, branch="b")


def _rows(path: Path, *keys: str) -> list[dict]:
    """Every row for `keys`, in the order given and by `position` within one.
    Every row when `keys` is empty, ordered by `task_key` for a plain compare."""
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    try:
        if not keys:
            rows = con.execute(
                "SELECT * FROM qualifications ORDER BY task_key, position"
            ).fetchall()
            return [dict(r) for r in rows]
        found = []
        for key in keys:
            found += [
                dict(r)
                for r in con.execute(
                    "SELECT * FROM qualifications WHERE task_key = ? ORDER BY position",
                    (key,),
                ).fetchall()
            ]
        return found
    finally:
        con.close()


def test_a_qualification_is_one_fact_and_one_row_numbered_within_its_task(
    tmp_path, record
):
    path = tmp_path / "ledger.db"
    ledger = Ledger(path, record=record)
    te1 = _task(ledger, "TE-1")
    te2 = _task(ledger, "TE-2")
    key1, key2 = _key(ledger, te1), _key(ledger, te2)

    ledger.record_qualification(
        te1,
        finding=_find("spec", "blocker", "src/a.py", 3, "q1", "survived"),
        filed="concern",
        outcome="qualified",
        reason="",
    )
    ledger.record_qualification(
        te2,
        finding=_find("standards", "note", "src/b.py", 7, "q2", "killed"),
        filed="blocker",
        outcome="killed",
        reason="",
    )
    ledger.record_qualification(
        te1,
        finding=_find("correctness", "concern", "src/a.py", 4, "q3", "unproven"),
        filed="concern",
        outcome="unverified",
        reason="why",
    )
    ledger.record_qualification(
        te2,
        finding=_find("join", "concern", "src/c.py", 9, "q4", None),
        filed="concern",
        outcome="unanchored",
        reason="",
    )
    ledger.record_qualification(
        te1,
        finding=_find("adequacy", "note", "src/b.py", 5, "q5", None),
        filed="note",
        outcome="note",
        reason="",
    )
    ledger.close()

    assert _rows(path, key1, key2) == [
        {
            "task_key": key1,
            "position": 1,
            "lens": "spec",
            "severity": "concern",
            "file": "src/a.py",
            "line": 3,
            "claim": "q1",
            "probe_verdict": "survived",
            "outcome": "qualified",
            "reason": "",
        },
        {
            "task_key": key1,
            "position": 2,
            "lens": "correctness",
            "severity": "concern",
            "file": "src/a.py",
            "line": 4,
            "claim": "q3",
            "probe_verdict": "unproven",
            "outcome": "unverified",
            "reason": "why",
        },
        {
            "task_key": key1,
            "position": 3,
            "lens": "adequacy",
            "severity": "note",
            "file": "src/b.py",
            "line": 5,
            "claim": "q5",
            "probe_verdict": None,
            "outcome": "note",
            "reason": "",
        },
        {
            "task_key": key2,
            "position": 1,
            "lens": "standards",
            "severity": "blocker",
            "file": "src/b.py",
            "line": 7,
            "claim": "q2",
            "probe_verdict": "killed",
            "outcome": "killed",
            "reason": "",
        },
        {
            "task_key": key2,
            "position": 2,
            "lens": "join",
            "severity": "concern",
            "file": "src/c.py",
            "line": 9,
            "claim": "q4",
            "probe_verdict": None,
            "outcome": "unanchored",
            "reason": "",
        },
    ]

    kinds1 = [f.kind for f in record.read(key1)]
    assert kinds1 == ["task_created", "qualification", "qualification", "qualification"]


def test_the_fold_rebuilds_each_tasks_qualifications_and_drops_one_task_alone(
    tmp_path, record
):
    source_path = tmp_path / "source.db"
    source = Ledger(source_path, record=record)
    te1 = _task(source, "TE-1")
    te2 = _task(source, "TE-2")
    key1, key2 = _key(source, te1), _key(source, te2)

    source.record_qualification(
        te1,
        finding=_find("spec", "blocker", "src/a.py", 3, "q1", "survived"),
        filed="concern",
        outcome="qualified",
        reason="",
    )
    source.record_qualification(
        te2,
        finding=_find("standards", "note", "src/b.py", 7, "q2", "killed"),
        filed="blocker",
        outcome="killed",
        reason="",
    )
    source.record_qualification(
        te1,
        finding=_find("correctness", "concern", "src/a.py", 4, "q3", "unproven"),
        filed="concern",
        outcome="unverified",
        reason="why",
    )

    fresh_path = tmp_path / "fresh.db"
    fresh = Ledger(fresh_path)
    other_repo = fresh.upsert_repo("o", "https://other", "/o", policy_sha="p")
    other_run = fresh.create_run(other_repo, base_sha="b" * 40)
    fresh.create_task(other_run, spec_id="OTHER", spec_sha="t" * 64, branch="o")

    fold(record, fresh)
    assert _rows(fresh_path) == _rows(source_path)

    fold(record, source)
    assert _rows(source_path) == _rows(fresh_path)

    fresh.fold_task(key2, [])
    remaining = _rows(fresh_path)
    assert remaining == [row for row in remaining if row["task_key"] == key1]
    assert len(remaining) == 2

    source.close()
    fresh.close()
