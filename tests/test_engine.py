"""`saffron.engine.engine_commit`, the engine that judged a task (ADR 10)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def _isolate_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Shields every git call here from the operator's own config, the way
    `_isolate_git` in `tests/test_finish.py` does."""
    empty = tmp_path / "empty-home"
    empty.mkdir()
    monkeypatch.setenv("HOME", str(empty))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(empty))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")


def _commit(repo: Path) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")


def test_a_baked_engine_commit_is_read_before_any_checkout(tmp_path, monkeypatch):
    from saffron.engine import engine_commit

    _isolate_git(tmp_path, monkeypatch)

    # A baked file inside a committed checkout wins over the checkout's own HEAD.
    repo = tmp_path / "repo"
    pkg = repo / "saffron"
    pkg.mkdir(parents=True)
    (repo / "f.txt").write_text("x")
    (pkg / "ENGINE_COMMIT").write_text("  deadbeef00  \n")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Test")
    _commit(repo)

    with monkeypatch.context() as m:

        def _no_git(*_args, **_kwargs):
            raise AssertionError("git should not be asked when a baked value answers")

        m.setattr(subprocess, "run", _no_git)
        assert engine_commit(pkg) == "deadbeef00"

    # A baked file in a directory no checkout holds answers the same way.
    bare = tmp_path / "nocheckout"
    bare.mkdir()
    (bare / "ENGINE_COMMIT").write_text("cafebabe00")
    assert engine_commit(bare) == "cafebabe00"

    # A blank file, untracked so the checkout stays clean, reads HEAD instead.
    blank_repo = tmp_path / "blank-repo"
    blank_pkg = blank_repo / "saffron"
    blank_pkg.mkdir(parents=True)
    (blank_repo / "f.txt").write_text("x")
    _git(blank_repo, "init", "-q", "-b", "main")
    _git(blank_repo, "config", "user.email", "t@example.com")
    _git(blank_repo, "config", "user.name", "Test")
    _commit(blank_repo)
    blank_head = _git(blank_repo, "rev-parse", "HEAD")
    for blank in ("", "\n \n"):
        (blank_pkg / "ENGINE_COMMIT").write_text(blank)
        assert engine_commit(blank_pkg) == blank_head


def test_a_checkout_reports_its_head_and_marks_a_tracked_change_dirty(
    tmp_path, monkeypatch
):
    from saffron.engine import engine_commit

    _isolate_git(tmp_path, monkeypatch)
    repo = tmp_path / "repo"
    pkg = repo / "saffron"
    pkg.mkdir(parents=True)
    (repo / "f.txt").write_text("a\nb\n")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Test")
    _commit(repo)
    head = _git(repo, "rev-parse", "HEAD")
    assert len(head) == 40

    index = repo / ".git" / "index"
    before = index.read_bytes()
    future = os.path.getmtime(repo / "f.txt") + 120
    os.utime(repo / "f.txt", (future, future))
    assert engine_commit(pkg) == head
    assert index.read_bytes() == before

    (repo / "untracked.txt").write_text("new")
    assert engine_commit(pkg) == head

    (repo / "f.txt").write_text("a\nb\nCHANGED\n")
    assert engine_commit(pkg) == f"{head}-dirty"

    _git(repo, "add", "f.txt")
    assert engine_commit(pkg) == f"{head}-dirty"


def test_no_baked_value_and_no_checkout_of_its_own_reads_none(tmp_path, monkeypatch):
    from saffron.engine import engine_commit

    _isolate_git(tmp_path, monkeypatch)

    stray = tmp_path / "stray"
    stray.mkdir()
    assert engine_commit(stray) is None

    repo = tmp_path / "repo"
    nested = repo / "pkg" / "saffron"
    nested.mkdir(parents=True)
    (repo / "f.txt").write_text("x")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Test")
    _commit(repo)
    assert engine_commit(nested) is None

    empty_repo = tmp_path / "empty-repo"
    empty_pkg = empty_repo / "saffron"
    empty_pkg.mkdir(parents=True)
    _git(empty_repo, "init", "-q", "-b", "main")
    assert engine_commit(empty_pkg) is None


def test_with_no_argument_it_reads_its_own_directory_wherever_it_runs(
    tmp_path, monkeypatch
):
    import saffron.engine as engine_mod

    fresh = tmp_path / "wherever" / "saffron"
    fresh.mkdir(parents=True)
    (fresh / "ENGINE_COMMIT").write_text("sentinel-engine-value")
    monkeypatch.setattr(engine_mod, "__file__", str(fresh / "engine.py"))
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    assert engine_mod.engine_commit() == engine_mod.engine_commit(fresh)
