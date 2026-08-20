"""Build a repo's cell image from its .saffron/Dockerfile (DESIGN.md §2.1).

Core's only involvement in a repo's toolchain is rebuilding this when the
Dockerfile changes. It never installs anything on a repo's behalf.
"""

from __future__ import annotations

import re
from pathlib import Path

from saffron.cell import runtime

# What a repo's .saffron/Dockerfile builds FROM. Never what a cell runs: it
# carries no toolchain, so every gate would error before the agent is reached.
BASE_TAG = "saffron/cell-base:python"


def cell_tag(repo: Path) -> str:
    """The image a cell of this repo runs (§5.1's `saffron/cell:<repo>`).

    A tag is `[A-Za-z0-9_.-]`; a directory name is not (a git worktree named
    `joel+branch` would otherwise build an image that cannot be referenced).
    """
    return "saffron/cell:" + re.sub(r"[^A-Za-z0-9_.-]", "-", repo.name)


def _build_argv(dockerfile: Path, tag: str, context: Path) -> list[str]:
    return [
        runtime.RUNTIME,
        "build",
        "-t",
        tag,
        "-f",
        str(dockerfile),
        str(context),
    ]


def build_image(dockerfile: Path, tag: str, context: Path) -> None:
    """Build one image, or raise. A failed build is an infrastructure failure."""
    done = runtime.call(_build_argv(dockerfile, tag, context), timeout_s=1800)
    if done.returncode != 0:
        raise runtime.CellRuntimeError(
            f"building {tag} failed:\n{done.stderr.strip() or done.stdout.strip()}"
        )


def build_cell_image(repo: Path) -> str:
    """Build the repo's cell image from its own Dockerfile and return the tag."""
    dockerfile = repo / ".saffron" / "Dockerfile"
    if not dockerfile.is_file():
        raise runtime.CellRuntimeError(
            f"no {dockerfile} — a repo declares its own toolchain, core never "
            "installs one on its behalf (§2.1)"
        )
    tag = cell_tag(repo)
    build_image(dockerfile, tag, repo)
    return tag
