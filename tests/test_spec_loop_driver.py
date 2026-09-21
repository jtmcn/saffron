"""The spec-loop skill's driver: stack order, rebase fork points, staleness,
and the watch pattern. Real git in a temporary repo; `gh` is always injected."""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

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

# CONTEXT.md's **Terminal state**, spelled out apart from the ontology the driver
# reads, so a state added to or dropped from either one fails here.
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
    return driver.OrderRow(
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


def test_a_parent_of_waiting_children_runs_before_a_leaf_of_equal_priority():
    # Stack #251: SA-0080, parent of three, sorted after the leaf SA-0079 by
    # id, so once it ran nothing independent was left to run beside its review.
    rows = [
        _row("L", 3, state=None, pr=None),
        _row("P", 3, state=None, pr=None),
        _row("C1", 3, ["P"], state=None, pr=None),
        _row("C2", 3, ["P"], state=None, pr=None),
        _row("H", 2, state=None, pr=None),
    ]
    assert [p.spec_id for p in driver._sequence(rows)] == ["H", "P", "C1", "C2", "L"]


def test_a_parent_with_two_children_is_reported_not_hidden():
    rows = [_row("A", pr=10), _row("B", 2, ["A"], pr=11), _row("C", 2, ["A"], pr=12)]
    order, warnings = driver._stack_order(rows)
    assert [p.spec_id for p in order] == ["A", "B", "C"]
    # Not "will show A's changes": A is further down the stack, so #12's merge
    # base with B is A's head and its diff is C's own (measured on #249).
    assert warnings == [
        "C sits above its sibling B, not directly above its parent A; #12's diff "
        "is unaffected, and `rebase` would chain them if asked"
    ]


@pytest.mark.parametrize(
    ("rows", "below"),
    [
        (["B", "C"], "the trunk"),
        (["C", "B"], "saffron/C"),
    ],
)
def test_a_child_whose_parent_is_not_reviewable_is_reported(rows, below):
    # `link` corrects every base it finds wrong, so the child does not stay on
    # its parent's branch: it lands on whatever sits below it.
    made = {"B": _row("B", 2, ["A"], pr=11), "C": _row("C", pr=12)}
    order, warnings = driver._stack_order(
        [_row("A", state="EXHAUSTED", pr=None), *(made[r] for r in rows)]
    )
    assert [p.spec_id for p in order] == rows
    assert warnings == [
        f"B's parent A is not in the stack; `link` retargets #11 onto {below}, "
        "where it shows A's changes"
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
def empty_repo(tmp_path, monkeypatch):
    """A git repo on `main` with no commits, blind to the host's git config."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    return tmp_path


@pytest.fixture
def repo(empty_repo):
    """main at M0; `a` cut from M0; `b` a child of `a`; `c` a sibling cut from
    M0; main then advances to M1, and `d` is a sibling cut from M1."""
    tmp_path = empty_repo
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


@pytest.mark.parametrize(
    ("lower", "upper", "spec_type", "ceiling"),
    [
        ("main", "a", "bug", 300),
        ("a", "b", "feature", 600),
        ("main", "c", "test", 1000),
    ],
)
def test_size_counts_a_branch_against_the_gates_own_ceiling(
    repo, lower, upper, spec_type, ceiling
):
    # Review commits took #247 from 294 to 367 lines against a bug's 300, and
    # `size` runs only in the cell (item 40). Each branch here adds one line.
    tmp, _tips = repo
    result = driver._size(lower, upper, spec_type, [], cwd=tmp)
    assert result.status == "pass"
    assert (
        result.summary == f"1 changed lines within the {spec_type} ceiling of {ceiling}"
    )


def test_size_measures_a_parent_from_below_it_not_from_its_own_child(repo):
    # Every other loop branch was a candidate base, so a parent whose child had
    # been cut from it measured from its own tip: 0 changed lines.
    cwd, tips = repo
    a, b, c = _row("a"), _row("b", depends_on=["a"]), _row("c")
    for p in (a, b, c):
        p.branch = p.spec_id

    below_a = driver._bases_below("a", [a, b, c])
    assert below_a == []
    assert driver._own_base("a", below_a, "main", cwd) == tips["M0"]
    assert driver._own_base("a", ["b", "c"], "main", cwd) == tips["a"]  # the defect
    assert driver._bases_below("b", [a, b, c]) == ["a"]


def test_size_measures_a_branch_from_the_nearest_branch_it_was_cut_or_rebased_from(
    repo,
):
    # Stack #251's siblings were chained before they merged, and measured from
    # trunk SA-0080 counted SA-0078 to SA-0079 as well: 802 lines, not 367.
    cwd, tips = repo
    assert driver._own_base("b", ["a", "c"], "main", cwd) == tips["a"]  # a child
    assert driver._own_base("c", ["a", "b"], "main", cwd) == tips["M0"]  # a sibling
    assert driver._own_base("d", ["a", "b", "c"], "main", cwd) == tips["M1"]

    layers = driver._layers(["a", "b", "c", "d"], "main", cwd, prefix="")
    ok, messages = driver._apply_layers(layers, cwd)
    assert ok, messages
    chained_c = _git(cwd, "rev-parse", "c")
    assert driver._own_base("d", ["a", "b", "c"], "main", cwd) == chained_c


def test_a_fork_point_is_the_newer_of_the_two_merge_bases(repo):
    cwd, tips = repo
    assert driver._fork_point("b", "a", "main", cwd) == tips["a"]
    assert driver._fork_point("c", "b", "main", cwd) == tips["M0"]
    # The trunk-side merge-base, not the one with the layer below: `c` was cut
    # from M0, and replaying from there would carry M1's commits into `d`.
    assert driver._fork_point("d", "c", "main", cwd) == tips["M1"]


def test_rebase_chains_siblings_onto_the_new_trunk_and_keeps_each_layers_content(repo):
    cwd, _tips = repo
    layers = driver._layers(["a", "b", "c", "d"], "main", cwd, prefix="")
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
        driver._layers(["a", "e"], "main", cwd, prefix=""), cwd
    )

    assert not ok
    assert "every branch is restored" in messages[0]
    assert {b: _git(cwd, "rev-parse", b) for b in ("a", "e")} == before
    assert _git(cwd, "rev-parse", "--abbrev-ref", "HEAD") == "main"
    assert not (cwd / ".git" / "rebase-merge").exists()


def test_a_branch_checked_out_in_another_worktree_is_refused_before_anything_moves(
    repo,
):
    # Its rebase failed as if on a conflict, and the restore then raised on it,
    # leaving HEAD detached with nothing said.
    cwd, _tips = repo
    _git(cwd, "worktree", "add", "-q", str(cwd.with_name(cwd.name + "-wt")), "c")
    before = {b: _git(cwd, "rev-parse", b) for b in ("a", "c", "d")}

    ok, messages = driver._apply_layers(
        driver._layers(["a", "c", "d"], "main", cwd, prefix=""), cwd
    )

    assert not ok
    assert messages[0].startswith("c is checked out in ")
    assert {b: _git(cwd, "rev-parse", b) for b in ("a", "c", "d")} == before
    assert _git(cwd, "rev-parse", "--abbrev-ref", "HEAD") == "main"


def test_restore_resets_every_branch_it_can_and_names_the_one_it_cannot(repo):
    cwd, tips = repo
    layers = driver._layers(["a", "c"], "main", cwd, prefix="")
    for branch in ("a", "c"):
        _git(cwd, "branch", "-f", branch, tips["M1"])
    _git(cwd, "worktree", "add", "-q", str(cwd.with_name(cwd.name + "-wt")), "a")

    failed = driver._restore(layers, "main", cwd)

    assert len(failed) == 1 and failed[0].startswith("a: ")
    assert _git(cwd, "rev-parse", "c") == tips["c"]
    assert _git(cwd, "rev-parse", "--abbrev-ref", "HEAD") == "main"


def test_a_local_branch_that_differs_from_the_recorded_tip_is_refused(repo):
    cwd, tips = repo
    layers = driver._layers(["a", "c"], "main", cwd, prefix="")
    _git(cwd, "branch", "-f", "c", tips["M0"])
    ok, messages = driver._apply_layers(layers, cwd)
    assert not ok
    assert messages[0].startswith("local c is")


def test_neighbours_that_both_append_to_one_file_are_reported_as_a_conflict(repo):
    # Two siblings both appended `## 34.` to the backlog, and each PR page
    # looked clean after `link` retargeted it.
    cwd, tips = repo
    for branch in ("x", "y"):
        _git(cwd, "checkout", "-q", "-b", branch, tips["M0"])
        _commit(cwd, "base.txt", f"base\n## 34. {branch}\n")
    _git(cwd, "checkout", "-q", "main")

    assert driver._merge_conflicts("a", "c", cwd) == []
    conflicts = driver._merge_conflicts("x", "y", cwd)
    assert conflicts and all(line.startswith("CONFLICT") for line in conflicts)
    assert "base.txt" in conflicts[0]


def test_a_gone_spec_an_edited_spec_and_a_merged_or_closed_pr_make_the_order_stale(
    tmp_path,
):
    from saffron.intake import load_spec

    source = sorted((REPO / ".saffron" / "specs").rglob("SA-*.md"))[0]
    spec = tmp_path / source.name
    shutil.copy(source, spec)
    sha = load_spec(spec)[1]
    rows = [
        driver.OrderRow("A", str(tmp_path / "gone.md"), 1),
        driver.OrderRow("B", str(spec), 1, spec_sha="0" * len(sha)),
        driver.OrderRow("C", str(spec), 1, spec_sha=sha, pr=5),
        driver.OrderRow("D", str(spec), 1, spec_sha=sha, pr=6),
        driver.OrderRow("E", str(spec), 1, spec_sha=sha, pr=7),
    ]
    states = {5: "MERGED", 6: "OPEN", 7: "CLOSED"}
    reasons = driver._stale(rows, pr_state=states.get)
    assert reasons == [
        f"A: {tmp_path / 'gone.md'} is gone",
        "B: the spec changed after the snapshot",
        "C: #5 is MERGED",
        "E: #7 is CLOSED",
    ]


def test_the_watch_pattern_matches_every_terminal_state_after_a_padded_spec_id():
    pattern = re.compile(driver.watch_pattern())
    for state in TERMINAL_STATES:
        assert pattern.search(f"SA-0077    {state}  https://github.com/o/r/pull/1"), (
            state
        )
    assert pattern.search("IMPLEMENT: 1 commit(s), $1.48 spent")
    assert not pattern.search("agent: thinking")


def test_the_watch_pattern_ignores_state_names_inside_the_agents_own_lines():
    # SA-0084's agent grepped for SCOPE_REVIEW and the Monitor fired on it.
    pattern = re.compile(driver.watch_pattern())
    assert not pattern.search(
        'agent: Grep {"pattern": "SCOPE_REVIEW|PhaseStart|detail=", "path": "/work"}'
    )
    assert pattern.search("READY_FOR_REVIEW: $2.82 spent, session 7b45a3b7")
    assert not pattern.search('agent: Grep {"pattern": "Traceback", "path": "/work"}')
    assert pattern.search("Traceback (most recent call last):")


def test_editing_a_spec_with_an_open_pull_request_names_what_it_refuses(
    tmp_path, monkeypatch
):
    """Item 137. The bare "the spec changed after the snapshot" line said
    nothing about the cost: the next `snapshot --force` holds the spec out of
    the order, refuses every dependent, and drops its pull request from the
    stack. It cost two pull requests on 2026-09-16, because the operator edited
    a spec after reading its review, which is the normal thing to do."""
    spec = tmp_path / "SA-0088.md"
    spec.write_text("---\nid: SA-0088\n---\n")
    monkeypatch.setattr(driver, "REPO", tmp_path)
    monkeypatch.setattr(
        "saffron.intake.load_spec", lambda _p: (object(), "the-new-sha")
    )

    parent = _row("SA-0088", pr=277)
    parent.path = "SA-0088.md"
    parent.spec_sha = "the-sha-its-task-ran-at"
    child = _row("SA-0089", depends_on=["SA-0088"], pr=None, state=None)
    grandchild = _row("SA-0091", depends_on=["SA-0089"], pr=None, state=None)
    for row in (child, grandchild):
        row.path = "SA-0088.md"
        row.spec_sha = "the-new-sha"

    # A second-position dependency is refused too: `scheduler._refuse` loops
    # the whole list and `_order` admits only when *all* are in, so walking
    # `depends_on[0]` would leave this one unnamed.
    second = _row("SA-0093", depends_on=["SA-0000", "SA-0088"], pr=None, state=None)
    # Already ran, so `_carried` keeps it and `_order` admits it — it is not
    # refused, and neither is its own child.
    ran = _row("SA-0094", depends_on=["SA-0088"], pr=278)
    under_ran = _row("SA-0095", depends_on=["SA-0094"], pr=None, state=None)
    for row in (second, ran, under_ran):
        row.path = "SA-0088.md"
        row.spec_sha = "the-new-sha"

    rows = [parent, child, grandchild, second, ran, under_ran]
    traps = driver._edit_traps(rows, lambda _n: "OPEN")

    assert len(traps) == 1
    assert "SA-0089" in traps[0] and "SA-0091" in traps[0]  # both, transitively
    assert "SA-0093" in traps[0]  # named second, refused all the same
    assert "SA-0094" not in traps[0]  # it ran; nothing refuses it
    assert "SA-0095" not in traps[0]  # nor its child, which stacks on a kept row
    assert "#277" in traps[0]
    assert "item 137" in traps[0]

    # A merged pull request is the ordinary re-queue, not the trap.
    assert driver._edit_traps([parent, child, grandchild], lambda _n: "MERGED") == []


def test_every_progress_line_the_cli_prints_reaches_the_watcher():
    """Item 139's other half. `SALVAGE` was missing and so were `SCOPE` and
    `REPAIR`, and nothing held the two lists together — the same reason
    `watch_pattern` reads the ontology's terminal states rather than copying
    them. `events.LineLabel` is the closed set of progress-line prefixes."""
    from typing import get_args

    from saffron.events import LineLabel

    pattern = re.compile(driver.watch_pattern())
    for label in get_args(LineLabel):
        assert pattern.search(f"{label}: something happened"), label


def test_the_watch_pattern_shows_whether_a_salvage_recovered_anything():
    # Item 139: the Monitor showed `IMPLEMENT: cut off at the turn ceiling with
    # nothing committed — spending one turn to salvage it` and then nothing, so
    # whether the cell had anything left to gate was invisible.
    pattern = re.compile(driver.watch_pattern())
    assert pattern.search("SALVAGE: recovered 1 commit(s), $7.96 spent")
    assert pattern.search("SALVAGE: cut off and could not be salvaged, $8.39 spent")
    assert not pattern.search('agent: Bash {"command": "echo SALVAGE: 1"}')


def test_size_measures_from_a_parent_the_order_does_not_carry(monkeypatch):
    """Item 138, whose cause is item 137. A spec whose text moved while its
    pull request was open is held out of the order entirely, so the order-only
    lookup returned no base and `size` measured from the default branch —
    counting the parent's whole diff as the child's. `SA-0089` read 776 of a
    600 ceiling for a branch that was 477."""
    from saffron.intake import Spec

    def _spec_with(spec_id, depends_on):
        spec = object.__new__(Spec)
        object.__setattr__(spec, "id", spec_id)
        object.__setattr__(spec, "depends_on", list(depends_on))
        return spec

    known = {
        "SA-0088": _spec_with("SA-0088", []),
        "SA-0089": _spec_with("SA-0089", ["SA-0088"]),
        "SA-0091": _spec_with("SA-0091", ["SA-0089"]),
    }
    monkeypatch.setattr(driver, "_known_specs", lambda: known)

    # The order carries only the child: its parent was held out (item 137).
    orphaned = [_row("SA-0089", depends_on=["SA-0088"])]
    assert driver._bases_below("SA-0089", orphaned) == ["saffron/SA-0088"]

    # Two deep, and still nearest first.
    assert driver._bases_below(
        "SA-0091", [_row("SA-0091", depends_on=["SA-0089"])]
    ) == [
        "saffron/SA-0089",
        "saffron/SA-0088",
    ]

    # A spec with no parent still measures from the trunk.
    assert driver._bases_below("SA-0088", [_row("SA-0088")]) == []


def test_the_watch_pattern_shows_the_lines_that_decide_a_turn_ceiling():
    # SA-0087: a turn-ceiling line reads as non-terminal, and only the `budget:`
    # line after it said nothing could be salvaged. The Monitor never showed it.
    pattern = re.compile(driver.watch_pattern())
    assert pattern.search(
        "budget: $8.39 of $8.00 — cut off at the turn ceiling with nothing "
        "committed, no room left to salvage"
    )
    assert pattern.search("PLAN: accepted, sha256 ff246b44a498")
    assert not pattern.search('agent: Bash {"command": "echo budget: 1"}')


def test_the_driver_reads_every_terminal_state_from_the_ontology():
    assert sorted(driver.terminal_states()) == sorted(TERMINAL_STATES)


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


def test_next_passes_over_a_child_until_its_parents_review_commits_are_pushed():
    # Stack #251: `next` named SA-0083 while SA-0082's review was unpushed, and
    # exit 0 with a spec id reads as "start this".
    parent = _row("A", pr=10)
    parent.pushed_sha = "p" * 40
    child = _row("B", 2, ["A"], pr=None, state=None)
    sibling = _row("C", 2, pr=None, state=None)
    heads = {"saffron/A": "p" * 40}

    chosen, note = driver._next_spec(
        [parent, child, sibling], again=False, head_of=heads.get
    )
    assert chosen is sibling
    assert note == "B waits on A's review commits: none are pushed yet"

    chosen, note = driver._next_spec([parent, child], again=False, head_of=heads.get)
    assert chosen is None
    assert note == "B waits on A's review commits: none are pushed yet"

    heads["saffron/A"] = "r" * 40
    chosen, note = driver._next_spec(
        [parent, child, sibling], again=False, head_of=heads.get
    )
    assert chosen is child
    assert note == "B is cut from A, whose review commits are pushed (rrrrrrrr)"


def test_next_says_a_waiting_child_is_all_that_is_left(monkeypatch, capsys):
    parent = _row("A", pr=10)
    parent.pushed_sha = "p" * 40
    child = _row("B", 2, ["A"], pr=None, state=None)
    monkeypatch.setattr(driver, "_load", lambda: [parent, child])
    monkeypatch.setattr(driver, "_stale", lambda rows: [])
    monkeypatch.setattr(driver, "_origin_head", lambda branch: "p" * 40)

    assert driver.cmd_next(argparse.Namespace(again=False)) == 1
    err = capsys.readouterr().err
    assert "B waits on A's review commits" in err
    assert "nothing untouched left" not in err


def test_status_says_which_reviewable_branches_carry_pushed_review_commits(
    monkeypatch, capsys
):
    # Item 14: `status` showed `READY_FOR_REVIEW #243` either way, so it could
    # not answer "what is left to review?".
    reviewed, unreviewed, unrecorded = _row("A", pr=10), _row("B", pr=11), _row("C")
    reviewed.pushed_sha = unreviewed.pushed_sha = "p" * 40
    heads = {"saffron/A": "r" * 40, "saffron/B": "p" * 40}
    monkeypatch.setattr(driver, "_load", lambda: [reviewed, unreviewed, unrecorded])
    monkeypatch.setattr(driver, "_stale", lambda rows: [])
    monkeypatch.setattr(driver, "_origin_head", heads.get)

    assert driver.cmd_status(argparse.Namespace()) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].endswith("#10    reviewed rrrrrrrr")
    assert lines[1].endswith("#11    no review commits pushed")
    assert lines[2].endswith("#1   ")


def _rate_limited(spec_id: str):
    row = _row(spec_id, pr=None, state=None)
    row.last_state = "RATE_LIMITED"
    return row


def _dropped(spec_id: str):
    row = _row(spec_id, pr=None, state=None)
    row.dropped = "operator's call"
    return row


@pytest.mark.parametrize(
    ("parent", "why"),
    [
        (_rate_limited("A"), "RATE_LIMITED"),
        (_row("A", state="EXHAUSTED", pr=None), "EXHAUSTED"),
        (_dropped("A"), "dropped"),
    ],
)
def test_next_holds_back_a_child_whose_parent_has_no_reviewable_branch(parent, why):
    # `saffron cell` runs no `depends_on` refusal, and a parent with no waiting
    # task leaves the child's worktree cut from main, without a word.
    child = _row("B", 2, ["A"], pr=None, state=None)
    sibling = _row("C", 2, pr=None, state=None)

    chosen, note = driver._next_spec([parent, child, sibling], again=False)
    assert chosen is sibling
    assert note == (
        f"held back B: its parent A is {why}, so a cell would cut it from main"
    )

    chosen, note = driver._next_spec([parent, child], again=False)
    assert chosen is None


@pytest.fixture
def loop(tmp_path, monkeypatch):
    """Four real specs in a scratch repo root, the driver pointed at it, and
    `gh` answering #10 OPEN and #11 MERGED."""
    from saffron.intake import load_spec

    specs_dir = tmp_path / ".saffron" / "specs"
    specs_dir.mkdir(parents=True)
    paths = []
    for source in sorted((REPO / ".saffron" / "specs" / "done").glob("SA-*.md"))[:4]:
        shutil.copy(source, specs_dir / source.name)
        paths.append(specs_dir / source.name)
    loaded = [load_spec(p) for p in paths]

    monkeypatch.setattr(driver, "REPO", tmp_path)
    monkeypatch.setattr(driver, "STATE_DIR", tmp_path / ".saffron-loop")
    monkeypatch.setattr(driver, "ORDER", tmp_path / ".saffron-loop" / "order.json")
    monkeypatch.setattr(
        driver, "_gh_pr_field", lambda n, _name: {10: "OPEN", 11: "MERGED"}[n]
    )

    def row(i, **recorded):
        spec, sha = loaded[i]
        recorded.setdefault("spec_sha", sha)
        return driver.OrderRow(
            spec.id,
            str(paths[i].relative_to(tmp_path)),
            spec.priority,
            branch=f"saffron/{spec.id}",
            **recorded,
        )

    def scan_returns(*indices):
        scanned = [SimpleNamespace(spec=loaded[i][0], path=paths[i]) for i in indices]
        seen = {}

        def scan(*, loop_branches):
            seen["loop_branches"] = loop_branches
            return scanned, []

        monkeypatch.setattr(driver, "_scan", scan)
        return seen

    return SimpleNamespace(
        ids=[spec.id for spec, _sha in loaded],
        row=row,
        scan_returns=scan_returns,
        root=tmp_path,
    )


def test_snapshot_shows_each_specs_title_and_budget_and_counts_every_root(loop, capsys):
    # The operator saw no queue before the first cell, and the note said "3
    # spec(s) declare no depends_on" of four that did.
    loop.scan_returns(0, 1, 2, 3)

    assert (
        driver.cmd_snapshot(argparse.Namespace(force=False, new=False, add=None)) == 0
    )

    out = capsys.readouterr().out
    for title in (
        "Define a factory ontology",
        "The size core gate is specified but not implemented",
        "An attempt's identity is recorded nowhere",
        "The anti-gaming gate is declared, parsed, and enforced by nothing",
    ):
        assert title in out
    assert "$28.50" in out  # 10 + 8 + 6 + 4.5, the four specs' budget_usd
    assert "4 specs declare no depends_on" in out
    assert out.count("  risk=") == 4  # item 5's table asked for it


def test_a_child_is_admitted_once_its_edited_parent_is_kept(loop):
    """The other half of item 137, and the half that actually stranded two
    specs. `build_queue` refuses a child whose parent has no task at its
    current sha; `_order` admits such a refusal only when every `depends_on`
    is already admitted. Holding the parent out left the child refused with
    nowhere to go — keeping it admits both."""
    parent_id, _sibling, _merged, _new = loop.ids
    child = driver.REPO / ".saffron" / "specs" / "SA-9999-child.md"
    child.write_text(
        "---\n"
        "id: SA-9999\n"
        "title: a child of the edited spec\n"
        "type: bug\n"
        "priority: 3\n"
        f"depends_on: [{parent_id}]\n"
        "touches:\n  - saffron/cli.py\n"
        "budget_usd: 5\nmax_attempts: 3\nmax_turns: 40\nrisk: standard\n"
        "acceptance:\n"
        "  - claim: it does the thing\n"
        "    witness: tests/test_cli.py::test_it\n"
        "---\n\n## Context\n\nnothing\n"
    )
    refusal = SimpleNamespace(
        path=child,
        reason=f"depends_on {parent_id} has no task at its current spec_sha",
    )
    held = loop.row(0, state="READY_FOR_REVIEW", pr=10, spec_sha="edited")

    # Held out, as it was: the child has no admitted parent and is stranded.
    ordered, stranded = driver._order([], [refusal], [], frozenset({parent_id}))
    assert [p.spec_id for p in ordered] == []
    assert stranded == [child]

    # Kept: the parent is admitted, so the child is too.
    ordered, stranded = driver._order([], [refusal], [held], frozenset())
    assert [p.spec_id for p in ordered] == [parent_id, "SA-9999"]
    assert stranded == []


def test_a_resnapshot_keeps_the_outcome_of_a_spec_edited_while_its_pr_is_open(
    loop, capsys
):
    """Item 137. Holding the row out lost its recorded outcome with it: the
    spec left the order, so `stack` printed a stack missing that pull request —
    which would have retargeted a child off its parent onto the default branch.
    It is kept now, at the sha its task ran at, and the edit is recorded as
    acknowledged rather than leaving the order permanently stale."""
    edited, sibling, _merged, _new = loop.ids
    driver._save(
        [loop.row(0, state="READY_FOR_REVIEW", pr=10, spec_sha="edited"), loop.row(1)]
    )
    seen = loop.scan_returns(0, 1)

    assert driver.cmd_snapshot(argparse.Namespace(force=True, new=False, add=None)) == 0

    rows = driver._load()
    kept = {p.spec_id: p for p in rows}
    assert edited in kept  # the row, and #10 with it
    assert kept[edited].state == "READY_FOR_REVIEW"
    assert kept[edited].pr == 10
    assert kept[edited].spec_sha == "edited"  # the sha its task ran at, not the edit
    assert kept[edited].edited_sha  # and the edit, acknowledged
    assert sibling in kept
    assert "#10 is still open" in capsys.readouterr().out
    assert seen["loop_branches"] == {f"saffron/{edited}", f"saffron/{sibling}"}

    # The order is not stale on its account, so `next` is not deadlocked by a
    # spec that cannot be re-queued until its pull request closes.
    assert [r for r in driver._stale(rows) if edited in r] == []

    # And it is not re-run: it carries a recorded outcome, so it is not pending.
    assert not kept[edited].pending

    # Edited a second time, it is stale again — the acknowledgement is of one
    # edit, not of the file.
    spec_file = driver.REPO / kept[edited].path
    spec_file.write_text(spec_file.read_text() + "\nA second edit.\n")
    assert [r for r in driver._stale(rows) if edited in r] != []


def test_a_resnapshot_looks_past_only_the_loops_own_open_prs():
    # Hiding every open PR also hid step 5's backlog PR from the conflict set.
    import json

    listed = [
        {"number": 10, "headRefName": "saffron/SA-0001", "files": []},
        {"number": 20, "headRefName": "joel/backlog", "files": []},
    ]

    def gh(argv):
        return subprocess.CompletedProcess(
            argv, 0, stdout=json.dumps(listed), stderr=""
        )

    hiding = driver._hiding(gh, frozenset({"saffron/SA-0001"}))
    assert json.loads(hiding(["gh", "pr", "list"]).stdout) == [listed[1]]


def test_record_keeps_what_package_pushed_and_says_what_the_cell_spent(
    loop, monkeypatch, capsys
):
    # SA-0080 finished at $7.55 against a $6 budget and nothing on the way out
    # said so; `next` needs the pushed sha to tell a reviewed parent apart. A
    # real ledger: `tasks_by_spec` rows carry neither, and dicts hid that.
    from saffron.ledger import Ledger

    spec_id = loop.ids[0]
    driver._save([loop.row(0)])
    sha = driver._load()[0].spec_sha
    ledger = Ledger(loop.root / "ledger.db")
    repo_id = ledger.upsert_repo("r", "git@github.com:o/r.git", "/mirror", "policy")
    task_id = ledger.create_task(
        ledger.create_run(repo_id, "b" * 40), spec_id, sha, "saffron/X", budget_usd=6.0
    )
    attempt_id = ledger.open_attempt(task_id, "IMPLEMENT")
    ledger.close_attempt(
        attempt_id,
        session_id=None,
        subtype="success",
        terminal_reason=None,
        num_turns=1,
        cost_usd_est=7.55,
    )
    ledger.set_task_state(task_id, "PACKAGE")
    ledger.set_task_package(
        task_id,
        "READY_FOR_REVIEW",
        "saffron/X",
        "p" * 40,
        "https://github.com/o/r/pull/247",
    )
    monkeypatch.setattr(driver, "_ledger_and_repo", lambda: (ledger, repo_id, "url"))

    assert driver.cmd_record(argparse.Namespace(spec_id=spec_id)) == 0
    assert driver._load()[0].pushed_sha == "p" * 40
    assert capsys.readouterr().out == (
        f"{spec_id}  READY_FOR_REVIEW  #247  $7.55 of $6.00\n"
    )


@pytest.mark.parametrize("running", [False, True])
def test_record_calls_an_in_flight_state_a_halt_once_the_cell_has_exited(
    loop, monkeypatch, capsys, running
):
    # SA-0087's second cell exited with the task at REBUTTING, its branch
    # pushed, and `record` said "the cell is still running" to a delegate the
    # skill had told to wait for exactly that.
    from saffron.ledger import Ledger

    spec_id = loop.ids[0]
    driver._save([loop.row(0)])
    sha = driver._load()[0].spec_sha
    ledger = Ledger(loop.root / "ledger.db")
    repo_id = ledger.upsert_repo("r", "git@github.com:o/r.git", "/mirror", "policy")
    task_id = ledger.create_task(
        ledger.create_run(repo_id, "b" * 40), spec_id, sha, "saffron/X", budget_usd=14.0
    )
    ledger.set_task_state(task_id, "REBUTTING")
    ledger.record_push(task_id, "p" * 40)
    monkeypatch.setattr(driver, "_ledger_and_repo", lambda: (ledger, repo_id, "url"))
    monkeypatch.setattr(driver, "_cell_running", lambda _spec_id: running)

    assert driver.cmd_record(argparse.Namespace(spec_id=spec_id)) == 1
    row = driver._load()[0]
    err = capsys.readouterr().err
    assert row.state is None and row.last_state == "REBUTTING"
    if running:
        assert "still running" in err
        assert row.undecided_cells == 0
    else:
        assert "halted at REBUTTING" in err and "p" * 12 in err
        assert "still running" not in err
        assert row.undecided_cells == 1


@pytest.mark.skipif(shutil.which("pgrep") is None, reason="needs pgrep")
def test_a_live_saffron_cell_is_found_by_its_spec_id():
    probe = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import time; time.sleep(30)",
            "saffron",
            "cell",
            ".saffron/specs/SA-9999-probe.md",
        ]
    )
    try:
        assert driver._cell_running("SA-9999")
        assert not driver._cell_running("SA-9998")
    finally:
        probe.kill()
        probe.wait()
    assert not driver._cell_running("SA-9999")


