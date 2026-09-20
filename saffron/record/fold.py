"""Record -> index. The ledger holds no fact of its own after this: every row
is replayed from the task facts, so deleting it costs nothing.

Replay, not snapshot: a task's state is what its facts add up to (design §3).
"""

from __future__ import annotations

from datetime import UTC, datetime

from saffron.agents.findings import Finding
from saffron.gates.contract import Failure, GateResult
from saffron.ledger import Ledger
from saffron.record.contract import Fact, Record


def fold(record: Record, ledger: Ledger, strict: bool = True) -> int:
    folded = 0
    for key in _creation_order(record, strict):
        try:
            _fold_task(ledger, key, record.read(key))
        except Exception as exc:
            _discard_task(ledger, key)
            _skipped(key, exc, strict)
            continue
        folded += 1
    return folded


def _skipped(key: str, exc: Exception, strict: bool) -> None:
    """`Exception`, not a named few: `RefsRecord.read` raises
    `subprocess.CalledProcessError` on a broken repository, which is the
    likeliest unreadable task there is (`tests/test_record_refs.py`), and a
    guard that misses it costs the night its whole index."""
    if strict:
        raise ValueError(f"task {key} is unreadable: {exc}") from exc
    print(f"fold: skipped task {key}: {type(exc).__name__}: {exc}")


def _creation_order(record: Record, strict: bool) -> list[str]:
    """Task keys oldest first, by the time their `task_created` fact was
    appended. A record key is random hex, and `ORDER BY t.task_id` is read as
    a chronology by `queue_lines` and `tasks_by_spec`, so folding in key order
    scatters a rebuilt index through time.

    A second read rather than a corpus held in memory: the 118 tasks measured
    on 2026-09-20 carry 33.7 MB of fact JSON, which is not a thing to hold to
    sort by one field of it."""
    dated = []
    for key in sorted(record.task_keys()):
        try:
            created = next(f for f in record.read(key) if f.kind == "task_created")
        except Exception as exc:
            _skipped(key, exc, strict)
            continue
        dated.append((created.at, key))
    return [key for _, key in sorted(dated)]


def _fold_task(ledger: Ledger, key: str, facts: list[Fact]) -> None:
    created = next(f for f in facts if f.kind == "task_created")
    run_id = _run_for(ledger, created)
    task_id = _upsert_task(ledger, key, run_id, created)
    _clear_replayed(ledger, task_id)
    attempt_id: int | None = None
    findings: dict[int, int] = {}
    for fact in facts:
        if fact.kind == "attempt_opened":
            attempt_id = ledger.open_attempt(task_id, phase=fact.payload["phase"])
            _at(ledger, "attempts", "started_at", "attempt_id", attempt_id, fact.at)
        elif fact.kind == "attempt_closed" and attempt_id is not None:
            ledger.close_attempt(attempt_id, **fact.payload)
            _at(ledger, "attempts", "ended_at", "attempt_id", attempt_id, fact.at)
        elif fact.kind == "gate_result":
            ledger.record_gate_result(_gate_result(fact), attempt_id=attempt_id)
        elif fact.kind == "task_state":
            ledger.set_task_state(task_id, fact.payload["state"])
        elif fact.kind == "task_package":
            ledger.set_task_package(task_id, **fact.payload)
        elif fact.kind == "task_push":
            ledger.record_push(task_id, fact.payload["pushed_sha"])
        elif fact.kind == "task_merged_head":
            ledger.record_merged_head(task_id, fact.payload["head"])
        elif fact.kind == "task_policy":
            ledger.record_policy(task_id, fact.payload["policy_sha"])
        elif fact.kind == "finding":
            findings[fact.payload["finding_id"]] = ledger.record_findings(
                task_id, [_finding(fact)]
            )[0]
        elif fact.kind == "rebuttal":
            _rebut(ledger, findings, fact)
    _at(ledger, "tasks", "updated_at", "task_id", task_id, facts[-1].at)


def _ledger_time(at: str) -> str:
    """`Fact.at` is ISO-8601 with an offset; every ledger timestamp column is
    `datetime('now')`'s `%Y-%m-%d %H:%M:%S` in UTC, and `projection` parses it
    with exactly that format."""
    return datetime.fromisoformat(at).astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")


def _at(
    ledger: Ledger, table: str, column: str, key: str, row_id: int, at: str
) -> None:
    """A timestamp column defaults to `datetime('now')`, which for a fold is
    the rebuild's own clock — so `projection`, which ties a task to its
    ceiling span by `runs.started_at` and never by position, would tie every
    folded task to one instant. The fact's own time goes in instead."""
    ledger._db.execute(
        f"UPDATE {table} SET {column} = ? WHERE {key} = ?",
        (_ledger_time(at), row_id),
    )
    ledger._db.commit()


