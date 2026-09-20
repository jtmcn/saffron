"""How long the fold takes, and what the record costs, against real nights.

`usage: python <this> <ledger.db> <work-dir>`

There is no record anywhere yet, so the benchmark synthesises one: it replays
a real ledger's rows through `Ledger`'s own write methods into a throwaway
`RefsRecord`, which gives the fold the fact shapes and counts production would
hand it. Nothing is written to `~/.saffron` — the ledger is copied first.
"""

from __future__ import annotations

import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from saffron.gates.contract import Failure, GateResult
from saffron.ledger import Ledger
from saffron.record.fold import fold
from saffron.record.refs import RefsRecord


def _source(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    return db


def _synthesize(db: sqlite3.Connection, ledger: Ledger) -> int:
    """Every stored task, written as the facts its night would have appended."""
    facts = 0
    repos = {
        row["repo_id"]: ledger.upsert_repo(
            row["name"], row["origin"], row["mirror_path"], row["policy_sha"]
        )
        for row in db.execute("SELECT * FROM repos")
    }
    for task in db.execute("SELECT * FROM tasks ORDER BY task_id"):
        run = db.execute(
            "SELECT * FROM runs WHERE run_id = ?", (task["run_id"],)
        ).fetchone()
        run_id = ledger.create_run(repos[run["repo_id"]], base_sha=run["base_sha"])
        task_id = ledger.create_task(
            run_id,
            spec_id=task["spec_id"],
            spec_sha=task["spec_sha"],
            branch=task["branch"],
            risk=task["risk"],
            budget_usd=task["budget_usd"],
            policy_sha=task["policy_sha"],
            prompt_sha=task["prompt_sha"],
        )
        facts += 1
        for attempt in db.execute(
            "SELECT * FROM attempts WHERE task_id = ? ORDER BY attempt_id",
            (task["task_id"],),
        ):
            attempt_id = ledger.open_attempt(task_id, phase=attempt["phase"])
            facts += 1
            facts += _replay_gates(db, ledger, attempt["attempt_id"], attempt_id)
            if attempt["ended_at"] is not None:
                ledger.close_attempt(
                    attempt_id,
                    session_id=attempt["session_id"],
                    model=attempt["model"],
                    subtype=attempt["subtype"],
                    terminal_reason=attempt["terminal_reason"],
                    num_turns=attempt["num_turns"],
                    cost_usd_est=attempt["cost_usd_est"],
                )
                facts += 1
        ledger.set_task_state(task_id, task["state"])
        facts += 1
    return facts


def _replay_gates(
    db: sqlite3.Connection, ledger: Ledger, was: int, now: int
) -> int:
    count = 0
    for result in db.execute(
        "SELECT * FROM gate_results WHERE attempt_id = ? ORDER BY gate_result_id",
        (was,),
    ):
        failures = [
            Failure(file=f["file"], line=f["line"], code=f["code"],
                    message=f["message"] or "")
            for f in db.execute(
                "SELECT * FROM failures WHERE gate_result_id = ?",
                (result["gate_result_id"],),
            )
        ]
        ledger.record_gate_result(
            GateResult(
                gate=result["gate"],
                status=result["status"],
                tool=result["tool"],
                duration_ms=result["duration_ms"],
                summary=result["summary"] or "",
                failures=failures,
            ),
            attempt_id=now,
        )
        count += 1
    return count


def _sizes(repo: Path) -> tuple[int, int, str]:
    """Bytes on disk, the largest fact's own bytes, and the object it is."""
    disk = sum(f.stat().st_size for f in repo.rglob("*") if f.is_file())
    listed = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "--batch-all-objects",
         "--batch-check=%(objecttype) %(objectsize) %(objectname)"],
        capture_output=True, text=True, check=True,
    ).stdout
    blobs = [line.split() for line in listed.splitlines() if line.startswith("blob")]
    biggest = max(blobs, key=lambda b: int(b[1]))
    return disk, int(biggest[1]), biggest[2]


def main(source: Path, work: Path) -> None:
    work.mkdir(parents=True, exist_ok=True)
    copy = work / "source.db"
    shutil.copy(source, copy)
    repo = work / "record.git"
    subprocess.run(["git", "init", "-q", "--bare", str(repo)], check=True)

    record = RefsRecord(repo)
    synth = Ledger(work / "synth.db", record=record)
    started = time.monotonic()
    facts = _synthesize(_source(copy), synth)
    print(f"record built: {facts} facts in {time.monotonic() - started:.1f}s")
    synth.close()

    disk, largest, name = _sizes(repo)
    rebuilt = work / "rebuilt.db"
    rebuilt.unlink(missing_ok=True)
    ledger = Ledger(rebuilt)
    started = time.monotonic()
    tasks = fold(record, ledger)
    elapsed = time.monotonic() - started
    ledger.close()

    print(f"folded {tasks} tasks, {facts} facts in {elapsed:.2f}s")
    print(f"record on disk: {disk / 1e6:.1f} MB ({disk} bytes)")
    print(f"largest single fact: {largest / 1e6:.2f} MB ({largest} bytes) {name}")
    print(f"index rebuilt: {rebuilt.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