def test_a_resnapshot_keeps_what_the_loop_recorded(loop):
    # `build_queue` passes over a spec with a finished task, so an order rebuilt from
    # the scan alone lost every reviewable PR and every drop.
    ready, dropped, _merged, new = loop.ids
    driver._save(
        [
            loop.row(0, state="READY_FOR_REVIEW", pr=10),
            loop.row(1, dropped="operator's call"),
            loop.row(2, state="READY_FOR_REVIEW", pr=11),
        ]
    )
    # What the scan returns now: the three recorded specs all have finished
    # tasks (or a drop the ledger knows nothing of), and one spec is new.
    loop.scan_returns(1, 3)

    assert driver.cmd_snapshot(argparse.Namespace(force=True, new=False, add=[])) == 0

    rows = {p.spec_id: p for p in driver._load()}
    assert set(rows) == {ready, dropped, new}  # a merged PR leaves the loop
    assert (rows[ready].state, rows[ready].pr) == ("READY_FOR_REVIEW", 10)
    assert rows[dropped].dropped == "operator's call"
    assert rows[new].state is None
    assert driver._stale(list(rows.values())) == []


def test_a_resnapshot_names_a_new_spec_and_leaves_it_out_unasked(loop, capsys):
    # Run 7 (2026-09-18): `--force` after a spec edit took in two specs whose
    # parent had become reviewable, unannounced and unreviewed (item b-afec7c).
    ready, _dropped, _merged, new = loop.ids
    driver._save([loop.row(0, state="READY_FOR_REVIEW", pr=10)])
    loop.scan_returns(0, 3)

    assert driver.cmd_snapshot(argparse.Namespace(force=True, new=False, add=None)) == 0

    assert [p.spec_id for p in driver._load()] == [ready]
    out = capsys.readouterr().out
    assert "new since the last snapshot, left out (1):" in out
    assert new in out.split("order:")[0]


