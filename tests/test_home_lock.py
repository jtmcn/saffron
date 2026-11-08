"""`cli.main`'s home lock (`saffron/home_lock.py`, backlog item b-a714d2).

Never imports `saffron.home_lock`: every witness drives `cli.main` itself,
so a reverted lock fails an assertion here rather than a collection error.
"""

from __future__ import annotations

import contextlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from saffron import cli, preflight
from saffron.ledger import Ledger
from tests.test_cli import (
    _fake_batch_resolution,
    _seed_repo,
    _seed_task,
    _task_state,
)

_COMMANDS = ("cell", "batch", "draft")

# Kept before any test patches `cli._batch`. A stub standing in for it can
# still hand a nested call to the real function this way.
_REAL_BATCH = cli._batch


def _argv(command: str, home: Path, tmp_path: Path, tag: str) -> list[str]:
    if command == "cell":
        return ["--home", str(home), "cell", str(tmp_path / f"{tag}-spec.md")]
    if command == "batch":
        return [
            "--home",
            str(home),
            "batch",
            "--repo",
            str(tmp_path / f"{tag}-repo"),
        ]
    return [
        "--home",
        str(home),
        "draft",
        str(tmp_path / f"{tag}-item.md"),
        "--repo",
        str(tmp_path / f"{tag}-repo"),
    ]


def _fake_readiness(*_args: object, **_kwargs: object) -> preflight.Readiness:
    return preflight.Readiness(
        True,
        mirror=Path("/tmp/saffron-home-lock-mirror.git"),
        url="https://github.com/o/r.git",
        base_sha="a" * 40,
    )


def _wire_a_draining_batch(monkeypatch, tmp_path, repo_id: int) -> None:
    """`check_readiness`, `_resolve_queue` and `run_batch` faked so the real
    `_batch` reaches a real `reconcile.reconcile` call and nothing past it
    (`cli.run_batch` returns `DRAINED` at once).
    """
    monkeypatch.setattr(cli.preflight, "check_readiness", _fake_readiness)

    def _fake_resolve_queue(
        _repo: Path,
        _home: Path,
        ledger: Ledger,
        *,
        stamp_orphaned: bool,
        pinned: object = None,
        stack: bool = False,
    ) -> cli.QueueResolution:
        cli.reconcile(ledger, repo_id, stamp_orphaned=stamp_orphaned)
        return _fake_batch_resolution(tmp_path, repo_id=repo_id)

    monkeypatch.setattr(cli, "_resolve_queue", _fake_resolve_queue)
    monkeypatch.setattr(cli, "run_batch", lambda *a, **k: "DRAINED")


def test_a_batch_cell_or_draft_beside_another_on_one_home_is_refused(
    monkeypatch, tmp_path
):
    for holder_cmd in _COMMANDS:
        for contender_cmd in _COMMANDS:
            tag = f"{holder_cmd}-{contender_cmd}"
            home = tmp_path / f"home-{tag}"
            pending: dict[str, str | None] = {"command": holder_cmd}
            outcome: dict[str, object] = {}

            def _make_stub(
                name: str,
                pending=pending,
                outcome=outcome,
                contender_cmd=contender_cmd,
                home=home,
                tag=tag,
            ):
                def _stub(args, ledger, out_dir):
                    if pending["command"] == name:
                        pending["command"] = None
                        outcome["result"] = cli.main(
                            _argv(contender_cmd, home, tmp_path, f"{tag}-contender")
                        )
                    else:
                        outcome["started"] = name
                    return 0

                return _stub

            monkeypatch.setattr(cli, "_batch", _make_stub("batch"))
            monkeypatch.setattr(cli, "_run_cell", _make_stub("cell"))
            monkeypatch.setattr(cli, "_draft", _make_stub("draft"))

            holder_result = cli.main(_argv(holder_cmd, home, tmp_path, f"{tag}-holder"))

            assert holder_result == 0, (holder_cmd, contender_cmd, outcome)
            assert outcome.get("result") == 2, (holder_cmd, contender_cmd, outcome)
            assert "started" not in outcome, (holder_cmd, contender_cmd, outcome)

    # A batch started on another home beside each holder still starts its work.
    for holder_cmd in _COMMANDS:
        home_a = tmp_path / f"solo-a-{holder_cmd}"
        home_b = tmp_path / f"solo-b-{holder_cmd}"
        held = {"active": False}
        outcome = {}

        def _make_solo_stub(
            name: str,
            held=held,
            outcome=outcome,
            holder_cmd=holder_cmd,
            home_b=home_b,
        ):
            def _stub(args, ledger, out_dir):
                if not held["active"] and name == holder_cmd:
                    held["active"] = True
                    outcome["other_home_result"] = cli.main(
                        _argv("batch", home_b, tmp_path, f"other-{holder_cmd}")
                    )
                    held["active"] = False
                else:
                    outcome["other_started"] = name
                return 0

            return _stub

        monkeypatch.setattr(cli, "_batch", _make_solo_stub("batch"))
        monkeypatch.setattr(cli, "_run_cell", _make_solo_stub("cell"))
        monkeypatch.setattr(cli, "_draft", _make_solo_stub("draft"))

        result = cli.main(_argv(holder_cmd, home_a, tmp_path, f"solo-{holder_cmd}"))

        assert result == 0, (holder_cmd, outcome)
        assert outcome.get("other_home_result") == 0, (holder_cmd, outcome)


