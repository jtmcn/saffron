"""Qualifying an end review's findings into follow-up groups (ADR 7, step 4
of backlog item b-792ab2). `saffron/task.py:165-166` is what makes the tree
this reads stacked. This module never writes one.

The host decides, never the model. Each finding is anchored against its own
layer's diff, probed if it carries a probe, and filed as `qualified`,
`unverified`, `unanchored`, `note` or `killed`. A `qualified` finding joins a
`FollowUpGroup`. Everything else but `killed` joins the flat `pool`.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from saffron import end_review
from saffron.agents.findings import Finding, Severity, anchor
from saffron.cell import session
from saffron.cell.worktree import DIFF_FLAGS
from saffron.gates.contract import GateResult
from saffron.ledger import Ledger
from saffron.phases import review
from saffron.repos.mirror import GitError, _git, file_at


@dataclass(frozen=True)
class Qualified:
    """One finding, decided. `finding` is the object `anchor` and
    `session.probe_findings` mutate in place. Its `severity` can already be
    the probe's, not the one `filed` on the ledger row."""

    task_key: str
    finding: Finding
    outcome: str
    reason: str


@dataclass(frozen=True)
class FollowUpGroup:
    """One layer and one file's qualified findings, in the order the first
    of them was met."""

    task_key: str
    file: str
    findings: tuple[Qualified, ...]


@dataclass(frozen=True)
class Qualification:
    """What `qualify` returns: the groups a follow-up spec can be written
    from, and everything else that was decided but did not join one."""

    groups: list[FollowUpGroup]
    pool: list[Qualified]


def _read_head(mirror: Path, head: str, path: str) -> str | None:
    try:
        return file_at(mirror, head, path)
    except GitError:
        return None


def _layer_task(ledger: Ledger, task_key: str) -> tuple[int, int]:
    """The task and run a record key names. No public `Ledger` method maps a
    key to either (`saffron/ledger.py` is closed to this spec)."""
    row = ledger._db.execute(
        "SELECT task_id, run_id FROM tasks WHERE record_key = ?", (task_key,)
    ).fetchone()
    if row is None:
        raise ValueError(f"{task_key!r} names no task")
    return row["task_id"], row["run_id"]


def _reasons_by_probe(entries: list[dict]) -> dict[tuple[str, str, str], str]:
    return {
        (e["probe"]["file"], e["probe"]["find"], e["probe"]["replace"]): e["reason"]
        for e in entries
    }


def _qualify_range(
    ledger: Ledger,
    findings: list[Finding],
    *,
    base: str,
    task_id: int,
    task_key: str,
    run_id: int,
    spec_id: str,
    branch: str,
    diff: str,
    mirror: Path,
    repo: Path,
    gates_dir: Path,
    thread_env: Mapping[str, str],
    test_paths: Sequence[str],
    gates: dict[str, Path],
    created: set[str],
    note: Callable[[str, bool, str], None],
) -> list[Qualified]:
    """One range's already-anchored findings, probed and decided, each
    recorded under `task_id` in the order given. Builds no group.
    `qualify` does, across every range's own call, so a later one can
    extend an earlier one's."""
    filed: dict[int, Severity] = {id(f): f.severity for f in findings}
    probed = [f for f in findings if f.anchored and f.probe is not None]
    reasons: dict[tuple[str, str, str], str] = {}
    if probed:
        base_sha = _git(mirror, "rev-parse", base).strip()
        spec = session.CellSpec(
            spec_id=spec_id,
            spec_sha="",
            branch=branch,
            base_sha=base_sha,
            touches=[],
            spec_type="",
            body="",
        )
        base_results: Sequence[GateResult] = ledger.baseline_results(run_id)
        entries = session.probe_findings(
            probed,
            spec=spec,
            repo=repo,
            mirror=mirror,
            gates_dir=gates_dir,
            thread_env=thread_env,
            test_paths=test_paths,
            base_results=base_results,
            gates=gates,
            patch=diff,
            created=created,
            note=note,
        )
        reasons = _reasons_by_probe(entries)

    decided: list[Qualified] = []
    for f in findings:
        outcome, reason = _decide(f, reasons)
        ledger.record_qualification(
            task_id, finding=f, filed=filed[id(f)], outcome=outcome, reason=reason
        )
        decided.append(Qualified(task_key, f, outcome, reason))
    return decided


def _decide(f: Finding, reasons: dict[tuple[str, str, str], str]) -> tuple[str, str]:
    if not f.anchored:
        return "unanchored", ""
    if f.probe is None:
        return ("note", "") if f.severity == "note" else ("qualified", "")
    key = (f.probe.file, f.probe.find, f.probe.replace)
    if f.probe_verdict == "killed":
        return "killed", ""
    if f.probe_verdict == "survived":
        return "qualified", ""
    return "unverified", reasons.get(key, "")


def qualify(
    ledger: Ledger,
    layers: Sequence[end_review.LayerReview],
    join: review.LensReview | None,
    *,
    mirror: Path,
    repo: Path,
    gates_dir: Path,
    thread_env: Mapping[str, str],
    test_paths: Sequence[str],
    gates: dict[str, Path],
    created: set[str],
    note: Callable[[str, bool, str], None],
) -> Qualification:
    """Every reached layer's end-review findings, anchored, probed and
    decided, top down. `join` is not walked yet. `SA-0147` replaces this
    guard once it is."""
    if join is not None:
        raise ValueError("the join lens is not walked yet (SA-0147)")

    groups: dict[tuple[str, str], list[Qualified]] = {}
    pool: list[Qualified] = []
    for layer in layers:
        if not layer.reviews:
            continue
        fields = end_review.layer_fields(ledger, layer.task_key)
        task_id, run_id = _layer_task(ledger, layer.task_key)
        head = fields.head
        diff = _git(mirror, "diff", *DIFF_FLAGS, f"{head}^..{head}", strip=False)
        inputs = [f for r in layer.reviews for f in r.findings]
        anchored = anchor(inputs, diff, read_head=partial(_read_head, mirror, head))
        decided = _qualify_range(
            ledger,
            anchored,
            base=f"{head}^",
            task_id=task_id,
            task_key=layer.task_key,
            run_id=run_id,
            spec_id=fields.spec_id,
            branch=fields.branch,
            diff=diff,
            mirror=mirror,
            repo=repo,
            gates_dir=gates_dir,
            thread_env=thread_env,
            test_paths=test_paths,
            gates=gates,
            created=created,
            note=note,
        )
        for q in decided:
            if q.outcome == "qualified":
                groups.setdefault((q.task_key, q.finding.file), []).append(q)
            elif q.outcome != "killed":
                pool.append(q)

    return Qualification(
        groups=[
            FollowUpGroup(task_key=k[0], file=k[1], findings=tuple(v))
            for k, v in groups.items()
        ],
        pool=pool,
    )
