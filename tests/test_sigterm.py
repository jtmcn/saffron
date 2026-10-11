"""SIGTERM must unwind `saffron cell` and `saffron batch` the way Ctrl-C does
(DESIGN.md §4.5, backlog item b-5df2a7). Both share one handler, installed
around `_run_cell` and around `_batch` in turn."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from saffron import cli, task
from saffron.cell import runtime
from saffron.cell.session import CRITIC_NETWORK
from saffron.ledger import Ledger
from tests.test_session import (
    _CRITIC_CONTAINER,
    _CRITIC_STATE,
    _CRITIC_VOLUME,
    _DIFF,
    _IMPLEMENTER_CONTAINER,
    _PLAN,
    _block,
    _drive,
    _stub_the_runtime,
    _turn,
)

_SPEC_TEXT = (
    "---\nid: SY-1\ntitle: One\ntype: feature\ntouches: ['src/**']\n---\n\n"
    "## Acceptance criteria\n- [ ] it works\n"
)

_CELL_DOWN_ORDER = [
    f"removed:container:{_IMPLEMENTER_CONTAINER}",
    "removed:network:saffron-cells",
    f"removed:network:{CRITIC_NETWORK}",
    "removed:volume:saffron-wt-SY-1",
    "removed:volume:saffron-st-SY-1",
]

_CRITIC_CELL_ORDER = [
    f"removed:container:{_CRITIC_CONTAINER}",
    f"removed:volume:{_CRITIC_VOLUME}",
    f"removed:volume:{_CRITIC_STATE}",
]


@dataclass
class _SigtermCall:
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
        except BaseException as exc:  # a leak fails this one call, not the session
            result = exc
        restored = signal.getsignal(signal.SIGTERM)
    finally:
        signal.signal(signal.SIGTERM, outer_previous)

    return _SigtermCall(
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

    call = _run_cell_under_sigterm(
        monkeypatch, tmp_path, "mid-implement", cell=cell, turns=_mid_implement()
    )
    assert call.result == 143
    assert sent == [KeyboardInterrupt]
    assert call.restored == call.handler
    assert call.heard == []
    assert _tail_after_last_turn(cell.order) == _CELL_DOWN_ORDER
    assert "stop" in cell.preflight
    assert (call.run_dir / "out" / "SY-1" / "patch.diff").read_text() == _DIFF
    ledger = Ledger(call.run_dir / "ledger.db")
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

    call = _run_cell_under_sigterm(
        monkeypatch, tmp_path, "mid-review", cell=cell, turns=_mid_review()
    )
    assert call.result == 143
    assert sent == [KeyboardInterrupt]
    assert call.restored == call.handler
    assert call.heard == []
    assert _tail_after_last_turn(cell.order) == _CRITIC_CELL_ORDER + _CELL_DOWN_ORDER
    assert "stop" in cell.preflight
    assert (call.run_dir / "out" / "SY-1" / "patch.diff").read_text() == _DIFF
    ledger = Ledger(call.run_dir / "ledger.db")
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
    call = _run_cell_under_sigterm(
        monkeypatch, tmp_path, "bare-interrupt", cell=cell, turns=[KeyboardInterrupt()]
    )
    assert type(call.result) is KeyboardInterrupt
    assert call.restored == call.handler
    assert call.heard == []

    # `batch` runs under this module's own handler too, never whatever
    # `main` was called with.
    batch_recorded: list[object] = []

    def _batch_stub(_args, _ledger, _out_dir):
        batch_recorded.append(signal.getsignal(signal.SIGTERM))
        return 0

    def batch_previous(_signum: int, _frame: object) -> None:
        pass

    monkeypatch.setattr(cli, "_batch", _batch_stub)
    outer = signal.signal(signal.SIGTERM, batch_previous)
    try:
        batch_result = cli.main(
            ["--home", str(tmp_path / "batch-home"), "batch", "--repo", str(tmp_path)]
        )
    finally:
        signal.signal(signal.SIGTERM, outer)
    assert batch_result == 0
    assert batch_recorded != [batch_previous]


def test_a_second_sigterm_does_not_cut_the_teardown_short(monkeypatch, tmp_path):
    cell = _stub_the_runtime(monkeypatch)
    sent: list[type[BaseException]] = []
    armed = False
    guarded_names: list[str] = []
    stubbed_remove_container = runtime.remove_container

    def _guarded_remove_container(name: str) -> object:
        nonlocal armed
        if armed and name == _IMPLEMENTER_CONTAINER and name not in guarded_names:
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

    call = _run_cell_under_sigterm(
        monkeypatch, tmp_path, "second-signal", cell=cell, turns=_turns()
    )

    assert call.result == 143
    assert sent == [KeyboardInterrupt]
    assert call.restored == call.handler
    assert call.heard == []
    assert guarded_names == [_IMPLEMENTER_CONTAINER]
    assert _tail_after_last_turn(cell.order) == _CELL_DOWN_ORDER


_BATCH_WITNESS_SCRIPT = """
import subprocess
import sys
import time
from pathlib import Path

