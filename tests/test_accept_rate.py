"""The trailing accept rate: §6's one header number that says whether this
works (`DESIGN.md` §6, backlog item b-49a2f7). The settled/not table lives
once here, so two tests cannot drift apart on its labels.
"""

from __future__ import annotations

from pathlib import Path

from saffron.ledger import Ledger
from saffron.report.index import QueueLine, append_queue_line
from saffron.report.stack import write_stack_view

REPO_URL = "https://github.com/o/r.git"

# Every `TaskState`, marked settled or not (§6). The seven marked `True`
# are the names §6 gives.
_SETTLED_TABLE: dict[str, bool] = {
    "DRAFT": False,
    "QUEUED": False,
    "DIAGNOSING": False,
    "IMPLEMENTING": False,
    "GATING": False,
    "REPAIRING": False,
    "REVIEWING": False,
    "REBUTTING": False,
    "SCOPE_REVIEW": False,
    "PLAN_REJECTED": True,
    "EXHAUSTED": True,
    "READY_FOR_REVIEW": False,
    "MERGE_FAILED": True,
    "PREFLIGHT_FAILED": False,
    "NOT_IMPLEMENTED": True,
    "GATE_ERROR": False,
    "RATE_LIMITED": False,
    "SPEC_WITHHELD": True,
    "APPROVED": False,
    "CHANGES_REQUESTED": False,
    "REJECTED": True,
    "MERGED": True,
    "ORPHANED": False,
    "MERGE_TRAIN": False,
}


def _ledger_with(tmp_path: Path, name: str, states: list[str]) -> Ledger:
    """A fresh ledger holding one task per entry in `states`, in order."""
    ledger = Ledger(tmp_path / f"{name}.db")
    repo_id = ledger.upsert_repo("r", REPO_URL, "/m.git", policy_sha=None)
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    for i, state in enumerate(states):
        task_id = ledger.create_task(
            run_id, spec_id=f"T-{i}", spec_sha="s" * 64, branch=f"saffron/T-{i}"
        )
        ledger.set_task_state(task_id, state)
    return ledger


def test_every_task_state_is_marked_settled_or_not_and_the_set_agrees():
    from typing import get_args

    from saffron.ledger import TaskState
    from saffron.scheduler import SETTLED_STATES

    assert set(_SETTLED_TABLE.keys()) == set(get_args(TaskState))

    settled_names = {
        "MERGED",
        "REJECTED",
        "MERGE_FAILED",
        "EXHAUSTED",
        "NOT_IMPLEMENTED",
        "PLAN_REJECTED",
        "SPEC_WITHHELD",
    }
    assert {name for name, settled in _SETTLED_TABLE.items() if settled} == (
        settled_names
    )
    assert settled_names == SETTLED_STATES


def test_the_rate_is_merged_over_settled_and_names_the_count_below_twenty(tmp_path):
    from saffron.report.index import trailing_accept_rate

    empty = Ledger(tmp_path / "empty.db")
    assert trailing_accept_rate(empty) == "no settled task yet"

    not_settled = [name for name, settled in _SETTLED_TABLE.items() if not settled]
    assert len(not_settled) == 17
    ledger_not_settled = _ledger_with(tmp_path, "not-settled", not_settled)
    assert trailing_accept_rate(ledger_not_settled) == "no settled task yet"

    settled = [
        "MERGED",
        "REJECTED",
        "MERGE_FAILED",
        "EXHAUSTED",
        "NOT_IMPLEMENTED",
        "PLAN_REJECTED",
        "SPEC_WITHHELD",
    ]
    ledger_seven = _ledger_with(tmp_path, "seven-settled", settled)
    assert trailing_accept_rate(ledger_seven) == "14% of 7"

    ledger_one_of_eight = _ledger_with(
        tmp_path, "one-of-eight", ["MERGED"] + ["EXHAUSTED"] * 7
    )
    assert trailing_accept_rate(ledger_one_of_eight) == "13% of 8"

    ledger_none_of_five = _ledger_with(tmp_path, "none-of-five", ["EXHAUSTED"] * 5)
    assert trailing_accept_rate(ledger_none_of_five) == "0% of 5"

    ledger_full_window = _ledger_with(
        tmp_path, "full-window", ["MERGED"] * 15 + ["EXHAUSTED"] * 5
    )
    assert trailing_accept_rate(ledger_full_window) == "75%"


