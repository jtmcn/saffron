"""The spec loop driver's `jev` command: review round numbering, the diff
between review rounds, re-scoring, and the exits that keep a failed call off
the loop."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from typesafe_sdk import TypeSafeError

from tests.test_jev_observe import FakeClient

REPO = Path(__file__).resolve().parents[1]
DRIVER = REPO / ".claude" / "skills" / "run-saffron-spec-loop" / "driver.py"
if "spec_loop_driver" in sys.modules:
    driver = sys.modules["spec_loop_driver"]
else:
    _SPEC = importlib.util.spec_from_file_location("spec_loop_driver", DRIVER)
    assert _SPEC is not None and _SPEC.loader is not None
    driver = importlib.util.module_from_spec(_SPEC)
    sys.modules[_SPEC.name] = driver
    _SPEC.loader.exec_module(driver)

SPEC = """---
id: SA-0901
title: a spec the jev tests score
type: feature
---

## Acceptance criteria

- [ ] it parses
- [ ] it saves
"""
FINDING = {
    "severity": "blocker",
    "criterion": 1,
    "file": "a.py",
    "line": 1,
    "claim": "wrong",
}


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def _commit(root: Path, name: str, text: str) -> str:
    (root / name).write_text(text)
    _git(root, "add", ".")
    _git(root, "commit", "-qm", name)
    return _git(root, "rev-parse", "HEAD")


@pytest.fixture
def loop(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    commits = (
        _commit(root, "spec.md", SPEC),
        _commit(root, "a.py", "x = 1\n"),
        _commit(root, "b.py", "y = 2\n"),
    )
    client = FakeClient()
    monkeypatch.setattr(driver, "JEV_ROOT", tmp_path / "batches")
    monkeypatch.setattr(driver, "_jev_client", lambda: client)
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    return SimpleNamespace(
        root=root,
        commits=commits,
        client=client,
        batches=tmp_path / "batches",
        tmp=tmp_path,
    )


def _report(loop, name: str, findings: list) -> str:
    path = loop.tmp / name
    path.write_text(
        "prose\n\n```json\n" + json.dumps({"findings": findings}) + "\n```\n"
    )
    return str(path)


def _run(monkeypatch, *argv: str) -> int:
    monkeypatch.setattr(sys, "argv", ["driver.py", *argv])
    return driver.main()


def _review(monkeypatch, loop, *extra: str) -> int:
    common = (
        "jev",
        "SA-0901",
        "--kind",
        "pr-review",
        "--spec",
        str(loop.root / "spec.md"),
    )
    return _run(monkeypatch, *common, "--root", str(loop.root), *extra)


def _two_rounds(monkeypatch, loop) -> Path:
    first, second, third = loop.commits
    one = _report(loop, "r1.md", [FINDING])
    assert (
        _review(monkeypatch, loop, "--report", one, "--commit", second, "--base", first)
        == 0
    )
    two = _report(loop, "r2.md", [])
    assert _review(monkeypatch, loop, "--report", two, "--commit", third) == 0
    return loop.batches / "spec-loop" / "SA-0901" / "pr-review"


def test_rounds_number_themselves_and_each_diff_starts_at_the_last_round(
    monkeypatch, loop
):
    base = _two_rounds(monkeypatch, loop)
    assert sorted(p.name for p in base.iterdir()) == ["round-1", "round-2"]
    assert (
        "b.py" in loop.client.state["diff"] and "a.py" not in loop.client.state["diff"]
    )
    assert [f["claim"] for f in loop.client.state["earlier_findings"]] == ["wrong"]
    assert (base / "round-2" / "jev.ttl").is_file()


def test_the_first_round_diffs_from_base(monkeypatch, loop):
    first, second, _ = loop.commits
    one = _report(loop, "r1.md", [FINDING])
    assert (
        _review(monkeypatch, loop, "--report", one, "--commit", second, "--base", first)
        == 0
    )
    assert (
        "a.py" in loop.client.state["diff"] and "b.py" not in loop.client.state["diff"]
    )


def test_scoring_a_round_again_keeps_its_ids_and_its_diff(monkeypatch, loop):
    base = _two_rounds(monkeypatch, loop)
    ids = [
        row["id"]
        for row in json.loads((base / "round-1" / "findings.json").read_text())
    ]
    before = (base / "round-1" / "jev.ttl").read_text()
    assert _review(monkeypatch, loop, "--round", "1") == 0
    assert [
        row["id"]
        for row in json.loads((base / "round-1" / "findings.json").read_text())
    ] == ids
    assert "a.py" in loop.client.state["diff"]
    assert (base / "round-1" / "jev.ttl").read_text() == before
    assert sorted(p.name for p in base.iterdir()) == ["round-1", "round-2"]


def test_both_seats_share_one_round(monkeypatch, loop):
    first, second, _ = loop.commits
    spec_seat = _report(loop, "spec-seat.md", [FINDING])
    standards = _report(loop, "standards.md", [{**FINDING, "claim": "other"}])
    assert (
        _review(
            monkeypatch,
            loop,
            "--report",
            spec_seat,
            "--report",
            standards,
            "--commit",
            second,
            "--base",
            first,
        )
        == 0
    )
    d = loop.batches / "spec-loop" / "SA-0901" / "pr-review" / "round-1"
    assert sorted(p.name for p in d.glob("report-*.md")) == [
        "report-1.md",
        "report-2.md",
    ]
    assert [r["claim"] for r in json.loads((d / "findings.json").read_text())] == [
        "wrong",
        "other",
    ]


def test_a_malformed_block_exits_1_and_writes_no_round(monkeypatch, loop):
    bad = loop.tmp / "bad.md"
    bad.write_text("no block here\n")
    assert (
        _review(monkeypatch, loop, "--report", str(bad), "--commit", loop.commits[1])
        == 1
    )
    assert not loop.batches.exists() and loop.client.questions == {}


def test_no_key_exits_2_before_any_call(monkeypatch, loop):
    monkeypatch.delenv("TYPESAFE_API_KEY")
    one = _report(loop, "r1.md", [FINDING])
    # A resolvable base, so a key check moved below the round's creation is what fails here.
    argv = ("--report", one, "--commit", loop.commits[1], "--base", loop.commits[0])
    assert _review(monkeypatch, loop, *argv) == 2
    assert not loop.batches.exists() and loop.client.questions == {}


def test_a_failed_call_exits_2_and_leaves_the_round_to_score_again(monkeypatch, loop):
    class Down:
        def system_one(self, *args, **kwargs):
            raise TypeSafeError("down")

    monkeypatch.setattr(driver, "_jev_client", Down)
    first, second, _ = loop.commits
    one = _report(loop, "r1.md", [FINDING])
    assert (
        _review(monkeypatch, loop, "--report", one, "--commit", second, "--base", first)
        == 2
    )
    d = loop.batches / "spec-loop" / "SA-0901" / "pr-review" / "round-1"
    assert (d / "findings.json").is_file() and not (d / "jev.ttl").exists()


def test_commit_and_base_resolve_to_shas_and_stay_pinned_on_a_rescore(
    monkeypatch, loop
):
    first, second, third = loop.commits
    _git(loop.root, "branch", "feature", second)
    one = _report(loop, "r1.md", [FINDING])
    assert (
        _review(
            monkeypatch, loop, "--report", one, "--commit", "feature", "--base", first
        )
        == 0
    )
    base = loop.batches / "spec-loop" / "SA-0901" / "pr-review"
    saved = json.loads((base / "round-1" / "round.json").read_text())
    assert saved["commit"] == second
    assert (
        "a.py" in loop.client.state["diff"] and "b.py" not in loop.client.state["diff"]
    )

    _git(loop.root, "branch", "-f", "feature", third)
    assert _review(monkeypatch, loop, "--round", "1") == 0
    saved_again = json.loads((base / "round-1" / "round.json").read_text())
    assert saved_again["commit"] == second
    assert (
        "a.py" in loop.client.state["diff"] and "b.py" not in loop.client.state["diff"]
    )


def test_an_unresolvable_ref_exits_1_before_any_directory(monkeypatch, loop):
    one = _report(loop, "r1.md", [FINDING])
    assert (
        _review(
            monkeypatch,
            loop,
            "--report",
            one,
            "--commit",
            "no-such-ref",
            "--base",
            loop.commits[0],
        )
        == 1
    )
    assert not loop.batches.exists()


def test_round_refuses_report_alongside_it(monkeypatch, loop):
    _two_rounds(monkeypatch, loop)
    extra = _report(loop, "extra.md", [FINDING])
    assert _review(monkeypatch, loop, "--round", "1", "--report", extra) == 1


def test_round_glob_ignores_a_non_numeric_suffix(monkeypatch, loop):
    base = _two_rounds(monkeypatch, loop)
    (base / "round-1.bak").mkdir()
    three = _report(loop, "r3.md", [])
    assert (
        _review(monkeypatch, loop, "--report", three, "--commit", loop.commits[2]) == 0
    )
    assert (base / "round-3").is_dir()


def test_a_corrupt_earlier_findings_file_exits_1_not_a_traceback(monkeypatch, loop):
    base = _two_rounds(monkeypatch, loop)
    (base / "round-1" / "findings.json").write_text("not json")
    three = _report(loop, "r3.md", [])
    assert (
        _review(monkeypatch, loop, "--report", three, "--commit", loop.commits[2]) == 1
    )


def test_a_rerun_cell_clears_a_stale_ttl_before_scoring_again(monkeypatch, loop):
    cell = loop.batches / "v0" / "SA-0901"
    cell.mkdir(parents=True)
    lens = {
        "lens": "adequacy",
        "severity": "note",
        "file": "t.py",
        "line": 5,
        "claim": "weak",
    }
    (cell / "findings.json").write_text(
        json.dumps([{"lens": "adequacy", "findings": [lens]}])
    )
    (cell / "patch.json").write_text(json.dumps({"head_sha": "feedbeef"}))
    (cell / "patch.diff").write_text("diff --git a/t.py b/t.py\n")
    (cell / "jev.ttl").write_text("stale")

    class Down:
        def system_one(self, *args, **kwargs):
            raise TypeSafeError("down")

    monkeypatch.setattr(driver, "_jev_client", Down)
    assert (
        _run(
            monkeypatch,
            "jev",
            "SA-0901",
            "--kind",
            "cell",
            "--spec",
            str(loop.root / "spec.md"),
        )
        == 2
    )
    assert not (cell / "jev.ttl").exists()


def test_a_cell_is_scored_from_its_batch_directory(monkeypatch, loop):
    cell = loop.batches / "v0" / "SA-0901"
    cell.mkdir(parents=True)
    lens = {
        "lens": "adequacy",
        "severity": "note",
        "file": "t.py",
        "line": 5,
        "claim": "weak",
    }
    (cell / "findings.json").write_text(
        json.dumps([{"lens": "adequacy", "findings": [lens]}])
    )
    (cell / "patch.json").write_text(json.dumps({"head_sha": "feedbeef"}))
    (cell / "patch.diff").write_text("diff --git a/t.py b/t.py\n")
    assert (
        _run(
            monkeypatch,
            "jev",
            "SA-0901",
            "--kind",
            "cell",
            "--spec",
            str(loop.root / "spec.md"),
        )
        == 0
    )
    assert '"feedbeef"' in (cell / "jev.ttl").read_text()
    assert {k.split("_", 1)[0] for k in loop.client.questions} == {
        "Q1",
        "Q2",
        "Q3",
        "Q6",
    }


def test_the_spec_is_found_by_its_id(monkeypatch, loop, tmp_path):
    specs = tmp_path / "specs" / "done"
    specs.mkdir(parents=True)
    (specs / "SA-0901-a-spec.md").write_text(SPEC)
    monkeypatch.setattr(driver, "SPECS_DIR", tmp_path / "specs")
    first, second, _ = loop.commits
    one = _report(loop, "r1.md", [FINDING])
    argv = ("jev", "SA-0901", "--kind", "pr-review", "--root", str(loop.root))
    assert (
        _run(monkeypatch, *argv, "--report", one, "--commit", second, "--base", first)
        == 0
    )


def test_other_commands_run_without_the_sdk():
    code = (
        "import runpy, sys; sys.modules['typesafe_sdk'] = None; "
        f"sys.argv = ['driver.py', 'pattern']; runpy.run_path({str(DRIVER)!r}, run_name='__main__')"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr


def _moved_base(loop) -> str:
    """A base branch that moved on after the PR branched. It adds `c.py`."""
    _git(loop.root, "checkout", "-q", "-b", "moved", loop.commits[0])
    moved = _commit(loop.root, "c.py", "z = 3\n")
    _git(loop.root, "checkout", "-q", "main")
    return moved


def test_the_first_round_diffs_from_the_merge_base_when_the_base_moved_on(
    monkeypatch, loop
):
    moved = _moved_base(loop)
    one = _report(loop, "r1.md", [FINDING])
    argv = ("--report", one, "--commit", loop.commits[1], "--base", moved)
    assert _review(monkeypatch, loop, *argv) == 0
    diff = loop.client.state["diff"]
    assert "a.py" in diff and "c.py" not in diff


def test_a_restacked_pr_diffs_whole_from_its_new_merge_base(monkeypatch, loop):
    first, second, _ = loop.commits
    one = _report(loop, "r1.md", [FINDING])
    argv = ("--report", one, "--commit", second, "--base", first)
    assert _review(monkeypatch, loop, *argv) == 0
    moved = _moved_base(loop)
    _git(loop.root, "checkout", "-q", "-b", "restacked", moved)
    _git(loop.root, "cherry-pick", second)
    head = _commit(loop.root, "d.py", "w = 4\n")
    two = _report(loop, "r2.md", [])
    argv = ("--report", two, "--commit", head, "--base", moved)
    assert _review(monkeypatch, loop, *argv) == 0
    diff = loop.client.state["diff"]
    assert "a.py" in diff and "d.py" in diff and "c.py" not in diff
    base = loop.batches / "spec-loop" / "SA-0901" / "pr-review"
    assert json.loads((base / "round-2" / "round.json").read_text())["base"] == moved


def test_a_head_that_does_not_descend_from_the_last_diffs_whole(monkeypatch, loop):
    first, second, _ = loop.commits
    one = _report(loop, "r1.md", [FINDING])
    argv = ("--report", one, "--commit", second, "--base", first)
    assert _review(monkeypatch, loop, *argv) == 0
    _git(loop.root, "checkout", "-q", "-b", "reopened", first)
    head = _commit(loop.root, "d.py", "w = 4\n")
    two = _report(loop, "r2.md", [])
    assert _review(monkeypatch, loop, "--report", two, "--commit", head) == 0
    diff = loop.client.state["diff"]
    assert "d.py" in diff and "a.py" not in diff


def test_a_base_merged_into_the_pr_diffs_whole_from_the_new_merge_base(
    monkeypatch, loop
):
    first, second, _ = loop.commits
    one = _report(loop, "r1.md", [FINDING])
    argv = ("--report", one, "--commit", second, "--base", first)
    assert _review(monkeypatch, loop, *argv) == 0
    moved = _moved_base(loop)
    _git(loop.root, "checkout", "-q", "-b", "merged", second)
    _git(loop.root, "merge", "-q", "--no-edit", moved)
    head = _commit(loop.root, "d.py", "w = 4\n")
    two = _report(loop, "r2.md", [])
    argv = ("--report", two, "--commit", head, "--base", moved)
    assert _review(monkeypatch, loop, *argv) == 0
    diff = loop.client.state["diff"]
    assert "a.py" in diff and "d.py" in diff and "c.py" not in diff


def test_a_rescore_reads_the_spec_the_reviewer_read(monkeypatch, loop):
    _two_rounds(monkeypatch, loop)
    (loop.root / "spec.md").write_text(SPEC + "- [ ] it was added later\n")
    assert _review(monkeypatch, loop, "--round", "1") == 0
    assert loop.client.state["spec"] == SPEC
    assert list(loop.client.state["criteria"].values()) == ["it parses", "it saves"]


def test_a_failed_rescore_clears_the_old_ttl(monkeypatch, loop):
    base = _two_rounds(monkeypatch, loop)

    class Down:
        def system_one(self, *args, **kwargs):
            raise TypeSafeError("down")

    monkeypatch.setattr(driver, "_jev_client", Down)
    assert _review(monkeypatch, loop, "--round", "1") == 2
    assert not (base / "round-1" / "jev.ttl").exists()


def test_a_cell_whose_review_predates_its_latest_run_is_refused(monkeypatch, loop):
    cell = loop.batches / "v0" / "SA-0901"
    cell.mkdir(parents=True)
    (cell / "findings.json").write_text(json.dumps([]))
    (cell / "patch.json").write_text(json.dumps({"head_sha": "feedbeef"}))
    (cell / "patch.diff").write_text("diff --git a/t.py b/t.py\n")
    (cell / "baseline.json").write_text("{}")
    os.utime(cell / "findings.json", (1_000_000, 1_000_000))
    argv = ("jev", "SA-0901", "--kind", "cell", "--spec", str(loop.root / "spec.md"))
    assert _run(monkeypatch, *argv) == 1
    assert loop.client.questions == {} and not (cell / "jev.ttl").exists()
