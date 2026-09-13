"""The spec-loop skill's driver: stack order, rebase fork points, staleness,
and the watch pattern. Real git in a temporary repo; `gh` is always injected."""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "spec_loop_driver",
    REPO / ".claude" / "skills" / "run-saffron-spec-loop" / "driver.py",
)
assert _SPEC is not None and _SPEC.loader is not None
driver = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = driver  # a dataclass resolves its annotations through it
_SPEC.loader.exec_module(driver)

# CONTEXT.md's **Terminal state**, spelled out: the pattern reads the ontology,
# so this is the second source that notices the two drifting apart.
TERMINAL_STATES = (
    "SCOPE_REVIEW",
    "PLAN_REJECTED",
    "EXHAUSTED",
    "READY_FOR_REVIEW",
    "MERGE_FAILED",
    "PREFLIGHT_FAILED",
    "NOT_IMPLEMENTED",
    "GATE_ERROR",
    "RATE_LIMITED",
)


def _row(
    spec_id: str,
    priority: int = 1,
    depends_on: tuple[str, ...] | list[str] = (),
    pr: int | None = 1,
    state: str | None = "READY_FOR_REVIEW",
):
    return driver.Planned(
        spec_id=spec_id,
        path=f"x/{spec_id}.md",
        priority=priority,
        depends_on=list(depends_on),
        state=state,
        pr=pr,
        branch=f"saffron/{spec_id}",
    )


def test_a_child_sits_directly_above_its_parent_ahead_of_an_earlier_sibling():
    # Snapshot order is A, B, C. Linked in that order, C sat above B and its
    # PR showed A's changes.
    rows = [_row("A", 1, pr=10), _row("B", 1, pr=11), _row("C", 2, ["A"], pr=12)]
    order, warnings = driver._stack_order(rows)
    assert [p.spec_id for p in order] == ["A", "C", "B"]
    assert warnings == []


def test_a_parent_with_two_children_is_reported_not_hidden():
    rows = [_row("A", pr=10), _row("B", 2, ["A"], pr=11), _row("C", 2, ["A"], pr=12)]
    order, warnings = driver._stack_order(rows)
    assert [p.spec_id for p in order] == ["A", "B", "C"]
    assert warnings == ["C sits above B, not its parent A: #12 will show A's changes"]


def test_a_child_whose_parent_is_not_reviewable_is_reported():
    rows = [
        _row("A", state="EXHAUSTED", pr=None),
        _row("B", 2, ["A"], pr=11),
        _row("C", pr=12),
    ]
    order, warnings = driver._stack_order(rows)
    assert [p.spec_id for p in order] == ["B", "C"]
    assert warnings == [
        "B's parent A is not in the stack; #11 stays based on saffron/A"
    ]


