"""Witnesses for `consumes:` (SA-0135).

Covers the field on `Spec` and the fixture spec that declares it. Covers
`run_task`'s pre-cell refusal for an entry that does not resolve at the
task's tree base. Also covers `saffron cell` and a batch, the two callers
that must survive `run_task`'s widened return type.

`Refused` and `unresolved_consumes` are imported inside each test body that
needs them, never here: a module-scope import of a name this spec adds would
fail collection with the source reverted, and `revert` reads that as `skip`.
"""

from __future__ import annotations

import json
import locale
import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from saffron import cli
from saffron import task as task_module
from saffron.cell.session import CellOutcome
from saffron.intake import Spec, SpecError, discover_specs, load_spec, parse_spec
from saffron.ledger import Ledger
from saffron.phases import package as package_phase
from saffron.repos.mirror import GitError, ensure_mirror
from saffron.task import PinnedBase, ResolvedCeilings
from tests.test_batch import FakeRunner, _candidate, _outcome, _ready, _spend
from tests.test_cli import _local_origin, _namespace
from tests.test_mirror import _plain_repo, git

_CEILINGS = ResolvedCeilings(
    budget_usd=12.0,
    max_attempts=4,
    max_turns=60,
    budget_source="default",
    attempts_source="default",
    turns_source="default",
)

_NO_PUSH = package_phase.PushResult(pushed=False, note="no commits, nothing to push")


def _consumes_spec(spec_id: str, consumes: list[str], *, depends_on=("SY-0",)) -> Spec:
    return Spec(
        id=spec_id,
        title="t",
        type="feature",
        depends_on=list(depends_on),
        consumes=consumes,
    )


def _frontmatter(*, depends_yaml: str = "", consumes_yaml: str = "") -> str:
    return (
        "---\n"
        "id: SY-1\n"
        "title: One\n"
        "type: feature\n"
        f"{depends_yaml}{consumes_yaml}"
        "---\n\n"
        "## Acceptance criteria\n- [ ] it works\n"
    )


def _entry_yaml(*entries: str) -> str:
    """A `consumes:` block, each entry quoted so it reads as a scalar rather
    than a YAML mapping or a parse error (measured 2026-09-23)."""
    lines = "".join(f"  - {json.dumps(entry)}\n" for entry in entries)
    return f"consumes:\n{lines}"


def _load_ok(entry: str) -> None:
    text = _frontmatter(
        depends_yaml="depends_on: [SA-0001]\n", consumes_yaml=_entry_yaml(entry)
    )
    assert parse_spec(text).consumes == [entry]


def _load_refused(entry: str) -> None:
    text = _frontmatter(
        depends_yaml="depends_on: [SA-0001]\n", consumes_yaml=_entry_yaml(entry)
    )
    with pytest.raises(SpecError) as excinfo:
        parse_spec(text)
    cause = excinfo.value.__cause__
    assert isinstance(cause, ValidationError)
    msg = cause.errors()[0]["msg"]
    assert repr(entry) in msg


def test_a_spec_declares_what_it_consumes_and_needs_a_parent_to_consume_from(
    tmp_path,
):
    declared = _frontmatter(
        depends_yaml="depends_on: [SY-0]\n",
        consumes_yaml=(
            "consumes:\n"
            "  - saffron/task.py\n"
            "  - saffron/task.py:run_task\n"
            "  - lib.rs:Foo::bar\n"
        ),
    )
    spec = parse_spec(declared)
    assert spec.consumes == [
        "saffron/task.py",
        "saffron/task.py:run_task",
        "lib.rs:Foo::bar",
    ]

    for consumes_yaml in ("", "consumes:\n", "consumes: []\n"):
        empty = parse_spec(_frontmatter(consumes_yaml=consumes_yaml))
        assert empty.consumes == []

    for depends_yaml in ("", "depends_on: []\n"):
        text = _frontmatter(
            depends_yaml=depends_yaml, consumes_yaml="consumes: [a.py]\n"
        )
        with pytest.raises(SpecError):
            parse_spec(text)

    orphaned = _frontmatter(consumes_yaml="consumes: [a.py]\n")
    spec_path = tmp_path / "SY-1.md"
    spec_path.write_text(orphaned)
    with pytest.raises(SpecError):
        load_spec(spec_path)

    directory = tmp_path / "specs"
    directory.mkdir()
    (directory / "SY-1.md").write_text(orphaned)
    specs, failures = discover_specs(directory)
    assert specs == []
    assert len(failures) == 1
    assert failures[0].path == directory / "SY-1.md"


