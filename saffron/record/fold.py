"""Record -> index. The ledger holds no fact of its own after this: every row
is replayed from the task facts, so deleting it costs nothing.

Replay, not snapshot: a task's state is what its facts add up to (design §3).
"""

from __future__ import annotations

from saffron.gates.contract import Failure, GateResult
from saffron.ledger import Ledger
from saffron.record.contract import Fact, Record


def fold(record: Record, ledger: Ledger, strict: bool = True) -> int:
    folded = 0
    for key in sorted(record.task_keys()):
        try:
            facts = record.read(key)
            # Inside the try with the read: a backend that hands back rubbish
            # rather than raising is the same unreadable task, and fails here.
            _fold_task(ledger, key, facts)
        except (ValueError, TypeError, AttributeError) as exc:
            if strict:
                raise ValueError(f"task {key} is unreadable: {exc}") from exc
            continue
        folded += 1
    return folded


def _fold_task(ledger: Ledger, key: str, facts: list[Fact]) -> None:
    created = next(f for f in facts if f.kind == "task_created")
    run_id = _run_for(ledger, created)
    task_id = _upsert_task(ledger, key, run_id, created)
    _clear_replayed(ledger, task_id)
    attempt_id: int | None = None
    for fact in facts:
        if fact.kind == "attempt_opened":
            attempt_id = ledger.open_attempt(task_id, phase=fact.payload["phase"])
        elif fact.kind == "attempt_closed" and attempt_id is not None:
            ledger.close_attempt(attempt_id, **fact.payload)
        elif fact.kind == "gate_result":
            ledger.record_gate_result(_gate_result(fact), attempt_id=attempt_id)
        elif fact.kind == "task_state":
            ledger.set_task_state(task_id, fact.payload["state"])


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
    # ponytail: two runs off one base_sha fold into one row, and `batch_id`
    # stays NULL. The run and batch folds are the next plan's (design §5).
    return ledger.create_run(repo_id, base_sha=payload["base_sha"])


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
