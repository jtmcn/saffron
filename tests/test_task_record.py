"""`run_task` pushes a task's own record exactly once, on every way out
that follows a returned cell. A push it cannot make never moves the
task's own outcome (backlog item 170)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from saffron import task as task_module
from saffron.agents.findings import Finding
from saffron.cell.session import CellOutcome
from saffron.events import Teardown, read_log
from saffron.intake import Spec
from saffron.ledger import Ledger
from saffron.phases import package as package_phase
from saffron.phases.review import LensReview
from saffron.record.refs import TASKS, RefsRecord
from saffron.task import Handoff, PinnedBase, ResolvedCeilings


def _bare(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "--bare", str(path)], check=True)
    return path


@pytest.fixture(autouse=True)
def _isolated_git(tmp_path, monkeypatch):
    """No user or system config reaches a push: an empty `HOME` and
    `XDG_CONFIG_HOME`, and `GIT_CONFIG_NOSYSTEM` set."""
    config_home = tmp_path / "home"
    config_home.mkdir()
    monkeypatch.setenv("HOME", str(config_home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def _ceilings() -> ResolvedCeilings:
    return ResolvedCeilings(
        budget_usd=12.0,
        max_attempts=4,
        max_turns=60,
        budget_source="default",
        attempts_source="default",
        turns_source="default",
    )


def _one_spec(spec_id: str) -> Spec:
    return Spec(
        id=spec_id,
        title="t",
        type="feature",
        touches=["src/**"],
        acceptance_criteria=["it works"],
    )


_UNSTACKED = Handoff(stacked_on=None, target_branch=None)


def _run_task(ledger, *, spec_id, repo_id, tmp_path, out_dir):
    return task_module.run_task(
        _one_spec(spec_id),
        "s" * 40,
        ceilings=_ceilings(),
        base=PinnedBase(
            mirror=tmp_path / "base-mirror.git",
            url="https://github.com/o/r.git",
            base_sha="a" * 40,
        ),
        repo_id=repo_id,
        repo=tmp_path / "target-repo",
        ledger=ledger,
        out_dir=out_dir,
        token=None,
        handoff=_UNSTACKED,
    )


def test_every_way_out_of_a_task_after_its_cell_pushes_its_record_once(
    tmp_path, monkeypatch
):
    """Six ways out of `run_task` after a cell returns, each pushing the
    task's own record exactly once, after PACKAGE's last fact."""
    from saffron.record.routed import RoutedRecord

    mirror = _bare(tmp_path / "mirror.git")
    origin = _bare(tmp_path / "origin.git")
    out_dir = tmp_path / "out"

    ledger = Ledger(
        tmp_path / "l.db", record=RoutedRecord(lambda key: ledger.record_home(key))
    )
    repo_id = ledger.upsert_repo("repo", str(origin), str(mirror), None)

    push_calls: list[str] = []
    original_push = RoutedRecord.push

    def _spy_push(self, key):
        push_calls.append(key)
        return original_push(self, key)

    monkeypatch.setattr(RoutedRecord, "push", _spy_push)

    def _new_task(spec_id: str) -> int:
        run_id = ledger.create_run(repo_id, base_sha="a" * 40)
        return ledger.create_task(
            run_id, spec_id=spec_id, spec_sha="s" * 40, branch=f"saffron/{spec_id}"
        )

    def _outcome(
        spec_id: str, task_id: int, *, state: str, blocker: bool
    ) -> CellOutcome:
        reviews = []
        if blocker:
            finding = Finding(
                lens="correctness",
                severity="blocker",
                file="a.py",
                line=1,
                claim="broken",
                anchored=True,
            )
            reviews = [LensReview(lens="correctness", findings=[finding])]
        return CellOutcome(
            state=state,
            task_id=task_id,
            run_id=task_id,
            task_dir=out_dir / spec_id,
            reviews=reviews,
            rebut_result=None,
        )

    def _assert_pushed_once_and_in_sync(task_id: int) -> None:
        key = ledger.record_key(task_id)
        assert key is not None
        mirror_facts = RefsRecord(mirror).read(key)
        origin_facts = RefsRecord(origin).read(key)
        assert origin_facts == mirror_facts
        assert origin_facts  # at least one fact landed

    # 1) A packaged `READY_FOR_REVIEW`.
    task_id = _new_task("SY-1")
    monkeypatch.setattr(
        task_module,
        "run_one_cell",
        lambda *a, **k: _outcome(
            "SY-1", task_id, state="READY_FOR_REVIEW", blocker=False
        ),
    )

    def _package_ok(outcome, **kwargs):
        kwargs["ledger"].record_push(outcome.task_id, "1" * 40)
        return package_phase.PackageResult(
            state="READY_FOR_REVIEW", pr_url="https://x/1"
        )

    monkeypatch.setattr(package_phase, "package", _package_ok)
    before = len(push_calls)
    result = _run_task(
        ledger, spec_id="SY-1", repo_id=repo_id, tmp_path=tmp_path, out_dir=out_dir
    )
    assert isinstance(result, CellOutcome)
    assert len(push_calls) - before == 1
    _assert_pushed_once_and_in_sync(task_id)

    # 2) An `EXHAUSTED` cell packaged in the exhausted mode.
    task_id = _new_task("SY-2")
    monkeypatch.setattr(
        task_module,
        "run_one_cell",
        lambda *a, **k: _outcome("SY-2", task_id, state="EXHAUSTED", blocker=True),
    )

    def _package_exhausted(outcome, **kwargs):
        kwargs["ledger"].record_push(outcome.task_id, "2" * 40)
        return package_phase.PackageResult(state="EXHAUSTED", pr_url="https://x/2")

    monkeypatch.setattr(package_phase, "package", _package_exhausted)
    before = len(push_calls)
    result = _run_task(
        ledger, spec_id="SY-2", repo_id=repo_id, tmp_path=tmp_path, out_dir=out_dir
    )
    assert isinstance(result, CellOutcome)
    assert len(push_calls) - before == 1
    _assert_pushed_once_and_in_sync(task_id)

    # 3) An `EXHAUSTED` cell `PACKAGE` never ran on.
    task_id = _new_task("SY-3")
    monkeypatch.setattr(
        task_module,
        "run_one_cell",
        lambda *a, **k: _outcome("SY-3", task_id, state="EXHAUSTED", blocker=False),
    )

    def _push_unpackaged(outcome, **kwargs):
        kwargs["ledger"].record_push(outcome.task_id, "3" * 40)
        return package_phase.PushResult(
            pushed=True, branch="saffron/SY-3", pushed_sha="3" * 40, note="pushed"
        )

    monkeypatch.setattr(package_phase, "push_unpackaged_work", _push_unpackaged)
    before = len(push_calls)
    result = _run_task(
        ledger, spec_id="SY-3", repo_id=repo_id, tmp_path=tmp_path, out_dir=out_dir
    )
    assert isinstance(result, CellOutcome)
    assert len(push_calls) - before == 1
    _assert_pushed_once_and_in_sync(task_id)

    # 4) A `PackageError` from a `READY_FOR_REVIEW` cell's `PACKAGE`.
    task_id = _new_task("SY-4")
    monkeypatch.setattr(
        task_module,
        "run_one_cell",
        lambda *a, **k: _outcome(
            "SY-4", task_id, state="READY_FOR_REVIEW", blocker=False
        ),
    )

    def _package_raises_package_error(outcome, **kwargs):
        kwargs["ledger"].record_push(outcome.task_id, "4" * 40)
        raise package_phase.PackageError("broke")

    monkeypatch.setattr(package_phase, "package", _package_raises_package_error)
    before = len(push_calls)
    with pytest.raises(package_phase.PackageError):
        _run_task(
            ledger, spec_id="SY-4", repo_id=repo_id, tmp_path=tmp_path, out_dir=out_dir
        )
    assert len(push_calls) - before == 1
    _assert_pushed_once_and_in_sync(task_id)

    # 5) A `RuntimeError` from it.
    task_id = _new_task("SY-5")
    monkeypatch.setattr(
        task_module,
        "run_one_cell",
        lambda *a, **k: _outcome(
            "SY-5", task_id, state="READY_FOR_REVIEW", blocker=False
        ),
    )

    def _package_raises_runtime_error(outcome, **kwargs):
        kwargs["ledger"].record_push(outcome.task_id, "5" * 40)
        raise RuntimeError("broke")

    monkeypatch.setattr(package_phase, "package", _package_raises_runtime_error)
    before = len(push_calls)
    with pytest.raises(RuntimeError):
        _run_task(
            ledger, spec_id="SY-5", repo_id=repo_id, tmp_path=tmp_path, out_dir=out_dir
        )
    assert len(push_calls) - before == 1
    _assert_pushed_once_and_in_sync(task_id)

    # 6) A `KeyboardInterrupt` from it.
    task_id = _new_task("SY-6")
    monkeypatch.setattr(
        task_module,
        "run_one_cell",
        lambda *a, **k: _outcome(
            "SY-6", task_id, state="READY_FOR_REVIEW", blocker=False
        ),
    )

    def _package_raises_keyboard_interrupt(outcome, **kwargs):
        kwargs["ledger"].record_push(outcome.task_id, "6" * 40)
        raise KeyboardInterrupt()

    monkeypatch.setattr(package_phase, "package", _package_raises_keyboard_interrupt)
    before = len(push_calls)
    with pytest.raises(KeyboardInterrupt):
        _run_task(
            ledger, spec_id="SY-6", repo_id=repo_id, tmp_path=tmp_path, out_dir=out_dir
        )
    assert len(push_calls) - before == 1
    _assert_pushed_once_and_in_sync(task_id)


def test_a_refused_push_is_an_event_and_the_task_keeps_its_outcome(
    tmp_path, monkeypatch
):
    """A push `run_task` cannot make leaves the task's outcome untouched.
    `events.jsonl` gains one `Teardown` with `ok` false naming why, and a
    raise already propagating out of `PACKAGE` still propagates as itself."""
    from saffron.record.routed import RoutedRecord

    mirror = _bare(tmp_path / "mirror.git")
    out_dir = tmp_path / "out"

    db_count = [0]

    def _ledger_over(origin) -> Ledger:
        db_count[0] += 1
        ledger = Ledger(
            tmp_path / f"l{db_count[0]}.db",
            record=RoutedRecord(lambda key: ledger.record_home(key)),
        )
        ledger.upsert_repo("repo", str(origin), str(mirror), None)
        return ledger

    def _teardown_events(spec_id: str) -> list[Teardown]:
        return [e for e in read_log(out_dir / spec_id) if isinstance(e, Teardown)]

    def _run_one_cell_factory(task_id):
        def _run_one_cell(*a, **k):
            return CellOutcome(
                state="EXHAUSTED",
                task_id=task_id,
                run_id=task_id,
                task_dir=out_dir / "ignored",
            )

        return _run_one_cell

    # 1) The origin path is no repository.
    no_repo_origin = tmp_path / "not-a-repo"
    no_repo_origin.mkdir()
    ledger = _ledger_over(no_repo_origin)
    repo_id = ledger.resolve_repo_id(str(no_repo_origin))
    assert repo_id is not None
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    task_id = ledger.create_task(run_id, spec_id="SY-10", spec_sha="s" * 40, branch="x")
    monkeypatch.setattr(task_module, "run_one_cell", _run_one_cell_factory(task_id))
    monkeypatch.setattr(
        package_phase,
        "push_unpackaged_work",
        lambda outcome, **k: package_phase.PushResult(pushed=False, note="nothing"),
    )
    result = _run_task(
        ledger, spec_id="SY-10", repo_id=1, tmp_path=tmp_path, out_dir=out_dir
    )
    assert result.state == "EXHAUSTED"
    events = _teardown_events("SY-10")
    assert len(events) == 1
    assert events[0].ok is False
    assert str(no_repo_origin) in events[0].detail

    # 2) An origin whose ref for the key already holds another history.
    stale_origin = _bare(tmp_path / "stale-origin.git")
    ledger = _ledger_over(stale_origin)
    repo_id = ledger.resolve_repo_id(str(stale_origin))
    assert repo_id is not None
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    task_id = ledger.create_task(run_id, spec_id="SY-11", spec_sha="s" * 40, branch="x")
    key = ledger.record_key(task_id)

    scratch_mirror = _bare(tmp_path / "scratch-mirror.git")
    scratch_ledger = Ledger(
        tmp_path / "scratch.db",
        record=RoutedRecord(lambda k: scratch_ledger.record_home(k)),
    )
    scratch_repo_id = scratch_ledger.upsert_repo(
        "stale", str(stale_origin), str(scratch_mirror), None
    )
    scratch_run = scratch_ledger.create_run(scratch_repo_id, base_sha="c" * 40)
    scratch_task = scratch_ledger.create_task(
        scratch_run, spec_id="SY-STALE", spec_sha="s" * 40, branch="y"
    )
    scratch_key = scratch_ledger.record_key(scratch_task)
    subprocess.run(
        [
            "git",
            "-C",
            str(scratch_mirror),
            "update-ref",
            f"{TASKS}/{key}",
            f"{TASKS}/{scratch_key}",
        ],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(scratch_mirror),
            "push",
            str(stale_origin),
            f"{TASKS}/{key}:{TASKS}/{key}",
        ],
        check=True,
    )

    monkeypatch.setattr(task_module, "run_one_cell", _run_one_cell_factory(task_id))
    result = _run_task(
        ledger, spec_id="SY-11", repo_id=1, tmp_path=tmp_path, out_dir=out_dir
    )
    assert result.state == "EXHAUSTED"
    events = _teardown_events("SY-11")
    assert len(events) == 1
    assert events[0].ok is False
    assert str(stale_origin) in events[0].detail

    # 3) The first case again, under a `PackageError`: the raise still
    # propagates as itself, beside the push's own refused event.
    ledger = _ledger_over(no_repo_origin)
    repo_id = ledger.resolve_repo_id(str(no_repo_origin))
    assert repo_id is not None
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    task_id = ledger.create_task(run_id, spec_id="SY-12", spec_sha="s" * 40, branch="x")

    def _run_one_cell_ready(*a, **k):
        return CellOutcome(
            state="READY_FOR_REVIEW",
            task_id=task_id,
            run_id=task_id,
            task_dir=out_dir / "ignored",
        )

    monkeypatch.setattr(task_module, "run_one_cell", _run_one_cell_ready)
    monkeypatch.setattr(
        package_phase,
        "package",
        lambda outcome, **k: (_ for _ in ()).throw(package_phase.PackageError("broke")),
    )
    with pytest.raises(package_phase.PackageError):
        _run_task(
            ledger, spec_id="SY-12", repo_id=1, tmp_path=tmp_path, out_dir=out_dir
        )
    events = _teardown_events("SY-12")
    assert len(events) == 1
    assert events[0].ok is False
    assert ledger.record_key(task_id) is not None
    row = ledger._db.execute(
        "SELECT state FROM tasks WHERE task_id = ?", (task_id,)
    ).fetchone()
    assert row["state"] == "READY_FOR_REVIEW"

    # 4) A push that raises `FileNotFoundError`, as git missing from
    # `PATH` does. `RoutedRecord.push` is replaced directly for it.
    def _raise_file_not_found(self, key):
        raise FileNotFoundError(2, "No such file or directory", "git")

    monkeypatch.setattr(RoutedRecord, "push", _raise_file_not_found)
    good_origin = _bare(tmp_path / "good-origin.git")
    ledger = _ledger_over(good_origin)
    repo_id = ledger.resolve_repo_id(str(good_origin))
    assert repo_id is not None
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    task_id = ledger.create_task(run_id, spec_id="SY-13", spec_sha="s" * 40, branch="x")
    monkeypatch.setattr(task_module, "run_one_cell", _run_one_cell_factory(task_id))
    monkeypatch.setattr(
        package_phase,
        "push_unpackaged_work",
        lambda outcome, **k: package_phase.PushResult(pushed=False, note="nothing"),
    )
    result = _run_task(
        ledger, spec_id="SY-13", repo_id=1, tmp_path=tmp_path, out_dir=out_dir
    )
    assert result.state == "EXHAUSTED"
    events = _teardown_events("SY-13")
    assert len(events) == 1
    assert events[0].ok is False
    assert "git" in events[0].detail
