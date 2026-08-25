from __future__ import annotations

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
    result = size_gate(_diff(added=ceiling, removed=0), "bug")
    assert result.gate == "size"
    assert result.status == "pass"
    assert result.failures == []


def test_a_diff_one_line_over_the_bug_ceiling_fails():
    ceiling = _CEILINGS["bug"]
    result = size_gate(_diff(added=ceiling + 1, removed=0), "bug")
    assert result.status == "fail"
    assert len(result.failures) == 1
    assert result.failures[0].code == "diff-too-large"


def test_a_diff_at_exactly_the_feature_ceiling_passes():
    ceiling = _CEILINGS["feature"]
    result = size_gate(_diff(added=ceiling, removed=0), "feature")
    assert result.status == "pass"


def test_a_diff_one_line_over_the_feature_ceiling_fails():
    ceiling = _CEILINGS["feature"]
    result = size_gate(_diff(added=ceiling, removed=1), "feature")
    assert result.status == "fail"


def test_a_diff_at_exactly_the_refactor_ceiling_passes():
    ceiling = _CEILINGS["refactor"]
    result = size_gate(_diff(added=0, removed=ceiling), "refactor")
    assert result.status == "pass"


def test_a_diff_one_line_over_the_refactor_ceiling_fails():
    ceiling = _CEILINGS["refactor"]
    result = size_gate(_diff(added=0, removed=ceiling + 1), "refactor")
    assert result.status == "fail"


def test_the_ceiling_is_added_plus_removed_not_either_side_alone():
    # 200 added + 200 removed is over the bug ceiling (300) even though
    # neither side alone is.
    result = size_gate(_diff(added=200, removed=200), "bug")
    assert result.status == "fail"


def test_a_spec_type_with_no_declared_ceiling_defaults_rather_than_erroring():
    """`test`/`docs`/`chore` have no ceiling in DESIGN.md §5.4. Absence of a
    declared ceiling is not the gate breaking, so it must default rather than
    ever return `error` for a diff it could read."""
    passing = size_gate(_diff(added=_DEFAULT_CEILING, removed=0), "docs")
    failing = size_gate(_diff(added=_DEFAULT_CEILING + 1, removed=0), "docs")
    assert passing.status == "pass"
    assert failing.status == "fail"


def test_size_never_returns_error_for_a_readable_diff():
    assert size_gate("", "bug").status in ("pass", "fail")
    assert size_gate(_diff(added=5000, removed=5000), "chore").status in (
        "pass",
        "fail",
    )


def test_an_empty_diff_passes():
    result = size_gate("", "feature")
    assert result.status == "pass"


def test_every_result_names_its_tool():
    assert size_gate(_diff(added=1, removed=0), "bug").tool
    assert size_gate(_diff(added=10_000, removed=0), "bug").tool


def test_the_summary_names_the_count_and_the_ceiling():
    ceiling = _CEILINGS["bug"]
    result = size_gate(_diff(added=ceiling + 1, removed=0), "bug")
    assert str(ceiling + 1) in result.summary
    assert str(ceiling) in result.summary
