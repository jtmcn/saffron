"""Record <- ledger. Reads a stored `Ledger`'s rows directly, read-only.
Appends the facts a live run would have written. A fold then gives back §4's
tasks, attempts, gate results, findings and six key-filed tables (backlog item
170, §7).

§ numbers here are `docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md`'s,
not `DESIGN.md`'s.

Sixteen kinds. `task_created`, `attempt_opened`, `attempt_closed`,
`gate_result`, `finding`, `rebuttal`, `task_merged_head`, `task_package`,
`task_push`, `task_state`, `stack_layer`, `end_review`, `qualification`,
`spec_review`, `spec_text` and `stack_finish`. No `task_policy` fact is
written, since `policy_sha` rides on `task_created` as stored. The six key-filed tables (`stack_layers`,
`end_reviews`, `qualifications`, `spec_reviews`, `spec_texts` and
`stack_finishes`) are written after each task's own `task_state` fact.

Never a `Ledger`. Its open adds missing columns, so it would write the source.

`migrate_and_push` is the orchestration the `saffron migrate` command runs.
One `RefsRecord` per repo row is fetched from its own `origin` before
anything is written. Then each repo's tasks are migrated and pushed one ref
at a time.
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from saffron.gates.baseline import subtract_baseline, suite_drift
from saffron.gates.contract import Failure, GateResult
from saffron.gates.suite import aborted_gates
from saffron.record.contract import Fact, Record, RecordError, StaleWriter
from saffron.record.refs import RefsRecord

_Maker = Callable[[str, str, dict[str, Any]], Fact]


@dataclass
class Migration:
    """What one migration did. `migrated` lists task keys in source order.
    A key the record now holds the full fact list for is one, a key with
    nothing left to add included. `refused` pairs a key that disagreed with
    what the record already held against the reason, and costs the other
    keys nothing."""

    migrated: list[str] = field(default_factory=list)
    refused: list[tuple[str, str]] = field(default_factory=list)


_TASKS = """
    SELECT t.*, r.started_at AS run_started_at, r.base_sha AS run_base_sha,
           r.batch_id AS run_batch_id, r.repo_id AS run_repo_id, rp.name AS repo_name,
           rp.origin AS repo_origin, rp.mirror_path AS repo_mirror_path
      FROM tasks t
      JOIN runs r ON r.run_id = t.run_id
      JOIN repos rp ON rp.repo_id = r.repo_id
     ORDER BY t.task_id
"""


def _fact_time(value: str) -> str:
    """A ledger time is UTC text with no offset (`saffron.ledger._ledger_time`'s
    own shape). Read with that assumption, then written back as the offset form
    every live fact carries."""
    return datetime.fromisoformat(value).replace(tzinfo=UTC).isoformat()


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    """The source's column names for `table`, read per table because an old
    source can lack one."""
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def migrate(source: Path, record: Record, *, repo_id: int | None = None) -> Migration:
    """Append the facts `source`'s stored tasks are owed, task by task in
    `task_id` order. Opens `source` read-only, so its bytes are the same
    after this returns. A path that does not exist raises
    `sqlite3.OperationalError` and creates no file.

    `repo_id` is `None` for every caller but `migrate_and_push`: given one,
    only that repo's tasks are migrated, everything else skipped."""
    conn = sqlite3.connect(f"{source.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        has_head_count = "failures_at_head" in _columns(conn, "gate_results")
        has_earned_risk = "earned_risk" in _columns(conn, "attempts")
        result = Migration()
        for task in conn.execute(_TASKS).fetchall():
            if repo_id is not None and task["run_repo_id"] != repo_id:
                continue
            key = task["record_key"]
            refusal = _refusal_reason(conn, task, has_head_count)
            if refusal is not None:
                result.refused.append((key, refusal))
                continue
            facts = _facts_for_task(conn, task, has_head_count, has_earned_risk)
            held = record.read(key)
            if held != facts[: len(held)]:
                result.refused.append(
                    (key, f"the record holds {len(held)} fact(s) that disagree")
                )
                continue
            for fact in facts[len(held) :]:
                record.append(key, fact)
            result.migrated.append(key)
        return result
    finally:
        conn.close()


def _result_rows(
    conn: sqlite3.Connection, column: str, value: int
) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            f"SELECT * FROM gate_results WHERE {column} = ? ORDER BY gate_result_id",
            (value,),
        )
    )


