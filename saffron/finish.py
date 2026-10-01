"""The stack batch's finishing layer (ADR 7).

Reads a batch's layers and every spec text it will write. Checks each one
before touching git, then commits them atop the top layer's own head. It
also writes the batch's own `findings.json`, the backlog pool a delegate
files by hand. No ref moves and no gate executes here: that is `SA-0167`'s
own job.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Sequence
from pathlib import Path

from saffron.follow_up import Pooled
from saffron.intake import discover_specs
from saffron.ledger import _REVISION_PATH, Ledger
from saffron.phases import review
from saffron.repos import mirror as git_mirror
from saffron.scheduler import RETIRED_DIRNAME

# The backlog pool file the finish writes beside its tree (`SA-0174`).
FINDINGS_NAME = "findings.json"


def _checked(row) -> tuple[str, str]:
    path = row["path"]
    # The writer's own pattern, so this last check is never looser than it.
    if re.fullmatch(_REVISION_PATH, path) is None:
        raise ValueError(
            f"spec text path {path!r} is not a .md file directly in .saffron/specs/"
        )
    text = row["text"]
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != row["spec_sha"]:
        raise ValueError(f"spec text for {row['spec_id']!r} does not match its hash")
    return path, text


def commit_finish(
    ledger: Ledger,
    batch_id: int,
    unrun: list[int],
    *,
    mirror: Path,
    workdir: Path,
    emit: Callable[[str], None] = print,
) -> str | None:
    """One commit in `mirror`, atop the top layer's recorded `pushed_sha`.

    Writes each layer's and each task in `unrun`'s latest spec text, then
    retires each layer's file into `done/`. Returns the new sha, or `None`
    for a batch with no layer or a tree the writes left unchanged."""
    layers = ledger.stack_layers(batch_id)
    if not layers:
        return None
    top = layers[-1]
    if top["pushed_sha"] is None:
        raise ValueError(f"top layer {top['spec_id']!r} has no pushed_sha")

    pending: list[tuple[str, str]] = []
    for layer in layers:
        row = ledger.spec_text(layer["task_id"])
        if row is not None:
            pending.append(_checked(row))
    for task_id in unrun:
        row = ledger.spec_text(task_id)
        if row is None:
            emit(f"finish: task {task_id} has no spec text")
            continue
        pending.append(_checked(row))

    git_mirror.add_worktree(mirror, top["pushed_sha"], workdir)
    try:
        for path, text in pending:
            (workdir / path).write_text(text)
        specs_dir = workdir / ".saffron" / "specs"
        discovered, _failures = discover_specs(specs_dir)
        by_id = {d.spec.id: d.path for d in discovered}
        done_dir = specs_dir / RETIRED_DIRNAME
        done_dir.mkdir(exist_ok=True)
        for layer in layers:
            found = by_id.get(layer["spec_id"])
            if found is not None:
                found.rename(done_dir / found.name)

        git_mirror._git(workdir, "add", "-A")
        # Its exit code is the answer, so it alone runs unchecked.
        unchanged = git_mirror._run(
            ["git", "-C", str(workdir), "diff", "--cached", "--quiet"]
        )
        if unchanged.returncode == 0:
            return None
        git_mirror._git(
            workdir,
            "-c",
            "user.email=saffron@localhost",
            "-c",
            "user.name=Saffron",
            "commit",
            "-q",
            "-m",
            f"saffron batch {batch_id}: finishing layer",
        )
        return git_mirror._git(workdir, "rev-parse", "HEAD")
    finally:
        git_mirror.remove_worktree(mirror, workdir)


def _match_pooled(pooled: Sequence[Pooled], task_key: str, row) -> Pooled | None:
    """The first `Pooled` naming this layer's key and the row's file whose
    group holds a finding at the row's lens, line and claim. Checks no
    severity: the group's finding can already carry a probe's promotion."""
    for p in pooled:
        if p.group.task_key != task_key or p.group.file != row["file"]:
            continue
        for qualified in p.group.findings:
            found = qualified.finding
            if (
                found.lens == row["lens"]
                and found.line == row["line"]
                and found.claim == row["claim"]
            ):
                return p
    return None


def _left_by_critic(
    ledger: Ledger, task_id: int, spec_id: str, head: str | None
) -> list[dict]:
    """The findings a task's own critic left that `qualify` never read: ADR 7
    sends these to the backlog rather than a second generation. Keeps a lens
    `review.LENSES` names, in the order `Ledger.findings` recorded them."""
    return [
        {
            "spec_id": spec_id,
            "head": head,
            "lens": row["lens"],
            "severity": row["severity"],
            "file": row["file"],
            "line": row["line"],
            "claim": row["claim"],
            "outcome": "left_by_critic",
            "reason": row["verdict"] or "",
        }
        for row in ledger.findings(task_id)
        if row["lens"] in review.LENSES
    ]


def _layer_findings(ledger: Ledger, layer, pooled: Sequence[Pooled]) -> list[dict]:
    """One layer's own entries: each kept `qualifications` row, remapped
    through `pooled`, then its own critic's findings when it is a
    follow-up layer (generation 1, ADR 7)."""
    task_key = layer["task_key"]
    spec_id = layer["spec_id"]
    head = layer["pushed_sha"]
    entries: list[dict] = []
    for row in ledger.qualifications(layer["task_id"]):
        outcome = row["outcome"]
        if outcome == "killed":
            continue
        if outcome == "qualified":
            match = _match_pooled(pooled, task_key, row)
            outcome, reason = ("pooled", match.reason) if match else ("follow_up", "")
        else:
            reason = row["reason"]
        entries.append(
            {
                "spec_id": spec_id,
                "head": head,
                "lens": row["lens"],
                "severity": row["severity"],
                "file": row["file"],
                "line": row["line"],
                "claim": row["claim"],
                "outcome": outcome,
                "reason": reason,
            }
        )
    if layer["generation"] == 1:
        entries.extend(_left_by_critic(ledger, layer["task_id"], spec_id, head))
    return entries


def write_findings(
    ledger: Ledger,
    batch_id: int,
    unrun: list[int],
    dest: Path,
    *,
    pooled: Sequence[Pooled] = (),
) -> Path:
    """The batch's own backlog pool, one object of `batch`, `findings` and
    `follow_ups` (design section 4). `findings` walks each layer in position
    order, then each follow-up that ran and added no layer, in task order.
    `follow_ups` names each such follow-up's latest spec text.
    Writes `dest`, making its directory, and returns it."""
    layers = ledger.stack_layers(batch_id)
    layer_task_ids = {layer["task_id"] for layer in layers}
    unrun_ids = set(unrun)

    findings: list[dict] = []
    for layer in layers:
        findings.extend(_layer_findings(ledger, layer, pooled))

    follow_up_rows = [
        row
        for row in ledger.batch_follow_ups(batch_id)
        if row["task_id"] not in layer_task_ids and row["task_id"] not in unrun_ids
    ]
    for row in follow_up_rows:
        findings.extend(
            _left_by_critic(ledger, row["task_id"], row["spec_id"], row["pushed_sha"])
        )

    follow_ups: list[dict] = []
    for row in follow_up_rows:
        text = ledger.spec_text(row["task_id"])
        # Always set: a follow-up's first spec_texts row is what named it one.
        assert text is not None
        follow_ups.append(
            {
                "spec_id": row["spec_id"],
                "state": row["state"],
                "path": text["path"],
                "text": text["text"],
            }
        )

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(
            {"batch": batch_id, "findings": findings, "follow_ups": follow_ups},
            indent=2,
        )
    )
    return dest
