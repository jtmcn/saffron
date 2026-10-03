"""The stack batch's finishing layer commit and its publish (ADR 7, SA-0151, SA-0167)."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from saffron.agents.findings import Finding, Severity
from saffron.follow_up import Pooled
from saffron.ledger import Ledger
from saffron.qualify import FollowUpGroup, Qualified


def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def _spec_md(spec_id: str, title: str) -> str:
    return f"---\nid: {spec_id}\ntitle: {title}\ntype: chore\n---\nBody.\n"


def _isolate_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The env `commit_finish`'s own fixture isolates git under, reused by
    `publish_finish`'s tests so a hand push below finds no operator config."""
    empty = tmp_path / "empty-home"
    empty.mkdir()
    monkeypatch.setenv("HOME", str(empty))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(empty))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")


def _refs(repo: Path) -> dict[str, str]:
    out = _git(repo, "for-each-ref", "--format=%(objectname) %(refname)")
    refs: dict[str, str] = {}
    for line in out.splitlines():
        sha, ref = line.split(" ", 1)
        refs[ref] = sha
    return refs


def _stack(root: Path, count: int) -> SimpleNamespace:
    """A linear stack of `count` layers (criterion 1 and 2's own fixture,
    reused by `SA-0170`). A work repository on `trunk`, its bare remote and
    its mirror. A `Ledger` whose tasks and layers are recorded top first,
    out of both task id and position order.
    """
    origin = root / "origin"
    origin.mkdir(parents=True)
    _git(origin, "init", "-q", "-b", "trunk")
    (origin / "a.py").write_text("a = 0\n")
    _git(origin, "add", "-A")
    _git(origin, "-c", "user.email=o@o", "-c", "user.name=O", "commit", "-qm", "base")

    heads: dict[int, str] = {}
    for n in range(1, count + 1):
        branch = f"saffron/TE-{n}"
        start = "trunk" if n == 1 else f"saffron/TE-{n - 1}"
        _git(origin, "checkout", "-q", "-b", branch, start)
        (origin / "a.py").write_text(f"a = {n}\n")
        _git(origin, "add", "-A")
        _git(
            origin,
            "-c",
            "user.email=o@o",
            "-c",
            "user.name=O",
            "commit",
            "-qm",
            branch,
        )
        heads[n] = _git(origin, "rev-parse", "HEAD")
    _git(origin, "checkout", "-q", "trunk")

    remote = root / "remote.git"
    _git(root, "clone", "-q", "--bare", str(origin), str(remote))
    mirror = root / "mirror.git"
    _git(root, "clone", "-q", "--mirror", str(remote), str(mirror))

    ledger_path = root / "ledger.db"
    ledger = Ledger(ledger_path)
    base_sha = _git(origin, "rev-parse", "trunk")
    repo_id = ledger.upsert_repo(
        "r", "https://example.invalid/o/r.git", str(mirror), policy_sha=None
    )
    batch_id = ledger.create_batch(100.0)

    task_ids: dict[int, int] = {}
    for n in range(count, 0, -1):
        spec_id = f"TE-{n}"
        run_id = ledger.create_run(repo_id, base_sha=base_sha, batch_id=batch_id)
        task_id = ledger.create_task(
            run_id, spec_id=spec_id, spec_sha="s" * 64, branch=f"saffron/{spec_id}"
        )
        task_ids[n] = task_id
        ledger.set_task_package(
            task_id,
            "READY_FOR_REVIEW",
            f"saffron/{spec_id}",
            heads[n],
            f"https://github.com/o/r/pull/{100 + n}",
        )
    for n in range(count, 0, -1):
        ledger.record_stack_layer(
            task_ids[n],
            position=n,
            predecessor_task_id=task_ids[n - 1] if n > 1 else None,
            generation=0,
        )

    layers = [
        {
            "position": n,
            "spec_id": f"TE-{n}",
            "branch": f"saffron/TE-{n}",
            "head": heads[n],
            "pr_url": f"https://github.com/o/r/pull/{100 + n}",
            "task_id": task_ids[n],
        }
        for n in range(1, count + 1)
    ]

    return SimpleNamespace(
        root=root,
        origin=origin,
        remote=remote,
        mirror=mirror,
        ledger=ledger,
        ledger_path=ledger_path,
        batch_id=batch_id,
        layers=layers,
        url=str(remote),
        slug="o/r",
    )


def _finishing_commit(mirror: Path, parent: str) -> str:
    tree = _git(mirror, "rev-parse", f"{parent}^{{tree}}")
    return _git(
        mirror,
        "-c",
        "user.email=saffron@localhost",
        "-c",
        "user.name=Saffron",
        "commit-tree",
        tree,
        "-p",
        parent,
        "-m",
        "finish",
    )


def _hand_push(remote: Path, branch: str, dest: Path) -> None:
    """Clone `remote` at `branch`, commit an intruder's file, and push it
    back. This is the moved-head half of criterion 2's escalation table."""
    _git(dest.parent, "clone", "-q", "-b", branch, str(remote), str(dest))
    (dest / "intruder.txt").write_text("hand pushed\n")
    _git(dest, "add", "-A")
    _git(
        dest, "-c", "user.email=h@h", "-c", "user.name=H", "commit", "-qm", "hand push"
    )
    _git(dest, "push", "-q", "origin", branch)


def _seed_finish_branch(
    remote: Path, batch_id: int, head_branch: str, dest: Path
) -> None:
    """Pushes `saffron/batch-<batch_id>-finish` to `remote` at `head_branch`'s
    own head, standing in for an earlier finish the lease must refuse."""
    _git(dest.parent, "clone", "-q", "-b", head_branch, str(remote), str(dest))
    _git(
        dest, "push", "-q", "origin", f"HEAD:refs/heads/saffron/batch-{batch_id}-finish"
    )


class _FakeGh:
    """Answers `pr view <url> --json baseRefName` from `bases`, another
    `pr view` with `view_existing`, `pr create` with `create`, `pr ready`
    with success, and `stack link` with `link`. It records every call it
    is given in order."""

    def __init__(
        self,
        bases: dict[str, str],
        *,
        create: tuple[int, str, str] = (
            0,
            "https://github.com/o/r/pull/200\n",
            "",
        ),
        view_existing: tuple[int, str, str] | None = None,
        link: tuple[int, str, str] = (0, "", ""),
    ) -> None:
        self.bases = bases
        self.create = create
        self.view_existing = view_existing
        self.link = link
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(argv))
        if argv[:3] == ["gh", "pr", "view"] and "baseRefName" in argv:
            base = self.bases.get(argv[3])
            if base is None:
                return subprocess.CompletedProcess(argv, 1, "", "no such pull request")
            return subprocess.CompletedProcess(argv, 0, base + "\n", "")
        if argv[:3] == ["gh", "pr", "create"]:
            code, out, err = self.create
            return subprocess.CompletedProcess(argv, code, out, err)
        if argv[:3] == ["gh", "pr", "view"]:
            if self.view_existing is None:
                return subprocess.CompletedProcess(argv, 1, "", "no such pull request")
            code, out, err = self.view_existing
            return subprocess.CompletedProcess(argv, code, out, err)
        if argv[:3] == ["gh", "pr", "ready"]:
            return subprocess.CompletedProcess(argv, 0, "", "")
        if argv[:3] == ["gh", "stack", "link"]:
            code, out, err = self.link
            return subprocess.CompletedProcess(argv, code, out, err)
        raise AssertionError(f"unexpected gh call: {argv}")


