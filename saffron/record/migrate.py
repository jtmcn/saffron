"""Record <- ledger. Reads a stored `Ledger`'s rows directly, read-only.
Appends the facts a live run would have written, so a fold gives back §4's
tasks, attempts and findings (backlog item 170, §7).

§ numbers here are `docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md`'s,
not `DESIGN.md`'s.

Nine kinds only. `task_created`, `attempt_opened`, `attempt_closed`,
`finding`, `rebuttal`, `task_merged_head`, `task_package`, `task_push` and
`task_state`. `gate_result` is `SA-0223`'s. No `task_policy` fact is written,
since `policy_sha` rides on `task_created` as stored. The six key-filed
tables are `SA-0224`'s.

Never a `Ledger`. Its open adds missing columns, so it would write the source.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from saffron.record.contract import Fact, Record

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
           r.batch_id AS run_batch_id, rp.name AS repo_name,
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


def migrate(source: Path, record: Record) -> Migration:
    """Append the facts `source`'s stored tasks are owed, task by task in
    `task_id` order. Opens `source` read-only, so its bytes are the same
    after this returns. A path that does not exist raises
    `sqlite3.OperationalError` and creates no file."""
    conn = sqlite3.connect(f"{source.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        result = Migration()
        for task in conn.execute(_TASKS).fetchall():
            key = task["record_key"]
            facts = _facts_for_task(conn, task)
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


def _facts_for_task(conn: sqlite3.Connection, task: sqlite3.Row) -> list[Fact]:
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
    facts.extend(_attempt_facts(conn, task, one))
    facts.extend(_finding_facts(conn, task, one))
    facts.extend(_outcome_facts(task, one))
    return facts


def _attempt_facts(
    conn: sqlite3.Connection, task: sqlite3.Row, one: _Maker
) -> list[Fact]:
    facts = []
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
        if attempt["ended_at"] is not None:
            facts.append(
                one(
                    "attempt_closed",
                    attempt["ended_at"],
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
