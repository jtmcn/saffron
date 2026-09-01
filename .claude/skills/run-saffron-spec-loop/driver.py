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

if not (REPO / "DESIGN.md").is_file():  # the skill was moved; say so, do not guess
    raise SystemExit(
        f"error: {REPO} is not the Saffron repo root — this driver resolves it "
        "as parents[3] of its own path, so moving the skill directory breaks it"
    )


def _fail(message: str) -> int:
    """1, not 2: `saffron/cli.py` reserves 2 for infrastructure, and this is
    the operator holding it wrong."""
    print(f"error: {message}", file=sys.stderr)
    return 1


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


def _protected() -> list[str]:
    """`policy.yaml`'s repo-wide deny list, read from the checkout beside the
    specs this plans against.

    Gate 0 checks it first and cheapest, and `SA-0023` exists because the
    collision was otherwise found inside a cell — "after the cell, the turn
    and the money". A planner that launches cells is the last place to drop it.
    """
    from saffron.repos.policy import PolicyError, load_policy

    try:
        policy, _sha = load_policy(REPO)
    except PolicyError:
        return []
    return list(getattr(policy, "protected", []) or [])


def _scan(*, ignore_open_prs: bool):
    """`build_queue` against the specs on disk — not the mirror export
    `saffron queue` reads, because a plan is made against the specs the
    operator is looking at.

    `ignore_open_prs` is for a re-snapshot **mid-loop**, where this batch's
    own pull requests are open and are exactly what must be looked past. On a
    first snapshot the real `gh` runs: every open pull request is then someone
    else's, and a spec whose `touches` collide with one should still be
    refused.
    """
    from saffron.phases import package as package_phase
    from saffron.scheduler import build_queue, run_gh

    def no_prs(argv):
        return subprocess.CompletedProcess(argv, 0, stdout="[]", stderr="")

    ledger, repo_id, url = _ledger_and_repo()
    try:
        slug = package_phase.github_slug(url)
    except package_phase.PackageError:
        slug = None
    try:
        return build_queue(
            REPO / ".saffron" / "specs",
            repo_id,
            ledger,
            repo_slug=slug,
            protected=_protected(),
            gh=no_prs if ignore_open_prs else run_gh,
        )
    finally:
        ledger.close()


def _order(candidates, refusals) -> tuple[list[Planned], list[Path]]:
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
    unreadable = []
    for refusal in refusals:
        if "depends_on" not in refusal.reason:
            continue
        try:
            spec, _sha = load_spec(refusal.path)
        except Exception:
            # A parse failure can name `depends_on` too (a scalar where a list
            # belongs), and it is not a deferral. Do not let it vanish.
            unreadable.append(refusal)
            continue
        deferred.append((spec, refusal.path))

    # Enough passes for a chain: a grandchild's parent may itself be deferred.
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

    # Deferred and never admitted — a dead parent, or a parent that is not a
    # candidate at all. Returned so `plan` can say so rather than drop it.
    stranded = [path for spec, path in deferred if spec.id not in planned]
    return ordered, stranded + [r.path for r in unreadable]


# ------------------------------------------------------------- plan file


def _load() -> list[Planned]:
    if not PLAN.is_file():
        raise SystemExit(
            _fail(f"no plan at {PLAN.relative_to(REPO)} — run `plan` first")
        )
    try:
        return [Planned(**row) for row in json.loads(PLAN.read_text())]
    except TypeError as stale:
        raise SystemExit(
            _fail(
                f"{PLAN.relative_to(REPO)} does not match this driver ({stale}) "
                "— re-run `plan --force`"
            )
        ) from stale


def _save(rows: list[Planned]) -> None:
    PLAN.parent.mkdir(parents=True, exist_ok=True)
    PLAN.write_text(json.dumps([r.__dict__ for r in rows], indent=2) + "\n")


# ------------------------------------------------------------- commands


def cmd_plan(args) -> int:
    if PLAN.is_file() and not args.force:
        return _fail(f"{PLAN.relative_to(REPO)} exists — pass --force to re-snapshot")
    candidates, refusals = _scan(ignore_open_prs=args.force)
    ordered, stranded = _order(candidates, refusals)
    if not ordered:
        print("nothing to run: no candidate specs")
        for r in refusals:
            print(f"  {r.path.name}: {r.reason}")
        return 1
    _save(ordered)

    print(f"plan: {len(ordered)} spec(s), bottom of the stack first\n")
    for i, p in enumerate(ordered, 1):
        dep = f"  depends_on={p.depends_on}" if p.depends_on else ""
        print(f"  {i}. {p.spec_id}  priority={p.priority}{dep}")
    # Every refusal whose spec did not make the plan — including the ones that
    # mention `depends_on`, which are only *usually* deferrals.
    planned_paths = {p.path for p in ordered}
    held = [
        r
        for r in refusals
        if str(r.path.relative_to(REPO) if r.path.is_absolute() else r.path)
        not in planned_paths
        or r.path in stranded
    ]
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
        # Not `tasks[-1]`. `Ledger.tasks_by_spec`'s own docstring says folding
        # to the highest task_id answers a different question, "one an
        # `ORPHANED` corpse from a later killed run silently wins" — and this
        # repo's ledger proves it: SA-0013 holds ten rows at one sha with the
        # MERGED one at index 8 and NOT_IMPLEMENTED after it. The question
        # here is "did a cell produce a pull request for this spec", so a row
        # that carries one outranks a later row that does not.
        # `tasks_by_repo` is the public read that carries `pr_url`;
        # `tasks_by_spec` selects four columns and this is not one of them.
        urls = {
            row["task_id"]: row["pr_url"]
            for row in ledger.tasks_by_repo(repo_id)
            if row["pr_url"]
        }
        chosen = next(
            (row for row in reversed(tasks) if row["task_id"] in urls), tasks[-1]
        )
        match.state = chosen["state"]
        url = urls.get(chosen["task_id"], "")
        match.pr = int(url.rstrip("/").rsplit("/", 1)[-1]) if "/pull/" in url else None
    finally:
        ledger.close()

    _save(rows)
    where = f"#{match.pr}" if match.pr else "(no PR)"
    print(f"{match.spec_id}  {match.state}  {where}")
    return 0 if match.state == "READY_FOR_REVIEW" else 1


def cmd_skip(args) -> int:
    """Take a spec out of the loop by hand.

    `state` is only ever set by `record`, and `record` fails outright when the
    ledger has no task at the spec's current sha — so without this, `next`
    returns the same spec forever and an agent following the loop mechanically
    re-runs the same cell at an hour and real money a pass.
    """
    rows = _load()
    match = next((p for p in rows if p.spec_id == args.spec_id), None)
    if match is None:
        return _fail(f"{args.spec_id} is not in the plan")
    match.state = f"SKIPPED: {args.why}"
    _save(rows)
    print(f"{match.spec_id}  {match.state}")
    return 0


def cmd_status(_args) -> int:
    rows = _load()
    if not rows:
        return _fail("the plan is empty — re-run `plan --force`")
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

    p = sub.add_parser("skip", help="take a spec out of the loop by hand")
    p.add_argument("spec_id")
    p.add_argument("--why", required=True, help="what the operator should know")
    p.set_defaults(func=cmd_skip)

    p = sub.add_parser("status", help="show the plan and what has run")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("stack", help="link the reviewable PRs into a GitHub stack")
    p.add_argument("--execute", action="store_true", help="actually run gh stack link")
    p.set_defaults(func=cmd_stack)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
