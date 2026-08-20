"""v0 only: replay an already-merged pull request through the modelless half.

v1 deletes this file. Its job is taken over by scheduler.py and supervisor.py,
which run real tasks; nothing else in the tree knows this module exists.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

from saffron.gates.baseline import subtract_baseline
from saffron.gates.contract import GateResult
from saffron.gates.core.scope import scope_gate
from saffron.gates.runner import run_suite
from saffron.intake import load_spec
from saffron.ledger import Ledger
from saffron.report.index import QueueLine, render_index
from saffron.report.pr_body import render_pr_body
from saffron.repos import mirror as git_mirror
from saffron.repos.policy import load_policy


def replay(
    repo_dir: Path,
    pr_number: int,
    *,
    ledger: Ledger,
    out_dir: Path,
    mirrors_dir: Path,
    spec_path: Path | None = None,
    timeout_s: float = 900,
) -> QueueLine:
    repo_dir = repo_dir.resolve()
    name = repo_dir.name
    policy, policy_sha = load_policy(repo_dir)

    # Keyed on the origin path, not the directory name: two checkouts both
    # called "service" would otherwise share one mirror, and the second would
    # resolve its pull request against the first repo's history. The worktrees
    # carry it too — add_worktree deletes whatever sits at its path, so a path
    # two repos can both claim is a live worktree deleted mid-gate as soon as
    # anything runs concurrently.
    digest = hashlib.sha256(str(repo_dir).encode()).hexdigest()[:12]
    mirror = git_mirror.ensure_mirror(repo_dir, mirrors_dir / f"{name}-{digest}.git")
    base_sha, head_sha, _ = git_mirror.resolve_pull_request(mirror, pr_number)
    changed = git_mirror.changed_files(mirror, base_sha, head_sha)
    added, removed = git_mirror.diff_stat(mirror, base_sha, head_sha)

    spec, spec_sha = load_spec(spec_path or _sole_spec(repo_dir))

    repo_id = ledger.upsert_repo(name, str(repo_dir), str(mirror), policy_sha)
    run_id = ledger.create_run(repo_id, base_sha)
    task_id = ledger.create_task(
        run_id,
        spec.id,
        spec_sha,
        branch=f"saffron/{spec.id}",
        risk=spec.risk,
        budget_usd=spec.budget_usd,
    )

    gates = policy.gate_executables(repo_dir)
    baseline = _suite(
        mirror,
        base_sha,
        mirrors_dir / f"wt-{digest}-{spec.id}-base",
        gates,
        changed_files=[],
        touches=spec.touches,
        timeout_s=timeout_s,
    )
    head = _suite(
        mirror,
        head_sha,
        mirrors_dir / f"wt-{digest}-{spec.id}-head",
        gates,
        changed_files=changed,
        touches=spec.touches,
        timeout_s=timeout_s,
    )

    for result in baseline:
        ledger.record_gate_result(result, run_id=run_id)
    for result in head:
        ledger.record_gate_result(result, attempt_id=task_id)

    new_failures = subtract_baseline(head, baseline)
    # An errored gate aborts the attempt (CONTEXT.md §4): it contributes no
    # failures, so state read from new_failures alone calls a suite that never
    # ran "no new failures".
    errored = any(result.status == "error" for result in baseline + head)
    state = "READY_FOR_REVIEW" if not new_failures and not errored else "EXHAUSTED"
    ledger.set_task_state(task_id, state)
    ledger.finish_run(run_id, "COMPLETE")

    task_dir = out_dir / spec.id
    task_dir.mkdir(parents=True, exist_ok=True)
    _dump(task_dir / "base.json", baseline)
    _dump(task_dir / "head.json", head)
    (task_dir / "pr_body.md").write_text(
        render_pr_body(
            spec,
            head,
            new_failures,
            base_sha=base_sha,
            head_sha=head_sha,
            added=added,
            removed=removed,
            transcript_path=str(task_dir),
        )
    )

    line = QueueLine(
        repo=name,
        spec_id=spec.id,
        state=state,
        attempts=1,
        cost_usd_est=None,
        concerns=0,
        added=added,
        removed=removed,
        link=f"{spec.id}/pr_body.md",
        risk=spec.risk,
        note=_note(head, baseline, new_failures),
    )
    _write_index(out_dir, line)
    return line


def _suite(
    mirror: Path,
    sha: str,
    worktree: Path,
    gates: dict[str, Path],
    *,
    changed_files: list[str],
    touches: list[str],
    timeout_s: float,
) -> list[GateResult]:
    """Run every declared gate plus core `scope` at one sha.

    `scope` is given no changed files at base — the baseline is what the repo
    looks like before this change, and nothing has changed there.
    """
    git_mirror.add_worktree(mirror, sha, worktree)
    try:
        results = run_suite(gates, cwd=worktree, timeout_s=timeout_s)
        results.append(scope_gate(changed_files, touches))
        return results
    finally:
        git_mirror.remove_worktree(mirror, worktree)


def _sole_spec(repo_dir: Path) -> Path:
    specs = sorted((repo_dir / ".saffron" / "specs").glob("*.md"))
    if len(specs) != 1:
        raise ValueError(
            f"{len(specs)} specs in {repo_dir}/.saffron/specs — name one with --spec"
        )
    return specs[0]


def _note(
    results: list[GateResult], baseline: list[GateResult], new_failures: list
) -> str:
    errored = [r.gate for r in results if r.status == "error"]
    if errored:
        return f"errored: {', '.join(errored)}"
    parts = []
    # A gate that errored at base has no usable baseline, so its head failures
    # are unattributable rather than new — and EXHAUSTED alone reads as "this
    # task broke things", the opposite diagnosis.
    base_errored = [r.gate for r in baseline if r.status == "error"]
    if base_errored:
        parts.append(f"errored at base: {', '.join(base_errored)}")
    if new_failures:
        gates = sorted({gate for gate, _ in new_failures})
        parts.append(f"{len(new_failures)} new in {', '.join(gates)}")
    # Both, when both hold: an unusable baseline for one gate does not make the
    # new failures another gate did report disappear from the queue line.
    return "; ".join(parts) or "no new failures"


def _dump(path: Path, results: list[GateResult]) -> None:
    path.write_text(json.dumps([r.model_dump() for r in results], indent=2))


def _write_index(out_dir: Path, line: QueueLine) -> None:
    """Rewrite the index from every pr_body on disk, so replays accumulate."""
    index_lines = _existing_lines(out_dir, exclude=line.spec_id) + [line]
    _atomic_write(
        out_dir / "index.html",
        render_index(
            index_lines,
            header={
                "tasks": str(len(index_lines)),
                "spend": "—",
                "trailing accept rate": "—",
            },
        ),
    )
    _atomic_write(
        out_dir / "lines.json",
        json.dumps([vars(item) for item in index_lines], indent=2),
    )


def _atomic_write(path: Path, text: str) -> None:
    """Write via a same-directory temp file + rename, so a crash mid-write
    never leaves a truncated file for the next replay to trip over."""
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.replace(tmp_name, path)
    except BaseException:
        os.unlink(tmp_name)
        raise


def _existing_lines(out_dir: Path, exclude: str) -> list[QueueLine]:
    """The index is a rendered convenience, not a system of record: an
    unreadable or malformed lines.json is dropped, never fatal to a replay
    whose gates and ledger writes already succeeded."""
    path = out_dir / "lines.json"
    if not path.is_file():
        return []
    try:
        items = json.loads(path.read_text())
        return [QueueLine(**item) for item in items if item["spec_id"] != exclude]
    except (json.JSONDecodeError, OSError, TypeError, KeyError):
        return []
