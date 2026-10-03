"""The stack batch's finishing layer (ADR 7).

Reads a batch's layers and every spec text it will write. Checks each one
before touching git, then commits them atop the top layer's own head. It
also writes the batch's own `findings.json`, the backlog pool a delegate
files by hand. `publish_finish` then moves a ref for the gate suite's own
span, runs that suite, and pushes the commit to its own branch.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Sequence
from pathlib import Path

from saffron.cell.runtime import CellRuntimeError
from saffron.follow_up import Pooled
from saffron.intake import Spec, discover_specs
from saffron.ledger import _REVISION_PATH, Ledger
from saffron.phases import package as package_phase
from saffron.phases import review
from saffron.repos import mirror as git_mirror
from saffron.repos.policy import Policy
from saffron.scheduler import RETIRED_DIRNAME

# The backlog pool file the finish writes beside its tree (`SA-0174`).
FINDINGS_NAME = "findings.json"

# ADR 7's one exception to the repo's own `protected` list: the finishing
# commit touches only a spec directly in the spec directory or in `done/`.
FINISH_TOUCHES = (".saffron/specs/*.md", ".saffron/specs/done/*.md")

# The prefixes of `publish_finish`'s first line. `SA-0170` links a pushed
# stack only once a line starts with `PUSHED`.
ESCALATE = "escalate: "
PUSHED = "pushed "


def link_stack(
    ledger: Ledger,
    batch_id: int,
    *,
    mirror: Path,
    url: str,
    gh: package_phase.GhRunner,
) -> list[str]:
    """Link a pushed stack with `gh stack link`, finishing layer included.

    Raises `ValueError` naming the batch when the finishing row is missing
    or carries no `pr_url`, before any `gh` call. Passes pull request URLs,
    bottom to top, finishing layer last: gh-stack pushes a branch argument,
    never a pull request's. Marks no pull request ready.
    """
    finishing = ledger.stack_finish(batch_id)
    if finishing is None or finishing["pr_url"] is None:
        raise ValueError(f"batch {batch_id} has no finishing pull request")
    urls = [layer["pr_url"] for layer in ledger.stack_layers(batch_id)]
    urls.append(finishing["pr_url"])
    default = package_phase.default_branch(url, cwd=mirror)
    done = gh(["gh", "stack", "link", "--base", default, *urls])
    if done.returncode == 127:
        return [
            "gh could not start, so nothing is linked and every pull request "
            f"stays a draft: {done.stderr.strip()}"
        ]
    if done.returncode != 0:
        return [
            "gh stack link failed, so every pull request stays a draft: "
            f"{done.stderr.strip()}"
        ]
    return [f"linked {len(urls)} pull requests"]


def finish_suite(policy: Policy) -> tuple[Spec, Policy]:
    """The spec and policy the finishing commit's own gate suite runs under.

    The spec is a `chore` whose only allowed paths are `FINISH_TOUCHES`
    (`DESIGN.md` §5.4, ADR 7). The policy is the repo's own, copied with its
    `protected` list emptied and its suppression scan turned off for this
    commit alone. Every other field, including its declared gates, stays as
    the repo declared it.
    """
    spec = Spec(
        id="FINISH-0",
        title="the finishing layer",
        type="chore",
        touches=list(FINISH_TOUCHES),
    )
    finishing_policy = policy.model_copy(
        update={
            "protected": [],
            "integrity": policy.integrity.model_copy(update={"suppressions": []}),
        }
    )
    return spec, finishing_policy


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


def _new_failures(n: int) -> str:
    return f"{n} new failure" + ("" if n == 1 else "s")


def publish_finish(
    ledger: Ledger,
    batch_id: int,
    sha: str,
    *,
    mirror: Path,
    url: str,
    slug: str,
    verify: Callable[[str, str], int],
    gh: package_phase.GhRunner,
    workdir: Path,
) -> list[str]:
    """Judge `sha` with the finishing suite, then push it and open its draft
    pull request (ADR 7). Every check below runs before the one push, in
    order, and each returns one line starting `ESCALATE` on its own failure.

    A temporary ref names `sha` for `verify`'s own span, since a gate-only
    cell's seed can only fetch a branch. Every layer's remote head is then
    read against its own `pushed_sha`, and every pull request's base against
    its predecessor's branch, bottom to top. Only then is `sha` pushed to
    its own branch, recorded, and handed to `gh pr create`.
    """
    layers = ledger.stack_layers(batch_id)
    top = layers[-1]
    ref = f"refs/heads/saffron-finish/{batch_id}"
    git_mirror._git(mirror, "update-ref", ref, sha)
    try:
        new_failures = verify(sha, top["pushed_sha"])
    except (package_phase.PackageError, CellRuntimeError) as exc:
        return [f"{ESCALATE}the finishing suite did not finish: {exc}"]
    finally:
        git_mirror._git(mirror, "update-ref", "-d", ref)
    if new_failures > 0:
        return [f"{ESCALATE}red suite, {_new_failures(new_failures)}"]

    default = package_phase.default_branch(url, cwd=mirror)
    for layer in layers:
        head = package_phase.remote_sha(url, layer["branch"], cwd=mirror)
        if head != layer["pushed_sha"]:
            got = head if head else "nothing"
            return [
                f"{ESCALATE}{layer['branch']} is at {got}, not {layer['pushed_sha']}"
            ]

    by_key = {layer["task_key"]: layer for layer in layers}
    for layer in layers:
        predecessor = by_key.get(layer["predecessor_key"])
        wanted = predecessor["branch"] if predecessor is not None else default
        view = gh(
            [
                "gh",
                "pr",
                "view",
                layer["pr_url"],
                "--json",
                "baseRefName",
                "--jq",
                ".baseRefName",
            ]
        )
        base = view.stdout.strip() if view.returncode == 0 else None
        if base != wanted:
            got = base if base is not None else "nothing readable"
            return [
                f"{ESCALATE}{layer['spec_id']}'s pull request targets {got}, "
                f"not {wanted}"
            ]

    branch = f"saffron/batch-{batch_id}-finish"
    git_mirror.add_worktree(mirror, sha, workdir)
    worktree_error: git_mirror.GitError | None = None
    try:
        try:
            package_phase.push_with_lease(workdir, url=url, branch=branch, expect="")
        except package_phase.LeaseRejected:
            return [f"{ESCALATE}{branch} already exists"]
        ledger.record_stack_finish(batch_id, branch=branch, head_sha=sha)
        body_path = workdir.parent / "pr-body.md"
        body_path.write_text(f"Batch {batch_id}'s finishing layer.\n")
        pr_url = package_phase.open_draft_pr(
            slug=slug,
            branch=branch,
            base=top["branch"],
            title=f"saffron batch {batch_id}: finishing layer",
            body_path=body_path,
            gh=gh,
        )
        ledger.record_stack_finish(batch_id, branch=branch, head_sha=sha, pr_url=pr_url)
    finally:
        try:
            git_mirror.remove_worktree(mirror, workdir)
        except git_mirror.GitError as exc:
            worktree_error = exc

    lines = [f"{PUSHED}{sha[:12]} to {branch}, draft pull request {pr_url}"]
    if worktree_error is not None:
        lines.append(f"worktree left at {workdir}: GitError: {worktree_error}")
    return lines
