"""SIGTERM must unwind `saffron cell` the way Ctrl-C does (DESIGN.md §4.5,
backlog item b-5df2a7). `batch` is untouched here. `SA-0258` wraps it."""

from __future__ import annotations

import os
import signal
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from saffron import cli, task
from saffron.cell import runtime
from saffron.ledger import Ledger
from tests.test_session import _DIFF, _PLAN, _block, _drive, _stub_the_runtime, _turn

_SPEC_TEXT = (
    "---\nid: SY-1\ntitle: One\ntype: feature\ntouches: ['src/**']\n---\n\n"
    "## Acceptance criteria\n- [ ] it works\n"
)

_CELL_DOWN_ORDER = [
    "removed:container:saffron-cell-SY-1",
    "removed:network:saffron-cells",
    "removed:network:saffron-critic-net",
    "removed:volume:saffron-wt-SY-1",
    "removed:volume:saffron-st-SY-1",
]

_CRITIC_CELL_ORDER = [
    "removed:container:saffron-critic-SY-1",
    "removed:volume:saffron-critic-wt-SY-1",
    "removed:volume:saffron-critic-st-SY-1",
]


@dataclass
class _SigtermRun:
    """What one `cli.main(["cell", ...])` call, driven under a record-only
    SIGTERM handler, came back as."""

    result: Any
    restored: Any
    handler: Any
    heard: list[int]
    run_dir: Path


def _run_cell_under_sigterm(monkeypatch, tmp_path, run_name, *, cell, turns):
    """Drive `cli.main(["cell", ...])` with its cell replaced by `_drive`
    over the already-stubbed `cell` and `turns`.

    Stubs the token and the three mirror reads `_run_cell` pays for. Then
    replaces `task.run_one_cell` so the real `run_one_cell` runs, against
    `cell`, in its own directory under `tmp_path`. Installs a record-only
    handler before the call, and reads the disposition right after, before
    putting the test's own handler back.
    """
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-test")
    monkeypatch.setattr("saffron.repos.mirror.ensure_mirror", lambda repo, at: at)
    monkeypatch.setattr(
        "saffron.phases.package.real_remote", lambda repo: "https://github.com/o/r.git"
    )
    monkeypatch.setattr(
        "saffron.phases.package.fetch_default_branch",
        lambda mirror, url: ("main", "a" * 40),
    )

    run_dir = tmp_path / run_name
    run_dir.mkdir()
    spec_path = run_dir / "SY-1.md"
    spec_path.write_text(_SPEC_TEXT)

    def _run_one_cell_stub(*_a: object, **_k: object) -> object:
        outcome, _ledger = _drive(monkeypatch, run_dir, cell=cell, turns=turns)
        return outcome

    monkeypatch.setattr(task, "run_one_cell", _run_one_cell_stub)

    heard: list[int] = []

    def _record(signum: int, _frame: object) -> None:
        heard.append(signum)

    outer_previous = signal.signal(signal.SIGTERM, _record)
    try:
        try:
            result: Any = cli.main(
                ["--home", str(run_dir / "home"), "cell", str(spec_path)]
            )
        except BaseException as exc:  # a leak fails this one run, not the session
            result = exc
        restored = signal.getsignal(signal.SIGTERM)
    finally:
        signal.signal(signal.SIGTERM, outer_previous)

    return _SigtermRun(
        result=result, restored=restored, handler=_record, heard=heard, run_dir=run_dir
    )


def _tail_after_last_turn(order: list[str]) -> list[str]:
    last = max(i for i, entry in enumerate(order) if entry.startswith("turn:"))
    return order[last + 1 :]