def test_a_resnapshot_names_new_specs_even_when_nothing_known_is_left(loop, capsys):
    # The empty-order return came before the arrivals were printed, so the
    # operator saw "nothing to run" and never the specs held out.
    new = loop.ids[3]
    driver._save([loop.row(2, state="READY_FOR_REVIEW", pr=11)])
    loop.scan_returns(3)

    assert driver.cmd_snapshot(argparse.Namespace(force=True, new=False, add=None)) == 1

    out = capsys.readouterr().out
    assert "new since the last snapshot, left out (1):" in out
    assert new in out


def test_a_forced_snapshot_with_no_order_to_read_is_a_first_snapshot(loop):
    # With nothing known, every spec read as new and all were held out.
    loop.scan_returns(0, 3)

    assert driver.cmd_snapshot(argparse.Namespace(force=True, new=False, add=None)) == 0

    assert {p.spec_id for p in driver._load()} == {loop.ids[0], loop.ids[3]}


def test_add_takes_in_only_the_new_specs_it_names(loop, capsys):
    # A spec joins after its own step 1b review, so one reviewed spec must be
    # addable while another waits.
    ready, _dropped, waiting, reviewed = loop.ids
    driver._save([loop.row(0, state="READY_FOR_REVIEW", pr=10)])
    loop.scan_returns(0, 2, 3)

    assert (
        driver.cmd_snapshot(argparse.Namespace(force=True, new=False, add=[reviewed]))
        == 0
    )

    assert {p.spec_id for p in driver._load()} == {ready, reviewed}
    out = capsys.readouterr().out
    assert f"left out (1):\n  {waiting}" in out


