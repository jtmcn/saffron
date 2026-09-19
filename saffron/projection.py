"""The ledger/batch-tree → RDF projection — `DESIGN.md` Appendix T, N5.

`SA-0107` found that N5's derivation-chain query (`ontology/queries/
Q4-derivation-chain.rq`) had only ever run against hand-authored fixtures, so
it proved the query well formed and proved nothing about any change this
repository merged. This module is the emitter that lets it run against the
real run record: one call, `materialize`, that reads the ledger plus the batch
tree it is paired with and writes a Turtle projection of exactly six kinds —
`Spec`, `Plan`, `Diff`, `GateSuite`, `Finding`, `PullRequest` — the ones Q4
names. `SA-0108` builds the comparator and the command that runs this once
over merged history; nothing here decides anything or runs at batch end
(`DESIGN.md` §1.4 stands).

Two facts shape every decision below. First, the batch tree is keyed by spec,
not by task (`task_dir = out_dir / spec_id`), so a later task of the same spec
overwrites the earlier one's `plan.json`/`patch.diff` — a chain is stated only
when the file on disk still matches what the *owning* task's own event log
recorded at extraction, never from whatever happens to be sitting there now.
Second, `events.jsonl` is one log per spec, shared by every task that spec has
ever run, so a task must be tied to its own span of that log *by time*
(`runs.started_at` against `Ceilings.timestamp`), never by position — a span a
task's own start time does not land in cleanly is not this task's span.

A task the shapes would reject is never written to the graph at all: it is
left out with a reason, and the rest are still projected. A projection that
fails `pyshacl` is an `error` in this module's own sense — it raises and
removes whatever projection was there before, so a reader finds none rather
than the last one.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from saffron.intake import Spec
    from saffron.ledger import Ledger

_ROOT = Path(__file__).resolve().parent.parent
VOCABULARY = _ROOT / "ontology" / "factory.ttl"
DEFAULT_SHAPES = _ROOT / "ontology" / "shapes" / "factory-shapes.ttl"
_VENDOR_DIR = _ROOT / "ontology" / "vendor"

NS = "urn:software-factory:ns#"
DATA_NS = "urn:software-factory:projection:"

# `TaskShape`'s and `SpecShape`'s `sh:in` sets, read from the caller's shapes
# file so a custom `shapes_path` (the fifth criterion) governs both.
_END_STATE_PATH = f"{NS}endedInState"
_SPEC_TYPE_PATH = f"{NS}specType"

_PLAN_ACCEPTED = re.compile(r"^accepted, sha256 ([0-9a-f]{12})$")
_DIFF_EXPORTED = re.compile(r"^exported (\d+) bytes to ")

LeftOutReason = Literal[
    "unsupported_end_state",
    "spec_not_found",
    "spec_unusable",
    "unattributable",
    "missing_artifact",
]


class ProjectionError(RuntimeError):
    """The graph failed the shapes. The caller's previous projection, if any,
    is already gone by the time this is raised — see `materialize`."""


@dataclass(frozen=True)
class LeftOut:
    """Why a task is absent from the graph. `spec_unusable` covers a matched
    spec version that does not parse, has no criterion, or has a type outside
    `SpecShape`'s set."""

    reason: LeftOutReason
    detail: str = ""


@dataclass(frozen=True)
class Projection:
    """What one `materialize` call found. `kept` maps every projected task's
    id to the task's own PullRequest IRI, the node Q4 binds as ?pr when the
    task merged and its chain holds, or to `None` for a kept task that never
    opened one. `left_out` names why every other task is absent from the graph."""

    kept: dict[int, str | None]
    left_out: dict[int, LeftOut]


# ── git plumbing: every committed spec version, across every ref ───────────


def _git_lines(mirror: Path, *args: str) -> list[str]:
    completed = subprocess.run(
        ["git", "-C", str(mirror), *args], capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        return []
    return completed.stdout.splitlines()


def _git_blob(mirror: Path, blob_sha: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(mirror), "cat-file", "-p", blob_sha],
        capture_output=True,
        check=False,
    )
    return completed.stdout if completed.returncode == 0 else b""