def _finding(fact: Fact) -> Finding:
    payload = fact.payload
    return Finding(
        lens=payload["lens"],
        severity=payload["severity"],
        file=payload["file"],
        line=payload["line"],
        claim=payload["claim"],
        anchored=payload["anchored"],
    )


def _rebut(ledger: Ledger, findings: dict[int, int], fact: Fact) -> None:
    # The fact names the source ledger's `finding_id`; the fold minted its own,
    # so a rebuttal is placed by the finding fact that preceded it or not at all.
    finding_id = findings.get(fact.payload["finding_id"])
    if finding_id is not None:
        ledger.record_rebuttal(
            finding_id,
            verdict=fact.payload["verdict"],
            rebuttal=fact.payload["rebuttal"],
        )


def _discard_task(ledger: Ledger, key: str) -> None:
    """Every row this fold wrote for one task. `Ledger`'s own methods commit as
    they go, so a `with` block around the replay does not roll it back — a
    measured fact, not a supposition (`docs/evidence/2026-09-20-fold-rebuild-
    time.md`). The fold compensates instead, so a task that failed mid-replay
    is absent from the index rather than half-present in it."""
    row = ledger._db.execute(
        "SELECT task_id FROM tasks WHERE record_key = ?", (key,)
    ).fetchone()
    if row is None:
        return
    task_id = int(row["task_id"])
    _clear_replayed(ledger, task_id)
    with ledger._db:
        ledger._db.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))


def _clear_replayed(ledger: Ledger, task_id: int) -> None:
    """Everything the replay is about to re-insert. The fold is an upsert on
    `record_key`, not an append: a task folded twice must hold one copy of its
    attempts, not two. A fresh task has nothing here and the deletes are no-ops.

    Only what hangs off this task's attempts — a baseline result belongs to a
    run, has no task to be folded from, and is not the fold's to delete."""
    with ledger._db:
        ledger._db.execute(
            """DELETE FROM failures WHERE gate_result_id IN
                 (SELECT g.gate_result_id FROM gate_results g
                    JOIN attempts a ON a.attempt_id = g.attempt_id
                   WHERE a.task_id = ?)""",
            (task_id,),
        )
        ledger._db.execute(
            """DELETE FROM gate_results WHERE attempt_id IN
                 (SELECT attempt_id FROM attempts WHERE task_id = ?)""",
            (task_id,),
        )
        ledger._db.execute("DELETE FROM attempts WHERE task_id = ?", (task_id,))
        ledger._db.execute("DELETE FROM findings WHERE task_id = ?", (task_id,))


def _gate_result(fact: Fact) -> GateResult:
    data = dict(fact.payload)
    failures = [Failure(**f) for f in data.pop("failures", [])]
    return GateResult(failures=failures, **data)


def _run_for(ledger: Ledger, created: Fact) -> int:
    """The repo and run a `task_created` fact names. Neither has a record of
    its own — both are a fold over the tasks that name them (design §5), which
    is why the three columns their `NOT NULL` needs ride on the task's fact."""
    payload = created.payload
    # `repos.policy_sha` is nobody's fact: the `policy_sha` a task carries is
    # the declaration that task's gates ran under, not the repo's.
    repo_id = ledger.upsert_repo(
        created.repo, payload["origin"], payload["mirror_path"], policy_sha=None
    )
    found = ledger._db.execute(
        "SELECT run_id FROM runs WHERE repo_id = ? AND base_sha = ?",
        (repo_id, payload["base_sha"]),
    ).fetchone()
    if found is not None:
        return int(found["run_id"])
    # ponytail: design §5 identifies a run by batch and repo, but `batch_key`
    # is NULL on every stored task, so `base_sha` stands in and collapses some.
    run_id = ledger.create_run(repo_id, base_sha=payload["base_sha"])
    _at(ledger, "runs", "started_at", "run_id", run_id, created.at)
    return run_id


def _upsert_task(ledger: Ledger, key: str, run_id: int, created: Fact) -> int:
    """Insert the task the fact describes, or return the one already folded
    under this `record_key` — what makes a second fold cost nothing."""
    found = ledger._db.execute(
        "SELECT task_id FROM tasks WHERE record_key = ?", (key,)
    ).fetchone()
    if found is not None:
        return int(found["task_id"])
    payload = created.payload
    task_id = ledger.create_task(
        run_id,
        spec_id=payload["spec_id"],
        spec_sha=payload["spec_sha"],
        branch=payload["branch"],
        risk=payload["risk"],
        budget_usd=payload["budget_usd"],
        policy_sha=payload["policy_sha"],
        prompt_sha=payload["prompt_sha"],
    )
    # `create_task` mints a key only for a ledger that has a record, and the
    # fold's has none — without this the next fold inserts the task again.
    ledger._db.execute(
        "UPDATE tasks SET record_key = ? WHERE task_id = ?", (key, task_id)
    )
    ledger._db.commit()
    return task_id