def _failure_rows(conn: sqlite3.Connection, gate_result_id: int) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            "SELECT * FROM failures WHERE gate_result_id = ? ORDER BY failure_id",
            (gate_result_id,),
        )
    )


def _comparison_result(row: sqlite3.Row, failure_rows: list[sqlite3.Row]) -> GateResult:
    """A `GateResult` built from stored rows, for `aborted_gates`,
    `suite_drift` and `subtract_baseline` only. It is never written to a
    fact. A null `message` reads as `""`, since `Failure.message` is a `str`.
    The fact payload keeps the stored null instead."""
    return GateResult(
        gate=row["gate"],
        status=row["status"],
        tool=row["tool"],
        failures=[
            Failure(
                file=f["file"],
                line=f["line"],
                code=f["code"],
                message=f["message"] or "",
            )
            for f in failure_rows
        ],
    )


def _baseline_comparison(conn: sqlite3.Connection, run_id: int) -> list[GateResult]:
    """The run's own stored baseline, as comparison-only `GateResult`s."""
    return [
        _comparison_result(row, _failure_rows(conn, row["gate_result_id"]))
        for row in _result_rows(conn, "run_id", run_id)
    ]


def _doubled_gate(rows: Iterable[sqlite3.Row]) -> str | None:
    """The first gate name stored more than once among `rows`, or `None`."""
    counts = Counter(row["gate"] for row in rows)
    return next((gate for gate, n in counts.items() if n > 1), None)


def _refusal_reason(
    conn: sqlite3.Connection, task: sqlite3.Row, has_head_count: bool
) -> str | None:
    """A doubled baseline or a doubled attempt makes the subtraction below
    ambiguous, but only where that ambiguity can bite: some attempt-scoped
    result has no stored head count to fall back on.
    A run-scoped baseline row is never one of "its own results". It never
    carries a count of its own, so a doubled baseline whose task stores
    every result counted still migrates."""
    baseline_rows = _result_rows(conn, "run_id", task["run_id"])
    doubled_baseline = _doubled_gate(baseline_rows)

    any_null_count = False
    doubled_attempt: tuple[str, sqlite3.Row] | None = None
    for attempt in conn.execute(
        "SELECT * FROM attempts WHERE task_id = ? ORDER BY attempt_id",
        (task["task_id"],),
    ):
        rows = _result_rows(conn, "attempt_id", attempt["attempt_id"])
        if doubled_attempt is None:
            gate = _doubled_gate(rows)
            if gate is not None:
                doubled_attempt = (gate, attempt)
        for row in rows:
            if not has_head_count or row["failures_at_head"] is None:
                any_null_count = True

    if not any_null_count:
        return None
    if doubled_baseline is not None:
        return f"gate {doubled_baseline!r} stored twice in the run's baseline"
    if doubled_attempt is not None:
        gate, attempt = doubled_attempt
        return (
            f"gate {gate!r} stored twice on attempt {attempt['phase']} {attempt['n']}"
        )
    return None


def _failure_payload(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "file": row["file"],
        "line": row["line"],
        "code": row["code"],
        "message": row["message"],
    }


