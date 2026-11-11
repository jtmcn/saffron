"""Build a repo's cell image from its .saffron/Dockerfile (DESIGN.md §2.1).

Core's only involvement in a repo's toolchain is rebuilding this when the
Dockerfile changes. It never installs anything on a repo's behalf.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from saffron.cell import runtime

# What a repo's .saffron/Dockerfile builds FROM. Never what a cell runs: it
# carries no toolchain, so every gate would error before the agent is reached.
BASE_TAG = "saffron/cell-base:python"
_SAFFRON_ROOT = Path(__file__).resolve().parents[2]
BASE_DOCKERFILE = _SAFFRON_ROOT / "images" / "cell-base.python.Dockerfile"
# A host with no registry names its own base (§5.1.2): declared, never detected.
BASE_IMAGE_ENV = "SAFFRON_BASE_IMAGE"


# A local git read, bounded so a wedged git never stalls a cell's start.
ORIGIN_TIMEOUT_S = 30.0


def _origin_name(repo: Path) -> str | None:
    """The last segment of `repo`'s git `origin`, or None with no usable one."""
    try:
        done = subprocess.run(
            ["git", "-C", str(repo), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=ORIGIN_TIMEOUT_S,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode != 0:
        return None
    url = done.stdout.strip()
    if not url:
        return None
    if url.endswith("/"):
        url = url[:-1]
    if url.endswith(".git"):
        url = url[: -len(".git")]
    cut = max(url.rfind("/"), url.rfind(":"))
    name = url[cut + 1 :]
    return name or None


def cell_tag(repo: Path) -> str:
    """The image a cell of this repo runs (§5.1's `saffron/cell:<repo>`).

    Named for `repo`'s git `origin` when it has one. Every git worktree of one
    repo then builds one cell image instead of one each (backlog b-2bc0d5). A
    repo with no origin, or no git at all, keeps its directory name.

    A tag is `[A-Za-z0-9_.-]`. A directory name is not, and neither is an
    origin's last segment. A git worktree named `joel+branch`, or an origin ending
    `joel+v0.5.git`, would otherwise build a tag no runtime can reference.
    """
    name = _origin_name(repo) or repo.name
    return "saffron/cell:" + re.sub(r"[^A-Za-z0-9_.-]", "-", name)


def _build_argv(
    dockerfile: Path, tag: str, context: Path, build_args: dict[str, str] | None = None
) -> list[str]:
    args = [f"--build-arg={k}={v}" for k, v in (build_args or {}).items()]
    return [
        runtime.RUNTIME,
        "build",
        "-t",
        tag,
        "-f",
        str(dockerfile),
        *args,
        str(context),
    ]


def build_image(
    dockerfile: Path, tag: str, context: Path, build_args: dict[str, str] | None = None
) -> None:
    """Build one image, or raise. A failed build is an infrastructure failure."""
    argv = _build_argv(dockerfile, tag, context, build_args)
    done = runtime.call(argv, timeout_s=1800)
    if done.returncode != 0:
        raise runtime.CellRuntimeError(
            f"building {tag} failed:\n{done.stderr.strip() or done.stdout.strip()}"
        )


def build_base_image() -> None:
    """Rebuild core's base from this checkout, so a changed `agent_runner.py`
    reaches the next cell. Cached, it costs about 5 s (measured 2026-09-19)."""
    base = os.environ.get(BASE_IMAGE_ENV)
    build_args = {"BASE_IMAGE": base} if base else None
    build_image(BASE_DOCKERFILE, BASE_TAG, _SAFFRON_ROOT, build_args)


def build_cell_image(repo: Path) -> str:
    """Build the base, then the repo's cell image from its own Dockerfile, and
    return the tag."""
    dockerfile = repo / ".saffron" / "Dockerfile"
    if not dockerfile.is_file():
        raise runtime.CellRuntimeError(
            f"no {dockerfile} — a repo declares its own toolchain, core never "
            "installs one on its behalf (§2.1)"
        )
    build_base_image()
    tag = cell_tag(repo)
    build_image(dockerfile, tag, repo)
    return tag
