import subprocess
from dataclasses import replace

import pytest

from saffron import cli
from saffron.agents.findings import Finding
from saffron.cell.session import CellSpec, previous_cut_orphan, row_is_orphaned_cut
from saffron.gates.contract import Failure, GateResult
from saffron.ledger import Ledger
from saffron.record.contract import Fact
from saffron.record.fold import UnreadableTask, fold
from saffron.record.memory import MemoryRecord
from saffron.record.refs import RefsRecord


@pytest.fixture
def record():
    return MemoryRecord()


def a_night(tmp_path, record):
    """One task through every write a real one makes: creation, an attempt, a
    gate result, a state, a policy, a finding and its rebuttal, a push, a
    package and a merged head."""
    source = Ledger(tmp_path / "source.db", record=record)
    repo_id = source.upsert_repo("saffron", "/o", "/m.git", policy_sha="p" * 64)
    run_id = source.create_run(repo_id, base_sha="a" * 40)
    task_id = source.create_task(
        run_id,
        spec_id="SA-0099",
        spec_sha="s" * 64,
        branch="saffron/SA-0099",
        risk="elevated",
        budget_usd=12,
    )
    attempt_id = source.open_attempt(task_id, phase="IMPLEMENTING")
    source.record_gate_result(
        GateResult(
            gate="lint",
            status="pass",
            tool="ruff 0.6.0",
            duration_ms=9,
            summary="clean",
        ),
        attempt_id=attempt_id,
    )
    source.close_attempt(
        attempt_id,
        session_id="s",
        subtype="success",
        terminal_reason=None,
        num_turns=4,
        cost_usd_est=1.25,
    )
    source.set_task_state(task_id, "READY_FOR_REVIEW")
    source.record_policy(task_id, "c" * 64)
    finding_id = source.record_findings(
        task_id,
        [
            Finding(
                lens="adequacy",
                severity="blocker",
                file="saffron/task.py",
                line=3,
                claim="no witness guards the new branch",
                anchored=True,
            )
        ],
    )[0]
    source.record_rebuttal(finding_id, verdict="withdrawn", rebuttal="fair")
    source.record_push(task_id, "d" * 40)
    source.set_task_package(
        task_id, "READY_FOR_REVIEW", "saffron/SA-0099", "d" * 40, "https://x/1"
    )
    source.record_merged_head(task_id, "e" * 40)
    return source


def rows(ledger):
    """Every row that describes the night, with the autoincrement ids left
    out — the fold mints those, so they are not what has to match. The columns
    `queue_lines` and `reconcile` read are in here deliberately: a criterion
    that excludes them cannot show the fold dropping them."""
    tasks = [
        dict(r)
        for r in ledger._db.execute(
            "SELECT spec_id, spec_sha, state, risk, branch, budget_usd,"
            "       spent_usd_est, record_key, pushed_sha, pr_url, policy_sha,"
            "       merged_head_sha FROM tasks ORDER BY record_key"
        )
    ]
    attempts = [
        dict(r)
        for r in ledger._db.execute(
            "SELECT phase, n, session_id, subtype, num_turns, cost_usd_est"
            "  FROM attempts ORDER BY phase, n"
        )
    ]
    gates = [
        dict(r)
        for r in ledger._db.execute(
            "SELECT gate, status, tool, summary FROM gate_results ORDER BY gate"
        )
    ]
    found = [
        dict(r)
        for r in ledger._db.execute(
            "SELECT lens, severity, file, line, claim, anchored, verdict,"
            "       rebuttal FROM findings ORDER BY finding_id"
        )
    ]
    return tasks, attempts, gates, found


def test_folding_an_empty_record_makes_no_rows(tmp_path, record):
    into = Ledger(tmp_path / "into.db")
    assert fold(record, into).folded == 0
    assert rows(into)[0] == []
    into.close()


def test_the_fold_reproduces_the_task(tmp_path, record):
    source = a_night(tmp_path, record)
    into = Ledger(tmp_path / "into.db")
    assert fold(record, into).folded == 1
    assert rows(into)[0] == rows(source)[0]
    source.close()
    into.close()


def test_the_fold_reproduces_attempts_and_gate_results(tmp_path, record):
    source = a_night(tmp_path, record)
    into = Ledger(tmp_path / "into.db")
    fold(record, into)
    _, attempts, gates, found = rows(into)
    _, want_attempts, want_gates, want_found = rows(source)
    assert attempts == want_attempts
    assert gates == want_gates
    assert found == want_found
    source.close()
    into.close()


