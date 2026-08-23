from __future__ import annotations

import subprocess

from saffron.cell import worktree
from saffron.gates.core.integrity import integrity_gate
from saffron.repos.policy import IntegrityPatterns

PATTERNS = IntegrityPatterns(
    test_paths=["tests/**"],
    suppressions=["@pytest.mark.skip", "# type: ignore"],
    gate_config=["pyproject.toml"],
)

TESTS = "def test_a():\n    assert 1 == 1\n\n\ndef test_b():\n    assert 2 == 2\n"


def _repo(tmp_path, files):
    run = lambda *a: subprocess.run(a, cwd=tmp_path, check=True, capture_output=True)  # noqa: E731
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


def _diff(tmp_path, run, changes):
    for name, content in changes.items():
        path = tmp_path / name
        if content is None:
            path.unlink()
        else:
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


def test_an_added_suppression_fails_and_names_the_token(tmp_path):
    run = _repo(tmp_path, {"src/a.py": "x = 1\n"})
    diff = _diff(tmp_path, run, {"src/a.py": "x = 1  # type: ignore\n"})
    result = integrity_gate(diff, PATTERNS, touches=["src/b.py"])
    assert result.status == "fail"
    assert result.failures[0].code == "added-suppression"
    assert "# type: ignore" in result.failures[0].message


def test_a_suppression_is_not_exempt_when_the_spec_declared_the_file(tmp_path):
    """The finding that sank the first draft. `scope` already requires every
    changed file to be inside `touches`, so exempting a line-level check by a
    file-level key nullifies it: every scope-passing diff would be exempt."""
    run = _repo(tmp_path, {"tests/test_a.py": TESTS})
    diff = _diff(
        tmp_path,
        run,
        {"tests/test_a.py": "import pytest\n\n\n@pytest.mark.skip\n" + TESTS},
    )
    result = integrity_gate(diff, PATTERNS, touches=["tests/test_a.py"])
    assert result.status == "fail"
    assert result.failures[0].code == "added-suppression"


def test_prose_quoting_a_token_fails_and_that_is_the_accepted_cost(tmp_path):
    """Correction 3's false positive, kept deliberately. A `fail` reaches the
    repair loop naming the file, line and token; a gate that never fires does
    not (§5.4). The repair is to reword the docstring."""
    run = _repo(tmp_path, {"src/a.py": "x = 1\n"})
    diff = _diff(tmp_path, run, {"src/a.py": 'x = 1\n"""quotes # type: ignore"""\n'})
    result = integrity_gate(diff, PATTERNS, touches=["src/a.py"])
    assert result.status == "fail"
    assert result.failures[0].line == 2


def test_a_gate_config_edit_fails(tmp_path):
    run = _repo(tmp_path, {"pyproject.toml": "[tool.x]\n"})
    diff = _diff(tmp_path, run, {"pyproject.toml": "[tool.x]\ny = 1\n"})
    result = integrity_gate(diff, PATTERNS, touches=["src/a.py"])
    assert result.status == "fail"
    assert result.failures[0].code == "gate-config-changed"


def test_a_gate_config_edit_the_spec_declared_is_exempt(tmp_path):
    run = _repo(tmp_path, {"pyproject.toml": "[tool.x]\n"})
    diff = _diff(tmp_path, run, {"pyproject.toml": "[tool.x]\ny = 1\n"})
    assert integrity_gate(diff, PATTERNS, touches=["pyproject.toml"]).status == "pass"


def test_a_deleted_test_is_not_this_gate_s_business(tmp_path):
    """`census` owns removal. A diff-reading gate answering it was wrong three
    times in three different ways (Appendix M, principle 52)."""
    run = _repo(tmp_path, {"tests/test_x.py": TESTS})
    diff = _diff(tmp_path, run, {"tests/test_x.py": None})
    assert integrity_gate(diff, PATTERNS, touches=["src/a.py"]).status == "pass"


def test_a_suppression_on_a_removed_line_does_not_count(tmp_path):
    run = _repo(tmp_path, {"src/a.py": "x = 1  # type: ignore\n"})
    diff = _diff(tmp_path, run, {"src/a.py": "x = 1\n"})
    assert integrity_gate(diff, PATTERNS, touches=["src/b.py"]).status == "pass"