def _bases(layers: list[dict]) -> dict[str, str]:
    """Each layer's own pull request answered against its predecessor's
    branch, or `trunk` for the bottom layer."""
    return {
        layer["pr_url"]: (layers[i - 1]["branch"] if i > 0 else "trunk")
        for i, layer in enumerate(layers)
    }


def _qual(
    ledger: Ledger,
    task_id: int,
    *,
    lens: str,
    filed: Severity,
    outcome: str,
    file: str,
    claim: str,
    line: int = 3,
    reason: str = "",
) -> None:
    finding = Finding(
        lens=lens, severity=filed, file=file, line=line, claim=claim, anchored=True
    )
    ledger.record_qualification(
        task_id, finding=finding, filed=filed, outcome=outcome, reason=reason
    )


@pytest.fixture
def stack(tmp_path, monkeypatch):
    """The arrangement the `commit_finish` and `write_findings` witnesses
    drive: an origin repo on three stacked branches, its bare mirror, and a
    ledger carrying two batches' tasks, layers and texts."""
    empty = tmp_path / "empty-home"
    empty.mkdir()
    monkeypatch.setenv("HOME", str(empty))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(empty))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")

    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "-q", "-b", "main")
    (origin / "a.py").write_text("a = 0\n")
    specs = origin / ".saffron" / "specs"
    specs.mkdir(parents=True)
    (specs / "TE-1-one.md").write_text(_spec_md("TE-1", "One"))
    (specs / "ten.md").write_text(_spec_md("TE-10", "Ten"))
    (specs / "TE-7-seven.md").write_text(_spec_md("TE-7", "Seven"))
    (specs / "TE-5-five.md").write_text(_spec_md("TE-5", "Five"))
    (specs / "TE-6-six.md").write_text(_spec_md("TE-6", "Six"))
    (specs / "done").mkdir()
    (specs / "done" / "README.md").write_text("Retired specs.\n")
    _git(origin, "add", "-A")
    _git(origin, "-c", "user.email=o@o", "-c", "user.name=O", "commit", "-qm", "base")
    base_sha = _git(origin, "rev-parse", "HEAD")

    def _branch_commit(name: str, content: str) -> str:
        _git(origin, "checkout", "-q", "-b", name)
        (origin / "a.py").write_text(content)
        _git(origin, "add", "-A")
        _git(origin, "-c", "user.email=o@o", "-c", "user.name=O", "commit", "-qm", name)
        return _git(origin, "rev-parse", "HEAD")

    head_10 = _branch_commit("saffron/TE-10", "a = 10\n")
    head_7 = _branch_commit("saffron/TE-7", "a = 17\n")
    head_20 = _branch_commit("saffron/TE-20", "a = 20\n")

    (origin / "extra.txt").write_text("extra\n")
    _git(origin, "add", "-A")
    _git(
        origin, "-c", "user.email=o@o", "-c", "user.name=O", "commit", "-qm", "one more"
    )
    head_20_plus = _git(origin, "rev-parse", "HEAD")

    mirror = tmp_path / "mirror.git"
    _git(tmp_path, "clone", "-q", "--mirror", str(origin), str(mirror))

    ledger = Ledger(tmp_path / "ledger.db")
    repo_id = ledger.upsert_repo(
        "r", "https://example.invalid/o/r.git", str(mirror), policy_sha=None
    )

    def _task(spec_id: str, *, batch_id: int | None) -> int:
        run_id = ledger.create_run(repo_id, base_sha=base_sha, batch_id=batch_id)
        return ledger.create_task(
            run_id, spec_id=spec_id, spec_sha="s" * 64, branch=f"saffron/{spec_id}"
        )

    def _package(task_id: int, spec_id: str, head: str) -> None:
        ledger.set_task_package(
            task_id,
            "READY_FOR_REVIEW",
            f"saffron/{spec_id}",
            head,
            f"https://example.invalid/pr/{spec_id}",
        )

    batch_b = ledger.create_batch(100.0)
    batch_o = ledger.create_batch(100.0)

    te10 = _task("TE-10", batch_id=batch_b)
    _package(te10, "TE-10", head_10)
    te20 = _task("TE-20", batch_id=batch_b)
    _package(te20, "TE-20", head_20)
    te7 = _task("TE-7", batch_id=batch_b)
    _package(te7, "TE-7", head_7)

    te5 = _task("TE-5", batch_id=batch_b)
    ledger.set_task_state(te5, "EXHAUSTED")
    te21 = _task("TE-21", batch_id=batch_b)
    te22 = _task("TE-22", batch_id=batch_b)
    ledger.set_task_state(te22, "EXHAUSTED")
    te23 = _task("TE-23", batch_id=batch_b)
    te24 = _task("TE-24", batch_id=batch_b)

    te6 = _task("TE-6", batch_id=batch_o)
    _package(te6, "TE-6", head_10)
    te26 = _task("TE-26", batch_id=batch_o)
    ledger.set_task_state(te26, "EXHAUSTED")

    te20_outside = _task("TE-20", batch_id=None)
    _package(te20_outside, "TE-20", head_20_plus)

    ledger.record_stack_layer(te7, position=2, predecessor_task_id=te10, generation=0)
    ledger.record_stack_layer(te20, position=3, predecessor_task_id=te7, generation=1)
    ledger.record_stack_layer(te10, position=1, predecessor_task_id=None, generation=0)
    ledger.record_stack_layer(te6, position=1, predecessor_task_id=None, generation=0)

    ledger.record_spec_text(
        te7,
        origin="revision",
        spec_id="TE-7",
        path=".saffron/specs/TE-7-seven.md",
        text=_spec_md("TE-7", "Seven r1"),
    )
    ledger.record_spec_text(
        te7,
        origin="revision",
        spec_id="TE-7",
        path=".saffron/specs/TE-7-seven.md",
        text=_spec_md("TE-7", "Seven r2"),
    )
    ledger.record_spec_text(
        te5,
        origin="revision",
        spec_id="TE-5",
        path=".saffron/specs/TE-5-five.md",
        text=_spec_md("TE-5", "Five r1"),
    )
    ledger.record_spec_text(
        te20,
        origin="follow_up",
        spec_id="TE-20",
        path=".saffron/specs/TE-20-follow.md",
        text=_spec_md("TE-20", "Twenty"),
    )
    ledger.record_spec_text(
        te20,
        origin="revision",
        spec_id="TE-20",
        path=".saffron/specs/TE-20-follow.md",
        text=_spec_md("TE-20", "Twenty r1"),
    )
    ledger.record_spec_text(
        te21,
        origin="follow_up",
        spec_id="TE-21",
        path=".saffron/specs/TE-21-other.md",
        text=_spec_md("TE-21", "Twenty-one"),
    )
    ledger.record_spec_text(
        te22,
        origin="follow_up",
        spec_id="TE-22",
        path=".saffron/specs/TE-22-missed.md",
        text=_spec_md("TE-22", "Twenty-two"),
    )
    ledger.record_spec_text(
        te22,
        origin="revision",
        spec_id="TE-22",
        path=".saffron/specs/TE-22-missed.md",
        text=_spec_md("TE-22", "Twenty-two r1"),
    )
    ledger.record_spec_text(
        te23,
        origin="follow_up",
        spec_id="TE-23",
        path=".saffron/specs/TE-23-refused.md",
        text=_spec_md("TE-23", "Twenty-three"),
    )
    ledger.record_spec_text(
        te6,
        origin="revision",
        spec_id="TE-6",
        path=".saffron/specs/TE-6-six.md",
        text=_spec_md("TE-6", "Six r1"),
    )
    ledger.record_spec_text(
        te26,
        origin="follow_up",
        spec_id="TE-26",
        path=".saffron/specs/TE-26-other.md",
        text=_spec_md("TE-26", "Twenty-six"),
    )

    return SimpleNamespace(
        mirror=mirror,
        ledger=ledger,
        batch_b=batch_b,
        batch_o=batch_o,
        task=_task,
        tasks={
            "TE-10": te10,
            "TE-20": te20,
            "TE-7": te7,
            "TE-5": te5,
            "TE-21": te21,
            "TE-22": te22,
            "TE-23": te23,
            "TE-24": te24,
            "TE-6": te6,
            "TE-26": te26,
        },
        heads={
            "TE-10": head_10,
            "TE-7": head_7,
            "TE-20": head_20,
            "TE-20-plus": head_20_plus,
        },
    )


