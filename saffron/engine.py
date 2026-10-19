"""The engine commit that judged a task (ADR 10, `DESIGN.md` §4.1).

A target repo never ships the engine (ADR 10), so this module answers one
question for whichever engine is running: what commit of itself is this. A
build bakes `ENGINE_COMMIT` beside `saffron/__init__.py`. With no such file,
the answer comes from the checkout the engine happens to run from.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    """One git call, or `None` for anything that is not a clean answer: a
    non-zero exit, or git missing outright. Never raises."""
    try:
        done = subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    return done if done.returncode == 0 else None


def _checkout_head(parent: Path) -> str | None:
    """The full `HEAD` of the checkout whose top level is `parent`, or
    `None` when `parent` is not one, or holds no commit yet."""
    toplevel = _git(parent, "rev-parse", "--show-toplevel")
    if toplevel is None:
        return None
    if Path(toplevel.stdout.strip()).resolve() != parent.resolve():
        return None
    head = _git(parent, "rev-parse", "--verify", "HEAD")
    if head is None:
        return None
    sha = head.stdout.strip()
    if not sha:
        return None
    # `--no-optional-locks`: a plain `status` rewrites the index once a
    # tracked file's mtime moves, and that index is not this process's own.
    status = _git(
        parent, "--no-optional-locks", "status", "--porcelain", "--untracked-files=no"
    )
    if status is None:
        return None
    return f"{sha}-dirty" if status.stdout.strip() else sha


def engine_commit(source: str | Path | None = None) -> str | None:
    """The commit of the engine itself, never the target repo.

    Reads `ENGINE_COMMIT` in `source` first, stripped, treating a blank file
    as no file. With none, asks git about the checkout whose top level is
    `source`'s parent, returning its `HEAD` marked `-dirty` on a tracked
    change. `None` when neither answers. `source` defaults to the directory
    holding this module, read from `__file__` at call time rather than
    frozen at import, so a test can relocate it.
    """
    source = Path(__file__).resolve().parent if source is None else Path(source)
    baked = source / "ENGINE_COMMIT"
    if baked.is_file():
        text = baked.read_text().strip()
        if text:
            return text
    return _checkout_head(source.parent)
