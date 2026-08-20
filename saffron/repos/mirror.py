"""The local bare mirror, and worktrees cut from it.

The mirror is the only remote anything downstream ever reads (DESIGN.md §5.1).
v0 has no cell to enforce that against — it establishes the property because it
is free now and expensive later.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

_ADDED = re.compile(r"(\d+) insertions?\(\+\)")
_REMOVED = re.compile(r"(\d+) deletions?\(-\)")


class GitError(RuntimeError):
    """A git invocation that did not do what was asked."""


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a git command, wrapping a missing `git` binary as GitError too."""
    try:
        return subprocess.run(args, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise GitError(f"{' '.join(args)}: {exc}") from exc


def _git(repo: Path, *args: str) -> str:
    completed = _run(["git", "-C", str(repo), *args])
    if completed.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {completed.stderr.strip()}")
    return completed.stdout.strip()


def ensure_mirror(origin: Path | str, mirror_path: Path) -> Path:
    """Create the bare mirror if absent, fetch it if present."""
    if mirror_path.is_dir():
        _git(mirror_path, "fetch", "--prune", "origin", "+refs/*:refs/*")
        return mirror_path

    mirror_path.parent.mkdir(parents=True, exist_ok=True)
    completed = _run(["git", "clone", "--mirror", str(origin), str(mirror_path)])
    if completed.returncode != 0:
        raise GitError(f"git clone --mirror: {completed.stderr.strip()}")
    return mirror_path


def resolve_pull_request(mirror: Path, number: int) -> tuple[str, str, str]:
    """Find a merged pull request's base and head.

    Two shapes exist in the wild, both offline (`git log` against the bare
    mirror, no API call, no credential, no network):

    - merge commit: subject "Merge pull request #N from ...". `^2` is the
      head that was merged; the base is the *merge base* of the two parents,
      not `^1`. `^1` is main at merge time, so where main advanced while the
      pull request was open it drags main's own commits into the diff and
      into the baseline. Tried first — it names base and head unambiguously,
      where a squash subject is just a number that happens to sit at the end
      of a string.
    - squash commit: subject ending "(#N)". The commit itself *is* the head;
      its sole parent is the base — which for a squash *is* the merge base.
    """
    merge_pattern = f"^Merge pull request #{number} from "
    merge = _git(
        mirror, "log", "--merges", "--grep", merge_pattern, "-E", "--format=%H", "-n", "1", "--all"
    )
    if merge:
        title = _git(mirror, "log", "--format=%s", "-n", "1", merge)
        base = _git(mirror, "merge-base", f"{merge}^1", f"{merge}^2")
        return base, _git(mirror, "rev-parse", f"{merge}^2"), title

    # Anchored in Python, not git's --grep, so "(#4)" can't match a subject
    # ending "(#42)" and "(#42)" can't match one ending "(#142)" — a regex
    # with $ inside a multi-line commit message is not worth trusting for this.
    squash_suffix = f"(#{number})"
    log = _git(mirror, "log", "--all", "--format=%H\x1f%s")
    for line in log.splitlines():
        sha, _, subject = line.partition("\x1f")
        if subject.endswith(squash_suffix):
            return _git(mirror, "rev-parse", f"{sha}^1"), sha, subject

    raise GitError(f"no merge or squash commit for pull request #{number} in {mirror}")


def add_worktree(mirror: Path, sha: str, dest: Path) -> Path:
    _git(mirror, "worktree", "add", "--detach", "--force", str(dest), sha)
    return dest


def remove_worktree(mirror: Path, dest: Path) -> None:
    _git(mirror, "worktree", "remove", "--force", str(dest))


def changed_files(mirror: Path, base: str, head: str) -> list[str]:
    output = _git(mirror, "diff", "--name-only", f"{base}..{head}")
    return output.splitlines() if output else []


def diff_stat(mirror: Path, base: str, head: str) -> tuple[int, int]:
    """Added and removed line counts, for the queue line.

    Two searches rather than one optional-group pattern: every group in the
    combined form is optional, so it matches the empty string at position 0
    and reports (0, 0) for every diff.
    """
    summary = _git(mirror, "diff", "--shortstat", f"{base}..{head}")
    added = _ADDED.search(summary)
    removed = _REMOVED.search(summary)
    return (
        int(added.group(1)) if added else 0,
        int(removed.group(1)) if removed else 0,
    )