def test_delete_the_ledger_rebuild_it_and_get_the_same_rows(tmp_path, record):
    # Spec §4's acceptance criterion, and the reason the ledger may be deleted
    # at any time.
    source = a_night(tmp_path, record)
    first = Ledger(tmp_path / "a.db")
    fold(record, first)
    want = rows(first)
    first.close()
    (tmp_path / "a.db").unlink()

    second = Ledger(tmp_path / "a.db")
    fold(record, second)
    assert rows(second) == want
    second.close()
    source.close()


def test_folding_twice_into_one_ledger_does_not_double_the_rows(tmp_path, record):
    # The fold is an upsert keyed on `record_key`, not an append: a rebuild
    # that runs twice must be indistinguishable from one that ran once.
    source = a_night(tmp_path, record)
    into = Ledger(tmp_path / "into.db")
    fold(record, into)
    once = rows(into)
    fold(record, into)
    assert rows(into) == once
    source.close()
    into.close()


def test_the_fold_keeps_each_attempts_cost_floor(tmp_path, record):
    """`Ledger.close_attempt` takes `cost_floor_usd_est`, `None` by default,
    and carries it on the `attempt_closed` fact into
    `attempts.cost_floor_usd_est`. A fold reproduces it. A fact written
    before this change carries no such key, and folds to null rather than
    raising (SA-0206, backlog b-209696)."""
    source = Ledger(tmp_path / "source.db", record=record)
    repo_id = source.upsert_repo("saffron", "/o", "/m.git", policy_sha="p")
    run_id = source.create_run(repo_id, base_sha="a" * 40)
    task_id = source.create_task(
        run_id, spec_id="SA-0099", spec_sha="s" * 64, branch="b"
    )

    a1 = source.open_attempt(task_id)
    source.close_attempt(
        a1,
        session_id="s1",
        subtype="success",
        terminal_reason=None,
        num_turns=1,
        cost_usd_est=0.1,
        cost_floor_usd_est=0.4,
    )
    a2 = source.open_attempt(task_id)
    source.close_attempt(
        a2,
        session_id="s2",
        subtype="success",
        terminal_reason=None,
        num_turns=1,
        cost_usd_est=0.0,
        cost_floor_usd_est=0.0,
    )
    a3 = source.open_attempt(task_id)
    source.close_attempt(
        a3,
        session_id="s3",
        subtype="success",
        terminal_reason=None,
        num_turns=1,
        cost_usd_est=0.0,
    )
    # A fourth attempt, closed by a fact built the way one was before this
    # change: no `cost_floor_usd_est` key at all, not even a null one.
    a4 = source.open_attempt(task_id)
    owner = source._attempt_of(a4, "close")
    legacy = source._build_fact(
        task_id,
        "attempt_closed",
        {
            "phase": owner["phase"],
            "n": owner["n"],
            "session_id": "s4",
            "model": None,
            "subtype": "success",
            "terminal_reason": None,
            "num_turns": 1,
            "cost_usd_est": 0.05,
        },
    )
    source._commit_and_append(legacy)

    into = Ledger(tmp_path / "into.db")
    fold(record, into)

    def _floors(ledger):
        return [r["cost_floor_usd_est"] for r in ledger.attempts(task_id)]

    assert _floors(source) == [0.4, 0.0, None, None]
    assert _floors(into) == [0.4, 0.0, None, None]
    source.close()
    into.close()


def test_the_fold_keeps_new_failures_the_head_count_and_the_tier(tmp_path, record):
    """`record_gate_result`'s `failures_at_head` and `earned_risk` are carried
    on the `gate_result` fact and fold back exactly. A fact written before
    this change carries neither key. Folding it leaves whatever tier an
    earlier fact on the same attempt already gave it (item 170)."""
    source = Ledger(tmp_path / "source.db", record=record)
    repo_id = source.upsert_repo("saffron", "/o", "/m.git", policy_sha="p")
    run_id = source.create_run(repo_id, base_sha="a" * 40)
    task_id = source.create_task(
        run_id, spec_id="SA-0099", spec_sha="s" * 64, branch="b"
    )

    a1 = source.open_attempt(task_id)
    source.record_gate_result(
        GateResult(
            gate="lint",
            status="fail",
            failures=[Failure(file="a.py", code="E1", message="boom", line=1)],
        ),
        attempt_id=a1,
        earned_risk="standard",
    )
    a2 = source.open_attempt(task_id)
    source.record_gate_result(
        GateResult(
            gate="lint",
            status="fail",
            failures=[Failure(file="b.py", code="E2", message="bang", line=2)],
        ),
        attempt_id=a2,
        earned_risk="elevated",
    )

    # A second, stale fact against `a1`, the shape every pre-change fact has.
    # It follows `a1`'s real fact, so a fold must not let it clear the tier.
    key = source.record_key(task_id)
    facts = record.read(key)
    first_gate_result = next(i for i, f in enumerate(facts) if f.kind == "gate_result")
    stale_payload = dict(facts[first_gate_result].payload)
    stale_payload["gate"] = "types"
    stale_payload["failures"] = []
    del stale_payload["failures_at_head"]
    del stale_payload["earned_risk"]
    stale = replace(facts[first_gate_result], payload=stale_payload)
    record.append(key, stale)

    into = Ledger(tmp_path / "into.db")
    fold(record, into)

    def _counts(ledger, attempt_id):
        return [
            r["failures_at_head"]
            for r in ledger._db.execute(
                "SELECT failures_at_head FROM gate_results "
                "WHERE attempt_id = ? ORDER BY gate_result_id",
                (attempt_id,),
            )
        ]

    def _earned_risk(ledger, attempt_id):
        return ledger._db.execute(
            "SELECT earned_risk FROM attempts WHERE attempt_id = ?", (attempt_id,)
        ).fetchone()["earned_risk"]

    # `a1` keeps the tier its first, real fact gave it: the second, stale
    # fact carries no `earned_risk` key, and must not clear it.
    assert _counts(into, a1) == [1, None]
    assert _earned_risk(into, a1) == "standard"
    assert _counts(into, a2) == [1]
    assert _earned_risk(into, a2) == "elevated"
    source.close()
    into.close()