from saffron import cli, preflight

MARKER = Path("__MARKER__")

_spec1 = cli.Spec(id="SY-1", title="One", type="feature", touches=["src/**"])
_spec2 = cli.Spec(id="SY-2", title="Two", type="feature", touches=["src/**"])
_candidates = [
    cli.Candidate(path=Path("SY-1.md"), spec=_spec1, spec_sha="a" * 40, task_id=None),
    cli.Candidate(path=Path("SY-2.md"), spec=_spec2, spec_sha="b" * 40, task_id=None),
]


def _fake_readiness(repo, mirror_path, *, scratch, home, token):
    return preflight.Readiness(
        ok=True, mirror=mirror_path, url="https://github.com/o/r.git", base_sha="c" * 40
    )


def _fake_resolve_queue(repo, home, ledger, *, stamp_orphaned, pinned=None, stack=False):
    return cli.QueueResolution(
        repo_id=None,
        mirror=pinned.mirror if pinned is not None else Path("mirror"),
        base_sha=pinned.base_sha if pinned is not None else "c" * 40,
        repo_slug=None,
        exported=Path("exported"),
        candidates=_candidates,
        refusals=[],
        reconciled=cli.ReconcileResult(),
        gh_failures=[],
        policy_unread=[],
    )


def _fake_protected_paths_at(mirror, base_sha, scratch, unread=None):
    return []


def _fake_retirement_markers_at(mirror, base_sha):
    return []


def _fake_run_task(spec, spec_sha, **kwargs):
    print(f"run_task: {spec.id}")
    with subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(20)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ):
        MARKER.write_text("ready")
        time.sleep(60)
    raise AssertionError("run_task stub should not return")


preflight.check_readiness = _fake_readiness
cli._resolve_queue = _fake_resolve_queue
cli._protected_paths_at = _fake_protected_paths_at
cli._retirement_markers_at = _fake_retirement_markers_at
cli.run_task = _fake_run_task

sys.exit(cli.main(["--home", "__HOME__", "batch", "--repo", "__REPO__"]))
"""


def test_a_batch_sent_sigterm_exits_143_with_its_log_flushed(tmp_path):
    """A real `saffron batch` process, stdout piped, no `PYTHONUNBUFFERED`.
    SIGTERM arrives while the first task holds a live child inside its own
    `with subprocess.Popen` block, the case `Popen.__exit__`'s exact-class
    check turns on. The first task never returns, so no second one
    starts."""
    repo_root = Path(__file__).resolve().parents[1]
    home = tmp_path / "home"
    marker = tmp_path / "marker"
    script = (
        _BATCH_WITNESS_SCRIPT.replace("__MARKER__", str(marker))
        .replace("__HOME__", str(home))
        .replace("__REPO__", str(tmp_path / "repo"))
    )

    env = dict(os.environ, CLAUDE_CODE_OAUTH_TOKEN="sk-test")
    env.pop("PYTHONUNBUFFERED", None)
    env.pop("SAFFRON_CELL_RUNTIME", None)

    proc = subprocess.Popen(
        [sys.executable, "-c", script],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=env,
        text=True,
    )
    try:
        deadline = time.monotonic() + 30
        while not marker.exists():
            if proc.poll() is not None:
                pytest.fail(
                    f"the batch process exited ({proc.returncode}) before "
                    "its first task's child was holding the marker"
                )
            if time.monotonic() >= deadline:
                pytest.fail("the marker was never written within 30s")
            time.sleep(0.05)

        proc.send_signal(signal.SIGTERM)
        try:
            stdout, _ = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            stdout = ""
            pytest.fail("the batch process did not exit within 10s of SIGTERM")
    finally:
        proc.kill()
        proc.wait()

    assert proc.returncode == 143
    lines = [line for line in stdout.splitlines() if line]
    assert lines[-1] == "run_task: SY-1"
    assert "SY-2       starting" not in stdout
    assert "run_task: SY-2" not in stdout

    ledger = Ledger(home / "ledger.db")
    try:
        (row,) = ledger._db.execute("SELECT status, ended_at FROM batches").fetchall()
        assert row["status"] == "INFRASTRUCTURE"
        assert row["ended_at"] is not None
    finally:
        ledger.close()
