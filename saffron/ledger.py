"""The ledger — SQLite, one file, WAL, authoritative for state (DESIGN.md §4.1).

Five of the ten tables. The rest wait for an agent to have something to put in
them.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from saffron.gates.contract import Failure, GateResult

SCHEMA = """
CREATE TABLE IF NOT EXISTS repos (
    repo_id     INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    origin      TEXT NOT NULL UNIQUE,
    mirror_path TEXT NOT NULL,
    policy_sha  TEXT,
    enabled     INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS runs (
    run_id     INTEGER PRIMARY KEY,
    repo_id    INTEGER NOT NULL REFERENCES repos(repo_id),
    base_sha   TEXT NOT NULL,
    preflight  TEXT,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at   TEXT,
    status     TEXT
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id    INTEGER PRIMARY KEY,
    run_id     INTEGER NOT NULL REFERENCES runs(run_id),
    spec_id    TEXT NOT NULL,
    spec_sha   TEXT NOT NULL,
    state      TEXT NOT NULL,
    risk       TEXT NOT NULL DEFAULT 'standard',
    branch     TEXT,
    budget_usd REAL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Exactly one of attempt_id and run_id is set, and the null is the point: a
-- gate result belongs to an attempt, except the baseline suite, which runs
-- against a run's base_sha with no agent, no session and no cost (§4.1).
-- v0 has no attempts table; attempt_id holds a task_id until v1 backfills it.
CREATE TABLE IF NOT EXISTS gate_results (
    gate_result_id INTEGER PRIMARY KEY,
    attempt_id     INTEGER,
    run_id         INTEGER REFERENCES runs(run_id),
    gate           TEXT NOT NULL,
    status         TEXT NOT NULL,
    duration_ms    INTEGER,
    summary        TEXT,
    CHECK ((attempt_id IS NULL) <> (run_id IS NULL))
);

CREATE TABLE IF NOT EXISTS failures (
    failure_id     INTEGER PRIMARY KEY,
    gate_result_id INTEGER NOT NULL REFERENCES gate_results(gate_result_id),
    file           TEXT NOT NULL,
    code           TEXT NOT NULL,
    message        TEXT,
    line           INTEGER
);

CREATE INDEX IF NOT EXISTS failures_by_result ON failures(gate_result_id);
CREATE INDEX IF NOT EXISTS gate_results_by_run ON gate_results(run_id);
CREATE INDEX IF NOT EXISTS gate_results_by_attempt ON gate_results(attempt_id);
"""


class Ledger:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.executescript(SCHEMA)
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    def upsert_repo(
        self, name: str, origin: str, mirror_path: str, policy_sha: str
    ) -> int:
        self._db.execute(
            """INSERT INTO repos (name, origin, mirror_path, policy_sha)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(origin) DO UPDATE
                 SET name=excluded.name,
                     mirror_path=excluded.mirror_path,
                     policy_sha=excluded.policy_sha""",
            (name, str(origin), str(mirror_path), policy_sha),
        )
        self._db.commit()
        row = self._db.execute(
            "SELECT repo_id FROM repos WHERE origin = ?", (str(origin),)
        ).fetchone()
        return int(row["repo_id"])

    def create_run(self, repo_id: int, base_sha: str) -> int:
        cursor = self._db.execute(
            "INSERT INTO runs (repo_id, base_sha, status) VALUES (?, ?, 'RUNNING')",
            (repo_id, base_sha),
        )
        self._db.commit()
        return int(cursor.lastrowid)

    def finish_run(self, run_id: int, status: str) -> None:
        self._db.execute(
            "UPDATE runs SET status = ?, ended_at = datetime('now') WHERE run_id = ?",
            (status, run_id),
        )
        self._db.commit()

    def create_task(
        self,
        run_id: int,
        spec_id: str,
        spec_sha: str,
        branch: str,
        risk: str = "standard",
        budget_usd: float | None = None,
    ) -> int:
        cursor = self._db.execute(
            """INSERT INTO tasks (run_id, spec_id, spec_sha, state, risk, branch, budget_usd)
               VALUES (?, ?, ?, 'QUEUED', ?, ?, ?)""",
            (run_id, spec_id, spec_sha, risk, branch, budget_usd),
        )
        self._db.commit()
        return int(cursor.lastrowid)

    def set_task_state(self, task_id: int, state: str) -> None:
        self._db.execute(
            "UPDATE tasks SET state = ?, updated_at = datetime('now') WHERE task_id = ?",
            (state, task_id),
        )
        self._db.commit()

    def record_gate_result(
        self,
        result: GateResult,
        *,
        run_id: int | None = None,
        attempt_id: int | None = None,
    ) -> int:
        with self._db:
            cursor = self._db.execute(
                """INSERT INTO gate_results (attempt_id, run_id, gate, status, duration_ms, summary)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (attempt_id, run_id, result.gate, result.status, result.duration_ms,
                 result.summary),
            )
            gate_result_id = int(cursor.lastrowid)
            self._db.executemany(
                """INSERT INTO failures (gate_result_id, file, code, message, line)
                   VALUES (?, ?, ?, ?, ?)""",
                [
                    (gate_result_id, f.file, f.code, f.message, f.line)
                    for f in result.failures
                ],
            )
        return gate_result_id

    # baseline_results, task_results and queue_lines have no production caller
    # in v0: they are v1's supervisor's read side, and the tests exercise them.
    def baseline_results(self, run_id: int) -> list[GateResult]:
        return self._results("run_id", run_id)

    def task_results(self, task_id: int) -> list[GateResult]:
        return self._results("attempt_id", task_id)

    def queue_lines(self) -> list[sqlite3.Row]:
        return list(
            self._db.execute(
                """SELECT r.name AS repo, t.spec_id, t.state, t.risk, t.task_id,
                          t.branch, t.budget_usd
                   FROM tasks t
                   JOIN runs  ON runs.run_id = t.run_id
                   JOIN repos r ON r.repo_id = runs.repo_id
                   ORDER BY t.task_id"""
            )
        )

    def _results(self, column: str, value: int) -> list[GateResult]:
        rows = self._db.execute(
            f"SELECT * FROM gate_results WHERE {column} = ? ORDER BY gate_result_id",
            (value,),
        ).fetchall()
        results = []
        for row in rows:
            failures = self._db.execute(
                "SELECT * FROM failures WHERE gate_result_id = ? ORDER BY failure_id",
                (row["gate_result_id"],),
            ).fetchall()
            results.append(
                GateResult(
                    gate=row["gate"],
                    status=row["status"],
                    summary=row["summary"] or "",
                    duration_ms=row["duration_ms"],
                    failures=[
                        Failure(
                            file=f["file"],
                            code=f["code"],
                            message=f["message"] or "",
                            line=f["line"],
                        )
                        for f in failures
                    ],
                )
            )
        return results
