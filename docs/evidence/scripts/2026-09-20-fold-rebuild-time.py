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
from collections import Counter
from pathlib import Path

from saffron.agents.findings import Finding
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
        facts += _replay_outcome(db, ledger, task, task_id)
    return facts


def _replay_outcome(
    db: sqlite3.Connection, ledger: Ledger, task: sqlite3.Row, task_id: int
) -> int:
    """The columns PACKAGE, `reconcile` and REVIEW write, as the facts that
    wrote them. `policy_sha` is left to `create_task`, which carries it
    already; nothing in a stored row says whether `record_policy` also ran."""
    count = 0
    if task["pushed_sha"] is not None:
        ledger.record_push(task_id, task["pushed_sha"])
        count += 1
    if task["pr_url"] is not None:
        ledger.set_task_package(
            task_id, task["state"], task["branch"], task["pushed_sha"], task["pr_url"]
        )
        count += 1
    if task["merged_head_sha"] is not None:
        ledger.record_merged_head(task_id, task["merged_head_sha"])
        count += 1
    for f in db.execute(
        "SELECT * FROM findings WHERE task_id = ? ORDER BY finding_id",
        (task["task_id"],),
    ):
        finding_id = ledger.record_findings(
            task_id,
            [
                Finding(
                    lens=f["lens"],
                    severity=f["severity"],
                    file=f["file"],
                    line=f["line"],
                    claim=f["claim"],
                    anchored=bool(f["anchored"]),
                )
            ],
        )[0]
        count += 1
        if f["verdict"] is not None or f["rebuttal"] is not None:
            ledger.record_rebuttal(
                finding_id, verdict=f["verdict"], rebuttal=f["rebuttal"]
            )
            count += 1
    return count


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


def _sizes(repo: Path) -> tuple[dict[str, int], str]:
    """What the record costs three ways, because they differ by an order of
    magnitude: the blocks it occupies, the compressed bytes it is, and the
    fact JSON it holds. `st_size` alone reads as the smallest of the three."""
    files = [f for f in repo.rglob("*") if f.is_file()]
    listed = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "--batch-all-objects",
         "--batch-check=%(objecttype) %(objectsize) %(objectname)"],
        capture_output=True, text=True, check=True,
    ).stdout
    blobs = [line.split() for line in listed.splitlines() if line.startswith("blob")]
    biggest = max(blobs, key=lambda b: int(b[1]))
    return {
        "allocated": sum(f.stat().st_blocks * 512 for f in files),
        "compressed": sum(f.stat().st_size for f in files),
        "fact_json": sum(int(b[1]) for b in blobs),
        "facts": len(blobs),
        "largest": int(biggest[1]),
    }, biggest[2]


# The columns each table has to bring back. Multisets, not ordered reads: the
# fold mints its own autoincrements, so row order is not what has to match.
_SAME = {
    "tasks": "spec_id, spec_sha, state, risk, branch, budget_usd, spent_usd_est,"
    " record_key, pushed_sha, pr_url, policy_sha, merged_head_sha",
    "attempts": "phase, n, session_id, subtype, num_turns, cost_usd_est,"
    " started_at, ended_at",
    "gate_results": "gate, status, tool, summary, duration_ms",
    "failures": "file, code, message, line",
    "findings": "lens, severity, file, line, claim, anchored, verdict, rebuttal",
}


def _agrees(source: Path, rebuilt: Path) -> None:
    """Design §4's criterion against real nights. The unit tests pin the
    mechanism on a fixture, which can only show the fold agreeing with itself;
    this is the half that can say 118 stored tasks came back."""
    was, now = _source(source), _source(rebuilt)
    for table, columns in _SAME.items():
        a = Counter(tuple(r) for r in was.execute(f"SELECT {columns} FROM {table}"))
        b = Counter(tuple(r) for r in now.execute(f"SELECT {columns} FROM {table}"))
        verdict = "identical" if a == b else f"DIFFERS on {sum(((a - b) + (b - a)).values())}"
        print(f"  {table:<13} {sum(a.values()):>7} -> {sum(b.values()):>7}  {verdict}")
    runs = [
        len(was.execute("SELECT run_id FROM runs").fetchall()),
        len(now.execute("SELECT run_id FROM runs").fetchall()),
    ]
    print(f"  {'runs':<13} {runs[0]:>7} -> {runs[1]:>7}  declared collapse on base_sha")


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

    size, biggest = _sizes(repo)
    rebuilt = work / "rebuilt.db"
    rebuilt.unlink(missing_ok=True)
    ledger = Ledger(rebuilt)
    started = time.monotonic()
    tasks = fold(record, ledger).folded
    elapsed = time.monotonic() - started
    ledger.close()

    print(f"folded {tasks} tasks, {facts} facts in {elapsed:.2f}s")
    print(f"record, blocks allocated: {size['allocated'] / 1e6:.1f} MB")
    print(f"record, compressed bytes: {size['compressed'] / 1e6:.1f} MB")
    print(f"record, fact JSON:        {size['fact_json'] / 1e6:.1f} MB")
    print(
        f"largest single fact: {size['largest'] / 1e6:.2f} MB "
        f"({size['largest']} bytes) {biggest}"
    )
    print(f"ledger rebuilt: {rebuilt.stat().st_size / 1e6:.1f} MB")
    print("what came back:")
    _agrees(work / "synth.db", rebuilt)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
