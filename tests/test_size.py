from __future__ import annotations

import subprocess

from saffron.cell import worktree
from saffron.gates.core.size import (
    _CEILINGS,
    _DEFAULT_CEILING,
    _changed_lines,
    size_gate,
)


def _diff(added: int, removed: int, *, path: str = "src/a.py") -> str:
    """A diff-shaped text with exactly `added` added lines and `removed`
    removed lines of content. Not a real git diff — `size_gate` never
    validates headers the way `scope`/`integrity` do; it only counts."""
    lines = [
        f"diff --git a/{path} b/{path}",
        f"--- a/{path}",
        f"+++ b/{path}",
        f"@@ -1,{removed} +1,{added} @@",
    ]
    lines += [f"+line{i}" for i in range(added)]
    lines += [f"-line{i}" for i in range(removed)]
    return "\n".join(lines) + "\n"


def test_changed_lines_counts_added_plus_removed():
    assert _changed_lines(_diff(added=3, removed=2)) == 5


def test_changed_lines_does_not_count_the_file_header():
    # Just the `--- a/x` / `+++ b/x` header lines, no content.
    diff = "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n"
    assert _changed_lines(diff) == 0


def test_each_file_block_gets_its_own_headers_back():
    """Every diff Saffron gates is multi-file, and nothing here was: deleting
    the `in_headers` reset in `_changed_lines` left all sixteen tests passing
    while a two-file diff counted 4 instead of 2 — the second block's
    `--- a/x` / `+++ b/x` read as content, once per extra file."""
    two = _diff(added=1, removed=0) + _diff(added=1, removed=0, path="src/b.py")
    assert two.count("diff --git") == 2
    assert _changed_lines(two) == 2


def test_changed_lines_does_not_count_the_hunk_or_diff_headers():
    diff = _diff(added=1, removed=1)
    assert "diff --git" in diff
    assert "@@ -1,1 +1,1 @@" in diff
    assert _changed_lines(diff) == 2


def test_hunk_content_shaped_like_a_file_header_is_still_counted():
    """A `--- a/path` / `+++ b/path` file header only ever appears before a
    block's first `@@` line. An added/removed source line can itself start
    with `--`, `---`, `++` or `+++` at column 0 — a SQL/Lua `--` comment, a
    YAML/Markdown `---` delimiter, a bare `++i;`/`--i;` statement — and once
    prefixed with the diff's own leading `+`/`-` marker it is indistinguishable
    from a header *by content alone*. Position, not a string prefix, is what
    must decide."""
    diff = "\n".join(
        [
            "diff --git a/x.sql b/x.sql",
            "--- a/x.sql",
            "+++ b/x.sql",
            "@@ -1,2 +1,4 @@",
            "+++i;",  # added line whose content is "++i;"
            "+---",  # added line whose content is a bare "---"
            "--- old comment",  # removed line whose content is "-- old comment"
            "-++i;",  # removed line whose content is "++i;"
        ]
    )
    # None of the four hunk lines is a file header — this hunk has 4 changed
    # lines, not 0.
    assert _changed_lines(diff) == 4


def test_a_diff_at_exactly_the_bug_ceiling_passes():
    ceiling = _CEILINGS["bug"]
    result = size_gate(_diff(added=ceiling, removed=0), "bug", touches=[])
    assert result.gate == "size"
    assert result.status == "pass"
    assert result.failures == []


def test_a_diff_one_line_over_the_bug_ceiling_fails():
    ceiling = _CEILINGS["bug"]
    result = size_gate(_diff(added=ceiling + 1, removed=0), "bug", touches=[])
    assert result.status == "fail"
    assert len(result.failures) == 1
    assert result.failures[0].code == "diff-too-large"


def test_a_diff_at_exactly_the_feature_ceiling_passes():
    ceiling = _CEILINGS["feature"]
    result = size_gate(_diff(added=ceiling, removed=0), "feature", touches=[])
    assert result.status == "pass"


def test_a_diff_one_line_over_the_feature_ceiling_fails():
    ceiling = _CEILINGS["feature"]
    result = size_gate(_diff(added=ceiling, removed=1), "feature", touches=[])
    assert result.status == "fail"


def test_a_diff_at_exactly_the_refactor_ceiling_passes():
    ceiling = _CEILINGS["refactor"]
    result = size_gate(_diff(added=0, removed=ceiling), "refactor", touches=[])
    assert result.status == "pass"


def test_a_diff_one_line_over_the_refactor_ceiling_fails():
    ceiling = _CEILINGS["refactor"]
    result = size_gate(_diff(added=0, removed=ceiling + 1), "refactor", touches=[])
    assert result.status == "fail"


def test_the_ceiling_is_added_plus_removed_not_either_side_alone():
    # 200 added + 200 removed is over the bug ceiling (300) even though
    # neither side alone is.
    result = size_gate(_diff(added=200, removed=200), "bug", touches=[])
    assert result.status == "fail"


