import subprocess

import pytest

from saffron.agents.findings import Finding, anchor, parse_diff


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout


@pytest.fixture
def repo(tmp_path):
    """A change carrying every diff shape that has ever bitten: a rename, a new
    file, a deleted file, and a file with no trailing newline (Appendix K)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "Test")
    (repo / "alpha.py").write_text("def compute_gap(series):\n    return series\n")
    (repo / "caller.py").write_text(
        "from alpha import compute_gap\n\n\ndef report(series):\n"
        "    return compute_gap(series)\n"
    )
    (repo / "importer.py").write_text("from legacy import LEGACY\n")
    (repo / "unrelated.py").write_text('MAX_RETRIES = "untouched"\n')
    (repo / "legacy.py").write_text("LEGACY = 1\n")
    (repo / "obsolete.py").write_text("GONE = 1\n")
    (repo / "tail.txt").write_text(
        "one\ntwo\nthree\nfour\nfive\nsix\nseven\neight\nnine\nzeta"
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")

    (repo / "alpha.py").write_text(
        "def compute_forecast_gap(series):\n    return series\n"
    )
    (repo / "beta.py").write_text("BETA = 2\n")
    git(repo, "mv", "legacy.py", "modern.py")
    git(repo, "rm", "-q", "obsolete.py")
    (repo / "tail.txt").write_text(
        "uno\ntwo\nthree\nfour\nfive\nsix\nseven\neight\nnine\nomega"
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "the change")
    return repo


@pytest.fixture
def diff(repo):
    return git(repo, "diff", "-M", "HEAD~1", "HEAD")


@pytest.fixture
def read_head(repo):
    """How the host wires it: content at head, None for a file that isn't there."""

    def read(path):
        target = repo / path
        return target.read_text() if target.is_file() else None

    return read


def test_the_fixture_is_real_git_output_with_the_markers_that_bite(diff):
    assert "\\ No newline at end of file" in diff
    assert "--- /dev/null" in diff
    assert "+++ /dev/null" in diff
    assert "rename from legacy.py" in diff


def test_hunk_lines_are_new_file_coordinates(diff):
    facts = parse_diff(diff)
    assert facts.hunk_lines["alpha.py"] == {1, 2}
    assert facts.hunk_lines["beta.py"] == {1}
    # Two hunks in one file, the second reached only if the first was counted
    # right — and the no-newline marker sits inside it.
    assert facts.hunk_lines["tail.txt"] == {1, 2, 3, 4, 7, 8, 9, 10}
    # A deleted file has no new-file line to anchor to, and neither has the
    # `/dev/null` it is diffed against.
    assert set(facts.hunk_lines) == {"alpha.py", "beta.py", "tail.txt"}


def test_no_newline_marker_is_not_content(diff):
    facts = parse_diff(diff)
    assert {"zeta", "omega"} <= facts.tokens
    assert "newline" not in facts.tokens


def test_context_lines_are_not_changed_identifiers(diff):
    # `return series` is context in alpha.py's hunk; only ± lines are changes.
    facts = parse_diff(diff)
    assert "compute_forecast_gap" in facts.tokens
    assert "return" not in facts.tokens


def test_finding_inside_a_hunk_anchors(diff, read_head):
    finding = Finding(
        lens="correctness",
        severity="blocker",
        file="alpha.py",
        line=1,
        claim="renamed function drops the gap check",
    )
    assert anchor([finding], diff, read_head=read_head)[0].anchored


def test_blast_radius_finding_on_an_untouched_line_anchors(diff, read_head):
    """The test that must survive: remove the identifier rule and lens #3 goes
    to zero, silently (§5.5, principle 28)."""
    finding = Finding(
        lens="blast-radius",
        severity="blocker",
        file="caller.py",
        line=5,
        claim="still calls compute_gap, which the diff renamed",
    )
    # Not anchorable by hunk: the diff never touches this file at all.
    assert "caller.py" not in parse_diff(diff).hunk_lines
    assert anchor([finding], diff, read_head=read_head)[0].anchored


def test_a_renamed_file_anchors_its_importer(diff, read_head):
    finding = Finding(
        lens="blast-radius",
        severity="concern",
        file="importer.py",
        line=1,
        claim="imports legacy, which the diff renamed to modern",
    )
    assert anchor([finding], diff, read_head=read_head)[0].anchored


def test_untouched_line_naming_nothing_changed_drops(diff, read_head):
    finding = Finding(
        lens="correctness",
        severity="concern",
        file="unrelated.py",
        line=1,
        claim="the retry count is wrong",
    )
    assert not anchor([finding], diff, read_head=read_head)[0].anchored


def test_hallucinated_file_anchors_nowhere(diff, read_head):
    finding = Finding(
        lens="contract",
        severity="blocker",
        file="saffron/does_not_exist.py",
        line=12,
        claim="the migration is irreversible",
    )
    assert not anchor([finding], diff, read_head=read_head)[0].anchored


def test_line_past_end_of_file_does_not_crash(diff, read_head):
    findings = [
        Finding(lens="l", severity="note", file="alpha.py", line=999, claim="c"),
        Finding(lens="l", severity="note", file="alpha.py", line=0, claim="c"),
    ]
    assert [f.anchored for f in anchor(findings, diff, read_head=read_head)] == [
        False,
        False,
    ]


def test_dropped_findings_are_kept_so_the_drop_rate_is_computable(diff, read_head):
    findings = [
        Finding(
            lens="blast-radius", severity="note", file="alpha.py", line=1, claim="a"
        ),
        Finding(
            lens="blast-radius", severity="note", file="ghost.py", line=1, claim="b"
        ),
        Finding(
            lens="blast-radius", severity="note", file="ghost.py", line=2, claim="c"
        ),
    ]
    reconciled = anchor(findings, diff, read_head=read_head)
    assert [f.claim for f in reconciled] == ["a", "b", "c"]
    dropped = [f for f in reconciled if not f.anchored]
    assert len(dropped) / len(reconciled) == pytest.approx(2 / 3)


def test_severity_is_three_levels_and_nothing_else():
    with pytest.raises(ValueError):
        Finding(lens="l", severity="critical", file="a.py", line=1, claim="c")


def test_diff_shaped_content_is_content(repo):
    """A test fixture containing diff text is ordinary added content — its
    tokens count, and its `@@` line is not a hunk of its own."""
    (repo / "fixture.txt").write_text(
        "@@ -1,1 +1,1 @@\ndiff --git a/x b/x\nGUARD = 1\n"
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "diff-shaped fixture")
    facts = parse_diff(git(repo, "diff", "HEAD~1", "HEAD"))
    assert facts.hunk_lines == {"fixture.txt": {1, 2, 3}}
    assert "GUARD" in facts.tokens


def test_a_patch_file_parses_like_its_diff(repo, diff):
    """`git format-patch` wraps the same diff in a preamble and a `-- <version>`
    epilogue; neither is hunk body."""
    patch = git(repo, "format-patch", "-1", "-M", "--stdout")
    assert patch.rstrip().splitlines()[-2] == "-- "
    assert parse_diff(patch) == parse_diff(diff)
