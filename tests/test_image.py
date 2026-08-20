from __future__ import annotations

import pytest

from saffron.cell import runtime
from saffron.repos import image


def test_build_argv_names_the_dockerfile_and_tag(tmp_path):
    argv = image._build_argv(tmp_path / "D", "saffron/cell-base:python", tmp_path)
    assert argv[:2] == ["container", "build"]
    assert "-t" in argv and "saffron/cell-base:python" in argv
    assert "-f" in argv and str(tmp_path / "D") in argv
    assert argv[-1] == str(tmp_path)


@pytest.mark.cell
def test_base_image_has_git_and_the_agent_runtime():
    done = runtime.run_ephemeral(image.BASE_TAG, ["git", "--version"])
    assert done.returncode == 0, done.stderr
    done = runtime.run_ephemeral(
        image.BASE_TAG, ["python", "-c", "import claude_agent_sdk"]
    )
    assert done.returncode == 0, done.stderr


@pytest.mark.cell
def test_the_cell_sees_only_the_cpus_it_has():
    """The requirement §5.1 states, with the offset Appendix G measured."""
    assert runtime.visible_cpus(image.BASE_TAG, 1) == 1 + runtime.CPU_OFFSET
