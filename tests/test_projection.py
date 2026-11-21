"""Tests for `saffron.projection` (see its own module docstring for the design).

Every test imports `saffron.projection` inside its own body, never at module
scope: a module-scope import of a name this diff adds turns the `revert`
gate's reverted run into a collection error for the whole file, and `revert`
reads a collection error as `skip` (`DESIGN.md` §5.5.1).
"""

from __future__ import annotations

import hashlib
import math
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
    """A minimal, valid committed spec version; `marker` varies its bytes, so
    two versions of one spec_id hash apart."""
    body = "\n## Acceptance criteria\n\n- [ ] does the thing\n" if criteria else "\n"
    return f"---\nid: {spec_id}\ntitle: t {marker}\ntype: feature\n---\n{body}"


def _epoch(started_at: str) -> float:
    dt = datetime.strptime(started_at, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    return dt.timestamp()


def _ledger_text(epoch: float) -> str:
    """The ledger's own timestamp text, floored to the second, for an
    attempt's `started_at` set by hand (see `build`'s `attempts`)."""
    return datetime.fromtimestamp(math.floor(epoch), tz=UTC).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


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
    attempts: list[tuple[str, str]] | None = None


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

        ts = t.ceilings_ts if t.ceilings_ts is not None else _epoch(t.started_at)

        if not t.no_ceilings:
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

        if t.attempts is not None:
            attempt_specs = t.attempts
        elif not t.no_ceilings:
            attempt_specs = [("IMPLEMENT", _ledger_text(ts))]
        else:
            attempt_specs = []

        attempt_ids_by_phase: dict[str, int] = {}
        for phase, started_at_text in attempt_specs:
            attempt_id = ledger.open_attempt(task_id, phase=phase)
            ledger._db.execute(
                "UPDATE attempts SET started_at = ? WHERE attempt_id = ?",
                (started_at_text, attempt_id),
            )
            ledger._db.commit()
            attempt_ids_by_phase.setdefault(phase, attempt_id)

        if t.gate_result:
            implement_attempt_id = attempt_ids_by_phase.get(
                "IMPLEMENT"
            ) or attempt_ids_by_phase.get("IMPLEMENTING")
            if implement_attempt_id is None:
                implement_attempt_id = ledger.open_attempt(task_id, phase="IMPLEMENT")
            ledger.close_attempt(
                implement_attempt_id,
                session_id="s",
                subtype="success",
                terminal_reason=None,
                num_turns=1,
                cost_usd_est=1.0,
            )
            ledger.record_gate_result(
                GateResult(gate="tests", status="pass", tool="pytest 1.0"),
                attempt_id=implement_attempt_id,
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


def _write_span(
    log: EventLog,
    spec_id: str,
    task_dir: Path,
    ceilings_ts: float,
    plan_hash: str | None = None,
    diff_length: int | None = None,
) -> None:
    """One span's own `Ceilings`, plus the `PLAN`/`exported` lines that give
    it its own `plan_hash`/`diff_length`, when the caller names either."""
    log.append(
        Ceilings(
            timestamp=ceilings_ts,
            spec_id=spec_id,
            budget_usd=12.0,
            max_attempts=4,
            max_turns=60,
            budget_source="default",
            attempts_source="default",
            turns_source="default",
        )
    )
    if plan_hash is not None:
        log.append(
            PhaseStart(
                timestamp=ceilings_ts + 0.1,
                spec_id=spec_id,
                phase="IMPLEMENT",
                label="PLAN",
                detail=f"accepted, sha256 {plan_hash}",
            )
        )
    if diff_length is not None:
        log.append(
            Teardown(
                timestamp=ceilings_ts + 0.2,
                spec_id=spec_id,
                step="exported",
                ok=True,
                detail=f"exported {diff_length} bytes to {task_dir / 'patch.diff'}",
            )
        )


def _edges(output_path: Path, task_id: int) -> tuple[bool, bool]:
    """`(diff states its diff-to-plan edge, pull request states its
    pull-request-to-diff edge)`, read straight from the written graph."""
    import rdflib

    g = rdflib.Graph().parse(output_path, format="turtle")
    prov = rdflib.Namespace("http://www.w3.org/ns/prov#")
    data = rdflib.Namespace("urn:software-factory:projection:")
    diff_edge = any(g.triples((data[f"diff-{task_id}"], prov.wasDerivedFrom, None)))
    pr_edge = any(g.triples((data[f"pr-{task_id}"], prov.wasDerivedFrom, None)))
    return diff_edge, pr_edge


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
    mirror = tmp_path / "mirror"
    (mirror / ".saffron" / "specs" / "done").mkdir()
    _git(mirror, "mv", ".saffron/specs/SA-8001-v1.md", ".saffron/specs/done/")
    _git(mirror, "commit", "-q", "-m", "retire SA-8001")

    output_path = tmp_path / "projection.ttl"
    result1 = materialize(ledger, out_dir, output_path)
    assert a in result1.kept, result1.left_out.get(a)
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

    # IMPLEMENT 2 is the last attempt with gate results; a later REVIEWING one has none.
    gated = ledger.open_attempt(task_id, phase="IMPLEMENT")
    ledger.record_gate_result(
        GateResult(gate="tests", status="pass", tool="pytest 1.0"), attempt_id=gated
    )
    ledger.open_attempt(task_id, phase="REVIEWING")

    output_path = tmp_path / "projection.ttl"
    result = materialize(ledger, out_dir, output_path)
    pr_iri = result.kept[task_id]
    assert pr_iri is not None

    import rdflib

    g = rdflib.Graph().parse(output_path, format="turtle")
    factory = rdflib.Namespace("urn:software-factory:ns#")
    prov = rdflib.Namespace("http://www.w3.org/ns/prov#")
    attempts = set(g.subjects(rdflib.RDF.type, factory.Attempt))
    assert sorted(int(str(g.value(at, factory.n))) for at in attempts) == [1, 1, 2]
    assert len(set(g.subjects(rdflib.RDF.type, factory.Phase))) == 2
    generators = [at for at in attempts if g.value(at, prov.generated)]
    assert [int(str(g.value(at, factory.n))) for at in generators] == [2]

    rows = _run_q4(output_path)
    kinds = {
        row["kind"].value.rsplit("#", 1)[-1]
        for row in rows
        if row["pr"].value == pr_iri
    }
    assert kinds == {"Spec", "Plan", "Diff", "GateSuite", "Finding", "PullRequest"}


def test_an_artifact_a_later_task_overwrote_drops_only_the_earlier_chain(tmp_path):
    from saffron.projection import materialize

    # Pair 1: b overwrites a's plan only (same diff length). Pair 2: d overwrites
    # c's diff only (same plan). Each pair shares one pr_url.
    plan_a, plan_b = '{"v": "a"}', '{"v": "b, longer"}'
    diff_b = "diff --git a/b b/b\n+â\n"
    plan_d, diff_c, diff_d = (
        '{"v": "d"}',
        "diff --git a/c b/c\n+â\n",
        "diff --git a/d b/d\n+â longer\n",
    )

    def merged(spec_id, pr, started, **kw):
        return T(
            spec_id,
            "MERGED",
            spec_text=spec_text(spec_id),
            pr_url=pr,
            started_at=started,
            plan_line=True,
            diff_line=True,
            gate_result=True,
            finding=True,
            **kw,
        )

    ledger, out_dir, (a, b, c, d) = build(
        tmp_path,
        [
            merged(
                "SA-8201",
                "https://example/pr/shared-1",
                "2026-01-01 00:00:00",
                plan_line_hash=hashlib.sha256(plan_a.encode()).hexdigest()[:12],
                diff_line_length=len(diff_b),
            ),
            merged(
                "SA-8201",
                "https://example/pr/shared-1",
                "2026-01-01 00:05:00",
                plan_file=plan_b,
                diff_file=diff_b,
            ),
            merged(
                "SA-8202",
                "https://example/pr/shared-2",
                "2026-01-01 00:00:00",
                plan_line_hash=hashlib.sha256(plan_d.encode()).hexdigest()[:12],
                diff_line_length=len(diff_c),
            ),
            merged(
                "SA-8202",
                "https://example/pr/shared-2",
                "2026-01-01 00:05:00",
                plan_file=plan_d,
                diff_file=diff_d,
            ),
        ],
    )
    output_path = tmp_path / "projection.ttl"
    result = materialize(ledger, out_dir, output_path)

    for overwritten, sibling in ((a, b), (c, d)):
        assert overwritten in result.kept and sibling in result.kept
        assert result.kept[overwritten] is not None
        assert result.kept[overwritten] != result.kept[sibling]

    rows = _run_q4(output_path)
    prs_in_q4 = {row["pr"].value for row in rows}
    assert result.kept[a] not in prs_in_q4
    assert result.kept[c] not in prs_in_q4
    for sibling in (b, d):
        kinds = {
            row["kind"].value.rsplit("#", 1)[-1]
            for row in rows
            if row["pr"].value == result.kept[sibling]
        }
        assert kinds == {"Spec", "Plan", "Diff", "GateSuite", "Finding", "PullRequest"}

    # A mismatch drops one edge: every task's Diff is still a finding's
    # subject and a gate suite's input.
    import rdflib

    g = rdflib.Graph().parse(output_path, format="turtle")
    factory = rdflib.Namespace("urn:software-factory:ns#")
    earl = rdflib.Namespace("http://www.w3.org/ns/earl#")
    prov = rdflib.Namespace("http://www.w3.org/ns/prov#")
    diffs = set(g.subjects(rdflib.RDF.type, factory.Diff))
    assert len(diffs) == 4
    for diff in diffs:
        assert any(
            (f, rdflib.RDF.type, factory.Finding) in g
            for f in g.subjects(earl.subject, diff)
        )
        assert any(
            (s, rdflib.RDF.type, factory.GateSuite) in g
            for s in g.subjects(prov.used, diff)
        )


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


def test_a_test_or_docs_task_reaches_the_projection(tmp_path):
    """Intake takes six spec types, and the shapes once held three, so a
    `test` or `docs` task was left out as `spec_unusable` (b-60d804)."""
    from saffron.projection import materialize

    as_test = spec_text("SA-8502").replace("type: feature", "type: test")
    as_docs = spec_text("SA-8503").replace("type: feature", "type: docs")
    ledger, out_dir, (test_id, docs_id) = build(
        tmp_path,
        [
            T("SA-8502", "PREFLIGHT_FAILED", spec_text=as_test),
            T("SA-8503", "PREFLIGHT_FAILED", spec_text=as_docs),
        ],
    )

    result = materialize(ledger, out_dir, tmp_path / "projection.ttl")

    assert test_id in result.kept
    assert docs_id in result.kept


def test_tasks_that_match_their_spans_in_count_but_not_time_are_unattributable(
    tmp_path,
):
    diff = "diff --git a/x b/x\n+ü\n"
    plan = '{"a": "ü"}'
    tasks = [
        # (a) two spans, two tasks: both last cell attempts land in span 1,
        # never the run row, which sits away from its own span.
        T(
            "SA-8301",
            "MERGED",
            spec_text=spec_text("SA-8301"),
            started_at="2025-06-01 00:00:00",
            ceilings_ts=_epoch("2026-01-01 00:00:00"),
            attempts=[("IMPLEMENTING", "2026-01-01 00:02:00")],
            plan_line=True,
            plan_file=plan,
            diff_line=True,
            diff_file=diff,
        ),
        T(
            "SA-8301",
            "MERGED",
            spec_text=spec_text("SA-8301"),
            started_at="2025-06-01 00:05:00",
            ceilings_ts=_epoch("2026-01-01 00:00:00") + 100,
            attempts=[("IMPLEMENTING", "2026-01-01 00:02:10")],
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
        # (i) merged, plan line recorded, plan.json never written.
        T(
            "SA-8309",
            "MERGED",
            spec_text=spec_text("SA-8309"),
            plan_line=True,
            plan_line_hash="0" * 12,
            diff_line=True,
            diff_file=diff,
        ),
        # (j) two Ceilings share second N: one attempt lands in N, its
        # sibling's a day before, and both run rows sit away from N.
        T(
            "SA-8310",
            "PREFLIGHT_FAILED",
            spec_text=spec_text("SA-8310"),
            started_at="2030-01-01 00:00:00",
            ceilings_ts=_epoch("2026-01-01 00:00:00") + 0.2,
            attempts=[("REVIEWING", "2026-01-01 00:00:00")],
        ),
        T(
            "SA-8310",
            "PREFLIGHT_FAILED",
            spec_text=spec_text("SA-8310"),
            started_at="2030-01-01 00:05:00",
            ceilings_ts=_epoch("2026-01-01 00:00:00") + 0.6,
            attempts=[("REVIEWING", "2025-12-31 00:00:00")],
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

    a1, a2, b_, c_, d_, e_, f_, g_, i_, j1, j2, h_ = ids
    reasons = {t: lo.reason for t, lo in result.left_out.items()}

    assert reasons.get(a1) == "unattributable"
    assert reasons.get(a2) == "unattributable"
    assert reasons.get(b_) == "unattributable"
    assert reasons.get(c_) == "unattributable"
    assert d_ in result.kept
    assert reasons.get(e_) == "spec_not_found"
    assert reasons.get(f_) == "spec_unusable"
    assert reasons.get(g_) == "missing_artifact"
    assert reasons.get(i_) == "missing_artifact"
    assert reasons.get(j1) == "unattributable"
    assert reasons.get(j2) == "unattributable"
    assert h_ in result.kept

    import rdflib

    g = rdflib.Graph().parse(tmp_path / "projection.ttl", format="turtle")
    terms = {str(term) for triple in g for term in triple}
    left_specs = {tasks[ids.index(t)].spec_id for t in result.left_out}
    assert not any(spec_id in term for spec_id in left_specs for term in terms)
    task_class = rdflib.URIRef("urn:software-factory:ns#Task")
    assert len(set(g.subjects(rdflib.RDF.type, task_class))) == len(result.kept)


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


# ── the last-cell-attempt criteria ──────────────────────────────────────────


def test_a_task_is_tied_to_the_span_its_last_cell_attempt_starts_in(tmp_path):
    """Four spans, three merged tasks share one log. A's last cell attempt
    is REVIEWING, in span 1. Its earlier gated IMPLEMENTING attempt sits in
    span 0, and its later SPEC_WRITING one in span 2. B's last cell attempt
    is REBUTTING, in span 2. Its earlier REPAIRING attempt sits in span 1,
    and its later COMMIT_REVIEW one in span 3. C's only cell attempt lands
    a day into the open span 3. Each span's own plan_hash and diff_length
    match the stored files in its own pattern. A states both edges, B
    states one, C the other, and Q4 reaches only A's pull request."""
    from saffron.projection import materialize

    spec_id = "SA-9201"
    plan_whole = '{"span": "one"}'
    diff_whole = "diff --git a/one b/one\n+é\n"
    plan_hash = hashlib.sha256(plan_whole.encode()).hexdigest()[:12]
    diff_length = len(diff_whole)

    t0 = _epoch("2026-02-01 00:00:00")
    t1 = _epoch("2026-02-01 00:10:00")
    t2 = _epoch("2026-02-01 00:20:00")
    t3 = _epoch("2026-02-01 00:30:00")

    a = T(
        spec_id,
        "MERGED",
        spec_text=spec_text(spec_id),
        pr_url="https://example/pr/a",
        started_at="2026-01-01 00:00:00",  # predates every span
        no_ceilings=True,
        attempts=[
            ("IMPLEMENTING", _ledger_text(t0 + 60)),
            ("REVIEWING", _ledger_text(t1)),
            ("SPEC_WRITING", _ledger_text(t2 + 60)),
        ],
        gate_result=True,
    )
    b = T(
        spec_id,
        "MERGED",
        spec_text=spec_text(spec_id),
        pr_url="https://example/pr/b",
        started_at=_ledger_text(t1 + 60),
        no_ceilings=True,
        attempts=[
            ("SPEC_REVIEW", _ledger_text(t1 + 120)),
            ("REPAIRING", _ledger_text(t1 + 300)),
            ("IMPLEMENTING", _ledger_text(t2 + 60)),
            ("REBUTTING", _ledger_text(t3 - 1)),
            ("COMMIT_REVIEW", _ledger_text(t3 + 60)),
        ],
        gate_result=True,
    )
    c = T(
        spec_id,
        "MERGED",
        spec_text=spec_text(spec_id),
        pr_url="https://example/pr/c",
        started_at=_ledger_text(t3 + 1),
        no_ceilings=True,
        attempts=[("IMPLEMENTING", _ledger_text(t3 + 86400))],
    )

    ledger, out_dir, (a_id, b_id, c_id) = build(tmp_path, [a, b, c])
    task_dir = out_dir / spec_id
    (task_dir / "plan.json").write_bytes(plan_whole.encode("utf-8"))
    with open(task_dir / "patch.diff", "w", newline="", encoding="utf-8") as fh:
        fh.write(diff_whole)

    log = EventLog(task_dir)
    _write_span(log, spec_id, task_dir, t0, "0" * 12, 111)
    _write_span(log, spec_id, task_dir, t1 + 0.4, plan_hash, diff_length)
    _write_span(log, spec_id, task_dir, t2, plan_hash, 222)
    _write_span(log, spec_id, task_dir, t3, "f" * 12, diff_length)

    output_path = tmp_path / "projection.ttl"
    result = materialize(ledger, out_dir, output_path)

    assert {
        "a": _edges(output_path, a_id),
        "b": _edges(output_path, b_id),
        "c": _edges(output_path, c_id),
    } == {"a": (True, True), "b": (True, False), "c": (False, True)}

    rows = _run_q4(output_path)
    assert {row["pr"].value for row in rows} == {result.kept.get(a_id)}


def test_a_task_with_no_cell_attempt_takes_no_span(tmp_path):
    """One open-ended span, in one shared log, owned by merged task F. D's
    only attempt is a SPEC_REVIEW inside it, and E has no attempt at all,
    though its run row lies inside it too. D and E are each unattributable.
    F alone is kept, states both edges, and is the pull request Q4 reaches."""
    from saffron.projection import materialize

    spec_id = "SA-9202"
    plan_whole = '{"owner": "f"}'
    diff_whole = "diff --git a/f b/f\n+ü\n"
    plan_hash = hashlib.sha256(plan_whole.encode()).hexdigest()[:12]
    diff_length = len(diff_whole)

    s = _epoch("2026-03-01 00:00:00")

    d = T(
        spec_id,
        "PREFLIGHT_FAILED",
        spec_text=spec_text(spec_id),
        started_at="2020-01-01 00:00:00",
        no_ceilings=True,
        attempts=[("SPEC_REVIEW", _ledger_text(s + 30))],
    )
    e = T(
        spec_id,
        "PREFLIGHT_FAILED",
        spec_text=spec_text(spec_id),
        started_at=_ledger_text(s + 10),  # inside the span, with no attempt
        no_ceilings=True,
        attempts=[],
    )
    f = T(
        spec_id,
        "MERGED",
        spec_text=spec_text(spec_id),
        pr_url="https://example/pr/f",
        started_at="2020-01-01 00:00:00",
        no_ceilings=True,
        attempts=[("IMPLEMENTING", _ledger_text(s + 60))],
        gate_result=True,
    )

    ledger, out_dir, (d_id, e_id, f_id) = build(tmp_path, [d, e, f])
    task_dir = out_dir / spec_id
    (task_dir / "plan.json").write_bytes(plan_whole.encode("utf-8"))
    with open(task_dir / "patch.diff", "w", newline="", encoding="utf-8") as fh:
        fh.write(diff_whole)

    log = EventLog(task_dir)
    _write_span(log, spec_id, task_dir, s, plan_hash, diff_length)

    output_path = tmp_path / "projection.ttl"
    result = materialize(ledger, out_dir, output_path)

    reasons = {t: lo.reason for t, lo in result.left_out.items()}
    assert reasons.get(d_id) == "unattributable"
    assert reasons.get(e_id) == "unattributable"
    assert f_id in result.kept
    assert _edges(output_path, f_id) == (True, True)

    rows = _run_q4(output_path)
    assert {row["pr"].value for row in rows} == {result.kept.get(f_id)}


def test_a_repair_or_rebuttal_turn_is_a_cell_attempt(tmp_path):
    """P and Q each gate an IMPLEMENTING attempt in span 0. P's last cell
    attempt is a REPAIRING turn in span 1, and Q's a REBUTTING turn in
    span 2. Each is tied to the span its last turn starts in."""
    from saffron.projection import materialize

    spec_id = "SA-9204"
    plan_whole = '{"owner": "pq"}'
    diff_whole = "diff --git a/p b/p\n+p\n"
    plan_hash = hashlib.sha256(plan_whole.encode()).hexdigest()[:12]
    diff_length = len(diff_whole)
    t0 = _epoch("2026-03-02 00:00:00")
    t1, t2 = t0 + 3600, t0 + 7200

    def task(name: str, last: tuple[str, str]) -> T:
        return T(
            spec_id,
            "MERGED",
            spec_text=spec_text(spec_id),
            pr_url=f"https://example/pr/{name}",
            started_at="2020-01-01 00:00:00",
            no_ceilings=True,
            attempts=[("IMPLEMENTING", _ledger_text(t0 + 600)), last],
            gate_result=True,
        )

    p = task("p", ("REPAIRING", _ledger_text(t1 + 1200)))
    q = task("q", ("REBUTTING", _ledger_text(t2 + 1200)))
    ledger, out_dir, (p_id, q_id) = build(tmp_path, [p, q])
    task_dir = out_dir / spec_id
    (task_dir / "plan.json").write_bytes(plan_whole.encode("utf-8"))
    with open(task_dir / "patch.diff", "w", newline="", encoding="utf-8") as fh:
        fh.write(diff_whole)

    log = EventLog(task_dir)
    _write_span(log, spec_id, task_dir, t0)
    _write_span(log, spec_id, task_dir, t1, plan_hash, 1)
    _write_span(log, spec_id, task_dir, t2, "e" * 12, diff_length)

    output_path = tmp_path / "projection.ttl"
    materialize(ledger, out_dir, output_path)

    assert {"p": _edges(output_path, p_id), "q": _edges(output_path, q_id)} == {
        "p": (True, False),
        "q": (False, True),
    }


def test_a_span_two_tasks_claim_is_no_ones_and_the_next_span_is_still_owned(
    tmp_path,
):
    """One shared log, two spans. Merged tasks G and H each end their cell
    in span 0, one after the other, so span 0 goes to neither. Merged task
    J has its run row and a SPEC_REVIEW attempt in span 0 too, but its own
    cell sits alone in span 1. J states only its pull-request-to-diff edge."""
    from saffron.projection import materialize

    spec_id = "SA-9203"
    plan_whole = '{"owner": "j"}'
    diff_whole = "diff --git a/j b/j\n+ö\n"
    diff_length = len(diff_whole)

    s0 = _epoch("2026-04-01 00:00:00")
    s1 = _epoch("2026-04-01 00:10:00")

    g = T(
        spec_id,
        "MERGED",
        spec_text=spec_text(spec_id),
        started_at="2020-01-01 00:00:00",
        no_ceilings=True,
        attempts=[("IMPLEMENTING", _ledger_text(s0 + 30))],
    )
    h = T(
        spec_id,
        "MERGED",
        spec_text=spec_text(spec_id),
        started_at="2020-01-01 00:05:00",
        no_ceilings=True,
        attempts=[("REVIEWING", _ledger_text(s0 + 60))],
    )
    j = T(
        spec_id,
        "MERGED",
        spec_text=spec_text(spec_id),
        pr_url="https://example/pr/j",
        started_at=_ledger_text(s0 + 10),  # inside span 0, not span 1
        no_ceilings=True,
        attempts=[
            ("SPEC_REVIEW", _ledger_text(s0 + 90)),
            ("IMPLEMENTING", _ledger_text(s1 + 30)),
        ],
        gate_result=True,
    )

    ledger, out_dir, (g_id, h_id, j_id) = build(tmp_path, [g, h, j])
    task_dir = out_dir / spec_id
    (task_dir / "plan.json").write_bytes(plan_whole.encode("utf-8"))
    with open(task_dir / "patch.diff", "w", newline="", encoding="utf-8") as fh:
        fh.write(diff_whole)

    log = EventLog(task_dir)
    # A recorded line here, even one unmatched, keeps a wrongly-attributed
    # G or H kept instead of masked as "merged with no recorded line".
    _write_span(log, spec_id, task_dir, s0, "a" * 12, 999)
    _write_span(log, spec_id, task_dir, s1, "f" * 12, diff_length)

    output_path = tmp_path / "projection.ttl"
    result = materialize(ledger, out_dir, output_path)

    reasons = {t: lo.reason for t, lo in result.left_out.items()}
    assert reasons.get(g_id) == "unattributable"
    assert reasons.get(h_id) == "unattributable"
    assert j_id in result.kept
    assert _edges(output_path, j_id) == (False, True)
