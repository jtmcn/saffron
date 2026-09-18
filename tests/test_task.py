"""`run_task` end to end: what reaches the queue store for a task that never
packaged (`CONTEXT.md` §6, the morning index).

Nothing tested `run_task` directly before this file — `tests/test_cli.py` and
`tests/test_package.py` name it only in comments — so this is the first place
it is driven on its own, with `run_one_cell` and the two `package_phase` entry
points it calls (`push_unpackaged_work`, `package`) replaced by doubles at
module scope, the seams `saffron/task.py`'s own docstring names.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from saffron import task as task_module
from saffron.cell.session import CellOutcome
from saffron.intake import Spec
from saffron.ledger import Ledger
from saffron.phases import package as package_phase
from saffron.task import PinnedBase, ResolvedCeilings


def _spec(spec_id: str) -> Spec:
    return Spec(
        id=spec_id,
        title="A spec",
        type="feature",
        touches=["src/**"],
        acceptance_criteria=["it works"],
    )


def _ceilings() -> ResolvedCeilings:
    return ResolvedCeilings(
        budget_usd=12.0,
        max_attempts=4,
        max_turns=60,
        budget_source="default",
        attempts_source="default",
        turns_source="default",
    )


def _base(tmp_path: Path) -> PinnedBase:
    return PinnedBase(
        mirror=tmp_path / "mirror.git",
        url="https://github.com/o/r.git",
        base_sha="a" * 40,
    )


def _drive(
    tmp_path: Path,
    monkeypatch,
    *,
    spec_id: str,
    outcome: CellOutcome,
    out_dir: Path,
) -> CellOutcome:
    """One `run_task` call, with `run_one_cell` stubbed to hand back `outcome`
    and everything else — the ledger, the base, the ceilings, the repo path —
    built the same way for every test here."""
    monkeypatch.setattr(task_module, "run_one_cell", lambda *a, **k: outcome)
    ledger = Ledger(tmp_path / f"{spec_id}.db")
    return task_module.run_task(
        _spec(spec_id),
        "s" * 40,
        ceilings=_ceilings(),
        base=_base(tmp_path),
        repo_id=1,
        repo=tmp_path / "target-repo",
        ledger=ledger,
        out_dir=out_dir,
        token=None,
    )


def _rows(out_dir: Path) -> list[dict]:
    store = out_dir / "queue.json"
    if not store.is_file():
        return []
    return json.loads(store.read_text())


def test_a_task_that_never_packaged_still_reaches_the_index(tmp_path, monkeypatch):
    """Two different unpackaged states, for two different specs, each land
    their own row — not just one state, and not one row overwriting the
    other."""
    out_dir = tmp_path / "out"
    monkeypatch.setattr(
        package_phase,
        "push_unpackaged_work",
        lambda *a, **k: package_phase.PushResult(
            pushed=False, note="no commits, nothing to push"
        ),
    )

    _drive(
        tmp_path,
        monkeypatch,
        spec_id="SY-1",
        outcome=CellOutcome(
            state="EXHAUSTED",
            task_id=1,
            run_id=1,
            task_dir=out_dir / "SY-1",
            spent_usd=3.5,
            attempts=4,
        ),
        out_dir=out_dir,
    )
    _drive(
        tmp_path,
        monkeypatch,
        spec_id="SY-2",
        outcome=CellOutcome(
            state="NOT_IMPLEMENTED",
            task_id=2,
            run_id=2,
            task_dir=out_dir / "SY-2",
            spent_usd=1.25,
            attempts=2,
        ),
        out_dir=out_dir,
    )

    rows = {row["spec_id"]: row for row in _rows(out_dir)}
    assert rows.keys() == {"SY-1", "SY-2"}
    assert rows["SY-1"]["state"] == "EXHAUSTED"
    assert rows["SY-1"]["cost_usd_est"] == 3.5
    assert rows["SY-1"]["attempts"] == 4
    assert rows["SY-2"]["state"] == "NOT_IMPLEMENTED"
    assert rows["SY-2"]["cost_usd_est"] == 1.25
    assert rows["SY-2"]["attempts"] == 2


def test_an_unpackaged_row_carries_no_pull_request_link(tmp_path, monkeypatch):
    """The link is empty — no pull request exists — and the operator's route
    back to the work is the branch name in the note, not the link."""
    out_dir = tmp_path / "out"
    monkeypatch.setattr(
        package_phase,
        "push_unpackaged_work",
        lambda *a, **k: package_phase.PushResult(
            pushed=True,
            branch="saffron/SY-3",
            pushed_sha="b" * 40,
            note=f"pushed saffron/SY-3 @ {'b' * 12}",
        ),
    )

    _drive(
        tmp_path,
        monkeypatch,
        spec_id="SY-3",
        outcome=CellOutcome(
            state="RATE_LIMITED",
            task_id=3,
            run_id=3,
            task_dir=out_dir / "SY-3",
            spent_usd=0.9,
            attempts=1,
        ),
        out_dir=out_dir,
    )

    rows = _rows(out_dir)
    assert len(rows) == 1
    assert rows[0]["link"] == ""
    assert "saffron/SY-3" in rows[0]["note"]
    assert rows[0]["repo"] == (tmp_path / "target-repo").name


def test_a_later_package_replaces_the_unpackaged_row_and_keeps_its_link(
    tmp_path, monkeypatch
):
    """A spec whose first task never packaged and whose second task does
    leaves one row, holding the packaged outcome and its pull request link —
    never a second row, and never the earlier, linkless one surviving on
    top."""
    out_dir = tmp_path / "out"
    monkeypatch.setattr(
        package_phase,
        "push_unpackaged_work",
        lambda *a, **k: package_phase.PushResult(
            pushed=False, note="no commits, nothing to push"
        ),
    )

    _drive(
        tmp_path,
        monkeypatch,
        spec_id="SY-4",
        outcome=CellOutcome(
            state="EXHAUSTED",
            task_id=4,
            run_id=4,
            task_dir=out_dir / "SY-4",
            spent_usd=2.0,
            attempts=3,
        ),
        out_dir=out_dir,
    )
    rows = _rows(out_dir)
    assert [r["spec_id"] for r in rows] == ["SY-4"]
    assert rows[0]["state"] == "EXHAUSTED"
    assert rows[0]["link"] == ""

    from saffron.report import index as index_report

    def _package_ok(outcome, *, spec, repo, **kwargs):
        """Stands in for `_finish`: the packaged row's own write, with the
        pull request address as its link — `package.py:966-983`'s shape,
        reproduced here since the real `package()` is replaced wholesale."""
        result = package_phase.PackageResult(
            state="READY_FOR_REVIEW",
            pr_url="https://github.com/o/r/pull/9",
            pushed_sha="c" * 40,
            branch=f"saffron/{spec.id}",
        )
        index_report.append_queue_line(
            out_dir,
            index_report.QueueLine(
                repo=repo.name,
                spec_id=spec.id,
                state=result.state,
                attempts=outcome.attempts,
                cost_usd_est=outcome.spent_usd,
                concerns=0,
                added=0,
                removed=0,
                link=result.pr_url,
            ),
        )
        return result

    monkeypatch.setattr(package_phase, "package", _package_ok)
    _drive(
        tmp_path,
        monkeypatch,
        spec_id="SY-4",
        outcome=CellOutcome(
            state="READY_FOR_REVIEW",
            task_id=5,
            run_id=5,
            task_dir=out_dir / "SY-4",
            spent_usd=4.0,
            attempts=1,
        ),
        out_dir=out_dir,
    )
    rows = _rows(out_dir)
    assert [r["spec_id"] for r in rows] == ["SY-4"]
    assert rows[0]["state"] == "READY_FOR_REVIEW"
    assert rows[0]["link"] == "https://github.com/o/r/pull/9"

    def _package_raises(outcome, *, spec, repo, **kwargs):
        raise package_phase.PackageError("gh is unavailable")

    monkeypatch.setattr(package_phase, "package", _package_raises)
    with pytest.raises(package_phase.PackageError):
        _drive(
            tmp_path,
            monkeypatch,
            spec_id="SY-5",
            outcome=CellOutcome(
                state="READY_FOR_REVIEW",
                task_id=6,
                run_id=6,
                task_dir=out_dir / "SY-5",
                spent_usd=1.0,
                attempts=1,
            ),
            out_dir=out_dir,
        )

    rows = {row["spec_id"] for row in _rows(out_dir)}
    assert "SY-5" not in rows
    assert rows == {"SY-4"}