def _gate_result_facts(
    conn: sqlite3.Connection,
    attempt: sqlite3.Row,
    baseline: list[GateResult],
    at: str,
    one: _Maker,
    *,
    has_head_count: bool,
    has_earned_risk: bool,
) -> list[Fact]:
    """One `gate_result` fact per `gate_results` row stored against this
    attempt, carrying the keys the fold's `gate_result` branch reads. A row
    whose `failures_at_head` is already stored (post `SA-0220`) is copied
    through unchanged. Otherwise its stored failures are the full head set,
    so the count becomes how many were stored. The kept failures are then
    what `subtract_baseline` leaves against the run's baseline, unless this
    attempt's own suite `error`ed or drifted against it. Either one keeps
    every stored failure whole instead (`DESIGN.md` §4.1 and §5.4)."""
    rows = _result_rows(conn, "attempt_id", attempt["attempt_id"])
    if not rows:
        return []
    failure_rows_by_result = [
        _failure_rows(conn, row["gate_result_id"]) for row in rows
    ]
    comparisons = [
        _comparison_result(row, failures)
        for row, failures in zip(rows, failure_rows_by_result, strict=True)
    ]
    # In that order: an aborted suite is never also checked for drift,
    # though either alone is enough to distrust the subtraction.
    aborted = aborted_gates(comparisons)
    keep_whole = bool(aborted) or bool(suite_drift(comparisons, baseline))
    earned_risk = attempt["earned_risk"] if has_earned_risk else None

    facts = []
    for row, failure_rows, comparison in zip(
        rows, failure_rows_by_result, comparisons, strict=True
    ):
        stored_count = row["failures_at_head"] if has_head_count else None
        if stored_count is not None:
            failures = [_failure_payload(f) for f in failure_rows]
            count = stored_count
        elif keep_whole:
            failures = [_failure_payload(f) for f in failure_rows]
            count = len(failure_rows)
        else:
            kept = {id(nf.failure) for nf in subtract_baseline([comparison], baseline)}
            failures = [
                _failure_payload(f)
                for f, comp_failure in zip(
                    failure_rows, comparison.failures, strict=True
                )
                if id(comp_failure) in kept
            ]
            count = len(failure_rows)
        facts.append(
            one(
                "gate_result",
                at,
                {
                    "gate": row["gate"],
                    "status": row["status"],
                    "tool": row["tool"],
                    "duration_ms": row["duration_ms"],
                    "summary": row["summary"],
                    "failures": failures,
                    "failures_at_head": count,
                    "earned_risk": earned_risk,
                    "phase": attempt["phase"],
                    "n": attempt["n"],
                },
            )
        )
    return facts


def _facts_for_task(
    conn: sqlite3.Connection,
    task: sqlite3.Row,
    has_head_count: bool,
    has_earned_risk: bool,
) -> list[Fact]:
    key = task["record_key"]
    repo = task["repo_name"]
    batch_key = str(task["run_batch_id"]) if task["run_batch_id"] is not None else None

    def one(kind: str, at: str, payload: dict[str, Any]) -> Fact:
        return Fact(
            kind=kind,
            task_key=key,
            at=_fact_time(at),
            repo=repo,
            batch_key=batch_key,
            payload=payload,
        )

    facts = [
        one(
            "task_created",
            task["run_started_at"],
            {
                "spec_id": task["spec_id"],
                "spec_sha": task["spec_sha"],
                "branch": task["branch"],
                "risk": None if task["risk"] == "standard" else task["risk"],
                "budget_usd": task["budget_usd"],
                "policy_sha": task["policy_sha"],
                "prompt_sha": task["prompt_sha"],
                "base_sha": task["run_base_sha"],
                "origin": task["repo_origin"],
                "mirror_path": task["repo_mirror_path"],
            },
        )
    ]
    facts.extend(_attempt_facts(conn, task, one, has_head_count, has_earned_risk))
    facts.extend(_finding_facts(conn, task, one))
    facts.extend(_outcome_facts(task, one))
    facts.extend(_key_filed_facts(conn, task, one))
    return facts