def test_the_fold_keeps_error_and_fail_apart(tmp_path, record):
    source = Ledger(tmp_path / "source.db", record=record)
    repo_id = source.upsert_repo("saffron", "/o", "/m.git", policy_sha="p")
    run_id = source.create_run(repo_id, base_sha="a" * 40)
    task_id = source.create_task(
        run_id,
        spec_id="SA-0099",
        spec_sha="s" * 64,
        branch="b",
    )
    attempt_id = source.open_attempt(task_id)
    for status in ("error", "fail"):
        source.record_gate_result(
            GateResult(
                gate=f"g-{status}",
                status=status,
                tool="t",
                duration_ms=1,
                summary=status,
            ),
            attempt_id=attempt_id,
        )
    into = Ledger(tmp_path / "into.db")
    fold(record, into)
    assert [g["status"] for g in rows(into)[2]] == ["error", "fail"]
    source.close()
    into.close()


def test_an_unreadable_task_names_itself_and_folds_the_rest(tmp_path, record):
    # A record one task cannot be read from must still produce a ledger of
    # the others, or one bad task costs a whole night's page.
    a_night(tmp_path, record)
    borrowed = record.read(record.task_keys()[0])[0]
    record.append("f" * 32, replace(borrowed, task_key="f" * 32))
    record._facts["f" * 32] = ["not a fact"]
    into = Ledger(tmp_path / "into.db")
    with pytest.raises(UnreadableTask, match="f" * 32):
        fold(record, into, strict=True)
    assert fold(record, into, strict=False).folded == 1
    into.close()


def test_a_rebuttal_with_no_finding_fact_raises_under_strict(tmp_path, record):
    # A rebuttal naming no finding fact makes its whole task unreadable.
    a_night(tmp_path, record).close()
    key = record.task_keys()[0]
    record._facts[key] = [f for f in record._facts[key] if f.kind != "finding"]
    into = Ledger(tmp_path / "into.db")
    with pytest.raises(UnreadableTask, match="rebuttal"):
        fold(record, into, strict=True)
    result = fold(record, into, strict=False)
    assert result.folded == 0
    assert [k for k, _ in result.skipped] == [key]
    into.close()


def _read(ledger, query):
    return [tuple(r) for r in ledger._db.execute(query)]


def _retimed(fact, key, at, spec_id):
    payload = dict(fact.payload)
    if fact.kind == "task_created":
        payload["spec_id"] = spec_id
    return replace(fact, task_key=key, at=at, payload=payload)


def test_the_fold_restores_the_times_the_facts_carry(tmp_path, record):
    # `projection` ties a task to its ceiling span by `runs.started_at`, so a
    # ledger carrying the fold's own clock ties every task to one instant.
    a_night(tmp_path, record).close()
    key = record.task_keys()[0]
    record._facts[key] = [
        replace(f, at="2026-09-19T01:02:03+00:00") for f in record._facts[key]
    ]
    into = Ledger(tmp_path / "into.db")
    fold(record, into)
    assert _read(into, "SELECT started_at FROM runs") == [("2026-09-19 01:02:03",)]
    assert _read(into, "SELECT started_at, ended_at FROM attempts") == [
        ("2026-09-19 01:02:03", "2026-09-19 01:02:03")
    ]
    assert _read(into, "SELECT updated_at FROM tasks") == [("2026-09-19 01:02:03",)]
    into.close()


