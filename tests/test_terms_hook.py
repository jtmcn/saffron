"""Witnesses for the `terms` hook (backlog item b-1e106d).

The `terms` gate ran over the whole tree only inside a cell, where
baseline subtraction hides a failure already on `main`. These tests run the
hook's own `entry`, split the way prek and `sh -c` split it. They run it
against disposable trees under `tmp_path`, never against this repo's own
tree.

`prose.py` is loaded by path inside the test that needs it, as
`tests/test_prose_gate.py` loads it.
"""

from __future__ import annotations

import importlib.util
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
GATES = REPO / ".saffron" / "gates"

CLEAN_README = "The agent runs in a cell.\n"
# Built as a plain string, never a comment or docstring: the `terms` gate
# reads this file's own comments and docstrings, not its string literals.
HIT_README = "The agent runs in a sandbox.\n"
HIT_DOCSTRING = 'class Bypass:\n    """Runs the task outside its sandbox."""\n'


def _hook_config() -> dict:
    """The `terms` hook, read from the file prek reads."""
    config = yaml.safe_load((REPO / ".pre-commit-config.yaml").read_text())
    hooks = [hook for repo in config["repos"] for hook in repo["hooks"]]
    (found,) = [hook for hook in hooks if hook["id"] == "terms"]
    return found


def _env(**extra: str) -> dict[str, str]:
    venv_bin = str(Path(sys.executable).parent)
    base = {**os.environ, "PATH": f"{venv_bin}{os.pathsep}{os.environ['PATH']}"}
    base["GIT_CONFIG_GLOBAL"] = os.devnull
    base["GIT_CONFIG_NOSYSTEM"] = "1"
    return {**base, **extra}


def _git_in(tree: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=tree,
        check=True,
        capture_output=True,
        env=_env(),
    )


def _tree(root: Path) -> Path:
    """A fixture repo carrying the real gate, committed so nothing is staged."""
    shutil.copytree(GATES, root / ".saffron" / "gates")
    (root / "README.md").write_text(CLEAN_README)
    _git_in(root, "init")
    _git_in(root, "add", "-A")
    _git_in(root, "commit", "-m", "x")
    return root


def _commit(root: Path, message: str) -> None:
    _git_in(root, "add", "-A")
    _git_in(root, "commit", "-m", message)


def _run_entry(tree: Path, env: dict[str, str] | None = None) -> int:
    """The hook's whole `entry`, split and run as prek runs it."""
    shell, flag, script = shlex.split(_hook_config()["entry"])
    assert (shell, flag) == ("sh", "-c")
    done = subprocess.run(
        [shell, flag, script],
        cwd=tree,
        capture_output=True,
        text=True,
        timeout=120,
        env=env if env is not None else _env(),
    )
    return done.returncode


def test_the_terms_hook_fails_a_tree_carrying_an_avoided_phrase(tmp_path):
    clean = _tree(tmp_path / "clean")
    assert _run_entry(clean) == 0

    markdown = _tree(tmp_path / "markdown")
    (markdown / "README.md").write_text(HIT_README)
    _commit(markdown, "hit")
    assert _run_entry(markdown) != 0

    docstring = _tree(tmp_path / "docstring")
    (docstring / "saffron").mkdir()
    (docstring / "saffron" / "bypass.py").write_text(HIT_DOCSTRING)
    _commit(docstring, "hit")
    assert _run_entry(docstring) != 0


def test_the_terms_hook_fails_when_the_gate_reports_an_error(tmp_path):
    erroring = tmp_path / "no-repo"
    shutil.copytree(GATES, erroring / ".saffron" / "gates")
    env = _env(GIT_CEILING_DIRECTORIES=str(tmp_path))
    assert _run_entry(erroring, env=env) != 0


def _prose():
    spec = importlib.util.spec_from_file_location(
        "saffron_prose_gate_for_terms_hook", GATES / "prose.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _tracked() -> list[str]:
    return subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.splitlines()


def test_prek_runs_the_terms_hook_on_every_file_the_gate_reads():
    hook = _hook_config()
    prose = _prose()
    assert prose.in_scope(".saffron/gates/prose.py")
    for path in _tracked():
        if prose.in_scope(path):
            assert re.search(hook["files"], path), path
    # The gate's own wrapper moves its answer too.
    assert re.search(hook["files"], ".saffron/gates/terms")

    assert hook["pass_filenames"] is False
    stages = hook.get("stages")
    if stages is not None:
        assert "pre-commit" in stages
    assert ".saffron/gates/terms" in hook["entry"]