def test_add_refuses_a_spec_that_is_not_new(loop, capsys):
    ready, *_ = loop.ids
    driver._save([loop.row(0, state="READY_FOR_REVIEW", pr=10)])
    loop.scan_returns(0, 3)

    assert (
        driver.cmd_snapshot(argparse.Namespace(force=True, new=False, add=[ready])) == 1
    )
    assert ready in capsys.readouterr().err
    assert [p.spec_id for p in driver._load()] == [ready]


def test_add_without_force_is_refused_rather_than_ignored(loop, capsys):
    loop.scan_returns(0, 3)

    assert driver.cmd_snapshot(argparse.Namespace(force=False, new=False, add=[])) == 1
    assert "--add" in capsys.readouterr().err
    assert not driver.ORDER.exists()


def test_a_new_loop_forgets_the_last_loops_drops(loop):
    # Run 6 (2026-09-17): `--force` over run 5's finished order brought back
    # three specs `dropped` for a reason that was true of run 5 only.
    merged, dropped, *_ = loop.ids
    driver._save(
        [
            loop.row(0, state="READY_FOR_REVIEW", pr=11),
            loop.row(1, dropped="kept the loop to another chain"),
        ]
    )
    loop.scan_returns(1)

    assert driver.cmd_snapshot(argparse.Namespace(force=False, new=True, add=None)) == 0

    [row] = driver._load()
    assert (row.spec_id, row.dropped) == (dropped, None)


def test_a_new_loop_is_refused_while_the_last_one_has_an_open_pull_request(
    loop, capsys
):
    driver._save([loop.row(0, state="READY_FOR_REVIEW", pr=10)])
    loop.scan_returns(1)

    assert driver.cmd_snapshot(argparse.Namespace(force=False, new=True, add=None)) == 1
    assert "#10" in capsys.readouterr().err
    assert [p.pr for p in driver._load()] == [10]


def _ledger_with_one_cell(tmp_path):
    from saffron.gates.contract import GateResult
    from saffron.ledger import Ledger

    ledger = Ledger(tmp_path / "ledger.db")
    repo_id = ledger.upsert_repo("r", "git@github.com:o/r.git", "/mirror", "policy")
    task_id = ledger.create_task(
        ledger.create_run(repo_id, "b" * 40),
        "SA-0001",
        "s" * 40,
        "saffron/SA-0001",
        budget_usd=6.0,
    )
    implement = None
    for phase, turns, cost, subtype, terminal_reason in (
        ("IMPLEMENTING", 20, 1.82, "success", None),  # the plan checkpoint
        ("IMPLEMENTING", 41, 2.33, "error_max_turns", None),
        ("REPAIRING", 7, 0.40, "success", None),
        ("IMPLEMENTING", 3, 0.17, "success", None),  # the salvage turn
        ("REVIEWING", 11, 0.80, "success", None),
        ("REBUTTING", 45, 3.09, "error_max_budget_usd", "budget_exhausted"),
    ):
        attempt = ledger.open_attempt(task_id, phase)
        ledger.close_attempt(
            attempt,
            session_id=None,
            subtype=subtype,
            terminal_reason=terminal_reason,
            num_turns=turns,
            cost_usd_est=cost,
        )
        if phase == "IMPLEMENTING":
            implement = attempt
    ledger.record_gate_result(
        GateResult(
            gate="size",
            status="pass",
            tool="size 1",
            summary="269 changed lines within the bug ceiling of 300",
        ),
        attempt_id=implement,
    )
    ledger.set_task_state(task_id, "READY_FOR_REVIEW")
    return ledger, repo_id


