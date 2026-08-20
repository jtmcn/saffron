import subprocess

import pytest

from saffron.repos.mirror import (
    GitError,
    add_worktree,
    changed_files,
    diff_stat,
    ensure_mirror,
    remove_worktree,
    resolve_pull_request,
)


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def origin(tmp_path):
    """A repo with one merged pull request, shaped like a real one."""
    repo = tmp_path / "origin"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "Test")
    (repo / "a.py").write_text("print('one')\n")
    (repo / "keep.py").write_text("print('keep')\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")

    git(repo, "checkout", "-qb", "feature")
    (repo / "a.py").write_text("print('two')\n")
    (repo / "b.py").write_text("print('new')\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "the change")

    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "--no-ff", "-q", "feature", "-m",
        "Merge pull request #42 from someone/feature")
    return repo


def test_ensure_mirror_creates_a_bare_clone(tmp_path, origin):
    mirror = ensure_mirror(origin, tmp_path / "m.git")
    assert mirror.is_dir()
    assert git(mirror, "rev-parse", "--is-bare-repository") == "true"


def test_ensure_mirror_is_idempotent_and_fetches(tmp_path, origin):
    mirror = ensure_mirror(origin, tmp_path / "m.git")
    (origin / "c.py").write_text("print('later')\n")
    git(origin, "add", "-A")
    git(origin, "commit", "-qm", "later")
    ensure_mirror(origin, tmp_path / "m.git")
    assert git(mirror, "log", "--oneline", "-1", "main").endswith("later")


def test_resolve_pull_request_finds_base_and_head(tmp_path, origin):
    mirror = ensure_mirror(origin, tmp_path / "m.git")
    base, head, title = resolve_pull_request(mirror, 42)
    assert base == git(origin, "rev-parse", "main^1")
    assert head == git(origin, "rev-parse", "main^2")
    assert "pull request #42" in title


def test_an_unknown_pull_request_number_raises(tmp_path, origin):
    mirror = ensure_mirror(origin, tmp_path / "m.git")
    with pytest.raises(GitError, match="#999"):
        resolve_pull_request(mirror, 999)


def test_changed_files_lists_only_what_moved(tmp_path, origin):
    mirror = ensure_mirror(origin, tmp_path / "m.git")
    base, head, _ = resolve_pull_request(mirror, 42)
    assert changed_files(mirror, base, head) == ["a.py", "b.py"]


def test_diff_stat_counts_lines(tmp_path, origin):
    mirror = ensure_mirror(origin, tmp_path / "m.git")
    base, head, _ = resolve_pull_request(mirror, 42)
    added, removed = diff_stat(mirror, base, head)
    assert added == 2
    assert removed == 1


def test_add_worktree_checks_out_the_requested_sha(tmp_path, origin):
    mirror = ensure_mirror(origin, tmp_path / "m.git")
    base, head, _ = resolve_pull_request(mirror, 42)

    at_base = add_worktree(mirror, base, tmp_path / "wt-base")
    assert (at_base / "a.py").read_text() == "print('one')\n"
    assert not (at_base / "b.py").exists()

    at_head = add_worktree(mirror, head, tmp_path / "wt-head")
    assert (at_head / "a.py").read_text() == "print('two')\n"
    assert (at_head / "b.py").exists()


def test_remove_worktree_leaves_no_trace(tmp_path, origin):
    mirror = ensure_mirror(origin, tmp_path / "m.git")
    base, _, _ = resolve_pull_request(mirror, 42)
    dest = add_worktree(mirror, base, tmp_path / "wt")
    remove_worktree(mirror, dest)
    assert not dest.exists()
    assert "wt" not in git(mirror, "worktree", "list")


def test_a_bad_sha_raises_rather_than_silently_producing_nothing(tmp_path, origin):
    mirror = ensure_mirror(origin, tmp_path / "m.git")
    with pytest.raises(GitError):
        add_worktree(mirror, "0" * 40, tmp_path / "wt")
