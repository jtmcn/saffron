"""The local bare mirror, and worktrees cut from it.

The mirror is the only remote anything downstream ever reads (DESIGN.md §5.1).
v0 has no cell to enforce that against — it establishes the property because it
is free now and expensive later.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tarfile
from pathlib import Path

_ADDED = re.compile(r"(\d+) insertions?\(\+\)")
_REMOVED = re.compile(r"(\d+) deletions?\(-\)")

# The marker convention (`SA-0027`, docs/BACKLOG.md item 34): a comment or
# docstring carrying `saffron:retired-by <SPEC-ID>` declares that its file
# asserts something the named spec is expected to falsify — a half-wired
# capability's note to its own successor. Opt-in: a heuristic over every
# `SA-NNNN` mention would refuse most of this repository, which cites spec
# ids as attribution far more often than as a claim about the future.
_RETIREMENT_MARKER = "saffron:retired-by"
_RETIREMENT_SPEC_ID = re.compile(r"saffron:retired-by\s+([A-Za-z0-9]+-[0-9]+)")


class GitError(RuntimeError):
    """A git invocation that did not do what was asked."""


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a git command, wrapping a missing `git` binary as GitError too."""
    try:
        return subprocess.run(args, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise GitError(f"{' '.join(args)}: {exc}") from exc


def _git(repo: Path, *args: str, strip: bool = True) -> str:
    completed = _run(["git", "-C", str(repo), *args])
    if completed.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {completed.stderr.strip()}")
    # strip=False for NUL-delimited output, where a leading or trailing space
    # is part of a filename rather than padding.
    return completed.stdout.strip() if strip else completed.stdout


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
    # Both anchors are matched in Python rather than by git's --grep: `^` and
    # `$` in a --grep regex match per *line* of the commit message, so a merge
    # whose body quotes another merge's subject matches the prefix too, and
    # "(#4)" matches a subject ending "(#42)".
    merge_prefix = f"Merge pull request #{number} from "
    squash_suffix = f"(#{number})"
    entries = [
        line.split("\x1f", 2)
        for line in _git(mirror, "log", "--all", "--format=%H\x1f%P\x1f%s").splitlines()
        if line
    ]

    for sha, parents, subject in entries:
        if len(parents.split()) > 1 and subject.startswith(merge_prefix):
            base = _git(mirror, "merge-base", f"{sha}^1", f"{sha}^2")
            return base, _git(mirror, "rev-parse", f"{sha}^2"), subject

    for sha, _, subject in entries:
        if subject.endswith(squash_suffix):
            return _git(mirror, "rev-parse", f"{sha}^1"), sha, subject

    raise GitError(f"no merge or squash commit for pull request #{number} in {mirror}")


def add_worktree(mirror: Path, sha: str, dest: Path) -> Path:
    # --force covers a stale registration, not an existing directory: git dies
    # on the path before it looks at the registry. A worktree left behind by a
    # killed process would otherwise wedge every later add at the same path.
    shutil.rmtree(dest, ignore_errors=True)
    _git(mirror, "worktree", "prune")
    _git(mirror, "worktree", "add", "--detach", "--force", str(dest), sha)
    return dest


def remove_worktree(mirror: Path, dest: Path) -> None:
    _git(mirror, "worktree", "remove", "--force", str(dest))


def changed_files(mirror: Path, base: str, head: str) -> list[str]:
    """Changed paths, verbatim — they are matched against `touches`.

    git quotes and octal-escapes any path outside plain ASCII by default, and
    `"src/caf\303\251.py"` matches no glob a human wrote. -z also keeps a
    newline in a path from splitting into two entries.
    """
    output = _git(
        mirror,
        "-c",
        "core.quotePath=false",
        "diff",
        "--name-only",
        "-z",
        f"{base}..{head}",
        strip=False,
    )
    return [path for path in output.split("\0") if path]


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


def export_saffron_dir(mirror: Path, sha: str, dest: Path) -> Path:
    """`.saffron/` as it stood at `sha`, on the host.

    The cell reads its gates from here rather than from `/work`, so an in-cell
    edit — committed or not — cannot reach the runner (§5.4). `git archive`
    carries the mode bits, and a gate that is not executable reads identically
    to one that was never declared.

    The whole directory, not `gates/` alone: the policy *declaring* the gates
    has to come from the same commit as the executables, or the two diverge on
    any branch that touches `.saffron/`. It also lets a repo that has not added
    `gates/` yet export at all — `git archive` fails on an unmatched pathspec,
    which made adding a repo's first gate an exit-2 infrastructure failure.
    """
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    archive = dest / "gates.tar"
    # subprocess.run, not _run: stdout goes to a file rather than a pipe, so a
    # missing git binary raises OSError here rather than the module's GitError.
    with archive.open("wb") as sink:
        done = subprocess.run(
            [
                "git",
                "-C",
                str(mirror),
                "archive",
                "--format=tar",
                sha,
                ".saffron",
            ],
            stdout=sink,
            stderr=subprocess.PIPE,
            check=False,
        )
    if done.returncode != 0:
        detail = done.stderr.decode(errors="replace").strip()
        raise GitError(f"git archive {sha[:12]} .saffron: {detail}")
    with tarfile.open(archive) as tar:
        # filter="data" clears setuid/setgid/sticky and group-and-other write,
        # and keeps the execute bit the gate needs.
        tar.extractall(dest, filter="data")
    archive.unlink()

    if not (dest / ".saffron").is_dir():
        raise GitError(f"{sha[:12]} has no .saffron for the cell to run")
    return dest


def retirement_markers(mirror: Path, sha: str) -> list[tuple[str, str]]:
    """Every `saffron:retired-by <SPEC-ID>` marker at `sha`, read straight
    from the bare mirror — no export, no checkout, no working tree.

    `git grep -n -z` against the tree-ish directly: `-z` NUL-delimits the
    path, line number and matched text within one match (the same reason
    `changed_files` passes `-z` — a path carrying a colon must not be misread
    as a field boundary), while matches stay newline-separated so several
    hits parse apart cleanly.

    A mirror with no markers is `[]`, never an error: `git grep` exits 1 on
    no match, a fact about the tree, not a broken command — `error` ≠ `fail`,
    read onto a gathering step rather than a gate. Exit codes past 1 (a bad
    revision, a corrupt mirror) still raise, the same as every other call in
    this module.
    """
    argv = ["git", "-C", str(mirror), "-c", "core.quotePath=false"]
    argv += ["grep", "-n", "-z", "-e", _RETIREMENT_MARKER, sha]
    completed = _run(argv)
    if completed.returncode == 1:
        return []
    if completed.returncode != 0:
        raise GitError(
            f"git grep {_RETIREMENT_MARKER!r} {sha[:12]}: {completed.stderr.strip()}"
        )

    prefix = f"{sha}:"
    pairs: list[tuple[str, str]] = []
    for record in completed.stdout.split("\n"):
        if not record:
            continue
        fields = record.split("\0")
        if len(fields) != 3:
            continue
        path = fields[0].removeprefix(prefix)
        found = _RETIREMENT_SPEC_ID.search(fields[2])
        if found is not None:
            pairs.append((path, found.group(1)))
    return pairs
