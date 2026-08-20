from __future__ import annotations

import subprocess

import pytest

from saffron.cell import runtime, worktree
from saffron.repos import image


def _seed_repo(path):
    path.mkdir(parents=True, exist_ok=True)
    run = lambda *a: subprocess.run(a, cwd=path, check=True, capture_output=True)  # noqa: E731
    run("git", "init", "-q", "-b", "main")
    run("git", "config", "user.email", "t@example.com")
    run("git", "config", "user.name", "t")
    (path / "a.txt").write_text("one\n")
    run("git", "add", "a.txt")
    run("git", "commit", "-qm", "first")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True
    ).stdout.strip()


@pytest.mark.cell
def test_a_worktree_is_cloned_into_a_volume_and_the_cell_can_commit(tmp_path):
    origin = tmp_path / "origin"
    base = _seed_repo(origin)
    mirror = tmp_path / "m.git"
    subprocess.run(
        ["git", "clone", "--bare", "-q", str(origin), str(mirror)], check=True
    )

    volume = "saffron-test-wt"
    runtime.remove_volume(volume)
    runtime.create_volume(volume)
    container = "saffron-test-cell"
    runtime.remove_container(container)
    try:
        worktree.prepare_worktree(
            mirror=mirror,
            volume=volume,
            base_sha=base,
            branch="saffron/test",
            image=image.BASE_TAG,
            container=container,
        )
        assert worktree.commits_ahead(container, base) == 0

        runtime.exec_(container, ["sh", "-c", "echo two >> a.txt"], workdir="/work")
        runtime.exec_(container, ["git", "add", "a.txt"], workdir="/work")
        runtime.exec_(container, ["git", "commit", "-qm", "second"], workdir="/work")

        assert worktree.commits_ahead(container, base) == 1
        patch = worktree.export_patch(container, base)
        assert "two" in patch
    finally:
        runtime.remove_container(container)
        runtime.remove_volume(volume)


@pytest.mark.cell
def test_the_cell_cannot_reach_the_real_remote(tmp_path):
    """The mirror is the only remote a cell has (DESIGN.md §5.1)."""
    origin = tmp_path / "origin"
    base = _seed_repo(origin)
    mirror = tmp_path / "m.git"
    subprocess.run(
        ["git", "clone", "--bare", "-q", str(origin), str(mirror)], check=True
    )
    volume, container = "saffron-test-wt2", "saffron-test-cell2"
    runtime.remove_volume(volume)
    runtime.create_volume(volume)
    runtime.remove_container(container)
    try:
        worktree.prepare_worktree(
            mirror=mirror,
            volume=volume,
            base_sha=base,
            branch="saffron/test",
            image=image.BASE_TAG,
            container=container,
        )
        remotes = runtime.exec_(container, ["git", "remote", "-v"], workdir="/work")
        assert "origin" not in remotes.stdout
    finally:
        runtime.remove_container(container)
        runtime.remove_volume(volume)