def _spec(spec_id, spec_type="bug", touches=2, criteria=3):
    from saffron.intake import Spec

    return Spec(
        id=spec_id,
        title=spec_id,
        type=spec_type,
        touches=[f"f{i}.py" for i in range(touches)],
        acceptance_criteria=[f"c{i}" for i in range(criteria)],
    )


def test_known_specs_skips_a_missing_done_directory(tmp_path, monkeypatch):
    # A repo with nothing retired yet has no `done/`, and `discover_specs`
    # raises `SpecError` on a directory that does not exist.
    specs_dir = tmp_path / ".saffron" / "specs"
    specs_dir.mkdir(parents=True)
    (specs_dir / "SA-0001-x.md").write_text(
        "---\nid: SA-0001\ntitle: x\ntype: bug\n---\n"
    )
    monkeypatch.setattr(driver, "SPECS_DIR", specs_dir)

    assert set(driver._known_specs()) == {"SA-0001"}


def test_history_splits_a_cells_spend_by_phase_and_names_how_attempts_ended(tmp_path):
    # SA-0087: 47 of 60 turns went to the plan checkpoint, and nothing showed
    # the operator that a cell of its shape needed more.
    ledger, repo_id = _ledger_with_one_cell(tmp_path)

    [cell] = driver._past_cells(ledger, repo_id, {"SA-0001": _spec("SA-0001")})

    assert cell.spec_id == "SA-0001"
    assert cell.state == "READY_FOR_REVIEW"
    assert cell.budget_usd == 6.0
    assert cell.plan == (20, pytest.approx(1.82))
    assert cell.implement == (44, pytest.approx(2.50))
    assert cell.repair == (7, pytest.approx(0.40))  # REPAIR is its own phase
    assert "implement 44t $2.50  repair 7t $0.40" in driver._cell_line(cell)
    assert cell.peak_turns == 45  # REBUT runs under `max_turns` too
    assert cell.review_usd == pytest.approx(0.80)
    assert cell.rebut_usd == pytest.approx(3.09)
    assert cell.endings == [
        "IMPLEMENTING error_max_turns",
        "REBUTTING error_max_budget_usd (budget_exhausted)",
    ]
    assert cell.size == "269 changed lines within the bug ceiling of 300"


def test_history_before_a_commit_hides_later_cells_and_always_the_specs_own(tmp_path):
    # A blind review must not see the outcome it is being scored against.
    ledger, repo_id = _ledger_with_one_cell(tmp_path)
    specs = {"SA-0001": _spec("SA-0001")}

    assert (
        driver._past_cells(ledger, repo_id, specs, before="2000-01-01 00:00:00") == []
    )
    assert (
        len(driver._past_cells(ledger, repo_id, specs, before="2999-01-01 00:00:00"))
        == 1
    )
    assert driver._past_cells(ledger, repo_id, specs, exclude="SA-0001") == []


def test_history_before_a_cells_own_start_hides_it(tmp_path):
    # "Started before": a cell that started at `before` itself is hidden.
    ledger, repo_id = _ledger_with_one_cell(tmp_path)
    [[row]] = ledger.tasks_by_spec(repo_id).values()
    started = ledger.attempts(row["task_id"])[0]["started_at"]

    assert (
        driver._past_cells(
            ledger, repo_id, {"SA-0001": _spec("SA-0001")}, before=started
        )
        == []
    )


def _cell(
    spec_id,
    spec_type,
    touches,
    criteria,
    started_at="2026-09-14 12:00:00",
    *,
    peak_cut_off=False,
):
    return driver.PastCell(
        spec_id=spec_id,
        spec_type=spec_type,
        touches=touches,
        criteria=criteria,
        started_at=started_at,
        state="READY_FOR_REVIEW",
        budget_usd=6.0,
        plan=driver.Spend(20, 1.82),
        implement=driver.Spend(44, 2.5),
        repair=driver.Spend(0, 0.0),
        peak_turns=41,
        review_usd=0.8,
        rebut_usd=0.0,
        endings=[],
        peak_cut_off=peak_cut_off,
        size=None,
    )


def test_history_lists_only_the_same_type_most_similar_shape_first():
    lines = driver._history_lines(
        _spec("SA-0009", touches=2, criteria=3),
        [
            _cell("SA-0002", "feature", 2, 3),
            _cell("SA-0003", "bug", 9, 9),
            _cell("SA-0004", "bug", 2, 4),
        ],
    )

    assert lines[0].startswith("SA-0009  bug  touches=2 criteria=3")
    assert [line.split()[0] for line in lines[1:-1]] == ["SA-0004", "SA-0003"]
    assert lines[-1].startswith("ceilings:")


def test_history_lists_the_newer_of_two_same_shape_cells_first():
    lines = driver._history_lines(
        _spec("SA-0009", touches=2, criteria=3),
        [
            _cell("SA-0002", "bug", 2, 3, started_at="2026-09-01 12:00:00"),
            _cell("SA-0003", "bug", 2, 3, started_at="2026-09-10 12:00:00"),
        ],
    )

    assert [line.split()[0] for line in lines[1:-1]] == ["SA-0003", "SA-0002"]
    assert lines[-1].startswith("ceilings:")


def test_history_compares_the_targets_ceilings_with_the_rows_it_printed():
    # SA-0031 (EXHAUSTED at 141 of 140 turns) and SA-0087@24edb32 (60 turns
    # against a 47-turn plan checkpoint) both read `checked` because nothing
    # actually compared the target's ceilings with what its history showed.
    target = _spec("SA-0009", touches=2, criteria=3)
    target.max_turns = 100
    target.budget_usd = 10.0

    high_peak = _cell("SA-0002", "bug", 2, 3)
    high_peak.peak_turns = 90
    high_peak.plan = driver.Spend(1, 1.0)
    high_peak.implement = driver.Spend(1, 1.0)
    high_peak.repair = driver.Spend(0, 0.0)
    high_spend = _cell("SA-0003", "bug", 2, 3)
    high_spend.peak_turns = 30
    high_spend.plan = driver.Spend(5, 5.0)
    high_spend.implement = driver.Spend(5, 5.0)
    high_spend.repair = driver.Spend(5, 5.0)

    # Neither of these is printed — `_history_lines` filters to the target's
    # own type and then to `_HISTORY_LIMIT` — so comparing against the
    # unfiltered rows is the mis-comparison this line exists to prevent.
    off_type = _cell("SA-0004", "feature", 2, 3)
    off_type.peak_turns = 500
    off_type.plan = driver.Spend(1, 500.0)
    crowded = [_cell(f"SA-01{n:02d}", "bug", 2, 3) for n in range(12)]
    for spare in crowded:
        spare.peak_turns = 1
        spare.plan = driver.Spend(1, 0.0)
        spare.implement = driver.Spend(1, 0.0)
        spare.repair = driver.Spend(0, 0.0)
    overflow = crowded[-1]
    overflow.spec_id = "SA-0999"
    overflow.peak_turns = 400
    overflow.plan = driver.Spend(1, 400.0)

    rows = [high_peak, high_spend, *crowded[:-1], off_type, overflow]
    ceilings = driver._history_lines(target, rows)[-1]

    assert ceilings.startswith("ceilings:")
    assert "max_turns=100" in ceilings
    assert "SA-0002's peak 90t (used), above by 10t" in ceilings
    assert "budget_usd=10.0" in ceilings
    assert "SA-0003's pre-review total $15.00, below by $5.00" in ceilings
    assert "SA-0004" not in ceilings  # wrong type, never printed
    assert "SA-0999" not in ceilings  # past the limit, never printed

    # The mirrored directions. Witnessed one way each, hardcoding both words
    # passes the whole suite — and ceiling-below-peak is SA-0031, the very
    # case this line exists to catch.
    target.max_turns = 50
    target.budget_usd = 20.0
    mirrored = driver._history_lines(target, [high_peak, high_spend])[-1]
    assert "SA-0002's peak 90t (used), below by 40t" in mirrored
    assert "SA-0003's pre-review total $15.00, above by $5.00" in mirrored


def test_an_abnormal_ending_reaches_the_row_however_its_subtype_was_spelled(
    tmp_path,
):
    """Item 144: `endings` filtered on `subtype not in (None, "success")`, so an
    attempt that ended abnormally while its subtype read `success` never reached
    the row at all. Six such rows are in the live ledger — `subtype=success,
    terminal_reason=api_error` — including a 22-turn REVIEWING attempt, and a
    spec review reading `history` could not see any of them."""
    ledger, repo_id = _ledger_with_one_cell(tmp_path)
    task_id = ledger.tasks_by_spec_id(repo_id, "SA-0001")[-1]["task_id"]
    ledger.close_attempt(
        ledger.open_attempt(task_id, "REVIEWING"),
        session_id=None,
        subtype="success",
        terminal_reason="api_error",
        num_turns=22,
        cost_usd_est=0.9,
    )
    (cell,) = driver._past_cells(ledger, repo_id, {"SA-0001": _spec("SA-0001")})
    ledger.close()

    assert "REVIEWING success (api_error)" in cell.endings


def test_a_peak_that_stopped_on_budget_is_not_called_a_turn_floor(tmp_path):
    """The fixture peaks at 45 turns on a REBUTTING attempt that ran out of
    budget, while the attempt that hit the turn ceiling ran 41. Reading the
    label off the row's `endings` calls 45 "at least what it needed" — a
    ceilings misreading of exactly the kind this line exists to end."""
    ledger, repo_id = _ledger_with_one_cell(tmp_path)
    (cell,) = driver._past_cells(ledger, repo_id, {"SA-0001": _spec("SA-0001")})
    ledger.close()

    assert cell.peak_turns == 45
    assert "IMPLEMENTING error_max_turns" in cell.endings
    assert cell.peak_cut_off is False

    target = _spec("SA-0009", touches=2, criteria=3)
    target.max_turns = 80
    ceilings = driver._ceilings_line(target, [cell])
    assert "peak 45t (used)" in ceilings
    assert "floor" not in ceilings


