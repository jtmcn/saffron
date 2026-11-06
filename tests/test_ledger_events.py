"""`Ledger._append`'s own event emission (record design §8, backlog item
b-6677b6): every record append also emits a `RecordAppend`, through the
`events` sink `Ledger.__init__` now takes, and no event implies no append.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from saffron import cli
from saffron.agents.findings import Finding, Severity
from saffron.events import RecordAppend, read_log
from saffron.gates.contract import Failure, GateResult
from saffron.ledger import Ledger
from saffron.record.contract import Fact, RecordError
from saffron.record.memory import MemoryRecord
from saffron.record.refs import RefsRecord
from saffron.report.index import QueueLine
from saffron.spec_review import SpecReviewFinding

# One entry per kind `saffron/record/contract.py`'s `KINDS` names that a
# write method appends (SA-0336's notes).
_ALL_KINDS = (
    "task_created",
    "task_state",
    "attempt_opened",
    "attempt_closed",
    "gate_result",
    "finding",
    "rebuttal",
    "task_policy",
    "task_engine",
    "task_push",
    "task_package",
    "task_merged_head",
    "stack_layer",
    "stack_finish",
    "task_regate",
    "spec_review",
    "spec_finding",
    "spec_text",
    "end_review",
    "qualification",
)


class _RecordingRecord(MemoryRecord):
    """A `MemoryRecord` that also keeps every fact it took, across every
    task key, in the order `append` was called. A `refuse` predicate, given
    each fact before `MemoryRecord.append` ever sees it, raises `RecordError`
    for the ones it picks and keeps the rest."""

    def __init__(self, refuse=None) -> None:
        super().__init__()
        self.taken: list[Fact] = []
        self._refuse = refuse or (lambda fact: False)

    def append(self, task_key: str, fact: Fact) -> None:
        if self._refuse(fact):
            raise RecordError(f"refused a {fact.kind!r} fact")
        super().append(task_key, fact)
        self.taken.append(fact)


def _key(ledger: Ledger, task_id: int) -> str:
    key = ledger.record_key(task_id)
    assert key is not None
    return key


def _fail(file: str, code: str, line: int, msg: str) -> Failure:
    return Failure(file=file, code=code, message=msg, line=line)


def _gate(gate: str, tool: str, *fails: Failure) -> GateResult:
    return GateResult(
        gate=gate,
        status="fail",
        tool=tool,
        duration_ms=1,
        summary="x",
        failures=list(fails),
    )


def _find(
    lens: str, sev: Severity, file: str, line: int, claim: str, anchored: bool = True
) -> Finding:
    return Finding(
        lens=lens, severity=sev, file=file, line=line, claim=claim, anchored=anchored
    )


def _drive_every_kind(ledger: Ledger) -> tuple[str, str, int]:
    """Every one of the twenty fact kinds the ledger appends, across two
    tasks under two spec ids in one batch. Both tasks are created first,
    then a fact lands on the first task. A spec id read from the newest
    task, rather than the fact's own, would then name the wrong one.
    Returns `(key1, key2, batch_id)`."""
    repo_id = ledger.upsert_repo("saffron", "https://o", "/m.git", policy_sha="p" * 64)
    batch_id = ledger.create_batch(budget_usd=20.0)
    run1 = ledger.create_run(repo_id, base_sha="a" * 40, batch_id=batch_id)
    run2 = ledger.create_run(repo_id, base_sha="a" * 40, batch_id=batch_id)

    task1 = ledger.create_task(run1, spec_id="SA-1", spec_sha="s" * 64, branch="b1")
    task2 = ledger.create_task(run2, spec_id="SA-2", spec_sha="s" * 64, branch="b2")

    # A first-task fact, after the second task's own `task_created`.
    ledger.set_task_state(task1, "IMPLEMENTING")

    a1 = ledger.open_attempt(task1, phase="IMPLEMENT")
    gate = _gate("lint", "ruff", _fail("a.py", "E1", 3, "m1"))
    ledger.record_gate_result(gate, attempt_id=a1, earned_risk="standard")
    ledger.close_attempt(
        a1,
        session_id="s1",
        model="m1",
        subtype="success",
        terminal_reason="done",
        num_turns=5,
        cost_usd_est=1.0,
        cost_floor_usd_est=0.1,
    )

    f1, _f2 = ledger.record_findings(
        task1,
        [
            _find("lens-a", "blocker", "x.py", 1, "claim one"),
            _find("lens-b", "note", "y.py", 2, "claim two", False),
        ],
    )
    ledger.record_rebuttal(f1, verdict="confirmed", rebuttal="r1")

    ledger.record_policy(task1, "c" * 64)
    ledger.record_engine(task1, "e" * 40)
    ledger.record_push(task1, "d" * 40)
    ledger.set_task_package(
        task1, "READY_FOR_REVIEW", "pkg", "e" * 40, "https://x/9", added=3, removed=1
    )
    ledger.record_merged_head(task1, "h" * 40)

    ledger.record_stack_layer(task1, position=1, predecessor_task_id=None, generation=1)
    ledger.record_end_review(
        task1, lens="l1", status="reviewed", cost_usd=1.0, error=None
    )
    ledger.record_qualification(
        task1,
        finding=_find("l1", "blocker", "a.py", 1, "c1"),
        filed="blocker",
        outcome="kept",
        reason="r",
    )
    ledger.record_spec_review(
        task1,
        route="run",
        block="b" * 10,
        block_sha256="c" * 64,
        error=None,
        findings=[
            SpecReviewFinding(
                severity="blocker",
                claim="x",
                fixes=None,
                criterion=1,
                file=None,
                line=None,
            )
        ],
    )
    ledger.record_spec_text(
        task1,
        origin="revision",
        spec_id="SA-1",
        path=".saffron/specs/SA-1-foo.md",
        text="hello",
    )
    ledger.record_stack_finish(
        batch_id, branch="saffron/SA-2", head_sha="d" * 40, pr_url=None
    )
    ledger.record_regate(
        task1, head_sha="h" * 40, baseline_sha="a" * 40, new_failures=0
    )

    return _key(ledger, task1), _key(ledger, task2), batch_id


def test_each_fact_the_ledger_appends_emits_one_event_naming_its_kind_and_key(
    tmp_path: Path,
) -> None:
    record = _RecordingRecord()
    calls: list[tuple[RecordAppend, int]] = []

    def sink(event: RecordAppend) -> None:
        calls.append((event, len(record.taken)))

    ledger = Ledger(tmp_path / "l.db", record=record, events=sink)
    key1, key2, _batch_id = _drive_every_kind(ledger)
    spec_of = {key1: "SA-1", key2: "SA-2"}

    facts = record.taken
    assert len(calls) == len(facts)
    # Event n saw exactly n facts: it follows its own fact and precedes the
    # next.
    for i, (event, count_at_call) in enumerate(calls):
        assert count_at_call == i + 1
        assert event.task_key == facts[i].task_key
        assert event.fact_kind == facts[i].kind
        assert event.spec_id == spec_of[event.task_key]

    assert {f.kind for f in facts} == set(_ALL_KINDS)

    # Every fact `_drive_every_kind` writes lands, every one, and twice
    # for `task_created` and `finding`.
    assert len(facts) == 22
    finding_claims = [f.payload["claim"] for f in facts if f.kind == "finding"]
    assert finding_claims == ["claim one", "claim two"]
    assert len([f for f in facts if f.kind == "spec_finding"]) == 1

    # The first task's fact lands strictly after the second task's own
    # `task_created`.
    task_created_at = [i for i, f in enumerate(facts) if f.kind == "task_created"]
    assert len(task_created_at) == 2
    second_created = task_created_at[1]
    assert any(i > second_created and f.task_key == key1 for i, f in enumerate(facts))
    ledger.close()


def test_an_append_the_record_refuses_emits_no_event(tmp_path: Path) -> None:
    # The `_commit_and_append` path: a refused `task_state` emits nothing,
    # though the `task_created` before it did.
    captured_a: list[RecordAppend] = []
    refuse_state = _RecordingRecord(lambda fact: fact.kind == "task_state")
    ledger_a = Ledger(tmp_path / "a.db", record=refuse_state, events=captured_a.append)
    repo_id = ledger_a.upsert_repo(
        "saffron", "https://a", "/ma.git", policy_sha="p" * 64
    )
    run_id = ledger_a.create_run(repo_id, base_sha="a" * 40)
    task_id = ledger_a.create_task(
        run_id, spec_id="SA-1", spec_sha="s" * 64, branch="b"
    )
    assert len(captured_a) == 1
    with pytest.raises(RecordError):
        ledger_a.set_task_state(task_id, "IMPLEMENTING")
    assert len(captured_a) == 1
    ledger_a.close()

    # `record_findings`' own per-fact loop: its second fact refused, its
    # first fact still took and still emitted.
    captured_b: list[RecordAppend] = []
    seen = {"findings": 0}

    def _refuse_second_finding(fact: Fact) -> bool:
        if fact.kind != "finding":
            return False
        seen["findings"] += 1
        return seen["findings"] == 2

    refuse_finding = _RecordingRecord(_refuse_second_finding)
    ledger_b = Ledger(
        tmp_path / "b.db", record=refuse_finding, events=captured_b.append
    )
    repo_id_b = ledger_b.upsert_repo(
        "saffron", "https://b", "/mb.git", policy_sha="p" * 64
    )
    run_id_b = ledger_b.create_run(repo_id_b, base_sha="a" * 40)
    task_id_b = ledger_b.create_task(
        run_id_b, spec_id="SA-2", spec_sha="s" * 64, branch="b"
    )
    before = len(captured_b)
    with pytest.raises(RecordError):
        ledger_b.record_findings(
            task_id_b,
            [
                _find("lens-a", "blocker", "x.py", 1, "claim one"),
                _find("lens-b", "note", "y.py", 2, "claim two", False),
            ],
        )
    added = captured_b[before:]
    assert len(added) == 1
    assert added[0].fact_kind == "finding"
    # The taken fact is the first finding passed, named by its own claim,
    # never the second one a reordered loop would take instead.
    assert refuse_finding.taken[-1].payload["claim"] == "claim one"
    ledger_b.close()


def test_a_ledger_with_no_record_emits_no_event(tmp_path: Path) -> None:
    no_record_events: list[RecordAppend] = []
    ledger_no_record = Ledger(tmp_path / "no-record.db", events=no_record_events.append)
    _drive_every_kind(ledger_no_record)
    assert no_record_events == []
    ledger_no_record.close()

    # Proof the drive does reach all twenty kinds: the same drive, on a
    # ledger with a record, fills the sink with every one of them.
    with_record_events: list[RecordAppend] = []
    ledger_with_record = Ledger(
        tmp_path / "with-record.db",
        record=MemoryRecord(),
        events=with_record_events.append,
    )
    _drive_every_kind(ledger_with_record)
    assert {e.fact_kind for e in with_record_events} == set(_ALL_KINDS)
    ledger_with_record.close()


def test_main_writes_each_append_event_to_its_own_tasks_log(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    mirror = tmp_path / "mirror.git"
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(mirror)], check=True)
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    home = tmp_path / "home"

    seed = Ledger(home / "ledger.db")
    seed.upsert_repo("demo", str(origin), str(mirror), policy_sha=None)
    seed.close()

    created: dict[str, tuple[str, str]] = {}

    def _cell_stub(args: object, ledger: Ledger, out_dir: Path) -> int:
        repo_id = ledger.resolve_repo_id(str(origin))
        assert repo_id is not None
        run_id = ledger.create_run(repo_id, base_sha="a" * 40)
        task1 = ledger.create_task(
            run_id, spec_id="SA-9001", spec_sha="s" * 64, branch="b1"
        )
        task2 = ledger.create_task(
            run_id, spec_id="SA-9002", spec_sha="s" * 64, branch="b2"
        )
        # Both tasks created before either gets a fact of its own.
        ledger.set_task_state(task1, "READY_FOR_REVIEW")
        created["cell"] = (_key(ledger, task1), _key(ledger, task2))
        return 0

    def _replay_stub(
        repo_dir: Path,
        pr_number: int,
        *,
        ledger: Ledger,
        out_dir: Path,
        mirrors_dir: Path,
        spec_path: Path | None,
        timeout_s: float,
    ) -> QueueLine:
        repo_id = ledger.resolve_repo_id(str(origin))
        assert repo_id is not None
        run_id = ledger.create_run(repo_id, base_sha="b" * 40)
        task3 = ledger.create_task(
            run_id, spec_id="SA-9003", spec_sha="s" * 64, branch="b3"
        )
        task4 = ledger.create_task(
            run_id, spec_id="SA-9004", spec_sha="s" * 64, branch="b4"
        )
        ledger.set_task_state(task3, "READY_FOR_REVIEW")
        created["replay"] = (_key(ledger, task3), _key(ledger, task4))
        return QueueLine(
            repo="demo",
            spec_id="SA-9003",
            state="READY_FOR_REVIEW",
            attempts=1,
            cost_usd_est=0.0,
            concerns=0,
            added=0,
            removed=0,
            link="",
            note="",
        )

    monkeypatch.setattr(cli, "_run_cell", _cell_stub)
    monkeypatch.setattr(cli, "replay", _replay_stub)

    spec_file = tmp_path / "SA-9001.md"
    spec_file.write_text("never read: `_run_cell` is stubbed")
    assert cli.main(["--home", str(home), "cell", str(spec_file)]) == 0

    out_dir_default = home / "batches" / "v0"
    key1, key2 = created["cell"]
    facts1 = RefsRecord(mirror).read(key1)
    facts2 = RefsRecord(mirror).read(key2)
    events1 = [
        e for e in read_log(out_dir_default / "SA-9001") if isinstance(e, RecordAppend)
    ]
    events2 = [
        e for e in read_log(out_dir_default / "SA-9002") if isinstance(e, RecordAppend)
    ]
    assert events1 and events2
    assert [e.fact_kind for e in events1] == [f.kind for f in facts1]
    assert [e.fact_kind for e in events2] == [f.kind for f in facts2]
    assert all(e.task_key == key1 for e in events1)
    assert all(e.task_key == key2 for e in events2)
    assert not any(e.task_key == key2 for e in events1)
    assert not any(e.task_key == key1 for e in events2)

    out_dir_replay = tmp_path / "out-replay"
    assert (
        cli.main(
            [
                "--home",
                str(home),
                "replay",
                str(tmp_path),
                "7",
                "--out",
                str(out_dir_replay),
            ]
        )
        == 0
    )

    key3, key4 = created["replay"]
    facts3 = RefsRecord(mirror).read(key3)
    facts4 = RefsRecord(mirror).read(key4)
    events3 = [
        e for e in read_log(out_dir_replay / "SA-9003") if isinstance(e, RecordAppend)
    ]
    events4 = [
        e for e in read_log(out_dir_replay / "SA-9004") if isinstance(e, RecordAppend)
    ]
    assert events3 and events4
    assert [e.fact_kind for e in events3] == [f.kind for f in facts3]
    assert [e.fact_kind for e in events4] == [f.kind for f in facts4]
    assert all(e.task_key == key3 for e in events3)
    assert all(e.task_key == key4 for e in events4)
    assert not any(e.task_key == key4 for e in events3)
    assert not any(e.task_key == key3 for e in events4)