def _attempt_facts(
    conn: sqlite3.Connection,
    task: sqlite3.Row,
    one: _Maker,
    has_head_count: bool,
    has_earned_risk: bool,
) -> list[Fact]:
    """`attempt_opened`, an optional `attempt_closed`, then that attempt's
    own `gate_result` facts. They stay contiguous, before the next
    attempt's own facts start. A reader walking the list backward from any
    one of them meets its own attempt's open or close fact first."""
    facts = []
    baseline = _baseline_comparison(conn, task["run_id"])
    for attempt in conn.execute(
        "SELECT * FROM attempts WHERE task_id = ? ORDER BY attempt_id",
        (task["task_id"],),
    ):
        facts.append(
            one(
                "attempt_opened",
                attempt["started_at"],
                {"phase": attempt["phase"], "n": attempt["n"]},
            )
        )
        closed_at = attempt["ended_at"]
        if closed_at is not None:
            facts.append(
                one(
                    "attempt_closed",
                    closed_at,
                    {
                        "phase": attempt["phase"],
                        "n": attempt["n"],
                        "session_id": attempt["session_id"],
                        "model": attempt["model"],
                        "subtype": attempt["subtype"],
                        "terminal_reason": attempt["terminal_reason"],
                        "num_turns": attempt["num_turns"],
                        "cost_usd_est": attempt["cost_usd_est"],
                        "cost_floor_usd_est": attempt["cost_floor_usd_est"],
                    },
                )
            )
        at = closed_at if closed_at is not None else attempt["started_at"]
        facts.extend(
            _gate_result_facts(
                conn,
                attempt,
                baseline,
                at,
                one,
                has_head_count=has_head_count,
                has_earned_risk=has_earned_risk,
            )
        )
    return facts


def _finding_facts(
    conn: sqlite3.Connection, task: sqlite3.Row, one: _Maker
) -> list[Fact]:
    facts = []
    at = task["updated_at"]
    rows = conn.execute(
        "SELECT * FROM findings WHERE task_id = ? ORDER BY finding_id",
        (task["task_id"],),
    ).fetchall()
    for position, finding in enumerate(rows, start=1):
        facts.append(
            one(
                "finding",
                at,
                {
                    "position": position,
                    "lens": finding["lens"],
                    "severity": finding["severity"],
                    "file": finding["file"],
                    "line": finding["line"],
                    "claim": finding["claim"],
                    "anchored": bool(finding["anchored"]),
                },
            )
        )
        if finding["verdict"] is not None or finding["rebuttal"] is not None:
            facts.append(
                one(
                    "rebuttal",
                    at,
                    {
                        "position": position,
                        "verdict": finding["verdict"],
                        "rebuttal": finding["rebuttal"],
                    },
                )
            )
    return facts


_PACKAGED = frozenset({"READY_FOR_REVIEW", "MERGE_FAILED", "EXHAUSTED"})


def _outcome_facts(task: sqlite3.Row, one: _Maker) -> list[Fact]:
    """`task_merged_head`, then `task_package`/`task_push`, then `task_state`
    last, every one at `updated_at`. `task_package`'s `state` is copied where
    it is one PACKAGE writes. A state `reconcile` moved it to is derived back
    from `pr_url`, so a merged task's package fact never claims `MERGED`."""
    facts = []
    at = task["updated_at"]
    if task["merged_head_sha"] is not None:
        facts.append(one("task_merged_head", at, {"head": task["merged_head_sha"]}))
    if task["pr_url"] is not None:
        state = task["state"]
        if state not in _PACKAGED:
            state = "MERGE_FAILED" if task["pr_url"] == "" else "READY_FOR_REVIEW"
        facts.append(
            one(
                "task_package",
                at,
                {
                    "state": state,
                    "branch": task["branch"],
                    "pushed_sha": task["pushed_sha"],
                    "pr_url": task["pr_url"],
                    "added": task["added"],
                    "removed": task["removed"],
                },
            )
        )
    elif task["pushed_sha"] is not None:
        facts.append(one("task_push", at, {"pushed_sha": task["pushed_sha"]}))
    facts.append(one("task_state", at, {"state": task["state"]}))
    return facts