def test_a_turn_ceiling_carried_only_on_terminal_reason_is_still_a_floor():
    """`session.py` reads `terminal_reason` as the primary field and keeps the
    subtype so a result event arriving without one does not skip the control in
    silence. A predicate on the subtype alone drops the primary half."""
    assert driver._cut_off_at_turn_ceiling(
        {"subtype": "error", "terminal_reason": "max_turns"}
    )
    assert driver._cut_off_at_turn_ceiling(
        {"subtype": "error_max_turns", "terminal_reason": None}
    )
    assert not driver._cut_off_at_turn_ceiling(
        {"subtype": "error_max_budget_usd", "terminal_reason": "budget_exhausted"}
    )
    assert not driver._cut_off_at_turn_ceiling(
        {"subtype": "success", "terminal_reason": None}
    )


def test_the_ceilings_line_does_not_call_an_equal_ceiling_headroom():
    """`max_turns` equal to the peak is check 4's blocker, not headroom —
    "at or below the peak a similar cell needed" (spec-reviewer.md). Printing
    "above by 0t" there is the reading this whole line exists to end, and 9
    live specs declare `max_turns: 120` against ledger peaks of exactly 120."""
    target = _spec("SA-0009", touches=2, criteria=3)
    target.max_turns = 140

    level = _cell("SA-0002", "bug", 2, 3)
    level.peak_turns = 140

    ceilings = driver._history_lines(target, [level])[-1]

    assert "SA-0002's peak 140t (used), level with it" in ceilings
    assert "above" not in ceilings.split(";")[0]
    assert "by 0t" not in ceilings

    # One either side still reads as a gap, and in the right direction.
    target.max_turns = 141
    assert "above by 1t" in driver._history_lines(target, [level])[-1]
    target.max_turns = 139
    assert "below by 1t" in driver._history_lines(target, [level])[-1]


def test_the_ceilings_line_calls_a_cut_off_rows_peak_a_floor():
    # A row whose worst attempt ended `error_max_turns` was cut off at its own
    # ceiling: its peak says what it needed at least, not what it used.
    target = _spec("SA-0009", touches=2, criteria=3)
    target.max_turns = 80

    cutoff = _cell("SA-0002", "bug", 2, 3, peak_cut_off=True)
    cutoff.peak_turns = 60
    # Endings the label must not be read off: the row ends `error_max_turns`
    # on an attempt that is not the peak, which is the false floor below.
    cutoff.endings = ["IMPLEMENTING error_max_turns"]
    other = _cell("SA-0003", "bug", 2, 3)
    other.peak_turns = 30
    other.endings = []

    ceilings = driver._history_lines(target, [cutoff, other])[-1]
    assert "SA-0002's peak 60t (a floor" in ceilings

    # The same cutoff row, now not the highest peak: the row actually being
    # compared did not hit its own ceiling, so no floor language belongs to it.
    other.peak_turns = 90
    ceilings = driver._history_lines(target, [cutoff, other])[-1]
    assert "SA-0003's peak 90t (used)" in ceilings
    assert "floor" not in ceilings

    # An abnormal ending that is not a turn ceiling is not a floor either, and
    # an `error_max_turns` ending on some *other* attempt does not make one.
    other.endings = ["IMPLEMENTING error_max_turns"]
    ceilings = driver._history_lines(target, [cutoff, other])[-1]
    assert "SA-0003's peak 90t (used)" in ceilings
    assert "floor" not in ceilings


class _StubLedger:
    """A ledger `check` never queries directly — `_past_cells` is
    monkeypatched — but must still be able to `close()`."""

    def close(self):
        pass


def test_check_blocks_the_ceilings_check_4_calls_blockers_and_no_others(
    monkeypatch, capsys
):
    # Five cases: both clear, turns below/level with the peak (both block),
    # budget below the total (blocks) and level with it (does not).
    target = _spec("SA-0009", touches=2, criteria=3)
    target.max_turns = 100
    target.budget_usd = 10.0

    other = _cell("SA-2000", "bug", 2, 3)  # neither maximum, and not first
    other.peak_turns = 50
    other.plan, other.implement, other.repair = (
        driver.Spend(1, 1.0),
        driver.Spend(1, 1.0),
        driver.Spend(0, 0.0),
    )
    peak_row = _cell("SA-2001", "bug", 2, 3)
    peak_row.peak_turns = 90
    peak_row.plan, peak_row.implement, peak_row.repair = (
        driver.Spend(1, 1.0),
        driver.Spend(1, 1.0),
        driver.Spend(0, 0.0),
    )
    budget_row = _cell("SA-2002", "bug", 2, 3)
    budget_row.peak_turns = 30
    budget_row.plan, budget_row.implement, budget_row.repair = (
        driver.Spend(2, 2.0),
        driver.Spend(2, 3.0),
        driver.Spend(0, 4.0),
    )  # whole-dollar pre-review total: $9.00, safe against float drift

    rows = [other, peak_row, budget_row]
    monkeypatch.setattr(driver, "_known_specs", lambda: {"SA-0009": target})
    monkeypatch.setattr(driver, "_ledger_and_repo", lambda: (_StubLedger(), 1, "url"))
    monkeypatch.setattr(driver, "_past_cells", lambda *a, **k: rows)

    def run():
        rc = driver.cmd_check(argparse.Namespace(spec_id="SA-0009"))
        return rc, capsys.readouterr().out

    rc, out = run()
    assert rc == 0 and "blocker:" not in out

    target.max_turns = 89  # below the 90t peak
    rc, out = run()
    assert rc == 1
    assert "blocker: max_turns=89" in out and "blocker: budget_usd" not in out

    target.max_turns = 90  # level with the peak: still a blocker
    rc, out = run()
    assert rc == 1
    assert "blocker: max_turns=90" in out and "blocker: budget_usd" not in out

    target.max_turns = 100  # clear again
    target.budget_usd = 8.0  # below the $9.00 pre-review total
    rc, out = run()
    assert rc == 1
    assert "blocker: budget_usd=8.0" in out and "blocker: max_turns" not in out

    target.budget_usd = 9.0  # level with it: not a blocker
    rc, out = run()
    assert rc == 0 and "blocker:" not in out


def test_check_judges_the_rows_history_prints_and_no_others(monkeypatch, capsys):
    # A far-shaped, an off-type, and a past-the-limit row each carry a peak
    # above the ceiling — only the rows `history` prints may vote (b-281f0a).
    target = _spec("SA-0009", touches=2, criteria=3)
    target.max_turns = 50
    target.budget_usd = 1000.0

    far = _cell("SA-3000", "bug", 9, 9)  # far shape: cut by closeness, not type
    far.peak_turns = 999
    low = [_cell(f"SA-31{n:02d}", "bug", 2, 3) for n in range(12)]
    for row in low:
        row.peak_turns = 10
    off_type = _cell("SA-3001", "feature", 2, 3)  # same shape, wrong type
    off_type.peak_turns = 999
    overflow = _cell("SA-3002", "bug", 2, 3)  # same shape and type, past limit
    overflow.peak_turns = 999

    rows = [far, *low[:6], off_type, *low[6:], overflow]
    monkeypatch.setattr(driver, "_known_specs", lambda: {"SA-0009": target})
    monkeypatch.setattr(driver, "_ledger_and_repo", lambda: (_StubLedger(), 1, "url"))
    monkeypatch.setattr(driver, "_past_cells", lambda *a, **k: rows)

    assert driver.cmd_check(argparse.Namespace(spec_id="SA-0009")) == 0
    assert "blocker:" not in capsys.readouterr().out


def test_check_reports_a_review_and_rebut_shortfall_as_a_concern(monkeypatch, capsys):
    # Worst review+rebut sum is a third row's ($5+$0, $0+$4, $3+$3 -> $6.00).
    # Each row's own pre-review total is distinct and non-zero too (below).
    target = _spec("SA-0009", touches=2, criteria=3)
    target.max_turns = 1000

    def row(spec_id, review_usd, rebut_usd, pre_review_usd):
        c = _cell(spec_id, "bug", 2, 3)
        c.plan = driver.Spend(1, pre_review_usd)
        c.implement, c.repair = driver.Spend(0, 0.0), driver.Spend(0, 0.0)
        c.peak_turns, c.review_usd, c.rebut_usd = 1, review_usd, rebut_usd
        return c

    rows = [
        row("SA-4000", 5.0, 0.0, 2.0),
        row("SA-4001", 0.0, 4.0, 1.0),
        row("SA-4002", 3.0, 3.0, 4.0),  # also the highest pre-review total
    ]
    monkeypatch.setattr(driver, "_known_specs", lambda: {"SA-0009": target})
    monkeypatch.setattr(driver, "_ledger_and_repo", lambda: (_StubLedger(), 1, "url"))
    monkeypatch.setattr(driver, "_past_cells", lambda *a, **k: rows)

    # $11.00 minus the $4.00 pre-review total leaves $7.00, covering $6.00.
    target.budget_usd = 11.0
    assert driver.cmd_check(argparse.Namespace(spec_id="SA-0009")) == 0
    assert "concern:" not in capsys.readouterr().out

    # $9.50 minus $4.00 leaves $5.50, which cannot cover $6.00 — a concern.
    # Reading $9.50 raw, or subtracting some other row's total, would not be.
    target.budget_usd = 9.5
    assert driver.cmd_check(argparse.Namespace(spec_id="SA-0009")) == 0
    assert "concern:" in capsys.readouterr().out


