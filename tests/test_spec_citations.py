"""Tests for `saffron/spec_citations.py`: a spec's `file:line` citations
checked against a git commit. Ported from the spec loop driver's `cite`
command. Each fixture builds its own small repository, so this module shares
no fixture with `tests/test_spec_loop_driver.py`.
"""

from __future__ import annotations

import os
import subprocess

import pytest

# The fixture module these tests cite, with 1-based line numbers.
LIB = [
    "import os",
    "",
    "",
    "def _diff(mirror, head):",
    '    """One layer\'s own commit."""',
    "    return run(mirror, head)",
    "",
    "",
    "def _review_one_layer(",
    "    ledger,",
    "    task_key,",
    "):",
    "    fields = layer_fields(ledger, task_key)",
    "",
    "    diff = _diff(fields.mirror, fields.head)",
    "    return review(diff)",
    "",
    "",
    "def export_saffron_dir(mirror, sha, dest):",
    '    """`.saffron/` under `dest`."""',
    '    archive = dest / "a.tar"',
    "    extract(archive, dest)",
    "    return dest",
    "",
    "",
    "class Ledger:",
    "    def create_batch(self):",
    "        return 1",
    "",
    "",
    "async def run_stack_batch(ledger):",
    "    batch = ledger.create_batch()",
    "    end_review(batch)",
    "    _print_summary(batch)",
    "    return batch",
    "",
    "# def _print_summary sits below",
    "def _print_summary(batch):",
    "    print(batch)",
    "",
    "",
    "def main():",
    "    _print_summary(None)",
    "    # IF NOT EXISTS",
    "",
    "",
    "def _rows(x=[",
    "    1,",
    "]):",
    "    return x",
    "",
    "",
    "def _shape(x={",
    '    "a": 1,',
    "}):",
    "    return x",
    "_diff_cache = {}",
]

_CITATION_POLICY = (
    "citations:\n"
    "  definitions:\n"
    "    - '\\s*(?:async\\s+)?def\\s+{name}\\b'\n"
    "    - '\\s*class\\s+{name}\\b'\n"
)


