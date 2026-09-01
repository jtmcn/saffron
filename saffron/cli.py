"""`saffron` — batch, run, queue, ratify, gc. v0 implements `replay`."""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

from saffron.cell.session import CellSpec, run_one_cell
from saffron.intake import Spec, load_spec
from saffron.ledger import Ledger
from saffron.phases import package as package_phase
from saffron.reconcile import ReconcileResult, reconcile
from saffron.replay import replay
from saffron.repos import image as repo_image
from saffron.repos import mirror as git_mirror
from saffron.repos.policy import PolicyError, load_policy
from saffron.scheduler import (
    Candidate,
    GhRunner,
    Refusal,
    build_queue,
    protected_touch_refusal,
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


def _protected_paths(exported: Path) -> list[str]:
    """`policy.protected` at an already-exported `.saffron` root — best
    effort, the same shape `scheduler._open_prs` is best-effort for the same
    reason (`SA-0016`): a `policy.yaml` that does not parse is a broken repo,
    and diagnosing a broken repo is preflight's job (inside the cell this
    refusal exists to let a task skip), not this cheap early read's. A repo
    this cannot answer for reaches exactly as far as it did before `SA-0023`.
    """
    try:
        policy, _policy_sha = load_policy(exported)
    except PolicyError:
        return []
    return policy.protected


def _protected_paths_at(mirror: Path, base_sha: str, scratch: Path) -> list[str]:
    """`_protected_paths`, but for a caller (`_run_cell`) that has not
    exported `.saffron` yet. A `base_sha` this repo has not onboarded — no
    `.saffron` at all — is the same best-effort case: `session.py`'s own
    `export_saffron_dir` call, deeper in preflight, is still there to say so
    properly once a cell actually starts."""
    try:
        exported = git_mirror.export_saffron_dir(mirror, base_sha, scratch)
    except git_mirror.GitError:
        return []
    return _protected_paths(exported)


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

    # Read before an image is built or a container is started, from `base_sha`
    # — never `repo`, the working copy (item 13, item 15 are both that
    # mistake) — so a spec whose own `touches` collide with `policy.yaml`'s
    # `protected` list is refused for the price of a `git archive`, not a
    # cell, a turn and $0.82 (`SA-0021`, measured, docs/BACKLOG.md item 28).
    # No task row exists yet, so nothing is left in an in-flight state.
    with tempfile.TemporaryDirectory() as scratch:
        protected = _protected_paths_at(mirror, base_sha, Path(scratch) / "at-base")
    collision = protected_touch_refusal(spec.touches, protected)
    if collision is not None:
        print(f"{spec.id:<10} refused  {collision}")
        return 1

    # Printed, not merely applied: three ceilings govern a run and only one of
    # them appears in the exit. SA-0005 was stopped by the turn ceiling with
    # more than half its budget left, and nothing on the way in had said what
    # any of the three were.
    ceilings, in_force = _ceilings(args, spec)
    print(f"ceilings: {in_force}")

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
        # Deliberately unset, and the only thing that keeps stacking off:
        # `spec.depends_on` is not consulted on this path. `SA-0025` resolves
        # a real parent here.
        stacked_on=None,
        **ceilings,
    )
    outcome = run_one_cell(
        cell_spec, repo=repo, mirror=mirror, ledger=ledger, out_dir=out_dir
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
            protected=_protected_paths(exported),
            gh=_guarded_gh(gh_failures),
        )

    _print_reconcile_summary(reconciled)
    _print_queue(candidates, refusals, repo_slug, exported, gh_failures)
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


def _print_queue(
    candidates: list[Candidate],
    refusals: list[Refusal],
    repo_slug: str | None,
    root: Path,
    gh_failures: list[str],
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
        print(f"  {refusal.path.relative_to(root)}: {refusal.reason}")
    if repo_slug is None:
        _print_skipped("no GitHub slug could be read from the remote")
    elif gh_failures:
        _print_skipped(f"gh could not be run ({gh_failures[0]})")


def _print_skipped(because: str) -> None:
    print(
        f"note: {because} — the open-pull-request and touches-overlap "
        "refusals did not run, so the refusal list above is incomplete"
    )


if __name__ == "__main__":
    raise SystemExit(main())
