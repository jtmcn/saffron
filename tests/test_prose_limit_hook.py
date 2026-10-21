"""`hooks/prose_limit.py`: a staged file may not gain hits of any `prose` rule."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
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
    assert "README.md: 1 new sentence-length hit" in done.stdout
    assert "README.md:3:" in done.stdout


def test_a_rewritten_hit_is_new(tmp_path):
    """A hit is its sentence, so one long sentence rewritten into another is new
    and cannot cancel against the one it replaced (backlog item b-044ae7)."""
    repo = _repo(tmp_path, {"README.md": LONG_A + "\n"})
    _stage(repo, "README.md", LONG_B + "\n")
    done = _hook(repo)
    assert done.returncode == 1
    assert "README.md: 1 new sentence-length hit" in done.stdout


def test_a_reflowed_hit_is_not_new(tmp_path):
    repo = _repo(tmp_path, {"README.md": LONG_A + "\n"})
    _stage(repo, "README.md", LONG_A.replace(" ", "\n", 3) + "\n")
    assert _hook(repo).returncode == 0


def test_a_new_file_compares_against_nothing(tmp_path):
    repo = _repo(tmp_path, {"README.md": "Short.\n"})
    _stage(repo, "docs/backlog/1-new.md", LONG_A + "\n")
    done = _hook(repo)
    assert done.returncode == 1
    assert "docs/backlog/1-new.md: 1 new sentence-length hit" in done.stdout


def test_a_rename_keeps_its_count(tmp_path):
    repo = _repo(tmp_path, {"docs/backlog/1-a.md": LONG_A + "\n"})
    _git(repo, "mv", "docs/backlog/1-a.md", "docs/backlog/2-b.md")
    assert _hook(repo).returncode == 0


def test_a_file_out_of_scope_is_not_read(tmp_path):
    repo = _repo(tmp_path, {"README.md": "Short.\n"})
    _stage(repo, "docs/evidence/x.md", LONG_A + "\n")
    assert _hook(repo).returncode == 0


def test_a_commit_of_python_alone_is_limited(tmp_path):
    repo = _repo(tmp_path, {"saffron/m.py": "x = 1\n"})
    _stage(repo, "saffron/m.py", "# one\n# two\n# three\nx = 1\n")
    done = _hook(repo)
    assert done.returncode == 1
    assert "saffron/m.py: 1 new comment-block hit" in done.stdout


def test_prek_runs_the_hook_on_markdown_and_python():
    # prek skips a hook no staged file matches, so a `.md` filter never ran
    # the comment rules on a commit of Python alone.
    config = yaml.safe_load((REPO / ".pre-commit-config.yaml").read_text())
    hooks = [hook for repo in config["repos"] for hook in repo["hooks"]]
    (hook,) = [hook for hook in hooks if hook["id"] == "prose-limit"]
    assert hook["entry"] == "uv run hooks/prose_limit.py"
    assert hook["pass_filenames"] is False
    assert re.search(hook["files"], "README.md")
    assert re.search(hook["files"], "saffron/task.py")


def _edited(repo: Path, file_path: Path) -> subprocess.CompletedProcess[str]:
    event = {"tool_input": {"file_path": str(file_path)}, "cwd": str(repo)}
    return subprocess.run(
        [sys.executable, str(HOOK), "--edited"],
        cwd=repo,
        input=json.dumps(event),
        capture_output=True,
        text=True,
    )


def test_an_edit_that_adds_a_hit_is_reported_to_the_model(tmp_path):
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


def test_an_edit_beside_an_untouched_hit_says_nothing(tmp_path):
    repo = _repo(
        tmp_path, {"README.md": "The agent works well — it helps a lot. It is fast.\n"}
    )
    (repo / "README.md").write_text(
        "The agent works well — it helps a lot. It is quick.\n"
    )
    done = _edited(repo, repo / "README.md")
    assert done.returncode == 0
    assert done.stderr == ""


def _raw_event(repo: Path, event: object) -> subprocess.CompletedProcess[str]:
    """`event` as JSON on stdin; bytes go through unencoded."""
    return subprocess.run(
        [sys.executable, str(HOOK), "--edited"],
        cwd=repo,
        input=event.decode() if isinstance(event, bytes) else json.dumps(event),
        capture_output=True,
        text=True,
    )


def test_edited_with_malformed_stdin_says_nothing(tmp_path):
    repo = _repo(tmp_path, {"README.md": "Short.\n"})
    done = _raw_event(repo, b"not json")
    assert done.returncode == 0
    assert done.stderr == ""


def test_edited_with_null_tool_input_says_nothing(tmp_path):
    repo = _repo(tmp_path, {"README.md": "Short.\n"})
    done = _raw_event(repo, {"tool_input": None})
    assert done.returncode == 0
    assert done.stderr == ""


@pytest.mark.parametrize("event", [[], "x"])
def test_edited_with_an_event_that_is_not_an_object_says_nothing(tmp_path, event):
    repo = _repo(tmp_path, {"README.md": "Short.\n"})
    (repo / "README.md").write_text(LONG_A + "\n")
    done = _raw_event(repo, event)
    assert (done.returncode, done.stderr) == (0, "")


def test_a_cwd_that_is_not_a_string_falls_back_to_the_repo(tmp_path):
    repo = _repo(tmp_path, {"README.md": "Short.\n"})
    (repo / "README.md").write_text(LONG_A + "\n")
    done = _raw_event(repo, {"tool_input": {"file_path": "README.md"}, "cwd": 3})
    assert done.returncode == 2
    assert "README.md:1: sentence-length" in done.stderr


def test_an_edit_the_gate_does_not_read_says_nothing(tmp_path):
    repo = _repo(tmp_path, {"README.md": "Short.\n"})
    evidence = repo / "docs" / "evidence" / "run.md"
    evidence.parent.mkdir(parents=True)
    evidence.write_text(LONG_A + "\n")
    assert _edited(repo, evidence).returncode == 0


def test_file_mode_reads_an_unstaged_new_file_against_zero(tmp_path):
    repo = _repo(tmp_path, {"README.md": "Short.\n"})
    (repo / "docs" / "backlog").mkdir(parents=True)
    (repo / "docs" / "backlog" / "1-new.md").write_text(LONG_A + "\n")
    done = _hook(repo, "--file", "docs/backlog/1-new.md")
    assert done.returncode == 1
    assert "1 new hit against zero" in done.stdout
    assert "docs/backlog/1-new.md:1: sentence-length" in done.stdout


def test_file_mode_reads_a_tracked_file_against_head(tmp_path):
    repo = _repo(tmp_path, {"README.md": LONG_A + "\n"})
    (repo / "README.md").write_text(LONG_A + "\n\n" + LONG_B + "\n")
    done = _hook(repo, "--file", "README.md")
    assert done.returncode == 1
    assert "1 new hit against HEAD" in done.stdout
    assert "README.md:3: sentence-length" in done.stdout


def test_file_mode_says_nothing_when_a_hit_only_moves(tmp_path):
    repo = _repo(tmp_path, {"README.md": LONG_A + "\n"})
    (repo / "README.md").write_text("Intro.\n\n" + LONG_A + "\n")
    done = _hook(repo, "--file", "README.md")
    assert done.returncode == 0
    assert "0 new hits against HEAD" in done.stdout


def test_file_mode_reads_the_working_tree_not_the_index(tmp_path):
    repo = _repo(tmp_path, {"README.md": "Short.\n"})
    _stage(repo, "README.md", "Short.\n")
    (repo / "README.md").write_text(LONG_A + "\n")
    done = _hook(repo, "--file", "README.md")
    assert done.returncode == 1
    assert "README.md:1: sentence-length" in done.stdout


def test_file_mode_refuses_a_path_the_gates_do_not_read(tmp_path):
    repo = _repo(tmp_path, {"README.md": "Short.\n"})
    (repo / "docs" / "evidence").mkdir(parents=True)
    (repo / "docs" / "evidence" / "run.md").write_text(LONG_A + "\n")
    done = _hook(repo, "--file", "docs/evidence/run.md")
    assert done.returncode == 2
    assert "out of the gates' scope" in done.stderr


def test_file_mode_refuses_a_path_that_is_not_there(tmp_path):
    repo = _repo(tmp_path, {"README.md": "Short.\n"})
    done = _hook(repo, "--file", "docs/backlog/9-gone.md")
    assert done.returncode == 2
    assert "no such file" in done.stderr


def test_file_mode_refuses_a_file_outside_the_worktree(tmp_path):
    """`_in_repo` returns None for two callers that answer it oppositely.

    `edit_time` goes quiet and `file_time` refuses, so the None branch needs a
    witness on each side (backlog item b-929465).
    """
    work = tmp_path / "work"
    work.mkdir()
    repo = _repo(work, {"README.md": "Short.\n"})
    # A name `in_scope` accepts, so the refusal below can only come from the
    # path sitting outside the worktree.
    outside = tmp_path / "README.md"
    outside.write_text(LONG_A + "\n")
    done = _hook(repo, "--file", str(outside))
    assert done.returncode == 2
    assert "out of the gates' scope" in done.stderr


def test_tree_mode_reads_an_untracked_file_against_zero(tmp_path):
    repo = _repo(tmp_path, {"README.md": "Short.\n"})
    (repo / "docs" / "backlog").mkdir(parents=True)
    (repo / "docs" / "backlog" / "1-new.md").write_text(LONG_A + "\n")
    spec_dir = repo / ".saffron" / "specs"
    spec_dir.mkdir(parents=True)
    spec_path = spec_dir / "SA-0001-x.md"
    spec_path.write_text("")
    _git(repo, "add", "-N", str(spec_path.relative_to(repo)))
    spec_path.write_text(LONG_B + "\n")
    done = _hook(repo, "--tree")
    assert done.returncode == 1
    assert "docs/backlog/1-new.md: 1 new sentence-length hit" in done.stdout
    assert "docs/backlog/1-new.md:1: sentence-length:" in done.stdout
    assert ".saffron/specs/SA-0001-x.md: 1 new sentence-length hit" in done.stdout
    assert ".saffron/specs/SA-0001-x.md:1: sentence-length:" in done.stdout


def test_tree_mode_reads_an_unstaged_edit_against_head(tmp_path):
    repo = _repo(tmp_path, {"README.md": "Short.\n", "saffron/m.py": "x = 1\n"})
    (repo / "README.md").write_text("Short.\n\n" + LONG_A + "\n")
    (repo / "saffron" / "m.py").write_text("# one\n# two\n# three\nx = 1\n")
    done = _hook(repo, "--tree")
    assert done.returncode == 1
    assert "README.md: 1 new sentence-length hit" in done.stdout
    assert "saffron/m.py: 1 new comment-block hit" in done.stdout
    assert "  README.md:3: sentence-length: " in done.stdout
    assert _hook(repo).returncode == 0


def test_tree_mode_reads_a_fixed_working_copy_not_the_staged_one(tmp_path):
    # The working copy still differs from HEAD, so the file stays in the
    # diff `--tree` reads. It carries no hit, unlike the staged blob.
    repo = _repo(tmp_path, {"README.md": "Short.\n"})
    _stage(repo, "README.md", "Short.\n\n" + LONG_A + "\n")
    (repo / "README.md").write_text("Short.\n\nFixed now.\n")
    done = _hook(repo, "--tree")
    assert (done.returncode, done.stdout) == (0, "")
    assert _hook(repo).returncode == 1


def test_tree_mode_counts_only_what_head_lacks(tmp_path):
    repo = _repo(
        tmp_path,
        {
            "README.md": LONG_A + "\n",
            "docs/backlog/1-a.md": LONG_A + "\n",
            "docs/backlog/3-c.md": LONG_A + "\n",
            "docs/evidence/x.md": "Short.\n",
            ".gitignore": "docs/backlog/9-ignored.md\n",
        },
    )
    (repo / "README.md").write_text("Intro.\n\n" + LONG_A + "\n")
    _git(repo, "mv", "docs/backlog/1-a.md", "docs/backlog/2-b.md")
    (repo / "docs" / "backlog" / "3-c.md").write_text(
        LONG_A + "\n\nThe agent runs in a sandbox.\n"
    )
    (repo / "docs" / "evidence" / "x.md").write_text(LONG_A + "\n")
    (repo / "docs" / "evidence" / "run.md").write_text(LONG_A + "\n")
    (repo / "docs" / "backlog" / "9-ignored.md").write_text(LONG_A + "\n")
    done = _hook(repo, "--tree")
    assert (done.returncode, done.stdout) == (0, "")


def test_make_check_runs_the_tree_hook_and_a_commit_does_not():
    config = yaml.safe_load((REPO / ".pre-commit-config.yaml").read_text())
    hooks = [hook for repo in config["repos"] for hook in repo["hooks"]]
    (tree_hook,) = [hook for hook in hooks if hook["id"] == "prose-limit-tree"]
    assert tree_hook["stages"] == ["manual"]
    assert tree_hook["pass_filenames"] is False
    assert tree_hook["always_run"] is True
    (commit_hook,) = [hook for hook in hooks if hook["id"] == "prose-limit"]
    assert "stages" not in commit_hook
    # The config alone does not say `make check` reaches this hook. `lint`
    # names each id with its own flag, in its own call.
    makefile = (REPO / "Makefile").read_text()
    assert "--skip prose-limit " in makefile
    assert "--stage manual prose-limit-tree" in makefile


def _lint_recipe_lines() -> list[str]:
    """`Makefile`'s `lint:` recipe, continuation lines joined, the way make
    reads it."""
    text = (REPO / "Makefile").read_text()
    raw: list[str] = []
    in_lint = False
    for line in text.splitlines():
        if line == "lint:":
            in_lint = True
            continue
        if in_lint:
            if not line.startswith("\t"):
                break
            raw.append(line[1:])
    joined: list[str] = []
    buf = ""
    for line in raw:
        buf += line
        if buf.endswith("\\"):
            buf = buf[:-1]
            continue
        joined.append(buf)
        buf = ""
    return joined


def _expand_make_dollars(cmd: str) -> str:
    """`$$` becomes a literal `$`. Any other `$` reference expands to nothing,
    the way make expands an undefined variable."""
    cmd = re.sub(r"\$\$", "\x00", cmd)
    cmd = re.sub(r"\$\([^)]*\)|\$\{[^}]*\}|\$.", "", cmd)
    return cmd.replace("\x00", "$")


def _run_make_recipe(lines: list[str], env: dict[str, str]) -> int:
    """Run `lines` the way make runs a recipe: each to its own `sh -c`. A
    leading `-` keeps that line's exit status from stopping the recipe."""
    for line in lines:
        cmd, ignore = line, False
        while cmd and cmd[0] in "@-+":
            ignore = ignore or cmd[0] == "-"
            cmd = cmd[1:]
        done = subprocess.run(["sh", "-c", _expand_make_dollars(cmd)], env=env)
        if done.returncode != 0 and not ignore:
            return done.returncode
    return 0