def test_tasks_are_folded_oldest_first(tmp_path, record):
    # `ORDER BY t.task_id` is read as a chronology, and a record key is random
    # hex — so the key sorting first here is the task that happened second.
    a_night(tmp_path, record).close()
    facts = record.read(record.task_keys()[0])
    record._facts.clear()
    for key, at, spec_id in (
        ("a" * 32, "2026-09-19T09:00:00+00:00", "SA-0002"),
        ("b" * 32, "2026-09-18T09:00:00+00:00", "SA-0001"),
    ):
        record._facts[key] = [_retimed(f, key, at, spec_id) for f in facts]
    into = Ledger(tmp_path / "into.db")
    assert fold(record, into).folded == 2
    assert _read(into, "SELECT spec_id FROM tasks ORDER BY task_id") == [
        ("SA-0001",),
        ("SA-0002",),
    ]
    into.close()


def test_a_task_git_cannot_read_is_skipped_and_the_rest_fold(tmp_path, record):
    # The likeliest unreadable task there is: a fact object git no longer has.
    # `RefsRecord.read` raises `RecordError`, which no named tuple lists.
    repo = tmp_path / "record.git"
    subprocess.run(["git", "init", "-q", "--bare", str(repo)], check=True)
    on_refs = RefsRecord(repo)
    a_night(tmp_path, on_refs).close()
    a_night(tmp_path, on_refs).close()
    broken, whole = sorted(on_refs.task_keys())
    blob = on_refs._blobs(broken)[0][1]
    (repo / "objects" / blob[:2] / blob[2:]).unlink()

    into = Ledger(tmp_path / "into.db")
    with pytest.raises(UnreadableTask, match=broken):
        fold(on_refs, into, strict=True)
    assert fold(on_refs, into, strict=False).folded == 1
    assert _read(into, "SELECT record_key FROM tasks") == [(whole,)]
    into.close()


def _with_unplaceable_kind(record):
    """A `decision` fact, one of the seven kinds `_apply` never places,
    appended after a task's own facts."""
    key = record.task_keys()[0]
    record.append(
        key,
        Fact(kind="decision", task_key=key, at="2026-09-19T00:00:00+00:00", repo="s"),
    )
    return key


def test_a_task_that_fails_mid_replay_leaves_no_rows_behind(tmp_path, record):
    # `fold_task` commits once for the whole task, so a fact it cannot
    # place leaves the ledger holding nothing for that task.
    a_night(tmp_path, record).close()
    _with_unplaceable_kind(record)
    into = Ledger(tmp_path / "into.db")
    with pytest.raises(ValueError, match="decision"):
        fold(record, into, strict=True)
    assert _read(into, "SELECT COUNT(*) FROM tasks") == [(0,)]
    assert _read(into, "SELECT COUNT(*) FROM attempts") == [(0,)]
    assert _read(into, "SELECT COUNT(*) FROM gate_results") == [(0,)]
    into.close()


def test_a_replay_that_breaks_is_not_skipped_as_unreadable(tmp_path, record):
    # A fold that cannot place a kind is the fold's own defect, and
    # charging it to the record drops the task and still exits 0.
    a_night(tmp_path, record).close()
    _with_unplaceable_kind(record)
    into = Ledger(tmp_path / "into.db")
    with pytest.raises(ValueError, match="decision"):
        fold(record, into, strict=False)
    into.close()


def test_a_log_with_no_creation_fact_says_what_is_missing(tmp_path, record):
    # `next` over an empty generator raises `StopIteration`, which stringifies
    # to nothing, so strict reported "is unreadable: " and named no reason.
    a_night(tmp_path, record).close()
    key = record.task_keys()[0]
    record._facts[key] = [f for f in record._facts[key] if f.kind != "task_created"]
    into = Ledger(tmp_path / "into.db")
    with pytest.raises(UnreadableTask, match="no task_created fact"):
        fold(record, into, strict=True)
    assert fold(record, into, strict=False).skipped == [
        (key, "ValueError: no task_created fact")
    ]
    into.close()


def test_a_task_that_pushed_without_packaging_keeps_its_sha(tmp_path, record):
    # `record_push` runs where no pull request follows and `reconcile` reads
    # `pushed_sha`, so the push fact is not the package's saying the same thing.
    source = Ledger(tmp_path / "source.db", record=record)
    repo_id = source.upsert_repo("saffron", "/o", "/m.git", policy_sha="p")
    run_id = source.create_run(repo_id, base_sha="a" * 40)
    task_id = source.create_task(
        run_id, spec_id="SA-0099", spec_sha="s" * 64, branch="b"
    )
    source.record_push(task_id, "d" * 40)
    source.set_task_state(task_id, "MERGE_FAILED")
    into = Ledger(tmp_path / "into.db")
    fold(record, into)
    assert _read(into, "SELECT state, pushed_sha, pr_url FROM tasks") == [
        ("MERGE_FAILED", "d" * 40, None)
    ]
    source.close()
    into.close()