def test_check_with_nothing_to_compare_against_claims_no_pass(monkeypatch, capsys):
    target = _spec("SA-0009", touches=2, criteria=3)
    monkeypatch.setattr(driver, "_known_specs", lambda: {"SA-0009": target})
    monkeypatch.setattr(driver, "_ledger_and_repo", lambda: (_StubLedger(), 1, "url"))
    monkeypatch.setattr(driver, "_past_cells", lambda *a, **k: [])

    assert driver.cmd_check(argparse.Namespace(spec_id="SA-0009")) == 0
    out = capsys.readouterr().out
    assert "no past cells of this shape to compare against" in out
    assert "check: ceilings clear this shape's history" not in out


def _spec_text(max_turns):
    return f"---\nid: SA-0001\ntitle: x\ntype: bug\nmax_turns: {max_turns}\n---\n"


def test_spec_at_reads_the_spec_as_it_stood_at_the_commit(empty_repo):
    # SA-0087@24edb32's header showed its later 90 turns, not the 60 it was run at.
    tmp_path = empty_repo
    specs = tmp_path / ".saffron" / "specs"
    (specs / "done").mkdir(parents=True)
    first = _commit(tmp_path, ".saffron/specs/SA-0001-x.md", _spec_text(60))
    _git(tmp_path, "mv", ".saffron/specs/SA-0001-x.md", ".saffron/specs/done/")
    second = _commit(tmp_path, ".saffron/specs/done/SA-0001-x.md", _spec_text(90))

    assert driver._spec_at("SA-0001", first, cwd=tmp_path).max_turns == 60
    assert driver._spec_at("SA-0001", second, cwd=tmp_path).max_turns == 90
    assert driver._spec_at("SA-0002", second, cwd=tmp_path) is None


def test_spec_at_reads_a_spec_that_todays_intake_refuses_as_a_disclosed_mutant(
    empty_repo,
):
    # SA-0063 predates item 82's check; `history` still needs its shape.
    tmp_path = empty_repo
    (tmp_path / ".saffron" / "specs").mkdir(parents=True)
    text = (
        "---\n"
        "id: SA-0063\n"
        "title: x\n"
        "type: bug\n"
        "max_turns: 42\n"
        "acceptance:\n"
        "  - claim: does the thing\n"
        "    witness: tests/test_x.py::test_thing\n"
        "    mutant:\n"
        "      file: x.py\n"
        "      find: 'return True'\n"
        "---\n"
        "The current code has `return True` at the end.\n"
    )
    commit = _commit(tmp_path, ".saffron/specs/SA-0063-x.md", text)

    spec = driver._spec_at("SA-0063", commit, cwd=tmp_path)

    assert spec is not None
    assert spec.id == "SA-0063"
    assert spec.max_turns == 42


def test_specs_at_reads_other_specs_as_they_stood_and_keeps_todays_where_absent(
    empty_repo,
):
    # A blind review ranks past cells by shape; today's text for them is later
    # than the base it reviews.
    tmp_path = empty_repo
    (tmp_path / ".saffron" / "specs").mkdir(parents=True)
    then = _commit(tmp_path, ".saffron/specs/SA-0001-x.md", _spec_text(60))
    _commit(tmp_path, ".saffron/specs/SA-0001-x.md", _spec_text(90))
    today = {"SA-0001": _spec("SA-0001"), "SA-0002": _spec("SA-0002")}
    today["SA-0001"].max_turns = 90

    shapes = driver._specs_at(then, today, cwd=tmp_path)

    assert shapes["SA-0001"].max_turns == 60
    assert shapes["SA-0002"] is today["SA-0002"]  # no text at `then` to read


def test_history_before_shows_every_spec_as_it_stood_and_none_of_the_targets_cells(
    empty_repo, monkeypatch, capsys
):
    # The helpers above were each tested; that `cmd_history` wires all four
    # into `--before` was not, and a mutant dropping any one passed.
    from saffron.ledger import Ledger

    tmp_path = empty_repo
    (tmp_path / ".saffron" / "specs").mkdir(parents=True)
    monkeypatch.setenv(
        "GIT_COMMITTER_DATE", "2000-01-01T00:00:00Z"
    )  # before every cell
    early = _commit(tmp_path, ".saffron/specs/SA-0001-x.md", _spec_text(60))
    monkeypatch.setenv("GIT_COMMITTER_DATE", "2099-01-01T00:00:00Z")  # after every cell
    then = _commit(
        tmp_path,
        ".saffron/specs/SA-0002-y.md",
        "---\nid: SA-0002\ntitle: y\ntype: bug\ntouches: [a.py, b.py]\n---\n",
    )
    ledger, repo_id = _ledger_with_one_cell(tmp_path)
    other = ledger.create_task(
        ledger.create_run(repo_id, "b" * 40), "SA-0002", "t" * 40, "saffron/SA-0002"
    )
    ledger.close_attempt(
        ledger.open_attempt(other, "IMPLEMENTING"),
        session_id=None,
        subtype="success",
        terminal_reason=None,
        num_turns=5,
        cost_usd_est=0.5,
    )
    today = {"SA-0001": _spec("SA-0001"), "SA-0002": _spec("SA-0002", touches=9)}
    today["SA-0001"].max_turns = 90
    real_git = driver._git
    monkeypatch.setattr(driver, "_git", lambda *a, cwd=None: real_git(*a, cwd=tmp_path))
    monkeypatch.setattr(driver, "_known_specs", lambda: today)
    ledger.close()
    monkeypatch.setattr(  # `cmd_history` closes the ledger it is handed
        driver,
        "_ledger_and_repo",
        lambda: (Ledger(tmp_path / "ledger.db"), repo_id, "u"),
    )

    args = SimpleNamespace(spec_id="SA-0001", before=early, limit=12)
    assert driver.cmd_history(args) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[1:] == ["ceilings: no past cells of this shape to compare against"]

    args = SimpleNamespace(spec_id="SA-0001", before=then, limit=12)
    assert driver.cmd_history(args) == 0

    header, *rest = capsys.readouterr().out.splitlines()
    *cells, ceilings = rest
    assert "max_turns=60" in header
    assert "budget_usd=" in header
    assert [line.split()[0] for line in cells] == ["SA-0002"]
    assert "touches=2" in cells[0]
    assert ceilings.startswith("ceilings:")


def test_commit_time_is_utc_in_the_ledgers_own_format(tmp_path):
    env = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_COMMITTER_DATE": "2026-09-14T12:00:00-07:00",
        "GIT_AUTHOR_DATE": "2026-09-14T12:00:00-07:00",
    }
    for argv in (
        ["git", "init", "-q", "-b", "main"],
        [
            "git",
            "-c",
            "user.email=t@example.com",
            "-c",
            "user.name=t",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "c",
        ],
    ):
        subprocess.run(argv, cwd=tmp_path, env=env, check=True)

    assert driver._commit_time("HEAD", cwd=tmp_path) == "2026-09-14 19:00:00"


def test_a_linked_stack_is_marked_ready_only_once_every_base_reads_back(
    loop, monkeypatch
):
    # Operator decision (2026-09-18): drafts are PACKAGE's, and a reviewed,
    # linked stack is handed over ready.
    rows = [
        loop.row(0, state="READY_FOR_REVIEW", pr=10),
        loop.row(1, state="READY_FOR_REVIEW", pr=11),
    ]
    ran = []
    monkeypatch.setattr(driver, "_load", lambda: rows)
    monkeypatch.setattr(driver, "_stack_order", lambda _rows: (rows, []))
    monkeypatch.setattr(driver, "_merge_conflicts", lambda _a, _b: [])
    monkeypatch.setattr(driver, "_trunk", lambda: "origin/main")
    monkeypatch.setattr(
        driver.subprocess,
        "run",
        lambda cmd, **_k: ran.append(cmd) or subprocess.CompletedProcess(cmd, 0),
    )
    bases = {10: "main", 11: rows[0].branch}
    monkeypatch.setattr(driver, "_gh_pr_field", lambda n, _name: bases[n])

    assert driver.cmd_stack(argparse.Namespace(execute=True)) == 0
    assert [c for c in ran if c[:3] == ["gh", "pr", "ready"]] == [
        ["gh", "pr", "ready", "10"],
        ["gh", "pr", "ready", "11"],
    ]

    ran.clear()
    bases[11] = "main"
    assert driver.cmd_stack(argparse.Namespace(execute=True)) == 1
    assert not [c for c in ran if c[:3] == ["gh", "pr", "ready"]]


def test_a_held_spec_is_passed_over_until_released(loop):
    # Run 7: `next` named SA-0100 while its edit sat in an open pull request,
    # and a cell started then would have run the old text.
    first, second, *_ = loop.ids
    driver._save([loop.row(0), loop.row(1)])

    assert (
        driver.cmd_hold(argparse.Namespace(spec_id=first, why="#333", release=False))
        == 0
    )
    chosen, note = driver._next_spec(driver._load(), again=False)
    assert chosen.spec_id == second
    assert f"held {first}: #333" in note

    assert (
        driver.cmd_hold(argparse.Namespace(spec_id=first, why=None, release=True)) == 0
    )
    chosen, _note = driver._next_spec(driver._load(), again=False)
    assert chosen.spec_id == first


def test_a_resnapshot_releases_a_hold(loop):
    held, *_ = loop.ids
    driver._save([loop.row(0, held="#333", last_state="RATE_LIMITED")])
    loop.scan_returns(0)

    assert driver.cmd_snapshot(argparse.Namespace(force=True, new=False, add=None)) == 0

    [row] = driver._load()
    assert (row.spec_id, row.held) == (held, None)


def _probe(root, find, replace, *command):
    return argparse.Namespace(
        file="mod.py", find=find, replace=replace, root=root, run=list(command)
    )