def _key_filed_facts(
    conn: sqlite3.Connection, task: sqlite3.Row, one: _Maker
) -> list[Fact]:
    """The six tables filed under a record key rather than a task id
    (backlog item 170). One fact per row, after the task's own
    `task_state`. The tables come in the order `Ledger._apply` lists them,
    each table's own rows by its key column, every one timed at the task's
    `updated_at`. A `stack_layer` or `stack_finish` fact carries its row's
    own stored `batch_key`, by `dataclasses.replace`. Every other one keeps
    the task's, already baked into `one`."""
    key = task["record_key"]
    at = task["updated_at"]
    facts: list[Fact] = []
    for row in conn.execute(
        "SELECT * FROM stack_layers WHERE task_key = ? ORDER BY position", (key,)
    ):
        fact = one(
            "stack_layer",
            at,
            {
                "position": row["position"],
                "spec_id": row["spec_id"],
                "predecessor_key": row["predecessor_key"],
                "predecessor_head": row["predecessor_head"],
                "generation": row["generation"],
            },
        )
        facts.append(replace(fact, batch_key=row["batch_key"]))
    for row in conn.execute(
        "SELECT * FROM end_reviews WHERE task_key = ? ORDER BY lens", (key,)
    ):
        facts.append(
            one(
                "end_review",
                at,
                {
                    "lens": row["lens"],
                    "status": row["status"],
                    "cost_usd": row["cost_usd"],
                    "error": row["error"],
                },
            )
        )
    for row in conn.execute(
        "SELECT * FROM qualifications WHERE task_key = ? ORDER BY position", (key,)
    ):
        facts.append(
            one(
                "qualification",
                at,
                {
                    "position": row["position"],
                    "lens": row["lens"],
                    "severity": row["severity"],
                    "file": row["file"],
                    "line": row["line"],
                    "claim": row["claim"],
                    "probe_verdict": row["probe_verdict"],
                    "outcome": row["outcome"],
                    "reason": row["reason"],
                },
            )
        )
    for row in conn.execute(
        "SELECT * FROM spec_reviews WHERE task_key = ? ORDER BY n", (key,)
    ):
        facts.append(
            one(
                "spec_review",
                at,
                {
                    "n": row["n"],
                    "route": row["route"],
                    "block": row["block"],
                    "block_sha256": row["block_sha256"],
                    "error": row["error"],
                },
            )
        )
    for row in conn.execute(
        "SELECT * FROM spec_texts WHERE task_key = ? ORDER BY n", (key,)
    ):
        facts.append(
            one(
                "spec_text",
                at,
                {
                    "n": row["n"],
                    "origin": row["origin"],
                    "spec_id": row["spec_id"],
                    "path": row["path"],
                    "text": row["text"],
                    "spec_sha": row["spec_sha"],
                },
            )
        )
    for row in conn.execute(
        "SELECT * FROM stack_finishes WHERE task_key = ? ORDER BY batch_key", (key,)
    ):
        fact = one(
            "stack_finish",
            at,
            {
                "branch": row["branch"],
                "head_sha": row["head_sha"],
                "pr_url": row["pr_url"],
            },
        )
        facts.append(replace(fact, batch_key=row["batch_key"]))
    return facts


def _repo_rows(source: Path) -> list[sqlite3.Row]:
    """Every `repos` row, read-only, oldest first. What `migrate_and_push`
    fetches from and pushes to, one `RefsRecord` per row."""
    conn = sqlite3.connect(f"{source.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return list(
            conn.execute(
                "SELECT repo_id, name, origin, mirror_path FROM repos ORDER BY repo_id"
            )
        )
    finally:
        conn.close()


def migrate_and_push(source: Path) -> Iterator[tuple[str, str, str | None]]:
    """The `saffron migrate` command's whole orchestration. One
    `RefsRecord` per repo row is fetched from its own `origin` before any
    repo's facts are written. Then each repo's tasks are migrated and each
    migrated key is pushed to the same `origin`, one ref at a time.

    Yields `(kind, key, detail)` as each task ends: `('migrated', key, None)`,
    `('refused', key, reason)`, or `('push_failed', key, detail)` for a stale
    or declined push. Any other push, fetch or append failure raises, and
    the lines already yielded are the caller's to keep."""
    rows = _repo_rows(source)
    records = {row["repo_id"]: RefsRecord(Path(row["mirror_path"])) for row in rows}
    for row in rows:
        records[row["repo_id"]].fetch(row["origin"])
    for row in rows:
        record = records[row["repo_id"]]
        result = migrate(source, record, repo_id=row["repo_id"])
        for key in result.migrated:
            try:
                record.push(key, row["origin"])
            except RecordError as exc:
                if isinstance(exc, StaleWriter) or "[remote rejected]" in exc.stderr:
                    yield ("push_failed", key, f"{type(exc).__name__}: {exc}")
                    continue
                raise
            yield ("migrated", key, None)
        for key, reason in result.refused:
            yield ("refused", key, reason)
