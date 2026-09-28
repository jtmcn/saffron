"""The loop driver asks GitHub what merged before it reads its order.

`saffron cell` never reconciles, so a merged parent the ledger still held as
`READY_FOR_REVIEW` had two children stacked on its stale branch (b-877e93).
"""

from __future__ import annotations

import argparse
import json
import subprocess

from saffron.ledger import Ledger
from tests.test_spec_loop_driver import driver

URL = "https://github.com/jtmcn/saffron/pull/7"


def _merged_gh(argv):
    assert argv[:3] == ["gh", "pr", "view"]
    return subprocess.CompletedProcess(
        argv, 0, json.dumps({"state": "MERGED", "reviewDecision": None}), ""
    )


def _waiting_parent(tmp_path):
    ledger = Ledger(tmp_path / "ledger.db")
    repo_id = ledger.upsert_repo("saffron", "o", "/m.git", policy_sha="p" * 64)
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    task_id = ledger.create_task(
        run_id, spec_id="SA-0001", spec_sha="s" * 40, branch="saffron/SA-0001"
    )
    ledger.set_task_state(task_id, "READY_FOR_REVIEW")
    ledger._db.execute("UPDATE tasks SET pr_url = ? WHERE task_id = ?", (URL, task_id))
    ledger._db.commit()
    return ledger, repo_id, task_id


def test_reconcile_first_moves_a_merged_parent_and_says_so_on_stderr(
    tmp_path, monkeypatch, capsys
):
    ledger, repo_id, task_id = _waiting_parent(tmp_path)
    monkeypatch.setattr(driver, "_ledger_and_repo", lambda: (ledger, repo_id, "o"))

    driver._reconcile_first(gh=_merged_gh)

    reopened = Ledger(tmp_path / "ledger.db")
    state = reopened._db.execute(
        "SELECT state FROM tasks WHERE task_id = ?", (task_id,)
    ).fetchone()["state"]
    reopened.close()
    assert state == "MERGED"
    out = capsys.readouterr()
    assert out.out == ""  # `next` prints the chosen spec id alone on stdout
    assert f"task {task_id}" in out.err and "MERGED" in out.err


def test_next_and_snapshot_reconcile_before_they_read(monkeypatch):
    calls = []
    monkeypatch.setattr(driver, "_reconcile_first", lambda: calls.append("reconcile"))

    def load():
        calls.append("read")
        return []

    monkeypatch.setattr(driver, "_load", load)
    monkeypatch.setattr(driver, "_stale", lambda rows: [])
    driver.cmd_next(argparse.Namespace(again=False))
    assert calls == ["reconcile", "read"]

    calls.clear()
    monkeypatch.setattr(driver, "ORDER", driver.REPO / "no-such-order.json")

    def scan(*, loop_branches):
        calls.append("read")
        return [], []

    monkeypatch.setattr(driver, "_scan", scan)
    driver.cmd_snapshot(argparse.Namespace(force=False, new=False, add=None))
    assert calls == ["reconcile", "read"]