def _spec_blobs(mirror: Path, cache: dict[str, list[str]]) -> list[str]:
    """Every `<blob-sha> <path>` line `.saffron/specs/` has ever held, on any
    ref — one `rev-list --objects` per mirror rather than one `ls-tree` per
    commit, and cached across every spec_id this mirror is asked about."""
    key = str(mirror)
    if key not in cache:
        cache[key] = _git_lines(
            mirror, "rev-list", "--objects", "--all", "--", ".saffron/specs"
        )
    return cache[key]


def _find_spec_version(
    mirror: Path,
    spec_id: str,
    spec_sha: str,
    spec_types: frozenset[str],
    blob_cache: dict[str, list[str]],
) -> tuple[Spec | None, LeftOutReason | None]:
    """The committed spec text whose sha256 equals `spec_sha`, parsed — or the
    reason none qualifies. Imported lazily: `saffron.intake` is heavier than
    this module needs for every caller."""
    from saffron.intake import SpecError, parse_spec

    # Any subdirectory: merged specs are retired to `.saffron/specs/done/`.
    pattern = re.compile(rf"^\.saffron/specs/(?:.*/)?{re.escape(spec_id)}-[^/]*\.md$")
    seen: set[str] = set()
    for line in _spec_blobs(mirror, blob_cache):
        parts = line.split(" ", 1)
        if len(parts) != 2:
            continue
        blob_sha, path = parts
        if blob_sha in seen or not pattern.match(path):
            continue
        seen.add(blob_sha)
        raw = _git_blob(mirror, blob_sha)
        if hashlib.sha256(raw).hexdigest() != spec_sha:
            continue
        try:
            spec = parse_spec(raw.decode())
        except (SpecError, UnicodeDecodeError):
            return None, "spec_unusable"
        criteria = len(spec.acceptance) + len(spec.acceptance_criteria)
        if f"{NS}{spec.type}" not in spec_types or criteria == 0:
            return None, "spec_unusable"
        return spec, None
    return None, "spec_not_found"


# ── spans: one spec's shared event log, cut at each Ceilings ───────────────


@dataclass(frozen=True)
class _Span:
    start: int
    end: float  # math.inf for the last span
    plan_hash: str | None
    diff_length: int | None


def _spans(spec_id: str, out_dir: Path) -> list[_Span]:
    from saffron.events import Ceilings, PhaseStart, Teardown, read_log

    events = read_log(out_dir / spec_id)
    marks = [
        (i, event) for i, event in enumerate(events) if isinstance(event, Ceilings)
    ]
    spans: list[_Span] = []
    for idx, (pos, ceilings) in enumerate(marks):
        end_pos = marks[idx + 1][0] if idx + 1 < len(marks) else len(events)
        plan_hash: str | None = None
        diff_length: int | None = None
        for event in events[pos:end_pos]:
            if (
                isinstance(event, PhaseStart)
                and event.phase == "IMPLEMENT"
                and event.label == "PLAN"
            ):
                m = _PLAN_ACCEPTED.match(event.detail)
                if m:
                    plan_hash = m.group(1)
            elif isinstance(event, Teardown) and event.step == "exported" and event.ok:
                m = _DIFF_EXPORTED.match(event.detail)
                if m:
                    diff_length = int(m.group(1))
        start = math.floor(ceilings.timestamp)
        end = (
            math.floor(marks[idx + 1][1].timestamp)
            if idx + 1 < len(marks)
            else math.inf
        )
        spans.append(
            _Span(start=start, end=end, plan_hash=plan_hash, diff_length=diff_length)
        )
    return spans


