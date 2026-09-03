"""`saffron` — batch, run, queue, ratify, gc. v0 implements `replay`."""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import tempfile
import time
from collections.abc import Callable, Sequence
from pathlib import Path

from saffron.cell.session import _SHA as _RESOLVED_SHA
from saffron.cell.session import CellSpec, run_one_cell
from saffron.events import Event, EventLog, Preflight, describe
from saffron.intake import Spec, load_spec
from saffron.ledger import Ledger
from saffron.phases import package as package_phase
from saffron.reconcile import ReconcileResult, reconcile
from saffron.replay import replay
from saffron.repos import image as repo_image
from saffron.repos import mirror as git_mirror
from saffron.repos.policy import PolicyError, load_policy
from saffron.scheduler import (
    DEPENDENCY_WAITING_STATES,
    Candidate,
    GhRunner,
    Refusal,
    build_queue,
    protected_touch_refusal,
    retirement_refusal,
    run_gh,
)

DEFAULT_HOME = Path.home() / ".saffron"

# The exit code is the only thing a script reads: 0 the task is reviewable,
# 2 the infrastructure failed, 1 the task did not make it (§3.3). The map covers
# states; a driver or runtime crash is the same class of failure and takes 2 by
# the handler in `main`, or an abort would read as an ordinary task outcome.
# Everything the setup path raises before a cell exists — an unreadable spec or
# policy, a mirror that will not clone, a repo with no HEAD — is that same
# infrastructure failure, and is caught there too rather than reaching the
# operator as a traceback.
CELL_EXIT = {
    "READY_FOR_REVIEW": 0,
    # Already the default for an unnamed state; named because PACKAGE returns it
    # and it is the task's failure, not the operator's.
    "MERGE_FAILED": 1,
    # Also already the default, and named for the opposite reason: a proposal
    # is a task that stopped on purpose with something for the operator to
    # ratify, not one that failed. It takes 1 because there is no reviewable
    # diff, and saying so here keeps that a decision rather than a fallthrough.
    "SCOPE_REVIEW": 1,
    "PREFLIGHT_FAILED": 2,
    "GATE_ERROR": 2,
    # Neither the task's failure nor the operator's: retry after the window.
    "RATE_LIMITED": 2,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="saffron")
    parser.add_argument(
        "--home",
        type=Path,
        default=DEFAULT_HOME,
        help="ledger, mirrors and batch tree (default: ~/.saffron)",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    replay_parser = subcommands.add_parser(
        "replay", help="replay an already-merged pull request, agent-free"
    )
    replay_parser.add_argument("repo", type=Path)
    replay_parser.add_argument("pr", type=int)
    replay_parser.add_argument("--spec", type=Path, default=None)
    replay_parser.add_argument("--out", type=Path, default=None)
    replay_parser.add_argument("--timeout", type=float, default=900)

    cell_parser = subcommands.add_parser(
        "cell", help="run one spec in one cell, attended (v0.5)"
    )
    cell_parser.add_argument("spec", type=Path)
    cell_parser.add_argument("--repo", type=Path, default=Path.cwd())
    # `None`, not a number: an argparse default makes "not given" and "given
    # the default" the same value, which is how the spec's own ceilings came to
    # be parsed, validated and then discarded below.
    cell_parser.add_argument("--budget", type=float, default=None)
    cell_parser.add_argument("--max-attempts", type=int, default=None)
    cell_parser.add_argument("--max-turns", type=int, default=None)

    queue_parser = subcommands.add_parser(
        "queue", help="show what a batch would run tonight, agent-free"
    )
    queue_parser.add_argument("--repo", type=Path, default=Path.cwd())

    reconcile_parser = subcommands.add_parser(
        "reconcile",
        help="ask GitHub what happened to this repo's open pull requests",
    )
    reconcile_parser.add_argument("--repo", type=Path, default=Path.cwd())

    args = parser.parse_args(argv)
    out_dir_arg = getattr(args, "out", None)
    out_dir = out_dir_arg or (args.home / "batches" / "v0")
    ledger = Ledger(args.home / "ledger.db")
    try:
        if args.command == "cell":
            return _run_cell(args, ledger, out_dir)

        if args.command == "queue":
            return _queue(args, ledger)

        if args.command == "reconcile":
            return _reconcile(args, ledger)

        line = replay(
            args.repo,
            args.pr,
            ledger=ledger,
            out_dir=out_dir,
            mirrors_dir=args.home / "mirrors",
            spec_path=args.spec,
            timeout_s=args.timeout,
        )
    except Exception as broke:
        # Every one of them, not a named few: an OSError, a sqlite3.Error or a
        # pydantic failure from an SDK shape change is as much an infrastructure
        # abort as a CellRuntimeError, and exiting 1 with a traceback says "the
        # task did not make it" about a task that never got to run. The
        # exception path in `run_one_cell` has already closed the run ABORTED.
        print(f"saffron: {type(broke).__name__}: {broke}")
        return 2
    finally:
        ledger.close()

    print(
        f"{line.repo:<14} {line.spec_id:<10} {line.state:<18} "
        f"+{line.added}/−{line.removed}  {line.note}"
    )
    print(f"→ {out_dir / line.spec_id / 'pr_body.md'}")
    print(f"→ {out_dir / 'index.html'}")
    return 0


def _ceilings(args: argparse.Namespace, spec: Spec) -> tuple[dict, str]:
    """What bounds this run, and where each bound came from.

    The flag wins when it is given; the spec governs otherwise. Both are real
    inputs — the flag is how an operator overrides a spec they are re-running,
    and the spec is how the author states what the task should cost.
    """
    declared = {
        "budget_usd": spec.budget_usd,
        "max_attempts": spec.max_attempts,
        "max_turns": spec.max_turns,
    }
    given = {
        "budget_usd": args.budget,
        "max_attempts": args.max_attempts,
        "max_turns": args.max_turns,
    }
    chosen = {
        name: given[name] if given[name] is not None else declared[name]
        for name in declared
    }

    def _source(name: str) -> str:
        # Three labels, not two. Calling a model default "(spec)" sends the
        # operator to grep a spec file for a line that is not in it — the same
        # not-given-is-given-the-default conflation this function exists to
        # end, moved from argparse to pydantic.
        if given[name] is not None:
            return "flag"
        return "spec" if name in spec.model_fields_set else "default"

    line = ", ".join(f"{name}={chosen[name]} ({_source(name)})" for name in declared)
    return chosen, line


def _protected_paths(exported: Path, unread: list[str] | None = None) -> list[str]:
    """`policy.protected` at an already-exported `.saffron` root.

    Best effort about the *value* — a `policy.yaml` that does not parse is a
    broken repo, and diagnosing one is preflight's job, not this cheap early
    read's — but never silent about the *absence*. `_open_prs` is the
    precedent for the shape and `_guarded_gh` is the precedent for this half:
    a scan whose refusals never ran must not print what a scan that ran them
    and found nothing prints (§5.4). The reason is appended to `unread` when
    the caller passes a list to collect it.
    """
    if not (exported / ".saffron" / "policy.yaml").is_file():
        # A repo that declares no policy declares no protected paths, which is
        # the ordinary case for every repo not yet onboarded (§5.6). Absent is
        # a different fact from unreadable and must not print a note.
        return []
    try:
        policy, _policy_sha = load_policy(exported)
    except PolicyError as broke:
        if unread is not None:
            unread.append(str(broke))
        return []
    return policy.protected


def _protected_paths_at(
    mirror: Path, base_sha: str, scratch: Path, unread: list[str] | None = None
) -> list[str]:
    """`_protected_paths`, but for a caller (`_run_cell`) that has not
    exported `.saffron` yet. A `base_sha` this repo has not onboarded — no
    `.saffron` at all — is the same best-effort case: `session.py`'s own
    `export_saffron_dir` call, deeper in preflight, is still there to say so
    properly once a cell actually starts.

    Nothing is collected in this handler, and that is the point: `git archive`
    fails on an unmatched pathspec, so every repo without a `.saffron` at
    `base_sha` reaches it. Reporting that as an unreadable policy is the
    absence-as-unreadability defect `_protected_paths` exists to avoid, one
    function up. A genuinely broken mirror is not lost with it: `session.py`
    calls `export_saffron_dir` unguarded during preflight, *before* the image
    build and before any container exists, so it raises to `main`'s handler
    and exits `2` having spent nothing. (A missing `git` binary raises
    `OSError`, not `GitError`, and never reached this handler at all.)"""
    try:
        exported = git_mirror.export_saffron_dir(mirror, base_sha, scratch)
    except git_mirror.GitError:
        return []
    return _protected_paths(exported, unread)


def _retirement_markers_at(mirror: Path, base_sha: str) -> list[tuple[str, str]]:
    """`git_mirror.retirement_markers`, best-effort the same way
    `_protected_paths_at` is: a mirror this cheap pre-cell read cannot
    actually grep (no such tree, no such mirror) answers `[]` rather than
    aborting a run this check exists to save money on, not gate."""
    try:
        return git_mirror.retirement_markers(mirror, base_sha)
    except git_mirror.GitError:
        return []


def _resolve_stacked_on(
    ledger: Ledger,
    repo_id: int | None,
    depends_on: list[str],
    *,
    mirror: Path,
    url: str,
    spec_id: str,
    emit: Callable[[Event], None] = lambda event: print(describe(event)),
) -> tuple[str | None, str | None]:
    """The tree sha `CellSpec.stacked_on` should carry and the branch name
    `package()`'s stacking parameter should carry, or `(None, None)`
    together for an ordinary unstacked cell — never one without the other,
    since a worktree stacked on a sha whose pull request targets `main` is
    exactly the defect this spec exists to close (`SA-0026`).

    Only `depends_on[0]` is ever consulted — K=1. A spec naming a second,
    unmerged parent does not stack on it too: nothing here orders one
    batch's tasks against each other yet, so a grandchild (or a second
    unmerged parent) is out of reach by design, not by oversight.

    Among that one parent's task rows in this repo, across every `spec_sha`
    it has ever carried (`Ledger.tasks_by_spec_id` — this attended path never
    reads the parent's spec file, so it has no current sha to filter on, the
    same reach `scheduler.build_queue`'s `merged_anywhere` already takes),
    the newest row in a `scheduler.DEPENDENCY_WAITING_STATES` state is "the
    parent's task": the same waiting-outranks-dead precedence
    `scheduler._dependency_refusal` gives it. Not the *same* row, though —
    that function reads only the parent's current `spec_sha`, and a parent
    whose spec text moved after its pull request opened has a waiting row
    here and none there. The branch is real either way; it is the gate, not
    this resolver, that decides whether the dependent runs at all.
    A parent merged, retired, dead, unrun, or never in the
    ledger at all has no such row, and this function does not distinguish
    why — every one of those needs no stacking (its work, if any, is already
    on the default branch) or was never a candidate the gate should have
    admitted, which is not this attended path's check to make.

    **The ledger supplies the branch; the branch supplies the sha.** A row's
    `pushed_sha` is written once, by PACKAGE, and every review fix an operator
    commits by hand moves the branch past it — so the recorded sha is a tree
    the parent's pull request may no longer show. Worse, nothing puts that
    commit where the cell can read it: `ensure_mirror` fetches `+refs/*:refs/*`
    from the operator's *local checkout* with `--prune`, so a parent branch the
    operator does not happen to have locally is deleted from the mirror, and
    the cell's own seed (`worktree.py`) fetches the mirror's default refspec.
    Fetching the branch here fixes both — it is `fetch_default_branch`'s own
    argument (`package.py`), one branch over.

    `ParentGone` is an unstacked cell, not a failure: a parent branch that is
    deleted has either merged, in which case its work is on the default branch
    already, or been abandoned, in which case cutting from the default branch
    is the safe answer. Neither is worth killing an attended run over.

    A `pushed_sha` that is absent, empty, or not a resolved sha still yields
    `(None, None)` rather than reaching `CellSpec`: `__post_init__`
    (`SA-0022`) raises `ValueError` on anything else, and an operator's
    `saffron cell` must not die on a row this attended path cannot fully
    trust. A row with no `branch` recorded is treated the same way, since
    the two values this returns travel together.
    """
    if repo_id is None or not depends_on:
        return None, None
    parent_id = depends_on[0]
    rows = ledger.tasks_by_spec_id(repo_id, parent_id)
    waiting = [row for row in rows if row["state"] in DEPENDENCY_WAITING_STATES]
    if not waiting:
        return None, None
    newest = waiting[-1]
    branch = newest["branch"]
    # Refused here rather than left to the fetch: a row that evidences no push
    # has no branch worth fetching, and "branch None is gone" would send an
    # operator to look for a deleted ref instead of at the row.
    if not branch or not _RESOLVED_SHA.fullmatch(newest["pushed_sha"] or ""):
        emit(
            Preflight(
                timestamp=time.time(),
                spec_id=spec_id,
                step="unstacked",
                detail=f"{parent_id}'s newest waiting task records no pushed branch",
            )
        )
        return None, None
    try:
        head = package_phase.fetch_parent_branch(mirror, url, branch)
    except package_phase.ParentGone as gone:
        emit(
            Preflight(
                timestamp=time.time(),
                spec_id=spec_id,
                step="unstacked",
                detail=str(gone),
            )
        )
        return None, None
    if not _RESOLVED_SHA.fullmatch(head):
        return None, None
    return head, branch


def _run_cell(args: argparse.Namespace, ledger: Ledger, out_dir: Path) -> int:
    # Checked before the image build, not at the cell door: `session` forwards
    # this only if it is set, so a missing one reached the agent as "Not logged
    # in" after a full preflight had already been paid for.
    if not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "").strip():
        raise RuntimeError(
            "CLAUDE_CODE_OAUTH_TOKEN is unset; the agent cannot authenticate "
            "(`claude setup-token`)"
        )

    repo = args.repo.resolve()
    spec, spec_sha = load_spec(args.spec)

    digest = hashlib.sha256(str(repo).encode()).hexdigest()[:12]
    mirror = git_mirror.ensure_mirror(
        repo, args.home / "mirrors" / f"{repo.name}-{digest}.git"
    )
    url = package_phase.real_remote(repo)
    # Read for its refusal, not its value: `package` needs the slug and only
    # reaches it after the budget is spent, so a non-GitHub origin fails here
    # for the same reason an unreachable one does (§5.1).
    package_phase.github_slug(url)
    # The remote's default-branch head, not the invoking checkout's: a task's
    # base must not depend on where the operator was standing (§5.7).
    _, base_sha = package_phase.fetch_default_branch(mirror, url)
    # The same string `resolve_repo_id`'s own callers already have in hand —
    # this repo's own ledger holds the SSH form (`git@github.com:...`), not
    # the https one, so whatever `real_remote` returned above is the form to
    # read it back with. `None` for a repo the ledger has never seen, which
    # `_resolve_stacked_on` treats as nothing to stack on.
    repo_id = ledger.resolve_repo_id(url)

    # Read before an image is built or a container is started, from `base_sha`
    # — never `repo`, the working copy (item 13, item 15 are both that
    # mistake) — so a spec whose own `touches` collide with `policy.yaml`'s
    # `protected` list is refused for the price of a `git archive`, not a
    # cell, a turn and $0.82 (`SA-0021`, measured, docs/BACKLOG.md item 28).
    # No task row exists yet, so nothing is left in an in-flight state.
    policy_unread: list[str] = []
    with tempfile.TemporaryDirectory() as scratch:
        protected = _protected_paths_at(
            mirror, base_sha, Path(scratch) / "at-base", policy_unread
        )
    if policy_unread:
        # This is the path that spends: an image build and a preflight suite
        # follow. A check that did not run must say so before the money, which
        # is the whole argument for running it here at all.
        _print_skipped(
            "policy.yaml at this base_sha could not be read",
            "this spec was not checked against the protected list",
        )
    collision = protected_touch_refusal(spec.touches, protected, spec.forbidden)
    if collision is not None:
        print(f"{spec.id:<10} refused  {collision}")
        return 1

    # Same cheap-before-a-cell shape, one check later: a `saffron:retired-by`
    # marker this spec's own `touches` cannot reach (`SA-0027`, docs/BACKLOG.md
    # item 35) is a `git grep` against the mirror, not a plan checkpoint an
    # agent has to talk its way out of.
    markers = _retirement_markers_at(mirror, base_sha)
    retirement = retirement_refusal(spec, markers)
    if retirement is not None:
        print(f"{spec.id:<10} refused  {retirement}")
        return 1

    # Printed, not merely applied: three ceilings govern a run and only one of
    # them appears in the exit. SA-0005 was stopped by the turn ceiling with
    # more than half its budget left, and nothing on the way in had said what
    # any of the three were.
    ceilings, in_force = _ceilings(args, spec)
    print(f"ceilings: {in_force}")

    # Built once, here, and handed to every phase this command drives —
    # `_resolve_stacked_on` below, `run_one_cell`, and `package()` — so a
    # task's PACKAGE events land in the same `events.jsonl` as everything
    # before them. `run_one_cell`'s own default (session.py's
    # `_default_emit`) is this same shape; duplicated rather than imported,
    # the way `_when` is duplicated across modules instead of reaching into a
    # forbidden one.
    task_dir = out_dir / spec.id
    event_log = EventLog(task_dir)

    def emit(event: Event) -> None:
        line = describe(event)
        if line:
            print(line)
        event_log.append(event)

    # Resolved from `depends_on[0]`'s newest waiting task, or `(None, None)`
    # together for an ordinary unstacked cell (`_resolve_stacked_on`,
    # `SA-0026`) — the one place a `CellSpec` is built, so this is the only
    # place either has to be read.
    stacked_on, target_branch = _resolve_stacked_on(
        ledger,
        repo_id,
        spec.depends_on,
        mirror=mirror,
        url=url,
        spec_id=spec.id,
        emit=emit,
    )
    # Printed for the same reason the ceilings are: which tree a run was cut
    # from is not recoverable from the exit code, and a stacked run that
    # surprises an operator is one they cannot diagnose.
    if stacked_on is not None:
        print(f"stacked on {target_branch} @ {stacked_on[:12]}")

    cell_spec = CellSpec(
        spec_id=spec.id,
        spec_sha=spec_sha,
        branch=f"saffron/{spec.id}",
        base_sha=base_sha,
        touches=spec.touches,
        spec_type=spec.type,
        body=spec.body,
        forbidden=spec.forbidden,
        acceptance=spec.acceptance,
        risk=spec.risk,
        stacked_on=stacked_on,
        **ceilings,
    )
    outcome = run_one_cell(
        cell_spec, repo=repo, mirror=mirror, ledger=ledger, out_dir=out_dir, emit=emit
    )
    if outcome.state == "READY_FOR_REVIEW":
        result = package_phase.package(
            outcome,
            spec=spec,
            repo=repo,
            mirror=mirror,
            # Derived, not rebuilt: preflight already built this tag.
            image=repo_image.cell_tag(repo),
            ledger=ledger,
            out_dir=out_dir,
            token=os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"),
            # `None` unless `stacked_on` is too: a stacked worktree must not
            # reach a pull request that is not.
            parent_branch=target_branch,
            emit=emit,
        )
        print(f"{spec.id:<10} {result.state}  {result.pr_url or result.note}")
        return CELL_EXIT.get(result.state, 1)

    print(f"{spec.id:<10} {outcome.state}")
    return CELL_EXIT.get(outcome.state, 1)