def test_the_fixture_spec_declares_what_it_consumes_and_loads():
    path = Path("tests/fixtures/consumes/FX-0001-a-child-names-what-it-consumes.md")
    spec, _sha = load_spec(path)
    assert spec.depends_on == ["FX-0000"]
    assert spec.consumes == ["saffron/task.py", "saffron/task.py:run_task"]


def test_run_task_refuses_an_unresolved_consumed_entry_before_the_cell(
    tmp_path, monkeypatch, capsys
):
    from saffron.task import Refused

    repo = _plain_repo(tmp_path, "consumes-3")
    (repo / "code.py").write_text("run_task\n")
    (repo / "comment.py").write_text("# helper\n")
    (repo / "doc.py").write_text('"""Widget"""\n')
    (repo / "weird:name.py").write_text("anything\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "consumes-3")
    sha = git(repo, "rev-parse", "HEAD")
    mirror = ensure_mirror(repo, tmp_path / "consumes-3.git")

    calls: list[object] = []
    monkeypatch.setattr(
        task_module,
        "run_one_cell",
        lambda spec, **k: (
            calls.append(spec)
            or CellOutcome(
                state="EXHAUSTED",
                task_id=1,
                run_id=1,
                task_dir=Path("/tmp/nonexistent"),
            )
        ),
    )
    monkeypatch.setattr(package_phase, "push_unpackaged_work", lambda *a, **k: _NO_PUSH)

    ledger = Ledger(tmp_path / "l.db")
    out_dir = tmp_path / "out"
    spec = _consumes_spec(
        "SY-1",
        [
            "gone_b.py",
            "code.py:run_task",
            "comment.py:helper",
            "doc.py:Widget",
            "weird:name.py",
            "gone_a.py:run_task",
        ],
    )

    result = task_module.run_task(
        spec,
        "s" * 40,
        ceilings=_CEILINGS,
        base=PinnedBase(mirror=mirror, url="https://github.com/o/r.git", base_sha=sha),
        repo_id=None,
        repo=repo,
        ledger=ledger,
        out_dir=out_dir,
        token=None,
    )

    assert isinstance(result, Refused)
    assert calls == []
    assert ledger._db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0
    assert ledger._db.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0

    expected_reason = (
        f"{sha[:12]} does not resolve gone_b.py, weird:name.py, gone_a.py:run_task"
    )
    assert result.reason == expected_reason
    lines = capsys.readouterr().out.splitlines()
    refused_lines = [line for line in lines if "refused" in line]
    assert refused_lines == [f"{spec.id:<10} refused  {expected_reason}"]

    second = _consumes_spec(
        "SY-2", ["code.py:run_task", "comment.py:helper", "doc.py:Widget"]
    )
    result2 = task_module.run_task(
        second,
        "s" * 40,
        ceilings=_CEILINGS,
        base=PinnedBase(mirror=mirror, url="https://github.com/o/r.git", base_sha=sha),
        repo_id=None,
        repo=repo,
        ledger=ledger,
        out_dir=out_dir,
        token=None,
    )
    assert not isinstance(result2, Refused)
    assert len(calls) == 1


def test_consumed_entries_resolve_at_the_tasks_tree_base(tmp_path, monkeypatch):
    from saffron.task import Refused

    repo = _plain_repo(tmp_path, "history")
    (repo / "old.py").write_text("old_name\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "C1")
    c1 = git(repo, "rev-parse", "HEAD")

    (repo / "head.py").write_text("head_name\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "C2")

    git(repo, "checkout", "-q", "-b", "saffron/SY-0", c1)
    (repo / "old.py").unlink()
    (repo / "new.py").write_text("new_name\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "P")
    p = git(repo, "rev-parse", "HEAD")

    git(repo, "checkout", "-q", "main")
    (repo / "wc.py").write_text("wc_name\n")

    mirror = ensure_mirror(repo, tmp_path / "history.git")

    ledger = Ledger(tmp_path / "l.db")
    out_dir = tmp_path / "out"
    calls: list[object] = []
    monkeypatch.setattr(
        task_module,
        "run_one_cell",
        lambda spec, **k: (
            calls.append(spec)
            or CellOutcome(
                state="EXHAUSTED",
                task_id=1,
                run_id=1,
                task_dir=Path("/tmp/nonexistent"),
            )
        ),
    )
    monkeypatch.setattr(package_phase, "push_unpackaged_work", lambda *a, **k: _NO_PUSH)

    def _run(consumes: list[str]) -> CellOutcome | Refused:
        return task_module.run_task(
            _consumes_spec("SY-1", consumes),
            "s" * 40,
            ceilings=_CEILINGS,
            base=PinnedBase(
                mirror=mirror, url="https://github.com/o/r.git", base_sha=c1
            ),
            repo_id=None,
            repo=repo,
            ledger=ledger,
            out_dir=out_dir,
            token=None,
        )

    # Unstacked at C1: only old.py:old_name resolves.
    unstacked = _run(
        ["old.py:old_name", "head.py:head_name", "wc.py:wc_name", "new.py:new_name"]
    )
    assert isinstance(unstacked, Refused)
    assert unstacked.reason.startswith(c1[:12])
    assert "head.py:head_name" in unstacked.reason
    assert "wc.py:wc_name" in unstacked.reason
    assert "new.py:new_name" in unstacked.reason
    assert "old.py:old_name" not in unstacked.reason
    assert calls == []

    # Stacked on P (base_sha stays C1): new.py:new_name resolves, old.py:old_name does not.
    monkeypatch.setattr(
        task_module, "_resolve_stacked_on", lambda *a, **k: (p, "saffron/SY-0")
    )
    stacked = _run(["new.py:new_name", "old.py:old_name"])
    assert isinstance(stacked, Refused)
    assert stacked.reason.startswith(p[:12])
    assert "old.py:old_name" in stacked.reason
    assert "new.py:new_name" not in stacked.reason
    assert calls == []

    resolved = _run(["new.py:new_name"])
    assert not isinstance(resolved, Refused)
    assert len(calls) == 1


def test_a_tree_base_the_mirror_lacks_is_an_error_and_not_a_refusal(
    tmp_path, monkeypatch, capsys
):
    repo = _plain_repo(tmp_path, "bad-sha")
    (repo / "a.py").write_text("x\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    mirror = ensure_mirror(repo, tmp_path / "bad-sha.git")

    calls: list[object] = []
    monkeypatch.setattr(task_module, "run_one_cell", lambda *a, **k: calls.append(1))

    ledger = Ledger(tmp_path / "l.db")
    spec = _consumes_spec("SY-1", ["a.py"])

    with pytest.raises(GitError):
        task_module.run_task(
            spec,
            "s" * 40,
            ceilings=_CEILINGS,
            base=PinnedBase(
                mirror=mirror, url="https://github.com/o/r.git", base_sha="0" * 40
            ),
            repo_id=None,
            repo=repo,
            ledger=ledger,
            out_dir=tmp_path / "out",
            token=None,
        )

    assert calls == []
    assert "refused" not in capsys.readouterr().out


def test_a_spec_that_consumes_nothing_never_calls_the_reader(tmp_path, monkeypatch):
    """No `consumes` means no reader call, not a call with an empty list."""

    class _Stop(Exception):
        pass

    def _stop(*_a, **_k):
        raise _Stop

    seen: list[object] = []
    monkeypatch.setattr(task_module, "run_one_cell", _stop)
    monkeypatch.setattr(
        task_module, "unresolved_consumes", lambda *a, **k: seen.append(a) or []
    )
    with pytest.raises(_Stop):
        task_module.run_task(
            _consumes_spec("SY-2", []),
            "s" * 40,
            ceilings=_CEILINGS,
            base=PinnedBase(
                mirror=tmp_path / "none.git",
                url="https://github.com/o/r.git",
                base_sha="0" * 40,
            ),
            repo_id=None,
            repo=tmp_path,
            ledger=Ledger(tmp_path / "l.db"),
            out_dir=tmp_path / "out",
            token=None,
        )
    assert seen == []


def test_saffron_cell_exits_1_on_a_consumes_refusal(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-test")
    repo = _local_origin(tmp_path)
    args = _namespace(repo, tmp_path)
    args.spec = tmp_path / "SY-1.md"
    args.spec.write_text(
        "---\nid: SY-1\ntitle: One\ntype: feature\ntouches: ['src/**']\n"
        "depends_on: [SY-0]\nconsumes: [missing.py]\n---\n\n"
        "## Acceptance criteria\n- [ ] it works\n"
    )
    monkeypatch.setattr("saffron.phases.package.github_slug", lambda _url: "o/r")
    started = False

    def _started(*_a, **_k):
        nonlocal started
        started = True
        raise SystemExit(0)

    monkeypatch.setattr("saffron.task.run_one_cell", _started)
    ledger = Ledger(tmp_path / "l.db")

    result = cli._run_cell(args, ledger, tmp_path / "out")

    assert result == 1
    assert not started
    out = capsys.readouterr().out
    assert out.count("refused") == 1
    count = ledger._db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    assert count == 0
    ledger.close()


@pytest.fixture
def ledger(tmp_path):
    made = Ledger(tmp_path / "ledger.db")
    yield made
    made.close()


@pytest.fixture
def repo_id(ledger):
    return ledger.upsert_repo("thermal-edge", "/o", "/m.git", policy_sha="p" * 64)


def test_a_batch_steps_over_a_refused_task(ledger, repo_id):
    from saffron.batch import run_batch
    from saffron.task import Refused

    drained = [_candidate("TE-1"), _candidate("TE-2"), _candidate("TE-3")]
    third_run = _spend(ledger, repo_id, 1.0)
    drained_runner = FakeRunner(
        [
            Refused(reason="TE-1 does not resolve x.py"),
            Refused(reason="TE-2 does not resolve y.py"),
            _outcome(state="READY_FOR_REVIEW", run_id=third_run),
        ]
    )
    rescans = {"n": 0}

    def _rescan_all():
        rescans["n"] += 1
        return drained

    reason = run_batch(
        drained,
        ledger,
        budget_usd=100.0,
        until=None,
        runner=drained_runner,
        rescan=_rescan_all,
        readiness_check=_ready,
    )

    assert reason == "DRAINED"
    assert drained_runner.calls == drained
    assert rescans["n"] == 3

    infra = [
        _candidate("TE-4"),
        _candidate("TE-5"),
        _candidate("TE-6"),
        _candidate("TE-7"),
    ]
    run_one = _spend(ledger, repo_id, 1.0)
    run_two = _spend(ledger, repo_id, 1.0)
    infra_runner = FakeRunner(
        [
            _outcome(state="GATE_ERROR", run_id=run_one),
            Refused(reason="TE-5 does not resolve z.py"),
            _outcome(state="GATE_ERROR", run_id=run_two),
        ]
    )

    reason2 = run_batch(
        infra,
        ledger,
        budget_usd=100.0,
        until=None,
        runner=infra_runner,
        rescan=lambda: infra,
        readiness_check=_ready,
    )

    assert reason2 == "INFRASTRUCTURE"
    assert infra_runner.calls == infra[:3]


# --------------------------------------------------------- shapes, at load


def test_an_empty_consumed_entry_is_refused_at_load():
    _load_refused("")
    _load_ok("a")


def test_a_consumed_entry_with_an_empty_path_is_refused_at_load():
    _load_refused(":run_task")
    _load_ok("a.py:run_task")


def test_a_consumed_entry_with_an_empty_name_is_refused_at_load():
    _load_refused("a.py:")
    _load_ok("a.py:x")


def test_an_absolute_consumed_path_is_refused_at_load():
    for entry in ("/a.py", "/a.py:run_task"):
        _load_refused(entry)
    for entry in ("a.py", "a.py:run_task"):
        _load_ok(entry)


def test_a_bare_dot_consumed_path_is_refused_at_load():
    for entry in (".", ".:run_task"):
        _load_refused(entry)
    for entry in (".github", ".github:run_task"):
        _load_ok(entry)


def test_a_consumed_path_with_a_dot_segment_is_refused_at_load():
    for entry in (
        "pkg/./mod.py",
        "pkg/./mod.py:run_task",
        "pkg/.",
        "pkg/.:run_task",
        "./mod.py",
        "./mod.py:run_task",
    ):
        _load_refused(entry)
    for entry in (
        "pkg/.hidden/mod.py",
        "pkg/.hidden/mod.py:run_task",
        "pkg/v1./mod.py",
        "pkg/v1./mod.py:run_task",
    ):
        _load_ok(entry)


def test_a_consumed_path_with_a_dot_dot_segment_is_refused_at_load():
    for entry in (
        "pkg/../mod.py",
        "pkg/../mod.py:run_task",
        "pkg/..",
        "pkg/..:run_task",
        "../mod.py",
        "../mod.py:run_task",
        "..",
        "..:run_task",
    ):
        _load_refused(entry)
    for entry in (
        "pkg/..hidden/mod.py",
        "pkg/..hidden/mod.py:run_task",
        "pkg/v1../mod.py",
        "pkg/v1../mod.py:run_task",
    ):
        _load_ok(entry)


def test_a_consumed_path_with_an_empty_segment_is_refused_at_load():
    for entry in ("pkg//mod.py", "pkg//mod.py:run_task"):
        _load_refused(entry)
    for entry in ("pkg/mod.py", "pkg/mod.py:run_task"):
        _load_ok(entry)


def test_a_consumed_path_ending_in_a_slash_is_refused_at_load():
    for entry in ("pkg/", "pkg/:run_task", "pkg/:Foo::bar"):
        _load_refused(entry)
    for entry in ("pkg", "pkg:run_task", "a.py:Foo::bar"):
        _load_ok(entry)


# --------------------------------------------------------- unreadable entries


def test_an_unreadable_consumed_entry_refuses_the_task_and_names_it(
    tmp_path, monkeypatch
):
    from saffron.repos.mirror import UnreadablePath, unresolved_consumes
    from saffron.task import Refused

    repo = _plain_repo(tmp_path, "unreadable")
    (repo / "docs").mkdir()
    (repo / "docs" / "a.md").write_text("doc\n")
    (repo / "real.py").write_text("run_task\n")
    os.symlink("real.py", repo / "link.md")
    os.symlink("link.md", repo / "hop.md")
    os.symlink("docs", repo / "dir.md")
    os.symlink("missing.md", repo / "gone.md")
    os.symlink("../outside", repo / "out.md")
    (repo / "bytes.py").write_bytes(b"\xff\xfe")
    os.symlink("bytes.py", repo / "bytes_link.py")

    git(repo, "add", "-A")
    # Staged right before the commit: a later `add -A` would remove it again,
    # since nothing exists at `sub` in the worktree (git 2.54.0, 2026-09-24).
    git(repo, "update-index", "--add", "--cacheinfo", f"160000,{'1' * 40},sub")
    git(repo, "commit", "-qm", "unreadable entries")
    sha = git(repo, "rev-parse", "HEAD")
    mirror = ensure_mirror(repo, tmp_path / "unreadable.git")

    entries = [
        "sub:x",
        "out.md:x",
        "gone.md:x",
        "absent.py:x",
        "dir.md:x",
        "hop.md:x",
        "bytes.py:x",
        "bytes_link.py:x",
        "real.py:run_task",
    ]

    for entry in ("sub:x", "out.md:x", "gone.md:x", "dir.md:x", "hop.md:x"):
        with pytest.raises(UnreadablePath):
            unresolved_consumes(mirror, sha, [entry])

    try:
        b"\xff\xfe".decode(locale.getpreferredencoding(False))
        decodes_the_bytes = True
    except (UnicodeDecodeError, LookupError):
        decodes_the_bytes = False
    if not decodes_the_bytes:
        for entry in ("bytes.py:x", "bytes_link.py:x"):
            with pytest.raises(UnicodeDecodeError):
                unresolved_consumes(mirror, sha, [entry])

    assert unresolved_consumes(mirror, sha, ["absent.py:x"]) == ["absent.py:x"]

    calls: list[object] = []
    monkeypatch.setattr(
        task_module, "run_one_cell", lambda spec, **k: calls.append(spec)
    )
    monkeypatch.setattr(package_phase, "push_unpackaged_work", lambda *a, **k: _NO_PUSH)

    ledger = Ledger(tmp_path / "l.db")
    spec = _consumes_spec("SY-1", entries)
    result = task_module.run_task(
        spec,
        "s" * 40,
        ceilings=_CEILINGS,
        base=PinnedBase(mirror=mirror, url="https://github.com/o/r.git", base_sha=sha),
        repo_id=None,
        repo=repo,
        ledger=ledger,
        out_dir=tmp_path / "out",
        token=None,
    )
    assert isinstance(result, Refused)
    assert calls == []
    expected = ", ".join(entries[:-1])
    assert result.reason == f"{sha[:12]} does not resolve {expected}"

    blob = git(repo, "rev-parse", f"{sha}:real.py")
    loose = mirror / "objects" / blob[:2] / blob[2:]
    assert loose.exists()
    loose.unlink()

    only_real = _consumes_spec("SY-2", ["real.py:run_task"])
    with pytest.raises(GitError):
        task_module.run_task(
            only_real,
            "s" * 40,
            ceilings=_CEILINGS,
            base=PinnedBase(
                mirror=mirror, url="https://github.com/o/r.git", base_sha=sha
            ),
            repo_id=None,
            repo=repo,
            ledger=ledger,
            out_dir=tmp_path / "out",
            token=None,
        )
    assert calls == []


def test_has_commit_answers_whether_the_mirror_holds_a_commit(tmp_path):
    from saffron.repos.mirror import has_commit

    repo = _plain_repo(tmp_path, "has-commit")
    (repo / "a.py").write_text("x\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "first")
    first = git(repo, "rev-parse", "HEAD")
    tree = git(repo, "rev-parse", f"{first}^{{tree}}")

    git(repo, "checkout", "-qb", "other", first)
    (repo / "b.py").write_text("y\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "second")
    second = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", "main")

    mirror = ensure_mirror(repo, tmp_path / "has-commit.git")

    assert has_commit(mirror, first) is True
    assert has_commit(mirror, second) is True
    assert has_commit(mirror, "0" * 40) is False
    assert has_commit(mirror, tree) is False
