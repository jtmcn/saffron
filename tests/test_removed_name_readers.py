"""Witnesses for the pre-cell `removes` refusal (backlog item b-1c59c3).

Covers `removed_name_readers` in `saffron/repos/mirror.py` and `run_task`'s
use of it, right beside the `consumes` refusal, before any cell starts.

`removed_name_readers` is imported inside each test body that needs it,
never here: a module-scope import of a name this spec adds would fail
collection with the source reverted, and `revert` reads that as `skip`.
"""

from __future__ import annotations

import locale
import os
from pathlib import Path

import pytest

from saffron import task as task_module
from saffron.cell.session import CellOutcome
from saffron.intake import Spec
from saffron.ledger import Ledger
from saffron.phases import package as package_phase
from saffron.repos.mirror import GitError, ensure_mirror
from saffron.task import PinnedBase, Refused
from tests.test_consumes import _CEILINGS, _NO_PUSH
from tests.test_mirror import _plain_repo, git

_undecodable_fails_here = False
try:
    b"\xff\xfe".decode(locale.getpreferredencoding(False))
except (UnicodeDecodeError, LookupError):
    _undecodable_fails_here = True


def _removes_spec(spec_id: str, removes: list[str], touches: list[str]) -> Spec:
    return Spec(id=spec_id, title="t", type="feature", removes=removes, touches=touches)


def _commit(repo: Path, message: str) -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", message)
    return git(repo, "rev-parse", "HEAD")


# --------------------------------------------------------- the mirror function


def test_the_readers_of_a_removed_entry_are_the_files_holding_its_subject_as_a_whole_word(
    tmp_path,
):
    from saffron.repos.mirror import removed_name_readers

    repo = _plain_repo(tmp_path, "readers")
    (repo / "dir").mkdir()

    # Entry 1 (`path:name`): subject OLD_NAME, defined in lib.py.
    (repo / "lib.py").write_text("OLD_NAME\n")
    # An import, an attribute read, a subject starting a file with no
    # trailing newline, and a Markdown reader.
    (repo / "importer.py").write_text("from lib import OLD_NAME\n")
    (repo / "obj.py").write_text("thing.OLD_NAME\n")
    (repo / "startfile.py").write_text("OLD_NAME")
    (repo / "notes.md").write_text("mentions OLD_NAME here\n")
    # Three substring decoys beside one genuine hit, all case sensitive.
    (repo / "decoy.py").write_text(
        "OLD_NAME_V2 and NOOLD_NAME and old_name, none of which read it\n"
    )
    (repo / "real.py").write_text("uses OLD_NAME properly\n")

    # Entry 2 (bare path): subject is the whole path "const.py".
    (repo / "const.py").write_text("# const.py defines it\n")
    (repo / "other.py").write_text("load from const.py\n")
    # Two near misses: last dot made an underscore, and a letter after the
    # extension.
    (repo / "miss1.py").write_text("const_py is not it\n")
    (repo / "miss2.py").write_text("const.pyc is similar\n")

    # An entry no file reads.
    (repo / "ghost_marker.py").write_text("nothing names it\n")

    # A file that does not decode, beside the subject.
    (repo / "weird.py").write_bytes(b"OLD_NAME\xff\xfe")

    sha = _commit(repo, "readers")
    mirror = ensure_mirror(repo, tmp_path / "readers.git")

    pairs = removed_name_readers(
        mirror, sha, ["lib.py:OLD_NAME", "const.py", "ghost.py"]
    )

    old_name_pairs = [p for p in pairs if p[1] == "lib.py:OLD_NAME"]
    const_pairs = [p for p in pairs if p[1] == "const.py"]
    ghost_pairs = [p for p in pairs if p[1] == "ghost.py"]

    assert {path for path, _ in old_name_pairs} == {
        "importer.py",
        "notes.md",
        "obj.py",
        "real.py",
        "startfile.py",
        "weird.py",
    }
    assert {path for path, _ in const_pairs} == {"other.py"}
    assert ghost_pairs == []

    # lib.py and const.py never read their own entry.
    assert "lib.py" not in {path for path, _ in old_name_pairs}
    assert "const.py" not in {path for path, _ in const_pairs}

    # Entry order, then the path order git lists.
    assert [entry for _, entry in pairs[: len(old_name_pairs)]] == [
        "lib.py:OLD_NAME"
    ] * len(old_name_pairs)
    paths_in_order = [path for path, entry in pairs if entry == "lib.py:OLD_NAME"]
    assert paths_in_order == sorted(paths_in_order)

    with pytest.raises(GitError):
        removed_name_readers(mirror, "0" * 40, ["lib.py:OLD_NAME"])


