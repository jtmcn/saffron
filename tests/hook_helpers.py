"""Helpers the hook and gate-script tests share (b-a99c76)."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import yaml

REPO = Path(__file__).resolve().parent.parent


def hook_config(hook_id: str) -> dict:
    """One hook, read from the file prek reads."""
    config = yaml.safe_load((REPO / ".pre-commit-config.yaml").read_text())
    hooks = [hook for repo in config["repos"] for hook in repo["hooks"]]
    (found,) = [hook for hook in hooks if hook["id"] == hook_id]
    return found


def git_in(tree: Path, *args: str) -> None:
    """Run git in `tree` with no global or system config and the venv first on PATH."""
    venv_bin = str(Path(sys.executable).parent)
    env = {
        **os.environ,
        "PATH": f"{venv_bin}{os.pathsep}{os.environ['PATH']}",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=tree,
        check=True,
        capture_output=True,
        env=env,
    )


def load_script(path: Path, name: str) -> ModuleType:
    """Load a gate or hook script by path, inside the calling test."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered first: a dataclass under postponed annotations looks its module up.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def tracked() -> list[str]:
    """Every path git tracks in this repository."""
    return subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.splitlines()