def test_a_batch_beside_a_live_task_leaves_it_in_its_state(monkeypatch, tmp_path):
    cases = [
        ("batch", "REVIEWING"),
        ("cell", "IMPLEMENTING"),
        ("draft", "QUEUED"),
    ]
    for holder_cmd, live_state in cases:
        home = tmp_path / f"home2-{holder_cmd}"
        ledger = Ledger(home / "ledger.db")
        repo_id = _seed_repo(
            tmp_path, ledger, "https://github.com/o/r.git", name=f"repo2-{holder_cmd}"
        )
        task_id = _seed_task(ledger, repo_id, spec_id="SY-1", state=live_state)
        ledger.close()

        _wire_a_draining_batch(monkeypatch, tmp_path, repo_id)

        pending: dict[str, str | None] = {"command": holder_cmd}
        outcome: dict[str, object] = {}

        def _make_stub(
            name: str,
            pending=pending,
            outcome=outcome,
            holder_cmd=holder_cmd,
            home=home,
        ):
            def _stub(args, ledger_arg, out_dir):
                if pending["command"] == name:
                    pending["command"] = None
                    outcome["contender_result"] = cli.main(
                        _argv("batch", home, tmp_path, f"{holder_cmd}-contender2")
                    )
                else:
                    _REAL_BATCH(args, ledger_arg, out_dir)
                return 0

            return _stub

        monkeypatch.setattr(cli, "_batch", _make_stub("batch"))
        monkeypatch.setattr(cli, "_run_cell", _make_stub("cell"))
        monkeypatch.setattr(cli, "_draft", _make_stub("draft"))

        holder_result = cli.main(
            _argv(holder_cmd, home, tmp_path, f"{holder_cmd}-holder2")
        )

        assert holder_result == 0, (holder_cmd, outcome)
        assert outcome.get("contender_result") == 2, (holder_cmd, outcome)
        assert _task_state(home, task_id) == live_state, (holder_cmd, outcome)


def _holder_script(marker: Path, argv: list[str]) -> str:
    return f"""
import subprocess
import sys
import time
from pathlib import Path

from saffron import cli

MARKER = Path({json.dumps(str(marker))})


def _hold(args, ledger, out_dir):
    grandchild = subprocess.Popen(
        ["sleep", "300"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=False,
    )
    MARKER.write_text(str(grandchild.pid))
    time.sleep(300)
    return 0


cli._batch = _hold
cli._run_cell = _hold
cli._draft = _hold

sys.exit(cli.main({json.dumps(argv)}))
"""


def _contender_script(argv: list[str]) -> str:
    return f"""
import sys

from saffron import cli


def _started(args, ledger, out_dir):
    print("contender: started")
    return 0


cli._batch = _started

sys.exit(cli.main({json.dumps(argv)}))
"""


