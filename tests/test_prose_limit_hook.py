"""`hooks/prose_limit.py`: a staged file may not gain hits of any `prose` rule."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / "hooks" / "prose_limit.py"
LONG_A = "alpha " * 30 + "end."
LONG_B = "beta " * 30 + "end."


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@example.invalid", "-c", "user.name=t", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _repo(tmp_path: Path, files: dict[str, str]) -> Path:
    _git(tmp_path, "init", "-q")
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "base")
    return tmp_path


def _stage(repo: Path, name: str, text: str) -> None:
    (repo / name).parent.mkdir(parents=True, exist_ok=True)
    (repo / name).write_text(text)
    _git(repo, "add", "-A")


def _hook(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HOOK), *args], cwd=repo, capture_output=True, text=True
    )


def test_an_added_long_sentence_fails(tmp_path):
    repo = _repo(tmp_path, {"README.md": "Short.\n"})
    _stage(repo, "README.md", "Short.\n\n" + LONG_A + "\n")
    done = _hook(repo)
    assert done.returncode == 1
    assert "README.md: sentence-length rose from 0 to 1" in done.stdout
    assert "README.md:3:" in done.stdout


def test_a_rewritten_hit_passes(tmp_path):
    repo = _repo(tmp_path, {"README.md": LONG_A + "\n"})
    _stage(repo, "README.md", LONG_B + "\n")
    assert _hook(repo).returncode == 0


def test_a_new_file_compares_against_nothing(tmp_path):
    repo = _repo(tmp_path, {"README.md": "Short.\n"})
    _stage(repo, "docs/backlog/1-new.md", LONG_A + "\n")
    done = _hook(repo)
    assert done.returncode == 1
    assert "docs/backlog/1-new.md: sentence-length rose from 0 to 1" in done.stdout


def test_a_rename_keeps_its_count(tmp_path):
    repo = _repo(tmp_path, {"docs/backlog/1-a.md": LONG_A + "\n"})
    _git(repo, "mv", "docs/backlog/1-a.md", "docs/backlog/2-b.md")
    assert _hook(repo).returncode == 0


def test_a_file_out_of_scope_is_not_read(tmp_path):
    repo = _repo(tmp_path, {"README.md": "Short.\n"})
    _stage(repo, "docs/evidence/x.md", LONG_A + "\n")
    assert _hook(repo).returncode == 0


def test_prek_runs_the_hook_on_markdown():
    config = yaml.safe_load((REPO / ".pre-commit-config.yaml").read_text())
    hooks = [hook for repo in config["repos"] for hook in repo["hooks"]]
    (hook,) = [hook for hook in hooks if hook["id"] == "prose-limit"]
    assert hook["entry"] == "uv run hooks/prose_limit.py"
    assert hook["pass_filenames"] is False
    assert hook["files"] == r"\.md$"


def _edited(repo: Path, file_path: Path) -> subprocess.CompletedProcess[str]:
    event = {"tool_input": {"file_path": str(file_path)}, "cwd": str(repo)}
    return subprocess.run(
        [sys.executable, str(HOOK), "--edited"],
        cwd=repo,
        input=json.dumps(event),
        capture_output=True,
        text=True,
    )


def test_an_edit_that_adds_a_finding_is_reported_to_the_model(tmp_path):
    repo = _repo(tmp_path, {"README.md": "Short.\n"})
    (repo / "README.md").write_text("Short.\n\n" + LONG_A + "\n")
    done = _edited(repo, repo / "README.md")
    assert done.returncode == 2
    assert "README.md:3: sentence-length" in done.stderr


def test_an_edit_that_adds_an_avoided_phrase_is_reported(tmp_path):
    repo = _repo(tmp_path, {"README.md": "Short.\n"})
    (repo / "README.md").write_text("The agent runs in a sandbox.\n")
    done = _edited(repo, repo / "README.md")
    assert done.returncode == 2
    assert 'sandbox: say "cell"' in done.stderr


def test_a_clean_edit_and_a_file_elsewhere_say_nothing(tmp_path):
    repo = _repo(tmp_path, {"README.md": "Short.\n"})
    (repo / "README.md").write_text("Short. Still short.\n")
    assert _edited(repo, repo / "README.md").returncode == 0
    outside = tmp_path.parent / f"{tmp_path.name}-outside.md"
    outside.write_text(LONG_A + "\n")
    assert _edited(repo, outside).returncode == 0


def test_claude_code_runs_the_hook_after_each_edit():
    settings = json.loads((REPO / ".claude" / "settings.json").read_text())
    (entry,) = settings["hooks"]["PostToolUse"]
    assert entry["matcher"] == "Write|Edit"
    (hook,) = entry["hooks"]
    assert hook["command"].endswith("python3 hooks/prose_limit.py --edited")