def test_lint_runs_the_tree_hook_after_a_failure_and_still_fails(tmp_path):
    lines = _lint_recipe_lines()
    stub = tmp_path / "prek"
    stub.write_text(
        "#!/bin/sh\n"
        'echo "$@" >> "$PREK_LOG"\n'
        'case "$*" in\n'
        '  *--skip*) [ "$PREK_FAIL" = first ] && exit 1 ;;\n'
        '  *--stage*) [ "$PREK_FAIL" = second ] && exit 1 ;;\n'
        "esac\n"
        "exit 0\n"
    )
    stub.chmod(0o755)
    log = tmp_path / "log"
    for fail, expect in [("none", 0), ("first", 1), ("second", 1)]:
        log.write_text("")
        env = {
            **os.environ,
            "PATH": f"{tmp_path}:{os.environ['PATH']}",
            "PREK_LOG": str(log),
            "PREK_FAIL": fail,
        }
        status = _run_make_recipe(lines, env)
        logged = [call for call in log.read_text().splitlines() if call]
        # Exact content and order: a hook id swapped between the two calls
        # still logs two lines, but the wrong ones.
        assert logged == [
            "run --all-files --skip prose-limit",
            "run --all-files --stage manual prose-limit-tree",
        ]
        assert status == expect


def test_claude_code_runs_the_hook_after_each_edit():
    settings = json.loads((REPO / ".claude" / "settings.json").read_text())
    (entry,) = settings["hooks"]["PostToolUse"]
    assert entry["matcher"] == "Write|Edit"
    (hook,) = entry["hooks"]
    assert hook["command"] == (
        'cd "$CLAUDE_PROJECT_DIR" && python3 hooks/prose_limit.py --edited'
    )