def test_a_spec_type_with_no_declared_ceiling_defaults_rather_than_erroring():
    """`test`/`docs`/`chore` have no ceiling in DESIGN.md §5.4. Absence of a
    declared ceiling is not the gate breaking, so it must default rather than
    ever return `error` for a diff it could read."""
    passing = size_gate(_diff(added=_DEFAULT_CEILING, removed=0), "docs", touches=[])
    failing = size_gate(
        _diff(added=_DEFAULT_CEILING + 1, removed=0), "docs", touches=[]
    )
    assert passing.status == "pass"
    assert failing.status == "fail"


def test_size_never_returns_error_for_a_readable_diff():
    assert size_gate("", "bug", touches=[]).status in ("pass", "fail")
    assert size_gate(_diff(added=5000, removed=5000), "chore", touches=[]).status in (
        "pass",
        "fail",
    )


def test_an_empty_diff_passes():
    result = size_gate("", "feature", touches=[])
    assert result.status == "pass"


def test_no_result_names_a_tool():
    """`tool` is obtained by executing the tool, never written down (§5.4,
    Appendix H) — so a gate that executes nothing leaves it unset, as `scope`
    and `integrity` do. A literal would also read identically forever and
    silently defeat `baseline.suite_drift`, which watches `tool` to notice a
    gate's implementation changing mid-run."""
    assert size_gate(_diff(added=1, removed=0), "bug", touches=[]).tool is None
    assert size_gate(_diff(added=10_000, removed=0), "bug", touches=[]).tool is None


def test_the_summary_names_the_count_and_the_ceiling():
    ceiling = _CEILINGS["bug"]
    result = size_gate(_diff(added=ceiling + 1, removed=0), "bug", touches=[])
    assert str(ceiling + 1) in result.summary
    assert str(ceiling) in result.summary


def _real_repo(tmp_path, files):
    """Same helper shape as `test_integrity.py`'s `_repo`: a real git history,
    not a hand-written fixture — the string git actually emits for a `-diff`
    gitattribute is the thing under test (unlike `_diff` above, which is
    explicit that `size_gate` never validates real diff headers)."""

    def run(*a):
        return subprocess.run(a, cwd=tmp_path, check=True, capture_output=True)

    run("git", "init", "-q", "-b", "main")
    run("git", "config", "user.email", "t@example.com")
    run("git", "config", "user.name", "t")
    for name, content in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    run("git", "add", "-A")
    run("git", "commit", "-qm", "base")
    return run


def _real_diff(tmp_path, run, changes):
    for name, content in changes.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    run("git", "add", "-A")
    return subprocess.run(
        ["git", "diff", "--cached", *worktree.DIFF_FLAGS],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def test_a_gitattributes_hidden_rewrite_errors_when_the_file_is_in_touches(tmp_path):
    """Measured: a repo committing `*.py -diff` in `.gitattributes` and then
    rewriting 2000 lines of `a.py` reports 1 changed line — the
    `.gitattributes` addition — under the old counting-only rule, and `size`
    would have passed a rewrite of any size. `error` closes that route: the
    gate is saying it cannot measure, never that the diff is small."""
    run = _real_repo(tmp_path, {"a.py": "x = 1\n", ".gitattributes": "*.py -diff\n"})
    rewritten = "\n".join(f"y{i} = {i}" for i in range(2000)) + "\n"
    diff = _real_diff(tmp_path, run, {"a.py": rewritten})
    assert "Binary files" in diff

    result = size_gate(diff, "bug", touches=["a.py"])
    assert result.status == "error"
    assert "a.py" in result.summary


def test_a_gitattributes_hidden_rewrite_outside_touches_is_not_this_gate_s_error(
    tmp_path,
):
    """A file nobody declared has already failed `scope`, which is a `fail`
    the agent can repair by deleting it. `size` erroring here too would turn a
    genuine binary asset outside `touches` into an abandoned task."""
    run = _real_repo(tmp_path, {"a.py": "x = 1\n", ".gitattributes": "*.py -diff\n"})
    rewritten = "\n".join(f"y{i} = {i}" for i in range(2000)) + "\n"
    diff = _real_diff(tmp_path, run, {"a.py": rewritten})
    assert "Binary files" in diff

    result = size_gate(diff, "bug", touches=[])
    assert result.status != "error"


def test_a_readable_change_still_counts_beside_an_undeclared_binary_block(tmp_path):
    """A mixed diff — one file hidden as binary and outside `touches`, one
    ordinary readable hunk — must not abort on the binary block: the readable
    hunk is still counted and the gate still reaches a `pass`/`fail` verdict."""
    run = _real_repo(
        tmp_path,
        {"a.py": "x = 1\n", "b.py": "z = 1\n", ".gitattributes": "a.py -diff\n"},
    )
    diff = _real_diff(tmp_path, run, {"a.py": "x = 2\n", "b.py": "z = 1\nz2 = 2\n"})
    assert "Binary files" in diff

    result = size_gate(diff, "bug", touches=["b.py"])
    assert result.status == "pass"
    assert "1 changed lines" in result.summary
