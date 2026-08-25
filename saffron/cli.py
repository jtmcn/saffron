"""`saffron` — batch, run, queue, ratify, gc. v0 implements `replay`."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

from saffron.cell.session import CellSpec, run_one_cell
from saffron.intake import Spec, load_spec
from saffron.ledger import Ledger
from saffron.phases import package as package_phase
from saffron.replay import replay
from saffron.repos import image as repo_image
from saffron.repos import mirror as git_mirror

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

    args = parser.parse_args(argv)
    out_dir_arg = getattr(args, "out", None)
    out_dir = out_dir_arg or (args.home / "batches" / "v0")
    ledger = Ledger(args.home / "ledger.db")
    try:
        if args.command == "cell":
            return _run_cell(args, ledger, out_dir)

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


def _run_cell(args: argparse.Namespace, ledger: Ledger, out_dir: Path) -> int:
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


if __name__ == "__main__":
    raise SystemExit(main())
