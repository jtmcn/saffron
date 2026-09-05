"""The ledger — SQLite, one file, WAL, authoritative for state (DESIGN.md §4.1).

Eight of the nine tables. `decisions` waits for an operator to have something
to put in it.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from pathlib import Path

from saffron.agents.findings import Finding
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

-- One night's window and how it ended (§4.2.1). Timestamps are TEXT, matching
-- every other timestamp this module writes (`datetime('now')`, sortable as
-- text) rather than inventing a second representation. `budget_usd` is known
-- at start and required; `ended_at` and the running spend estimate are unset
-- while the batch is still going, so both of those columns are nullable.
-- `status` is one of the four stop reasons — `DRAINED`, `BUDGET`, `UNTIL`,
-- `INFRASTRUCTURE`, one per stop condition (§4.2.1) — and the CHECK is
-- satisfied by NULL, so a still-running batch's row is neither a violation
-- nor a fifth reason. No `concurrency`: §4.2.1 defers it until K has a second
-- position.
CREATE TABLE IF NOT EXISTS batches (
    batch_id      INTEGER PRIMARY KEY,
    started_at    TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at      TEXT,
    budget_usd    REAL NOT NULL,
    spent_usd_est REAL,
    until_ts      TEXT,
    status        TEXT CHECK (status IN ('DRAINED', 'BUDGET', 'UNTIL', 'INFRASTRUCTURE'))
);

CREATE TABLE IF NOT EXISTS runs (
    run_id     INTEGER PRIMARY KEY,
    repo_id    INTEGER NOT NULL REFERENCES repos(repo_id),
    batch_id   INTEGER REFERENCES batches(batch_id),
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
    pushed_sha TEXT,
    pr_url     TEXT,
    spent_usd_est REAL NOT NULL DEFAULT 0.0,
    policy_sha TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- `phase` is the state the task was in when the turn started, and `n` numbers
-- within it (§4.1). `model` is declared and not written: the runner's result
-- event does not carry it, and only assistant messages do (agent_runner.py).
CREATE TABLE IF NOT EXISTS attempts (
    attempt_id      INTEGER PRIMARY KEY,
    task_id         INTEGER NOT NULL REFERENCES tasks(task_id),
    phase           TEXT NOT NULL,
    n               INTEGER NOT NULL,
    session_id      TEXT,
    model           TEXT,
    started_at      TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at        TEXT,
    subtype         TEXT,
    terminal_reason TEXT,
    num_turns       INTEGER,
    cost_usd_est    REAL
);

-- Exactly one of attempt_id and run_id is set, and the null is the point: a
-- gate result belongs to an attempt, except the baseline suite, which runs
-- against a run's base_sha with no agent, no session and no cost (§4.1).
CREATE TABLE IF NOT EXISTS gate_results (
    gate_result_id INTEGER PRIMARY KEY,
    attempt_id     INTEGER REFERENCES attempts(attempt_id),
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

-- `anchored` records whether the finding survived reconciliation against the
-- diff (§5.5); a dropped one is kept, because the drop rate is the signal that
-- a lens is badly prompted. `verdict` is the critic's confirm-or-withdraw,
-- `rebuttal` the implementer's argument, `adjudication` the operator's — three
-- judgements that must not collapse into one column (§4.1). Nothing produces
-- an adjudication yet; the morning queue is where it will come from (§6).
CREATE TABLE IF NOT EXISTS findings (
    finding_id   INTEGER PRIMARY KEY,
    task_id      INTEGER NOT NULL REFERENCES tasks(task_id),
    lens         TEXT NOT NULL,
    severity     TEXT NOT NULL,
    file         TEXT NOT NULL,
    line         INTEGER,
    claim        TEXT NOT NULL,
    anchored     INTEGER NOT NULL,
    verdict      TEXT,
    adjudication TEXT,
    rebuttal     TEXT
);

CREATE INDEX IF NOT EXISTS failures_by_result ON failures(gate_result_id);
CREATE INDEX IF NOT EXISTS gate_results_by_run ON gate_results(run_id);
CREATE INDEX IF NOT EXISTS gate_results_by_attempt ON gate_results(attempt_id);
CREATE INDEX IF NOT EXISTS attempts_by_task ON attempts(task_id);
CREATE INDEX IF NOT EXISTS findings_by_task ON findings(task_id);
"""