def test_the_fold_command_exits_nonzero_when_it_skipped_a_task(tmp_path, capsys):
    # Exit codes are load-bearing, and a ledger short of tasks is not the
    # ledger back: "folded 1 tasks" over exit 0 reads as a whole rebuild.
    repo = tmp_path / "record.git"
    subprocess.run(["git", "init", "-q", "--bare", str(repo)], check=True)
    on_refs = RefsRecord(repo)
    a_night(tmp_path, on_refs).close()
    a_night(tmp_path, on_refs).close()
    broken = sorted(on_refs.task_keys())[0]
    blob = on_refs._blobs(broken)[0][1]
    (repo / "objects" / blob[:2] / blob[2:]).unlink()

    exit_code = cli.main(
        [
            "--home",
            str(tmp_path / "home"),
            "fold",
            "--repo",
            str(repo),
            "--into",
            str(tmp_path / "into.db"),
            "--skip-unreadable",
        ]
    )
    assert exit_code == 1
    printed = capsys.readouterr().out
    assert f"skipped task {broken}" in printed
    assert "skipped 1" in printed


def _a_repo_with_one_broken_task(tmp_path):
    """Two tasks on real refs, one of them missing a fact object git had."""
    repo = tmp_path / "record.git"
    subprocess.run(["git", "init", "-q", "--bare", str(repo)], check=True)
    on_refs = RefsRecord(repo)
    a_night(tmp_path, on_refs).close()
    a_night(tmp_path, on_refs).close()
    broken = sorted(on_refs.task_keys())[0]
    blob = on_refs._blobs(broken)[0][1]
    (repo / "objects" / blob[:2] / blob[2:]).unlink()
    return repo, broken


def test_one_unreadable_record_exits_one_in_either_mode(tmp_path, capsys):
    # The flag changes how much is folded, never what went wrong. Exit 2 is
    # infrastructure, and a record git cannot read is not that.
    repo, broken = _a_repo_with_one_broken_task(tmp_path)
    argv = [
        "--home",
        str(tmp_path / "home"),
        "fold",
        "--repo",
        str(repo),
        "--into",
        str(tmp_path / "into.db"),
    ]
    assert cli.main(argv) == 1
    assert broken in capsys.readouterr().out
    assert cli.main([*argv, "--skip-unreadable"]) == 1


def test_a_fold_that_breaks_still_exits_two(tmp_path, record, monkeypatch):
    # The other half of the split: the fold's own defect stays infrastructure.
    a_night(tmp_path, record).close()
    monkeypatch.setattr(
        "saffron.cli.RefsRecord", lambda *a, **k: _Exploding(), raising=True
    )
    exit_code = cli.main(
        [
            "--home",
            str(tmp_path / "home"),
            "fold",
            "--repo",
            str(tmp_path),
            "--into",
            str(tmp_path / "into.db"),
        ]
    )
    assert exit_code == 2


class _Exploding:
    def task_keys(self):
        raise RuntimeError("the backend is broken")


def test_folding_never_opens_the_home_ledger(tmp_path):
    # `--into` names the ledger to rebuild. Opening the home one to reach the
    # dispatch created the file the flag exists to keep a fold away from.
    repo, _ = _a_repo_with_one_broken_task(tmp_path)
    home = tmp_path / "home"
    cli.main(
        [
            "--home",
            str(home),
            "fold",
            "--repo",
            str(repo),
            "--into",
            str(tmp_path / "into.db"),
            "--skip-unreadable",
        ]
    )
    assert not (home / "ledger.db").exists()


def test_a_fold_leaves_a_policy_it_cannot_reproduce(tmp_path, record):
    # `repos.policy_sha` is nobody's fact, so the fold upserts `None`. Into a
    # surviving ledger that cleared a column the record cannot restore.
    source = a_night(tmp_path, record)
    assert _read(source, "SELECT policy_sha FROM repos") == [("p" * 64,)]
    fold(record, source)
    assert _read(source, "SELECT policy_sha FROM repos") == [("p" * 64,)]
    source.close()


def _cut(ledger, repo_id, spec_id, spec_sha, status):
    """One pass of SA-0126's re-queue cap: a task cut at `IMPLEMENTING`,
    its row finished with `status`, skipped for a cell that died in flight."""
    run_id = ledger.create_run(repo_id, base_sha="a" * 40)
    task_id = ledger.create_task(
        run_id, spec_id=spec_id, spec_sha=spec_sha, branch=f"b{status}"
    )
    ledger.set_task_state(task_id, "IMPLEMENTING")
    attempt_id = ledger.open_attempt(task_id, phase="IMPLEMENTING")
    ledger.close_attempt(
        attempt_id,
        session_id="s",
        subtype="success",
        terminal_reason="done",
        num_turns=1,
        cost_usd_est=0.1,
    )
    ledger.set_task_state(task_id, "ORPHANED")
    if status is not None:
        ledger.finish_run(run_id, status)
    return task_id


