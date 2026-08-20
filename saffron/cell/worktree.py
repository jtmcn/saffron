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
_MIRROR_MOUNT = "/mirror"


def mounts(volume: str, state_volume: str) -> list[runtime.Mount]:
    """The two volumes every cell gets, and why they are two.

    Session state and any credential file must not live in the tree the agent
    can write, that the scope gate walks, and that gets patch-exported.
    """
    return [
        runtime.Mount("volume", volume, WORKTREE_MOUNT),
        runtime.Mount("volume", state_volume, STATE_MOUNT),
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
    state_volume: str | None = None,
) -> None:
    """Clone the mirror into the volume at `base_sha` on `branch`, cell running.

    `network` and `env` are required, not defaulted: a cell started without them
    joins the runtime's default network with full egress, and every containment
    control the caller ran applies to some other container (§5.1).

    The mirror is bind-mounted read-only for the clone and is not among the
    mounts the cell keeps — a cell that could write the mirror could rewrite
    the history the host is about to read.

    `git clone` refuses a non-empty destination, and a freshly formatted
    volume already has a `lost+found` — init/fetch/checkout in place instead.
    """
    state = state_volume or f"{volume}-state"
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

    runtime.run_detached(
        container,
        image,
        command=["sleep", "infinity"],
        network=network,
        env=env,
        mounts=mounts(volume, state),
        cpus=1,
        memory="4g",
    )


def _git(container: str, *args: str) -> runtime.Completed:
    return runtime.exec_(container, ["git", *args], workdir=WORKTREE_MOUNT)


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


def export_patch(container: str, base_sha: str) -> str:
    done = _git(container, "diff", f"{base_sha}..HEAD")
    if done.returncode != 0:
        raise runtime.CellRuntimeError(f"diff failed: {done.stderr.strip()}")
    return done.stdout


def changed_files(container: str, base_sha: str) -> list[str]:
    done = _git(container, "diff", "--name-only", f"{base_sha}..HEAD")
    if done.returncode != 0:
        raise runtime.CellRuntimeError(f"diff --name-only failed: {done.stderr}")
    return [line for line in done.stdout.splitlines() if line.strip()]