def _git(cwd, *args):
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def _commit(cwd, name, text):
    (cwd / name).write_text(text)
    _git(cwd, "add", name)
    _git(cwd, "commit", "-qm", name)
    return _git(cwd, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """main at M0; `a` cut from M0; `b` a child of `a`; `c` a sibling cut from
    M0; main then advances to M1, and `d` is a sibling cut from M1."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    tips = {"M0": _commit(tmp_path, "base.txt", "base\n")}
    _git(tmp_path, "checkout", "-q", "-b", "a")
    tips["a"] = _commit(tmp_path, "a.txt", "a\n")
    _git(tmp_path, "checkout", "-q", "-b", "b")
    tips["b"] = _commit(tmp_path, "b.txt", "b\n")
    _git(tmp_path, "checkout", "-q", "-b", "c", tips["M0"])
    tips["c"] = _commit(tmp_path, "c.txt", "c\n")
    _git(tmp_path, "checkout", "-q", "main")
    tips["M1"] = _commit(tmp_path, "m1.txt", "m1\n")
    _git(tmp_path, "checkout", "-q", "-b", "d")
    tips["d"] = _commit(tmp_path, "d.txt", "d\n")
    _git(tmp_path, "checkout", "-q", "main")
    return tmp_path, tips


def test_a_fork_point_is_the_newer_of_the_two_merge_bases(repo):
    cwd, tips = repo
    assert driver._fork_point("b", "a", "main", cwd) == tips["a"]
    assert driver._fork_point("c", "b", "main", cwd) == tips["M0"]
    # The trunk-side merge-base, not the one with the layer below: `c` was cut
    # from M0, and replaying from there would carry M1's commits into `d`.
    assert driver._fork_point("d", "c", "main", cwd) == tips["M1"]


def test_rebase_chains_siblings_onto_the_new_trunk_and_keeps_each_layers_content(repo):
    cwd, _tips = repo
    layers = driver._plan_layers(["a", "b", "c", "d"], "main", cwd, prefix="")
    ok, messages = driver._apply_layers(layers, cwd)
    assert ok, messages
    assert messages == [f"{b}: identical" for b in ("a", "b", "c", "d")]
    for lower, upper, own in (
        ("main", "a", "a.txt"),
        ("a", "b", "b.txt"),
        ("b", "c", "c.txt"),
        ("c", "d", "d.txt"),
    ):
        _git(cwd, "merge-base", "--is-ancestor", lower, upper)
        assert _git(cwd, "diff", "--name-only", lower, upper) == own
    assert _git(cwd, "rev-parse", "--abbrev-ref", "HEAD") == "main"


def test_a_conflict_restores_every_branch(repo):
    cwd, tips = repo
    _git(cwd, "checkout", "-q", "-b", "e", tips["M0"])
    _commit(cwd, "a.txt", "not a\n")
    _git(cwd, "checkout", "-q", "main")
    before = {b: _git(cwd, "rev-parse", b) for b in ("a", "e")}

    ok, messages = driver._apply_layers(
        driver._plan_layers(["a", "e"], "main", cwd, prefix=""), cwd
    )

    assert not ok
    assert "every branch is restored" in messages[0]
    assert {b: _git(cwd, "rev-parse", b) for b in ("a", "e")} == before
    assert _git(cwd, "rev-parse", "--abbrev-ref", "HEAD") == "main"
    assert not (cwd / ".git" / "rebase-merge").exists()


def test_a_local_branch_that_differs_from_the_plan_is_refused(repo):
    cwd, tips = repo
    layers = driver._plan_layers(["a", "c"], "main", cwd, prefix="")
    _git(cwd, "branch", "-f", "c", tips["M0"])
    ok, messages = driver._apply_layers(layers, cwd)
    assert not ok
    assert messages[0].startswith("local c is")


def test_a_gone_spec_an_edited_spec_and_a_merged_pr_make_the_order_stale(tmp_path):
    from saffron.intake import load_spec

    source = sorted((REPO / ".saffron" / "specs").rglob("SA-*.md"))[0]
    spec = tmp_path / source.name
    shutil.copy(source, spec)
    sha = load_spec(spec)[1]
    rows = [
        driver.Planned("A", str(tmp_path / "gone.md"), 1),
        driver.Planned("B", str(spec), 1, spec_sha="0" * len(sha)),
        driver.Planned("C", str(spec), 1, spec_sha=sha, pr=5),
        driver.Planned("D", str(spec), 1, spec_sha=sha, pr=6),
    ]
    states = {5: "MERGED", 6: "OPEN"}
    reasons = driver._stale(rows, pr_state=states.get)
    assert reasons == [
        f"A: {tmp_path / 'gone.md'} is gone",
        "B: the spec changed after the snapshot",
        "C: #5 is MERGED",
    ]


def test_the_watch_pattern_matches_every_terminal_state_after_a_padded_spec_id():
    pattern = re.compile(driver.watch_pattern())
    for state in TERMINAL_STATES:
        assert pattern.search(f"SA-0077    {state}  https://github.com/o/r/pull/1"), (
            state
        )
    assert pattern.search("IMPLEMENT: 1 commit(s), $1.48 spent")
    assert not pattern.search("agent: thinking")


def test_next_says_when_the_spec_it_names_is_cut_from_a_reviewable_parent():
    parent = _row("A", pr=10)
    child = _row("B", 2, ["A"], pr=None, state=None)
    sibling = _row("C", 2, pr=None, state=None)

    chosen, note = driver._next_spec([parent, child, sibling], again=False)
    assert chosen is child
    assert note == "B is cut from A: push its review commits first"

    chosen, note = driver._next_spec([parent, sibling], again=False)
    assert chosen is sibling
    assert note is None