def test_the_finishing_commit_writes_each_layers_and_unrun_texts_and_retires_each_layers_spec(
    stack, tmp_path
):
    from saffron.finish import commit_finish

    before = _git(stack.mirror, "for-each-ref")

    emitted: list[str] = []
    sha = commit_finish(
        stack.ledger,
        stack.batch_b,
        [stack.tasks["TE-24"], stack.tasks["TE-21"]],
        mirror=stack.mirror,
        workdir=tmp_path / "work",
        emit=emitted.append,
    )
    assert sha is not None

    assert len(emitted) == 1
    assert str(stack.tasks["TE-24"]) in emitted[0]

    assert _git(stack.mirror, "rev-parse", f"{sha}^1") == stack.heads["TE-20"]
    author = _git(stack.mirror, "show", "-s", "--format=%an <%ae>", sha)
    assert author == "Saffron <saffron@localhost>"
    subject = _git(stack.mirror, "show", "-s", "--format=%s", sha)
    assert subject == f"saffron batch {stack.batch_b}: finishing layer"

    assert _git(stack.mirror, "for-each-ref") == before
    assert len(_git(stack.mirror, "worktree", "list").splitlines()) == 1

    diff = sorted(
        _git(
            stack.mirror,
            "diff",
            "--no-renames",
            "--name-status",
            f"{stack.heads['TE-20']}..{sha}",
        ).splitlines()
    )
    assert diff == sorted(
        [
            "D\t.saffron/specs/ten.md",
            "D\t.saffron/specs/TE-7-seven.md",
            "A\t.saffron/specs/done/ten.md",
            "A\t.saffron/specs/done/TE-7-seven.md",
            "A\t.saffron/specs/done/TE-20-follow.md",
            "A\t.saffron/specs/TE-21-other.md",
        ]
    )

    assert "Seven r2" in _git(
        stack.mirror, "show", f"{sha}:.saffron/specs/done/TE-7-seven.md"
    )
    assert "Twenty r1" in _git(
        stack.mirror, "show", f"{sha}:.saffron/specs/done/TE-20-follow.md"
    )
    assert "Twenty-one" in _git(
        stack.mirror, "show", f"{sha}:.saffron/specs/TE-21-other.md"
    )
    assert "Ten" in _git(stack.mirror, "show", f"{sha}:.saffron/specs/done/ten.md")

    empty_batch = stack.ledger.create_batch(10.0)
    before2 = _git(stack.mirror, "for-each-ref")
    result = commit_finish(
        stack.ledger,
        empty_batch,
        [stack.tasks["TE-21"]],
        mirror=stack.mirror,
        workdir=tmp_path / "work2",
    )
    assert result is None
    assert _git(stack.mirror, "for-each-ref") == before2


def test_a_spec_text_outside_the_spec_directory_or_off_its_hash_is_refused_before_any_commit(
    stack, tmp_path, monkeypatch
):
    from saffron.finish import commit_finish
    from saffron.repos import mirror as git_mirror

    bad_paths = [
        ".saffron/specs/../CLAUDE.md",
        ".saffron/specs/done/x.md",
        "CLAUDE.md",
        ".saffron/specs/x.txt",
        ".saffron/specs/x.md/../../CLAUDE.md",
    ]
    real_spec_text = stack.ledger.spec_text

    def _bad_row(task_id: int, **overrides):
        def _stand_in(tid: int):
            row = real_spec_text(tid)
            if tid != task_id or row is None:
                return row
            data = dict(row)
            data.update(overrides)
            return data

        return _stand_in

    def _assert_refused(
        task_id: int, is_unrun: bool, i: int, match: str, **overrides
    ) -> None:
        with monkeypatch.context() as m:
            m.setattr(stack.ledger, "spec_text", _bad_row(task_id, **overrides))
            calls: list[tuple] = []
            m.setattr(
                git_mirror,
                "add_worktree",
                lambda mirror, sha, dest: calls.append((mirror, sha, dest)),
            )
            before = _git(stack.mirror, "count-objects", "-v")
            # The message names this row, so a raise on another row fails it.
            with pytest.raises(ValueError, match=match):
                commit_finish(
                    stack.ledger,
                    stack.batch_b,
                    [task_id] if is_unrun else [],
                    mirror=stack.mirror,
                    workdir=tmp_path / f"bad-{task_id}-{i}",
                )
            assert calls == []
            assert _git(stack.mirror, "count-objects", "-v") == before

    for spec_id, is_unrun in [("TE-7", False), ("TE-21", True)]:
        task_id = stack.tasks[spec_id]
        for i, bad_path in enumerate(bad_paths):
            _assert_refused(task_id, is_unrun, i, re.escape(bad_path), path=bad_path)
        _assert_refused(
            task_id,
            is_unrun,
            len(bad_paths),
            f"{spec_id}.*does not match its hash",
            spec_sha="0" * 64,
        )