def _queue(args: argparse.Namespace, ledger: Ledger) -> int:
    """`saffron queue --repo .` — the scan a batch would run tonight.

    No longer writes nothing: `reconcile`'s pull-request half runs first, so
    the scan filters on current state. Still no cell, and never `ORPHANED` —
    this is not a batch scan; an operator can run it at will, mid-phase
    included. `resolve_repo_id`, never `upsert_repo`: an unseen repo gets
    `None`, which both `build_queue` and `reconcile` treat as nothing to do.
    """
    repo = args.repo.resolve()

    digest = hashlib.sha256(str(repo).encode()).hexdigest()[:12]
    mirror = git_mirror.ensure_mirror(
        repo, args.home / "mirrors" / f"{repo.name}-{digest}.git"
    )
    url = package_phase.real_remote(repo)
    _, base_sha = package_phase.fetch_default_branch(mirror, url)

    repo_id = ledger.resolve_repo_id(url)

    gh_failures: list[str] = []
    policy_unread: list[str] = []
    reconciled = ReconcileResult()
    if repo_id is not None:
        reconciled = reconcile(ledger, repo_id, gh=_guarded_gh(gh_failures))

    # Unlike `_run_cell`, a slug that cannot be read is not this command's
    # failure — it just means two of `build_queue`'s refusals cannot run, and
    # the printed output below says so on its own line rather than letting an
    # empty refusal list stand in for "these were never checked."
    try:
        repo_slug = package_phase.github_slug(url)
    except package_phase.PackageError:
        repo_slug = None

    with tempfile.TemporaryDirectory() as scratch:
        exported = git_mirror.export_saffron_dir(
            mirror, base_sha, Path(scratch) / "at-base"
        )
        candidates, refusals = build_queue(
            exported / ".saffron" / "specs",
            repo_id,
            ledger,
            # The slug is what makes the open-pull-request and touches-overlap
            # refusals run at all; the runner only decides how a `gh` that
            # cannot start is reported.
            repo_slug=repo_slug,
            # `policy.yaml` sits right beside `specs/` in the same export —
            # no second export, and never the working copy (`SA-0023`).
            protected=_protected_paths(exported, policy_unread),
            # Read from the mirror directly, not the export: a marker is a
            # comment anywhere in the tree, not something `.saffron/`'s own
            # archive carries (`SA-0027`).
            markers=_retirement_markers_at(mirror, base_sha),
            gh=_guarded_gh(gh_failures),
        )

    _print_reconcile_summary(reconciled)
    _print_queue(candidates, refusals, repo_slug, exported, gh_failures, policy_unread)
    return 0


