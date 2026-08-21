"""`saffron` — batch, run, queue, ratify, gc. v0 implements `replay`."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
from pathlib import Path

from saffron.cell.runtime import CellRuntimeError
from saffron.cell.session import CellSessionError, CellSpec, run_one_cell
from saffron.intake import SpecError, load_spec
from saffron.ledger import Ledger
from saffron.replay import replay
from saffron.repos import mirror as git_mirror
from saffron.repos.mirror import GitError
from saffron.repos.policy import PolicyError

DEFAULT_HOME = Path.home() / ".saffron"

# The exit code is the only thing a script reads: 0 the task is reviewable,
# 2 the infrastructure failed, 1 the task did not make it (§3.3). The map covers
# states; a driver or runtime crash is the same class of failure and takes 2 by
# the handler in `main`, or an abort would read as an ordinary task outcome.
# Everything the setup path raises before a cell exists — an unreadable spec or
# policy, a mirror that will not clone, a repo with no HEAD — is that same
# infrastructure failure, and is caught there too rather than reaching the
# operator as a traceback.
CELL_EXIT = {"READY_FOR_REVIEW": 0, "PREFLIGHT_FAILED": 2, "GATE_ERROR": 2}


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
    cell_parser.add_argument("--budget", type=float, default=12.0)
    cell_parser.add_argument("--max-attempts", type=int, default=4)

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
    except (
        CellSessionError,
        CellRuntimeError,
        PolicyError,
        SpecError,
        GitError,
        subprocess.CalledProcessError,
    ) as broke:
        print(f"saffron: {broke}")
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


def _run_cell(args: argparse.Namespace, ledger: Ledger, out_dir: Path) -> int:
    repo = args.repo.resolve()
    spec, spec_sha = load_spec(args.spec)

    digest = hashlib.sha256(str(repo).encode()).hexdigest()[:12]
    mirror = git_mirror.ensure_mirror(
        repo, args.home / "mirrors" / f"{repo.name}-{digest}.git"
    )
    base_sha = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    cell_spec = CellSpec(
        spec_id=spec.id,
        spec_sha=spec_sha,
        branch=f"saffron/{spec.id}",
        base_sha=base_sha,
        touches=spec.touches,
        spec_type=spec.type,
        body=spec.body,
        forbidden=spec.forbidden,
        budget_usd=args.budget,
        max_attempts=args.max_attempts,
    )
    state = run_one_cell(
        cell_spec, repo=repo, mirror=mirror, ledger=ledger, out_dir=out_dir
    )
    print(f"{spec.id:<10} {state}")
    return CELL_EXIT.get(state, 1)


if __name__ == "__main__":
    raise SystemExit(main())
