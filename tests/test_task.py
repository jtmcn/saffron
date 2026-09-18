"""`run_task` end to end: what reaches the queue store for a task that never
packaged (`DESIGN.md` §6). `run_one_cell`, `push_unpackaged_work` and
`package` are replaced at module scope."""

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

_NO_COMMITS = "no commits, nothing to push"


def _drive(
    tmp_path: Path,
    monkeypatch,
    *,
    spec_id: str,
    state: str,
    task_id: int,
    out_dir: Path,
    spent_usd: float = 1.0,
    attempts: int = 0,
    **outcome_fields,
) -> CellOutcome:
    """One `run_task` call whose cell ends in `state`."""
    outcome = CellOutcome(
        state=state,
        task_id=task_id,
        run_id=task_id,
        task_dir=out_dir / spec_id,
        spent_usd=spent_usd,
        attempts=attempts,
        **outcome_fields,
    )
    monkeypatch.setattr(task_module, "run_one_cell", lambda *a, **k: outcome)
    return task_module.run_task(
        Spec(
            id=spec_id,
            title="A spec",
            type="feature",
            touches=["src/**"],
            acceptance_criteria=["it works"],
        ),
        "s" * 40,
        ceilings=ResolvedCeilings(
            budget_usd=12.0,
            max_attempts=4,
            max_turns=60,
            budget_source="default",
            attempts_source="default",
            turns_source="default",
        ),
        base=PinnedBase(
            mirror=tmp_path / "mirror.git",
            url="https://github.com/o/r.git",
            base_sha="a" * 40,
        ),
        repo_id=1,
        repo=tmp_path / "target-repo",
        ledger=Ledger(tmp_path / f"{spec_id}.db"),
        out_dir=out_dir,
        token=None,
    )


def _push(monkeypatch, result: package_phase.PushResult) -> None:
    monkeypatch.setattr(package_phase, "push_unpackaged_work", lambda *a, **k: result)


def _rows(out_dir: Path) -> list[dict]:
    store = out_dir / "queue.json"
    return json.loads(store.read_text()) if store.is_file() else []


def test_a_task_that_never_packaged_still_reaches_the_index(tmp_path, monkeypatch):
    """Two unpackaged states, for two specs, each land their own row."""
    out_dir = tmp_path / "out"
    _push(monkeypatch, package_phase.PushResult(pushed=False, note=_NO_COMMITS))

    for spec_id, state, task_id, spent, attempts in (
        ("SY-1", "EXHAUSTED", 1, 3.5, 4),
        ("SY-2", "NOT_IMPLEMENTED", 2, 1.25, 2),
    ):
        _drive(
            tmp_path,
            monkeypatch,
            spec_id=spec_id,
            state=state,
            task_id=task_id,
            out_dir=out_dir,
            spent_usd=spent,
            attempts=attempts,
        )

    rows = {row["spec_id"]: row for row in _rows(out_dir)}
    assert rows.keys() == {"SY-1", "SY-2"}
    assert rows["SY-1"]["state"] == "EXHAUSTED"
    assert rows["SY-1"]["cost_usd_est"] == 3.5
    assert rows["SY-1"]["attempts"] == 4
    assert rows["SY-1"]["note"] == _NO_COMMITS
    assert rows["SY-2"]["state"] == "NOT_IMPLEMENTED"
    assert rows["SY-2"]["cost_usd_est"] == 1.25
    assert rows["SY-2"]["attempts"] == 2


def test_an_unpackaged_row_carries_no_pull_request_link(tmp_path, monkeypatch):
    """The link is empty, and the pushed branch is in the note."""
    out_dir = tmp_path / "out"
    note = f"pushed saffron/SY-3 @ {'b' * 12}"
    _push(
        monkeypatch,
        package_phase.PushResult(
            pushed=True, branch="saffron/SY-3", pushed_sha="b" * 40, note=note
        ),
    )

    _drive(
        tmp_path,
        monkeypatch,
        spec_id="SY-3",
        state="RATE_LIMITED",
        task_id=3,
        out_dir=out_dir,
    )

    rows = _rows(out_dir)
    assert len(rows) == 1
    assert rows[0]["link"] == ""
    assert rows[0]["note"] == note
    assert rows[0]["repo"] == (tmp_path / "target-repo").name


def test_a_later_package_replaces_the_unpackaged_row_and_keeps_its_link(
    tmp_path, monkeypatch
):
    """One row survives, holding the packaged outcome and its link, and a
    PACKAGE that raises leaves no row."""
    from saffron.report import index as index_report

    out_dir = tmp_path / "out"
    _push(monkeypatch, package_phase.PushResult(pushed=False, note=_NO_COMMITS))

    _drive(
        tmp_path,
        monkeypatch,
        spec_id="SY-4",
        state="EXHAUSTED",
        task_id=4,
        out_dir=out_dir,
    )
    rows = _rows(out_dir)
    assert [r["spec_id"] for r in rows] == ["SY-4"]
    assert rows[0]["state"] == "EXHAUSTED"
    assert rows[0]["link"] == ""

    def _package_ok(outcome, *, spec, repo, **kwargs):
        """Stands in for `_finish`, which writes the packaged row itself."""
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
        state="READY_FOR_REVIEW",
        task_id=5,
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
            state="READY_FOR_REVIEW",
            task_id=6,
            out_dir=out_dir,
        )
    assert {row["spec_id"] for row in _rows(out_dir)} == {"SY-4"}


def test_an_unpackaged_row_counts_its_review_and_rebuttal(tmp_path, monkeypatch):
    """Concerns, sustained blockers and unkept fixes each reach the row as
    their own count, as `_finish` counts them for a packaged task."""
    from saffron.agents.findings import Finding
    from saffron.phases import rebut
    from saffron.phases.review import LensReview

    concern = Finding(
        lens="correctness",
        severity="concern",
        file="a.py",
        line=1,
        claim="c",
        anchored=True,
    )
    verdicts = [
        rebut.Verdict(finding=n, verdict="confirmed", reason="r") for n in (1, 2, 3)
    ]
    rebut_result = rebut.RebutResult(
        state="REBUTTING",
        why="halted",
        rebuttal=rebut.RebuttalTurn(
            rebuttals=[
                rebut.Rebuttal(finding=1, action="argued", argument="wrong"),
                rebut.Rebuttal(finding=2, action="fixed", argument="fixed it"),
                rebut.Rebuttal(finding=3, action="fixed", argument="fixed it"),
            ]
        ),
        verdicts=[rebut.LensVerdicts(lens="correctness", verdicts=verdicts)],
        moved=False,
        cost_usd=0.0,
    )
    assert (
        rebut.sustained_blockers(rebut_result),
        rebut.unkept_fixes(rebut_result),
    ) == (1, 2)
    out_dir = tmp_path / "out"
    _push(monkeypatch, package_phase.PushResult(pushed=False, note=_NO_COMMITS))

    _drive(
        tmp_path,
        monkeypatch,
        spec_id="SY-6",
        state="REBUTTING",
        task_id=7,
        out_dir=out_dir,
        reviews=[LensReview(lens="correctness", findings=[concern] * 3)],
        rebut_result=rebut_result,
    )

    (row,) = _rows(out_dir)
    assert (row["concerns"], row["sustained"], row["unkept"]) == (3, 1, 2)
