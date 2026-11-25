"""The spec loop driver's `save-round` command: review round numbering, what
each review round saves, and the `labels` check that reads them."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

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
title: a spec the save-round tests save
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
    monkeypatch.setattr(driver, "BATCHES", tmp_path / "batches")
    return SimpleNamespace(
        root=root,
        commits=commits,
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
        "save-round",
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


def test_rounds_number_themselves_and_save_what_the_reviewer_read(monkeypatch, loop):
    base = _two_rounds(monkeypatch, loop)
    assert sorted(p.name for p in base.iterdir()) == ["round-1", "round-2"]
    one = base / "round-1"
    assert (one / "spec.md").read_text() == SPEC
    assert [f["claim"] for f in json.loads((one / "findings.json").read_text())] == [
        "wrong"
    ]
    assert json.loads((base / "round-2" / "findings.json").read_text()) == []


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
    assert not loop.batches.exists()


def test_commit_and_base_resolve_to_shas(monkeypatch, loop):
    first, second, _ = loop.commits
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
    assert saved["base"] == first


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


def test_round_glob_ignores_a_non_numeric_suffix(monkeypatch, loop):
    base = _two_rounds(monkeypatch, loop)
    (base / "round-1.bak").mkdir()
    three = _report(loop, "r3.md", [])
    assert (
        _review(monkeypatch, loop, "--report", three, "--commit", loop.commits[2]) == 0
    )
    assert (base / "round-3").is_dir()


def test_a_cell_is_saved_from_its_batch_directory(monkeypatch, loop):
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
    assert (
        _run(
            monkeypatch,
            "save-round",
            "SA-0901",
            "--kind",
            "cell",
            "--spec",
            str(loop.root / "spec.md"),
        )
        == 0
    )
    saved = loop.batches / "spec-loop" / "SA-0901" / "cell" / "round-1"
    assert json.loads((saved / "round.json").read_text()) == {"commit": "feedbeef"}
    rows = json.loads((saved / "findings.json").read_text())
    assert [(r["severity"], r["criterion"], r["claim"]) for r in rows] == [
        ("note", None, "weak")
    ]


def test_the_spec_is_found_by_its_id(monkeypatch, loop, tmp_path):
    specs = tmp_path / "specs" / "done"
    specs.mkdir(parents=True)
    (specs / "SA-0901-a-spec.md").write_text(SPEC)
    monkeypatch.setattr(driver, "SPECS_DIR", tmp_path / "specs")
    first, second, _ = loop.commits
    one = _report(loop, "r1.md", [FINDING])
    argv = ("save-round", "SA-0901", "--kind", "pr-review", "--root", str(loop.root))
    assert (
        _run(monkeypatch, *argv, "--report", one, "--commit", second, "--base", first)
        == 0
    )


def test_a_cell_whose_review_predates_its_latest_run_is_refused(monkeypatch, loop):
    cell = loop.batches / "v0" / "SA-0901"
    cell.mkdir(parents=True)
    (cell / "findings.json").write_text(json.dumps([]))
    (cell / "patch.json").write_text(json.dumps({"head_sha": "feedbeef"}))
    (cell / "gates").mkdir()
    os.utime(cell / "findings.json", (1_000_000, 1_000_000))
    spec = str(loop.root / "spec.md")
    argv = ("save-round", "SA-0901", "--kind", "cell", "--spec", spec)
    assert _run(monkeypatch, *argv) == 1
    assert not (loop.batches / "spec-loop").exists()


def test_save_round_and_record_read_one_cell_directory_alike(monkeypatch, loop):
    """b-a09d30: the cell save anchored on `baseline.json` where `record` reads `gates/`."""
    cell = loop.batches / "v0" / "SA-0901"
    (cell / "gates").mkdir(parents=True)
    os.utime(cell / "gates", (1_000_000, 1_000_000))
    (cell / "findings.json").write_text(json.dumps([]))
    os.utime(cell / "findings.json", (2_000_000, 2_000_000))
    (cell / "baseline.json").write_text("{}")
    (cell / "patch.json").write_text(json.dumps({"head_sha": "feedbeef"}))
    found = driver._save_cell("SA-0901", "spec")
    assert not isinstance(found, int), found


def _label_all(round_dir: Path, **override) -> None:
    ids = [f["id"] for f in json.loads((round_dir / "findings.json").read_text())]
    label = {
        "verified": "real",
        "disposition": "fixed-in-review",
        "recurred_in": [],
        "item": None,
    }
    doc = {
        "blocker_followed": {
            "next_spec_round": None,
            "cell_review": None,
            "pr_seats": None,
        },
        "findings": {fid: {**label, **override} for fid in ids},
    }
    (round_dir / "labels.json").write_text(json.dumps(doc))


def test_labels_passes_only_when_every_saved_round_is_labelled(
    monkeypatch, loop, capsys
):
    base = _two_rounds(monkeypatch, loop)
    _label_all(base / "round-1")
    assert _run(monkeypatch, "labels", "SA-0901") == 1
    assert "pr-review round-2  no labels.json" in capsys.readouterr().out

    _label_all(base / "round-2")
    assert _run(monkeypatch, "labels", "SA-0901") == 0
    assert "2 saved review round(s), each labelled" in capsys.readouterr().out


def test_labels_names_a_finding_with_no_label_or_an_unknown_value(
    monkeypatch, loop, capsys
):
    base = _two_rounds(monkeypatch, loop)
    _label_all(base / "round-2")
    _label_all(base / "round-1", disposition="ignored")
    assert _run(monkeypatch, "labels", "SA-0901") == 1
    assert "disposition='ignored'" in capsys.readouterr().out

    doc = json.loads((base / "round-1" / "labels.json").read_text())
    doc["findings"] = {}
    del doc["blocker_followed"]["pr_seats"]
    (base / "round-1" / "labels.json").write_text(json.dumps(doc))
    assert _run(monkeypatch, "labels", "SA-0901") == 1
    out = capsys.readouterr().out
    assert "has no label" in out
    assert "blocker_followed needs" in out


def test_labels_skips_a_folder_no_round_was_saved_in(monkeypatch, loop, capsys):
    base = _two_rounds(monkeypatch, loop)
    _label_all(base / "round-1")
    _label_all(base / "round-2")
    # A killed run leaves an empty folder.
    (base / "round-3").mkdir()
    assert _run(monkeypatch, "labels", "SA-0901") == 0
    assert "2 saved review round(s)" in capsys.readouterr().out


def _follow(round_dir: Path, schema: int | None, **followed) -> None:
    path = round_dir / "labels.json"
    doc = json.loads(path.read_text())
    if schema is not None:
        doc["schema"] = schema
    doc["blocker_followed"].update(followed)
    path.write_text(json.dumps(doc))


def test_a_schema_2_label_about_a_later_review_round_needs_that_review_round(
    monkeypatch, loop, capsys
):
    base = _two_rounds(monkeypatch, loop)
    for n in (1, 2):
        _label_all(base / f"round-{n}")
        _follow(base / f"round-{n}", 2, pr_seats=True)
    # A killed run leaves an empty folder with no round.json.
    (base / "round-3").mkdir()
    assert _run(monkeypatch, "labels", "SA-0901") == 1
    out = capsys.readouterr().out
    assert "pr-review round-2  pr_seats reads review round 3, which never ran" in out
    assert "round-1  pr_seats" not in out


def test_a_schema_2_null_on_the_last_review_round_is_no_gap(monkeypatch, loop):
    base = _two_rounds(monkeypatch, loop)
    for n in (1, 2):
        _label_all(base / f"round-{n}")
    _follow(base / "round-1", 2, pr_seats=False)
    _follow(base / "round-2", 2, pr_seats=None)
    assert _run(monkeypatch, "labels", "SA-0901") == 0


def test_a_schema_1_label_keeps_its_old_reading(monkeypatch, loop):
    base = _two_rounds(monkeypatch, loop)
    for n in (1, 2):
        _label_all(base / f"round-{n}")
    _follow(base / "round-2", None, pr_seats=True)
    assert _run(monkeypatch, "labels", "SA-0901") == 0


def test_a_review_round_records_when_it_was_saved(monkeypatch, loop):
    base = _two_rounds(monkeypatch, loop)
    doc = json.loads((base / "round-1" / "round.json").read_text())
    assert dt.datetime.fromisoformat(doc["saved_at"]).tzinfo is not None


def _saved_cell(monkeypatch, loop, head: str) -> int:
    cell = loop.batches / "v0" / "SA-0901"
    cell.mkdir(parents=True, exist_ok=True)
    lens = {"lens": "adequacy", "severity": "note", "file": "t.py", "line": 5}
    (cell / "findings.json").write_text(
        json.dumps([{"lens": "adequacy", "findings": [{**lens, "claim": "weak"}]}])
    )
    (cell / "patch.json").write_text(json.dumps({"head_sha": head}))
    spec = str(loop.root / "spec.md")
    return _run(monkeypatch, "save-round", "SA-0901", "--kind", "cell", "--spec", spec)


def test_labels_reads_a_cell_round_saved_beside_the_other_kinds(
    monkeypatch, loop, capsys
):
    # b-91ead2: the cell round sat under `v0/`, and its labels landed where nothing read them.
    base = loop.batches / "spec-loop" / "SA-0901" / "cell"
    assert _saved_cell(monkeypatch, loop, "feedbeef") == 0
    assert (base / "round-1" / "findings.json").is_file()
    capsys.readouterr()
    assert _run(monkeypatch, "labels", "SA-0901") == 1
    assert "SA-0901  cell round-1  no labels.json" in capsys.readouterr().out

    _label_all(base / "round-1")
    _follow(base / "round-1", 2, cell_review=True)
    assert _run(monkeypatch, "labels", "SA-0901") == 0
    # Saving the same head keeps its review round. A re-run cell takes the next one.
    assert _saved_cell(monkeypatch, loop, "feedbeef") == 0
    assert _saved_cell(monkeypatch, loop, "cafebabe") == 0
    assert sorted(p.name for p in base.iterdir()) == ["round-1", "round-2"]