def test_a_suppression_on_a_context_line_does_not_count(tmp_path):
    run = _repo(tmp_path, {"src/a.py": "x = 1  # type: ignore\ny = 2\n"})
    diff = _diff(tmp_path, run, {"src/a.py": "x = 1  # type: ignore\ny = 3\n"})
    assert integrity_gate(diff, PATTERNS, touches=["src/b.py"]).status == "pass"


def test_the_marker_after_both_sides_parses(tmp_path):
    """Four positions git emits `\\ No newline at end of file`; the reviewed
    patch died on one and had no test (Appendix K). Characterization, one per
    position, each asserting the marker is actually in the fixture — a test
    that does not check for it proves nothing about the marker."""
    run = _repo(tmp_path, {"src/a.py": "x = 1"})
    diff = _diff(tmp_path, run, {"src/a.py": "x = 2"})
    assert diff.count("\\ No newline") == 2
    assert integrity_gate(diff, PATTERNS, touches=[]).status == "pass"


def test_the_marker_after_a_removal_only_parses(tmp_path):
    run = _repo(tmp_path, {"src/a.py": "x = 1"})
    diff = _diff(tmp_path, run, {"src/a.py": "x = 1\n"})
    assert diff.count("\\ No newline") == 1
    assert integrity_gate(diff, PATTERNS, touches=[]).status == "pass"


def test_the_marker_after_an_addition_only_parses(tmp_path):
    run = _repo(tmp_path, {"src/a.py": "x = 1\n"})
    diff = _diff(tmp_path, run, {"src/a.py": "x = 1"})
    assert diff.count("\\ No newline") == 1
    assert integrity_gate(diff, PATTERNS, touches=[]).status == "pass"


def test_the_marker_after_a_context_line_parses(tmp_path):
    """The last line is unchanged and has no newline, so the marker follows a
    context line rather than a `+` or `-` one."""
    run = _repo(tmp_path, {"src/a.py": "x = 1\ny = 2"})
    diff = _diff(tmp_path, run, {"src/a.py": "x = 9\ny = 2"})
    assert "\\ No newline" in diff
    assert integrity_gate(diff, PATTERNS, touches=[]).status == "pass"


def test_a_bent_prefix_errors_rather_than_passing(tmp_path):
    run = _repo(tmp_path, {"src/a.py": "x = 1\n"})
    run("git", "config", "diff.srcPrefix", "x/")
    run("git", "config", "diff.dstPrefix", "y/")
    for name, content in {"src/a.py": "x = 1  # type: ignore\n"}.items():
        (tmp_path / name).write_text(content)
    run("git", "add", "-A")
    bent = subprocess.run(
        ["git", "diff", "--cached"], cwd=tmp_path, capture_output=True, text=True
    ).stdout
    assert integrity_gate(bent, PATTERNS, touches=[]).status == "error"


def test_a_binary_section_is_unreadable_not_unchanged(tmp_path):
    """A `-diff` gitattribute renders a text file as `Binary files ... differ`,
    hiding content but not paths. A file whose added lines cannot be read is a
    file whose suppressions cannot be counted (BACKLOG item 2's close)."""
    run = _repo(tmp_path, {"src/a.py": "x = 1\n", ".gitattributes": "*.py -diff\n"})
    diff = _diff(tmp_path, run, {"src/a.py": "x = 1  # type: ignore\n"})
    assert "Binary files" in diff
    result = integrity_gate(diff, PATTERNS, touches=["src/a.py"])
    assert result.status == "error"
    # Proves the path survived: `Binary files ...` replaces the `---`/`+++`
    # headers, so a gate reading paths only from those would have none here.
    assert "src/a.py" in result.summary


def test_a_binary_section_outside_touches_leaves_the_report_to_scope(tmp_path):
    """A file nobody authorized has already failed `scope`, which is a `fail`
    the agent can repair by deleting it. `repair_loop` checks `aborted_gates`
    before the subtraction, so erroring here would replace that repairable
    failure with an abandoned task charged to nobody."""
    run = _repo(tmp_path, {"src/a.py": "x = 1\n", ".gitattributes": "*.py -diff\n"})
    diff = _diff(tmp_path, run, {"src/a.py": "x = 1  # type: ignore\n"})
    assert integrity_gate(diff, PATTERNS, touches=[]).status != "error"


def test_an_empty_diff_passes():
    assert integrity_gate("", PATTERNS, touches=[]).status == "pass"


def test_no_declared_patterns_skips():
    empty = IntegrityPatterns(test_paths=[], suppressions=[], gate_config=[])
    assert integrity_gate("", empty, touches=[]).status == "skip"