# --------------------------------------------------------- run_task's refusal


def test_run_task_refuses_a_removed_name_read_outside_touches_before_the_cell(
    tmp_path, monkeypatch, capsys
):
    repo = _plain_repo(tmp_path, "scoped")

    (repo / ".saffron").mkdir()
    (repo / ".saffron" / "policy.yaml").write_text(
        "protected:\n  - secrets/**\n  - gen/*.txt\n"
    )
    (repo / ".saffron" / "specs").mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "nested").mkdir()
    (repo / "docs").mkdir()
    (repo / "docs" / "nested").mkdir()
    (repo / "secrets").mkdir()
    (repo / "secrets" / "sub").mkdir()
    (repo / "tests").mkdir()
    (repo / "tests" / "sub").mkdir()
    (repo / "gen").mkdir()
    (repo / "gen" / "sub").mkdir()

    (repo / "lib.py").write_text("OLD_NAME\n")
    (repo / "away.py").write_text("mentions away.py somewhere\n")

    (repo / "src" / "allowed.py").write_text("sees OLD_NAME here\n")
    (repo / "src" / "nested" / "extra.py").write_text("sees OLD_NAME here\n")
    (repo / "top.md").write_text("OLD_NAME mentioned\n")
    (repo / "docs" / "nested" / "readme.md").write_text("OLD_NAME mentioned\n")
    (repo / ".saffron" / "specs" / "notes.txt").write_text("OLD_NAME mentioned\n")
    (repo / "secrets" / "sub" / "config.py").write_text("OLD_NAME mentioned\n")
    (repo / "tests" / "sub" / "file.txt").write_text("OLD_NAME mentioned\n")
    (repo / "gen" / "sub" / "file.txt").write_text("calls away.py here\n")

    sha = _commit(repo, "scoped")
    mirror = ensure_mirror(repo, tmp_path / "scoped.git")

    def _cell_must_not_start(*_a, **_k):
        raise AssertionError("cell started")

    monkeypatch.setattr(task_module, "run_one_cell", _cell_must_not_start)
    monkeypatch.setattr(package_phase, "push_unpackaged_work", lambda *a, **k: _NO_PUSH)

    ledger = Ledger(tmp_path / "l.db")
    touches = ["src/allowed.py", "src/**", "tests/*.txt"]
    spec = _removes_spec("SY-1", ["lib.py:OLD_NAME", "away.py"], touches)

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
    expected = (
        f"{sha[:12]} holds readers outside touches: "
        "tests/sub/file.txt reads OLD_NAME, gen/sub/file.txt reads away.py"
    )
    assert result.reason == expected
    assert ledger._db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0
    assert ledger._db.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0
    lines = capsys.readouterr().out.splitlines()
    refused_lines = [line for line in lines if "refused" in line]
    assert refused_lines == [f"{spec.id:<10} refused  {expected}"]

    started: list[object] = []
    monkeypatch.setattr(
        task_module,
        "run_one_cell",
        lambda spec, **k: (
            started.append(spec)
            or CellOutcome(
                state="EXHAUSTED",
                task_id=1,
                run_id=1,
                task_dir=Path("/tmp/nonexistent"),
            )
        ),
    )
    spec2 = _removes_spec(
        "SY-2",
        ["lib.py:OLD_NAME", "away.py"],
        touches + ["tests/sub/file.txt", "gen/sub/file.txt"],
    )
    result2 = task_module.run_task(
        spec2,
        "s" * 40,
        ceilings=_CEILINGS,
        base=PinnedBase(mirror=mirror, url="https://github.com/o/r.git", base_sha=sha),
        repo_id=None,
        repo=repo,
        ledger=ledger,
        out_dir=tmp_path / "out",
        token=None,
    )
    assert not isinstance(result2, Refused)
    assert len(started) == 1