def _git(cwd, *args):
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def empty_repo(tmp_path, monkeypatch):
    """A git repo on `main` with no commits, blind to the host's git config."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    return tmp_path


@pytest.fixture
def cite_repo(empty_repo):
    """A repo holding `mod/lib.py` (`LIB`), a three-line `pkg/other.py`, and
    a policy declaring `def`, `async def` and `class` as constructs. Returns
    `(repo, base)`."""
    repo = empty_repo
    (repo / "mod").mkdir()
    (repo / "mod" / "lib.py").write_text("\n".join(LIB) + "\n")
    (repo / "pkg").mkdir()
    (repo / "pkg" / "other.py").write_text("x = 1\ny = 2\nz = 3\n")
    (repo / ".saffron").mkdir()
    (repo / ".saffron" / "policy.yaml").write_text(_CITATION_POLICY)
    _git(repo, "add", "mod/lib.py", "pkg/other.py", ".saffron/policy.yaml")
    _git(repo, "commit", "-qm", "fixture")
    base = _git(repo, "rev-parse", "HEAD")
    return repo, base


def test_citation_defects_resolve_each_citation_at_the_given_commit(empty_repo):
    from saffron.repos.mirror import GitError
    from saffron.spec_citations import citation_defects

    repo = empty_repo
    thing = "\n".join(f"line {i}" for i in range(1, 21)) + "\n"  # 20 lines
    (repo / "pkg").mkdir()
    (repo / "pkg" / "thing.py").write_text(thing)
    (repo / "pkg" / "README").write_text("no suffix at all\n")
    (repo / "run.zzz").write_text("a\nb\nc\nd\n")  # 4 lines, an unlisted suffix
    (repo / "pkg" / "sub").mkdir()
    (repo / "pkg" / "sub" / "deep.py").write_text("one\n")
    _git(
        repo,
        "add",
        "pkg/thing.py",
        "pkg/README",
        "run.zzz",
        "pkg/sub/deep.py",
    )
    _git(repo, "commit", "-qm", "fixture")
    base = _git(repo, "rev-parse", "HEAD")

    # A read from the working tree, not the committed blob, would see this.
    (repo / "pkg" / "thing.py").write_text("only\ntwo\n")

    clean = (
        "The loop reads `pkg/thing.py:5` for its shape. It also reads "
        "`pkg/thing.py:20` at the tail. A `localhost:8080` fixture stub sits "
        "beside it, never a citation. Neither is `importlib.util:3`. Nor is "
        "a plain `06:30` deploy window."
    )
    assert citation_defects(repo, base, clean) == []

    defective = clean + (
        " A now-missing `pkg/missing.py:5` citation points at nothing. Another "
        "dangling `dir/README:3` points at nothing too. The range "
        "`pkg/thing.py:2-999` overruns the file. The helper `run.zzz:9` "
        "overruns too. A directory `pkg/sub:3` is cited directly."
    )
    assert [str(d) for d in citation_defects(repo, base, defective)] == [
        f"pkg/missing.py:5: no such file at {base}",
        f"dir/README:3: no such file at {base}",
        f"pkg/thing.py:2-999: pkg/thing.py has 20 lines at {base}",
        f"run.zzz:9: run.zzz has 4 lines at {base}",
        f"pkg/sub:3: no such file at {base}",
    ]

    with pytest.raises(GitError):
        citation_defects(repo, "0" * 40, "See `README.md:1` for the shape.")


def test_citation_defects_anchor_a_bare_line_number_inside_its_own_paragraph(
    empty_repo,
):
    from saffron.spec_citations import citation_defects

    repo = empty_repo
    (repo / "a").mkdir()
    (repo / "b").mkdir()
    (repo / "a" / "thing.py").write_text(
        "\n".join(f"a{i}" for i in range(1, 31)) + "\n"
    )
    (repo / "b" / "other.py").write_text(
        "\n".join(f"b{i}" for i in range(1, 51)) + "\n"
    )
    _git(repo, "add", "a/thing.py", "b/other.py")
    _git(repo, "commit", "-qm", "fixture")
    base = _git(repo, "rev-parse", "HEAD")

    text = (
        "The loop reads `a/thing.py` for its shape. See `:5` for where it starts "
        "and `:31` for the tail.\n"
        "\n"
        "Read `b/other.py:3` for the check. It matches no `importlib.util:2`. "
        "Then `:4` confirms it.\n"
        "\n"
        "Nothing here names a path. See `:9-45` for confirmation.\n"
    )

    assert [str(d) for d in citation_defects(repo, base, text)] == [
        f"a/thing.py:31: a/thing.py has 30 lines at {base}",
        ":9-45: no path named earlier in its paragraph",
    ]


def test_citation_defects_report_quoted_text_that_sits_on_other_lines(empty_repo):
    """None of these candidate words name a `def`, `async def` or `class`
    in `mod/lib.py`. So none of their citations names a construct the file
    holds, and the construct check refuses nothing here."""
    from saffron.spec_citations import citation_defects

    repo = empty_repo
    lines = [f"L{i}" for i in range(1, 72)]
    lines[2] = "alpha marker"  # line 3, "alpha" found elsewhere (case 1)
    lines[4] = "delta marker"  # line 5, "delta" found elsewhere (case 4)
    lines[6] = "alpha marker"  # line 7, "alpha" found elsewhere (case 1)
    lines[8] = "omega marker"  # line 9, "omega" found elsewhere (case 5)
    lines[24] = "beta marker"  # line 25, inside case 2's range, not its first line
    lines[44] = "epsilon marker"  # line 45, inside case 4's range
    lines[64] = "iota marker"  # line 65, inside case 6's range only if merged in
    lines[70] = "theta marker"  # line 71, "theta" found elsewhere (case 6)
    (repo / "mod").mkdir()
    (repo / "mod" / "lib.py").write_text("\n".join(lines) + "\n")
    (repo / ".saffron").mkdir()
    (repo / ".saffron" / "policy.yaml").write_text(_CITATION_POLICY)
    _git(repo, "add", "mod/lib.py", ".saffron/policy.yaml")
    _git(repo, "commit", "-qm", "fixture")
    base = _git(repo, "rev-parse", "HEAD")

    text = (
        # Case 1: a bare citation, "alpha" at two other lines, none in range.
        "The module `mod/lib.py` explains this. The `alpha` value sits at "
        "`:11-20` supposedly.\n"
        "\n"
        # Case 2: a range citation. "beta" sits inside it, below its first line.
        "Here `mod/lib.py:21-30` holds the `beta` reading directly.\n"
        "\n"
        # Case 3: a bare citation. "gamma" sits nowhere in the file at all.
        "The module `mod/lib.py` is unrelated here. It holds `gamma` at "
        "`:31-40` supposedly.\n"
        "\n"
        # Case 4: two strings. "epsilon" is in range and "delta" is not, so no report.
        "Here `delta` and `epsilon` both matter, at `mod/lib.py:41-50` precisely.\n"
        "\n"
        # Case 5: two strings, neither in range. "omega" sits elsewhere, "zeta" nowhere.
        "Both `zeta` and `omega` are claimed, at `mod/lib.py:51-60` exactly.\n"
        "\n"
        # Case 6: a period before a digit must still end the sentence, or the
        # next sentence's "iota" (in range) wrongly suppresses this report.
        "Here `theta` sits far off, at `mod/lib.py:61-70` presently. 9 more "
        "items hold `iota` too.\n"
    )

    assert citation_defects(repo, base, text) == []


def test_citation_defects_judge_a_citation_by_the_construct_its_clause_names(
    cite_repo,
):
    from saffron.spec_citations import citation_defects

    repo, base = cite_repo

    paragraphs = [
        "`_review_one_layer` reads those fields (`mod/lib.py:4-15`).",
        "`_review_one_layer` reads them too (`mod/lib.py:10-16`).",
        "`export_saffron_dir` writes `.saffron/` under its `dest` "
        "(`mod/lib.py:17-22`).",
        "`export_saffron_dir` writes the archive (`mod/lib.py:18-24`).",
        "`run_stack_batch` creates its row at `mod/lib.py:32`.",
        "`Ledger` holds the writer (`mod/lib.py:27-28`).",
        "`Ledger` holds the writer (`mod/lib.py:30-32`).",
        "The module prints through `_print_summary` (`mod/lib.py:43`).",
        "After `_review_one_layer` returns, it calls `end_review` (`mod/lib.py:33`).",
        "`_print_summary` checks `IF NOT EXISTS` (`mod/lib.py:44`).",
        "`os` is read at `mod/lib.py:20`.",
        "`_review_one_layer` builds its diff (`mod/lib.py:15`).",
        "Both `_diff` and `_print_summary` matter (`mod/lib.py:21`).",
        "`git_mirror.export_saffron_dir(mirror, sha, dest)` writes it "
        "(`mod/lib.py:17-22`).",
        "`Ledger.create_batch` returns one (`mod/lib.py:33`).",
        "`_diff()` builds the patch (`mod/lib.py:20`).",
        "`_rows` returns them (`mod/lib.py:50`).",
        "`_shape` returns it (`mod/lib.py:56`).",
        "`_diff` is cached at `mod/lib.py:57`.",
        "`run_stack_batch` returns it (`mod/lib.py:38`).",
    ]
    text = "\n\n".join(paragraphs)

    assert [str(d) for d in citation_defects(repo, base, text)] == [
        "mod/lib.py:4-15: the construct it names sits at mod/lib.py:9-16",
        "mod/lib.py:17-22: the construct it names sits at mod/lib.py:19-23",
        "mod/lib.py:30-32: the construct it names sits at mod/lib.py:26-28",
        "mod/lib.py:44: the construct it names sits at mod/lib.py:38-39",
        "mod/lib.py:21: the construct it names sits at mod/lib.py:4-6, 38-39",
        "mod/lib.py:17-22: the construct it names sits at mod/lib.py:19-23",
        "mod/lib.py:33: the construct it names sits at mod/lib.py:27-28",
        "mod/lib.py:20: the construct it names sits at mod/lib.py:4-6",
        "mod/lib.py:57: the construct it names sits at mod/lib.py:4-6",
        "mod/lib.py:38: the construct it names sits at mod/lib.py:31-35",
    ]


def test_citation_defects_scope_names_to_each_citations_own_clause(cite_repo):
    from saffron.spec_citations import citation_defects

    repo, base = cite_repo

    text = (
        "Every `qualifications` entry carries it (`mod/lib.py:21`), and "
        "`_diff` sits at `mod/lib.py:4-6`.\n"
        "\n"
        "`_print_summary` prints the batch (`mod/lib.py:39`, `:43`).\n"
        "\n"
        "`_diff` returns the patch (`mod/lib.py:5`, `:21`).\n"
        "\n"
        "`_diff` sits in three places (`mod/lib.py:4`, `:5`, `:21`).\n"
        "\n"
        "- `_diff` is the helper\n"
        "- the import sits at `mod/lib.py:1`\n"
        "\n"
        "* `_diff` is the helper\n"
        "* the import sits at `mod/lib.py:1`\n"
        "\n"
        "1. `_diff` is the helper\n"
        "2. the import sits at `mod/lib.py:1`\n"
        "\n"
        "**`_diff` is the helper.** The import sits at `mod/lib.py:1`.\n"
        "\n"
        "**`_diff` is the helper.** `mod/lib.py:1` holds the import.\n"
        "\n"
        "**`_diff` is the helper.** 1 import sits at `mod/lib.py:1`.\n"
        "\n"
        '**`_diff` is the helper.** "The import" sits at `mod/lib.py:1`.\n'
        "\n"
        "**`_diff` is the helper.** *The import* sits at `mod/lib.py:1`.\n"
        "\n"
        "- the module is `mod/lib.py`\n"
        "- `_diff` sits at `:4-6`\n"
        "\n"
        "The helpers live in `pkg/other.py` and `mod/lib.py`. `_diff` returns "
        "the patch (`:4-6`).\n"
        "\n"
        "The helpers live in `pkg/other.py`. `_diff` in `mod/lib.py` returns "
        "the patch (`:4-6`).\n"
        "\n"
        "See `pkg/other.py:1` and `mod/lib.py:4-6`. `_diff` returns it "
        "(`:5`).\n"
        "\n"
        "`_diff` sits at `mod/lib.py:4-6`, and the `qualifications` entry is "
        "at `mod/lib.py:21`.\n"
    )

    assert [str(d) for d in citation_defects(repo, base, text)] == [
        "mod/lib.py:21: the construct it names sits at mod/lib.py:4-6",
        "mod/lib.py:21: the construct it names sits at mod/lib.py:4-6",
    ]


def test_citation_defects_name_a_one_line_construct_alone_and_read_a_tab_indented_body(
    empty_repo,
):
    from saffron.spec_citations import citation_defects

    repo = empty_repo
    (repo / "mod").mkdir()
    (repo / "mod" / "tiny.py").write_text("x = 1\ndef tiny(): pass\ny = 2\n")
    (repo / "mod" / "tabs.py").write_text("def gofunc(x):\n\ty = x\n\treturn y\n")
    (repo / ".saffron").mkdir()
    (repo / ".saffron" / "policy.yaml").write_text(_CITATION_POLICY)
    _git(repo, "add", "mod", ".saffron/policy.yaml")
    _git(repo, "commit", "-qm", "fixture")
    base = _git(repo, "rev-parse", "HEAD")

    text = (
        "`tiny` does nothing (`mod/tiny.py:3`).\n"
        "\n"
        "`gofunc` returns it (`mod/tabs.py:2-3`).\n"
    )

    assert [str(d) for d in citation_defects(repo, base, text)] == [
        "mod/tiny.py:3: the construct it names sits at mod/tiny.py:2"
    ]


def test_citation_defects_read_definition_patterns_from_the_policy_at_the_commit(
    empty_repo,
):
    from saffron.repos.policy import PolicyError
    from saffron.spec_citations import citation_defects

    repo = empty_repo
    (repo / "mod").mkdir()
    (repo / "mod" / "lib.py").write_text("\n".join(LIB) + "\n")
    _git(repo, "add", "mod/lib.py")
    _git(repo, "commit", "-qm", "no policy file")
    no_policy = _git(repo, "rev-parse", "HEAD")

    (repo / ".saffron").mkdir()
    (repo / ".saffron" / "policy.yaml").write_text("gates: {}\n")
    _git(repo, "add", ".saffron/policy.yaml")
    _git(repo, "commit", "-qm", "no citations block")
    no_citations = _git(repo, "rev-parse", "HEAD")

    (repo / ".saffron" / "policy.yaml").write_text(
        "citations:\n  definitions:\n    - '\\s*def\\s+{name}\\b'\n"
    )
    _git(repo, "add", ".saffron/policy.yaml")
    _git(repo, "commit", "-qm", "def only")
    def_only = _git(repo, "rev-parse", "HEAD")

    (repo / ".saffron" / "policy.yaml").write_text(
        "citations:\n  definitions:\n    - 'def foo'\n"
    )
    _git(repo, "add", ".saffron/policy.yaml")
    _git(repo, "commit", "-qm", "invalid")
    invalid = _git(repo, "rev-parse", "HEAD")

    text = (
        "`_review_one_layer` reads those fields (`mod/lib.py:4-15`).\n"
        "\n"
        "`Ledger` holds the writer (`mod/lib.py:30-32`).\n"
    )

    assert citation_defects(repo, no_policy, text) == []
    assert citation_defects(repo, no_citations, text) == []

    # The commit's own policy decides, never the working tree's.
    (repo / ".saffron" / "policy.yaml").write_text(_CITATION_POLICY)
    assert [str(d) for d in citation_defects(repo, def_only, text)] == [
        "mod/lib.py:4-15: the construct it names sits at mod/lib.py:9-16"
    ]

    with pytest.raises(PolicyError):
        citation_defects(repo, invalid, text)


def test_citation_count_and_defects_count_each_citation_and_refuse_a_range_before_line_one_or_reversed(
    empty_repo,
):
    from saffron.spec_citations import citation_count_and_defects, citation_defects

    repo = empty_repo
    (repo / "mod").mkdir()
    (repo / "mod" / "lib.py").write_text("\n".join(LIB) + "\n")
    _git(repo, "add", "mod/lib.py")
    _git(repo, "commit", "-qm", "fixture")
    base = _git(repo, "rev-parse", "HEAD")

    text = (
        "See `mod/lib.py:0`, `mod/lib.py:0-3` and `mod/lib.py:6-2`. Then "
        "`mod/lib.py:1`, `missing.py:0` and `missing.py:3-1`.\n"
        "\n"
        "The module `mod/lib.py` starts at `:0` and runs `:9-4`.\n"
    )

    expected = [
        "mod/lib.py:0: starts before line 1",
        "mod/lib.py:0-3: starts before line 1",
        "mod/lib.py:6-2: ends before it starts",
        "missing.py:0: starts before line 1",
        "missing.py:3-1: ends before it starts",
        "mod/lib.py:0: starts before line 1",
        "mod/lib.py:9-4: ends before it starts",
    ]

    count, defects = citation_count_and_defects(repo, base, text)
    assert count == 8
    assert [str(d) for d in defects] == expected
    assert [str(d) for d in citation_defects(repo, base, text)] == expected


def _held_from_own_name(defects):
    """Every defect's offset whose clause names exactly one name, mapped
    to that name, whether or not that name opens exactly one construct.
    `rewrite_moved_citations` itself must still refuse one that opens
    more than one, such as `twin` below."""
    held = {}
    for defect in defects:
        if defect.spans and len(defect.spans) == 1:
            ((name, _spans),) = defect.spans.items()
            held[defect.offset] = name
    return held


def test_a_citation_whose_construct_sits_at_one_span_is_rewritten_to_that_span(
    cite_repo,
):
    from saffron.spec_citations import citation_defects, rewrite_moved_citations

    repo, base = cite_repo
    (repo / "mod" / "tiny.py").write_text("x = 1\ndef tiny(): pass\ny = 2\nz = 3\n")
    _git(repo, "add", "mod/tiny.py")
    _git(repo, "commit", "-qm", "tiny")
    base = _git(repo, "rev-parse", "HEAD")

    text = (
        "`_review_one_layer` reads\n"
        "  those fields (`mod/lib.py:4-15`).\n"
        "\n"
        "`_print_summary` checks `IF NOT EXISTS` (`mod/lib.py:44`).\n"
        "\n"
        "`tiny` does nothing (`mod/tiny.py:3-4`).\n"
        "\n"
        "The module `mod/lib.py` holds `Ledger` at `:30-32`.\n"
        "\n"
        "The module `mod/tiny.py` holds `tiny` at `:4`.\n"
        "\n"
        "`export_saffron_dir` writes it (`mod/lib.py:21`).\n"
        "\n"
        "`_diff` returns it (`mod/lib.py:21`), and `tiny` does nothing "
        "(`mod/tiny.py:3`).\n"
    )

    defects = citation_defects(repo, base, text)
    assert [str(d) for d in defects] == [
        "mod/lib.py:4-15: the construct it names sits at mod/lib.py:9-16",
        "mod/lib.py:44: the construct it names sits at mod/lib.py:38-39",
        "mod/tiny.py:3-4: the construct it names sits at mod/tiny.py:2",
        "mod/lib.py:30-32: the construct it names sits at mod/lib.py:26-28",
        "mod/tiny.py:4: the construct it names sits at mod/tiny.py:2",
        "mod/lib.py:21: the construct it names sits at mod/lib.py:4-6",
        "mod/tiny.py:3: the construct it names sits at mod/tiny.py:2",
    ]

    held = _held_from_own_name(defects)
    new_text, rewrites, left = rewrite_moved_citations(text, defects, held)

    assert left == []
    assert [(r.path, r.old, r.new) for r in rewrites] == [
        ("mod/lib.py", "4-15", "9-16"),
        ("mod/lib.py", "44", "38-39"),
        ("mod/tiny.py", "3-4", "2"),
        ("mod/lib.py", "30-32", "26-28"),
        ("mod/tiny.py", "4", "2"),
        ("mod/lib.py", "21", "4-6"),
        ("mod/tiny.py", "3", "2"),
    ]
    expected_text = (
        text.replace("mod/lib.py:4-15", "mod/lib.py:9-16")
        .replace("mod/lib.py:44", "mod/lib.py:38-39")
        .replace("mod/tiny.py:3-4", "mod/tiny.py:2")
        .replace(":30-32", ":26-28")
        .replace(":4`", ":2`")
        .replace(
            "`_diff` returns it (`mod/lib.py:21`)",
            "`_diff` returns it (`mod/lib.py:4-6`)",
        )
        .replace("(`mod/tiny.py:3`).\n", "(`mod/tiny.py:2`).\n")
    )
    assert new_text == expected_text
    assert citation_defects(repo, base, new_text) == []
    held_again = _held_from_own_name(citation_defects(repo, base, new_text))
    _, rewrites_again, left_again = rewrite_moved_citations(
        new_text, citation_defects(repo, base, new_text), held_again
    )
    assert rewrites_again == []
    assert left_again == []


def test_a_citation_defect_with_no_single_span_is_left_and_its_text_kept(cite_repo):
    from saffron.spec_citations import citation_defects, rewrite_moved_citations

    repo, base = cite_repo
    (repo / "mod" / "tiny.py").write_text("x = 1\ndef tiny(): pass\ny = 2\nz = 3\n")
    (repo / "mod" / "twice.py").write_text(
        "def twin():\n    return 1\n\ndef twin():\n    return 2\n"
    )
    _git(repo, "add", "mod/tiny.py", "mod/twice.py")
    _git(repo, "commit", "-qm", "twice")
    base = _git(repo, "rev-parse", "HEAD")

    text = (
        "The `_diff` helper sits at `:4-6`.\n"
        "\n"
        "See `mod/lib.py:0` for it.\n"
        "\n"
        "See `mod/lib.py:6-2` for it.\n"
        "\n"
        "`tiny` does nothing (`mod/tiny.py:3`).\n"
        "\n"
        "See `gone.py:1` for it.\n"
        "\n"
        "See `pkg/other.py:9` for it.\n"
        "\n"
        "`twin` returns its value (`mod/twice.py:3`).\n"
    )

    defects = citation_defects(repo, base, text)
    assert [str(d) for d in defects] == [
        ":4-6: no path named earlier in its paragraph",
        "mod/lib.py:0: starts before line 1",
        "mod/lib.py:6-2: ends before it starts",
        "mod/tiny.py:3: the construct it names sits at mod/tiny.py:2",
        f"gone.py:1: no such file at {base}",
        f"pkg/other.py:9: pkg/other.py has 3 lines at {base}",
        "mod/twice.py:3: the construct it names sits at mod/twice.py:1-2, 4-5",
    ]

    held = _held_from_own_name(defects)
    new_text, rewrites, left = rewrite_moved_citations(text, defects, held)

    assert [str(d) for d in left] == [
        ":4-6: no path named earlier in its paragraph",
        "mod/lib.py:0: starts before line 1",
        "mod/lib.py:6-2: ends before it starts",
        f"gone.py:1: no such file at {base}",
        f"pkg/other.py:9: pkg/other.py has 3 lines at {base}",
        "mod/twice.py:3: the construct it names sits at mod/twice.py:1-2, 4-5",
    ]
    assert new_text == text.replace("(`mod/tiny.py:3`).\n", "(`mod/tiny.py:2`).\n")
    assert len(rewrites) == 1
    assert rewrites[0].path == "mod/tiny.py"
    assert rewrites[0].old == "3"
    assert rewrites[0].new == "2"


def test_a_use_site_citation_is_left_while_its_definition_citation_is_rewritten(
    empty_repo,
):
    from saffron.spec_citations import (
        citation_defects,
        citations_held_at,
        rewrite_moved_citations,
    )

    repo = empty_repo
    cli_first = [
        "def _mirror_path(repo, home):",
        "    digest = repo",
        "    return home / digest",
        "",
        "",
        "def package(repo, home):",
        "    x = 1",
        "    y = 2",
        "    mirror_path = _mirror_path(repo, home)",
        "    return mirror_path",
    ]
    prelude = ["import os", "", ""]
    pair_first = ["def alpha():", "    return 1", "", "", "def beta():", "    return 2"]
    twin_first = ["def twin():", "    return 1", "", "", "def twin():", "    return 2"]
    nest = ["def outer():", "    def inner():", "        return 1", "    return inner"]
    both_first = [
        "def one():",
        "    return 1",
        "def two():",
        "    x = 1",
        "    return x",
    ]
    even_first = ["def left():", "    return 1", "def right():", "    return 2"]

    (repo / "mod").mkdir()
    (repo / ".saffron").mkdir()
    (repo / ".saffron" / "policy.yaml").write_text(_CITATION_POLICY)
    (repo / "mod" / "cli.py").write_text("\n".join(cli_first) + "\n")
    (repo / "mod" / "pair.py").write_text("\n".join(pair_first) + "\n")
    (repo / "mod" / "twin.py").write_text("\n".join(twin_first) + "\n")
    (repo / "mod" / "nest.py").write_text("\n".join(nest) + "\n")
    (repo / "mod" / "both.py").write_text("\n".join(both_first) + "\n")
    (repo / "mod" / "even.py").write_text("\n".join(even_first) + "\n")
    _git(repo, "add", "mod", ".saffron")
    _git(repo, "commit", "-qm", "first")
    first = _git(repo, "rev-parse", "HEAD")

    (repo / "mod" / "cli.py").write_text("\n".join(prelude + cli_first) + "\n")
    (repo / "mod" / "pair.py").write_text(
        "\n".join(prelude + ["def beta():", "    return 2"]) + "\n"
    )
    (repo / "mod" / "twin.py").write_text(
        "\n".join(prelude + ["def twin():", "    return 2"]) + "\n"
    )
    (repo / "mod" / "new.py").write_text("def fresh():\n    return 1\n")
    (repo / "mod" / "nest.py").write_text("\n".join(prelude + nest) + "\n")
    (repo / "mod" / "both.py").write_text(
        "\n".join(prelude + ["", ""] + both_first) + "\n"
    )
    (repo / "mod" / "even.py").write_text("\n".join(prelude + even_first) + "\n")
    _git(repo, "add", "mod")
    _git(repo, "commit", "-qm", "second")
    second = _git(repo, "rev-parse", "HEAD")

    text = (
        "`_mirror_path` and the blank line after it sit at `mod/cli.py:1-4`.\n"
        "\n"
        "`_mirror_path` returns its path at `mod/cli.py:3`.\n"
        "\n"
        "It builds `mirror_path` with `_mirror_path(repo, home)` and hands it "
        "over (`mod/cli.py:9-10`).\n"
        "\n"
        "`_mirror_path` is called at `mod/cli.py:12`.\n"
        "\n"
        "`fresh` returns one at `mod/new.py:1-2`.\n"
        "\n"
        "`_mirror_path` sits at `:1-3`.\n"
        "\n"
        "`_mirror_path` sits at `mod/cli.py:3-1`.\n"
        "\n"
        "`digest` is read at `mod/cli.py:2`.\n"
        "\n"
        "`alpha` and `beta` both matter (`mod/pair.py:2`).\n"
        "\n"
        "`twin` returns one (`mod/twin.py:2`).\n"
        "\n"
        "`outer` returns `inner` (`mod/nest.py:2-3`).\n"
        "\n"
        "`inner` is returned by `outer` (`mod/nest.py:2-3`).\n"
        "\n"
        "`two` and `one` sit together (`mod/both.py:1-5`).\n"
        "\n"
        "`left` and `right` sit together (`mod/even.py:1-4`).\n"
    )

    held = citations_held_at(repo, first, text)
    nest_offset = text.index("mod/nest.py:2-3")
    nest_offset_2 = text.index("mod/nest.py:2-3", nest_offset + 1)
    assert held == {
        text.index("mod/cli.py:1-4"): "_mirror_path",
        text.index("mod/cli.py:3`"): "_mirror_path",
        text.index("mod/pair.py:2"): "alpha",
        nest_offset: "inner",
        nest_offset_2: "inner",
    }

    defects = citation_defects(repo, second, text)
    assert [str(d) for d in defects] == [
        "mod/cli.py:1-4: the construct it names sits at mod/cli.py:4-6",
        "mod/cli.py:3: the construct it names sits at mod/cli.py:4-6",
        "mod/cli.py:9-10: the construct it names sits at mod/cli.py:4-6",
        ":1-3: no path named earlier in its paragraph",
        "mod/cli.py:3-1: ends before it starts",
        "mod/pair.py:2: the construct it names sits at mod/pair.py:4-5",
        "mod/twin.py:2: the construct it names sits at mod/twin.py:4-5",
        "mod/nest.py:2-3: the construct it names sits at mod/nest.py:4-7, 5-6",
        "mod/nest.py:2-3: the construct it names sits at mod/nest.py:4-7, 5-6",
        "mod/both.py:1-5: the construct it names sits at mod/both.py:6-7, 8-10",
        "mod/even.py:1-4: the construct it names sits at mod/even.py:4-5, 6-7",
    ]

    new_text, rewrites, left = rewrite_moved_citations(text, defects, held)

    assert new_text == (
        text.replace("mod/cli.py:1-4", "mod/cli.py:4-6")
        .replace("mod/cli.py:3`", "mod/cli.py:4-6`")
        .replace("mod/nest.py:2-3", "mod/nest.py:5-6")
    )
    assert [str(d) for d in left] == [
        "mod/cli.py:9-10: the construct it names sits at mod/cli.py:4-6",
        ":1-3: no path named earlier in its paragraph",
        "mod/cli.py:3-1: ends before it starts",
        "mod/pair.py:2: the construct it names sits at mod/pair.py:4-5",
        "mod/twin.py:2: the construct it names sits at mod/twin.py:4-5",
        "mod/both.py:1-5: the construct it names sits at mod/both.py:6-7, 8-10",
        "mod/even.py:1-4: the construct it names sits at mod/even.py:4-5, 6-7",
    ]


def test_a_bare_citation_is_held_by_the_file_the_later_check_anchors_it_to(
    empty_repo,
):
    """A suffix the later commit adds makes `x.rs` read as a path, so the
    check anchors the bare `:1-2` to `x.rs`. Held with the later tree's
    tokens, it anchors there at the spec's own commit too, where `x.rs`
    is missing, so nothing holds it. The rewrite leaves it, rather than
    moving a correct `mod/a.py:1-2` onto `x.rs:5-6`."""
    from saffron.spec_citations import (
        citation_defects,
        citations_held_at,
        rewrite_moved_citations,
    )

    repo = empty_repo
    (repo / ".saffron").mkdir()
    (repo / ".saffron" / "policy.yaml").write_text(_CITATION_POLICY)
    (repo / "mod").mkdir()
    (repo / "mod" / "a.py").write_text("def thing():\n    return 1\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "own")
    own = _git(repo, "rev-parse", "HEAD")
    (repo / "x.rs").write_text("\n\n\n\ndef thing():\n    return 2\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "later")
    head = _git(repo, "rev-parse", "HEAD")
    text = "The module `mod/a.py` and `x.rs` hold `thing` at `:1-2`.\n"

    defects = citation_defects(repo, head, text)
    assert [str(d) for d in defects] == [
        "x.rs:1-2: the construct it names sits at x.rs:5-6"
    ]
    assert citations_held_at(repo, own, text) == {text.index(":1-2"): "thing"}
    held = citations_held_at(repo, own, text, tokens_at=head)
    assert held == {}

    new_text, rewrites, left = rewrite_moved_citations(text, defects, held)
    assert new_text == text
    assert rewrites == []
    assert left == defects