def test_a_form_feed_inside_an_added_line_does_not_hide_a_suppression(tmp_path):
    """`str.splitlines()` also splits on `\\x0c`, `\\r` and friends, which git
    treats as ordinary content. Splitting on them shatters one added line
    into fragments, and a fragment beginning with a space then reads as a
    context line — hiding a suppression the diff actually contains."""
    run = _repo(tmp_path, {"src/a.py": "x = 1\n"})
    diff = _diff(tmp_path, run, {"src/a.py": "x = 1\x0c  # type: ignore\n"})
    result = integrity_gate(diff, PATTERNS, touches=["src/b.py"])
    assert result.status == "fail"
    assert result.failures[0].code == "added-suppression"


def test_a_bare_carriage_return_inside_an_added_line_does_not_hide_a_suppression(
    tmp_path,
):
    """`_diff`'s `text=True` capture applies universal-newlines translation
    and would itself turn a bare `\\r` into a `\\n` before this gate ever saw
    it, masking the parser bug rather than exercising it — so this reads the
    diff as bytes, the same way `worktree.export_patch` reads it in the cell,
    to keep the `\\r` intact end to end."""
    run = _repo(tmp_path, {"src/a.py": "x = 1\n"})
    (tmp_path / "src" / "a.py").write_bytes(b"x = 1\r  # type: ignore\n")
    run("git", "add", "-A")
    diff = subprocess.run(
        ["git", "diff", "--cached", *worktree.DIFF_FLAGS],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    ).stdout.decode()
    assert "\r" in diff
    result = integrity_gate(diff, PATTERNS, touches=["src/b.py"])
    assert result.status == "fail"
    assert result.failures[0].code == "added-suppression"


def test_a_forged_diff_header_inside_an_added_line_does_not_split_the_block(
    tmp_path,
):
    """An added line containing `\\x0c` followed by `diff --git a/x b/x` must
    not be split into a fragment that `_split_blocks` mistakes for the start
    of a new file block — losing the real suppression later in the hunk."""
    run = _repo(tmp_path, {"src/a.py": "one\ntwo\nthree\n"})
    diff = _diff(
        tmp_path,
        run,
        {"src/a.py": "one\x0cdiff --git a/z b/z\ntwo  # type: ignore\nthree\n"},
    )
    result = integrity_gate(diff, PATTERNS, touches=["src/b.py"])
    assert result.status == "fail"
    assert result.failures[0].code == "added-suppression"


def test_a_crlf_file_still_parses_and_reports_its_suppression(tmp_path):
    """`subprocess.run(..., text=True)` applies universal-newlines translation
    and would silently eat the `\\r` before it ever reached git's output, so
    this reads the diff as bytes to keep CRLF intact end to end."""
    run = _repo(tmp_path, {"src/a.py": "placeholder\n"})
    (tmp_path / "src" / "a.py").write_bytes(b"x = 1\r\ny = 2\r\n")
    run("git", "add", "-A")
    run("git", "commit", "-qm", "crlf base")
    (tmp_path / "src" / "a.py").write_bytes(b"x = 1  # type: ignore\r\ny = 2\r\n")
    run("git", "add", "-A")
    diff = subprocess.run(
        ["git", "diff", "--cached", *worktree.DIFF_FLAGS],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    ).stdout.decode()
    assert "\r\n" in diff
    result = integrity_gate(diff, PATTERNS, touches=["src/b.py"])
    assert result.status == "fail"
    assert result.failures[0].code == "added-suppression"


def test_a_path_containing_a_space_matches_touches_and_carries_no_tab(tmp_path):
    """Git appends a TAB after a `---`/`+++` path that contains whitespace.
    An exact `touches` entry must still match it, and no reported `Failure`
    should carry that tab into `file`."""
    run = _repo(tmp_path, {".saffron/my spec.yaml": "a: 1\n"})
    diff = _diff(tmp_path, run, {".saffron/my spec.yaml": "a: 1\nb: 2\n"})
    patterns = IntegrityPatterns(
        test_paths=[], suppressions=[], gate_config=[".saffron/my spec.yaml"]
    )

    exempt = integrity_gate(diff, patterns, touches=[".saffron/my spec.yaml"])
    assert exempt.status == "pass"

    flagged = integrity_gate(diff, patterns, touches=[])
    assert flagged.status == "fail"
    assert flagged.failures[0].file == ".saffron/my spec.yaml"
    assert not flagged.failures[0].file.endswith("\t")