def _inserted_id(cursor: sqlite3.Cursor) -> int:
    """`lastrowid` is `int | None` on the sqlite3 type stubs.

    Measured, it is not None after a statement that inserted nothing — it
    reports the connection's *previous* insert, which is why `open_attempt`
    guards on `rowcount` instead (see there, and `tests/test_ledger.py`). So
    this branch is defensive rather than reachable; it exists because
    `int(None)` would raise TypeError, reading as a caller passing rubbish
    rather than as a ledger that recorded nothing.
    """
    row_id = cursor.lastrowid
    if row_id is None:
        raise ValueError("INSERT reported no rowid")
    return row_id


class Ledger:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.executescript(SCHEMA)
        # An existing ledger predates these columns, and `IF NOT EXISTS` does
        # not alter. Additive only — never a migration that can lose a row.
        existing = {
            row["name"]
            for row in self._db.execute("PRAGMA table_info(tasks)").fetchall()
        }
        for column in ("pushed_sha", "pr_url", "policy_sha"):
            if column not in existing:
                self._db.execute(f"ALTER TABLE tasks ADD COLUMN {column} TEXT")
        if "spent_usd_est" not in existing:
            self._db.execute(
                "ALTER TABLE tasks ADD COLUMN spent_usd_est REAL NOT NULL DEFAULT 0.0"
            )
        # Same trap, this time on `runs`: `batches` arriving in `SCHEMA` does
        # not retrofit `batch_id` onto a `runs` table that already exists.
        runs_existing = {
            row["name"]
            for row in self._db.execute("PRAGMA table_info(runs)").fetchall()
        }
        if "batch_id" not in runs_existing:
            self._db.execute(
                "ALTER TABLE runs ADD COLUMN batch_id INTEGER REFERENCES batches(batch_id)"
            )
        # The backfill the old schema comment promised. A ledger written before
        # `attempts` existed holds a *task_id* in `gate_results.attempt_id`, and
        # a new attempt's id starts at 1 in that same integer namespace — so
        # without this, task 1's v0.5 results reattach to whichever attempt
        # draws id 1. Nulling them is not available: the CHECK rejects a row
        # with neither id. One row per legacy value, carrying that value as its
        # own id, so the ids stay taken and nothing is lost or moved.
        self._db.execute(
            """INSERT INTO attempts (attempt_id, task_id, phase, n)
               SELECT DISTINCT g.attempt_id, g.attempt_id, 'v0.5', 1
                 FROM gate_results g
                WHERE g.attempt_id IS NOT NULL
                  AND EXISTS (SELECT 1 FROM tasks t WHERE t.task_id = g.attempt_id)
                  AND NOT EXISTS (SELECT 1 FROM attempts a
                                   WHERE a.attempt_id = g.attempt_id)"""
        )
        self._db.commit()
        self._add_gate_result_reference()

    def _add_gate_result_reference(self) -> None:
        """`IF NOT EXISTS` cannot add the reference to a table that already
        exists, and there is no ADD CONSTRAINT — so a v0.5 ledger kept the old
        convention perfectly representable while the test said otherwise. The
        rebuild is SQLite's documented 12-step, and it runs *after* the backfill
        above, so every row it copies already has an attempt to point at."""
        sql = self._db.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'gate_results'"
        ).fetchone()["sql"]
        if "REFERENCES attempts" in sql:
            return
        # Outside any transaction, and off for the drop: `failures` references
        # `gate_results`, which is gone between the DROP and the RENAME.
        self._db.execute("PRAGMA foreign_keys=OFF")
        self._db.executescript(
            """BEGIN;
               CREATE TABLE gate_results_new (
                   gate_result_id INTEGER PRIMARY KEY,
                   attempt_id     INTEGER REFERENCES attempts(attempt_id),
                   run_id         INTEGER REFERENCES runs(run_id),
                   gate           TEXT NOT NULL,
                   status         TEXT NOT NULL,
                   duration_ms    INTEGER,
                   summary        TEXT,
                   CHECK ((attempt_id IS NULL) <> (run_id IS NULL))
               );
               INSERT INTO gate_results_new
                   SELECT gate_result_id, attempt_id, run_id, gate, status,
                          duration_ms, summary FROM gate_results;
               DROP TABLE gate_results;
               ALTER TABLE gate_results_new RENAME TO gate_results;
               COMMIT;"""
        )
        self._db.execute("PRAGMA foreign_keys=ON")
        # Every row is copied, including one the backfill could not account for:
        # SQLite checks a reference when a row is written, not when it is
        # rebuilt, and refusing to open a ledger over data that is already
        # written loses more than it protects. The constraint is about what can
        # be recorded from here on, which is what made the collision possible.
        # The DROP took the table's indexes with it; every statement is
        # `IF NOT EXISTS`, so this recreates those and touches nothing else.
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

    def resolve_repo_id(self, origin: str) -> int | None:
        """The scheduler's read of `upsert_repo` — a repo that has never run
        has no row, and a scan must be able to ask that without creating one
        just to answer it (`upsert_repo` always leaves a row behind, which is
        right for preflight and wrong for a read)."""
        row = self._db.execute(
            "SELECT repo_id FROM repos WHERE origin = ?", (str(origin),)
        ).fetchone()
        return int(row["repo_id"]) if row is not None else None

    def tasks_by_spec(self, repo_id: int) -> dict[tuple[str, str], list[sqlite3.Row]]:
        """Every task this repo has ever run, grouped by `(spec_id, spec_sha)`
        and ordered oldest first — the shape `scheduler.build_queue` filters
        against, in one query rather than one per spec. Spans every run the
        repo has had, not just the latest, because a `spec_sha` a task was
        recorded against on an earlier night is still the one a re-queue or a
        done-state check must find.

        Every task, not the newest one per key: `cell/session.py` mints a run
        and a task on each invocation without consulting what exists, so one
        key routinely holds many. This repo's own ledger carries ten tasks at
        `SA-0013`/`ce08b1eb`, mixing `READY_FOR_REVIEW` with three `ORPHANED`.
        §4.2.1 asks whether *a* task at this `spec_sha` is done with the spec,
        and folding to the highest `task_id` answers a different question —
        one an `ORPHANED` corpse from a later killed run silently wins.
        """
        rows = self._db.execute(
            """SELECT t.task_id, t.spec_id, t.spec_sha, t.state
                 FROM tasks t
                 JOIN runs r ON r.run_id = t.run_id
                WHERE r.repo_id = ?
                ORDER BY t.task_id""",
            (repo_id,),
        ).fetchall()
        grouped: dict[tuple[str, str], list[sqlite3.Row]] = {}
        for row in rows:
            grouped.setdefault((row["spec_id"], row["spec_sha"]), []).append(row)
        return grouped

    def tasks_by_repo(self, repo_id: int) -> list[sqlite3.Row]:
        """`task_id`/`state`/`pr_url` for every task in one repo, ungrouped —
        what `reconcile` (`saffron/reconcile.py`) needs to update one task at
        a time."""
        return list(
            self._db.execute(
                """SELECT t.task_id, t.state, t.pr_url
                     FROM tasks t
                     JOIN runs r ON r.run_id = t.run_id
                    WHERE r.repo_id = ?
                    ORDER BY t.task_id""",
                (repo_id,),
            )
        )

    def tasks_by_spec_id(self, repo_id: int, spec_id: str) -> list[sqlite3.Row]:
        """Every task this repo has ever run for one `spec_id`, across every
        `spec_sha` it has carried, oldest first — `branch` and `pushed_sha`
        beside the columns `tasks_by_spec` already carries (`SA-0026`).

        Spans every `spec_sha`, not just the one the spec has on disk today:
        the caller this serves (`cli._resolve_stacked_on`) is the attended
        `saffron cell` path, which never exports the parent's spec file and
        so has no current sha to filter on — the same "merging is permanent"
        reach `scheduler.build_queue`'s `merged_anywhere` already takes, for
        the same reason.

        Every row, not the newest one per id: this repo's own ledger holds
        ten tasks at one `spec_id`/`spec_sha`, mixing `READY_FOR_REVIEW` with
        three `ORPHANED` (`SA-0013`), so "the parent's task" is a row the
        caller has to choose deliberately among several, not the only one
        there is.
        """
        return list(
            self._db.execute(
                """SELECT t.task_id, t.spec_id, t.spec_sha, t.state,
                          t.branch, t.pushed_sha
                     FROM tasks t
                     JOIN runs r ON r.run_id = t.run_id
                    WHERE r.repo_id = ? AND t.spec_id = ?
                    ORDER BY t.task_id""",
                (repo_id, spec_id),
            )
        )

    def create_run(
        self, repo_id: int, base_sha: str, batch_id: int | None = None
    ) -> int:
        """`batch_id` defaults to `None` — a run created outside a batch (or
        by `saffron/replay.py`, which calls this with no `batch_id` at all)
        leaves the column NULL rather than inventing a batch that did not
        happen. Nothing passes a real value yet; the batch loop that will is
        `SA-0050`."""
        cursor = self._db.execute(
            """INSERT INTO runs (repo_id, base_sha, batch_id, status)
               VALUES (?, ?, ?, 'RUNNING')""",
            (repo_id, base_sha, batch_id),
        )
        self._db.commit()
        return _inserted_id(cursor)

    def finish_run(self, run_id: int, status: str) -> None:
        self._db.execute(
            "UPDATE runs SET status = ?, ended_at = datetime('now') WHERE run_id = ?",
            (status, run_id),
        )
        self._db.commit()

    def create_batch(self, budget_usd: float, until_ts: str | None = None) -> int:
        """Opens one night's window (§4.2.1). `status`, `ended_at` and
        `spent_usd_est` stay NULL until `close_batch` — none of the three is
        known yet, and NULL is what "not yet measured" means for a batch still
        going, the same distinction `ended_at` already draws on `runs`."""
        cursor = self._db.execute(
            "INSERT INTO batches (budget_usd, until_ts) VALUES (?, ?)",
            (budget_usd, until_ts),
        )
        self._db.commit()
        return _inserted_id(cursor)

    def close_batch(self, batch_id: int, status: str) -> None:
        """`finish_run`'s shape, one table over: one UPDATE, status and end
        together, then commit. The spend is derived through `batch_spend`
        rather than repeated in SQL, so the close and the reader can never
        become two spellings of one sum that drift apart. A `status` outside
        §4.2.1's four stop reasons is refused by the CHECK on `batches` — this
        surfaces `sqlite3.IntegrityError` rather than swallowing it."""
        spent = self.batch_spend(batch_id)
        self._db.execute(
            """UPDATE batches
                  SET status = ?, ended_at = datetime('now'), spent_usd_est = ?
                WHERE batch_id = ?""",
            (status, spent, batch_id),
        )
        self._db.commit()

    def attach_run_to_batch(self, run_id: int, batch_id: int) -> None:
        """`create_run` accepts a `batch_id`, but the only call that mints a
        run (`run_one_cell`, in `saffron/cell/**`) passes none — this stamps
        it on after the row already exists, the shape `record_push` and
        `set_task_package` already use on `tasks`: the row exists, then the
        fact about it arrives."""
        self._db.execute(
            "UPDATE runs SET batch_id = ? WHERE run_id = ?",
            (batch_id, run_id),
        )
        self._db.commit()

    def batch_spend(self, batch_id: int) -> float:
        """The same join `close_batch` derives through:
        `batches` -> `runs.batch_id` -> `tasks.run_id` -> `attempts.cost_usd_est`,
        summed and coalesced to 0.0 — never read off `tasks.spent_usd_est`,
        which is only as fresh as the last `set_task_state` and would silently
        omit the turn that just closed (`task_spend`'s docstring, one level
        down)."""
        row = self._db.execute(
            """SELECT COALESCE(SUM(a.cost_usd_est), 0.0) AS spent
                 FROM attempts a
                 JOIN tasks t ON t.task_id = a.task_id
                 JOIN runs r ON r.run_id = t.run_id
                WHERE r.batch_id = ?""",
            (batch_id,),
        ).fetchone()
        return float(row["spent"])

    def batch_runs(self, batch_id: int) -> list[sqlite3.Row]:
        """Every run a batch is made of, so a night can be walked from its own
        row. The column already round-trips through `create_run`, but no
        method had projected it until now, and `queue_lines` does not."""
        return list(
            self._db.execute(
                "SELECT * FROM runs WHERE batch_id = ? ORDER BY run_id",
                (batch_id,),
            )
        )

    def create_task(
        self,
        run_id: int,
        spec_id: str,
        spec_sha: str,
        branch: str,
        risk: str = "standard",
        budget_usd: float | None = None,
        policy_sha: str | None = None,
    ) -> int:
        """`policy_sha` is the declaration the cell's gates ran under — read
        from the export at `base_sha` (§5.4) — and defaults to `None`: every
        caller that predates this parameter (`saffron/replay.py` included)
        still records a task, just one that cannot say what it ran under."""
        cursor = self._db.execute(
            """INSERT INTO tasks
                   (run_id, spec_id, spec_sha, state, risk, branch, budget_usd, policy_sha)
               VALUES (?, ?, ?, 'QUEUED', ?, ?, ?, ?)""",
            (run_id, spec_id, spec_sha, risk, branch, budget_usd, policy_sha),
        )
        self._db.commit()
        return _inserted_id(cursor)

    def set_task_state(self, task_id: int, state: str) -> None:
        """Also rolls the task's spend up from its attempts. Derived rather than
        passed, so the figure can never disagree with the rows it is made of —
        and every terminal path already calls this, so none can forget it."""
        self._db.execute(
            """UPDATE tasks
                  SET state = ?, updated_at = datetime('now'),
                      spent_usd_est = (SELECT COALESCE(SUM(cost_usd_est), 0.0)
                                         FROM attempts WHERE task_id = ?)
                WHERE task_id = ?""",
            (state, task_id, task_id),
        )
        self._db.commit()

    def open_attempt(self, task_id: int, phase: str | None = None) -> int:
        """One agent turn. The phase defaults to the state the task is in — the
        caller sets that at each phase boundary and would otherwise have to
        track it again at every turn (§4.1). Only `replay`, which has no agent
        and no phase to be in, passes one."""
        cursor = self._db.execute(
            """INSERT INTO attempts (task_id, phase, n)
               SELECT ?, COALESCE(?, t.state),
                      1 + COALESCE((SELECT MAX(a.n) FROM attempts a
                                     WHERE a.task_id = t.task_id
                                       AND a.phase = COALESCE(?, t.state)), 0)
                 FROM tasks t WHERE t.task_id = ?""",
            (task_id, phase, phase, task_id),
        )
        # A task_id matching nothing selects nothing, and `lastrowid` still
        # reports the connection's previous insert — an id that exists, belongs
        # to another attempt, and satisfies the foreign key.
        if cursor.rowcount != 1:
            raise ValueError(f"no task {task_id} to open an attempt against")
        self._db.commit()
        return _inserted_id(cursor)

    def close_attempt(
        self,
        attempt_id: int,
        *,
        session_id: str | None,
        subtype: str,
        terminal_reason: str | None,
        num_turns: int,
        cost_usd_est: float,
    ) -> None:
        self._db.execute(
            """UPDATE attempts
                  SET ended_at = datetime('now'), session_id = ?, subtype = ?,
                      terminal_reason = ?, num_turns = ?, cost_usd_est = ?
                WHERE attempt_id = ?""",
            (session_id, subtype, terminal_reason, num_turns, cost_usd_est, attempt_id),
        )
        self._db.commit()

    def task_spend(self, task_id: int) -> float:
        """What the task's attempts add up to — a caller whose own tally lost a
        frame reads it back rather than reporting the gap. Summed, not read off
        `tasks.spent_usd_est`, which is only as fresh as the last
        `set_task_state` and would silently omit the turn that just closed."""
        row = self._db.execute(
            "SELECT COALESCE(SUM(cost_usd_est), 0.0) AS spent"
            "  FROM attempts WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        return float(row["spent"])

    def attempts(self, task_id: int) -> list[sqlite3.Row]:
        return list(
            self._db.execute(
                "SELECT * FROM attempts WHERE task_id = ? ORDER BY attempt_id",
                (task_id,),
            )
        )

    def record_push(self, task_id: int, pushed_sha: str) -> None:
        """The push already happened, so it is recorded before the pull request
        is opened: a `gh` that fails otherwise leaves a pushed branch the
        ledger cannot name (§5.7)."""
        self._db.execute(
            "UPDATE tasks SET pushed_sha = ?, updated_at = datetime('now') "
            "WHERE task_id = ?",
            (pushed_sha, task_id),
        )
        self._db.commit()

    def task_policy_sha(self, task_id: int) -> str | None:
        """What this task is currently on record as having run under — the
        base_sha declaration `create_task` recorded, or whatever PACKAGE last
        wrote over it with `record_policy`. PACKAGE reads this back to decide
        whether a re-verification ran under a different declaration."""
        row = self._db.execute(
            "SELECT policy_sha FROM tasks WHERE task_id = ?", (task_id,)
        ).fetchone()
        return row["policy_sha"] if row is not None else None

    def record_policy(self, task_id: int, policy_sha: str) -> None:
        """PACKAGE's own write-back (§5.7, backlog item 16): issued only when
        re-verification ran under a declaration different from the one this
        task is on record for — never unconditionally, which would satisfy
        the letter of "rewrites when it differs" while doing it every time."""
        self._db.execute(
            "UPDATE tasks SET policy_sha = ?, updated_at = datetime('now') "
            "WHERE task_id = ?",
            (policy_sha, task_id),
        )
        self._db.commit()

    def set_task_package(
        self,
        task_id: int,
        state: str,
        branch: str,
        pushed_sha: str,
        pr_url: str,
    ) -> None:
        """PACKAGE's own write-back, after `finish_run` (§5.7). The state it
        sets — `READY_FOR_REVIEW`, or `MERGE_FAILED` on the four paths where
        the push or the pull request could not be made — is not the last word
        on the task: `reconcile` (`saffron/reconcile.py`) revises a
        `READY_FOR_REVIEW` row once GitHub records what the operator decided.
        `MERGE_FAILED` is not revised — it is not in `PR_PENDING_STATES`,
        because it reaches the operator with no pull request to ask about."""
        self._db.execute(
            """UPDATE tasks
                  SET state = ?, branch = ?, pushed_sha = ?, pr_url = ?,
                      updated_at = datetime('now')
                WHERE task_id = ?""",
            (state, branch, pushed_sha, pr_url, task_id),
        )
        self._db.commit()

    def record_findings(self, task_id: int, findings: Sequence[Finding]) -> list[int]:
        """Every finding the review produced, anchored or not, in the order the
        lenses reported them. Returns the ids in that same order — REBUT names
        a finding by its position in it (`review.anchored_blockers`)."""
        with self._db:
            return [
                _inserted_id(
                    self._db.execute(
                        """INSERT INTO findings
                               (task_id, lens, severity, file, line, claim, anchored)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            task_id,
                            f.lens,
                            f.severity,
                            f.file,
                            f.line,
                            f.claim,
                            int(f.anchored),
                        ),
                    )
                )
                for f in findings
            ]

    def record_rebuttal(
        self, finding_id: int, *, verdict: str | None, rebuttal: str | None
    ) -> None:
        self._db.execute(
            "UPDATE findings SET verdict = ?, rebuttal = ? WHERE finding_id = ?",
            (verdict, rebuttal, finding_id),
        )
        self._db.commit()

    def findings(self, task_id: int) -> list[sqlite3.Row]:
        return list(
            self._db.execute(
                "SELECT * FROM findings WHERE task_id = ? ORDER BY finding_id",
                (task_id,),
            )
        )

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
                (
                    attempt_id,
                    run_id,
                    result.gate,
                    result.status,
                    result.duration_ms,
                    result.summary,
                ),
            )
            gate_result_id = _inserted_id(cursor)
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

    def attempt_results(self, attempt_id: int) -> list[GateResult]:
        return self._results("attempt_id", attempt_id)

    def task_results(self, task_id: int) -> list[GateResult]:
        rows = self._db.execute(
            "SELECT attempt_id FROM attempts WHERE task_id = ? ORDER BY attempt_id",
            (task_id,),
        ).fetchall()
        return [r for row in rows for r in self._results("attempt_id", row[0])]

    def queue_lines(self) -> list[sqlite3.Row]:
        return list(
            self._db.execute(
                """SELECT r.name AS repo, t.spec_id, t.state, t.risk, t.task_id,
                          t.branch, t.budget_usd, t.pushed_sha, t.pr_url,
                          t.spent_usd_est
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
