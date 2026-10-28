"""`saffron review <task id> --repo .` reads a pull request's own review
commits. It judges them with the end review's per-layer lenses (backlog
item b-549012, `DESIGN.md` §5.7).

PACKAGE pushes one commit, and an operator's review commits land on top of
it. Neither the in-cell lenses nor REBUT read those. This command reuses
`end_review`'s own Spec and Standards lenses over that slice alone. The
slice runs from the packaged head, or its rebased copy after a restack, to
the branch's current head. It charges the session to the task under its
own phase. It writes its findings beside the task, never through
`record_findings` or `record_end_review`. Either row there would make
`saffron finish` refuse the batch, and a `findings` row names no head.
"""

from __future__ import annotations

import json
import os
from functools import partial, wraps
from pathlib import Path

from saffron import end_review
from saffron.agents import context
from saffron.cell.session import _SAFFRON_ROOT, TURN_TIMEOUT_S, stop_on_rejected
from saffron.events import describe
from saffron.intake import SpecError, load_spec, parse_spec
from saffron.ledger import Ledger
from saffron.phases import implement
from saffron.phases import package as package_phase
from saffron.repos import mirror as git_mirror
from saffron.repos.policy import load_policy

# Open is the only state this reads. A merged or closed pull request has no
# branch left to read review commits off.
_JUDGEABLE_STATE = "OPEN"


class _Declined(Exception):
    """Internal to this module: a task this command will not read.

    Named differently from `Refusal` on purpose, since
    `tests/test_refusal_count.py` scans every file but `scheduler.py` for
    that constructor. It declines a task before any cell opens, and is not
    one of §4.2.1's eight queue-scan kinds."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


_TASK_ROW = """
    SELECT t.task_id, t.spec_id, t.spec_sha, t.branch, t.pr_url, t.pushed_sha,
           r.run_id, r.base_sha, r.repo_id
    FROM tasks t JOIN runs r ON r.run_id = t.run_id
    WHERE t.task_id = ?
