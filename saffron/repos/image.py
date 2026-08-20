"""Build a repo's cell image from its .saffron/Dockerfile (DESIGN.md §2.1).

Core's only involvement in a repo's toolchain is rebuilding this when the
Dockerfile changes. It never installs anything on a repo's behalf.
"""

from __future__ import annotations

from pathlib import Path

from saffron.cell import runtime

BASE_TAG = "saffron/cell-base:python"


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


def image_exists(tag: str) -> bool:
    done = runtime.call([runtime.RUNTIME, "image", "inspect", tag], timeout_s=60)
    return done.returncode == 0
