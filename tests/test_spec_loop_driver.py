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
    # A review round took #247 from 294 to 367 lines against a bug's 300, and
    # `size` runs only in the cell (item 40). Each branch here adds one line.
    tmp, _tips = repo
    assert driver._size(lower, upper, spec_type, cwd=tmp) == (1, ceiling)


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
        ids=[spec.id for spec, _sha in loaded], row=row, scan_returns=scan_returns
    )


def test_snapshot_shows_each_specs_title_and_budget_and_counts_every_root(loop, capsys):
    # The operator saw no queue before the first cell, and the note said "3
    # spec(s) declare no depends_on" of four that did.
    loop.scan_returns(0, 1, 2, 3)

    assert driver.cmd_snapshot(argparse.Namespace(force=False)) == 0

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


def test_a_resnapshot_holds_out_a_spec_edited_while_its_pr_is_open(loop, capsys):
    # The scan looks past the loop's own PRs, so the edited spec came back as a
    # fresh candidate, and its next cell would have packaged onto #10's branch.
    edited, sibling, _merged, _new = loop.ids
    driver._save(
        [loop.row(0, state="READY_FOR_REVIEW", pr=10, spec_sha="edited"), loop.row(1)]
    )
    seen = loop.scan_returns(0, 1)

    assert driver.cmd_snapshot(argparse.Namespace(force=True)) == 0

    assert [p.spec_id for p in driver._load()] == [sibling]
    assert "#10 is still open" in capsys.readouterr().out
    assert seen["loop_branches"] == {f"saffron/{edited}", f"saffron/{sibling}"}


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
    # said so; `next` needs the pushed sha to tell a reviewed parent apart.
    spec_id = loop.ids[0]
    driver._save([loop.row(0)])
    sha = driver._load()[0].spec_sha
    task = {
        "task_id": 7,
        "state": "READY_FOR_REVIEW",
        "pushed_sha": "p" * 40,
        "spent_usd_est": 7.55,
        "budget_usd": 6.0,
    }
    ledger = SimpleNamespace(
        tasks_by_spec=lambda _repo: {(spec_id, sha): [task]},
        tasks_by_repo=lambda _repo: [
            {"task_id": 7, "pr_url": "https://github.com/o/r/pull/247"}
        ],
        close=lambda: None,
    )
    monkeypatch.setattr(driver, "_ledger_and_repo", lambda: (ledger, 1, "url"))

    assert driver.cmd_record(argparse.Namespace(spec_id=spec_id)) == 0
    assert driver._load()[0].pushed_sha == "p" * 40
    assert capsys.readouterr().out == (
        f"{spec_id}  READY_FOR_REVIEW  #247  $7.55 of $6.00\n"
    )


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

    assert driver.cmd_snapshot(argparse.Namespace(force=True)) == 0

    rows = {p.spec_id: p for p in driver._load()}
    assert set(rows) == {ready, dropped, new}  # a merged PR leaves the loop
    assert (rows[ready].state, rows[ready].pr) == ("READY_FOR_REVIEW", 10)
    assert rows[dropped].dropped == "operator's call"
    assert rows[new].state is None
    assert driver._stale(list(rows.values())) == []
