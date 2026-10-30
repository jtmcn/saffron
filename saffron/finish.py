"""The stack batch's finishing layer (ADR 7).

Reads a batch's layers and every spec text it will write. Checks each
path's shape and hash before touching git, then cuts a worktree. It sits
atop the top layer's graded head when `heads` names it, else its recorded
`pushed_sha` (`DESIGN.md` §5.7). Once that worktree exists, each pending path is
checked again, this time against the tree itself, right before its own
write: a symlink on that path below the worktree makes the finish refuse
the write rather than follow the link out of the worktree. It also writes the batch's own
`findings.json`, the backlog pool a delegate files by hand.
`publish_finish` then moves a ref for the gate suite's own span, runs that
suite, and pushes the commit to its own branch. `link_stack` links the
pushed layers into one stack, and marks none ready. A follow-up layer's
latest text leaves the finishing commit. `commit_finish` writes it to a
`ran_dir` instead. `judge_draft` judges one draft's own commit against
the finishing suite, atop a given head, before a follow-up draft is ever
minted.
"""

from __future__ import annotations

import hashlib
import json
import re
import stat
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from saffron.cell.runtime import CellRuntimeError
from saffron.follow_up import Pooled
from saffron.gates.baseline import NewFailure
from saffron.intake import Spec
from saffron.ledger import _REVISION_PATH, Ledger
from saffron.phases import package as package_phase
from saffron.phases import review
from saffron.repos import mirror as git_mirror
from saffron.repos.policy import Policy

# The backlog pool file the finish writes beside its tree (`SA-0174`).
FINDINGS_NAME = "findings.json"

# ADR 7's one exception to the repo's own `protected` list: the finishing
# commit touches only a spec directly in the spec directory, never `done/`.
FINISH_TOUCHES = (".saffron/specs/*.md",)

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
    layers = ledger.stack_layers(batch_id)
    # ADR 7: stacked on an earlier pull request, so a list
    # missing it would retarget the bottom layer onto the default branch.
    if layers and layers[0]["predecessor_key"] is not None:
        return [
            "the bottom layer stacks on an earlier pull request, so nothing "
            "is linked — link it by hand"
        ]
    urls = [layer["pr_url"] for layer in layers]
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


def _refuse_symlink(workdir: Path, path: str) -> None:
    """Raise `ValueError` naming the first component of `path`, read below
    `workdir` and never above it, that `lstat` finds to already be a
    symlink. `lstat` reads the link itself, so a dangling symlink is caught
    too. A component `lstat` finds missing ends the walk: nothing below an
    absent path can already be a link."""
    accumulated = workdir
    rel = Path()
    for part in Path(path).parts:
        accumulated = accumulated / part
        rel = rel / part
        try:
            found = accumulated.lstat()
        except FileNotFoundError:
            return
        if stat.S_ISLNK(found.st_mode):
            raise ValueError(
                f"{rel} is a symlink, so the finish refuses to write through it"
            )


def commit_finish(
    ledger: Ledger,
    batch_id: int,
    unrun: list[int],
    *,
    mirror: Path,
    workdir: Path,
    ran_dir: Path,
    heads: Mapping[str, str] = {},
    emit: Callable[[str], None] = print,
) -> str | None:
    """One commit in `mirror`, atop the top layer's own entry in `heads`
    when named, else its recorded `pushed_sha`.

    Writes each layer's and each task in `unrun`'s latest spec text, except
    a follow-up layer's: its earliest `spec_texts` row carries the origin
    `follow_up`, and its latest text goes to `ran_dir` instead, one emitted
    line per text. Moves no spec into `done/` (ADR 7, amended). Raises
    `ValueError` naming a pending path's symlinked component, read below the
    cut worktree, before that path's own write. Returns the new sha, or
    `None` for a batch with no layer or a tree the writes left unchanged."""
    layers = ledger.stack_layers(batch_id)
    if not layers:
        return None
    top = layers[-1]
    if top["pushed_sha"] is None:
        raise ValueError(f"top layer {top['spec_id']!r} has no pushed_sha")

    follow_up_ids = {row["task_id"] for row in ledger.batch_follow_ups(batch_id)}

    pending: list[tuple[str, str]] = []
    ran: list[tuple[str, str, str]] = []
    for layer in layers:
        row = ledger.spec_text(layer["task_id"])
        if row is None:
            continue
        path, text = _checked(row)
        if layer["task_id"] in follow_up_ids:
            ran.append((layer["spec_id"], path, text))
        else:
            pending.append((path, text))
    for task_id in unrun:
        row = ledger.spec_text(task_id)
        if row is None:
            emit(f"finish: task {task_id} has no spec text")
            continue
        pending.append(_checked(row))

    if ran:
        ran_dir.mkdir(parents=True, exist_ok=True)
        for spec_id, path, text in ran:
            dest = ran_dir / Path(path).name
            dest.write_text(text)
            emit(
                f"finish: {spec_id} left out of the commit, its text written to {dest}"
            )

    git_mirror.add_worktree(
        mirror, heads.get(top["task_key"], top["pushed_sha"]), workdir
    )
    try:
        for path, text in pending:
            _refuse_symlink(workdir, path)
            (workdir / path).write_text(text)

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


def _render_new_failure(new_failure: NewFailure) -> str:
    """`[gate] file:line code: message`, `?` for a missing line, and no
    `file:line ` segment at all for a failure that carries no file."""
    failure = new_failure.failure
    loc = ""
    if failure.file:
        line = failure.line if failure.line is not None else "?"
        loc = f"{failure.file}:{line} "
    return f"[{new_failure.gate}] {loc}{failure.code}: {failure.message}"


