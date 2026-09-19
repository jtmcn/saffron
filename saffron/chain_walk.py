"""The checked walk — the other half of Q4's comparison (`SA-0108`,
`DESIGN.md` Appendix T, backlog item b-946f03).

`saffron.projection.materialize` (`SA-0107`) builds the RDF projection Q4
runs over. Nothing yet runs Q4 over it, and nothing compares Q4's answer
against anything — Appendix T's decision rule needs an independent notion of
"whole", built without reading the graph the projection wrote, or the
comparison would just be the projection agreeing with itself.

The walk here follows the ledger's own foreign keys (`runs`, `tasks`,
`attempts`, `gate_results` — `saffron/ledger.py`) and the batch tree's stored
files directly, never `saffron/projection.py` (forbidden to this spec) and
never `events.jsonl` (reading the log would make this the projection, and the
comparison would say nothing). A task's chain is whole only when its ledger
rows reach an attempt holding a gate result and a pull request, and its
stored `plan.json` and `patch.diff` exist — the four things, no more: a
`patch.json` sits beside `patch.diff` but Q4 never reads it, so neither does
this.

`compare_chains` then runs the walk over every merged task the projection
kept (`Projection.kept`, `SA-0107`'s own comparison key, since a `pr_url` can
be shared by more than one task) and reports the ones Q4 dropped anyway — a
break. A merged task the projection left out is counted apart, by the reason
`Projection.left_out` already gives it, and never printed as a break: it
never reached the comparison at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from saffron import projection as projection_module
from saffron.ledger import Ledger
from saffron.projection import LeftOutReason, Projection

_ROOT = Path(__file__).resolve().parent.parent
Q4_QUERY = _ROOT / "ontology" / "queries" / "Q4-derivation-chain.rq"


@dataclass(frozen=True)
class Break:
    """One merged, walk-whole task Q4 dropped anyway."""

    task_id: int
    spec_id: str


@dataclass(frozen=True)
class ChainComparison:
    """What running the walk over the projection's merged, kept tasks found.

    `compared` counts only tasks that reached the comparison — a merged task
    the projection left out never did, and is counted in `left_out` instead,
    by the reason `Projection.left_out` already gives it. A `0`/`0` reading
    is therefore "nothing merged was comparable", not "nothing broke"."""

    compared: int
    breaks: tuple[Break, ...]
    left_out: dict[LeftOutReason, int]


def _task_rows(ledger: Ledger) -> dict[int, dict]:
    """`task_id -> {spec_id, state, pr_url}`, joined through `runs` — the walk's
    own first hop, even though a task with no `runs` row cannot exist (the
    foreign key forbids it): this is what makes the read "reach" through the
    ledger's tables rather than assume the column sits on `tasks` alone."""
    rows = ledger._db.execute(
        """SELECT t.task_id, t.spec_id, t.state, t.pr_url
             FROM tasks t
             JOIN runs r ON r.run_id = t.run_id
            ORDER BY t.task_id"""
    ).fetchall()
    return {row["task_id"]: dict(row) for row in rows}


def checked_walk(
    ledger: Ledger, out_dir: Path, task_id: int, spec_id: str, pr_url: str | None
) -> bool:
    """Whole iff the ledger holds an attempt with a gate result and a pull
    request, and the batch tree still holds this task's `plan.json` and
    `patch.diff` — the four things Appendix T narrows this walk to, no
    fifth. Reads no event log and states no edge; it only answers whole or
    broken for one task."""
    if pr_url is None:
        return False
    has_gated_attempt = any(
        ledger.attempt_results(row["attempt_id"]) for row in ledger.attempts(task_id)
    )
    if not has_gated_attempt:
        return False
    task_dir = out_dir / spec_id
    return (task_dir / "plan.json").is_file() and (task_dir / "patch.diff").is_file()


def _q4_pull_requests(output_path: Path) -> frozenset[str]:
    """Every `?pr` Q4 actually reaches, read from Saffron's own source tree —
    never a target repo's — the way `SA-0107`'s own tests already do."""
    import pyoxigraph as ox

    store = ox.Store()
    store.bulk_load(path=str(output_path), format=ox.RdfFormat.TURTLE)
    result = store.query(Q4_QUERY.read_text())
    assert isinstance(result, ox.QuerySolutions), type(result).__name__
    return frozenset(row["pr"].value for row in result)


def compare_chains(
    ledger: Ledger, out_dir: Path, projection: Projection, output_path: Path
) -> ChainComparison:
    """Run the walk over every merged task the projection kept, and Q4 over
    the graph the projection just wrote to `output_path` — one call, so the
    two are judged against the same materialization. Compare like with like:
    a task the ledger does not record as `MERGED`, kept or left out alike, is
    skipped entirely, never counted and never printed."""
    q4_prs = _q4_pull_requests(output_path)
    rows = _task_rows(ledger)

    compared = 0
    breaks: list[Break] = []
    for task_id, pr_iri in projection.kept.items():
        row = rows[task_id]
        if row["state"] != "MERGED":
            continue
        compared += 1
        whole = checked_walk(ledger, out_dir, task_id, row["spec_id"], row["pr_url"])
        reached = pr_iri is not None and pr_iri in q4_prs
        if whole and not reached:
            breaks.append(Break(task_id=task_id, spec_id=row["spec_id"]))

    left_out: dict[LeftOutReason, int] = {}
    for task_id, left in projection.left_out.items():
        row = rows[task_id]
        if row["state"] != "MERGED":
            continue
        left_out[left.reason] = left_out.get(left.reason, 0) + 1

    return ChainComparison(compared=compared, breaks=tuple(breaks), left_out=left_out)


def materialize_and_compare(
    ledger: Ledger, out_dir: Path, output_path: Path
) -> ChainComparison:
    """`saffron chains`'s one call: materialize, then compare. Goes through
    the module object, never a bound name, so a caller (a test) that
    monkeypatches `saffron.projection.materialize` is observed here too."""
    projection = projection_module.materialize(ledger, out_dir, output_path)
    return compare_chains(ledger, out_dir, projection, output_path)