def _reconcile(args: argparse.Namespace, ledger: Ledger) -> int:
    """`saffron reconcile --repo .` — ask GitHub what happened to every open
    pull request this repo's ledger is waiting on, and write what it says.
    Never `ORPHANED`, for the same reason `queue` never asserts it."""
    repo = args.repo.resolve()
    url = package_phase.real_remote(repo)
    repo_id = ledger.resolve_repo_id(url)
    if repo_id is None:
        print("reconcile: no ledger history for this repo")
        return 0

    gh_failures: list[str] = []
    result = reconcile(ledger, repo_id, gh=_guarded_gh(gh_failures))
    _print_reconcile_summary(result)
    if gh_failures:
        print(f"reconcile: gh could not be run ({gh_failures[0]})")
    return 0


def _guarded_gh(failures: list[str]) -> GhRunner:
    """`run_gh`, but a `gh` that cannot start is recorded instead of raised.

    A preview must not exit `2` on a machine with no `gh` (`package.py` guards
    the same case), and a scan whose GitHub refusals never ran must not print
    the same thing as one that ran them and found nothing (§5.4).
    """

    def gh(argv: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            return run_gh(argv)
        except OSError as exc:
            failures.append(str(exc))
            return subprocess.CompletedProcess(argv, 127, "", str(exc))

    return gh


def _print_reconcile_summary(result: ReconcileResult) -> None:
    """What `reconcile` changed, by task id."""
    buckets = (
        ("MERGED", result.merged),
        ("REJECTED", result.rejected),
        ("CHANGES_REQUESTED", result.changes_requested),
    )
    for label, ids in buckets:
        for task_id in ids:
            print(f"reconcile: task {task_id} → {label}")
    for task_id in result.unasked:
        print(f"reconcile: task {task_id} could not be asked about")
    # Silence read identically to "there was nothing to ask about". A run
    # that asked and found every answer unchanged now says which it was.
    if not any(
        (
            result.merged,
            result.rejected,
            result.changes_requested,
            result.orphaned,
            result.unasked,
        )
    ):
        print("reconcile: nothing moved")


_GH_REFUSALS_SKIPPED = (
    "the open-pull-request and touches-overlap refusals did not run, so the "
    "refusal list above is incomplete"
)


def _print_queue(
    candidates: list[Candidate],
    refusals: list[Refusal],
    repo_slug: str | None,
    root: Path,
    gh_failures: list[str],
    policy_unread: Sequence[str] = (),
) -> None:
    # Paths are printed relative to the export root because the export is a
    # temporary directory already deleted by the time this runs — an absolute
    # one names a file the operator cannot open, and a refusal that failed to
    # parse has no spec id to fall back on.
    print(f"queue: {len(candidates)} candidate(s)")
    for candidate in candidates:
        print(
            f"  {candidate.spec.id:<10} priority={candidate.spec.priority}  "
            f"{candidate.path.relative_to(root)}"
        )
    print(f"refusals: {len(refusals)}")
    for refusal in refusals:
        # A dangling `saffron:retired-by` marker (`SA-0027`) names a
        # repo-relative path from the mirror, never exported under `root` at
        # all — `relative_to` raises on it, and the raw path is still a real
        # answer, not a fallback worth hiding.
        try:
            shown = refusal.path.relative_to(root)
        except ValueError:
            shown = refusal.path
        print(f"  {shown}: {refusal.reason}")
    if repo_slug is None:
        _print_skipped(
            "no GitHub slug could be read from the remote", _GH_REFUSALS_SKIPPED
        )
    elif gh_failures:
        _print_skipped(f"gh could not be run ({gh_failures[0]})", _GH_REFUSALS_SKIPPED)
    if policy_unread:
        # Not a refusal that found nothing: one that never ran. The same
        # distinction `_print_skipped` draws for a `gh` that could not start.
        # The reason is deliberately not interpolated: it carries the export's
        # own path, which is a temp directory already deleted by the time this
        # prints — the same reason every path above is relativised.
        _print_skipped(
            "policy.yaml at this base_sha could not be read",
            "no spec was checked against the protected list, so the refusal "
            "list above is incomplete",
        )


def _print_skipped(because: str, consequence: str) -> None:
    """One line saying a refusal never ran, and which one.

    The consequence is a required parameter rather than a constant in the
    string: a note that names the wrong refusals is the defect this whole gate
    exists to remove, one level up (§5.4), and a default would hand the next
    caller the `gh` clause without it having read one.
    """
    print(f"note: {because} — {consequence}")


if __name__ == "__main__":
    raise SystemExit(main())
