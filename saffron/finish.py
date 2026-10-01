"""The stack batch's finishing layer commit (ADR 7).

Reads a batch's layers and every spec text it will write. Checks each one
before touching git, then commits them atop the top layer's own head. No
ref moves and no gate executes here: that is `SA-0167`'s own job.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from pathlib import Path

from saffron.intake import discover_specs
from saffron.ledger import Ledger
from saffron.repos import mirror as git_mirror
from saffron.scheduler import RETIRED_DIRNAME

# A text's own path, exactly: under `.saffron/specs/`, one segment, `.md`.
# One pattern, so `.saffron/specs/done/x.md` is refused too (ADR 7).
_SPEC_PATH_RE = re.compile(r"\A\.saffron/specs/[^/]+\.md\Z")


def _checked(row) -> tuple[str, str]:
    path = row["path"]
    if _SPEC_PATH_RE.match(path) is None:
        raise ValueError(
            f"spec text path {path!r} is not a .md file directly in .saffron/specs/"
        )
    text = row["text"]
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != row["spec_sha"]:
        raise ValueError(f"spec text for {row['spec_id']!r} does not match its hash")
    return path, text


def commit_finish(
    ledger: Ledger,
    batch_id: int,
    unrun: list[int],
    *,
    mirror: Path,
    workdir: Path,
    emit: Callable[[str], None] = print,
) -> str | None:
    """One commit in `mirror`, atop the top layer's recorded `pushed_sha`.

    Writes each layer's and each task in `unrun`'s latest spec text, then
    retires each layer's file into `done/`. Returns the new sha, or `None`
    for a batch with no layer or a tree the writes left unchanged."""
    layers = ledger.stack_layers(batch_id)
    if not layers:
        return None
    top = layers[-1]
    if top["pushed_sha"] is None:
        raise ValueError(f"top layer {top['spec_id']!r} has no pushed_sha")

    pending: list[tuple[str, str]] = []
    for layer in layers:
        row = ledger.spec_text(layer["task_id"])
        if row is not None:
            pending.append(_checked(row))
    for task_id in unrun:
        row = ledger.spec_text(task_id)
        if row is None:
            emit(f"finish: task {task_id} has no spec text")
            continue
        pending.append(_checked(row))

    git_mirror.add_worktree(mirror, top["pushed_sha"], workdir)
    try:
        for path, text in pending:
            (workdir / path).write_text(text)
        specs_dir = workdir / ".saffron" / "specs"
        discovered, _failures = discover_specs(specs_dir)
        by_id = {d.spec.id: d.path for d in discovered}
        done_dir = specs_dir / RETIRED_DIRNAME
        done_dir.mkdir(exist_ok=True)
        for layer in layers:
            found = by_id.get(layer["spec_id"])
            if found is not None:
                found.rename(done_dir / found.name)

        _run_git(workdir, "add", "-A")
        unchanged = _run_git(workdir, "diff", "--cached", "--quiet")
        if unchanged.returncode == 0:
            return None
        done = _run_git(
            workdir,
            "-c",
            "user.email=saffron@localhost",
            "-c",
            "user.name=Saffron",
            "commit",
            "-q",
            "-m",
            f"saffron batch {batch_id}: finishing layer",
        )
        if done.returncode != 0:
            raise git_mirror.GitError(f"commit failed: {done.stderr.strip()[:200]}")
        return _run_git(workdir, "rev-parse", "HEAD").stdout.strip()
    finally:
        git_mirror.remove_worktree(mirror, workdir)


def _run_git(cwd: Path, *args: str):
    return git_mirror._run(["git", "-C", str(cwd), *args])
