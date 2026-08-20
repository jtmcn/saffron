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


def test_a_missing_git_binary_surfaces_as_giterror(tmp_path, origin, monkeypatch):
    mirror = ensure_mirror(origin, tmp_path / "m.git")

    def raise_oserror(*args, **kwargs):
        raise OSError("git: command not found")

    monkeypatch.setattr(subprocess, "run", raise_oserror)

    # the ensure_mirror clone path (no mirror exists yet) does not go through _git
    with pytest.raises(GitError):
        ensure_mirror(origin, tmp_path / "m2.git")

    # every other function goes through _git
    with pytest.raises(GitError):
        changed_files(mirror, "HEAD", "HEAD")


def _squash_repo(tmp_path, name, subject):
    """A base commit plus one commit with the given subject, no branch needed."""
    repo = tmp_path / name
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "Test")
    (repo / "a.py").write_text("print('one')\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")

    (repo / "a.py").write_text("print('two')\n")
    (repo / "b.py").write_text("print('new')\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", subject)
    return repo


def test_resolve_pull_request_finds_a_squash_commit(tmp_path):
    origin = _squash_repo(tmp_path, "sq", "Add the feature (#7)")
    mirror = ensure_mirror(origin, tmp_path / "sq.git")

    base, head, title = resolve_pull_request(mirror, 7)
    assert base == git(origin, "rev-parse", "HEAD^1")
    assert head == git(origin, "rev-parse", "HEAD")
    assert title == "Add the feature (#7)"

    at_base = add_worktree(mirror, base, tmp_path / "sq-wt-base")
    assert (at_base / "a.py").read_text() == "print('one')\n"
    assert not (at_base / "b.py").exists()

    at_head = add_worktree(mirror, head, tmp_path / "sq-wt-head")
    assert (at_head / "a.py").read_text() == "print('two')\n"
    assert (at_head / "b.py").exists()


def test_short_pr_number_does_not_match_a_longer_squash_subject(tmp_path):
    origin = _squash_repo(tmp_path, "sq42", "Add the feature (#42)")
    mirror = ensure_mirror(origin, tmp_path / "sq42.git")
    with pytest.raises(GitError, match="#4"):
        resolve_pull_request(mirror, 4)


def test_pr_number_does_not_match_a_squash_subject_with_a_longer_number(tmp_path):
    origin = _squash_repo(tmp_path, "sq142", "Add the feature (#142)")
    mirror = ensure_mirror(origin, tmp_path / "sq142.git")
    with pytest.raises(GitError, match="#42"):
        resolve_pull_request(mirror, 42)


def test_a_number_mentioned_mid_subject_does_not_match(tmp_path):
    origin = _squash_repo(tmp_path, "sqmid", "revert the #42 change")
    mirror = ensure_mirror(origin, tmp_path / "sqmid.git")
    with pytest.raises(GitError, match="#42"):
        resolve_pull_request(mirror, 42)


def test_both_shapes_in_one_repo_resolve_independently(tmp_path, origin):
    merge_sha = git(origin, "rev-parse", "HEAD")  # the #42 merge commit

    (origin / "c.py").write_text("print('squash')\n")
    git(origin, "add", "-A")
    git(origin, "commit", "-qm", "Add c (#7)")
    squash_sha = git(origin, "rev-parse", "HEAD")

    mirror = ensure_mirror(origin, tmp_path / "both.git")

    base42, head42, title42 = resolve_pull_request(mirror, 42)
    assert base42 == git(origin, "rev-parse", f"{merge_sha}^1")
    assert head42 == git(origin, "rev-parse", f"{merge_sha}^2")
    assert "pull request #42" in title42

    base7, head7, title7 = resolve_pull_request(mirror, 7)
    assert base7 == git(origin, "rev-parse", f"{squash_sha}^1")
    assert head7 == squash_sha
    assert title7 == "Add c (#7)"