def test_a_cell_sent_sigterm_tears_down_and_closes_its_task(monkeypatch, tmp_path):
    # Mid-IMPLEMENT: the plan turn lands, then SIGTERM arrives for the
    # implement turn itself.
    cell = _stub_the_runtime(monkeypatch)
    sent: list[type[BaseException]] = []

    def _mid_implement():
        scripted = [_turn(_block(_PLAN)), _turn()]
        for i, turn in enumerate(scripted):
            if i == 1:
                try:
                    os.kill(os.getpid(), signal.SIGTERM)
                except BaseException as exc:
                    sent.append(type(exc))
                    raise
            yield turn

    run = _run_cell_under_sigterm(
        monkeypatch, tmp_path, "mid-implement", cell=cell, turns=_mid_implement()
    )
    assert run.result == 143
    assert sent == [KeyboardInterrupt]
    assert run.restored == run.handler
    assert run.heard == []
    assert _tail_after_last_turn(cell.order) == _CELL_DOWN_ORDER
    assert "stop" in cell.preflight
    assert (run.run_dir / "out" / "SY-1" / "patch.diff").read_text() == _DIFF
    ledger = Ledger(run.run_dir / "ledger.db")
    try:
        (run_row,) = ledger._db.execute("SELECT status FROM runs").fetchall()
        assert run_row["status"] == "ABORTED"
        (queued,) = ledger.queue_lines()
        assert queued["state"] == "ORPHANED"
    finally:
        ledger.close()

    # Mid-REVIEW: plan and implement land clean, then SIGTERM arrives for
    # REVIEW's first lens turn.
    cell = _stub_the_runtime(monkeypatch)
    sent = []

    def _mid_review():
        scripted = [_turn(_block(_PLAN)), _turn(), _turn()]
        for i, turn in enumerate(scripted):
            if i == 2:
                try:
                    os.kill(os.getpid(), signal.SIGTERM)
                except BaseException as exc:
                    sent.append(type(exc))
                    raise
            yield turn

    run = _run_cell_under_sigterm(
        monkeypatch, tmp_path, "mid-review", cell=cell, turns=_mid_review()
    )
    assert run.result == 143
    assert sent == [KeyboardInterrupt]
    assert run.restored == run.handler
    assert run.heard == []
    assert _tail_after_last_turn(cell.order) == _CRITIC_CELL_ORDER + _CELL_DOWN_ORDER
    assert "stop" in cell.preflight
    assert (run.run_dir / "out" / "SY-1" / "patch.diff").read_text() == _DIFF
    ledger = Ledger(run.run_dir / "ledger.db")
    try:
        (run_row,) = ledger._db.execute("SELECT status FROM runs").fetchall()
        assert run_row["status"] == "ABORTED"
        (queued,) = ledger.queue_lines()
        assert queued["state"] == "ORPHANED"
    finally:
        ledger.close()

    # No signal at all: a bare KeyboardInterrupt still propagates out of
    # `main`, unread as a SIGTERM.
    cell = _stub_the_runtime(monkeypatch)
    run = _run_cell_under_sigterm(
        monkeypatch, tmp_path, "bare-interrupt", cell=cell, turns=[KeyboardInterrupt()]
    )
    assert type(run.result) is KeyboardInterrupt
    assert run.restored == run.handler
    assert run.heard == []

    # `batch` is untouched by this spec: the handler in place while it runs
    # is whatever `main` was called with, never one this change installs.
    batch_recorded: list[object] = []

    def _batch_stub(_args, _ledger, _out_dir):
        batch_recorded.append(signal.getsignal(signal.SIGTERM))
        return 0

    monkeypatch.setattr(cli, "_batch", _batch_stub)
    batch_previous = signal.getsignal(signal.SIGTERM)
    batch_result = cli.main(
        ["--home", str(tmp_path / "batch-home"), "batch", "--repo", str(tmp_path)]
    )
    assert batch_result == 0
    assert batch_recorded == [batch_previous]


def test_a_second_sigterm_does_not_cut_the_teardown_short(monkeypatch, tmp_path):
    cell = _stub_the_runtime(monkeypatch)
    sent: list[type[BaseException]] = []
    armed = False
    guarded_names: list[str] = []
    stubbed_remove_container = runtime.remove_container

    def _guarded_remove_container(name: str) -> object:
        nonlocal armed
        if armed and name == "saffron-cell-SY-1" and name not in guarded_names:
            guarded_names.append(name)
            if signal.getsignal(signal.SIGTERM) is signal.SIG_DFL:
                pytest.fail(
                    "SIGTERM is at its default disposition; a second "
                    "delivery would end the test process"
                )
            os.kill(os.getpid(), signal.SIGTERM)
        return stubbed_remove_container(name)

    monkeypatch.setattr(runtime, "remove_container", _guarded_remove_container)

    def _turns():
        nonlocal armed
        scripted = [_turn(_block(_PLAN)), _turn()]
        for i, turn in enumerate(scripted):
            if i == 1:
                armed = True
                try:
                    os.kill(os.getpid(), signal.SIGTERM)
                except BaseException as exc:
                    sent.append(type(exc))
                    raise
            yield turn

    run = _run_cell_under_sigterm(
        monkeypatch, tmp_path, "second-signal", cell=cell, turns=_turns()
    )

    assert run.result == 143
    assert sent == [KeyboardInterrupt]
    assert run.restored == run.handler
    assert run.heard == []
    assert _tail_after_last_turn(cell.order) == _CELL_DOWN_ORDER
