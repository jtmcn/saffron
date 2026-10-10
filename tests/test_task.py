"""`run_task` end to end: what reaches the queue store for a task that never
packaged (`DESIGN.md` §6). `run_one_cell`, `push_unpackaged_work` and
`package` are replaced at module scope."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

from saffron import task as task_module
from saffron.agents.findings import Finding
from saffron.cell.session import CellOutcome
from saffron.events import Ceilings, Event, Teardown, read_log
from saffron.intake import Spec, parse_spec
from saffron.ledger import Ledger
from saffron.phases import package as package_phase
from saffron.phases.rebut import RebutResult, RebuttalTurn
from saffron.phases.review import LensReview
from saffron.repos.mirror import GitError
from saffron.repos.policy import PolicyError
from saffron.task import PinnedBase, Refused, ResolvedCeilings

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
    on_cell: Callable[[dict], None] | None = None,
    **outcome_fields,
) -> CellOutcome:
    """One `run_task` call whose cell ends in `state`.

    `events`, when given, are emitted through the `emit` the `run_one_cell`
    double is handed, before it returns — the only way to drive the
    default `emit` closure `run_task` builds when a caller passes none, since
    that closure lives inside `run_task` itself and is never returned.

    `on_cell`, when given, runs on the keyword arguments `run_task` hands
    the double, before it returns. It is the one way to write to the
    `ledger` `run_task` passes, as the real cell does."""
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
        if on_cell is not None:
            on_cell(k)
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


def test_run_task_hands_its_cell_the_task_it_was_given(tmp_path, monkeypatch):
    """`run_task` takes a keyword `task_id`, forwarded onto the `CellSpec` it
    builds. A caller that passes none still gets the old shape: no task
    named, so `_drive_cell` mints its own."""
    import functools

    built: list[int | None] = []
    real_cell_spec = task_module.CellSpec

    def _recording_cell_spec(**kwargs):
        built.append(kwargs.get("task_id"))
        return real_cell_spec(**kwargs)

    monkeypatch.setattr(task_module, "CellSpec", _recording_cell_spec)
    real_run_task = task_module.run_task
    out_dir = tmp_path / "out"
    _push(monkeypatch, package_phase.PushResult(pushed=False, note=_NO_COMMITS))

    # `task_id=9` names no task here, and SA-0182's `spec_text` raises
    # `ValueError` for one. A stand-in returning `None` covers that case.
    monkeypatch.setattr(Ledger, "spec_text", lambda self, task_id: None)
    monkeypatch.setattr(
        task_module, "run_task", functools.partial(real_run_task, task_id=9)
    )
    _drive(
        tmp_path,
        monkeypatch,
        spec_id="SY-1",
        state="EXHAUSTED",
        task_id=1,
        out_dir=out_dir,
    )

    monkeypatch.setattr(task_module, "run_task", real_run_task)
    _drive(
        tmp_path,
        monkeypatch,
        spec_id="SY-2",
        state="EXHAUSTED",
        task_id=2,
        out_dir=out_dir,
    )

    assert built == [9, None]


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


def test_both_queue_writers_put_the_trailing_accept_rate_in_the_header(
    tmp_path, monkeypatch
):
    """`run_task`'s unpackaged branch and `PACKAGE._finish` each read
    `trailing_accept_rate` off their own ledger. Each reads it after that
    ledger's own task reaches its final state, then passes it through
    `append_queue_line`'s `header` kwarg (`DESIGN.md` §6)."""
    out_dir = tmp_path / "out"
    spec_id = "SY-9"
    seed = Ledger(tmp_path / f"{spec_id}.db")
    repo_id = seed.upsert_repo("r", "https://github.com/o/r.git", "/m.git", None)
    run_id = seed.create_run(repo_id, base_sha="a" * 40)
    for n in range(2):
        merged = seed.create_task(
            run_id, spec_id=f"X-{n}", spec_sha="s" * 64, branch=f"saffron/X-{n}"
        )
        seed.set_task_state(merged, "MERGED")
    not_implemented = seed.create_task(
        run_id, spec_id="X-2", spec_sha="s" * 64, branch="saffron/X-2"
    )
    seed.set_task_state(not_implemented, "NOT_IMPLEMENTED")
    fourth = seed.create_task(
        run_id, spec_id=spec_id, spec_sha="s" * 64, branch=f"saffron/{spec_id}"
    )
    seed.set_task_state(fourth, "IMPLEMENTING")
    seed.close()

    _push(monkeypatch, package_phase.PushResult(pushed=False, note=_NO_COMMITS))

    def _set_exhausted(kwargs: dict) -> None:
        kwargs["ledger"].set_task_state(fourth, "EXHAUSTED")

    _drive(
        tmp_path,
        monkeypatch,
        spec_id=spec_id,
        state="EXHAUSTED",
        task_id=fourth,
        out_dir=out_dir,
        on_cell=_set_exhausted,
    )

    page = (out_dir / "index.html").read_text()
    assert "trailing accept rate <strong>50% of 4</strong>" in page

    finish_ledger = Ledger(tmp_path / "finish.db")
    finish_repo_id = finish_ledger.upsert_repo(
        "r2", "https://github.com/o/r2.git", "/m2.git", None
    )
    finish_run_id = finish_ledger.create_run(finish_repo_id, base_sha="a" * 40)
    for n in range(3):
        merged = finish_ledger.create_task(
            finish_run_id, spec_id=f"Y-{n}", spec_sha="s" * 64, branch=f"saffron/Y-{n}"
        )
        finish_ledger.set_task_state(merged, "MERGED")
    reviewing = finish_ledger.create_task(
        finish_run_id, spec_id="Y-9", spec_sha="s" * 64, branch="saffron/Y-9"
    )
    finish_ledger.set_task_state(reviewing, "REVIEWING")

    finish_out_dir = tmp_path / "finish-out"
    outcome = CellOutcome(
        state="REVIEWING",
        task_id=reviewing,
        run_id=reviewing,
        task_dir=finish_out_dir / "Y-9",
        spent_usd=1.0,
        attempts=1,
    )
    spec = Spec(
        id="Y-9",
        title="A spec",
        type="feature",
        touches=["src/**"],
        acceptance_criteria=["it works"],
    )
    result = package_phase.PackageResult(state="MERGE_FAILED", branch="saffron/Y-9")
    package_phase._finish(finish_ledger, outcome, finish_out_dir, spec, "r2", result)

    finish_page = (finish_out_dir / "index.html").read_text()
    assert "trailing accept rate <strong>75% of 4</strong>" in finish_page


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

    def _mint_sy5(kwargs: dict) -> None:
        """The raise path's write needs this row (b-dce9a4). `run_one_cell`
        is replaced here, so nothing else creates it."""
        ledger = kwargs["ledger"]
        repo_id = ledger.upsert_repo("r", "o-sy5", "m-sy5", None)
        run_id = ledger.create_run(repo_id, "a" * 40)
        ledger._db.execute(
            "INSERT INTO tasks "
            "(task_id, run_id, spec_id, spec_sha, state, branch, record_key) "
            "VALUES (6, ?, 'SY-5', ?, 'READY_FOR_REVIEW', 'saffron/SY-5', 'seed-sy5')",
            (run_id, "a" * 64),
        )
        ledger._db.commit()

    monkeypatch.setattr(package_phase, "package", _package_raises)
    with pytest.raises(package_phase.PackageError):
        _drive(
            tmp_path,
            monkeypatch,
            spec_id="SY-5",
            state="READY_FOR_REVIEW",
            task_id=6,
            out_dir=out_dir,
            on_cell=_mint_sy5,
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


def test_the_cell_spec_carries_the_tier_the_spec_declared_and_none_where_it_declared_none(
    tmp_path, monkeypatch
):
    """`run_task` hands `run_one_cell` a `CellSpec` whose `declared_risk` is
    the spec's `declared_risk`. That is `None` where the frontmatter declared
    no tier. The `CellSpec`'s `risk` is still the spec's `risk` (item 170)."""
    from saffron.task import Handoff

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
        return package_phase.PackageResult(state="READY_FOR_REVIEW", pr_url="u")

    monkeypatch.setattr(package_phase, "package", _package)

    head = "---\nid: TE-1\ntitle: t\ntype: feature\ntouches:\n  - src/**\n"
    tail = "---\n\n## Acceptance criteria\n- [ ] it works\n"
    cases = [
        (head + tail, None, "standard"),
        (head + "risk:\n" + tail, None, "standard"),
        (head + "risk: standard\n" + tail, "standard", "standard"),
        (head + "risk: elevated\n" + tail, "elevated", "elevated"),
    ]

    for i, (text, declared, risk) in enumerate(cases):
        spec = parse_spec(text)
        ledger = Ledger(tmp_path / f"cell-spec-{i}.db")
        task_module.run_task(
            spec,
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
            handoff=Handoff(stacked_on=None, target_branch=None),
        )
        ledger.close()
        assert captured["spec"].declared_risk == declared
        assert captured["spec"].risk == risk


# --- SA-0150: run_task on a stack batch's recorded spec text -------------

_SY1_TEXT = (
    "---\n"
    "id: SY-1\n"
    "title: File\n"
    "type: feature\n"
    "depends_on: [SY-8, SY-9]\n"
    "touches: ['src/**']\n"
    "max_turns: 55\n"
    "---\n"
    "file body\n"
)
_SY5_TEXT = _SY1_TEXT.replace("id: SY-1", "id: SY-5", 1)
_DEFAULT_PATH = ".saffron/specs/SY-1-x.md"
_OTHER_PATH = ".saffron/specs/SY-5-other.md"
_LATE_PATH = ".saffron/specs/SY-1-late.md"


def _rev_text(
    *,
    id="SY-1",
    title="Rev",
    type="bug",
    depends_on="[SY-8, SY-9]",
    touches="['src/**', 'tests/**']",
    forbidden="['docs/**']",
    risk="elevated",
    budget_usd="9.5",
    max_attempts="4",
    max_turns="50",
    claim="`src/a.py` returns 2",
    witness="tests/test_a.py::test_two",
    mutant_find=None,
    body="revised body\n",
    extra_frontmatter="",
):
    """One revised spec text, built field by field. A case holds every
    field at the spec's own defaults and overrides only the one it drives."""
    fields = {
        "id": id,
        "title": title,
        "type": type,
        "depends_on": depends_on,
        "touches": touches,
        "forbidden": forbidden,
        "risk": risk,
        "budget_usd": budget_usd,
        "max_attempts": max_attempts,
        "max_turns": max_turns,
    }
    lines = ["---"]
    for key, value in fields.items():
        if value is not None:
            lines.append(f"{key}: {value}")
    if claim is not None:
        lines.append("acceptance:")
        lines.append(f"  - claim: '{claim}'")
        lines.append(f"    witness: {witness}")
        if mutant_find is not None:
            lines.append("    mutant:")
            lines.append("      file: src/a.py")
            lines.append(f"      find: '{mutant_find}'")
    if extra_frontmatter:
        lines.append(extra_frontmatter.rstrip("\n"))
    lines.append("---")
    return "\n".join(lines) + "\n" + body


_REV_TEXT = _rev_text()
_OLDER_TEXT = _rev_text(budget_usd="5.0", touches="['src/**']")


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(
        repo,
        "-c",
        "user.email=t@example.com",
        "-c",
        "user.name=T",
        "commit",
        "-qm",
        message,
    )
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _marker_line(spec_id: str) -> str:
    # Built apart from "SY-1" so the literal marker never sits in this
    # file's own source, which a real scan would read as a dangling one.
    return f"# saffron:retired-by {spec_id}\n"


def _recorded_mirror(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """The mirror both new witnesses share: four commits shaped as the
    spec's own table, named `bare`, `base`, `broken` and `HEAD`."""
    repo = tmp_path / "recorded-mirror"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    (repo / "src").mkdir()
    (repo / "src" / "old.py").write_text("x = 1\n")
    bare = _commit(repo, "bare")

    (repo / ".saffron").mkdir()
    (repo / ".saffron" / "policy.yaml").write_text(
        "gates: {}\nprotected: [DESIGN.md]\n"
    )
    (repo / "src" / "old.py").write_text(_marker_line("SY-1") + "x = 1\n")
    specs = repo / ".saffron" / "specs"
    specs.mkdir()
    (specs / "SY-1-x.md").write_text(_SY1_TEXT)
    (specs / "SY-5-other.md").write_text(_SY5_TEXT)
    base = _commit(repo, "base")

    (repo / ".saffron" / "policy.yaml").write_text("gates: [\n")
    (repo / "src" / "old.py").write_text("x = 1\n")
    broken = _commit(repo, "broken")

    (repo / ".saffron" / "policy.yaml").write_text("gates: {}\nprotected: []\n")
    (specs / "SY-1-late.md").write_text(_SY1_TEXT)
    head = _commit(repo, "HEAD")

    return repo, {"bare": bare, "base": base, "broken": broken, "HEAD": head}


def _recorded_ledger(
    tmp_path: Path,
) -> tuple[Ledger, int, int, Path, dict[str, str]]:
    """The shared arrangement both new witnesses build: one ledger, one
    repo, one run at `base`."""
    mirror, shas = _recorded_mirror(tmp_path)
    ledger = Ledger(tmp_path / "ledger.db")
    repo_id = ledger.upsert_repo(
        "recorded", str(mirror), str(mirror), policy_sha="p" * 64
    )
    run_id = ledger.create_run(repo_id, base_sha=shas["base"])
    return ledger, run_id, repo_id, mirror, shas


def _new_task(ledger: Ledger, run_id: int) -> int:
    return ledger.create_task(
        run_id, spec_id="SY-1", spec_sha="f" * 64, branch="saffron/SY-1"
    )


def _record(
    ledger: Ledger,
    task_id: int,
    text: str,
    *,
    origin: str = "revision",
    path: str = _DEFAULT_PATH,
) -> int:
    return ledger.record_spec_text(
        task_id, origin=origin, spec_id="SY-1", path=path, text=text
    )


def _handed_spec() -> tuple[Spec, str, ResolvedCeilings]:
    ceilings = ResolvedCeilings(
        budget_usd=12.0,
        max_attempts=4,
        max_turns=60,
        budget_source="default",
        attempts_source="default",
        turns_source="default",
    )
    return (
        parse_spec(_SY1_TEXT),
        hashlib.sha256(_SY1_TEXT.encode()).hexdigest(),
        ceilings,
    )


def _assert_text_ceilings(events: list[Event], *, max_attempts: int) -> None:
    # The handed ceilings are 12.0, 4 and 60 from defaults, so each value
    # and source here can only come from the recorded text.
    ceiling_events = [e for e in events if isinstance(e, Ceilings)]
    assert len(ceiling_events) == 1
    event = ceiling_events[0]
    assert (event.budget_usd, event.max_attempts, event.max_turns) == (
        9.5,
        max_attempts,
        50,
    )
    assert (event.budget_source, event.attempts_source, event.turns_source) == (
        "spec",
        "spec",
        "spec",
    )


def test_a_task_with_a_recorded_spec_text_runs_its_latest_text(tmp_path, monkeypatch):
    """`run_task` runs a task's latest recorded spec text (SA-0182, ADR 7)
    in place of the spec it was handed, once gate 0 passes it. It rebinds
    every ceiling and downstream read to that text."""
    ledger, run_id, repo_id, mirror, shas = _recorded_ledger(tmp_path)
    spec, spec_sha, ceilings = _handed_spec()
    out_dir = tmp_path / "out"

    built: list = []
    states = ["READY_FOR_REVIEW"]

    def _run_one_cell(cell_spec, **_kwargs):
        built.append(cell_spec)
        return CellOutcome(
            state=states[-1],
            task_id=cell_spec.task_id,
            run_id=cell_spec.task_id,
            task_dir=out_dir / cell_spec.spec_id,
        )

    package_calls: list = []
    push_calls: list = []

    def _package(_outcome, *, spec, **_kwargs):
        package_calls.append(spec)
        return package_phase.PackageResult(
            state="READY_FOR_REVIEW", pr_url="https://example.invalid/pull/1"
        )

    def _recording_push(_outcome, *, spec, **_kwargs):
        push_calls.append(spec)
        return package_phase.PushResult(pushed=False, note=_NO_COMMITS)

    monkeypatch.setattr(task_module, "run_one_cell", _run_one_cell)
    monkeypatch.setattr(package_phase, "package", _package)
    monkeypatch.setattr(package_phase, "push_unpackaged_work", _recording_push)

    def _run(task_id, *, base_sha=None):
        events: list[Event] = []
        result = task_module.run_task(
            spec,
            spec_sha,
            ceilings=ceilings,
            base=PinnedBase(
                mirror=mirror,
                url="https://example.invalid/o/r.git",
                base_sha=base_sha or shas["base"],
            ),
            repo_id=repo_id,
            repo=tmp_path / "target-repo",
            ledger=ledger,
            out_dir=out_dir,
            token=None,
            task_id=task_id,
            emit=events.append,
        )
        return result, events

    # `older` then `REV`, a task whose cell reports `READY_FOR_REVIEW`.
    task_a = _new_task(ledger, run_id)
    _record(ledger, task_a, _OLDER_TEXT)
    _record(ledger, task_a, _REV_TEXT)
    states[:] = ["READY_FOR_REVIEW"]
    result_a, events_a = _run(task_a)
    assert isinstance(result_a, CellOutcome)
    spec_a = built[-1]
    assert spec_a.spec_sha == hashlib.sha256(_REV_TEXT.encode()).hexdigest()
    assert spec_a.body == "revised body\n"
    assert spec_a.touches == ["src/**", "tests/**"]
    assert spec_a.forbidden == ["docs/**"]
    assert len(spec_a.acceptance) == 1
    assert spec_a.risk == "elevated"
    assert spec_a.spec_type == "bug"
    assert spec_a.budget_usd == 9.5
    assert spec_a.max_turns == 50
    assert spec_a.max_attempts == 4
    _assert_text_ceilings(events_a, max_attempts=4)
    assert package_calls[-1] == parse_spec(_REV_TEXT)

    # A fresh task: `older` then `REV` with `max_attempts: 3`, `EXHAUSTED`.
    task_b = _new_task(ledger, run_id)
    _record(ledger, task_b, _OLDER_TEXT)
    rev_max3 = _rev_text(max_attempts="3")
    _record(ledger, task_b, rev_max3)
    states[:] = ["EXHAUSTED"]
    built.clear()
    result_b, events_b = _run(task_b)
    assert isinstance(result_b, CellOutcome)
    _assert_text_ceilings(events_b, max_attempts=3)
    spec_b = built[-1]
    assert spec_b.max_attempts == 3
    assert push_calls[-1] == parse_spec(rev_max3)
    assert push_calls[-1].max_attempts == 3

    # A follow-up task holding `REV` alone, at its own follow-up path.
    task_c = _new_task(ledger, run_id)
    _record(
        ledger, task_c, _REV_TEXT, origin="follow_up", path=".saffron/specs/SY-1-g.md"
    )
    built.clear()
    states[:] = ["EXHAUSTED"]
    result_c, _ = _run(task_c)
    assert isinstance(result_c, CellOutcome)
    assert len(built) == 1
    assert built[0].spec_sha == hashlib.sha256(_REV_TEXT.encode()).hexdigest()

    # A follow-up task later revised, both at the same follow-up path.
    task_d = _new_task(ledger, run_id)
    _record(
        ledger, task_d, _REV_TEXT, origin="follow_up", path=".saffron/specs/SY-1-f.md"
    )
    _record(
        ledger, task_d, _REV_TEXT, origin="revision", path=".saffron/specs/SY-1-f.md"
    )
    built.clear()
    result_d, _ = _run(task_d)
    assert isinstance(result_d, CellOutcome)
    assert len(built) == 1
    assert built[0].spec_sha == hashlib.sha256(_REV_TEXT.encode()).hexdigest()

    # A task with no recorded text, at a sha the mirror does not hold.
    task_e = _new_task(ledger, run_id)
    built.clear()
    result_e, _ = _run(task_e, base_sha="a" * 40)
    assert isinstance(result_e, CellOutcome)
    assert built[-1].body == "file body\n"

    # `Ledger.spec_text` must never be read when no `task_id` is given.
    def _fails(self, task_id):
        raise AssertionError("spec_text read with no task_id")

    monkeypatch.setattr(Ledger, "spec_text", _fails)
    built.clear()
    events_f: list[Event] = []
    result_f = task_module.run_task(
        spec,
        spec_sha,
        ceilings=ceilings,
        base=PinnedBase(
            mirror=mirror, url="https://example.invalid/o/r.git", base_sha=shas["base"]
        ),
        repo_id=repo_id,
        repo=tmp_path / "target-repo",
        ledger=ledger,
        out_dir=out_dir,
        token=None,
        emit=events_f.append,
    )
    assert isinstance(result_f, CellOutcome)
    assert built[-1].spec_sha == hashlib.sha256(_SY1_TEXT.encode()).hexdigest()


def test_gate_zero_refuses_a_recorded_spec_text_before_its_cell(
    tmp_path, monkeypatch, capsys
):
    """`run_task` re-runs gate 0 against a task's latest recorded spec text
    before any cell starts. A refused text is refused the same way a queued
    spec at `base_sha` would be, and nothing else is read once it is."""
    ledger, run_id, repo_id, mirror, shas = _recorded_ledger(tmp_path)
    spec, spec_sha, ceilings = _handed_spec()
    out_dir = tmp_path / "out"

    def _run_one_cell(*_a, **_k):
        raise AssertionError("run_one_cell must not run for a refused task")

    monkeypatch.setattr(task_module, "run_one_cell", _run_one_cell)

    def _run(task_id, *, base_sha=None):
        return task_module.run_task(
            spec,
            spec_sha,
            ceilings=ceilings,
            base=PinnedBase(
                mirror=mirror,
                url="https://example.invalid/o/r.git",
                base_sha=base_sha or shas["base"],
            ),
            repo_id=repo_id,
            repo=tmp_path / "target-repo",
            ledger=ledger,
            out_dir=out_dir,
            token=None,
            task_id=task_id,
            emit=lambda _event: None,
        )

    def _assert_refused(task_id: int, phrase: str) -> None:
        result = _run(task_id)
        assert isinstance(result, Refused), phrase
        assert phrase in result.reason, result.reason
        assert "  " not in result.reason, result.reason
        out = capsys.readouterr().out
        assert out == f"{'SY-1':<10} refused  {result.reason}\n"
        row = ledger._db.execute(
            "SELECT state FROM tasks WHERE task_id = ?", (task_id,)
        ).fetchone()
        assert row["state"] == "QUEUED"
        assert ledger.attempts(task_id) == []

    single_row_cases = [
        ("no frontmatter", "revised body\n", "does not parse"),
        ("yaml", "---\n: [\n---\n\nbody\n", "does not parse"),
        ("list", "---\n- a\n---\n\nbody\n", "does not parse"),
        ("reserved", _rev_text(extra_frontmatter="body: x"), "does not parse"),
        ("invalid", _rev_text(type="nope"), "does not parse"),
        (
            "both",
            _rev_text(body="revised body\n\n## Acceptance criteria\n- [ ] it works\n"),
            "does not parse",
        ),
        (
            "mutant",
            _rev_text(mutant_find="return 2", body="it does return 2\n"),
            "does not parse",
        ),
        ("id", _rev_text(id="SY-2"), "declares SY-2"),
        ("added", _rev_text(depends_on="[SY-8, SY-9, SY-7]"), "depends_on"),
        ("dropped", _rev_text(depends_on="[SY-8]"), "depends_on"),
        ("reordered", _rev_text(depends_on="[SY-9, SY-8]"), "depends_on"),
        ("budget", _rev_text(budget_usd="12.5"), "budget_usd"),
        ("attempts", _rev_text(max_attempts="5"), "max_attempts"),
        ("turns", _rev_text(max_turns="56"), "max_turns"),
        ("undeclared", _rev_text(max_turns=None), "max_turns"),
        (
            "protected",
            _rev_text(touches="['src/**', 'tests/**', 'DESIGN.md']"),
            "protected",
        ),
        ("criterion", _rev_text(claim="`lib/a.py` returns 2"), "lib/a.py"),
        ("marker", _rev_text(touches="['src/a.py', 'tests/**']"), "src/old.py"),
        (
            "consumes",
            _rev_text(extra_frontmatter="consumes: [src/missing.py]"),
            "src/missing.py",
        ),
    ]
    for _name, text, phrase in single_row_cases:
        task = _new_task(ledger, run_id)
        _record(ledger, task, text)
        _assert_refused(task, phrase)

    # tampered: a row whose stored hash disagrees with its own text.
    task = _new_task(ledger, run_id)
    n = _record(ledger, task, _REV_TEXT)
    ledger._db.execute(
        "UPDATE spec_texts SET spec_sha = ? WHERE task_key = ? AND n = ?",
        ("0" * 64, ledger.record_key(task), n),
    )
    ledger._db.commit()
    _assert_refused(task, "does not hash to its spec_sha")

    # other spec / late: a revision's path names a file at `base_sha` that
    # is not the task's own spec, or one that only exists past `base_sha`.
    task = _new_task(ledger, run_id)
    _record(ledger, task, _REV_TEXT, path=_OTHER_PATH)
    _assert_refused(task, "not the task's spec file")

    task = _new_task(ledger, run_id)
    _record(ledger, task, _REV_TEXT, path=_LATE_PATH)
    _assert_refused(task, "not the task's spec file")

    # widened: a follow-up task's later revision cannot grow its touches.
    task = _new_task(ledger, run_id)
    _record(
        ledger, task, _REV_TEXT, origin="follow_up", path=".saffron/specs/SY-1-w.md"
    )
    _record(
        ledger,
        task,
        _rev_text(touches="['src/**', 'tests/**', 'lib/**']"),
        origin="revision",
        path=".saffron/specs/SY-1-w.md",
    )
    _assert_refused(task, "widens")

    # The latest revision repeats the earlier one's widened touches, so only
    # a check against the first row refuses it.
    task = _new_task(ledger, run_id)
    _record(
        ledger,
        task,
        _rev_text(touches="['src/**']"),
        origin="follow_up",
        path=".saffron/specs/SY-1-wc.md",
    )
    _record(
        ledger,
        task,
        _rev_text(touches="['src/**', 'lib/**']"),
        origin="revision",
        path=".saffron/specs/SY-1-wc.md",
    )
    _record(
        ledger,
        task,
        _rev_text(touches="['src/**', 'lib/**']"),
        origin="revision",
        path=".saffron/specs/SY-1-wc.md",
    )
    _assert_refused(task, "widens")

    # A follow-up first row that does not parse refuses its valid revision.
    task = _new_task(ledger, run_id)
    first_n = _record(
        ledger,
        task,
        "revised body\n",
        origin="follow_up",
        path=".saffron/specs/SY-1-u.md",
    )
    _record(ledger, task, _REV_TEXT, origin="revision", path=".saffron/specs/SY-1-u.md")
    _assert_refused(task, f"follows first text {first_n}, which does not parse")

    # An earlier row at the same path needs no read at all. Three broken
    # bases still raise, and one good base reaches the export cleanly.
    task = _new_task(ledger, run_id)
    _record(
        ledger, task, _REV_TEXT, origin="follow_up", path=".saffron/specs/SY-1-z.md"
    )
    _record(ledger, task, _REV_TEXT, origin="revision", path=".saffron/specs/SY-1-z.md")

    for bad_base in ("b" * 40, shas["bare"]):
        with pytest.raises(GitError):
            _run(task, base_sha=bad_base)
    with pytest.raises(PolicyError):
        _run(task, base_sha=shas["broken"])

    ok = task_module._recorded_spec_text(
        ledger,
        task,
        spec,
        PinnedBase(
            mirror=mirror, url="https://example.invalid/o/r.git", base_sha=shas["base"]
        ),
    )
    assert isinstance(ok, tuple)
    assert ok[0].id == "SY-1"
    assert ok[0].budget_usd == 9.5


def test_run_task_hands_the_cell_the_specs_own_estimate_in_lines(tmp_path, monkeypatch):
    """A spec's own `estimated_lines` is already in the plan's own unit
    (b-43a061). It never reached IMPLEMENT, REVIEW or REBUT, because
    `CellSpec.body` carried the spec's raw body alone (b-efdf1f). `run_task`
    must append the author's own estimate."""
    _push(monkeypatch, package_phase.PushResult(pushed=False, note=_NO_COMMITS))
    body = "the spec's own body text.\n"

    def _call(estimated_lines: int | None, db_name: str) -> str:
        captured: dict = {}

        def _run_one_cell(cell_spec, **_kwargs):
            captured["body"] = cell_spec.body
            return CellOutcome(
                state="EXHAUSTED",
                task_id=1,
                run_id=1,
                task_dir=tmp_path / "out" / "TE-1",
            )

        monkeypatch.setattr(task_module, "run_one_cell", _run_one_cell)
        ledger = Ledger(tmp_path / db_name)
        task_module.run_task(
            Spec(
                id="TE-1",
                title="t",
                type="feature",
                touches=["src/**"],
                acceptance_criteria=["it works"],
                body=body,
                estimated_lines=estimated_lines,
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
        )
        ledger.close()
        return captured["body"]

    assert _call(None, "unset.db") == body

    for estimated_lines in (37, 1210):
        result = _call(estimated_lines, f"{estimated_lines}.db")
        assert result.startswith(body)
        assert result.endswith("\n")
        tail = result[len(body) :]
        assert tail.startswith("\n")
        assert re.search(
            rf"\b{estimated_lines}\b\W+(?:changed\W+)?lines?\b", tail, re.I
        )
        assert not re.search(
            rf"\b{estimated_lines}\b\W+(?:changed\W+)?tokens?\b", tail, re.I
        )
        sentences = re.split(r"\.|\n", tail)
        assert any(
            re.search(rf"\b{estimated_lines}\b", s)
            and "estimat" in s.lower().replace("estimated_lines", "")
            for s in sentences
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


def _pinned(tmp_path: Path) -> PinnedBase:
    return PinnedBase(
        mirror=tmp_path / "mirror.git",
        url="https://github.com/o/r.git",
        base_sha="a" * 40,
    )


def _one_spec(spec_id: str, **overrides) -> Spec:
    return Spec(
        id=spec_id,
        title="t",
        type="feature",
        touches=["src/**"],
        acceptance_criteria=["it works"],
        **overrides,
    )


def _seed_one_merged(ledger: Ledger) -> None:
    """One settled task, so `trailing_accept_rate` reads `100% of 1`.
    An empty ledger reads a placeholder a bare key check cannot tell apart
    from a real rate."""
    repo_id = ledger.upsert_repo(
        "other", "https://github.com/o/other.git", "/o.git", None
    )
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    merged = ledger.create_task(
        run_id, spec_id="M-1", spec_sha="s" * 64, branch="saffron/M-1"
    )
    ledger.set_task_state(merged, "MERGED")


def test_a_running_task_holds_one_queue_row_that_its_end_replaces(
    tmp_path, monkeypatch
):
    """Each phase start writes a live row under the task's own repo and
    spec key. The task's end replaces it last, leaving one row (DESIGN.md
    §6, §5.7 step 4)."""
    from dataclasses import asdict

    from saffron.report import index as index_report

    def _expect_live(spec_id: str, state: str) -> dict:
        return asdict(
            index_report.QueueLine(
                repo="target-repo",
                spec_id=spec_id,
                state=state,
                attempts=0,
                cost_usd_est=None,
                concerns=0,
                added=0,
                removed=0,
                link="",
                risk="elevated",
            )
        )

    def _run_case(name: str, spec_id: str, *, end_state: str, package_ok: bool):
        out_dir = tmp_path / name
        other = index_report.QueueLine(
            repo="target-repo",
            spec_id="OTHER-1",
            state="READY_FOR_REVIEW",
            attempts=1,
            cost_usd_est=1.0,
            concerns=0,
            added=0,
            removed=0,
            link="",
        )
        index_report.append_queue_line(out_dir, other, header={})
        other_row = asdict(other)
        assert _rows(out_dir) == [other_row]

        ledger = Ledger(tmp_path / f"{name}.db")
        _seed_one_merged(ledger)
        reads: list[list[dict]] = []
        rates: list[str] = []

        def _run_one_cell(*a, **k):
            # Captured on entry, before any `on_state` call, so a row
            # written early, such as `QUEUED`, still shows up here.
            reads.append(_rows(out_dir))
            for state in ("IMPLEMENTING", "REVIEWING"):
                k["on_state"](state)
                reads.append(_rows(out_dir))
                page = (out_dir / "index.html").read_text()
                assert f"<code>{state}</code>" in page
                match = re.search(
                    r"trailing accept rate <strong>([^<]+)</strong>", page
                )
                assert match is not None
                rates.append(match.group(1))
                # A second settled task lands between the two writes, so a
                # header cached once would show the same rate twice.
                if state == "IMPLEMENTING":
                    _seed_one_merged(ledger)
            return CellOutcome(
                state=end_state,
                task_id=1,
                run_id=1,
                task_dir=out_dir / spec_id,
                spent_usd=2.0,
                attempts=3,
            )

        monkeypatch.setattr(task_module, "run_one_cell", _run_one_cell)
        if package_ok:

            def _package_ok(outcome, *, spec, repo, **kwargs):
                result = package_phase.PackageResult(
                    state="READY_FOR_REVIEW",
                    pr_url="https://github.com/o/r/pull/1",
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
        else:
            monkeypatch.setattr(
                package_phase,
                "push_unpackaged_work",
                lambda *a, **k: package_phase.PushResult(
                    pushed=False, note=_NO_COMMITS
                ),
            )

        result = task_module.run_task(
            _one_spec(spec_id, risk="elevated"),
            "s" * 40,
            ceilings=_ceilings(),
            base=_pinned(tmp_path),
            repo_id=1,
            repo=tmp_path / "target-repo",
            ledger=ledger,
            out_dir=out_dir,
            token=None,
        )
        ledger.close()
        assert isinstance(result, CellOutcome)
        assert reads[0] == [other_row]
        assert reads[1] == [other_row, _expect_live(spec_id, "IMPLEMENTING")]
        assert reads[2] == [other_row, _expect_live(spec_id, "REVIEWING")]
        assert rates == ["100% of 1", "100% of 2"]
        return result, _rows(out_dir), other_row

    result, final, _other = _run_case(
        "exhausted", "SY-30", end_state="EXHAUSTED", package_ok=False
    )
    assert result.state == "EXHAUSTED"
    assert [row["spec_id"] for row in final] == ["OTHER-1", "SY-30"]
    assert final[1]["state"] == "EXHAUSTED"

    result, final, other_row = _run_case(
        "ready", "SY-31", end_state="READY_FOR_REVIEW", package_ok=True
    )
    assert result.state == "READY_FOR_REVIEW"
    assert final[0] == other_row
    assert final[1]["spec_id"] == "SY-31"
    assert final[1]["state"] == "READY_FOR_REVIEW"
    assert final[1]["link"] == "https://github.com/o/r/pull/1"


def test_a_cell_that_raises_leaves_its_running_row_orphaned(tmp_path, monkeypatch):
    """A raise past at least one landed write orphans that row and
    re-raises the same exception object. A raise before any write leaves no
    row and no page behind (DESIGN.md §6)."""

    live_rows: dict[str, list[dict]] = {}

    def _drive(spec_id, out_dir, error, *, after_write):
        ledger = Ledger(tmp_path / f"{spec_id}.db")
        _seed_one_merged(ledger)

        def _run_one_cell(*a, **k):
            if after_write:
                k["on_state"]("REVIEWING")
                live_rows[spec_id] = json.loads((out_dir / "queue.json").read_text())
            raise error

        monkeypatch.setattr(task_module, "run_one_cell", _run_one_cell)

        with pytest.raises(type(error)) as raised:
            task_module.run_task(
                _one_spec(spec_id, risk="elevated"),
                "s" * 40,
                ceilings=_ceilings(),
                base=_pinned(tmp_path),
                repo_id=1,
                repo=tmp_path / "target-repo",
                ledger=ledger,
                out_dir=out_dir,
                token=None,
            )
        assert raised.value is error
        ledger.close()

    # A write landed: the raise orphans that row. Every other field,
    # the spec's declared `risk` included, stays as it was.
    out_dir = tmp_path / "out-write"
    error = RuntimeError("boom")
    _drive("SY-40", out_dir, error, after_write=True)
    rows = json.loads((out_dir / "queue.json").read_text())
    assert [live["risk"] for live in live_rows["SY-40"]] == ["elevated"]
    assert rows == [{**live, "state": "ORPHANED"} for live in live_rows["SY-40"]]
    page = (out_dir / "index.html").read_text()
    assert "trailing accept rate <strong>100% of 1</strong>" in page

    # A `KeyboardInterrupt`, caught the same way.
    out_dir2 = tmp_path / "out-write-interrupt"
    interrupt = KeyboardInterrupt()
    _drive("SY-41", out_dir2, interrupt, after_write=True)
    rows2 = json.loads((out_dir2 / "queue.json").read_text())
    assert rows2 == [{**live, "state": "ORPHANED"} for live in live_rows["SY-41"]]

    # No write landed before the raise: no row, no page, but the task's own
    # `events.jsonl` directory is there.
    out_dir3 = tmp_path / "out-no-write"
    error2 = RuntimeError("early")
    _drive("SY-42", out_dir3, error2, after_write=False)
    assert not (out_dir3 / "queue.json").exists()
    assert not (out_dir3 / "index.html").exists()
    assert (out_dir3 / "SY-42" / "events.jsonl").is_file()


def test_a_failed_live_row_write_never_stops_the_cell(tmp_path, monkeypatch):
    """A live row's own write never stops the cell. A state whose write
    failed does not count as written, for `ORPHANED`'s own sake (DESIGN.md
    §6)."""
    from saffron.report import index as index_report

    real_append = index_report.append_queue_line
    printed: list[str] = []
    monkeypatch.setattr(
        "builtins.print", lambda *a, **k: printed.append(" ".join(str(x) for x in a))
    )

    def _flaky(fails_on: set[str]):
        def _append(out, line, **kwargs):
            # Not an `OSError`, so a catch narrowed to one fails this test.
            if line.state in fails_on:
                raise ValueError(f"disk full writing {line.state}")
            return real_append(out, line, **kwargs)

        return _append

    def _prepare(spec_id, out_dir, *, fails_on):
        ledger = Ledger(tmp_path / f"{spec_id}.db")
        monkeypatch.setattr(
            task_module.index_report, "append_queue_line", _flaky(fails_on)
        )
        monkeypatch.setattr(
            package_phase,
            "push_unpackaged_work",
            lambda *a, **k: package_phase.PushResult(pushed=False, note=_NO_COMMITS),
        )
        return ledger

    # `IMPLEMENTING` fails: the cell goes on, and the end row still lands.
    out_dir = tmp_path / "out-implementing"
    ledger = _prepare("SY-50", out_dir, fails_on={"IMPLEMENTING"})
    went_on = False

    def _run_one_cell_a(*a, **k):
        nonlocal went_on
        k["on_state"]("IMPLEMENTING")
        went_on = True
        return CellOutcome(
            state="EXHAUSTED",
            task_id=1,
            run_id=1,
            task_dir=out_dir / "SY-50",
            spent_usd=1.0,
            attempts=1,
        )

    monkeypatch.setattr(task_module, "run_one_cell", _run_one_cell_a)
    result = task_module.run_task(
        _one_spec("SY-50"),
        "s" * 40,
        ceilings=_ceilings(),
        base=_pinned(tmp_path),
        repo_id=1,
        repo=tmp_path / "target-repo",
        ledger=ledger,
        out_dir=out_dir,
        token=None,
    )
    ledger.close()
    assert isinstance(result, CellOutcome)
    assert result.state == "EXHAUSTED"
    assert went_on is True
    rows = json.loads((out_dir / "queue.json").read_text())
    assert len(rows) == 1
    assert rows[0]["state"] == "EXHAUSTED"
    hits = [
        p for p in printed if "SY-50" in p and "IMPLEMENTING" in p and "disk full" in p
    ]
    assert len(hits) == 1

    # `ORPHANED` fails: the cell's own exception still propagates, and the
    # store keeps the live `REVIEWING` row.
    out_dir2 = tmp_path / "out-orphaned"
    ledger2 = _prepare("SY-51", out_dir2, fails_on={"ORPHANED"})
    error = RuntimeError("boom")

    def _run_one_cell_b(*a, **k):
        k["on_state"]("REVIEWING")
        raise error

    monkeypatch.setattr(task_module, "run_one_cell", _run_one_cell_b)
    with pytest.raises(RuntimeError) as raised:
        task_module.run_task(
            _one_spec("SY-51"),
            "s" * 40,
            ceilings=_ceilings(),
            base=_pinned(tmp_path),
            repo_id=1,
            repo=tmp_path / "target-repo",
            ledger=ledger2,
            out_dir=out_dir2,
            token=None,
        )
    ledger2.close()
    assert raised.value is error
    rows2 = json.loads((out_dir2 / "queue.json").read_text())
    assert len(rows2) == 1
    assert rows2[0]["state"] == "REVIEWING"
    orphan_hits = [
        p for p in printed if "SY-51" in p and "ORPHANED" in p and "disk full" in p
    ]
    assert len(orphan_hits) == 1

    # `REVIEWING` fails mid-run: the exception still propagates, and the
    # store holds no row at all.
    out_dir3 = tmp_path / "out-reviewing"
    ledger3 = _prepare("SY-52", out_dir3, fails_on={"REVIEWING"})
    error2 = RuntimeError("boom2")

    def _run_one_cell_c(*a, **k):
        k["on_state"]("REVIEWING")
        raise error2

    monkeypatch.setattr(task_module, "run_one_cell", _run_one_cell_c)
    with pytest.raises(RuntimeError) as raised2:
        task_module.run_task(
            _one_spec("SY-52"),
            "s" * 40,
            ceilings=_ceilings(),
            base=_pinned(tmp_path),
            repo_id=1,
            repo=tmp_path / "target-repo",
            ledger=ledger3,
            out_dir=out_dir3,
            token=None,
        )
    ledger3.close()
    assert raised2.value is error2
    assert not (out_dir3 / "queue.json").exists()


def test_an_exhausted_task_whose_rebuttal_was_never_paid_for_is_packaged(
    tmp_path, monkeypatch
):
    """`run_task` hands a cell to `package()` in the `EXHAUSTED` mode exactly
    when the cell ended `EXHAUSTED` with an anchored blocker and no
    `rebut_result`. That call passes the same `parent_branch` a
    `READY_FOR_REVIEW` cell's call does. Every other shape goes to
    `push_unpackaged_work`, never to `package()`."""
    from saffron.task import Handoff

    blocker = Finding(
        lens="correctness",
        severity="blocker",
        file="a.py",
        line=3,
        claim="broken",
        anchored=True,
    )
    unanchored = Finding.model_validate(blocker.model_dump() | {"anchored": False})
    concern = Finding.model_validate(blocker.model_dump() | {"severity": "concern"})
    cut_short_rebuttal = RebutResult(
        state="REBUTTED",
        why="budget",
        rebuttal=RebuttalTurn(),
        verdicts=[],
        moved=False,
        cost_usd=1.0,
    )

    handoff = Handoff(stacked_on="d" * 40, target_branch="saffron/TE-8")
    out_dir = tmp_path / "out"

    cases = [
        ("exhausted-unrebutted", "EXHAUSTED", [blocker], None, True, False),
        ("ready", "READY_FOR_REVIEW", [], None, True, False),
        ("exhausted-no-review", "EXHAUSTED", [], None, False, True),
        ("exhausted-rebutted", "EXHAUSTED", [blocker], cut_short_rebuttal, False, True),
        ("reviewing", "REVIEWING", [blocker], None, False, True),
        ("rebutting", "REBUTTING", [blocker], None, False, True),
        ("exhausted-unanchored", "EXHAUSTED", [unanchored], None, False, True),
        ("exhausted-concern", "EXHAUSTED", [concern], None, False, True),
    ]

    for n, (
        name,
        state,
        findings,
        rebut_result,
        expect_package,
        expect_push,
    ) in enumerate(cases):
        task_id = 100 + n

        def _run_one_cell(
            *a,
            _findings=findings,
            _state=state,
            _rebut=rebut_result,
            _task_id=task_id,
            _name=name,
            **k,
        ):
            return CellOutcome(
                state=_state,
                task_id=_task_id,
                run_id=_task_id,
                task_dir=out_dir / _name,
                spent_usd=1.0,
                attempts=1,
                reviews=(
                    [LensReview(lens="correctness", findings=_findings)]
                    if _findings
                    else []
                ),
                rebut_result=_rebut,
            )

        monkeypatch.setattr(task_module, "run_one_cell", _run_one_cell)

        package_calls: list[dict] = []

        def _package(_outcome, *, _calls=package_calls, _state=state, **kwargs):
            _calls.append(kwargs)
            # A pull request every time: this test checks only whether
            # `package()` is called. Criterion 4 covers push-after-refusal.
            return package_phase.PackageResult(state=_state, pr_url="https://x/pull/1")

        monkeypatch.setattr(package_phase, "package", _package)

        push_calls: list[dict] = []

        def _push(_outcome, *, _calls=push_calls, **kwargs):
            _calls.append(kwargs)
            return package_phase.PushResult(pushed=False, note="nothing to push")

        monkeypatch.setattr(package_phase, "push_unpackaged_work", _push)

        ledger = Ledger(tmp_path / f"{name}.db")
        task_module.run_task(
            _one_spec(f"TE-{n}"),
            "s" * 40,
            ceilings=_ceilings(),
            base=_pinned(tmp_path),
            repo_id=1,
            repo=tmp_path / "target-repo",
            ledger=ledger,
            out_dir=out_dir,
            token=None,
            handoff=handoff,
        )
        ledger.close()

        assert bool(package_calls) == expect_package, name
        assert bool(push_calls) == expect_push, name
        if expect_package:
            assert package_calls[0]["parent_branch"] == "saffron/TE-8", name
            assert package_calls[0]["exhausted"] == (state == "EXHAUSTED"), name


def test_an_exhausted_package_that_opened_nothing_still_pushes_its_work(
    tmp_path, monkeypatch
):
    """When `package()` in the `EXHAUSTED` mode returns no `pr_url`, or
    raises a `PackageError`, `run_task` still calls `push_unpackaged_work`,
    handing it `package()`'s note or the error's text. A `PackageError` from
    a `READY_FOR_REVIEW` cell's `package()` still raises, and nothing is
    pushed."""
    from saffron.report import index as index_report
    from saffron.task import Handoff

    out_dir = tmp_path / "out"
    blocker = Finding(
        lens="correctness",
        severity="blocker",
        file="a.py",
        line=3,
        claim="broken",
        anchored=True,
    )

    def _exhausted_outcome(task_id: int, name: str) -> CellOutcome:
        return CellOutcome(
            state="EXHAUSTED",
            task_id=task_id,
            run_id=task_id,
            task_dir=out_dir / name,
            spent_usd=1.0,
            attempts=1,
            reviews=[LensReview(lens="correctness", findings=[blocker])],
            rebut_result=None,
        )

    def _run(spec_id, task_id, name, outcome, package_fn, push_fn, seed=None):
        monkeypatch.setattr(task_module, "run_one_cell", lambda *a, **k: outcome)
        monkeypatch.setattr(package_phase, "package", package_fn)
        monkeypatch.setattr(package_phase, "push_unpackaged_work", push_fn)
        ledger = Ledger(tmp_path / f"{name}.db")
        if seed is not None:
            seed(ledger)
        result = task_module.run_task(
            _one_spec(spec_id),
            "s" * 40,
            ceilings=_ceilings(),
            base=_pinned(tmp_path),
            repo_id=1,
            repo=tmp_path / "target-repo",
            ledger=ledger,
            out_dir=out_dir,
            token=None,
            handoff=Handoff(stacked_on="d" * 40, target_branch="saffron/TE-8"),
        )
        ledger.close()
        return result

    # 1) A refusing fake: a `PackageResult` in `EXHAUSTED` whose note says it
    # conflicts, and no `pr_url`.
    push_calls_1: list[dict] = []

    def _package_refuses(_outcome, **kwargs):
        return package_phase.PackageResult(
            state="EXHAUSTED", note="conflicts with main"
        )

    def _push_records_1(_outcome, *, package_refusal=None, **kwargs):
        push_calls_1.append({"package_refusal": package_refusal, **kwargs})
        return package_phase.PushResult(
            pushed=True, branch="saffron/TE-1", pushed_sha="c" * 40, note="pushed"
        )

    result1 = _run(
        "TE-1",
        101,
        "refuses",
        _exhausted_outcome(101, "refuses"),
        _package_refuses,
        _push_records_1,
    )
    assert push_calls_1 and push_calls_1[0]["package_refusal"] == "conflicts with main"
    row1 = _rows(out_dir)
    row1 = next(r for r in row1 if r["spec_id"] == "TE-1")
    assert row1["state"] == "EXHAUSTED"
    assert row1["link"] == ""
    assert "conflicts with main" in row1["note"] and "pushed" in row1["note"]
    assert result1.state == "EXHAUSTED"

    # 2) An opening fake: writes its own row with `append_queue_line` and
    # returns a `pr_url`. No push must run.
    push_calls_2: list[dict] = []

    def _package_opens(_outcome, **kwargs):
        index_report.append_queue_line(
            out_dir,
            index_report.QueueLine(
                repo=(tmp_path / "target-repo").name,
                spec_id="TE-2",
                state="EXHAUSTED",
                attempts=1,
                cost_usd_est=1.0,
                concerns=0,
                added=1,
                removed=0,
                link="https://x/pull/2",
                risk="standard",
            ),
            header={},
        )
        return package_phase.PackageResult(state="EXHAUSTED", pr_url="https://x/pull/2")

    def _push_records_2(_outcome, **kwargs):
        push_calls_2.append(kwargs)
        return package_phase.PushResult(pushed=False, note="unused")

    result2 = _run(
        "TE-2",
        102,
        "opens",
        _exhausted_outcome(102, "opens"),
        _package_opens,
        _push_records_2,
    )
    assert push_calls_2 == []
    row2 = next(r for r in _rows(out_dir) if r["spec_id"] == "TE-2")
    assert row2["state"] == "EXHAUSTED"
    assert row2["link"] == "https://x/pull/2"
    assert result2.state == "EXHAUSTED"

    # 3) A raising fake: `run_task` catches it, pushes, and raises nothing.
    push_calls_3: list[dict] = []

    def _package_raises(_outcome, **kwargs):
        raise package_phase.PackageError("gh is unavailable")

    def _push_records_3(_outcome, *, package_refusal=None, **kwargs):
        push_calls_3.append({"package_refusal": package_refusal, **kwargs})
        return package_phase.PushResult(
            pushed=True, branch="saffron/TE-3", pushed_sha="d" * 40, note="pushed"
        )

    result3 = _run(
        "TE-3",
        103,
        "raises",
        _exhausted_outcome(103, "raises"),
        _package_raises,
        _push_records_3,
    )
    assert push_calls_3 and push_calls_3[0]["package_refusal"] == "gh is unavailable"
    row3 = next(r for r in _rows(out_dir) if r["spec_id"] == "TE-3")
    assert row3["state"] == "EXHAUSTED"
    assert row3["link"] == ""
    assert "gh is unavailable" in row3["note"] and "pushed" in row3["note"]
    assert result3.state == "EXHAUSTED"

    # Last: a `READY_FOR_REVIEW` cell's `PackageError` through the same
    # raising fake still raises, and no push runs.
    push_calls_4: list[dict] = []

    def _push_records_4(_outcome, **kwargs):
        push_calls_4.append(kwargs)
        return package_phase.PushResult(pushed=False, note="unused")

    ready_outcome = CellOutcome(
        state="READY_FOR_REVIEW",
        task_id=104,
        run_id=104,
        task_dir=out_dir / "raises-ready",
        spent_usd=1.0,
        attempts=1,
    )

    def _mint_te4(ledger: Ledger) -> None:
        """The raise path's write needs this row (b-dce9a4). The outcome
        here is canned, so nothing else creates it."""
        repo_id = ledger.upsert_repo("r", "o-te4", "m-te4", None)
        run_id = ledger.create_run(repo_id, "a" * 40)
        ledger._db.execute(
            "INSERT INTO tasks "
            "(task_id, run_id, spec_id, spec_sha, state, branch, record_key) "
            "VALUES (104, ?, 'TE-4', ?, 'READY_FOR_REVIEW', 'saffron/TE-4', 'seed-te4')",
            (run_id, "a" * 64),
        )
        ledger._db.commit()

    with pytest.raises(package_phase.PackageError):
        _run(
            "TE-4",
            104,
            "raises-ready",
            ready_outcome,
            _package_raises,
            _push_records_4,
            seed=_mint_te4,
        )
    assert push_calls_4 == []


def test_a_task_bound_for_package_reads_its_state_only_once_package_ends(
    tmp_path, monkeypatch
):
    """b-dce9a4: `run_task` settles a `READY_FOR_REVIEW` row only once
    PACKAGE ends, whichever way it ends. An `EXHAUSTED` row is the cell's
    own last write, and PACKAGE never revises it, whether it returns or
    raises. Every case rolls the task's spend up from its closed attempts."""
    from saffron.task import Handoff

    blocker = Finding(
        lens="correctness",
        severity="blocker",
        file="a.py",
        line=1,
        claim="broken",
        anchored=True,
    )

    # name, spec_id, seed state, exhausted, a return value or a raised
    # one (one of the last two always `None`), the row's final state.
    cases: list[
        tuple[
            str,
            str,
            str,
            bool,
            package_phase.PackageResult | None,
            BaseException | None,
            str,
        ]
    ] = [
        (
            "returns",
            "TE-1",
            "REVIEWING",
            False,
            package_phase.PackageResult(
                state="READY_FOR_REVIEW",
                pr_url="https://x/pull/1",
                pushed_sha="c" * 40,
                branch="saffron/TE-1",
            ),
            None,
            "READY_FOR_REVIEW",
        ),
        (
            "merge-failed",
            "TE-2",
            "REVIEWING",
            False,
            package_phase.PackageResult(state="MERGE_FAILED", branch="saffron/TE-2"),
            None,
            "MERGE_FAILED",
        ),
        (
            "package-error",
            "TE-3",
            "REVIEWING",
            False,
            None,
            package_phase.PackageError("gh is unavailable"),
            "READY_FOR_REVIEW",
        ),
        (
            "keyboard-interrupt",
            "TE-4",
            "REVIEWING",
            False,
            None,
            KeyboardInterrupt(),
            "READY_FOR_REVIEW",
        ),
        (
            "exhausted-returns",
            "TE-5",
            "EXHAUSTED",
            True,
            package_phase.PackageResult(state="EXHAUSTED", note="refused"),
            None,
            "EXHAUSTED",
        ),
        (
            "exhausted-package-error",
            "TE-6",
            "EXHAUSTED",
            True,
            None,
            package_phase.PackageError("gh is unavailable"),
            "EXHAUSTED",
        ),
        (
            "exhausted-runtime-error",
            "TE-7",
            "EXHAUSTED",
            True,
            None,
            RuntimeError("boom"),
            "EXHAUSTED",
        ),
    ]

    for name, spec_id, seed_state, exhausted, result, exc, final_state in cases:
        ledger = Ledger(tmp_path / f"{name}.db")
        repo_id = ledger.upsert_repo("r", f"o-{name}", "/m.git", None)
        run_id = ledger.create_run(repo_id, "a" * 40)
        task_id = ledger.create_task(
            run_id, spec_id, "a" * 64, branch=f"saffron/{spec_id}"
        )
        ledger.set_task_state(task_id, seed_state)
        for cost in (1.0, 2.0):
            attempt_id = ledger.open_attempt(task_id, phase="REVIEW")
            ledger.close_attempt(
                attempt_id,
                session_id="s",
                subtype="success",
                terminal_reason="completed",
                num_turns=1,
                cost_usd_est=cost,
            )

        outcome = CellOutcome(
            state="EXHAUSTED" if exhausted else "READY_FOR_REVIEW",
            task_id=task_id,
            run_id=run_id,
            task_dir=tmp_path / "out" / spec_id,
            spent_usd=3.0,
            attempts=2,
            reviews=[LensReview(lens="correctness", findings=[blocker])]
            if exhausted
            else [],
            rebut_result=None,
        )
        monkeypatch.setattr(
            task_module, "run_one_cell", lambda *a, outcome=outcome, **k: outcome
        )

        def _package(_outcome, *, ledger, spec, repo, result=result, exc=exc, **kwargs):
            if exc is not None:
                raise exc
            assert result is not None
            ledger.set_task_package(
                _outcome.task_id,
                result.state,
                result.branch,
                result.pushed_sha,
                result.pr_url,
                added=result.added,
                removed=result.removed,
            )
            return result

        monkeypatch.setattr(package_phase, "package", _package)
        monkeypatch.setattr(
            package_phase,
            "push_unpackaged_work",
            lambda *a, **k: package_phase.PushResult(pushed=False, note="unused"),
        )

        run_kwargs: dict = dict(
            ceilings=_ceilings(),
            base=_pinned(tmp_path),
            repo_id=repo_id,
            repo=tmp_path / "target-repo",
            ledger=ledger,
            out_dir=tmp_path / "out",
            token=None,
            handoff=Handoff(stacked_on=None, target_branch=None),
        )
        spec = _one_spec(spec_id)

        # EXHAUSTED absorbs its own `PackageError`, as it always did, but a
        # `RuntimeError` reaches no handler either way and still propagates.
        propagates = exc is not None and not (
            exhausted and isinstance(exc, package_phase.PackageError)
        )
        if propagates:
            with pytest.raises(BaseException) as excinfo:
                task_module.run_task(spec, "s" * 40, **run_kwargs)
            assert excinfo.value is exc
        else:
            task_module.run_task(spec, "s" * 40, **run_kwargs)

        (row,) = [r for r in ledger.queue_lines() if r["spec_id"] == spec_id]
        assert row["state"] == final_state
        if not exhausted:
            assert row["spent_usd_est"] == pytest.approx(3.0)
        ledger.close()