def judge_draft(
    mirror: Path,
    head: str,
    path: str,
    text: str,
    *,
    workdir: Path,
    verify: Callable[[str, str], Sequence[NewFailure]],
) -> list[str]:
    """Commit `text` at `path` atop `head`, in a worktree cut at `workdir`,
    and run `verify(sha, head)` against it under a throwaway ref.

    Raises `ValueError` naming the path, before any worktree, for a `path`
    `_REVISION_PATH` does not fully match. Raises `ValueError` before
    `verify` runs for a symlink on `.saffron`, `.saffron/specs` or `path`
    itself (`_refuse_symlink`). The ref and the worktree are gone once this
    returns or raises, and a raise from `verify` reaches the caller.
    Returns one rendered line per new failure, in order."""
    if re.fullmatch(_REVISION_PATH, path) is None:
        raise ValueError(
            f"spec text path {path!r} is not a .md file directly in .saffron/specs/"
        )
    git_mirror.add_worktree(mirror, head, workdir)
    try:
        _refuse_symlink(workdir, path)
        (workdir / path).write_text(text)
        git_mirror._git(workdir, "add", "-A")
        git_mirror._git(
            workdir,
            "-c",
            "user.email=saffron@localhost",
            "-c",
            "user.name=Saffron",
            "commit",
            "-q",
            "-m",
            f"saffron judge: {path}",
        )
        sha = git_mirror._git(workdir, "rev-parse", "HEAD")
        ref = f"refs/heads/saffron-judge/{sha[:12]}"
        git_mirror._git(mirror, "update-ref", ref, sha)
        try:
            failures = verify(sha, head)
        finally:
            git_mirror._git(mirror, "update-ref", "-d", ref)
    finally:
        git_mirror.remove_worktree(mirror, workdir)
    return [_render_new_failure(failure) for failure in failures]


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


def _layer_findings(
    ledger: Ledger, layer, pooled: Sequence[Pooled], heads: Mapping[str, str]
) -> list[dict]:
    """One layer's own entries: each kept `qualifications` row, remapped
    through `pooled`, then its own critic's findings when it is a
    follow-up layer (generation 1, ADR 7). A row whose lens is not an
    in-cell lens (`review.LENSES`) takes the layer's own entry in `heads`
    when named. Only an end-review or join row was ever read at that head.
    Every other row, critic entries included, keeps `pushed_sha`."""
    task_key = layer["task_key"]
    spec_id = layer["spec_id"]
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
        head = (
            layer["pushed_sha"]
            if row["lens"] in review.LENSES
            else heads.get(task_key, layer["pushed_sha"])
        )
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
        entries.extend(
            _left_by_critic(ledger, layer["task_id"], spec_id, layer["pushed_sha"])
        )
    return entries


def write_findings(
    ledger: Ledger,
    batch_id: int,
    unrun: list[int],
    dest: Path,
    *,
    pooled: Sequence[Pooled] = (),
    heads: Mapping[str, str] = {},
) -> Path:
    """The batch's own backlog pool, one object of `batch`, `findings` and
    `follow_ups` (design section 4). `findings` walks each layer in position
    order, then each follow-up that ran and added no layer, in task order.
    `follow_ups` names each such follow-up's latest spec text. A layer's
    end-review and join entries take its own entry in `heads` when named.
    Writes `dest`, making its directory, and returns it."""
    layers = ledger.stack_layers(batch_id)
    layer_task_ids = {layer["task_id"] for layer in layers}
    unrun_ids = set(unrun)

    findings: list[dict] = []
    for layer in layers:
        findings.extend(_layer_findings(ledger, layer, pooled, heads))

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
    heads: Mapping[str, str] = {},
) -> list[str]:
    """Judge `sha` with the finishing suite, then push it and open its draft
    pull request (ADR 7). Every check below runs before the one push, in
    order, and each returns one line starting `ESCALATE` on its own failure.

    A temporary ref names `sha` for `verify`'s own span, since a gate-only
    cell's seed can only fetch a branch. Each layer's remote head is read
    against its own entry in `heads`, else its `pushed_sha`. Each pull
    request's base is read against its predecessor's branch, bottom to
    top. Only then is `sha` pushed, recorded, and handed to `gh pr create`.
    """
    layers = ledger.stack_layers(batch_id)
    top = layers[-1]
    top_head = heads.get(top["task_key"], top["pushed_sha"])
    ref = f"refs/heads/saffron-finish/{batch_id}"
    git_mirror._git(mirror, "update-ref", ref, sha)
    try:
        new_failures = verify(sha, top_head)
    except (package_phase.PackageError, CellRuntimeError) as exc:
        return [f"{ESCALATE}the finishing suite did not finish: {exc}"]
    finally:
        git_mirror._git(mirror, "update-ref", "-d", ref)
    if new_failures > 0:
        return [f"{ESCALATE}red suite, {_new_failures(new_failures)}"]

    default = package_phase.default_branch(url, cwd=mirror)
    for layer in layers:
        graded = heads.get(layer["task_key"], layer["pushed_sha"])
        head = package_phase.remote_sha(url, layer["branch"], cwd=mirror)
        if head != graded:
            got = head if head else "nothing"
            return [f"{ESCALATE}{layer['branch']} is at {got}, not {graded}"]

    by_key = {layer["task_key"]: layer for layer in layers}
    for layer in layers:
        predecessor = by_key.get(layer["predecessor_key"])
        if predecessor is not None:
            wanted = predecessor["branch"]
        elif layer["predecessor_key"] is not None:
            # The stack base's own task (ADR 7), read by its
            # record key the way `end_review.layer_fields` reads one.
            row = ledger._db.execute(
                "SELECT branch FROM tasks WHERE record_key = ?",
                (layer["predecessor_key"],),
            ).fetchone()
            wanted = row["branch"] if row is not None else default
        else:
            wanted = default
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
