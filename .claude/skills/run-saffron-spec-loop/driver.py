#!/usr/bin/env python3
"""Drive Saffron's spec loop over every active spec, stacking the pull
requests instead of merging them.

The problem this exists to solve: `saffron queue` is computed against open
pull requests, and this workflow deliberately leaves them open. The moment
the first cell packages, gate 0 refuses every remaining spec whose `touches`
overlap that pull request's files — and nearly every spec in this repository
touches `docs/BACKLOG.md`. A loop that re-reads the queue each iteration
therefore stops after one spec and reports "nothing to do" with work left.

So the run order is snapshotted **once, before any pull request exists**, and
persisted. Everything after that reads the plan, never the queue.

Usage (from the repo root):

    uv run .claude/skills/run-saffron-spec-loop/driver.py plan
    uv run .claude/skills/run-saffron-spec-loop/driver.py next
    uv run .claude/skills/run-saffron-spec-loop/driver.py record SA-0028
    uv run .claude/skills/run-saffron-spec-loop/driver.py status
    uv run .claude/skills/run-saffron-spec-loop/driver.py stack [--execute]

The cell runs themselves are not this script's job: `saffron cell` needs
`CLAUDE_CODE_OAUTH_TOKEN` scoped to its own invocation and nothing else, so
the agent runs it directly (see SKILL.md) and calls `record` afterwards.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PLAN = REPO / ".saffron-loop" / "plan.json"


def _fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 2


# --------------------------------------------------------------- discovery


@dataclass
class Planned:
    spec_id: str
    path: str
    priority: int
    depends_on: list[str] = field(default_factory=list)
    state: str | None = None
    pr: int | None = None
    branch: str = ""


def _ledger_and_repo():
    """The ledger and this repo's id, resolved the way `cli._queue` does.

    `real_remote` supplies the origin string; the ledger holds the SSH form
    for this repository, so reading it back with anything else finds nothing.
    """
    from saffron.ledger import Ledger
    from saffron.phases import package as package_phase

    url = package_phase.real_remote(REPO)
    ledger = Ledger(Path.home() / ".saffron" / "ledger.db")
    return ledger, ledger.resolve_repo_id(url), url


def _scan():
    """`build_queue` against the specs on disk, with no open pull requests.

    On disk, not the mirror export `saffron queue` reads: a plan is made
    against the specs the operator is looking at. `gh` is stubbed to report
    no open pull requests, because the two refusals that need it are exactly
    the ones this workflow has to look past — a spec is not disqualified by
    a pull request this same batch is about to open.
    """
    from saffron.scheduler import build_queue

    def no_prs(argv):
        return subprocess.CompletedProcess(argv, 0, stdout="[]", stderr="")

    ledger, repo_id, _url = _ledger_and_repo()
    try:
        return build_queue(
            REPO / ".saffron" / "specs",
            repo_id,
            ledger,
            repo_slug="jtmcn/saffron",
            gh=no_prs,
        )
    finally:
        ledger.close()


def _order(candidates, refusals) -> list[Planned]:
    """Run order: parents before children, then priority, then file order.

    A spec refused *only* because its `depends_on` has not run is included —
    running the parent is what admits it, and that is the whole point of an
    ordered plan. Every other refusal stands.
    """
    from saffron.intake import load_spec

    planned = {
        c.spec.id: Planned(
            spec_id=c.spec.id,
            path=str(c.path.relative_to(REPO)) if c.path.is_absolute() else str(c.path),
            priority=c.spec.priority,
            depends_on=list(c.spec.depends_on),
            branch=f"saffron/{c.spec.id}",
        )
        for c in candidates
    }

    deferred = []
    for refusal in refusals:
        if "depends_on" not in refusal.reason:
            continue
        try:
            spec, _sha = load_spec(refusal.path)
        except Exception:
            continue
        deferred.append((spec, refusal.path))

    # Two passes: a grandchild's parent may itself be deferred.
    for _ in range(len(deferred) + 1):
        for spec, path in deferred:
            if spec.id in planned:
                continue
            if all(dep in planned for dep in spec.depends_on):
                planned[spec.id] = Planned(
                    spec_id=spec.id,
                    path=str(path.relative_to(REPO))
                    if path.is_absolute()
                    else str(path),
                    priority=spec.priority,
                    depends_on=list(spec.depends_on),
                    branch=f"saffron/{spec.id}",
                )

    ordered: list[Planned] = []
    remaining = dict(planned)
    while remaining:
        ready = [
            p
            for p in remaining.values()
            if all(d not in remaining for d in p.depends_on)
        ]
        if not ready:  # a cycle; emit the rest in a stable order rather than hang
            ready = sorted(remaining.values(), key=lambda p: p.spec_id)
        ready.sort(key=lambda p: (p.priority, p.spec_id))
        first = ready[0]
        ordered.append(first)
        del remaining[first.spec_id]
    return ordered


# ------------------------------------------------------------- plan file


def _load() -> list[Planned]:
    if not PLAN.is_file():
        raise SystemExit(
            _fail(f"no plan at {PLAN.relative_to(REPO)} — run `plan` first")
        )
    return [Planned(**row) for row in json.loads(PLAN.read_text())]


def _save(rows: list[Planned]) -> None:
    PLAN.parent.mkdir(parents=True, exist_ok=True)
    PLAN.write_text(json.dumps([r.__dict__ for r in rows], indent=2) + "\n")


# ------------------------------------------------------------- commands


def cmd_plan(args) -> int:
    if PLAN.is_file() and not args.force:
        return _fail(f"{PLAN.relative_to(REPO)} exists — pass --force to re-snapshot")
    candidates, refusals = _scan()
    ordered = _order(candidates, refusals)
    if not ordered:
        print("nothing to run: no candidate specs")
        return 1
    _save(ordered)

    print(f"plan: {len(ordered)} spec(s), bottom of the stack first\n")
    for i, p in enumerate(ordered, 1):
        dep = f"  depends_on={p.depends_on}" if p.depends_on else ""
        print(f"  {i}. {p.spec_id}  priority={p.priority}{dep}")
    held = [r for r in refusals if "depends_on" not in r.reason]
    if held:
        print(f"\nrefused, and not in the plan ({len(held)}):")
        for r in held:
            print(f"  {r.path.name}: {r.reason}")
    print(f"\nwritten to {PLAN.relative_to(REPO)}")
    _warn_siblings(ordered)
    return 0


def _warn_siblings(ordered: list[Planned]) -> None:
    """A stack of specs that do not depend on each other is a stack of
    siblings: Saffron cuts each branch from the default branch, so nothing
    chains them. `gh stack init`/`link` marks the upper ones "needs rebase",
    and `gh stack rebase --no-trunk` rewrites branches Saffron has already
    pushed. Say so now, not after the pull requests exist.
    """
    loose = [p for p in ordered[1:] if not p.depends_on]
    if not loose:
        return
    print(
        f"\nnote: {len(loose)} spec(s) declare no depends_on, so their branches "
        "will be siblings\n      cut from the default branch rather than a real "
        "chain. See SKILL.md, Gotchas."
    )


def cmd_next(_args) -> int:
    for p in _load():
        if p.state is None:
            print(p.spec_id)
            return 0
    print("done: every spec in the plan has been run", file=sys.stderr)
    return 1


def cmd_record(args) -> int:
    """Read the ledger for what the cell actually did. Reported states are
    not taken from the operator or the transcript — §4.3."""
    rows = _load()
    match = next((p for p in rows if p.spec_id == args.spec_id), None)
    if match is None:
        return _fail(f"{args.spec_id} is not in the plan")

    from saffron.intake import load_spec

    ledger, repo_id, _url = _ledger_and_repo()
    try:
        if repo_id is None:
            return _fail("this repo has no ledger row yet")
        _spec, spec_sha = load_spec(REPO / match.path)
        tasks = ledger.tasks_by_spec(repo_id).get((args.spec_id, spec_sha), [])
        if not tasks:
            return _fail(
                f"no task for {args.spec_id} at {spec_sha[:12]} — did the cell run?"
            )
        newest = tasks[-1]
        match.state = newest["state"]
        row = ledger._db.execute(
            "SELECT pr_url FROM tasks WHERE task_id = ?", (newest["task_id"],)
        ).fetchone()
        url = (row["pr_url"] if row else None) or ""
        match.pr = int(url.rstrip("/").rsplit("/", 1)[-1]) if "/pull/" in url else None
    finally:
        ledger.close()

    _save(rows)
    where = f"#{match.pr}" if match.pr else "(no PR)"
    print(f"{match.spec_id}  {match.state}  {where}")
    return 0 if match.state == "READY_FOR_REVIEW" else 1


def cmd_status(_args) -> int:
    rows = _load()
    width = max(len(p.spec_id) for p in rows)
    for p in rows:
        pr = f"#{p.pr}" if p.pr else ""
        print(f"  {p.spec_id:<{width}}  {p.state or 'pending':<18} {pr}")
    ready = [p for p in rows if p.state == "READY_FOR_REVIEW" and p.pr]
    print(f"\n{len(ready)}/{len(rows)} reviewable")
    return 0


def cmd_stack(args) -> int:
    rows = _load()
    ready = [p for p in rows if p.state == "READY_FOR_REVIEW" and p.pr]
    if len(ready) < 2:
        return _fail(
            f"a stack needs two or more reviewable pull requests; have {len(ready)}"
        )
    numbers = [str(p.pr) for p in ready]
    command = ["gh", "stack", "link", *numbers]

    print("stack, bottom to top:")
    for p in ready:
        print(f"  #{p.pr}  {p.spec_id}  ({p.branch})")
    print(f"\n  {' '.join(command)}")
    print(
        "\nnot passing --open: PACKAGE opens drafts on purpose (DESIGN.md §5.7),\n"
        "and ratifying one is `gh pr ready <n>` — the operator's call, not this\n"
        "script's."
    )
    if not args.execute:
        print("\n(dry run — pass --execute to run it)")
        return 0
    done = subprocess.run(command, cwd=REPO, text=True)
    return done.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("plan", help="snapshot the run order before any PR exists")
    p.add_argument("--force", action="store_true", help="overwrite an existing plan")
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("next", help="print the next spec id to run")
    p.set_defaults(func=cmd_next)

    p = sub.add_parser("record", help="read the ledger for what a cell did")
    p.add_argument("spec_id")
    p.set_defaults(func=cmd_record)

    p = sub.add_parser("status", help="show the plan and what has run")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("stack", help="link the reviewable PRs into a GitHub stack")
    p.add_argument("--execute", action="store_true", help="actually run gh stack link")
    p.set_defaults(func=cmd_stack)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