def test_findings_json_holds_each_layers_findings_and_each_follow_up_that_added_no_layer(
    stack, tmp_path
):
    """`finish.write_findings` pools a layer's qualified findings against
    the follow-up writer's pooled groups. It keeps a generation-1 layer's
    own critic findings, and a plain follow-up's. It also lists the
    follow-ups a layer never swallowed (`b-792ab2` step 8, section 4)."""
    from saffron.finish import FINDINGS_NAME, write_findings

    ledger = stack.ledger
    te10 = stack.tasks["TE-10"]
    te7 = stack.tasks["TE-7"]
    te20 = stack.tasks["TE-20"]
    te6 = stack.tasks["TE-6"]

    # The qualifications table, in the order given.
    _qual(
        ledger,
        te7,
        lens="spec",
        filed="concern",
        outcome="qualified",
        file="qualified.py",
        claim="pooled spec",
    )
    _qual(
        ledger,
        te10,
        lens="join",
        filed="blocker",
        outcome="qualified",
        file="qualified.py",
        claim="join",
    )
    _qual(
        ledger,
        te10,
        lens="spec",
        filed="concern",
        outcome="qualified",
        file="qualified.py",
        claim="pooled spec",
    )
    _qual(
        ledger,
        te10,
        lens="spec",
        filed="concern",
        outcome="qualified",
        file="written.py",
        claim="written",
    )
    _qual(
        ledger,
        te10,
        lens="spec",
        filed="concern",
        outcome="qualified",
        file="qualified.py",
        claim="pooled spec",
        line=4,
    )
    _qual(
        ledger,
        te10,
        lens="spec",
        filed="concern",
        outcome="qualified",
        file="written.py",
        claim="pooled spec",
    )
    _qual(
        ledger,
        te10,
        lens="standards",
        filed="concern",
        outcome="qualified",
        file="qualified.py",
        claim="pooled spec",
    )
    _qual(
        ledger,
        te10,
        lens="spec",
        filed="concern",
        outcome="qualified",
        file="qualified.py",
        claim="other",
    )
    _qual(
        ledger,
        te10,
        lens="spec",
        filed="concern",
        outcome="killed",
        file="qualified.py",
        claim="pooled spec",
    )
    _qual(
        ledger,
        te10,
        lens="standards",
        filed="concern",
        outcome="unanchored",
        file="unanchored.py",
        claim="far",
    )
    _qual(
        ledger,
        te10,
        lens="correctness",
        filed="note",
        outcome="note",
        file="note.py",
        claim="note",
    )
    _qual(
        ledger,
        te10,
        lens="spec",
        filed="concern",
        outcome="unverified",
        file="qualified.py",
        claim="pooled spec",
        reason="errored",
    )
    _qual(
        ledger,
        te6,
        lens="spec",
        filed="concern",
        outcome="qualified",
        file="qualified.py",
        claim="pooled spec",
    )

    # A generation-0 layer's own in-cell concern, dropped: already folded
    # into its qualifications above, were this not a synthetic fixture.
    ledger.record_findings(
        te10,
        [
            Finding(
                lens="correctness",
                severity="concern",
                file="decoy.py",
                line=1,
                claim="te10 decoy",
                anchored=True,
            )
        ],
    )
    # Decoys on tasks this call must never read: another batch's layer, another
    # batch's follow-up, and a revised queued spec with no layer.
    ledger.record_findings(
        stack.tasks["TE-6"],
        [
            Finding(
                lens="correctness",
                severity="concern",
                file="decoy.py",
                line=1,
                claim="te6 decoy",
                anchored=True,
            )
        ],
    )
    ledger.record_findings(
        stack.tasks["TE-5"],
        [
            Finding(
                lens="correctness",
                severity="concern",
                file="decoy.py",
                line=1,
                claim="te5 decoy",
                anchored=True,
            )
        ],
    )
    ledger.record_findings(
        stack.tasks["TE-26"],
        [
            Finding(
                lens="correctness",
                severity="concern",
                file="decoy.py",
                line=1,
                claim="te26 decoy",
                anchored=True,
            )
        ],
    )

    # TE-20, the generation-1 layer: seven in-cell findings, the last
    # filtered out because `spec` is no `review.LENSES` lens.
    te20_ids = ledger.record_findings(
        te20,
        [
            Finding(
                lens="correctness",
                severity="concern",
                file="k1.py",
                line=1,
                claim="k1",
                anchored=True,
            ),
            Finding(
                lens="contract",
                severity="blocker",
                file="k2.py",
                line=1,
                claim="k2",
                anchored=True,
            ),
            Finding(
                lens="adequacy",
                severity="blocker",
                file="k3.py",
                line=1,
                claim="k3",
                anchored=True,
            ),
            Finding(
                lens="correctness",
                severity="blocker",
                file="k4.py",
                line=1,
                claim="k4",
                anchored=True,
            ),
            Finding(
                lens="correctness",
                severity="note",
                file="k5.py",
                line=1,
                claim="k5",
                anchored=False,
            ),
            Finding(
                lens="conventions",
                severity="concern",
                file="k6.py",
                line=1,
                claim="k6",
                anchored=True,
            ),
            Finding(
                lens="spec",
                severity="concern",
                file="k7.py",
                line=1,
                claim="k7",
                anchored=True,
            ),
        ],
    )
    ledger.record_rebuttal(te20_ids[1], verdict="confirmed", rebuttal="r1")
    ledger.record_rebuttal(te20_ids[2], verdict=None, rebuttal="r2")
    ledger.record_rebuttal(te20_ids[3], verdict="withdrawn", rebuttal="r3")

    # TE-22, a follow-up that missed after a revision: one in-cell concern.
    ledger.record_findings(
        stack.tasks["TE-22"],
        [
            Finding(
                lens="correctness",
                severity="concern",
                file="m.py",
                line=1,
                claim="te22 concern",
                anchored=True,
            )
        ],
    )

    # Three more follow-ups in B, created out of spec id order, that added
    # no layer and carry their own critic findings.
    te29 = stack.task("TE-29", batch_id=stack.batch_b)
    te27 = stack.task("TE-27", batch_id=stack.batch_b)
    te28 = stack.task("TE-28", batch_id=stack.batch_b)
    ledger.set_task_state(te29, "GATE_ERROR")
    ledger.set_task_state(te27, "REVIEWING")
    ledger.set_task_state(te28, "REBUTTING")
    ledger.record_spec_text(
        te29,
        origin="follow_up",
        spec_id="TE-29",
        path=".saffron/specs/TE-29-nine.md",
        text=_spec_md("TE-29", "Twenty-nine"),
    )
    ledger.record_spec_text(
        te27,
        origin="follow_up",
        spec_id="TE-27",
        path=".saffron/specs/TE-27-seven.md",
        text=_spec_md("TE-27", "Twenty-seven"),
    )
    ledger.record_spec_text(
        te28,
        origin="follow_up",
        spec_id="TE-28",
        path=".saffron/specs/TE-28-eight.md",
        text=_spec_md("TE-28", "Twenty-eight"),
    )
    ledger.record_findings(
        te29,
        [
            Finding(
                lens="adequacy",
                severity="note",
                file="p.py",
                line=1,
                claim="te29 note",
                anchored=True,
            ),
            Finding(
                lens="spec",
                severity="concern",
                file="p.py",
                line=2,
                claim="te29 spec",
                anchored=True,
            ),
        ],
    )
    ledger.record_findings(
        te27,
        [
            Finding(
                lens="correctness",
                severity="concern",
                file="p.py",
                line=1,
                claim="te27 concern",
                anchored=True,
            )
        ],
    )
    ledger.record_findings(
        te28,
        [
            Finding(
                lens="contract",
                severity="blocker",
                file="p.py",
                line=1,
                claim="te28 blocker",
                anchored=True,
            )
        ],
    )

    # Three pooled groups on `qualified.py`: two layers hold the same
    # matching finding, and the first of the two holds it second.
    matched = Finding(
        lens="spec",
        severity="blocker",
        file="qualified.py",
        line=3,
        claim="pooled spec",
        anchored=True,
    )
    unmatched = Finding(
        lens="spec",
        severity="blocker",
        file="qualified.py",
        line=9,
        claim="unmatched",
        anchored=True,
    )
    te10_key = ledger.record_key(te10)
    te6_key = ledger.record_key(te6)
    assert te10_key is not None and te6_key is not None
    pooled = [
        Pooled(
            group=FollowUpGroup(
                task_key=te10_key,
                file="qualified.py",
                findings=(
                    Qualified(te10_key, unmatched, "qualified", ""),
                    Qualified(te10_key, matched, "qualified", ""),
                ),
            ),
            reason="cap",
        ),
        Pooled(
            group=FollowUpGroup(
                task_key=te6_key,
                file="qualified.py",
                findings=(Qualified(te6_key, matched, "qualified", ""),),
            ),
            reason="O",
        ),
        Pooled(
            group=FollowUpGroup(
                task_key=te10_key,
                file="qualified.py",
                findings=(Qualified(te10_key, matched, "qualified", ""),),
            ),
            reason="later",
        ),
    ]

    dest = tmp_path / "nested" / "dir" / FINDINGS_NAME
    result = write_findings(
        ledger, stack.batch_b, [stack.tasks["TE-21"]], dest, pooled=pooled
    )
    assert result is dest
    assert dest.exists()

    data = json.loads(dest.read_text())
    assert data["batch"] == stack.batch_b
    assert isinstance(data["batch"], int)

    head10, head7, head20 = (
        stack.heads["TE-10"],
        stack.heads["TE-7"],
        stack.heads["TE-20"],
    )

    def _f(spec_id, head, lens, severity, file, line, claim, outcome, reason=""):
        return {
            "spec_id": spec_id,
            "head": head,
            "lens": lens,
            "severity": severity,
            "file": file,
            "line": line,
            "claim": claim,
            "outcome": outcome,
            "reason": reason,
        }

    expected_findings = [
        _f("TE-10", head10, "join", "blocker", "qualified.py", 3, "join", "follow_up"),
        _f(
            "TE-10",
            head10,
            "spec",
            "concern",
            "qualified.py",
            3,
            "pooled spec",
            "pooled",
            "cap",
        ),
        _f("TE-10", head10, "spec", "concern", "written.py", 3, "written", "follow_up"),
        _f(
            "TE-10",
            head10,
            "spec",
            "concern",
            "qualified.py",
            4,
            "pooled spec",
            "follow_up",
        ),
        _f(
            "TE-10",
            head10,
            "spec",
            "concern",
            "written.py",
            3,
            "pooled spec",
            "follow_up",
        ),
        _f(
            "TE-10",
            head10,
            "standards",
            "concern",
            "qualified.py",
            3,
            "pooled spec",
            "follow_up",
        ),
        _f("TE-10", head10, "spec", "concern", "qualified.py", 3, "other", "follow_up"),
        _f(
            "TE-10",
            head10,
            "standards",
            "concern",
            "unanchored.py",
            3,
            "far",
            "unanchored",
        ),
        _f("TE-10", head10, "correctness", "note", "note.py", 3, "note", "note"),
        _f(
            "TE-10",
            head10,
            "spec",
            "concern",
            "qualified.py",
            3,
            "pooled spec",
            "unverified",
            "errored",
        ),
        _f(
            "TE-7",
            head7,
            "spec",
            "concern",
            "qualified.py",
            3,
            "pooled spec",
            "follow_up",
        ),
        _f(
            "TE-20",
            head20,
            "correctness",
            "concern",
            "k1.py",
            1,
            "k1",
            "left_by_critic",
        ),
        _f(
            "TE-20",
            head20,
            "contract",
            "blocker",
            "k2.py",
            1,
            "k2",
            "left_by_critic",
            "confirmed",
        ),
        _f("TE-20", head20, "adequacy", "blocker", "k3.py", 1, "k3", "left_by_critic"),
        _f(
            "TE-20",
            head20,
            "correctness",
            "blocker",
            "k4.py",
            1,
            "k4",
            "left_by_critic",
            "withdrawn",
        ),
        _f("TE-20", head20, "correctness", "note", "k5.py", 1, "k5", "left_by_critic"),
        _f(
            "TE-20",
            head20,
            "conventions",
            "concern",
            "k6.py",
            1,
            "k6",
            "left_by_critic",
        ),
        _f(
            "TE-22",
            None,
            "correctness",
            "concern",
            "m.py",
            1,
            "te22 concern",
            "left_by_critic",
        ),
        _f("TE-29", None, "adequacy", "note", "p.py", 1, "te29 note", "left_by_critic"),
        _f(
            "TE-27",
            None,
            "correctness",
            "concern",
            "p.py",
            1,
            "te27 concern",
            "left_by_critic",
        ),
        _f(
            "TE-28",
            None,
            "contract",
            "blocker",
            "p.py",
            1,
            "te28 blocker",
            "left_by_critic",
        ),
    ]
    assert data["findings"] == expected_findings

    te22_text = ledger.spec_text(stack.tasks["TE-22"])
    te23_text = ledger.spec_text(stack.tasks["TE-23"])
    te29_text = ledger.spec_text(te29)
    te27_text = ledger.spec_text(te27)
    te28_text = ledger.spec_text(te28)
    assert data["follow_ups"] == [
        {
            "spec_id": "TE-22",
            "state": "EXHAUSTED",
            "path": te22_text["path"],
            "text": te22_text["text"],
        },
        {
            "spec_id": "TE-23",
            "state": "QUEUED",
            "path": te23_text["path"],
            "text": te23_text["text"],
        },
        {
            "spec_id": "TE-29",
            "state": "GATE_ERROR",
            "path": te29_text["path"],
            "text": te29_text["text"],
        },
        {
            "spec_id": "TE-27",
            "state": "REVIEWING",
            "path": te27_text["path"],
            "text": te27_text["text"],
        },
        {
            "spec_id": "TE-28",
            "state": "REBUTTING",
            "path": te28_text["path"],
            "text": te28_text["text"],
        },
    ]

    empty_batch = ledger.create_batch(10.0)
    empty_dest = tmp_path / "empty" / FINDINGS_NAME
    write_findings(ledger, empty_batch, [], empty_dest)
    empty_data = json.loads(empty_dest.read_text())
    assert empty_data == {"batch": empty_batch, "findings": [], "follow_ups": []}