def test_a_killed_holder_frees_the_home_and_its_row_is_stamped_orphaned(
    monkeypatch, tmp_path
):
    repo_root = Path(__file__).resolve().parents[1]
    cases = [
        ("batch", "REVIEWING"),
        ("cell", "IMPLEMENTING"),
        ("draft", "QUEUED"),
    ]
    env = dict(os.environ)
    env.pop("SAFFRON_CELL_RUNTIME", None)

    for holder_cmd, live_state in cases:
        home = tmp_path / f"home3-{holder_cmd}"
        marker = tmp_path / f"marker3-{holder_cmd}"
        ledger = Ledger(home / "ledger.db")
        repo_id = _seed_repo(
            tmp_path, ledger, "https://github.com/o/r.git", name=f"repo3-{holder_cmd}"
        )
        task_id = _seed_task(ledger, repo_id, spec_id="SY-1", state=live_state)
        ledger.close()

        holder_argv = _argv(holder_cmd, home, tmp_path, f"{holder_cmd}-holder3")
        holder_proc = subprocess.Popen(
            [sys.executable, "-c", _holder_script(marker, holder_argv)],
            cwd=repo_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
        )
        grandchild_pid: int | None = None
        try:
            deadline = time.monotonic() + 30
            while not marker.exists():
                if time.monotonic() >= deadline:
                    pytest.fail("the holder's marker was never written within 30s")
                time.sleep(0.05)
            grandchild_pid = int(marker.read_text())

            contender_argv = _argv("batch", home, tmp_path, f"{holder_cmd}-contender3")
            contender = subprocess.run(
                [sys.executable, "-c", _contender_script(contender_argv)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
            )
            assert contender.returncode == 2, contender.stdout
            assert str(holder_proc.pid) in contender.stdout
            assert f"saffron {holder_cmd}" in contender.stdout
            assert "contender: started" not in contender.stdout

            os.kill(holder_proc.pid, signal.SIGKILL)
            holder_proc.wait()
            os.kill(grandchild_pid, 0)

            _wire_a_draining_batch(monkeypatch, tmp_path, repo_id)

            last_result = cli.main(
                _argv("batch", home, tmp_path, f"{holder_cmd}-after3")
            )

            assert last_result == 0
            assert _task_state(home, task_id) == "ORPHANED"
        finally:
            if holder_proc.poll() is None:
                holder_proc.kill()
            holder_proc.wait()
            if grandchild_pid is not None:
                with contextlib.suppress(ProcessLookupError):
                    os.kill(grandchild_pid, signal.SIGKILL)


def test_the_home_is_freed_when_its_holder_returns_or_raises(monkeypatch, tmp_path):
    for holder_cmd in _COMMANDS:
        for should_raise in (False, True):
            tag = f"{holder_cmd}-{should_raise}"
            home = tmp_path / f"home4-{tag}"
            pending = {"active": True}
            outcome: dict[str, object] = {}

            def _make_stub(
                name: str,
                pending=pending,
                outcome=outcome,
                holder_cmd=holder_cmd,
                home=home,
                tag=tag,
                should_raise=should_raise,
            ):
                def _stub(args, ledger, out_dir):
                    if pending["active"] and name == holder_cmd:
                        pending["active"] = False
                        outcome["nested"] = cli.main(
                            _argv("batch", home, tmp_path, f"{tag}-nested")
                        )
                        if should_raise:
                            raise RuntimeError("holder raised")
                        return 0
                    outcome["started"] = name
                    return 0

                return _stub

            monkeypatch.setattr(cli, "_batch", _make_stub("batch"))
            monkeypatch.setattr(cli, "_run_cell", _make_stub("cell"))
            monkeypatch.setattr(cli, "_draft", _make_stub("draft"))

            cli.main(_argv(holder_cmd, home, tmp_path, f"{tag}-holder"))

            assert outcome.get("nested") == 2, (holder_cmd, should_raise, outcome)
            assert "started" not in outcome, (holder_cmd, should_raise, outcome)

            after = cli.main(_argv("batch", home, tmp_path, f"{tag}-after"))
            assert after == 0, (holder_cmd, should_raise)
