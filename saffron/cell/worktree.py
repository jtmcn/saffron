"""The worktree a task edits, on a volume mounted at /work (DESIGN.md §5.1).

Cloned from the bare mirror, which is the cell's only remote — the cell
physically cannot reach the real one. Work happens on the volume, not a bind
mount: macOS bind-mount I/O is slow for the many-small-files pattern of test
collection, and the difference compounds across a four-attempt repair loop.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from saffron.cell import runtime

WORKTREE_MOUNT = "/work"
STATE_MOUNT = "/agent-state"
GATES_MOUNT = "/gates"
_MIRROR_MOUNT = "/mirror"


def mounts(volume: str, state_volume: str, gates_dir: Path) -> list[runtime.Mount]:
    """The mounts every cell gets, and why they are separate.

    Session state and any credential file must not live in the tree the agent
    can write, that the scope gate walks, and that gets patch-exported. The
    gates are read-only and come from a sha the cell never wrote: the
    executables that judge a task are not the ones the task can edit (§5.4).
    """
    return [
        runtime.Mount("volume", volume, WORKTREE_MOUNT),
        runtime.Mount("volume", state_volume, STATE_MOUNT),
        runtime.Mount("bind", str(gates_dir), GATES_MOUNT, readonly=True),
    ]


def prepare_worktree(
    *,
    mirror: Path,
    volume: str,
    base_sha: str,
    branch: str,
    image: str,
    container: str,
    network: str,
    env: Mapping[str, str],
    gates_dir: Path,
    state_volume: str | None = None,
    created: set[str] | None = None,
) -> None:
    """Clone the mirror into the volume at `base_sha` on `branch`, cell running.

    `network`, `env` and `gates_dir` are required, not defaulted: a cell started
    without them joins the runtime's default network with full egress, or falls
    back to the gates in `/work` that the agent can rewrite, and every
    containment control the caller ran applies to some other container (§5.1).

    `created` is the caller's leak ledger: each name is added immediately before
    the call that creates it, so a failure part-way reports what may survive and
    nothing that was never attempted.

    The mirror is bind-mounted read-only for the clone and is not among the
    mounts the cell keeps — a cell that could write the mirror could rewrite
    the history the host is about to read.

    `git clone` refuses a non-empty destination, and a freshly formatted
    volume already has a `lost+found` — init/fetch/checkout in place instead.
    """
    state = state_volume or f"{volume}-state"
    if created is not None:
        created.add(state)
    runtime.create_volume(state)

    seed = runtime.run_ephemeral(
        image,
        [
            "sh",
            "-euc",
            f"cd {WORKTREE_MOUNT} && "
            "git init -q && "
            f"git remote add origin {_MIRROR_MOUNT} && "
            "git fetch -q origin && "
            f"git checkout -q -b {branch} {base_sha} && "
            "git remote remove origin && "
            "git config user.email saffron@localhost && "
            "git config user.name Saffron",
        ],
        mounts=[
            runtime.Mount("bind", str(mirror), _MIRROR_MOUNT, readonly=True),
            runtime.Mount("volume", volume, WORKTREE_MOUNT),
        ],
        timeout_s=600,
    )
    if seed.returncode != 0:
        raise runtime.CellRuntimeError(
            f"seeding the worktree failed: {seed.stderr.strip()}"
        )

    # Here and not at the call site: the seed above is an *ephemeral* container
    # that can fail on a bad base_sha or an unreadable mirror, and recording the
    # cell's name before that reports a container nothing ever created.
    if created is not None:
        created.add(container)
    runtime.run_detached(
        container,
        image,
        command=["sleep", "infinity"],
        network=network,
        env=env,
        mounts=mounts(volume, state, gates_dir),
        cpus=1,
        memory="4g",
    )


# The shape of every diff the host reads, pinned on the command line. Worktree
# config is the agent's to write (§2), and a `-c` override or an explicit flag
# beats `.git/config` — including config it pulls in via `include.path`,
# measured on git 2.50.
DIFF_FLAGS = (
    # diff.srcPrefix/dstPrefix/noprefix/mnemonicPrefix all move the a/ b/ the
    # host matches paths against; these flags win over every one of them.
    "--src-prefix=a/",
    "--dst-prefix=b/",
    # diff.external replaces the diff with whatever program the agent names.
    "--no-ext-diff",
    # A textconv driver renders both sides through a program, so a real edit
    # can come back as no diff at all.
    "--no-textconv",
    # A rename is git's guess at intent; the host needs both paths, or a test
    # renamed into `touches` leaves scope nothing to object to.
    "--no-renames",
)


def _git(container: str, *args: str) -> runtime.Completed:
    # quotePath=false: a path outside ASCII comes back verbatim rather than
    # octal-escaped, which is what `touches` globs are written against.
    # suppressBlankEmpty=false: it strips the leading space from a blank context
    # line, and a diff the host cannot parse is an `error` the agent can set with
    # one uncommitted `git config` (§5.4).
    return runtime.exec_(
        container,
        [
            "git",
            "-c",
            "core.quotePath=false",
            "-c",
            "diff.suppressBlankEmpty=false",
            *args,
        ],
        workdir=WORKTREE_MOUNT,
    )


def commits_ahead(container: str, base_sha: str) -> int:
    """Doneness, measured (DESIGN.md §4.3). Zero means the attempt failed."""
    done = _git(container, "rev-list", "--count", f"{base_sha}..HEAD")
    if done.returncode != 0:
        raise runtime.CellRuntimeError(f"rev-list failed: {done.stderr.strip()}")
    return int(done.stdout.strip().splitlines()[-1])


def head_sha(container: str) -> str:
    done = _git(container, "rev-parse", "HEAD")
    if done.returncode != 0:
        raise runtime.CellRuntimeError(f"rev-parse failed: {done.stderr.strip()}")
    return done.stdout.strip().splitlines()[-1]


def commit_subjects(container: str, base_sha: str) -> list[str]:
    """The agent's own commit subjects, newest first — the only surviving trace
    of them once the squash lands (§5.7)."""
    done = _git(container, "log", "--format=%s", f"{base_sha}..HEAD")
    if done.returncode != 0:
        raise runtime.CellRuntimeError(f"log failed: {done.stderr.strip()}")
    return [line for line in done.stdout.splitlines() if line.strip()]


def export_patch(container: str, base_sha: str) -> str:
    done = _git(container, "diff", *DIFF_FLAGS, f"{base_sha}..HEAD")
    if done.returncode != 0:
        raise runtime.CellRuntimeError(f"diff failed: {done.stderr.strip()}")
    return done.stdout


def read_at_head(container: str, path: str) -> str | None:
    """A file's content at HEAD, or None if there is no such file — what
    anchoring a finding outside a hunk needs (§5.5). Read from git rather than
    the worktree: the agent may have left the tree dirty after its last commit.
    """
    done = _git(container, "show", f"HEAD:{path}")
    return done.stdout if done.returncode == 0 else None


def dirty_paths(container: str) -> list[str]:
    """Paths with uncommitted changes, verbatim, untracked files included."""
    done = _git(container, "status", "--porcelain", "-z", "--untracked-files=all")
    if done.returncode != 0:
        raise runtime.CellRuntimeError(f"status failed: {done.stderr.strip()}")
    chunks = [chunk for chunk in done.stdout.split("\0") if chunk]
    paths: list[str] = []
    index = 0
    while index < len(chunks):
        entry = chunks[index]
        index += 1
        # A rename or copy emits a second NUL-terminated field — the source
        # path — which is not itself an entry.
        if "R" in entry[:2] or "C" in entry[:2]:
            index += 1
        paths.append(entry[3:])
    return sorted(paths)


def changed_files(container: str, base_sha: str) -> list[str]:
    """Changed paths, verbatim — they are matched against `touches`.

    `-z` for the same reason `repos.mirror` uses it: a path holding a newline
    would otherwise arrive as two paths.
    """
    done = _git(
        container, "diff", *DIFF_FLAGS, "--name-only", "-z", f"{base_sha}..HEAD"
    )
    if done.returncode != 0:
        raise runtime.CellRuntimeError(f"diff --name-only failed: {done.stderr}")
    return [path for path in done.stdout.split("\0") if path.strip()]