def test_a_green_finish_pushes_its_own_branch_and_opens_its_draft_pull_request(
    tmp_path, monkeypatch
):
    from saffron.finish import PUSHED, publish_finish
    from saffron.repos import mirror as git_mirror

    _isolate_git(tmp_path, monkeypatch)

    def _run(count: int) -> None:
        s = _stack(tmp_path / f"stack-{count}", count)
        top = s.layers[-1]
        sha = _finishing_commit(s.mirror, top["head"])
        branch = f"saffron/batch-{s.batch_id}-finish"
        ref = f"refs/heads/saffron-finish/{s.batch_id}"
        gh = _FakeGh(_bases(s.layers))
        verify_calls: list[tuple[str, str]] = []

        def verify(sha_arg: str, base_arg: str) -> int:
            verify_calls.append((sha_arg, base_arg))
            assert git_mirror._git(s.mirror, "rev-parse", ref) == sha_arg
            return 0

        before_remote = _refs(s.remote)
        before_mirror = _refs(s.mirror)
        workdir = tmp_path / f"push-{count}"
        lines = publish_finish(
            s.ledger,
            s.batch_id,
            sha,
            mirror=s.mirror,
            url=s.url,
            slug=s.slug,
            verify=verify,
            gh=gh,
            workdir=workdir,
        )

        assert verify_calls == [(sha, top["head"])]

        after_remote = dict(before_remote)
        after_remote[f"refs/heads/{branch}"] = sha
        assert _refs(s.remote) == after_remote
        assert _refs(s.mirror) == before_mirror
        assert len(_git(s.mirror, "worktree", "list").splitlines()) == 1

        fresh = Ledger(s.ledger_path)
        rows = {row["spec_id"]: row for row in fresh.stack_layers(s.batch_id)}
        for layer in s.layers:
            assert rows[layer["spec_id"]]["pushed_sha"] == layer["head"]

        expected_calls = [
            [
                "gh",
                "pr",
                "view",
                layer["pr_url"],
                "--json",
                "baseRefName",
                "--jq",
                ".baseRefName",
            ]
            for layer in s.layers
        ] + [
            [
                "gh",
                "pr",
                "create",
                "--repo",
                s.slug,
                "--draft",
                "--base",
                top["branch"],
                "--head",
                branch,
                "--title",
                f"saffron batch {s.batch_id}: finishing layer",
                "--body-file",
                str(workdir.parent / "pr-body.md"),
            ]
        ]
        assert gh.calls == expected_calls
        assert str(s.batch_id) in (workdir.parent / "pr-body.md").read_text()

        finish_row = fresh.stack_finish(s.batch_id)
        assert finish_row is not None
        assert finish_row["branch"] == branch
        assert finish_row["head_sha"] == sha
        assert finish_row["pr_url"] == "https://github.com/o/r/pull/200"
        assert fresh.stack_finish(s.batch_id + 1000) is None

        # The literal text, not the symbol, so a change to `PUSHED` cannot
        # move expectation and output together.
        assert PUSHED == "pushed "
        assert lines == [
            f"pushed {sha[:12]} to {branch}, draft pull request "
            "https://github.com/o/r/pull/200"
        ]
        assert lines[0].startswith("pushed ")

    _run(3)
    _run(1)

    # The worktree's removal raises after the push returns, so the pushed
    # line comes first and a second line names the leftover worktree.
    s = _stack(tmp_path / "stack-worktree-raises", 3)
    top = s.layers[-1]
    sha = _finishing_commit(s.mirror, top["head"])
    branch = f"saffron/batch-{s.batch_id}-finish"
    gh = _FakeGh(_bases(s.layers))
    real_remove = git_mirror.remove_worktree

    def _raising_remove(mirror: Path, dest: Path) -> None:
        real_remove(mirror, dest)
        raise git_mirror.GitError("busy")

    workdir = tmp_path / "push-worktree-raises"
    with monkeypatch.context() as m:
        m.setattr(git_mirror, "remove_worktree", _raising_remove)
        lines = publish_finish(
            s.ledger,
            s.batch_id,
            sha,
            mirror=s.mirror,
            url=s.url,
            slug=s.slug,
            verify=lambda sha_arg, base_arg: 0,
            gh=gh,
            workdir=workdir,
        )
    assert lines == [
        f"pushed {sha[:12]} to {branch}, draft pull request "
        "https://github.com/o/r/pull/200",
        f"worktree left at {workdir}: GitError: busy",
    ]
    fresh = Ledger(s.ledger_path)
    row = fresh.stack_finish(s.batch_id)
    assert row is not None
    assert row["branch"] == branch
    assert row["head_sha"] == sha
    assert row["pr_url"] == "https://github.com/o/r/pull/200"

    # `gh` fails to open a pull request, and the fallback `pr view` finds
    # none either, so `open_draft_pr`'s own `PackageError` propagates.
    s = _stack(tmp_path / "stack-gh-fails", 3)
    top = s.layers[-1]
    sha = _finishing_commit(s.mirror, top["head"])
    branch = f"saffron/batch-{s.batch_id}-finish"
    gh = _FakeGh(
        _bases(s.layers),
        create=(1, "", "denied"),
        view_existing=(1, "", "still denied"),
    )
    from saffron.phases.package import PackageError

    with pytest.raises(PackageError):
        publish_finish(
            s.ledger,
            s.batch_id,
            sha,
            mirror=s.mirror,
            url=s.url,
            slug=s.slug,
            verify=lambda sha_arg, base_arg: 0,
            gh=gh,
            workdir=tmp_path / "push-gh-fails",
        )
    assert _refs(s.remote)[f"refs/heads/{branch}"] == sha
    fresh = Ledger(s.ledger_path)
    row = fresh.stack_finish(s.batch_id)
    assert row is not None
    assert row["branch"] == branch
    assert row["head_sha"] == sha
    assert row["pr_url"] is None
    assert len(_git(s.mirror, "worktree", "list").splitlines()) == 1