# --------------------------------------------------------- tree base + policy


def test_readers_are_read_at_the_tasks_tree_base_with_its_own_policy(
    tmp_path, monkeypatch
):
    repo = _plain_repo(tmp_path, "tree-base")

    (repo / "protected_dir").mkdir()
    (repo / ".saffron").mkdir()
    (repo / "old.py").write_text("OLD_NAME\n")
    (repo / "normal_reader.py").write_text("reads OLD_NAME\n")
    (repo / "protected_dir" / "reader1.py").write_text("reads OLD_NAME\n")
    (repo / ".saffron" / "policy.yaml").write_text("protected:\n  - protected_dir/**\n")
    c1 = _commit(repo, "C1")

    (repo / "head_reader.py").write_text("reads OLD_NAME\n")
    _commit(repo, "C2")

    (repo / "wc_reader.py").write_text("reads OLD_NAME\n")  # uncommitted

    git(repo, "checkout", "-q", "-b", "saffron/SY-0", c1)
    (repo / "normal_reader.py").unlink()
    (repo / "parent_new_reader.py").write_text("reads OLD_NAME\n")
    (repo / ".saffron" / "policy.yaml").write_text(
        "protected:\n  - parent_protected/**\n"
    )
    (repo / "parent_protected").mkdir()
    (repo / "parent_protected" / "reader2.py").write_text("reads OLD_NAME\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "P")
    p = git(repo, "rev-parse", "HEAD")

    git(repo, "checkout", "-q", "main")
    mirror = ensure_mirror(repo, tmp_path / "tree-base.git")

    monkeypatch.setattr(package_phase, "push_unpackaged_work", lambda *a, **k: _NO_PUSH)
    monkeypatch.setattr(
        task_module,
        "run_one_cell",
        lambda spec, **k: CellOutcome(
            state="EXHAUSTED", task_id=1, run_id=1, task_dir=Path("/x")
        ),
    )

    def _run(base_sha: str, count: int):
        ledger = Ledger(tmp_path / f"l-{count}.db")
        spec = _removes_spec("SY-1", ["old.py:OLD_NAME"], ["allowed.py"])
        return task_module.run_task(
            spec,
            "s" * 40,
            ceilings=_CEILINGS,
            base=PinnedBase(
                mirror=mirror, url="https://github.com/o/r.git", base_sha=base_sha
            ),
            repo_id=None,
            repo=repo,
            ledger=ledger,
            out_dir=tmp_path / "out",
            token=None,
        )

    real_task_module = task_module

    def _stack(stacked_on, target_branch):
        return lambda *a, **k: (stacked_on, target_branch)

    monkeypatch.setattr(real_task_module, "_resolve_stacked_on", _stack(None, None))
    unstacked = _run(c1, 1)
    assert isinstance(unstacked, Refused)
    assert unstacked.reason.startswith(c1[:12])
    assert "normal_reader.py reads OLD_NAME" in unstacked.reason
    assert "head_reader.py" not in unstacked.reason
    assert "wc_reader.py" not in unstacked.reason
    assert "protected_dir/reader1.py" not in unstacked.reason

    monkeypatch.setattr(
        real_task_module, "_resolve_stacked_on", _stack(p, "saffron/SY-0")
    )
    stacked = _run(c1, 2)
    assert isinstance(stacked, Refused)
    assert stacked.reason.startswith(p[:12])
    assert "parent_new_reader.py reads OLD_NAME" in stacked.reason
    assert "protected_dir/reader1.py reads OLD_NAME" in stacked.reason
    assert "normal_reader.py" not in stacked.reason
    assert "parent_protected/reader2.py" not in stacked.reason

    # No policy.yaml at the tree base: nothing is protected.
    repo2 = _plain_repo(tmp_path, "no-policy")
    (repo2 / "old.py").write_text("OLD_NAME\n")
    (repo2 / "protected_dir").mkdir()
    (repo2 / "protected_dir" / "reader.py").write_text("reads OLD_NAME\n")
    sha2 = _commit(repo2, "no policy")
    mirror2 = ensure_mirror(repo2, tmp_path / "no-policy.git")
    monkeypatch.setattr(real_task_module, "_resolve_stacked_on", _stack(None, None))
    monkeypatch.setattr(
        real_task_module,
        "run_one_cell",
        lambda spec, **k: CellOutcome(
            state="EXHAUSTED", task_id=1, run_id=1, task_dir=Path("/x")
        ),
    )
    ledger2 = Ledger(tmp_path / "l2.db")
    spec2 = _removes_spec("SY-1", ["old.py:OLD_NAME"], ["allowed.py"])
    result2 = task_module.run_task(
        spec2,
        "s" * 40,
        ceilings=_CEILINGS,
        base=PinnedBase(
            mirror=mirror2, url="https://github.com/o/r.git", base_sha=sha2
        ),
        repo_id=None,
        repo=repo2,
        ledger=ledger2,
        out_dir=tmp_path / "out2",
        token=None,
    )
    assert isinstance(result2, Refused)
    assert "protected_dir/reader.py reads OLD_NAME" in result2.reason

    # A policy symlink leaving the tree protects nothing.
    repo3 = _plain_repo(tmp_path, "escaping-policy")
    (repo3 / "old.py").write_text("OLD_NAME\n")
    (repo3 / "protected_dir").mkdir()
    (repo3 / "protected_dir" / "reader.py").write_text("reads OLD_NAME\n")
    (repo3 / ".saffron").mkdir()
    os.symlink("../../outside.yaml", repo3 / ".saffron" / "policy.yaml")
    sha3 = _commit(repo3, "escaping policy")
    mirror3 = ensure_mirror(repo3, tmp_path / "escaping-policy.git")
    ledger3 = Ledger(tmp_path / "l3.db")
    spec3 = _removes_spec("SY-1", ["old.py:OLD_NAME"], ["allowed.py"])
    result3 = task_module.run_task(
        spec3,
        "s" * 40,
        ceilings=_CEILINGS,
        base=PinnedBase(
            mirror=mirror3, url="https://github.com/o/r.git", base_sha=sha3
        ),
        repo_id=None,
        repo=repo3,
        ledger=ledger3,
        out_dir=tmp_path / "out3",
        token=None,
    )
    assert isinstance(result3, Refused)
    assert "protected_dir/reader.py reads OLD_NAME" in result3.reason

    # A policy that does not parse protects nothing.
    repo4 = _plain_repo(tmp_path, "bad-policy")
    (repo4 / "old.py").write_text("OLD_NAME\n")
    (repo4 / "protected_dir").mkdir()
    (repo4 / "protected_dir" / "reader.py").write_text("reads OLD_NAME\n")
    (repo4 / ".saffron").mkdir()
    (repo4 / ".saffron" / "policy.yaml").write_text("protected: [this is: not valid\n")
    sha4 = _commit(repo4, "bad policy")
    mirror4 = ensure_mirror(repo4, tmp_path / "bad-policy.git")
    ledger4 = Ledger(tmp_path / "l4.db")
    spec4 = _removes_spec("SY-1", ["old.py:OLD_NAME"], ["allowed.py"])
    result4 = task_module.run_task(
        spec4,
        "s" * 40,
        ceilings=_CEILINGS,
        base=PinnedBase(
            mirror=mirror4, url="https://github.com/o/r.git", base_sha=sha4
        ),
        repo_id=None,
        repo=repo4,
        ledger=ledger4,
        out_dir=tmp_path / "out4",
        token=None,
    )
    assert isinstance(result4, Refused)
    assert "protected_dir/reader.py reads OLD_NAME" in result4.reason

    # An undecodable policy protects nothing, caught rather than raised.
    if _undecodable_fails_here:
        repo5 = _plain_repo(tmp_path, "weird-policy")
        (repo5 / "old.py").write_text("OLD_NAME\n")
        (repo5 / "protected_dir").mkdir()
        (repo5 / "protected_dir" / "reader.py").write_text("reads OLD_NAME\n")
        (repo5 / ".saffron").mkdir()
        (repo5 / ".saffron" / "policy.yaml").write_bytes(b"\xff\xfe")
        sha5 = _commit(repo5, "weird policy")
        mirror5 = ensure_mirror(repo5, tmp_path / "weird-policy.git")
        ledger5 = Ledger(tmp_path / "l5.db")
        spec5 = _removes_spec("SY-1", ["old.py:OLD_NAME"], ["allowed.py"])
        result5 = task_module.run_task(
            spec5,
            "s" * 40,
            ceilings=_CEILINGS,
            base=PinnedBase(
                mirror=mirror5, url="https://github.com/o/r.git", base_sha=sha5
            ),
            repo_id=None,
            repo=repo5,
            ledger=ledger5,
            out_dir=tmp_path / "out5",
            token=None,
        )
        assert isinstance(result5, Refused)
        assert "protected_dir/reader.py reads OLD_NAME" in result5.reason

    # A tree base the mirror lacks is an error, not a refusal.
    monkeypatch.setattr(real_task_module, "_resolve_stacked_on", _stack(None, None))
    with pytest.raises(GitError):
        task_module.run_task(
            _removes_spec("SY-1", ["old.py:OLD_NAME"], ["allowed.py"]),
            "s" * 40,
            ceilings=_CEILINGS,
            base=PinnedBase(
                mirror=mirror, url="https://github.com/o/r.git", base_sha="0" * 40
            ),
            repo_id=None,
            repo=repo,
            ledger=Ledger(tmp_path / "l6.db"),
            out_dir=tmp_path / "out6",
            token=None,
        )


# --------------------------------------------------------- no-op cases


def test_a_spec_with_no_removes_or_no_touches_never_looks_for_readers(
    tmp_path, monkeypatch
):
    repo = _plain_repo(tmp_path, "no-lookup")
    (repo / "allowed.py").write_text("x = 1\n")
    sha = _commit(repo, "base")
    mirror = ensure_mirror(repo, tmp_path / "no-lookup.git")

    seen: list[object] = []
    monkeypatch.setattr(
        task_module,
        "removed_name_readers",
        lambda *a, **k: seen.append(a) or [],
    )
    monkeypatch.setattr(package_phase, "push_unpackaged_work", lambda *a, **k: _NO_PUSH)

    started: list[object] = []

    def _started(spec, **k):
        started.append(spec)
        return CellOutcome(state="EXHAUSTED", task_id=1, run_id=1, task_dir=Path("/x"))

    monkeypatch.setattr(task_module, "run_one_cell", _started)

    ledger = Ledger(tmp_path / "l.db")
    base = PinnedBase(
        mirror=mirror,
        url="https://github.com/o/r.git",
        base_sha=sha,
    )

    no_removes = _removes_spec("SY-1", [], ["allowed.py"])
    task_module.run_task(
        no_removes,
        "s" * 40,
        ceilings=_CEILINGS,
        base=base,
        repo_id=None,
        repo=repo,
        ledger=ledger,
        out_dir=tmp_path / "out",
        token=None,
    )
    assert seen == []
    assert len(started) == 1

    no_touches = _removes_spec("SY-2", ["gone.py"], [])
    task_module.run_task(
        no_touches,
        "s" * 40,
        ceilings=_CEILINGS,
        base=base,
        repo_id=None,
        repo=repo,
        ledger=ledger,
        out_dir=tmp_path / "out",
        token=None,
    )
    assert seen == []
    assert len(started) == 2

    both = _removes_spec("SY-3", ["gone.py"], ["allowed.py"])
    task_module.run_task(
        both,
        "s" * 40,
        ceilings=_CEILINGS,
        base=base,
        repo_id=None,
        repo=repo,
        ledger=ledger,
        out_dir=tmp_path / "out",
        token=None,
    )
    assert len(seen) == 1
    assert len(started) == 3