"""


def _task_and_run(ledger: Ledger, task_id: int, repo: Path, url: str):
    row = ledger._db.execute(_TASK_ROW, (task_id,)).fetchone()
    if row is None:
        raise _Declined(f"task {task_id} names no task")
    if not row["pr_url"]:
        raise _Declined(f"task {task_id} carries no pull request")
    if not row["pushed_sha"] or not row["branch"]:
        raise _Declined(f"task {task_id} has no packaged head")
    wanted = ledger.resolve_repo_id(url)
    if wanted is None or wanted != row["repo_id"]:
        raise _Declined(f"task {task_id} belongs to another repo than {repo}")
    return row


def _pr_state(gh: package_phase.GhRunner, pr_url: str) -> None:
    done = gh(["gh", "pr", "view", pr_url, "--json", "state"])
    if done.returncode != 0:
        raise RuntimeError(f"gh pr view {pr_url} failed: {done.stderr.strip()[:300]}")
    state = json.loads(done.stdout)["state"]
    if state != _JUDGEABLE_STATE:
        raise _Declined(f"{pr_url} is {state}, not {_JUDGEABLE_STATE}")


def _fetch_head(mirror: Path, url: str, branch: str) -> str:
    # `fetch_parent_branch`'s own message would call this branch a parent.
    try:
        return package_phase.fetch_parent_branch(mirror, url, branch)
    except package_phase.ParentGone as gone:
        raise package_phase.PackageError(
            f"task branch {branch} could not be fetched"
        ) from gone


def _full_message(mirror: Path, sha: str) -> str:
    return git_mirror._git(mirror, "show", "-s", "--format=%B", sha)


def _first_parent_chain(mirror: Path, head: str) -> list[str]:
    out = git_mirror._git(mirror, "log", "--first-parent", "--format=%H", head)
    return out.splitlines() if out else []


def _rebased_copy(mirror: Path, head: str, pushed_sha: str) -> str | None:
    """The newest commit on `head`'s first-parent chain whose full message
    equals `pushed_sha`'s. The chain is read newest first, so the first
    match is the newest one. A later review commit that repeats the
    packaged subject with a different body never matches, since the full
    message, not the subject alone, decides."""
    message = _full_message(mirror, pushed_sha)
    for sha in _first_parent_chain(mirror, head):
        if _full_message(mirror, sha) == message:
            return sha
    return None


def _range_start(mirror: Path, pushed_sha: str, head: str) -> str:
    """The range's own start: `pushed_sha` when it is still an ancestor of
    `head`, otherwise its rebased copy after a restack. Declines an empty
    range either way, and a head that carries the packaged commit nowhere
    at all."""
    if end_review._is_ancestor(mirror, pushed_sha, head):
        if pushed_sha == head:
            raise _Declined(f"{head} is the packaged head")
        return pushed_sha
    copy = _rebased_copy(mirror, head, pushed_sha)
    if copy is None:
        raise _Declined(f"{head} holds no packaged commit")
    if copy == head:
        raise _Declined(f"{head} is the packaged commit's rebased copy")
    return copy


def _spec_for_task(
    ledger: Ledger, task_id: int, exported: Path, spec_id: str, spec_sha: str
):
    recorded = ledger.spec_text(task_id)
    if recorded is not None:
        try:
            return parse_spec(recorded["text"])
        except SpecError as exc:
            raise _Declined(
                f"task {task_id}'s recorded text does not parse: {exc}"
            ) from exc
    specs_dir = exported / ".saffron" / "specs"
    candidates = sorted(specs_dir.glob(f"{spec_id}-*.md")) if specs_dir.is_dir() else []
    if not candidates:
        raise _Declined(f"no spec file for {spec_id} under {specs_dir}")
    spec, file_sha = load_spec(candidates[0])
    if file_sha != spec_sha:
        raise _Declined(
            f"{candidates[0].name} does not hash to task {task_id}'s spec_sha"
        )
    return spec


def _token() -> str:
    token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "")
    if not token.strip():
        raise _Declined("CLAUDE_CODE_OAUTH_TOKEN is unset")
    return token


_FRAMING = (
    "This diff holds only the review commits made after the cell's packaged "
    "head, from `{range_start}` to `{head}`. A criterion the diff meets "
    "below that range is not unmet."
)


def _framed_body(body: str, range_start: str, head: str) -> str:
    framing = _FRAMING.format(range_start=range_start, head=head)
    return f"{framing}\n\n{body}"


def _close(
    ledger: Ledger, attempt_id: int, attempt: implement.AttemptResult | None
) -> None:
    ledger.close_attempt(
        attempt_id,
        session_id=attempt.session_id if attempt else None,
        model=attempt.model if attempt else None,
        # A turn that produced no result at all is not a turn that succeeded,
        # and $0.00 here is measured absence, not a crash's zeroed fields.
        subtype=attempt.subtype if attempt else "error",
        terminal_reason=attempt.terminal_reason if attempt else None,
        num_turns=attempt.num_turns if attempt else 0,
        cost_usd_est=attempt.cost_usd_est if attempt else 0.0,
        cost_floor_usd_est=attempt.cost_floor_usd_est if attempt else None,
    )


def _charging(agent, *, ledger: Ledger, task_id: int):
    """Every turn opened and closed under phase `COMMIT_REVIEW`, never the
    task's own state: `session.record_attempts` defaults to that state, and
    this session never moves it (§4.1). On `AgentFailed` the attempt still
    closes, from the failed turn's own `attempt`, before the exception
    reaches `run_lens`."""

    @wraps(agent)
    def charged(*args: object, **kwargs: object) -> implement.AttemptResult:
        attempt_id = ledger.open_attempt(task_id, phase="COMMIT_REVIEW")
        try:
            attempt = agent(*args, **kwargs)
        except implement.AgentFailed as failed:
            _close(ledger, attempt_id, failed.attempt)
            raise
        _close(ledger, attempt_id, attempt)
        return attempt

    return charged


def _write_review_file(
    out_dir: Path, spec_id: str, *, task_id: int, range_start: str, head: str, reviews
) -> Path:
    directory = out_dir / spec_id / "commit-reviews"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{head}.json"
    payload = {
        "task_id": task_id,
        "range_start": range_start,
        "head": head,
        "reviews": [review.as_dict() for review in reviews],
    }
    path.write_text(json.dumps(payload, indent=2))
    return path


def run_commit_review(
    task_id: int,
    *,
    repo: Path,
    ledger: Ledger,
    out_dir: Path,
    mirror_path: Path,
    gh: package_phase.GhRunner,
) -> int:
    """Everything `saffron review` does: decline before any cell, or read
    the task's own review commits with the end review's two lenses.

    A decline prints `review:` and its reason, then returns 2. Any other
    raise reading the task, the range, the export or the spec is left to
    the caller, which exits 2. The task's state never moves."""
    url = package_phase.real_remote(repo)
    try:
        row = _task_and_run(ledger, task_id, repo, url)
        _pr_state(gh, row["pr_url"])

        mirror = git_mirror.ensure_mirror(repo, mirror_path)
        head = _fetch_head(mirror, url, row["branch"])
        range_start = _range_start(mirror, row["pushed_sha"], head)

        exported = git_mirror.export_saffron_dir(
            mirror, row["base_sha"], out_dir / "review" / str(task_id) / "gates"
        )
        policy, _policy_sha = load_policy(exported)
        spec = _spec_for_task(
            ledger, task_id, exported, row["spec_id"], row["spec_sha"]
        )

        _token()
    except _Declined as declined:
        print(f"review: {declined.reason}")
        return 2

    claude_md = git_mirror.file_at(mirror, row["base_sha"], "CLAUDE.md")
    context_md = (_SAFFRON_ROOT / "CONTEXT.md").read_text()

    framed = spec.model_copy(
        update={"body": _framed_body(spec.body, range_start, head)}
    )

    fields = end_review.LayerFields(
        spec_id=row["spec_id"],
        branch=row["branch"],
        pr_url=row["pr_url"],
        base=range_start,
        head=head,
        known=end_review._known_block(ledger.findings(task_id)),
        diff_base=range_start,
    )

    agent = stop_on_rejected(
        _charging(
            partial(
                implement.run_agent,
                timeout_s=TURN_TIMEOUT_S,
                spec_id=f"commit-review-{task_id}",
            ),
            ledger=ledger,
            task_id=task_id,
        )
    )
    open_cell = partial(
        end_review.layer_cell,
        repo=repo,
        mirror=mirror,
        gates_dir=exported,
        thread_env=policy.thread_env,
    )

    reviews = end_review._review_one_layer(
        ledger,
        str(task_id),
        {framed.id: framed},
        mirror=mirror,
        open_cell=open_cell,
        context_md=context_md,
        claude_md=claude_md,
        prompts_dir=context.PROMPTS_DIR,
        max_turns=end_review.LENS_MAX_TURNS,
        budget_usd=end_review.LENS_BUDGET_USD,
        agent=agent,
        emit=lambda event: print(describe(event)),
        resolve=lambda _ledger, _task_key: fields,
    )
    path = _write_review_file(
        out_dir,
        row["spec_id"],
        task_id=task_id,
        range_start=range_start,
        head=head,
        reviews=reviews,
    )

    blockers = 0
    errored = False
    for review in reviews:
        for finding in review.findings:
            if finding.severity == "blocker":
                blockers += 1
            print(
                f"review: {finding.severity} ({review.lens}) "
                f"{finding.file}:{finding.line}: {finding.claim}"
            )
        if review.error is not None:
            errored = True

    print(f"review: {head[:12]} vs {range_start[:12]}, {blockers} blocker(s)")
    print(f"review: {path}")

    if blockers:
        return 1
    if errored:
        return 2
    return 0