def test_a_pushed_stack_is_linked_bottom_to_top_with_its_finishing_layer_last(
    tmp_path, monkeypatch
):
    """`link_stack` passes gh-stack every pull request URL, bottom to top,
    with the finishing layer's own URL last, and never a branch name
    (`SA-0170`). A missing or url-less finishing row raises before any
    `gh` call, and a refused link leaves every pull request a draft."""
    from saffron.finish import link_stack

    _isolate_git(tmp_path, monkeypatch)

    def _record(s, *, pr_url: str | None = "https://github.com/o/r/pull/200") -> None:
        top = s.layers[-1]
        kwargs = {} if pr_url is None else {"pr_url": pr_url}
        s.ledger.record_stack_finish(
            s.batch_id,
            branch=f"saffron/batch-{s.batch_id}-finish",
            head_sha=top["head"],
            **kwargs,
        )

    # Three layers: the finishing URL goes last, after each layer's own,
    # bottom to top.
    s = _stack(tmp_path / "stack-3", 3)
    _record(s)
    gh = _FakeGh({})
    lines = link_stack(s.ledger, s.batch_id, mirror=s.mirror, url=s.url, gh=gh)
    assert gh.calls == [
        [
            "gh",
            "stack",
            "link",
            "--base",
            "trunk",
            "https://github.com/o/r/pull/101",
            "https://github.com/o/r/pull/102",
            "https://github.com/o/r/pull/103",
            "https://github.com/o/r/pull/200",
        ]
    ]
    assert lines == ["linked 4 pull requests"]

    # One layer: still the layer's own URL, then the finishing one.
    s = _stack(tmp_path / "stack-1", 1)
    _record(s)
    gh = _FakeGh({})
    lines = link_stack(s.ledger, s.batch_id, mirror=s.mirror, url=s.url, gh=gh)
    assert gh.calls == [
        [
            "gh",
            "stack",
            "link",
            "--base",
            "trunk",
            "https://github.com/o/r/pull/101",
            "https://github.com/o/r/pull/200",
        ]
    ]
    assert lines == ["linked 2 pull requests"]

    # A refused link, `stderr` stripped.
    s = _stack(tmp_path / "stack-fail", 3)
    _record(s)
    gh = _FakeGh({}, link=(1, "", "boom\n"))
    lines = link_stack(s.ledger, s.batch_id, mirror=s.mirror, url=s.url, gh=gh)
    assert gh.calls == [
        [
            "gh",
            "stack",
            "link",
            "--base",
            "trunk",
            "https://github.com/o/r/pull/101",
            "https://github.com/o/r/pull/102",
            "https://github.com/o/r/pull/103",
            "https://github.com/o/r/pull/200",
        ]
    ]
    assert lines == ["gh stack link failed, so every pull request stays a draft: boom"]
    refused_calls = gh.calls

    # gh-stack's measured exit 9 is refused too, so a check of exit 1 alone fails.
    s = _stack(tmp_path / "stack-fail-9", 3)
    _record(s)
    gh = _FakeGh({}, link=(9, "", "not enabled\n"))
    lines = link_stack(s.ledger, s.batch_id, mirror=s.mirror, url=s.url, gh=gh)
    assert gh.calls == refused_calls
    assert lines == [
        "gh stack link failed, so every pull request stays a draft: not enabled"
    ]

    # `gh` could not start.
    s = _stack(tmp_path / "stack-127", 3)
    _record(s)
    gh = _FakeGh({}, link=(127, "", "boom\n"))
    lines = link_stack(s.ledger, s.batch_id, mirror=s.mirror, url=s.url, gh=gh)
    assert gh.calls == refused_calls
    assert lines == [
        "gh could not start, so nothing is linked and every pull request "
        "stays a draft: boom"
    ]

    # No finishing row at all: raises before any `gh` call.
    s = _stack(tmp_path / "stack-norow", 3)
    gh = _FakeGh({})
    with pytest.raises(ValueError, match=str(s.batch_id)):
        link_stack(s.ledger, s.batch_id, mirror=s.mirror, url=s.url, gh=gh)
    assert gh.calls == []

    # A finishing row recorded with no URL: raises the same way.
    s = _stack(tmp_path / "stack-nourl", 3)
    _record(s, pr_url=None)
    gh = _FakeGh({})
    with pytest.raises(ValueError, match=str(s.batch_id)):
        link_stack(s.ledger, s.batch_id, mirror=s.mirror, url=s.url, gh=gh)
    assert gh.calls == []


