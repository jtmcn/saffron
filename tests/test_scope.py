from __future__ import annotations

import subprocess

from saffron.cell import worktree
from saffron.gates.core.scope import matches, scope_gate


def test_a_single_star_does_not_cross_a_slash():
    assert matches("src/a.py", "src/*.py")
    assert not matches("src/deep/a.py", "src/*.py")


def test_a_double_star_crosses_slashes():
    assert matches("src/deep/nested/a.py", "src/**")
    assert matches("src/a.py", "src/**")


def test_a_double_star_prefix_matches_at_any_depth():
    assert matches("a/b/c_test.go", "**/*_test.go")
    assert matches("c_test.go", "**/*_test.go")


def test_a_question_mark_matches_one_character_but_not_a_slash():
    assert matches("ab.py", "a?.py")
    assert not matches("a/b.py", "a?b.py")


def test_a_dot_in_a_pattern_is_literal():
    assert not matches("srcXa/py", "src.a/py")


def test_everything_inside_touches_passes():
    result = scope_gate(
        ["src/thermal_edge/weather/cli.py", "tests/test_cli.py"],
        touches=["src/thermal_edge/weather/**", "tests/**"],
    )
    assert result.gate == "scope"
    assert result.status == "pass"
    assert result.failures == []


def test_a_file_outside_touches_fails_and_names_itself():
    result = scope_gate(
        ["src/thermal_edge/weather/cli.py", "alembic/versions/0042_add.py"],
        touches=["src/thermal_edge/weather/**"],
    )
    assert result.status == "fail"
    assert [f.file for f in result.failures] == ["alembic/versions/0042_add.py"]
    assert result.failures[0].code == "out-of-scope"
    assert result.failures[0].line is None
    # The failure line is all the agent gets, and `touches` is frontmatter it
    # never sees — "not matched by touches" alone is not actionable.
    assert result.failures[0].message == "outside touches: src/thermal_edge/weather/**"


def test_the_summary_counts_what_escaped():
    result = scope_gate(["a.py", "b.py", "c.py"], touches=["a.py"])
    assert result.summary == "2 of 3 changed files outside touches"


def test_an_empty_diff_passes():
    assert scope_gate([], touches=["src/**"]).status == "pass"


def test_no_declared_touches_skips_rather_than_failing_everything():
    """A bug spec has no `touches` until DIAGNOSE proposes one (DESIGN.md §5.2)."""
    result = scope_gate(["a.py"], touches=[])
    assert result.status == "skip"
    assert "no touches declared" in result.summary


def _hostile_repo(path):
    """A real repo whose worktree config bends every diff knob an agent can set."""
    path.mkdir(parents=True, exist_ok=True)
    run = lambda *a: subprocess.run(a, cwd=path, check=True, capture_output=True)  # noqa: E731
    run("git", "init", "-q", "-b", "main")
    run("git", "config", "user.email", "t@example.com")
    run("git", "config", "user.name", "t")
    (path / "src").mkdir()
    (path / "tests").mkdir()
    (path / "src" / "a.py").write_text("a\n")
    (path / "tests" / "test_x.py").write_text("def test_x():\n    assert 1\n")
    run("git", "add", "-A")
    run("git", "commit", "-qm", "base")
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True
    ).stdout.strip()

    run("git", "config", "diff.srcPrefix", "x/")
    run("git", "config", "diff.dstPrefix", "y/")
    run("git", "config", "diff.noprefix", "true")
    run("git", "config", "diff.mnemonicPrefix", "true")
    run("git", "config", "diff.external", "/usr/bin/true")
    # A textconv driver renders both sides through a program that prints
    # nothing, so an edited file diffs as unchanged.
    run("git", "config", "diff.blank.textconv", "/usr/bin/true")
    (path / ".gitattributes").write_text("*.py diff=blank\n")
    run("git", "rm", "-q", "tests/test_x.py")
    (path / "src" / "a.py").write_text("a\nb\n")
    run("git", "add", "-A")
    run("git", "commit", "-qm", "delete the suite")
    return base


def _diff(path, base, *flags):
    return subprocess.run(
        ["git", "diff", *flags, f"{base}..HEAD"],
        cwd=path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def test_hostile_worktree_config_bends_a_bare_diff(tmp_path):
    """The attack, measured: bare `git diff` obeys the config the agent wrote."""
    base = _hostile_repo(tmp_path / "repo")
    assert _diff(tmp_path / "repo", base) == ""  # diff.external ate it whole


def test_the_pinned_flags_beat_repo_local_config(tmp_path):
    """`-c`/flags on the command line win over `.git/config` — the whole fix."""
    base = _hostile_repo(tmp_path / "repo")
    pinned = _diff(tmp_path / "repo", base, *worktree.DIFF_FLAGS)
    headers = [ln for ln in pinned.splitlines() if ln.startswith("diff --git")]
    assert headers == [
        "diff --git a/.gitattributes b/.gitattributes",
        "diff --git a/src/a.py b/src/a.py",
        "diff --git a/tests/test_x.py b/tests/test_x.py",
    ]
    # The edit itself survives, so --no-textconv is doing its half too.
    assert "+b" in pinned


def test_a_gate_handed_a_bent_diff_errors_rather_than_passing(tmp_path):
    """`error` is charged to nobody (§5.4); a `pass` here would be the escape."""
    base = _hostile_repo(tmp_path / "repo")
    # Only the external-diff knob disarmed: the prefixes are still the agent's.
    bent = _diff(tmp_path / "repo", base, "--no-ext-diff")
    # noprefix outranks the srcPrefix the agent also set; either is unreadable.
    assert "diff --git .gitattributes .gitattributes" in bent
    assert "src/a.py" not in bent  # textconv rendered a real edit as no change

    result = scope_gate(["src/a.py"], touches=["src/**"], diff=bent)
    assert result.status == "error"
    assert "a/ b/" in result.summary

    pinned = _diff(tmp_path / "repo", base, *worktree.DIFF_FLAGS)
    assert scope_gate(["src/a.py"], touches=["src/**"], diff=pinned).status == "pass"


def test_a_quoted_path_is_still_a_recognised_header():
    """git C-quotes both sides together for a path holding a tab or a quote."""
    diff = 'diff --git "a/src/tab\\tname.py" "b/src/tab\\tname.py"\n'
    assert (
        scope_gate(["src/tab\tname.py"], touches=["src/**"], diff=diff).status == "pass"
    )


def test_an_injected_separator_in_an_added_line_cannot_forge_a_bad_header(tmp_path):
    """`str.splitlines()` splits on `\\x0c` and friends, not just `\\n`. An
    added line embedding one of those bytes followed by header-shaped text
    must not be sliced into a fragment the header check reads as its own
    line — misreading a genuinely well-formed diff as `error`."""
    run = lambda *a: subprocess.run(a, cwd=tmp_path, check=True, capture_output=True)  # noqa: E731
    run("git", "init", "-q", "-b", "main")
    run("git", "config", "user.email", "t@example.com")
    run("git", "config", "user.name", "t")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("one\n")
    run("git", "add", "-A")
    run("git", "commit", "-qm", "base")
    (tmp_path / "src" / "a.py").write_text("one\x0cdiff --git bad header shape\n")
    run("git", "add", "-A")
    diff = subprocess.run(
        ["git", "diff", "--cached", *worktree.DIFF_FLAGS],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    result = scope_gate(["src/a.py"], touches=["src/**"], diff=diff)
    assert result.status == "pass"