def test_a_probe_whose_find_misses_runs_nothing(tmp_path, capsys):
    # Run 7, #338: two probes whose find text missed still printed "1 passed",
    # which reads exactly like a survivor.
    (tmp_path / "mod.py").write_text("x = 1\n")
    marker = tmp_path / "ran"
    args = _probe(
        tmp_path, "x = 2", "x = 3", sys.executable, "-c", f"open({str(marker)!r}, 'w')"
    )

    assert driver.cmd_probe(args) == 1
    assert "matches 0 times" in capsys.readouterr().err
    assert not marker.exists()
    assert (tmp_path / "mod.py").read_text() == "x = 1\n"


@pytest.mark.parametrize(
    ("script", "verdict"),
    [
        ("import mod; assert mod.x == 1", "killed:"),
        ("import mod", "survived:"),
        (
            "print('FAILED t.py::a - TypeError: boom'); raise SystemExit(1)",
            "killed only by errors",
        ),
    ],
)
def test_a_probe_reports_its_verdict_and_restores_the_file(
    tmp_path, capsys, script, verdict
):
    (tmp_path / "mod.py").write_text("x = 1\n")

    assert (
        driver.cmd_probe(
            _probe(tmp_path, "x = 1", "x = 2", sys.executable, "-c", script)
        )
        == 0
    )

    assert capsys.readouterr().out.startswith(verdict)
    assert (tmp_path / "mod.py").read_text() == "x = 1\n"


@pytest.mark.parametrize(
    "test_body",
    [
        # pytest wraps its summary at COLUMNS, and a long name loses the
        # ` - AttributeError` the verdict reads.
        "def test_a_sentence_long_enough_that_pytest_cuts_its_summary_row_short():\n"
        "    assert mod.C.value == 1\n",
        # A captured log line starts with ERROR too, and matched no error name.
        "def test_logs():\n"
        "    logging.getLogger().error('boom')\n"
        "    assert mod.C.value == 1\n",
    ],
    ids=["long-name", "logged-error"],
)
def test_a_probe_that_only_raised_is_not_killed_under_real_pytest(
    tmp_path, monkeypatch, capsys, test_body
):
    monkeypatch.setenv("COLUMNS", "80")
    (tmp_path / "mod.py").write_text("class C:\n    value = 1\n")
    (tmp_path / "test_mod.py").write_text(
        "import logging\nimport mod\n\n\n" + test_body
    )
    command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]

    assert (
        driver.cmd_probe(
            _probe(tmp_path, "value = 1", "other = 1", *command, "test_mod.py")
        )
        == 0
    )

    assert capsys.readouterr().out.startswith("killed only by errors")


def test_a_probe_whose_command_is_missing_fails_and_restores(tmp_path, capsys):
    (tmp_path / "mod.py").write_text("x = 1\n")

    assert driver.cmd_probe(_probe(tmp_path, "x = 1", "x = 2", "no-such-binary")) == 1
    assert "no-such-binary" in capsys.readouterr().err
    assert (tmp_path / "mod.py").read_text() == "x = 1\n"


def test_probe_parses_its_options_before_the_command(tmp_path, monkeypatch, capsys):
    # Run 7: `nargs=REMAINDER` after the file swallowed `--find`, and the tests
    # above call `cmd_probe` directly, so none saw it.
    (tmp_path / "mod.py").write_text("x = 1\n")
    argv = ["probe", "mod.py", "--find", "x = 1", "--replace", "x = 2"]
    argv += ["--root", str(tmp_path), "--", sys.executable, "-c", "import mod"]
    monkeypatch.setattr(sys, "argv", ["driver.py", *argv])
    monkeypatch.syspath_prepend(str(tmp_path))

    assert driver.main() == 0
    assert capsys.readouterr().out.startswith("survived:")


def test_only_probe_takes_a_command_after_the_separator(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["driver.py", "status", "--", "true"])

    with pytest.raises(SystemExit) as exit_:
        driver.main()
    assert exit_.value.code == 2


def test_cite_resolves_a_specs_citations_at_the_base_commit(
    empty_repo, monkeypatch, capsys
):
    """Twelve wrong shapes of `cite` this kills: reading the working tree
    instead of `--base`; reporting a citation that resolves; the swapped exit
    code; a boundary off by one at a file's last line; requiring `/` and
    missing a bare filename, or the reverse; dropping a range's end, or the
    whole range; treating a host:port or a dotted module name as a citation;
    letting the empty suffix into the known set; and printing defects with no
    count line, or a count line only when the run is clean."""
    repo = empty_repo
    monkeypatch.setattr(driver, "REPO", repo)
    thing = "\n".join(f"line {i}" for i in range(1, 21)) + "\n"  # 20 lines
    (repo / "pkg").mkdir()
    (repo / "pkg" / "thing.py").write_text(thing)
    (repo / "pkg" / "README").write_text("no suffix at all\n")
    (repo / "run.zzz").write_text("a\nb\nc\nd\n")  # 4 lines, an unlisted suffix
    _git(repo, "add", "pkg/thing.py", "pkg/README", "run.zzz")
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
    spec = repo / "spec.md"
    spec.write_text(clean)
    assert driver.cmd_cite(SimpleNamespace(spec_path=str(spec), base=base)) == 0
    out = capsys.readouterr().out
    assert out == "2 citation(s) checked\n"

    defective = clean + (
        " A now-missing `pkg/missing.py:5` citation points at nothing. Another "
        "dangling `dir/README:3` points at nothing too. The range "
        "`pkg/thing.py:2-999` overruns the file. The helper `run.zzz:9` "
        "overruns too."
    )
    spec.write_text(defective)
    assert driver.cmd_cite(SimpleNamespace(spec_path=str(spec), base=base)) == 1
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert lines[:-1] == [
        f"pkg/missing.py:5: no such file at {base}",
        f"dir/README:3: no such file at {base}",
        f"pkg/thing.py:2-999: pkg/thing.py has 20 lines at {base}",
        f"run.zzz:9: run.zzz has 4 lines at {base}",
    ]
    assert lines[-1] == "6 citation(s) checked"


def test_cite_anchors_a_bare_line_number_inside_its_own_paragraph(
    empty_repo, monkeypatch, capsys
):
    """Seven wrong anchors this kills: never anchoring to a plain backticked
    path with no line number of its own; anchoring only from a plain path and
    never from an explicit `path:n`, or the reverse (skipping the path test
    entirely); dropping a bare number rather than resolving it; letting a
    paragraph inherit the path a paragraph above it named; reporting an
    unanchored bare number as though it needed no report; and reading a bare
    `:n` while skipping a bare range."""
    repo = empty_repo
    monkeypatch.setattr(driver, "REPO", repo)
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

    spec = repo / "spec.md"
    spec.write_text(
        "The loop reads `a/thing.py` for its shape. See `:5` for where it starts.\n"
        "\n"
        "Read `b/other.py:3` for the check. It matches no `importlib.util:2`. "
        "Then `:4` confirms it.\n"
        "\n"
        "Nothing here names a path. See `:9-45` for confirmation.\n"
    )

    assert driver.cmd_cite(SimpleNamespace(spec_path=str(spec), base=base)) == 1
    out = capsys.readouterr().out
    assert out.splitlines() == [
        ":9-45: no path named earlier in its paragraph",
        "4 citation(s) checked",
    ]


def test_cite_reports_a_citation_whose_quoted_text_sits_on_other_lines(
    empty_repo, monkeypatch, capsys
):
    """Nine wrong moved-text checks this kills: reporting whenever the range
    lacks the text, without checking the file carries it elsewhere;
    searching the whole file instead of the range; reporting with no line
    numbers; skipping a bare citation; reading only a range's first line;
    requiring every other backticked string to be absent from the range
    rather than just one being present; reading only the first such
    string, or skipping a sentence holding more than one; and merging two
    sentences across a period followed by a digit, so a later sentence's
    text wrongly suppresses an earlier citation's report."""
    repo = empty_repo
    monkeypatch.setattr(driver, "REPO", repo)
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
    _git(repo, "add", "mod/lib.py")
    _git(repo, "commit", "-qm", "fixture")
    base = _git(repo, "rev-parse", "HEAD")

    spec = repo / "spec.md"
    spec.write_text(
        # Case 1: a bare citation, "alpha" at two other lines, none in range.
        "The module `mod/lib.py` explains this. The `alpha` value sits at "
        "`:11-20` supposedly.\n"
        "\n"
        # Case 2: a range citation; "beta" sits inside it, below its first line.
        "Here `mod/lib.py:21-30` holds the `beta` reading directly.\n"
        "\n"
        # Case 3: a bare citation; "gamma" sits nowhere in the file at all.
        "The module `mod/lib.py` is unrelated here. It holds `gamma` at "
        "`:31-40` supposedly.\n"
        "\n"
        # Case 4: two strings; "epsilon" is in range, "delta" is not — no report.
        "Here `delta` and `epsilon` both matter, at `mod/lib.py:41-50` precisely.\n"
        "\n"
        # Case 5: two strings, neither in range; "omega" elsewhere, "zeta" nowhere.
        "Both `zeta` and `omega` are claimed, at `mod/lib.py:51-60` exactly.\n"
        "\n"
        # Case 6: a period before a digit must still end the sentence, or the
        # next sentence's "iota" (in range) wrongly suppresses this report.
        "Here `theta` sits far off, at `mod/lib.py:61-70` presently. 9 more "
        "items hold `iota` too.\n"
    )

    assert driver.cmd_cite(SimpleNamespace(spec_path=str(spec), base=base)) == 1
    out = capsys.readouterr().out
    defects = out.splitlines()[:-1]
    assert defects == [
        "mod/lib.py:11-20: quoted text sits at mod/lib.py:3, 7 instead",
        "mod/lib.py:51-60: quoted text sits at mod/lib.py:9 instead",
        "mod/lib.py:61-70: quoted text sits at mod/lib.py:71 instead",
    ]
    assert out.splitlines()[-1] == "6 citation(s) checked"