def test_each_escalation_leaves_the_stack_unpushed(tmp_path, monkeypatch):
    from saffron.cell.runtime import CellRuntimeError
    from saffron.finish import ESCALATE, publish_finish
    from saffron.phases import package as package_phase

    # Pinned once here: every case below checks the literal text instead,
    # so a change to this constant cannot move expectation and output together.
    assert ESCALATE == "escalate: "

    _isolate_git(tmp_path, monkeypatch)

    def _fresh(name: str) -> tuple[SimpleNamespace, str, dict]:
        s = _stack(tmp_path / name, 3)
        top = s.layers[-1]
        sha = _finishing_commit(s.mirror, top["head"])
        return s, sha, top

    def _assert_untouched(
        s: SimpleNamespace, before_remote: dict, before_mirror: dict
    ) -> None:
        assert _refs(s.remote) == before_remote
        assert _refs(s.mirror) == before_mirror
        assert len(_git(s.mirror, "worktree", "list").splitlines()) == 1
        fresh = Ledger(s.ledger_path)
        rows = {row["spec_id"]: row for row in fresh.stack_layers(s.batch_id)}
        for layer in s.layers:
            assert rows[layer["spec_id"]]["pushed_sha"] == layer["head"]
        assert fresh.stack_finish(s.batch_id) is None

    def _run_case(
        name,
        *,
        verify,
        wrong_base_fn=None,
        missing_base_specs=(),
        hand_push_branch=None,
        seed_finish=False,
        expected_prefix_fn,
        expected_pr_view_count,
        expected_line_fn=None,
    ):
        s, sha, top = _fresh(name)
        branch = f"saffron/batch-{s.batch_id}-finish"
        if hand_push_branch is not None:
            _hand_push(s.remote, hand_push_branch, tmp_path / f"{name}-hand")
        if seed_finish:
            _seed_finish_branch(
                s.remote, s.batch_id, top["branch"], tmp_path / f"{name}-seed"
            )
        bases = _bases(s.layers)
        if wrong_base_fn is not None:
            bases.update(wrong_base_fn(s.layers))
        for spec_id in missing_base_specs:
            for layer in s.layers:
                if layer["spec_id"] == spec_id:
                    bases.pop(layer["pr_url"], None)
        gh = _FakeGh(bases)
        before_remote = _refs(s.remote)
        before_mirror = _refs(s.mirror)
        verify_calls: list[tuple[str, str]] = []

        def _verify_wrap(sha_arg: str, base_arg: str) -> int:
            verify_calls.append((sha_arg, base_arg))
            return verify(sha_arg, base_arg)

        lines = publish_finish(
            s.ledger,
            s.batch_id,
            sha,
            mirror=s.mirror,
            url=s.url,
            slug=s.slug,
            verify=_verify_wrap,
            gh=gh,
            workdir=tmp_path / f"{name}-push",
        )
        expected_prefix = expected_prefix_fn(s, branch)
        assert len(lines) == 1
        assert lines[0].startswith("escalate: ")
        assert lines[0].startswith(expected_prefix)
        if expected_line_fn is not None:
            assert lines[0] == expected_line_fn(s, branch)
        assert verify_calls == [(sha, top["head"])]
        assert len(gh.calls) == expected_pr_view_count
        _assert_untouched(s, before_remote, before_mirror)

    _run_case(
        "red",
        verify=lambda sha_arg, base_arg: 2,
        expected_prefix_fn=lambda s, branch: "escalate: red suite, 2 new failure",
        # The exact word, plural at 2: pins the suffix `_new_failures` picks, not
        # the prefix the two counts share.
        expected_line_fn=lambda s, branch: "escalate: red suite, 2 new failures",
        expected_pr_view_count=0,
    )
    _run_case(
        "red-one",
        verify=lambda sha_arg, base_arg: 1,
        expected_prefix_fn=lambda s, branch: "escalate: red suite, 1 new failure",
        expected_line_fn=lambda s, branch: "escalate: red suite, 1 new failure",
        expected_pr_view_count=0,
    )
    _run_case(
        "suite-broke",
        verify=lambda sha_arg, base_arg: (_ for _ in ()).throw(
            package_phase.PackageError("boom")
        ),
        expected_prefix_fn=(
            lambda s, branch: "escalate: the finishing suite did not finish"
        ),
        expected_pr_view_count=0,
    )
    _run_case(
        "cell-broke",
        verify=lambda sha_arg, base_arg: (_ for _ in ()).throw(
            CellRuntimeError("boom")
        ),
        expected_prefix_fn=(
            lambda s, branch: "escalate: the finishing suite did not finish"
        ),
        expected_pr_view_count=0,
    )
    _run_case(
        "red-and-moved",
        verify=lambda sha_arg, base_arg: 2,
        hand_push_branch="saffron/TE-2",
        expected_prefix_fn=lambda s, branch: "escalate: red suite, 2 new failure",
        expected_pr_view_count=0,
    )
    _run_case(
        "bottom-moved",
        verify=lambda sha_arg, base_arg: 0,
        hand_push_branch="saffron/TE-1",
        expected_prefix_fn=lambda s, branch: "escalate: saffron/TE-1 is at",
        expected_pr_view_count=0,
    )
    _run_case(
        "middle-moved",
        verify=lambda sha_arg, base_arg: 0,
        hand_push_branch="saffron/TE-2",
        expected_prefix_fn=lambda s, branch: "escalate: saffron/TE-2 is at",
        expected_pr_view_count=0,
    )
    _run_case(
        "top-moved",
        verify=lambda sha_arg, base_arg: 0,
        hand_push_branch="saffron/TE-3",
        expected_prefix_fn=lambda s, branch: "escalate: saffron/TE-3 is at",
        expected_pr_view_count=0,
    )
    _run_case(
        "bottom-base",
        verify=lambda sha_arg, base_arg: 0,
        wrong_base_fn=lambda layers: {layers[0]["pr_url"]: "saffron/TE-9"},
        expected_prefix_fn=lambda s, branch: (
            "escalate: TE-1's pull request targets saffron/TE-9, not trunk"
        ),
        expected_pr_view_count=1,
    )
    _run_case(
        "middle-base",
        verify=lambda sha_arg, base_arg: 0,
        wrong_base_fn=lambda layers: {layers[1]["pr_url"]: "trunk"},
        expected_prefix_fn=lambda s, branch: (
            "escalate: TE-2's pull request targets trunk, not saffron/TE-1"
        ),
        expected_pr_view_count=2,
    )
    _run_case(
        "top-unread",
        verify=lambda sha_arg, base_arg: 0,
        missing_base_specs=("TE-3",),
        expected_prefix_fn=lambda s, branch: (
            "escalate: TE-3's pull request targets nothing readable, not saffron/TE-2"
        ),
        expected_pr_view_count=3,
    )
    _run_case(
        "finish-exists",
        verify=lambda sha_arg, base_arg: 0,
        seed_finish=True,
        expected_prefix_fn=lambda s, branch: f"escalate: {branch} already exists",
        expected_pr_view_count=3,
    )

    # `push_with_lease` itself fails for a reason that is not the lease, so
    # its own `PackageError` propagates with nothing pushed or recorded.
    s, sha, top = _fresh("push-denied")
    gh = _FakeGh(_bases(s.layers))
    before_remote = _refs(s.remote)
    before_mirror = _refs(s.mirror)
    verify_calls: list[tuple[str, str]] = []

    def _verify(sha_arg: str, base_arg: str) -> int:
        verify_calls.append((sha_arg, base_arg))
        return 0

    with monkeypatch.context() as m:
        m.setattr(
            package_phase,
            "push_with_lease",
            lambda *a, **k: (_ for _ in ()).throw(
                package_phase.PackageError("push failed: denied")
            ),
        )
        with pytest.raises(package_phase.PackageError, match="denied"):
            publish_finish(
                s.ledger,
                s.batch_id,
                sha,
                mirror=s.mirror,
                url=s.url,
                slug=s.slug,
                verify=_verify,
                gh=gh,
                workdir=tmp_path / "push-denied-push",
            )
    assert verify_calls == [(sha, top["head"])]
    assert len(gh.calls) == 3
    _assert_untouched(s, before_remote, before_mirror)


