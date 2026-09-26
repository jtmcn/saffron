"""`run_task` end to end: what reaches the queue store for a task that never
packaged (`DESIGN.md` §6). `run_one_cell`, `push_unpackaged_work` and
`package` are replaced at module scope."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from saffron import task as task_module
from saffron.cell.session import CellOutcome
from saffron.events import Event, Teardown, read_log
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
    events: Sequence[Event] | None = None,
    **outcome_fields,
) -> CellOutcome:
    """One `run_task` call whose cell ends in `state`.

    `events`, when given, are emitted through the `emit` the `run_one_cell`
    double is handed, before it returns — the only way to drive the
    default `emit` closure `run_task` builds when a caller passes none, since
    that closure lives inside `run_task` itself and is never returned."""
    outcome = CellOutcome(
        state=state,
        task_id=task_id,
        run_id=task_id,
        task_dir=out_dir / spec_id,
        spent_usd=spent_usd,
        attempts=attempts,
        **outcome_fields,
    )

    def _run_one_cell(*a, **k):
        for event in events or ():
            k["emit"](event)
        return outcome

    monkeypatch.setattr(task_module, "run_one_cell", _run_one_cell)
    result = task_module.run_task(
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
    # None of this module's specs declare `consumes`, so `run_task` never
    # refuses here.
    assert isinstance(result, CellOutcome)
    return result


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


def test_a_log_that_stopped_writing_says_so_and_a_clean_one_does_not(
    tmp_path, monkeypatch, capsys
):
    """`run_task`'s default `emit` warns the terminal, naming the log that
    stopped growing, when the log cannot be written; a log that writes
    cleanly leaves no such line."""
    _push(monkeypatch, package_phase.PushResult(pushed=False, note=_NO_COMMITS))

    broken_dir = tmp_path / "broken"
    log_path = broken_dir / "SY-7" / "events.jsonl"
    log_path.parent.mkdir(parents=True)
    log_path.mkdir()  # events.jsonl occupied by a directory, not a file
    _drive(
        tmp_path,
        monkeypatch,
        spec_id="SY-7",
        state="EXHAUSTED",
        task_id=8,
        out_dir=broken_dir,
    )
    broken_output = capsys.readouterr().out
    assert f"{log_path} refused a write" in broken_output

    clean_dir = tmp_path / "clean"
    _drive(
        tmp_path,
        monkeypatch,
        spec_id="SY-8",
        state="EXHAUSTED",
        task_id=9,
        out_dir=clean_dir,
    )
    clean_output = capsys.readouterr().out
    assert "refused a write" not in clean_output


def test_a_log_that_refused_every_write_warns_once(tmp_path, monkeypatch, capsys):
    """Several events, every append failing, still carries exactly one
    warning line — not one per lost event."""

    _push(monkeypatch, package_phase.PushResult(pushed=False, note=_NO_COMMITS))

    out_dir = tmp_path / "out"
    log_path = out_dir / "SY-9" / "events.jsonl"
    log_path.parent.mkdir(parents=True)
    log_path.mkdir()  # events.jsonl occupied by a directory, not a file

    events = [
        Teardown(timestamp=float(i), spec_id="SY-9", step=f"step-{i}", ok=True)
        for i in range(3)
    ]
    _drive(
        tmp_path,
        monkeypatch,
        spec_id="SY-9",
        state="EXHAUSTED",
        task_id=10,
        out_dir=out_dir,
        events=events,
    )
    output = capsys.readouterr().out
    assert output.count("refused a write") == 1


def test_a_log_that_failed_on_its_first_write_still_warns(
    tmp_path, monkeypatch, capsys
):
    """A log unwritable from the very first append — the task's own
    `Ceilings` line — still warns once, and the warning is never appended to
    the log: `events.jsonl` ends up holding exactly the events the
    `run_one_cell` double emitted, in order, and nothing else."""

    class _FailFirst(task_module.EventLog):
        """The first `append` fails without writing; every later one is the
        real thing. `saffron.task.EventLog` is what `run_task` builds from,
        so this is where the substitution has to land."""

        def __init__(self, task_dir):
            super().__init__(task_dir)
            self._first = True

        def append(self, event):
            if self._first:
                self._first = False
                self.failed = True
                return
            super().append(event)

    monkeypatch.setattr(task_module, "EventLog", _FailFirst)
    _push(monkeypatch, package_phase.PushResult(pushed=False, note=_NO_COMMITS))

    out_dir = tmp_path / "out"
    events = [
        Teardown(timestamp=float(i), spec_id="SY-10", step=f"step-{i}", ok=True)
        for i in range(3)
    ]
    _drive(
        tmp_path,
        monkeypatch,
        spec_id="SY-10",
        state="EXHAUSTED",
        task_id=11,
        out_dir=out_dir,
        events=events,
    )
    output = capsys.readouterr().out
    log_path = out_dir / "SY-10" / "events.jsonl"
    assert f"{log_path} refused a write" in output
    assert output.count("refused a write") == 1
    assert read_log(out_dir / "SY-10") == events


def test_a_log_that_starts_failing_partway_through_still_warns(
    tmp_path, monkeypatch, capsys
):
    """The disk filling partway through the task, not at the first line: several appends
    succeed for real, and only later ones start refusing. A check that only
    ever looks at the very first `emit` call — and never again after — would
    see that first call succeed here and print nothing, so this is the case
    that check would miss."""

    class _FailAfterTwo(task_module.EventLog):
        """The first two appends — the task's own `Ceilings` line, then the
        double's first event — write for real; every append from the third
        onward fails without writing, as a disk that fills partway through a
        night would."""

        def __init__(self, task_dir):
            super().__init__(task_dir)
            self._count = 0

        def append(self, event):
            self._count += 1
            if self._count <= 2:
                super().append(event)
            else:
                self.failed = True

    monkeypatch.setattr(task_module, "EventLog", _FailAfterTwo)
    _push(monkeypatch, package_phase.PushResult(pushed=False, note=_NO_COMMITS))

    out_dir = tmp_path / "out"
    events = [
        Teardown(timestamp=float(i), spec_id="SY-11", step=f"step-{i}", ok=True)
        for i in range(4)
    ]
    _drive(
        tmp_path,
        monkeypatch,
        spec_id="SY-11",
        state="EXHAUSTED",
        task_id=12,
        out_dir=out_dir,
        events=events,
    )
    output = capsys.readouterr().out
    log_path = out_dir / "SY-11" / "events.jsonl"
    assert f"{log_path} refused a write" in output
    assert output.count("refused a write") == 1

    logged = read_log(out_dir / "SY-11")
    assert len(logged) == 2, "only the two appends that ran before the flip land"
    assert logged[1] == events[0]


def test_a_handoff_carries_both_halves_or_neither():
    """`Handoff` is not imported at module scope: it does not exist at the
    tree base, and a module-scope import would fail collection there."""
    from saffron.task import Handoff

    Handoff(stacked_on="d" * 40, target_branch="saffron/TE-8")
    Handoff(stacked_on=None, target_branch=None)
    with pytest.raises(ValueError):
        Handoff(stacked_on="d" * 40, target_branch=None)
    with pytest.raises(ValueError):
        Handoff(stacked_on=None, target_branch="saffron/TE-9")


def test_a_handoff_replaces_the_stacking_resolver(tmp_path, monkeypatch):
    """Given a `Handoff`, `run_task` trusts it outright and never asks the
    ledger. Given none, it resolves the parent the old way, once."""
    from saffron.task import Handoff

    resolver_calls: list[None] = []

    def _resolver(*_a, **_k):
        resolver_calls.append(None)
        return "c" * 40, "saffron/TE-9"

    monkeypatch.setattr(task_module, "_resolve_stacked_on", _resolver)

    captured: dict = {}

    def _run_one_cell(cell_spec, **_kwargs):
        captured["spec"] = cell_spec
        return CellOutcome(
            state="READY_FOR_REVIEW",
            task_id=1,
            run_id=1,
            task_dir=tmp_path / "out" / "TE-1",
        )

    monkeypatch.setattr(task_module, "run_one_cell", _run_one_cell)

    def _package(_outcome, **kwargs):
        captured["parent_branch"] = kwargs["parent_branch"]
        return package_phase.PackageResult(state="READY_FOR_REVIEW", pr_url="u")

    monkeypatch.setattr(package_phase, "package", _package)

    def _call(handoff, db_name):
        resolver_calls.clear()
        captured.clear()
        ledger = Ledger(tmp_path / db_name)
        task_module.run_task(
            Spec(
                id="TE-1",
                title="t",
                type="feature",
                touches=["src/**"],
                acceptance_criteria=["it works"],
                depends_on=["TE-9"],
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
            ledger=ledger,
            out_dir=tmp_path / "out",
            token=None,
            handoff=handoff,
        )
        ledger.close()
        return (
            len(resolver_calls),
            captured["spec"].stacked_on,
            captured["parent_branch"],
        )

    calls, stacked_on, parent_branch = _call(
        Handoff(stacked_on="d" * 40, target_branch="saffron/TE-8"), "one.db"
    )
    assert calls == 0
    assert stacked_on == "d" * 40
    assert parent_branch == "saffron/TE-8"

    calls, stacked_on, parent_branch = _call(
        Handoff(stacked_on=None, target_branch=None), "two.db"
    )
    assert calls == 0
    assert stacked_on is None
    assert parent_branch is None

    calls, stacked_on, parent_branch = _call(None, "three.db")
    assert calls == 1
    assert stacked_on == "c" * 40
    assert parent_branch == "saffron/TE-9"