def _task_id_by_key(ledger, key):
    row = ledger._db.execute(
        "SELECT task_id FROM tasks WHERE record_key = ?", (key,)
    ).fetchone()
    return int(row["task_id"])


def _run_shape(ledger, task_id):
    """A row's status and whether it has an `ended_at`, read through the
    task that holds it."""
    row = ledger._db.execute(
        "SELECT rn.status AS status, rn.ended_at AS ended_at"
        "  FROM tasks t JOIN runs rn ON rn.run_id = t.run_id"
        " WHERE t.task_id = ?",
        (task_id,),
    ).fetchone()
    return (row["status"], row["ended_at"] is not None)


def test_a_folded_ledger_finds_the_earlier_cut_by_its_runs_own_status(tmp_path, record):
    source = Ledger(tmp_path / "source.db", record=record)
    repo_id = source.upsert_repo("saffron", "/o", "/m.git", policy_sha="p" * 64)
    spec_id, spec_sha = "SA-0126", "s" * 64

    running = _cut(source, repo_id, spec_id, spec_sha, None)
    complete = _cut(source, repo_id, spec_id, spec_sha, "COMPLETE")
    aborted = _cut(source, repo_id, spec_id, spec_sha, "ABORTED")
    keys = [source.record_key(t) for t in (running, complete, aborted)]

    live = [_run_shape(source, t) for t in (running, complete, aborted)]
    assert live == [("RUNNING", False), ("COMPLETE", True), ("ABORTED", True)]

    # Each ended row's `run_finished` fact, retimed to its own past minute,
    # oldest first.
    for i, key in enumerate(keys[1:], start=1):
        record._facts[key] = [
            replace(f, at=f"2026-09-19T00:{i:02d}:00+00:00")
            if f.kind == "run_finished"
            else f
            for f in record._facts[key]
        ]

    into = Ledger(tmp_path / "into.db")
    fold(record, into)
    folded_ids = [_task_id_by_key(into, key) for key in keys]
    folded = [_run_shape(into, t) for t in folded_ids]
    assert folded == live

    for i, task_id in enumerate(folded_ids[1:], start=1):
        row = into._db.execute(
            "SELECT rn.ended_at AS ended_at FROM tasks t"
            " JOIN runs rn ON rn.run_id = t.run_id WHERE t.task_id = ?",
            (task_id,),
        ).fetchone()
        assert row["ended_at"] == f"2026-09-19 00:{i:02d}:00"

    assert [row_is_orphaned_cut(into, tid) for tid in folded_ids] == [
        False,
        True,
        False,
    ]

    folded_repo_id = int(
        into._db.execute(
            "SELECT rn.repo_id AS repo_id FROM tasks t"
            " JOIN runs rn ON rn.run_id = t.run_id WHERE t.task_id = ?",
            (folded_ids[0],),
        ).fetchone()["repo_id"]
    )
    fourth_run = into.create_run(folded_repo_id, base_sha="a" * 40)
    fourth = into.create_task(
        fourth_run, spec_id=spec_id, spec_sha=spec_sha, branch="b4"
    )
    spec = CellSpec(
        spec_id=spec_id,
        spec_sha=spec_sha,
        branch="b4",
        base_sha="a" * 40,
        touches=[],
        spec_type="bug",
        body="",
    )
    assert previous_cut_orphan(into, folded_repo_id, spec, fourth) == folded_ids[1]

    source.close()
    into.close()


def _copy_without(record, drop_kinds_by_key):
    """A `MemoryRecord` copy of `record`, with the kinds `drop_kinds_by_key`
    names for their own key left out, everything else unchanged."""
    copy = MemoryRecord()
    for key, facts in record._facts.items():
        drop = drop_kinds_by_key.get(key, set())
        copy._facts[key] = [f for f in facts if f.kind not in drop]
    return copy


def _row_count(ledger):
    return ledger._db.execute("SELECT COUNT(*) AS n FROM runs").fetchone()["n"]


def _status_by_key(ledger, key):
    return _run_shape(ledger, _task_id_by_key(ledger, key))[0]


def _grown_run_finished(key, at, status):
    return Fact(
        kind="run_finished",
        task_key=key,
        at=at,
        repo="saffron",
        batch_key=None,
        payload={"status": status},
    )