def _file_diff(path: str, added: list[str]) -> str:
    hunk = "\n".join(f"+{line}" for line in added)
    return (
        f"diff --git a/{path} b/{path}\n"
        "index 1111111..2222222 100644\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        f"@@ -1,0 +1,{len(added)} @@\n"
        f"{hunk}\n"
    )


def test_the_finishing_suite_passes_the_spec_directory_and_fails_every_other_path():
    from saffron.finish import FINISH_TOUCHES, finish_suite
    from saffron.gates.suite import GateSuite
    from saffron.repos.policy import load_policy
    from tests.test_suite import _Tree

    repo_root = Path(__file__).resolve().parents[1]
    policy, _policy_sha = load_policy(repo_root)
    assert policy.protected
    assert policy.integrity.suppressions

    spec, finishing_policy = finish_suite(policy)
    assert spec.type == "chore"
    assert spec.touches == list(FINISH_TOUCHES)
    assert spec.forbidden == []
    assert spec.acceptance == []

    expected = policy.model_dump()
    expected["protected"] = []
    expected["integrity"]["suppressions"] = []
    assert finishing_policy.model_dump() == expected

    token = policy.integrity.suppressions[0]
    suite = GateSuite(gates={}, spec=spec, policy=finishing_policy, diff_base="base")
    baseline = suite.baseline(_Tree())

    def _comparison(extra: tuple[str, list[str]] | None):
        files = [
            (".saffron/specs/example.md", [f"See {token} for its own context."]),
            (".saffron/specs/done/retired.md", ["Retired."]),
        ]
        if extra is not None:
            files.append(extra)
        changed = [path for path, _ in files]
        diff = "".join(_file_diff(path, lines) for path, lines in files)
        return suite.against(_Tree(changed=changed, patch=diff), baseline)

    base_comparison = _comparison(None)
    assert base_comparison.aborted == ()
    assert base_comparison.drift == ()
    assert base_comparison.new_failures == ()

    for extra_path in (
        ".saffron/policy.yaml",
        ".saffron/specs/sub/x.md",
        ".saffron/specs/x.txt",
        "CLAUDE.md",
        "docs/adr/0008-x.md",
    ):
        comparison = _comparison((extra_path, ["an extra, undeclared line"]))
        assert comparison.aborted == ()
        assert comparison.drift == ()
        files_hit = {nf.failure.file for nf in comparison.new_failures}
        assert files_hit == {extra_path}
        codes_hit = {nf.failure.code for nf in comparison.new_failures}
        assert "out-of-scope" in codes_hit