def test_the_window_is_the_twenty_latest_settled_tasks_by_update_then_task_id(
    tmp_path,
):
    from saffron.report.index import trailing_accept_rate

    ledger = Ledger(tmp_path / "window.db")
    repo_a = ledger.upsert_repo("a", "https://github.com/o/a.git", "/a.git", None)
    repo_b = ledger.upsert_repo("b", "https://github.com/o/b.git", "/b.git", None)
    run_a = ledger.create_run(repo_a, base_sha="a" * 40)
    run_b = ledger.create_run(repo_b, base_sha="a" * 40)

    def _task(spec_id: str, state: str, updated_at: str, repo: str) -> int:
        run_id = run_a if repo == "a" else run_b
        task_id = ledger.create_task(
            run_id, spec_id=spec_id, spec_sha="s" * 64, branch=f"saffron/{spec_id}"
        )
        ledger.set_task_state(task_id, state)
        ledger._db.execute(
            "UPDATE tasks SET updated_at = ? WHERE task_id = ?",
            (updated_at, task_id),
        )
        return task_id

    _task("TE-1", "MERGED", "2026-10-02 12:00:00", "a")
    _task("TE-2", "EXHAUSTED", "2026-10-01 00:00:00", "a")
    for n in range(3, 16):
        _task(f"TE-{n}", "MERGED", f"2026-10-01 01:{n:02d}:00", "b" if n % 2 else "a")
    for n in range(16, 21):
        _task(
            f"TE-{n}",
            "NOT_IMPLEMENTED",
            f"2026-10-01 01:{n:02d}:00",
            "b" if n % 2 else "a",
        )
    _task("TE-21", "REJECTED", "2026-10-01 00:30:00", "b")
    _task("TE-22", "MERGED", "2026-10-01 00:30:00", "a")
    _task("TE-23", "READY_FOR_REVIEW", "2026-10-02 13:00:00", "a")

    assert trailing_accept_rate(ledger) == "75%"


def test_the_stack_view_page_carries_the_trailing_accept_rate(tmp_path):
    ledger = Ledger(tmp_path / "stack.db")
    repo_id = ledger.upsert_repo("r", REPO_URL, "/m.git", policy_sha=None)

    batch_id = ledger.create_batch(50.0)
    run_id = ledger.create_run(repo_id, base_sha="a" * 40, batch_id=batch_id)
    layer_task = ledger.create_task(
        run_id, spec_id="Z-1", spec_sha="s" * 64, branch="saffron/Z-1"
    )
    ledger.set_task_state(layer_task, "MERGED")
    ledger.record_stack_layer(
        layer_task, position=1, predecessor_task_id=None, generation=0
    )
    exhausted_task = ledger.create_task(
        run_id, spec_id="Z-2", spec_sha="s" * 64, branch="saffron/Z-2"
    )
    ledger.set_task_state(exhausted_task, "EXHAUSTED")

    outside_run = ledger.create_run(repo_id, base_sha="a" * 40)
    for i in range(2):
        outside_task = ledger.create_task(
            outside_run,
            spec_id=f"Z-out-{i}",
            spec_sha="s" * 64,
            branch=f"saffron/Z-out-{i}",
        )
        ledger.set_task_state(outside_task, "MERGED")

    out_dir = tmp_path / "page"
    append_queue_line(
        out_dir,
        QueueLine(
            repo="r",
            spec_id="Z-2",
            state="EXHAUSTED",
            attempts=1,
            cost_usd_est=1.0,
            concerns=0,
            added=0,
            removed=0,
            link="",
        ),
    )

    written = write_stack_view(out_dir, ledger, {})
    assert written is not None
    assert "trailing accept rate <strong>75% of 4</strong>" in written.read_text()
