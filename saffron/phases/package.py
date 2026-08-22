"""PACKAGE — a green cell becomes a branch, a draft PR and a queue line (§5.7).

Host-side, no model, and no cell except the gate-only one part 3 of the spec
describes. It runs after the cell is torn down: the host should not be talking
to the real remote while an untrusted container is alive.

No named remote is ever added to the mirror, and no long-lived ref is created.
`mirror.ensure_mirror` fetches `+refs/*:refs/*` with `--prune`, so any ref left
behind that the local repo does not have is deleted on the next run — including
a branch this module just created.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

_SLUG = re.compile(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$")

APPLY_OK = "ok"
APPLY_CONFLICT = "conflict"

# Measured on git 2.50.1 (Apple Git-155). Both of these appear on stderr while
# git exits 0, which is why neither the exit code nor the output alone decides.
_NO_BLOB = "lacks the necessary blob"
_NO_FULL_INDEX = "without full index line"

# ponytail: a refusal, not the `secrets` gate (§5.4) — that is v1's to build.
# The ceiling is named in DESIGN.md §5.7: every credential shape not listed here
# still reaches the remote, and the upgrade path is the gate, not more regexes.
_CREDENTIAL_SHAPES = (
    ("an Anthropic API key", re.compile(r"sk-ant-api\d{2}-[A-Za-z0-9_\-]{16,}")),
    ("an Anthropic OAuth token", re.compile(r"sk-ant-oat\d{2}-[A-Za-z0-9_\-]{8,}")),
    ("a GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{16,}")),
    ("an AWS access key id", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("a private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
)

_CLOSES = re.compile(
    r"\b(clos(e|es|ed)|fix(es|ed)?|resolv(e|es|ed))\b(?=\s*:?\s*#\d)",
    re.IGNORECASE,
)
_MENTION = re.compile(r"(?<![\w/])@(?=\w)")


class PackageError(RuntimeError):
    """Infrastructure. Raised, caught by `cli.main`, exits 2 (§3.3)."""


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Every git call here inspects `returncode` *and* `stderr` — see
    `apply_patch`, where a zero exit does not mean what it looks like."""
    try:
        return subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise PackageError(f"git {' '.join(args)}: {exc}") from exc


def real_remote(repo: Path) -> str:
    """The URL a pull request is opened against — never the mirror's source."""
    done = _run(repo, "remote", "get-url", "origin")
    if done.returncode != 0 or not done.stdout.strip():
        raise PackageError(
            f"{repo} has no 'origin' remote, so there is nowhere to open a pull request"
        )
    return done.stdout.strip()


def github_slug(url: str) -> str:
    """`owner/repo`, from either URL shape git writes."""
    if not (found := _SLUG.search(url)):
        raise PackageError(f"cannot read owner/repo out of {url!r}")
    return f"{found.group(1)}/{found.group(2)}"


def default_branch(url: str, *, cwd: Path) -> str:
    """What the remote says HEAD points at. Not hardcoded `main`."""
    done = _run(cwd, "ls-remote", "--symref", url, "HEAD")
    if done.returncode != 0:
        raise PackageError(f"cannot reach {url}: {done.stderr.strip()[:200]}")
    for line in done.stdout.splitlines():
        if line.startswith("ref: "):
            return line.removeprefix("ref: ").split("\t")[0].removeprefix("refs/heads/")
    raise PackageError(f"{url} reported no symbolic HEAD")


def assert_base_objects(mirror: Path, base_sha: str) -> None:
    """Refuse to apply against a mirror missing the patch's preimage.

    Without this, `--3way` degrades to a context match and reports success —
    see `apply_patch`. Checked up front so the failure names its cause.
    """
    done = _run(mirror, "cat-file", "-e", f"{base_sha}^{{tree}}")
    if done.returncode != 0:
        raise PackageError(
            f"mirror {mirror} lacks the objects for base {base_sha[:12]}, so a "
            "three-way merge cannot be performed"
        )


def apply_patch(worktree: Path, patch: Path) -> str:
    """Apply the cell's squashed patch. §5.7's rebase, one commit long.

    Two measured hazards, and the exit code alone catches neither:

    - A **conflicting** apply exits 1 *and writes the file*, with `<<<<<<<`
      markers and a staged `U` entry. Non-zero is APPLY_CONFLICT and the
      worktree must be discarded unread — never committed.
    - A **degraded** apply exits **0**: with the preimage blob absent and the
      hunk's context matching, git falls back to direct application and
      succeeds. That is `error`, not `pass` — the toolchain, charged to nobody.
    """
    if not patch.is_file():
        raise PackageError(f"no patch at {patch}: there is nothing to package")
    done = _run(worktree, "apply", "--3way", "--index", str(patch))
    stderr = done.stderr
    if _NO_FULL_INDEX in stderr:
        raise PackageError(
            "the patch carries a binary change with no full index line, so it "
            "was never appliable — not a conflict"
        )
    if _NO_BLOB in stderr:
        raise PackageError(
            "git fell back to direct application: the preimage blob is absent, "
            "so no three-way merge happened and a clean exit would mean only "
            "that the context matched"
        )
    return APPLY_OK if done.returncode == 0 else APPLY_CONFLICT


def _added_lines(patch_text: str) -> list[tuple[str, str]]:
    """(path, added line) for every `+` line. A credential removed by the patch
    is already in history and is not this push's doing."""
    path, out = "?", []
    for line in patch_text.splitlines():
        if line.startswith("+++ b/"):
            path = line.removeprefix("+++ b/")
        elif line.startswith("+") and not line.startswith("+++"):
            out.append((path, line[1:]))
    return out


def find_credentials(patch_text: str, *, token: str | None) -> list[str]:
    """Describe every credential the patch would push. Never returns the value.

    The literal token is checked first and separately: it is the one secret we
    know is in the cell, so a miss there is not a heuristic failure.
    """
    found = []
    for path, line in _added_lines(patch_text):
        if token and len(token) > 8 and token in line:
            found.append(f"{path}: the cell's own CLAUDE_CODE_OAUTH_TOKEN")
            continue
        for what, pattern in _CREDENTIAL_SHAPES:
            if pattern.search(line):
                found.append(f"{path}: {what}")
                break
    return found


def neutralize(text: str) -> str:
    """Defang model-authored text before it reaches GitHub.

    GitHub closes an issue named by `Fixes #12` in a commit body *and* in a pull
    request body, and `@name` notifies a real account. This is the one place a
    cell's output causes an effect outside the boundary without executing (§2).
    """
    return _MENTION.sub(
        "@​", _CLOSES.sub(lambda m: m.group(0)[:1] + "​" + m.group(0)[1:], text)
    )
