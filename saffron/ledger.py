"""The ledger — SQLite, one file, WAL, authoritative for state (DESIGN.md §4.1).

Eight of the nine tables. `decisions` waits for an operator to have something
to put in it.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from saffron.agents.findings import Finding
from saffron.gates.contract import Failure, GateResult
from saffron.record.contract import Fact, Record, new_task_key

# The closed set `set_run_preflight` writes; the `CHECK` below is built from it.
RUN_PREFLIGHT_OUTCOMES = ("PASSED", "FAILED")
_PREFLIGHT_IN = ", ".join(f"'{outcome}'" for outcome in RUN_PREFLIGHT_OUTCOMES)

SCHEMA = f"""
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
-- `status` is one of the five stop reasons — `DRAINED`, `BUDGET`, `UNTIL`,
-- `INFRASTRUCTURE`, `INCOMPLETE`, one per stop condition (§4.2.1) — and the
-- CHECK is satisfied by NULL, so a still-running batch's row is neither a
-- violation nor a sixth reason. No `concurrency`: §4.2.1 defers it until K has
-- a second position.
CREATE TABLE IF NOT EXISTS batches (
    batch_id      INTEGER PRIMARY KEY,
    started_at    TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at      TEXT,
    budget_usd    REAL NOT NULL,
    spent_usd_est REAL,
    until_ts      TEXT,
    status        TEXT CHECK (status IN ('DRAINED', 'BUDGET', 'UNTIL',
                                         'INFRASTRUCTURE', 'INCOMPLETE'))
);

-- A run's own preflight outcome, read off its baseline suite (CONTEXT.md §2).
-- NULL: the run never reached the baseline suite.
CREATE TABLE IF NOT EXISTS runs (
    run_id     INTEGER PRIMARY KEY,
    repo_id    INTEGER NOT NULL REFERENCES repos(repo_id),
    batch_id   INTEGER REFERENCES batches(batch_id),
    base_sha   TEXT NOT NULL,
    preflight  TEXT CHECK (preflight IN ({_PREFLIGHT_IN})),
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
    prompt_sha  TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    merged_head_sha TEXT
    -- The commit GitHub reported a merge at, written once by `reconcile`
    -- (backlog item 97). NULL until a merge for this row is observed.
    -- Below the column, not above it like `tool`. Measured 2026-09-19: on
    -- SQLite 3.51.0 a comment above the *last* column makes `DROP COLUMN`
    -- rebuild an unterminated table ("incomplete input"); 3.53.1 tolerates it.
);

