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


def test_the_cell_image_is_named_for_the_repo(tmp_path):
    """A cell runs `saffron/cell:<repo>` (§5.1), never the toolchain-free base."""
    assert image.cell_tag(tmp_path / "thermal-edge") == "saffron/cell:thermal-edge"
    # A worktree directory name is not a legal tag.
    assert image.cell_tag(tmp_path / "joel+v0.5") == "saffron/cell:joel-v0.5"


def test_building_a_cell_image_without_a_dockerfile_is_an_error(tmp_path):
    with pytest.raises(runtime.CellRuntimeError):
        image.build_cell_image(tmp_path)