def _run_start_epoch(started_at: str) -> int:
    """`runs.started_at` is `datetime('now')` — UTC text with no offset.
    Parsed with an explicit UTC tzinfo so `.timestamp()` is correct
    regardless of the host's local zone (the fourth criterion's own test)."""
    dt = datetime.strptime(started_at, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    return math.floor(dt.timestamp())


def _attribute(
    tasks: list[tuple[int, str]], spans: list[_Span]
) -> dict[int, _Span | None]:
    """Ties each `(task_id, started_at)` to the one span whose half-open
    `[start, end)` holds it. `None` for a task no span holds, for every task
    in a span more than one task's start time lands in, and for a task whose
    second is more than one span's floor."""
    holders: list[list[int]] = [[] for _ in spans]
    task_spans: dict[int, list[int]] = {}
    for task_id, started_at in tasks:
        epoch = _run_start_epoch(started_at)
        if sum(1 for span in spans if span.start == epoch) > 1:
            continue
        for i, span in enumerate(spans):
            if span.start <= epoch < span.end:
                task_spans.setdefault(task_id, []).append(i)
                holders[i].append(task_id)
    result: dict[int, _Span | None] = {}
    for task_id, _ in tasks:
        matched = task_spans.get(task_id, [])
        if len(matched) != 1 or len(holders[matched[0]]) != 1:
            result[task_id] = None
        else:
            result[task_id] = spans[matched[0]]
    return result


# ── shapes: closed sets, read from the caller's file ───────────────────────


def _sh_in(shapes_path: Path, path: str) -> frozenset[str]:
    import rdflib
    import rdflib.collection

    g = rdflib.Graph().parse(shapes_path, format="turtle")
    sh_in = rdflib.URIRef("http://www.w3.org/ns/shacl#in")
    sh_path = rdflib.URIRef("http://www.w3.org/ns/shacl#path")
    accepted: set[str] = set()
    for shape in g.subjects(sh_path, rdflib.URIRef(path)):
        for lst in g.objects(shape, sh_in):
            for node in rdflib.collection.Collection(g, lst):
                accepted.add(str(node))
    return frozenset(accepted)


# ── the diff/plan on disk, compared against what the span recorded ─────────


def _plan_hash12(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def _diff_length(path: Path) -> int:
    with open(path, newline="", encoding="utf-8") as fh:
        return len(fh.read())


# ── the ledger, read whole: every task, from any run, any batch ────────────


def _all_tasks(ledger: Ledger) -> list[dict]:
    """Every task ever recorded, joined to its run and repo."""
    rows = ledger._db.execute(
        """SELECT t.task_id, t.spec_id, t.spec_sha, t.state, t.risk, t.pr_url,
                  r.run_id, r.started_at, r.repo_id, repos.mirror_path
             FROM tasks t
             JOIN runs r ON r.run_id = t.run_id
             JOIN repos ON repos.repo_id = r.repo_id
            ORDER BY t.task_id"""
    ).fetchall()
    return [dict(row) for row in rows]


# ── assembling the graph ────────────────────────────────────────────────


def materialize(
    ledger: Ledger,
    out_dir: Path,
    output_path: Path,
    *,
    shapes_path: Path = DEFAULT_SHAPES,
) -> Projection:
    """Project every ended task the shapes and Q4 can use, and write it to
    `output_path` as Turtle — replacing whatever was there, never adding to
    it. Raises `ProjectionError` (and removes `output_path`) if the result
    fails `shapes_path`; nothing else in this module raises for a single bad
    task, which is left out with a reason instead."""
    import rdflib

    g = rdflib.Graph()
    factory = rdflib.Namespace(NS)
    data = rdflib.Namespace(DATA_NS)
    prov = rdflib.Namespace("http://www.w3.org/ns/prov#")
    earl = rdflib.Namespace("http://www.w3.org/ns/earl#")
    xsd = rdflib.namespace.XSD

    end_states = _sh_in(shapes_path, _END_STATE_PATH)
    spec_types = _sh_in(shapes_path, _SPEC_TYPE_PATH)
    tasks = _all_tasks(ledger)

    kept: dict[int, str | None] = {}
    left_out: dict[int, LeftOut] = {}

    spans_by_spec: dict[str, list[_Span]] = {}
    attribution_by_spec: dict[str, dict[int, _Span | None]] = {}
    for spec_id in {row["spec_id"] for row in tasks}:
        spans = _spans(spec_id, out_dir)
        spans_by_spec[spec_id] = spans
        holders = [
            (row["task_id"], row["started_at"])
            for row in tasks
            if row["spec_id"] == spec_id
        ]
        attribution_by_spec[spec_id] = _attribute(holders, spans)

    spec_cache: dict[
        tuple[str, str, str], tuple[Spec | None, LeftOutReason | None]
    ] = {}
    blob_cache: dict[str, list[str]] = {}
    spec_nodes: dict[tuple[str, str], rdflib.URIRef] = {}

    for row in tasks:
        task_id = row["task_id"]

        if f"{NS}{row['state']}" not in end_states:
            left_out[task_id] = LeftOut("unsupported_end_state", row["state"])
            continue

        cache_key = (row["mirror_path"], row["spec_id"], row["spec_sha"])
        if cache_key not in spec_cache:
            spec_cache[cache_key] = _find_spec_version(
                Path(row["mirror_path"]),
                row["spec_id"],
                row["spec_sha"],
                spec_types,
                blob_cache,
            )
        spec, reason = spec_cache[cache_key]
        if spec is None:
            left_out[task_id] = LeftOut(reason or "spec_not_found")
            continue

        span = attribution_by_spec[row["spec_id"]].get(task_id)
        if span is None:
            left_out[task_id] = LeftOut("unattributable")
            continue

        is_merged = row["state"] == "MERGED"
        if is_merged and (span.plan_hash is None or span.diff_length is None):
            left_out[task_id] = LeftOut(
                "unattributable", "merged with no recorded line"
            )
            continue

        # Both files are checked before any triple, so a left-out task leaves none.
        task_dir = out_dir / row["spec_id"]
        plan_path = task_dir / "plan.json"
        diff_path = task_dir / "patch.diff"
        has_plan = span.plan_hash is not None and plan_path.is_file()
        has_diff = span.diff_length is not None and diff_path.is_file()
        if is_merged and not has_plan:
            left_out[task_id] = LeftOut("missing_artifact", "plan.json")
            continue
        if is_merged and not has_diff:
            left_out[task_id] = LeftOut("missing_artifact", "patch.diff")
            continue

        spec_key = (row["spec_id"], row["spec_sha"])
        if spec_key not in spec_nodes:
            spec_node = data[f"spec-{row['spec_id']}-{row['spec_sha']}"]
            g.add((spec_node, rdflib.RDF.type, factory.Spec))
            g.add((spec_node, factory.specType, factory[spec.type]))
            all_criteria = list(spec.acceptance) or list(spec.acceptance_criteria)
            for i, _ in enumerate(all_criteria):
                crit = data[f"criterion-{row['spec_id']}-{row['spec_sha']}-{i}"]
                g.add((crit, rdflib.RDF.type, factory.AcceptanceCriterion))
                g.add((spec_node, factory.hasCriterion, crit))
            spec_nodes[spec_key] = spec_node
        spec_node = spec_nodes[spec_key]

        plan_node = None
        plan_matches = False
        if has_plan:
            plan_node = data[f"plan-{task_id}"]
            g.add((plan_node, rdflib.RDF.type, factory.Plan))
            g.add((plan_node, prov.wasDerivedFrom, spec_node))
            plan_matches = _plan_hash12(plan_path) == span.plan_hash

        diff_node = None
        diff_matches = False
        if has_diff:
            diff_node = data[f"diff-{task_id}"]
            g.add((diff_node, rdflib.RDF.type, factory.Diff))
            if plan_node is not None and plan_matches:
                g.add((diff_node, prov.wasDerivedFrom, plan_node))
            diff_matches = _diff_length(diff_path) == span.diff_length

        task_node = data[f"task-{task_id}"]
        g.add((task_node, rdflib.RDF.type, factory.Task))
        g.add((task_node, factory.endedInState, factory[row["state"]]))
        g.add((task_node, factory.riskTier, factory[row["risk"]]))
        g.add((task_node, prov.used, spec_node))

        # The last gate-holding attempt generated the exported diff: its suite judged HEAD.
        attempt_rows = ledger.attempts(task_id)
        gated = [
            r["attempt_id"]
            for r in attempt_rows
            if ledger.attempt_results(r["attempt_id"])
        ]
        generator = gated[-1] if gated and diff_node is not None else None
        for attempt_row in attempt_rows:
            phase_node = data[f"phase-{task_id}-{attempt_row['phase']}"]
            attempt_node = data[f"attempt-{attempt_row['attempt_id']}"]
            g.add((phase_node, rdflib.RDF.type, factory.Phase))
            g.add((phase_node, prov.wasInformedBy, task_node))
            g.add((attempt_node, rdflib.RDF.type, factory.Attempt))
            g.add((attempt_node, factory.withinPhase, phase_node))
            g.add(
                (
                    attempt_node,
                    factory.n,
                    rdflib.Literal(attempt_row["n"], datatype=xsd.integer),
                )
            )
            generated_diff = (
                diff_node is not None and attempt_row["attempt_id"] == generator
            )
            if generated_diff and diff_node is not None:
                g.add((attempt_node, prov.generated, diff_node))
            if attempt_row["attempt_id"] not in gated:
                continue
            suite_node = data[f"gatesuite-{attempt_row['attempt_id']}"]
            g.add((suite_node, rdflib.RDF.type, factory.GateSuite))
            g.add((suite_node, prov.wasInformedBy, attempt_node))
            if generated_diff and diff_node is not None:
                g.add((suite_node, prov.used, diff_node))

        pr_node = None
        if row["pr_url"] is not None:
            pr_node = data[f"pr-{task_id}"]
            g.add((pr_node, rdflib.RDF.type, factory.PullRequest))
            if diff_node is not None and diff_matches:
                g.add((pr_node, prov.wasDerivedFrom, diff_node))

        if diff_node is not None:
            for finding_row in ledger.findings(task_id):
                finding_node = data[f"finding-{finding_row['finding_id']}"]
                lens_node = data[f"lens-{finding_row['lens']}"]
                g.add((lens_node, rdflib.RDF.type, factory.CriticLens))
                g.add((finding_node, rdflib.RDF.type, factory.Finding))
                g.add(
                    (finding_node, factory.severity, factory[finding_row["severity"]])
                )
                g.add((finding_node, earl.assertedBy, lens_node))
                g.add((finding_node, earl.subject, diff_node))
                g.add((finding_node, earl.mode, earl.semiAuto))

        kept[task_id] = str(pr_node) if pr_node is not None else None

    _validate_and_write(g, output_path, shapes_path)
    return Projection(kept=kept, left_out=left_out)


def _validate_and_write(graph, output_path: Path, shapes_path: Path) -> None:
    import pyshacl
    import rdflib

    data_graph = rdflib.Graph()
    data_graph += graph
    data_graph.parse(VOCABULARY, format="turtle")
    for vendor_path in sorted(_VENDOR_DIR.glob("*.ttl")):
        data_graph.parse(vendor_path, format="turtle")

    shapes_graph = rdflib.Graph().parse(shapes_path, format="turtle")
    conforms, _, report_text = pyshacl.validate(
        data_graph, shacl_graph=shapes_graph, advanced=True
    )
    if not conforms:
        output_path.unlink(missing_ok=True)
        raise ProjectionError(report_text)

    text = graph.serialize(format="turtle")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=output_path.parent, prefix=f".{output_path.name}."
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp_name, output_path)
    except BaseException:
        os.unlink(tmp_name)
        raise
