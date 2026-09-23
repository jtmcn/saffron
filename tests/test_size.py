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
    lines += [f"-gone{i}" for i in range(removed)]
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
    # Half the bug ceiling plus one on each side is within it alone, but
    # summed the two sides are one token over.
    half = _CEILINGS["bug"] // 2 + 1
    result = size_gate(_diff(added=half, removed=half), "bug", touches=[])
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


def _one_hunk(lines, path="src/a.py"):
    """A single-file, single-hunk diff around hand-picked hunk content.
    `_changed_lines` never validates the `@@` numbers, so a fixed header is
    fine for every case below."""
    return (
        "\n".join(
            [
                f"diff --git a/{path} b/{path}",
                f"--- a/{path}",
                f"+++ b/{path}",
                "@@ -1,1 +1,1 @@",
                *lines,
            ]
        )
        + "\n"
    )


def test_the_count_is_the_fewest_tokens_an_edit_of_each_files_stream_needs():
    assert _changed_lines(_one_hunk(["+x"])) == 1
    assert _changed_lines(_one_hunk(["-x"])) == 1
    assert _changed_lines(_one_hunk(["-x", "+y"])) == 2
    assert _changed_lines(_one_hunk(["+a b c d e"])) == 5
    assert _changed_lines(_one_hunk(["-a b c d e"])) == 5
    assert _changed_lines(_one_hunk(["-A B", "+B A"])) == 2
    assert _changed_lines(_one_hunk(["-alpha beta", " keep", "+alpha beta"])) == 2
    assert (
        _changed_lines(_one_hunk(["-alpha beta alpha", "+beta gamma alpha gamma"])) == 3
    )

    cross_file = _one_hunk(["-p q r"], path="src/a.py") + _one_hunk(
        ["+p q r"], path="src/b.py"
    )
    assert _changed_lines(cross_file) == 6

    two_hunk = (
        "\n".join(
            [
                "diff --git a/src/a.py b/src/a.py",
                "--- a/src/a.py",
                "+++ b/src/a.py",
                "@@ -1,2 +1,1 @@",
                "-A B C D E",
                " x",
                "@@ -3,1 +3,6 @@",
                " y",
                "+A B C D E",
            ]
        )
        + "\n"
    )
    assert _changed_lines(two_hunk) == 4


def test_each_type_is_judged_against_its_re_measured_ceiling_in_tokens():
    ceilings = {
        "bug": 1300,
        "feature": 3000,
        "refactor": 4200,
        "test": 4200,
        "docs": 4200,
        "chore": 4200,
    }
    for spec_type, ceiling in ceilings.items():
        at = size_gate(_diff(added=ceiling, removed=0), spec_type, touches=[])
        assert at.status == "pass"
        assert at.summary == (
            f"{ceiling} changed tokens within the {spec_type} ceiling of {ceiling}"
        )

        over = size_gate(_diff(added=ceiling + 1, removed=0), spec_type, touches=[])
        assert over.status == "fail"
        message = (
            f"{ceiling + 1} changed tokens exceeds the {spec_type} ceiling of {ceiling}"
        )
        assert over.summary == message
        assert over.failures[0].message == message


_ESTIMATE_PHRASE = "past the token-diff bound, estimated at 4 tokens a changed line"


def test_a_file_past_the_token_diff_bound_is_estimated_from_its_changed_lines():
    # Under the bound: an exact reversal of 30,000 distinct tokens. LCS of a
    # sequence and its exact reverse is 1, so the count is exact: 59998.
    under_tokens = [f"r{i}" for i in range(30_000)]
    under = _one_hunk(
        ["-" + " ".join(under_tokens), "+" + " ".join(reversed(under_tokens))],
        path="src/under.py",
    )
    result = size_gate(under, "bug", touches=[])
    assert result.summary.startswith("59998 changed tokens")
    assert "src/under.py" not in result.summary

    # Past the bound: 32,000 reversed tokens behind a shared first and
    # last token, and one unchanged context line, trim to a 1.024e9 product.
    middle = [f"m{i}" for i in range(32_000)]
    old_line = "FIRST " + " ".join(middle) + " LAST"
    new_line = "FIRST " + " ".join(reversed(middle)) + " LAST"
    shared = _one_hunk([" keep", "-" + old_line, "+" + new_line], path="src/shared.py")
    result = size_gate(shared, "bug", touches=[])
    assert result.summary.startswith("8 changed tokens")
    assert f"src/shared.py {_ESTIMATE_PHRASE}" in result.summary

    # First token of a 40,000-token line replaced: trimming the shared
    # suffix leaves one token each side, well under the bound.
    big = [f"b{i}" for i in range(40_000)]
    first_new = big.copy()
    first_new[0] = "REPLACED"
    first = _one_hunk(
        ["-" + " ".join(big), "+" + " ".join(first_new)], path="src/first.py"
    )
    result = size_gate(first, "bug", touches=[])
    assert result.summary.startswith("2 changed tokens")
    assert "src/first.py" not in result.summary

    # Last token of the same shape of line replaced: the mirror case.
    last_new = big.copy()
    last_new[-1] = "REPLACED"
    last = _one_hunk(
        ["-" + " ".join(big), "+" + " ".join(last_new)], path="src/last.py"
    )
    result = size_gate(last, "bug", touches=[])
    assert result.summary.startswith("2 changed tokens")
    assert "src/last.py" not in result.summary

    # The same 40,000 tokens re-wrapped onto 4,000 added lines: identical
    # content and order, so trimming leaves nothing.
    wrap_lines = ["+" + " ".join(big[i : i + 10]) for i in range(0, len(big), 10)]
    wrap = _one_hunk(["-" + " ".join(big), *wrap_lines], path="src/wrap.py")
    result = size_gate(wrap, "bug", touches=[])
    assert result.summary.startswith("0 changed tokens")
    assert "src/wrap.py" not in result.summary

    # A sixth diff: the shared-ends file beside a small file with one token
    # replaced. The small file is diffed exactly and stays unnamed.
    other = _one_hunk(["-one", "+two"], path="src/other.py")
    combined = shared + other
    result = size_gate(combined, "bug", touches=[])
    assert result.summary.startswith("10 changed tokens")
    assert f"src/shared.py {_ESTIMATE_PHRASE}" in result.summary
    assert "src/other.py" not in result.summary

    # A seventh diff: two files both past the bound. Both must be named,
    # not only the first, so a join that silently drops the rest is caught.
    shared2 = _one_hunk(
        [" keep", "-" + old_line, "+" + new_line], path="src/shared2.py"
    )
    two_estimated = shared + shared2
    result = size_gate(two_estimated, "bug", touches=[])
    assert result.summary.startswith("16 changed tokens")
    assert f"src/shared.py, src/shared2.py {_ESTIMATE_PHRASE}" in result.summary


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