-- `phase` is the state the task was in when the turn started, and `n` numbers
-- within it (§4.1). `close_attempt` now writes `model`, but `session.py`'s
-- own call site still passes `None`: the runner's result event does not
-- carry it, and only assistant messages do (agent_runner.py).
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
    -- What §5.4 makes the difference between a gate that ran and one that never
    -- did, and what `review.gate_summary` shows a critic. Null for a host-side
    -- core gate, which runs no tool (item 88).
    tool           TEXT,
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
    def __init__(self, path: Path, record: Record | None = None) -> None:
        self._record = record
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
        for column in (
            "pushed_sha",
            "pr_url",
            "policy_sha",
            "prompt_sha",
            "merged_head_sha",
            "record_key",
        ):
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
        # And on `gate_results`. Before `_add_gate_result_reference`, so the
        # rebuild below can copy the column rather than having to add it twice.
        gate_existing = {
            row["name"]
            for row in self._db.execute("PRAGMA table_info(gate_results)").fetchall()
        }
        if "tool" not in gate_existing:
            self._db.execute("ALTER TABLE gate_results ADD COLUMN tool TEXT")
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
        self._widen_batch_status()

    def _widen_batch_status(self) -> None:
        """`IF NOT EXISTS` leaves an existing table's CHECK as it was, so a
        ledger from before `INCOMPLETE` (item 70) refuses the first night to end
        that way. The same rebuild as `_add_gate_result_reference`, with the
        definition read out of `SCHEMA` so there is one copy of the CHECK."""
        sql = self._db.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'batches'"
        ).fetchone()["sql"]
        if "'INCOMPLETE'" in sql:
            return
        columns = SCHEMA.split("CREATE TABLE IF NOT EXISTS batches")[1].split(");")[0]
        # Off for the drop: `runs.batch_id` references `batches`.
        self._db.execute("PRAGMA foreign_keys=OFF")
        self._db.executescript(
            f"""BEGIN;
               CREATE TABLE batches_new {columns});
               INSERT INTO batches_new
                   SELECT batch_id, started_at, ended_at, budget_usd,
                          spent_usd_est, until_ts, status FROM batches;
               DROP TABLE batches;
               ALTER TABLE batches_new RENAME TO batches;
               COMMIT;"""
        )
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.commit()

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
                   tool           TEXT,
                   duration_ms    INTEGER,
                   summary        TEXT,
                   CHECK ((attempt_id IS NULL) <> (run_id IS NULL))
               );
               INSERT INTO gate_results_new
                   SELECT gate_result_id, attempt_id, run_id, gate, status,
                          tool, duration_ms, summary FROM gate_results;
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

    def _attempt_owner(self, attempt_id: int) -> int | None:
        """The task an attempt belongs to, for `_append`'s sake. An attempt the
        caller invented has no owner and files no fact."""
        row = self._db.execute(
            "SELECT task_id FROM attempts WHERE attempt_id = ?", (attempt_id,)
        ).fetchone()
        return row["task_id"] if row is not None else None

    def record_key(self, task_id: int) -> str | None:
        row = self._db.execute(
            "SELECT record_key FROM tasks WHERE task_id = ?", (task_id,)
        ).fetchone()
        return row["record_key"] if row else None

    def _append(self, task_id: int, kind: str, **payload: Any) -> None:
        """Every ledger write appends the fact it represents. A `None` record
        is every caller that predates the record, which must be unaffected."""
        if self._record is None:
            return
        row = self._db.execute(
            """SELECT t.record_key AS key, r.name AS repo, rn.batch_id AS batch
                 FROM tasks t
                 JOIN runs rn ON rn.run_id = t.run_id
                 JOIN repos r ON r.repo_id = rn.repo_id
                WHERE t.task_id = ?""",
            (task_id,),
        ).fetchone()
        # No row (unknown task_id) or no key (a pre-record task, NULL from
        # the additive ALTER) is a claim with nothing to file it under.
        if row is None or row["key"] is None:
            return
        fact = Fact(
            kind=kind,
            task_key=row["key"],
            at=datetime.now(UTC).isoformat(),
            repo=row["repo"],
            batch_key=str(row["batch"]) if row["batch"] is not None else None,
            payload=payload,
        )
        self._record.append(row["key"], fact)

    def upsert_repo(
        self, name: str, origin: str, mirror_path: str, policy_sha: str | None
    ) -> int:
        """`policy_sha` is nullable, as the column is: the fold has no fact
        that carries a repo's own declaration, only each task's. `COALESCE`
        on the conflict, so a fold into a surviving ledger leaves the value
        it cannot reproduce rather than clearing it."""
        self._db.execute(
            """INSERT INTO repos (name, origin, mirror_path, policy_sha)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(origin) DO UPDATE
                 SET name=excluded.name,
                     mirror_path=excluded.mirror_path,
                     policy_sha=COALESCE(excluded.policy_sha, repos.policy_sha)""",
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
        """`task_id`/`state`/`pr_url`/`pushed_sha` for every task in one repo,
        ungrouped — what `reconcile` (`saffron/reconcile.py`) needs to update
        one task at a time. `spec_id` and `prompt_sha` ride beside them for a
        caller that wants to name the task and what it ran under."""
        return list(
            self._db.execute(
                """SELECT t.task_id, t.spec_id, t.state, t.pr_url, t.pushed_sha,
                          t.prompt_sha
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
        the caller this serves (`task._resolve_stacked_on`) never reads the
        parent's spec file, so it has no current sha to filter on — the same
        "merging is permanent" reach `scheduler.build_queue`'s
        `merged_anywhere` already takes, for the same reason.

        Not a single-path artefact, and do not narrow it to one. The resolver
        moved to `saffron/task.py` and now serves the unattended path too,
        which *does* read spec files at scan time — but a parent whose spec
        text moved after its pull request opened still has a waiting row here
        and none at its current sha, and that row is the branch a child must
        stack on.

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

    def set_run_preflight(self, run_id: int, outcome: str) -> None:
        """Record a run's preflight outcome, one of `RUN_PREFLIGHT_OUTCOMES`.

        Refused here as well as by the `CHECK`: a ledger built before the
        `CHECK` existed keeps its old `runs` table."""
        if outcome not in RUN_PREFLIGHT_OUTCOMES:
            raise ValueError(
                f"preflight outcome {outcome!r} is not one of {RUN_PREFLIGHT_OUTCOMES}"
            )
        self._db.execute(
            "UPDATE runs SET preflight = ? WHERE run_id = ?", (outcome, run_id)
        )
        self._db.commit()

    def create_batch(self, budget_usd: float, until_ts: str | None = None) -> int:
        """Opens one night's window (§4.2.1). `status`, `ended_at` and
        `spent_usd_est` stay NULL until `close_batch` — none of the three is
        known yet, and NULL is what "not yet measured" means for a batch still
        going, the same distinction `ended_at` already draws on `runs`.

        `until_ts` goes through `datetime(?)` so it lands in the one spelling
        this module writes — `YYYY-MM-DD HH:MM:SS`, UTC, sortable as text. An
        ISO `T` string stored verbatim is neither: `'2026-09-06 23:00:00' <
        '2026-09-06T06:00:00'` is true, so an `ended_at` at 23:00 would sort
        before an `until_ts` of 06:30 the same night."""
        cursor = self._db.execute(
            "INSERT INTO batches (budget_usd, until_ts) VALUES (?, datetime(?))",
            (budget_usd, until_ts),
        )
        self._db.commit()
        return _inserted_id(cursor)

    def close_batch(self, batch_id: int, status: str) -> None:
        """`finish_run`'s shape, one table over: one UPDATE, status and end
        together, then commit. The spend is derived through `batch_spend`
        rather than repeated in SQL, so the close and the reader can never
        become two spellings of one sum that drift apart. A `status` outside
        §4.2.1's five stop reasons is refused by the CHECK on `batches` — this
        surfaces `sqlite3.IntegrityError` rather than swallowing it.

        `with self._db:` because of that raise: a failed UPDATE has already had
        sqlite3 issue an implicit BEGIN, and without the rollback the write
        lock is held until this connection next commits — every other process
        on the ledger gets `database is locked`. The read and the write share
        the transaction too, so a cost landing between them cannot be omitted
        from the figure stored."""
        with self._db:
            spent = self.batch_spend(batch_id)
            cursor = self._db.execute(
                """UPDATE batches
                      SET status = ?, ended_at = datetime('now'), spent_usd_est = ?
                    WHERE batch_id = ?""",
                (status, spent, batch_id),
            )
            # A batch_id matching nothing updates nothing and would close
            # cleanly, leaving the real row open — `open_attempt`'s guard,
            # for the same reason.
            if cursor.rowcount != 1:
                raise ValueError(f"no batch {batch_id} to close")

    def attach_run_to_batch(self, run_id: int, batch_id: int) -> None:
        """`create_run` accepts a `batch_id`, but the only call that mints a
        run (`run_one_cell`, in `saffron/cell/**`) passes none — this stamps
        it on after the row already exists, the shape `record_push` and
        `set_task_package` already use on `tasks`: the row exists, then the
        fact about it arrives.

        Raises on a run that does not exist. The two sides were asymmetric: an
        unknown `batch_id` hits the foreign key, an unknown `run_id` matched
        zero rows and returned cleanly — and a stamp that silently does not
        land is exactly what makes `batch_spend` under-count, the budget gate
        never fire, and the night overspend."""
        with self._db:
            cursor = self._db.execute(
                "UPDATE runs SET batch_id = ? WHERE run_id = ?",
                (batch_id, run_id),
            )
            if cursor.rowcount != 1:
                raise ValueError(f"no run {run_id} to attach to batch {batch_id}")

    def max_run_id(self) -> int:
        """The high-water mark on `runs.run_id`.

        Read immediately before a candidate runs, so a run minted by a call
        that then raised can be told apart from every run that already
        existed. `saffron/batch.py` needs it and may not reach past this
        class for it."""
        row = self._db.execute(
            "SELECT COALESCE(MAX(run_id), 0) AS high_water FROM runs"
        ).fetchone()
        return int(row["high_water"])

    def attach_orphan_runs_to_batch(self, batch_id: int, since_run_id: int) -> int:
        """Stamp any unattached run minted after `since_run_id`, returning how
        many. Answers "the runner raised — did it leave a billed run behind?"

        Scoped to `run_id > since_run_id` rather than every `batch_id IS NULL`
        row: a ledger accumulates plenty of those from `saffron cell` and
        `replay.py`, both of which pass no batch on purpose, and sweeping all
        of them would fold an unrelated past run's spend into tonight's
        budget."""
        with self._db:
            cursor = self._db.execute(
                """UPDATE runs SET batch_id = ?
                    WHERE run_id > ? AND batch_id IS NULL""",
                (batch_id, since_run_id),
            )
            return cursor.rowcount

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
        risk: str | None = None,
        budget_usd: float | None = None,
        policy_sha: str | None = None,
        prompt_sha: str | None = None,
    ) -> int:
        """`policy_sha` is the declaration the cell's gates ran under — read
        from the export at `base_sha` (§5.4). `prompt_sha` is
        `context.prompt_sha()`, the prompt tree the cell was given. Both
        default to `None`: every caller that predates the parameter
        (`saffron/replay.py` included) still records a task, just one that
        cannot say what it ran under.

        `risk=None` means the spec declared no tier; the column still defaults
        to `standard` because the ledger's consumers read it (item 170), but
        the fact carries the undeclared `None` rather than that default."""
        declared_risk = risk
        risk = risk if risk is not None else "standard"
        key = new_task_key() if self._record is not None else None
        cursor = self._db.execute(
            """INSERT INTO tasks
                   (run_id, spec_id, spec_sha, state, risk, branch, budget_usd,
                    policy_sha, prompt_sha, record_key)
               VALUES (?, ?, ?, 'QUEUED', ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                spec_id,
                spec_sha,
                risk,
                branch,
                budget_usd,
                policy_sha,
                prompt_sha,
                key,
            ),
        )
        self._db.commit()
        task_id = _inserted_id(cursor)
        self._append(
            task_id,
            "task_created",
            spec_id=spec_id,
            spec_sha=spec_sha,
            branch=branch,
            risk=declared_risk,
            budget_usd=budget_usd,
            policy_sha=policy_sha,
            prompt_sha=prompt_sha,
            **self._run_facts(run_id),
        )
        return task_id

    def _run_facts(self, run_id: int) -> dict[str, Any]:
        """What the fold needs to rebuild the `repos` and `runs` rows this task
        hangs from. A run has no record of its own — it is a fold over the
        tasks that name it (§5 of the record design, not `DESIGN.md` §5)."""
        if self._record is None:
            return {}
        row = self._db.execute(
            """SELECT rn.base_sha, r.origin, r.mirror_path
                 FROM runs rn JOIN repos r ON r.repo_id = rn.repo_id
                WHERE rn.run_id = ?""",
            (run_id,),
        ).fetchone()
        # ponytail: `mirror_path` puts the operator's home directory in a
        # trail §3 makes readable, and `repos.mirror_path` is `NOT NULL`.
        return {
            "base_sha": row["base_sha"],
            "origin": row["origin"],
            "mirror_path": row["mirror_path"],
        }

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
        self._append(task_id, "task_state", state=state)

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
        attempt_id = _inserted_id(cursor)
        if self._record is not None:
            opened = self._db.execute(
                "SELECT phase, n FROM attempts WHERE attempt_id = ?", (attempt_id,)
            ).fetchone()
            self._append(
                task_id,
                "attempt_opened",
                attempt_id=attempt_id,
                phase=opened["phase"],
                n=opened["n"],
            )
        return attempt_id

    def close_attempt(
        self,
        attempt_id: int,
        *,
        session_id: str | None,
        model: str | None = None,
        subtype: str,
        terminal_reason: str | None,
        num_turns: int,
        cost_usd_est: float,
    ) -> None:
        self._db.execute(
            """UPDATE attempts
                  SET ended_at = datetime('now'), session_id = ?, model = ?,
                      subtype = ?, terminal_reason = ?, num_turns = ?,
                      cost_usd_est = ?
                WHERE attempt_id = ?""",
            (
                session_id,
                model,
                subtype,
                terminal_reason,
                num_turns,
                cost_usd_est,
                attempt_id,
            ),
        )
        self._db.commit()
        if self._record is not None:
            owner = self._attempt_owner(attempt_id)
            if owner is not None:
                self._append(
                    owner,
                    "attempt_closed",
                    session_id=session_id,
                    model=model,
                    subtype=subtype,
                    terminal_reason=terminal_reason,
                    num_turns=num_turns,
                    cost_usd_est=cost_usd_est,
                )

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
        self._append(task_id, "task_push", pushed_sha=pushed_sha)

    def record_merged_head(self, task_id: int, head: str) -> None:
        """The commit a merged pull request's head actually was — called by
        `reconcile`, the only writer of `MERGED`, before that call moves the
        state (backlog item 97). A merged branch is gone by the next scan,
        so this is the one chance to keep it."""
        self._db.execute(
            "UPDATE tasks SET merged_head_sha = ?, updated_at = datetime('now') "
            "WHERE task_id = ?",
            (head, task_id),
        )
        self._db.commit()
        self._append(task_id, "task_merged_head", head=head)

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
        self._append(task_id, "task_policy", policy_sha=policy_sha)

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
        self._append(
            task_id,
            "task_package",
            state=state,
            branch=branch,
            pushed_sha=pushed_sha,
            pr_url=pr_url,
        )

    def record_findings(self, task_id: int, findings: Sequence[Finding]) -> list[int]:
        """Every finding the review produced, anchored or not, in the order the
        lenses reported them. Returns the ids in that same order — REBUT names
        a finding by its position in it (`review.anchored_blockers`)."""
        with self._db:
            ids = [
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
        # One fact per finding — a fold inserts `findings` one row at a time.
        for finding_id, f in zip(ids, findings, strict=True):
            self._append(
                task_id,
                "finding",
                finding_id=finding_id,
                lens=f.lens,
                severity=f.severity,
                file=f.file,
                line=f.line,
                claim=f.claim,
                anchored=f.anchored,
            )
        return ids

    def record_rebuttal(
        self, finding_id: int, *, verdict: str | None, rebuttal: str | None
    ) -> None:
        self._db.execute(
            "UPDATE findings SET verdict = ?, rebuttal = ? WHERE finding_id = ?",
            (verdict, rebuttal, finding_id),
        )
        self._db.commit()
        if self._record is not None:
            owner = self._db.execute(
                "SELECT task_id FROM findings WHERE finding_id = ?", (finding_id,)
            ).fetchone()
            if owner is not None:
                self._append(
                    owner["task_id"],
                    "rebuttal",
                    finding_id=finding_id,
                    verdict=verdict,
                    rebuttal=rebuttal,
                )

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
                """INSERT INTO gate_results
                       (attempt_id, run_id, gate, status, tool, duration_ms, summary)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    attempt_id,
                    run_id,
                    result.gate,
                    result.status,
                    result.tool,
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
        # A baseline result (`run_id` set) belongs to no task and has nothing
        # to append against; an attempt's result does.
        if attempt_id is not None and self._record is not None:
            owner = self._attempt_owner(attempt_id)
            if owner is not None:
                self._append(
                    owner,
                    "gate_result",
                    **result.model_dump(mode="json"),
                )
        return gate_result_id

    # The read side. The spec-loop driver calls task_results; the tests alone
    # read baseline_results and queue_lines.
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
                    tool=row["tool"],
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