def test_a_task_whose_record_holds_run_created_folds_onto_a_run_of_its_own(tmp_path):
    # Three cuts sharing one `base_sha`: both ends `RUNNING`, the middle
    # `COMPLETE`. Each must fold onto a row of its own, twice over.
    record = MemoryRecord()
    source = Ledger(tmp_path / "source.db", record=record)
    repo_id = source.upsert_repo("saffron", "/o", "/m.git", policy_sha="p" * 64)
    older, middle, younger = (
        _cut(source, repo_id, "SA-1", "s" * 64, None),
        _cut(source, repo_id, "SA-1", "s" * 64, "COMPLETE"),
        _cut(source, repo_id, "SA-1", "s" * 64, None),
    )
    keys = [source.record_key(t) for t in (older, middle, younger)]
    source.close()

    into_a = Ledger(tmp_path / "into-a.db")
    fold(record, into_a)
    assert _row_count(into_a) == 3
    fold(record, into_a)
    assert _row_count(into_a) == 3
    into_a.close()

    # The same three, each with both run kinds dropped: back to the base
    # behaviour, one shared row, through two folds.
    stripped = _copy_without(
        record, {key: {"run_created", "run_finished"} for key in keys}
    )
    into_b = Ledger(tmp_path / "into-b.db")
    fold(stripped, into_b)
    assert _row_count(into_b) == 1
    fold(stripped, into_b)
    assert _row_count(into_b) == 1
    into_b.close()

    # A second live ledger, two cuts sharing one `base_sha`: `COMPLETE` then
    # `ABORTED`. A stripped task never joins the other's row.
    record2 = MemoryRecord()
    source2 = Ledger(tmp_path / "source2.db", record=record2)
    repo_id2 = source2.upsert_repo("saffron", "/o2", "/m2.git", policy_sha="p" * 64)
    older2 = _cut(source2, repo_id2, "SA-2", "s" * 64, "COMPLETE")
    younger2 = _cut(source2, repo_id2, "SA-2", "s" * 64, "ABORTED")
    key_older2, key_younger2 = (
        source2.record_key(older2),
        source2.record_key(younger2),
    )
    source2.close()

    strip_older = _copy_without(record2, {key_older2: {"run_created", "run_finished"}})
    into_c1 = Ledger(tmp_path / "into-c1.db")
    fold(strip_older, into_c1)
    fold(strip_older, into_c1)
    assert _row_count(into_c1) == 2
    assert _status_by_key(into_c1, key_older2) == "RUNNING"
    assert _status_by_key(into_c1, key_younger2) == "ABORTED"
    into_c1.close()

    strip_younger = _copy_without(
        record2, {key_younger2: {"run_created", "run_finished"}}
    )
    into_c2 = Ledger(tmp_path / "into-c2.db")
    fold(strip_younger, into_c2)
    fold(strip_younger, into_c2)
    assert _row_count(into_c2) == 2
    assert _status_by_key(into_c2, key_younger2) == "RUNNING"
    assert _status_by_key(into_c2, key_older2) == "COMPLETE"
    into_c2.close()

    # The first record once more, the oldest task dropping both kinds and
    # the middle one dropping only `run_created`.
    mixed = _copy_without(
        record,
        {keys[0]: {"run_created", "run_finished"}, keys[1]: {"run_created"}},
    )
    into_d = Ledger(tmp_path / "into-d.db")
    fold(mixed, into_d)
    assert _row_count(into_d) == 3
    assert _status_by_key(into_d, keys[0]) == "RUNNING"
    assert _status_by_key(into_d, keys[1]) == "COMPLETE"
    assert _status_by_key(into_d, keys[2]) == "RUNNING"
    into_d.close()

    # A third live ledger, two cuts sharing one `base_sha`, both `RUNNING`.
    # Three copies of its record grow a `run_finished` between two folds.
    record3 = MemoryRecord()
    source3 = Ledger(tmp_path / "source3.db", record=record3)
    repo_id3 = source3.upsert_repo("saffron", "/o3", "/m3.git", policy_sha="p" * 64)
    older3 = _cut(source3, repo_id3, "SA-3", "s" * 64, None)
    younger3 = _cut(source3, repo_id3, "SA-3", "s" * 64, None)
    key_older3, key_younger3 = (
        source3.record_key(older3),
        source3.record_key(younger3),
    )
    source3.close()

    # The younger task bare from the start. The older, which already holds
    # `run_created`, gains `run_finished` between the two folds.
    copy1 = _copy_without(record3, {key_younger3: {"run_created", "run_finished"}})
    into_e1 = Ledger(tmp_path / "into-e1.db")
    fold(copy1, into_e1)
    assert _row_count(into_e1) == 2
    assert _status_by_key(into_e1, key_older3) == "RUNNING"
    assert _status_by_key(into_e1, key_younger3) == "RUNNING"
    copy1.append(
        key_older3,
        _grown_run_finished(key_older3, "2026-09-19T00:10:00+00:00", "COMPLETE"),
    )
    fold(copy1, into_e1)
    assert _row_count(into_e1) == 2
    assert _status_by_key(into_e1, key_older3) == "COMPLETE"
    assert _status_by_key(into_e1, key_younger3) == "RUNNING"
    into_e1.close()

    # Both bare from the start. The older gains `run_finished` between folds.
    copy2 = _copy_without(
        record3,
        {
            key_older3: {"run_created", "run_finished"},
            key_younger3: {"run_created", "run_finished"},
        },
    )
    into_e2 = Ledger(tmp_path / "into-e2.db")
    fold(copy2, into_e2)
    assert _row_count(into_e2) == 1
    assert _status_by_key(into_e2, key_older3) == "RUNNING"
    assert _status_by_key(into_e2, key_younger3) == "RUNNING"
    copy2.append(
        key_older3,
        _grown_run_finished(key_older3, "2026-09-19T00:11:00+00:00", "COMPLETE"),
    )
    fold(copy2, into_e2)
    assert _row_count(into_e2) == 2
    assert _status_by_key(into_e2, key_older3) == "COMPLETE"
    assert _status_by_key(into_e2, key_younger3) == "RUNNING"
    into_e2.close()

    # Both bare from the start. The younger gains `run_finished` between
    # folds this time.
    copy3 = _copy_without(
        record3,
        {
            key_older3: {"run_created", "run_finished"},
            key_younger3: {"run_created", "run_finished"},
        },
    )
    into_e3 = Ledger(tmp_path / "into-e3.db")
    fold(copy3, into_e3)
    assert _row_count(into_e3) == 1
    assert _status_by_key(into_e3, key_older3) == "RUNNING"
    assert _status_by_key(into_e3, key_younger3) == "RUNNING"
    copy3.append(
        key_younger3,
        _grown_run_finished(key_younger3, "2026-09-19T00:12:00+00:00", "COMPLETE"),
    )
    fold(copy3, into_e3)
    assert _row_count(into_e3) == 2
    assert _status_by_key(into_e3, key_older3) == "RUNNING"
    assert _status_by_key(into_e3, key_younger3) == "COMPLETE"
    into_e3.close()

    # Both bare from the start, sharing one row, and both gain their own
    # `run_finished` before the second fold: each must land on its own row.
    copy4 = _copy_without(
        record3,
        {
            key_older3: {"run_created", "run_finished"},
            key_younger3: {"run_created", "run_finished"},
        },
    )
    into_e4 = Ledger(tmp_path / "into-e4.db")
    fold(copy4, into_e4)
    assert _row_count(into_e4) == 1
    copy4.append(
        key_older3,
        _grown_run_finished(key_older3, "2026-09-19T00:13:00+00:00", "COMPLETE"),
    )
    copy4.append(
        key_younger3,
        _grown_run_finished(key_younger3, "2026-09-19T00:14:00+00:00", "ABORTED"),
    )
    fold(copy4, into_e4)
    assert _row_count(into_e4) == 2
    assert _status_by_key(into_e4, key_older3) == "COMPLETE"
    assert _status_by_key(into_e4, key_younger3) == "ABORTED"
    into_e4.close()

    # A fourth live ledger, one cut `COMPLETE`, carrying a batch, a
    # preflight outcome and a baseline gate result no fact can rebuild.
    record4 = MemoryRecord()
    source4 = Ledger(tmp_path / "source4.db", record=record4)
    repo_id4 = source4.upsert_repo("saffron", "/o4", "/m4.git", policy_sha="p" * 64)
    task4 = _cut(source4, repo_id4, "SA-4", "s" * 64, "COMPLETE")
    run_id4 = source4.task_run(task4)
    batch_id4 = source4.create_batch(budget_usd=10.0)
    source4.attach_run_to_batch(run_id4, batch_id4)
    source4.set_run_preflight(run_id4, "PASSED")
    source4.record_gate_result(
        GateResult(
            gate="lint", status="pass", tool="ruff", duration_ms=1, summary="ok"
        ),
        run_id=run_id4,
    )

    def _run_row():
        return source4._db.execute(
            "SELECT status, batch_id, preflight FROM runs WHERE run_id = ?",
            (run_id4,),
        ).fetchone()

    for _ in range(2):
        fold(record4, source4)
        assert source4.task_run(task4) == run_id4
        assert _row_count(source4) == 1
        row = _run_row()
        assert row["status"] == "COMPLETE"
        assert row["batch_id"] == batch_id4
        assert row["preflight"] == "PASSED"
        assert len(source4.baseline_results(run_id4)) == 1
    source4.close()
