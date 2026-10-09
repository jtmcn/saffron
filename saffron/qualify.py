"""Qualifying an end review's findings into follow-up groups (ADR 7, step 4
of backlog item b-792ab2). `saffron/task.py:165-166` is what makes the tree
this reads stacked. This module never writes one.

The host decides, never the model. Each finding is anchored against its own
range's diff, probed if it carries a probe, and filed as `qualified`,
`unverified`, `unanchored`, `note` or `killed`. A `qualified` finding joins a
`FollowUpGroup`. Everything else but `killed` joins the flat `pool`. The join
lens's findings are walked first, over the whole stack, under the top
layer's task. Each layer is then walked top down: its end-review findings,
then its own in-cell REVIEW concerns.
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
from saffron.intake import Mutant
from saffron.ledger import Ledger
from saffron.phases import review
from saffron.repos.mirror import _git, file_at


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


def _layer_task(ledger: Ledger, task_key: str) -> tuple[int, int]:
    """The task and run a record key names. No public `Ledger` method maps a
    key to either."""
    row = ledger._db.execute(
        "SELECT task_id, run_id FROM tasks WHERE record_key = ?", (task_key,)
    ).fetchone()
    if row is None:
        raise ValueError(f"{task_key!r} names no task")
    return row["task_id"], row["run_id"]


def _reasons_by_probe(entries: list[dict]) -> dict[tuple[str, str, str], str]:
    return {
        review.probe_key(Mutant.model_validate(e["probe"])): e["reason"]
        for e in entries
    }


def _in_cell_concerns(ledger: Ledger, task_id: int) -> list[Finding]:
    """A layer's own REVIEW concerns: a finding of a lens in
    `review.LENSES`, filed as `concern`, rebuilt with no probe, in the
    order `Ledger.findings` recorded them. The `findings` table keeps no
    probe, so none of these reaches the probe call."""
    return [
        Finding(
            lens=row["lens"],
            severity=row["severity"],
            file=row["file"],
            line=row["line"],
            claim=row["claim"],
        )
        for row in ledger.findings(task_id)
        if row["lens"] in review.LENSES and row["severity"] == "concern"
    ]


def _qualify_range(
    ledger: Ledger,
    inputs: list[Finding],
    *,
    base: str,
    head: str,
    task_id: int,
    task_key: str,
    run_id: int,
    spec_id: str,
    branch: str,
    mirror: Path,
    repo: Path,
    gates_dir: Path,
    thread_env: Mapping[str, str],
    test_paths: Sequence[str],
    gates: dict[str, Path],
    created: set[str],
    note: Callable[[str, bool, str], None],
) -> list[Qualified]:
    """One range's findings, anchored over `base..head`, probed and decided,
    each recorded under `task_id` in the order given. Builds no group.
    `qualify` does, across every range's own call, so a later one can
    extend an earlier one's. A read the mirror cannot answer raises before
    any finding in the range is recorded."""
    diff = _git(mirror, "diff", *DIFF_FLAGS, f"{base}..{head}", strip=False)
    findings = anchor(inputs, diff, read_head=partial(file_at, mirror, head))
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
        try:
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
        except RuntimeError as exc:
            # A patch that did not apply, or git failing. A cell that never came
            # up reaches no caller: `probe_findings` reads it as `unproven`.
            reasons = {}
            for f in probed:
                assert f.probe is not None  # this loop built `probed` from it
                reasons[review.probe_key(f.probe)] = str(exc)
        else:
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
        if f.lens == "adequacy":
            # A real adequacy finding always carries a probe (§5.5). One
            # without it is an in-cell concern its probe did not survive.
            return "unverified", "its REVIEW probe did not survive"
        return ("note", "") if f.severity == "note" else ("qualified", "")
    key = review.probe_key(f.probe)
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
    """The join's findings first, over the whole stack, then every layer's
    end-review findings and in-cell concerns, top down. Groups and pools
    the findings every range decides across the whole walk, so the join's
    findings and the top layer's own can share one group. A read the mirror
    cannot answer raises out of it, and ranges walked earlier keep their rows."""
    groups: dict[tuple[str, str], list[Qualified]] = {}
    pool: list[Qualified] = []

    def _fold(decided: list[Qualified]) -> None:
        for q in decided:
            if q.outcome == "qualified":
                groups.setdefault((q.task_key, q.finding.file), []).append(q)
            elif q.outcome != "killed":
                pool.append(q)

    if join is not None and layers:
        top = end_review.layer_fields(ledger, layers[0].task_key)
        bottom = end_review.layer_fields(ledger, layers[-1].task_key)
        top_task_id, _ = _layer_task(ledger, layers[0].task_key)
        _, bottom_run_id = _layer_task(ledger, layers[-1].task_key)
        _fold(
            _qualify_range(
                ledger,
                list(join.findings),
                base=f"{bottom.head}^",
                head=top.head,
                task_id=top_task_id,
                task_key=layers[0].task_key,
                run_id=bottom_run_id,
                spec_id=top.spec_id,
                branch=top.branch,
                mirror=mirror,
                repo=repo,
                gates_dir=gates_dir,
                thread_env=thread_env,
                test_paths=test_paths,
                gates=gates,
                created=created,
                note=note,
            )
        )

    for layer in layers:
        task_id, run_id = _layer_task(ledger, layer.task_key)
        inputs = [f for r in layer.reviews for f in r.findings]
        inputs += _in_cell_concerns(ledger, task_id)
        if not inputs:
            continue
        fields = end_review.layer_fields(ledger, layer.task_key)
        _fold(
            _qualify_range(
                ledger,
                inputs,
                base=f"{fields.head}^",
                head=fields.head,
                task_id=task_id,
                task_key=layer.task_key,
                run_id=run_id,
                spec_id=fields.spec_id,
                branch=fields.branch,
                mirror=mirror,
                repo=repo,
                gates_dir=gates_dir,
                thread_env=thread_env,
                test_paths=test_paths,
                gates=gates,
                created=created,
                note=note,
            )
        )

    return Qualification(
        groups=[
            FollowUpGroup(task_key=k[0], file=k[1], findings=tuple(v))
            for k, v in groups.items()
        ],
        pool=pool,
    )
