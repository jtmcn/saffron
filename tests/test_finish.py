"""The stack batch's finishing layer commit (ADR 7, SA-0171)."""

from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from saffron.ledger import Ledger


def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def _spec_md(spec_id: str, title: str) -> str:
    return f"---\nid: {spec_id}\ntitle: {title}\ntype: chore\n---\nBody.\n"


@pytest.fixture
def stack(tmp_path, monkeypatch):
    """The one arrangement both `commit_finish` witnesses drive: an origin
    repo on three stacked branches, its bare mirror, and a ledger carrying
    two batches' tasks, layers and texts."""
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

    def _assert_refused(task_id: int, is_unrun: bool, i: int, **overrides) -> None:
        with monkeypatch.context() as m:
            m.setattr(stack.ledger, "spec_text", _bad_row(task_id, **overrides))
            calls: list[tuple] = []
            m.setattr(
                git_mirror,
                "add_worktree",
                lambda mirror, sha, dest: calls.append((mirror, sha, dest)),
            )
            before = _git(stack.mirror, "count-objects", "-v")
            with pytest.raises(ValueError):
                commit_finish(
                    stack.ledger,
                    stack.batch_b,
                    [task_id] if is_unrun else [],
                    mirror=stack.mirror,
                    workdir=tmp_path / f"bad-{task_id}-{i}",
                )
            assert calls == []
            assert _git(stack.mirror, "count-objects", "-v") == before

    for task_id, is_unrun in [
        (stack.tasks["TE-7"], False),
        (stack.tasks["TE-21"], True),
    ]:
        for i, bad_path in enumerate(bad_paths):
            _assert_refused(task_id, is_unrun, i, path=bad_path)
        _assert_refused(task_id, is_unrun, len(bad_paths), spec_sha="0" * 64)