# Nine ways to move whitespace without changing a token. Each is wrapped in
# an unchanged line before and after, so the move sits inside a hunk.
_WHITESPACE_MOVES = {
    "a line split in two": ("alpha beta gamma delta\n", "alpha beta\ngamma delta\n"),
    "two lines joined": ("alpha beta\ngamma delta\n", "alpha beta gamma delta\n"),
    "a string spread over five lines packed onto one": (
        "alpha\nbeta\ngamma\ndelta\nepsilon\n",
        "alpha beta gamma delta epsilon\n",
    ),
    "a block re-indented": ("alpha\nbeta\n", "    alpha\n    beta\n"),
    "spaces widened inside a line": ("alpha beta\n", "alpha    beta\n"),
    "a tab replacing spaces": ("alpha beta\n", "alpha\tbeta\n"),
    "a blank line added": ("alpha\n", "alpha\n\n"),
    "a blank line removed": ("alpha\n\n", "alpha\n"),
    "trailing spaces added": ("alpha beta\n", "alpha beta   \n"),
}


def test_a_change_that_only_moves_whitespace_counts_no_tokens(tmp_path):
    for index, (name, (before, after)) in enumerate(_WHITESPACE_MOVES.items()):
        plain_dir = tmp_path / f"plain{index}"
        plain_dir.mkdir()
        content_before = f"keep_before token{index}\n{before}keep_after token{index}\n"
        content_after = f"keep_before token{index}\n{after}keep_after token{index}\n"
        run = _real_repo(plain_dir, {"a.py": content_before})
        diff = _real_diff(plain_dir, run, {"a.py": content_after})
        result = size_gate(diff, "bug", touches=[])
        assert result.summary.startswith("0 changed tokens"), name

        # The same move, plus one replaced token on a wrapping line: the
        # move still counts nothing, and the replaced token counts 2.
        paired_dir = tmp_path / f"paired{index}"
        paired_dir.mkdir()
        paired_after = f"keep_before changed{index}\n{after}keep_after token{index}\n"
        run = _real_repo(paired_dir, {"a.py": content_before})
        diff = _real_diff(paired_dir, run, {"a.py": paired_after})
        result = size_gate(diff, "bug", touches=[])
        assert result.summary.startswith("2 changed tokens"), name


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

    # A real declaration that this file is not in — not `touches=[]`, which
    # declares nothing and therefore constrains nothing: `scope` skips it, so
    # an empty list is the one case where nothing else covers the file either.
    result = size_gate(diff, "bug", touches=["src/**"])
    assert result.status != "error"


def test_a_spec_declaring_no_touches_does_not_get_a_free_hidden_rewrite(tmp_path):
    """`touches: []` is optional and `scope` skips it outright, so treating an
    empty list as "nothing is declared" would leave the one spec shape where a
    hidden rewrite is both unmeasurable and unremarked — the escape this gate
    exists to close, reachable by omitting a frontmatter field."""
    run = _real_repo(tmp_path, {"a.py": "x = 1\n", ".gitattributes": "*.py -diff\n"})
    rewritten = "\n".join(f"y{i} = {i}" for i in range(2000)) + "\n"
    diff = _real_diff(tmp_path, run, {"a.py": rewritten})

    assert size_gate(diff, "bug", touches=[]).status == "error"


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
    assert "3 changed tokens" in result.summary


def test_a_real_binary_inside_touches_is_refused_where_the_gate_blocks(tmp_path):
    """Not a `-diff` gitattribute — actual bytes, which is the case the fix's
    own tests never built. No diff can tell a genuine asset from a text file
    hidden as one, so where the verdict blocks the gate refuses both, and the
    accepted cost is that a task adding a PNG inside `touches` at `elevated`
    aborts rather than passing unmeasured."""
    run = _real_repo(tmp_path, {"src/a.py": "x = 1\n"})
    (tmp_path / "src" / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n" + bytes(400))
    run("git", "add", "-A")
    # `DIFF_FLAGS` and `check=True`, like `_real_diff`: a repo-local
    # `diff.noprefix` or a failing git would otherwise empty this diff and the
    # assertion below would read as a gate defect rather than a harness one.
    diff = subprocess.run(
        ["git", "diff", "--cached", *worktree.DIFF_FLAGS],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "Binary files" in diff

    blocked = size_gate(diff, "bug", ["src/**"], blocking=True)
    assert blocked.status == "error"
    assert "logo.png" in blocked.summary

    advisory = size_gate(diff, "bug", ["src/**"], blocking=False)
    assert advisory.status == "pass"
    assert "logo.png" in advisory.summary
