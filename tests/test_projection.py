"""Tests for `saffron.projection` (see its own module docstring for the design).

Every test imports `saffron.projection` inside its own body, never at module
scope: a module-scope import of a name this diff adds turns the `revert`
gate's reverted run into a collection error for the whole file, and `revert`
reads a collection error as `skip` (CLAUDE.md).
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from saffron.agents.findings import Finding
from saffron.events import Ceilings, EventLog, PhaseStart, Teardown
from saffron.gates.contract import GateResult
from saffron.ledger import Ledger

# ── fixture plumbing shared by all five tests ───────────────────────────────


def _git(mirror: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(mirror), *args], check=True, capture_output=True)


def _init_mirror(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q")
    _git(path, "config", "user.email", "t@example.com")
    _git(path, "config", "user.name", "t")
    (path / "README.md").write_bytes(b"x")
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", "init")
    return path


def _commit_spec(mirror: Path, spec_id: str, text: str, version: int) -> None:
    spec_dir = mirror / ".saffron" / "specs"
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / f"{spec_id}-v{version}.md").write_bytes(text.encode("utf-8"))
    _git(mirror, "add", "-A")
    _git(mirror, "commit", "-q", "-m", f"{spec_id} v{version}")


def spec_text(spec_id: str, *, criteria: bool = True, marker: str = "") -> str:
    """A minimal, valid committed spec version. A non-ASCII `marker` (used by
    the diff-content tests) is never spelled here; specs stay plain ASCII."""
    body = "\n## Acceptance criteria\n\n- [ ] does the thing\n" if criteria else "\n"
    return f"---\nid: {spec_id}\ntitle: t {marker}\ntype: feature\n---\n{body}"


def _epoch(started_at: str) -> float:
    dt = datetime.strptime(started_at, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    return dt.timestamp()


@dataclass
class T:
    """One task the fixture builder writes to a ledger + batch tree."""

    spec_id: str
    state: str
    spec_text: str | None = None
    spec_sha: str | None = None
    risk: str = "standard"
    pr_url: str | None = None
    started_at: str = "2026-01-01 00:00:00"
    ceilings_ts: float | None = None
    no_ceilings: bool = False
    plan_line: bool = False
    plan_line_hash: str | None = None
    plan_file: str | None = None
    diff_line: bool = False
    diff_line_length: int | None = None
    diff_file: str | None = None
    gate_result: bool = False
    finding: bool = False
    batch_id: int | None = None


def build(
    tmp_path: Path, tasks: list[T], ledger: Ledger | None = None
) -> tuple[Ledger, Path, list[int]]:
    """Write every `T` to a ledger + batch tree + git mirror, in order, and
    return `(ledger, out_dir, task_ids)` — `task_ids[i]` is `tasks[i]`'s. A
    caller that needs a `batch_id` before building tasks (test 1) passes its
    own already-open `Ledger`; everyone else gets a fresh one."""
    mirror = _init_mirror(tmp_path / "mirror")
    if ledger is None:
        ledger = Ledger(tmp_path / "ledger.db")
    out_dir = tmp_path / "batches"
    repo_id = ledger.upsert_repo("repo", "origin", str(mirror), "policy")

    versions: dict[str, int] = {}
    committed: set[tuple[str, str]] = set()
    task_ids: list[int] = []

    for i, t in enumerate(tasks):
        spec_sha = t.spec_sha
        if t.spec_text is not None:
            digest = hashlib.sha256(t.spec_text.encode()).hexdigest()
            spec_sha = spec_sha or digest
            key = (t.spec_id, digest)
            if key not in committed:
                versions[t.spec_id] = versions.get(t.spec_id, 0) + 1
                _commit_spec(mirror, t.spec_id, t.spec_text, versions[t.spec_id])
                committed.add(key)
        assert spec_sha is not None

        run_id = ledger.create_run(repo_id, "base-sha", batch_id=t.batch_id)
        ledger._db.execute(
            "UPDATE runs SET started_at = ? WHERE run_id = ?", (t.started_at, run_id)
        )
        ledger._db.commit()

        task_id = ledger.create_task(
            run_id, t.spec_id, spec_sha, branch=f"b-{i}", risk=t.risk
        )
        ledger._db.execute(
            "UPDATE tasks SET state = ?, pr_url = ? WHERE task_id = ?",
            (t.state, t.pr_url, task_id),
        )
        ledger._db.commit()
        task_ids.append(task_id)

        task_dir = out_dir / t.spec_id
        task_dir.mkdir(parents=True, exist_ok=True)

        if not t.no_ceilings:
            ts = t.ceilings_ts if t.ceilings_ts is not None else _epoch(t.started_at)
            log = EventLog(task_dir)
            log.append(
                Ceilings(
                    timestamp=ts,
                    spec_id=t.spec_id,
                    budget_usd=12.0,
                    max_attempts=4,
                    max_turns=60,
                    budget_source="default",
                    attempts_source="default",
                    turns_source="default",
                )
            )
            if t.plan_line:
                plan_hash = t.plan_line_hash
                if plan_hash is None:
                    assert t.plan_file is not None
                    plan_hash = hashlib.sha256(t.plan_file.encode()).hexdigest()[:12]
                log.append(
                    PhaseStart(
                        timestamp=ts + 0.1,
                        spec_id=t.spec_id,
                        phase="IMPLEMENT",
                        label="PLAN",
                        detail=f"accepted, sha256 {plan_hash}",
                    )
                )
            if t.diff_line:
                length = t.diff_line_length
                if length is None:
                    assert t.diff_file is not None
                    length = len(t.diff_file)
                log.append(
                    Teardown(
                        timestamp=ts + 0.2,
                        spec_id=t.spec_id,
                        step="exported",
                        ok=True,
                        detail=f"exported {length} bytes to {task_dir / 'patch.diff'}",
                    )
                )

        if t.plan_file is not None:
            (task_dir / "plan.json").write_bytes(t.plan_file.encode("utf-8"))
        if t.diff_file is not None:
            with open(task_dir / "patch.diff", "w", newline="", encoding="utf-8") as fh:
                fh.write(t.diff_file)

        if t.gate_result:
            attempt_id = ledger.open_attempt(task_id, phase="IMPLEMENT")
            ledger.close_attempt(
                attempt_id,
                session_id="s",
                subtype="success",
                terminal_reason=None,
                num_turns=1,
                cost_usd_est=1.0,
            )
            ledger.record_gate_result(
                GateResult(gate="tests", status="pass", tool="pytest 1.0"),
                attempt_id=attempt_id,
            )
        if t.finding:
            ledger.record_findings(
                task_id,
                [
                    Finding(
                        lens="correctness",
                        severity="blocker",
                        file="x.py",
                        line=1,
                        claim="a claim",
                        anchored=True,
                    )
                ],
            )

    return ledger, out_dir, task_ids


def _run_q4(output_path: Path) -> list:
    import pyoxigraph as ox

    root = Path(__file__).resolve().parent.parent
    query = (root / "ontology" / "queries" / "Q4-derivation-chain.rq").read_text()
    store = ox.Store()
    store.bulk_load(path=str(output_path), format=ox.RdfFormat.TURTLE)
    result = store.query(query)
    assert isinstance(result, ox.QuerySolutions), type(result).__name__
    return list(result)


# ── the five criteria ───────────────────────────────────────────────────────


def test_a_materialization_projects_every_ended_task_and_replaces_the_last(tmp_path):
    from saffron.projection import materialize

    diff_a = "diff --git a/x b/x\n+é\n"
    diff_b = "diff --git a/y b/y\n+é\n"
    ledger = Ledger(tmp_path / "ledger.db")
    batch_id = ledger.create_batch(50.0)
    ledger, out_dir, (a, b) = build(
        tmp_path,
        [
            T(
                "SA-8001",
                "MERGED",
                spec_text=spec_text("SA-8001"),
                pr_url="https://example/pr/1",
                started_at="2026-01-01 00:00:00",
                plan_line=True,
                plan_file="{}",
                diff_line=True,
                diff_file=diff_a,
                batch_id=batch_id,
            ),
            T(
                "SA-8002",
                "MERGED",
                spec_text=spec_text("SA-8002"),
                pr_url="https://example/pr/2",
                started_at="2026-01-02 00:00:00",
                plan_line=True,
                plan_file="{}",
                diff_line=True,
                diff_file=diff_b,
                batch_id=None,  # an attended cell: no batch at all
            ),
        ],
        ledger=ledger,
    )

    output_path = tmp_path / "projection.ttl"
    result1 = materialize(ledger, out_dir, output_path)
    assert result1.kept[a] is not None
    assert result1.kept[b] is not None

    import rdflib

    graph1 = rdflib.Graph().parse(output_path, format="turtle")
    FACTORY = rdflib.Namespace("urn:software-factory:ns#")
    assert len(list(graph1.subjects(rdflib.RDF.type, FACTORY.Task))) == 2

    # Task A stops being end-stated: a second call must not merely add to the
    # first output, it must replace it.
    ledger._db.execute("UPDATE tasks SET state = 'RUNNING' WHERE task_id = ?", (a,))
    ledger._db.commit()

    result2 = materialize(ledger, out_dir, output_path)
    assert a not in result2.kept
    assert result2.left_out[a].reason == "unsupported_end_state"
    assert result2.kept[b] is not None

    graph2 = rdflib.Graph().parse(output_path, format="turtle")
    assert len(list(graph2.subjects(rdflib.RDF.type, FACTORY.Task))) == 1


def test_q4_over_the_projection_reaches_a_merged_pull_request(tmp_path):
    from saffron.projection import materialize

    diff = "diff --git a/x b/x\n+café\n"
    plan = '{"steps": ["é"]}'
    ledger, out_dir, (task_id,) = build(
        tmp_path,
        [
            T(
                "SA-8101",
                "MERGED",
                spec_text=spec_text("SA-8101"),
                pr_url="https://example/pr/101",
                started_at="2026-01-01 00:00:00",
                plan_line=True,
                plan_file=plan,
                diff_line=True,
                diff_file=diff,
                gate_result=True,
                finding=True,
            )
        ],
    )

    output_path = tmp_path / "projection.ttl"
    result = materialize(ledger, out_dir, output_path)
    pr_iri = result.kept[task_id]
    assert pr_iri is not None

    rows = _run_q4(output_path)
    kinds = {
        row["kind"].value.rsplit("#", 1)[-1]
        for row in rows
        if row["pr"].value == pr_iri
    }
    assert kinds == {"Spec", "Plan", "Diff", "GateSuite", "Finding", "PullRequest"}


def test_an_artifact_a_later_task_overwrote_drops_only_the_earlier_chain(tmp_path):
    from saffron.projection import materialize

    plan_a, diff_a = '{"v": "a"}', "diff --git a/a b/a\n+â\n"
    plan_b, diff_b = '{"v": "b, longer"}', "diff --git a/b b/b\n+â longer\n"
    shared_pr = "https://example/pr/shared"

    ledger, out_dir, (a, b) = build(
        tmp_path,
        [
            T(
                "SA-8201",
                "MERGED",
                spec_text=spec_text("SA-8201"),
                pr_url=shared_pr,
                started_at="2026-01-01 00:00:00",
                plan_line=True,
                plan_line_hash=hashlib.sha256(plan_a.encode()).hexdigest()[:12],
                diff_line=True,
                diff_line_length=len(diff_a),
                # The file gets overwritten below by b's own write.
                gate_result=True,
                finding=True,
            ),
            T(
                "SA-8201",
                "MERGED",
                spec_text=spec_text("SA-8201"),
                pr_url=shared_pr,
                started_at="2026-01-01 00:05:00",
                plan_line=True,
                plan_file=plan_b,
                diff_line=True,
                diff_file=diff_b,
                gate_result=True,
                finding=True,
            ),
        ],
    )
    # Task a's own recorded lines pointed at plan_a/diff_a; only b's content
    # is ever written to disk, so a's chain is now stale.
    output_path = tmp_path / "projection.ttl"
    result = materialize(ledger, out_dir, output_path)

    assert a in result.kept and b in result.kept
    assert result.kept[a] is not None and result.kept[b] is not None
    assert result.kept[a] != result.kept[b]

    rows = _run_q4(output_path)
    prs_in_q4 = {row["pr"].value for row in rows}
    assert result.kept[b] in prs_in_q4
    assert result.kept[a] not in prs_in_q4


def test_spec_version_is_chosen_by_content_hash_not_by_being_seen_first(tmp_path):
    """`_find_spec_version` exists because a spec_id can hold more than one
    committed version; picking whichever blob is *seen* first (git's own
    traversal order, not this task's own `spec_sha`) would let two tasks of
    one spec_id silently resolve to the same, wrong, version. Two coexisting
    versions here, and two tasks each naming its own by hash — if the hash
    were ignored, both would resolve identically and this pair of opposite
    assertions could not both hold."""
    from saffron.projection import materialize

    with_criteria = spec_text("SA-8501", marker="a")
    without_criteria = spec_text("SA-8501", criteria=False, marker="b")
    ledger, out_dir, (usable_id, unusable_id) = build(
        tmp_path,
        [
            T(
                "SA-8501",
                "PREFLIGHT_FAILED",
                spec_text=with_criteria,
                started_at="2026-01-01 00:00:00",
            ),
            T(
                "SA-8501",
                "PREFLIGHT_FAILED",
                spec_text=without_criteria,
                started_at="2026-01-01 00:05:00",
            ),
        ],
    )

    result = materialize(ledger, out_dir, tmp_path / "projection.ttl")

    assert usable_id in result.kept
    assert result.left_out[unusable_id].reason == "spec_unusable"


def test_tasks_that_match_their_spans_in_count_but_not_time_are_unattributable(
    tmp_path,
):
    diff = "diff --git a/x b/x\n+ü\n"
    plan = '{"a": "ü"}'
    tasks = [
        # (a) two spans, two tasks — matched in count, not in time: both
        # tasks' start times land inside the *second* span.
        T(
            "SA-8301",
            "MERGED",
            spec_text=spec_text("SA-8301"),
            started_at="2026-01-01 00:02:00",
            ceilings_ts=_epoch("2026-01-01 00:00:00"),
            plan_line=True,
            plan_file=plan,
            diff_line=True,
            diff_file=diff,
        ),
        T(
            "SA-8301",
            "MERGED",
            spec_text=spec_text("SA-8301"),
            started_at="2026-01-01 00:02:10",
            ceilings_ts=_epoch("2026-01-01 00:00:00") + 100,
            plan_line=True,
            plan_file=plan,
            diff_line=True,
            diff_file=diff,
        ),
        # (b) merged, no plan-hash line.
        T(
            "SA-8302",
            "MERGED",
            spec_text=spec_text("SA-8302"),
            diff_line=True,
            diff_file=diff,
        ),
        # (c) merged, no diff-length line.
        T(
            "SA-8303",
            "MERGED",
            spec_text=spec_text("SA-8303"),
            plan_line=True,
            plan_file=plan,
        ),
        # (d) never merged, recorded neither line — kept.
        T("SA-8304", "PREFLIGHT_FAILED", spec_text=spec_text("SA-8304")),
        # (e) spec_sha matches no committed version.
        T("SA-8305", "MERGED", spec_sha="0" * 64),
        # (f) matched version has no criterion.
        T(
            "SA-8306",
            "MERGED",
            spec_text=spec_text("SA-8306", criteria=False),
        ),
        # (g) patch.diff deleted: line recorded, file never written.
        T(
            "SA-8307",
            "MERGED",
            spec_text=spec_text("SA-8307"),
            plan_line=True,
            plan_file=plan,
            diff_line=True,
            diff_line_length=123,
        ),
        # (h) TZ edge: run in second N, Ceilings at N+0.7, under JST-9.
        T(
            "SA-8308",
            "PREFLIGHT_FAILED",
            spec_text=spec_text("SA-8308"),
            started_at="2026-01-01 00:00:00",
            ceilings_ts=_epoch("2026-01-01 00:00:00") + 0.7,
        ),
    ]

    old_tz = os.environ.get("TZ")
    os.environ["TZ"] = "JST-9"
    time.tzset()
    try:
        ledger, out_dir, ids = build(tmp_path, tasks)
        from saffron.projection import materialize

        result = materialize(ledger, out_dir, tmp_path / "projection.ttl")
    finally:
        if old_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = old_tz
        time.tzset()

    a1, a2, b_, c_, d_, e_, f_, g_, h_ = ids

    assert result.left_out[a1].reason == "unattributable"
    assert result.left_out[a2].reason == "unattributable"
    assert result.left_out[b_].reason == "unattributable"
    assert result.left_out[c_].reason == "unattributable"
    assert d_ in result.kept
    assert result.left_out[e_].reason == "spec_not_found"
    assert result.left_out[f_].reason == "spec_unusable"
    assert result.left_out[g_].reason == "missing_artifact"
    assert h_ in result.kept


def test_a_projection_that_fails_the_shapes_leaves_none_behind(tmp_path):
    from saffron.projection import ProjectionError, materialize

    ledger, out_dir, (task_id,) = build(
        tmp_path,
        [
            T(
                "SA-8401",
                "MERGED",
                spec_text=spec_text("SA-8401"),
                pr_url="https://example/pr/401",
                started_at="2026-01-01 00:00:00",
                plan_line=True,
                plan_file="{}",
                diff_line=True,
                diff_file="diff --git a/x b/x\n+ñ\n",
            )
        ],
    )

    output_path = tmp_path / "projection.ttl"
    materialize(ledger, out_dir, output_path)
    assert output_path.exists()

    from saffron.projection import DEFAULT_SHAPES

    stricter = tmp_path / "stricter-shapes.ttl"
    stricter.write_text(
        DEFAULT_SHAPES.read_text() + "\nfactory:OnlyElevatedShape a sh:NodeShape ;\n"
        "    sh:targetClass factory:Task ;\n"
        "    sh:property [ sh:path factory:riskTier ; sh:in ( factory:elevated ) ] .\n"
    )

    try:
        materialize(ledger, out_dir, output_path, shapes_path=stricter)
        raise AssertionError("expected ProjectionError")
    except ProjectionError:
        pass

    assert not output_path.exists()
