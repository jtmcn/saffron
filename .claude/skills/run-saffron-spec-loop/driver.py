#!/usr/bin/env python3
"""Drive Saffron's spec loop over every queued spec, stacking the pull
requests instead of merging them. `SKILL.md` is the procedure; this is its
state.

`saffron queue` checks every spec against a conflict set that includes open
pull requests, and this loop leaves them open, so the loop's order is
snapshotted once, before any exists, and every later command reads
`.saffron-loop/order.json`.

The driver starts no cell: `saffron cell` takes `CLAUDE_CODE_OAUTH_TOKEN`
scoped to its own invocation, so the delegate driving the loop starts it and
calls `record` afterwards.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
STATE_DIR = REPO / ".saffron-loop"
ORDER = STATE_DIR / "order.json"
LEGACY_PLAN = STATE_DIR / "plan.json"
ONTOLOGY = REPO / "ontology" / "factory.ttl"
ONTOLOGY_NS = "urn:software-factory:ns#"
# What the CLI prints at column 0 while a cell runs. Terminal states are not
# listed here: `watch_pattern` takes them from the ontology's closed set.
WATCH_PREFIXES = (
    "IMPLEMENT",
    "GATE",
    "REVIEW",
    "REBUT",
    "PACKAGE",
    "gates:",
    "baseline:",
    "ceilings:",
    "teardown",
    "rate limit",
    "cell:",
)

if not (REPO / "DESIGN.md").is_file():  # the skill was moved; say so, do not guess
    raise SystemExit(
        f"error: {REPO} is not the Saffron repo root — this driver resolves it "
        "as parents[3] of its own path, so moving the skill directory breaks it"
    )


def _fail(message: str) -> int:
    """1, not 2: `saffron/cli.py` reserves 2 for infrastructure."""
    print(f"error: {message}", file=sys.stderr)
    return 1


class GitError(RuntimeError):
    pass


def _git(*args: str, cwd: Path = REPO) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if done.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {done.stderr.strip()}")
    return done.stdout.strip()


# --------------------------------------------------------------- the order


@dataclass
class OrderRow:
    spec_id: str
    path: str
    priority: int
    depends_on: list[str] = field(default_factory=list)
    spec_sha: str = ""
    state: str | None = None
    pr: int | None = None
    branch: str = ""
    # A cell that stopped without deciding (a rate limit, an orphan). `next`
    # walks past a spec carrying one, so a closed window cannot loop forever.
    last_state: str | None = None
    undecided_cells: int = 0
    dropped: str | None = None

    @property
    def pending(self) -> bool:
        return self.state is None and self.dropped is None

    @property
    def reviewable(self) -> bool:
        return self.state == "READY_FOR_REVIEW" and self.pr is not None


def _ledger_and_repo():
    """The ledger and this repo's id, resolved the way `cli._queue` does: the
    ledger holds the SSH remote, so any other spelling finds nothing."""
    from saffron.ledger import Ledger
    from saffron.phases import package as package_phase

    url = package_phase.real_remote(REPO)
    ledger = Ledger(Path.home() / ".saffron" / "ledger.db")
    return ledger, ledger.resolve_repo_id(url), url


def _protected() -> list[str]:
    """`policy.yaml`'s protected paths — gate 0's first refusal, kept here so
    a collision is found before a cell rather than inside one (`SA-0023`)."""
    from saffron.repos.policy import PolicyError, load_policy

    try:
        policy, _sha = load_policy(REPO)
    except PolicyError:
        return []
    return list(getattr(policy, "protected", []) or [])


def _scan(*, ignore_open_prs: bool):
    """`build_queue` over the specs on disk. A re-snapshot mid-loop looks past
    open pull requests, which are this loop's own; a first one does not."""
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


def _relative(path: Path) -> str:
    return str(path.relative_to(REPO)) if path.is_absolute() else str(path)


def _order(
    candidates, refusals, carried: Sequence[OrderRow] = ()
) -> tuple[list[OrderRow], list[Path]]:
    """Parents before children, then priority, then id. A spec refused only
    for an unmet `depends_on` on a parent in the order is admitted; every
    other refusal stands. A `carried` row outranks the scan's row for its id."""
    from saffron.intake import load_spec

    def row_for(spec, path: Path) -> OrderRow:
        return OrderRow(
            spec_id=spec.id,
            path=_relative(path),
            priority=spec.priority,
            depends_on=list(spec.depends_on),
            spec_sha=load_spec(REPO / _relative(path))[1],
            branch=f"saffron/{spec.id}",
        )

    admitted = {p.spec_id: p for p in carried}
    for c in candidates:
        admitted.setdefault(c.spec.id, row_for(c.spec, c.path))

    deferred = []
    unreadable = []
    for refusal in refusals:
        if "depends_on" not in refusal.reason:
            continue
        try:
            spec, _sha = load_spec(refusal.path)
        except Exception:
            # A parse failure can name `depends_on` too, and is not a deferral.
            unreadable.append(refusal)
            continue
        deferred.append((spec, refusal.path))

    for _ in range(len(deferred) + 1):  # enough passes for a chain
        for spec, path in deferred:
            if spec.id not in admitted and all(d in admitted for d in spec.depends_on):
                admitted[spec.id] = row_for(spec, path)

    ordered: list[OrderRow] = []
    remaining = dict(admitted)
    while remaining:
        ready = [
            p
            for p in remaining.values()
            if all(d not in remaining for d in p.depends_on)
        ]
        if not ready:  # a dependency cycle; emit the rest stably rather than hang
            ready = sorted(remaining.values(), key=lambda p: p.spec_id)
        ready.sort(key=lambda p: (p.priority, p.spec_id))
        ordered.append(ready[0])
        del remaining[ready[0].spec_id]

    stranded = [path for spec, path in deferred if spec.id not in admitted]
    return ordered, stranded + [r.path for r in unreadable]


def _parse_order() -> list[OrderRow]:
    return [OrderRow(**row) for row in json.loads(ORDER.read_text())]


def _load() -> list[OrderRow]:
    if not ORDER.is_file():
        legacy = (
            f" ({LEGACY_PLAN.relative_to(REPO)} is the previous driver's file — delete it)"
            if LEGACY_PLAN.is_file()
            else ""
        )
        raise SystemExit(
            _fail(f"no order at {ORDER.relative_to(REPO)} — run `snapshot`{legacy}")
        )
    try:
        return _parse_order()
    except TypeError as stale:
        raise SystemExit(
            _fail(
                f"{ORDER.relative_to(REPO)} does not match this driver ({stale}) — `snapshot --force`"
            )
        ) from stale


def _save(rows: list[OrderRow]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    ORDER.write_text(json.dumps([r.__dict__ for r in rows], indent=2) + "\n")


def _gh_pr_field(number: int, name: str) -> str | None:
    done = subprocess.run(
        ["gh", "pr", "view", str(number), "--json", name, "-q", f".{name}"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    return done.stdout.strip() if done.returncode == 0 else None


def _pr_state(number: int) -> str | None:
    return _gh_pr_field(number, "state")


def _stale_reasons(
    p: OrderRow, pr_state: Callable[[int], str | None] = _pr_state
) -> list[str]:
    from saffron.intake import load_spec

    path = REPO / p.path
    if not path.is_file():
        return [f"{p.spec_id}: {p.path} is gone"]
    reasons = []
    if p.spec_sha and load_spec(path)[1] != p.spec_sha:
        reasons.append(f"{p.spec_id}: the spec changed after the snapshot")
    if p.pr and (state := pr_state(p.pr)) in {"MERGED", "CLOSED"}:
        reasons.append(f"{p.spec_id}: #{p.pr} is {state}")
    return reasons


def _stale(
    rows: list[OrderRow], *, pr_state: Callable[[int], str | None] = _pr_state
) -> list[str]:
    """Why the order no longer describes the repository, if it does not. A
    leftover order once listed a merged PR as reviewable and an unrun spec as
    next, and nothing said so (2026-09-12)."""
    return [reason for p in rows for reason in _stale_reasons(p, pr_state)]


def _carried() -> list[OrderRow]:
    """The rows a re-snapshot keeps: every recorded outcome still true.
    `build_queue` passes over a spec with a finished task, so an order rebuilt from
    the scan alone dropped every reviewable pull request."""
    try:
        previous = _parse_order() if ORDER.is_file() else []
    except (TypeError, ValueError):
        return []  # an order this driver cannot read has nothing to carry
    return [
        p
        for p in previous
        if (p.state or p.dropped or p.last_state) and not _stale_reasons(p)
    ]


# ------------------------------------------------------------ the stack


def _stack_order(rows: list[OrderRow]) -> tuple[list[OrderRow], list[str]]:
    """The reviewable pull requests, bottom to top, each child directly above
    its parent. Snapshot order alone put a child above an unrelated sibling,
    and the child's PR then showed its parent's changes. A stack is a line, so
    a parent with two children, or a child whose parent is not in it, is said
    rather than hidden."""
    ready = [p for p in rows if p.reviewable]
    ids = {p.spec_id for p in ready}
    by_id = {p.spec_id: p for p in rows}

    def parent(p: OrderRow) -> str | None:
        return next((d for d in p.depends_on if d in ids), None)

    order: list[OrderRow] = []
    seen: set[str] = set()

    def visit(p: OrderRow) -> None:
        if p.spec_id in seen:
            return
        seen.add(p.spec_id)
        order.append(p)
        for child in ready:
            if parent(child) == p.spec_id:
                visit(child)

    for p in ready:
        if parent(p) is None:
            visit(p)
    for p in ready:  # a dependency cycle leaves some unvisited
        visit(p)

    warnings = []
    for lower, upper in zip(order, order[1:], strict=False):
        want = parent(upper)
        if want is not None and want != lower.spec_id:
            warnings.append(
                f"{upper.spec_id} sits above {lower.spec_id}, not its parent {want}: "
                f"#{upper.pr} will show {want}'s changes"
            )
    for p in ready:
        for dep in p.depends_on:
            if dep in by_id and dep not in ids:
                warnings.append(
                    f"{p.spec_id}'s parent {dep} is not in the stack; "
                    f"#{p.pr} stays based on {by_id[dep].branch}"
                )
    return order, warnings


def _trunk(cwd: Path = REPO) -> str:
    try:
        return _git("symbolic-ref", "--short", "refs/remotes/origin/HEAD", cwd=cwd)
    except GitError:
        return "origin/main"


def _merge_conflicts(lower: str, upper: str, cwd: Path = REPO) -> list[str]:
    """What merging the two would conflict on. A retargeted PR page looks
    clean either way: two siblings both appending `## 34.` to the backlog did."""
    done = subprocess.run(
        ["git", "merge-tree", "--write-tree", lower, upper],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if done.returncode == 0:
        return []
    conflicts = [
        line for line in done.stdout.splitlines() if line.startswith("CONFLICT")
    ]
    return conflicts or [f"merge-tree exited {done.returncode}: {done.stderr.strip()}"]


# ----------------------------------------------------------- the rebase


@dataclass
class Layer:
    branch: str
    old_tip: str
    fork: str
    onto: str


def _fork_point(branch: str, lower: str, trunk: str, cwd: Path = REPO) -> str:
    """Where `branch` left what it was cut from: its merge-base with the layer
    below or with the trunk, whichever is newer. A child forks from its
    parent; a sibling forks from the trunk it was cut from, even when the
    layer below was cut from an older one."""
    below = _git("merge-base", branch, lower, cwd=cwd)
    trunkward = _git("merge-base", branch, trunk, cwd=cwd)
    newer_is_trunkward = (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", below, trunkward], cwd=cwd
        ).returncode
        == 0
    )
    return trunkward if newer_is_trunkward else below


def _layers(
    branches: list[str], trunk: str, cwd: Path = REPO, prefix: str = "origin/"
) -> list[Layer]:
    """Every fork point, taken before anything moves."""
    layers = []
    for i, branch in enumerate(branches):
        ref = prefix + branch
        lower = trunk if i == 0 else prefix + branches[i - 1]
        layers.append(
            Layer(
                branch=branch,
                old_tip=_git("rev-parse", ref, cwd=cwd),
                fork=_fork_point(ref, lower, trunk, cwd),
                onto=trunk if i == 0 else branches[i - 1],
            )
        )
    return layers


def _patch_id(a: str, b: str, cwd: Path) -> str:
    diff = subprocess.run(
        ["git", "diff", a, b], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout
    out = subprocess.run(
        ["git", "patch-id", "--stable"],
        cwd=cwd,
        input=diff,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return out.split()[0] if out else ""


def _restore(layers: list[Layer], start: str, cwd: Path) -> None:
    subprocess.run(["git", "checkout", "-q", "--detach"], cwd=cwd, capture_output=True)
    for layer in layers:
        _git("branch", "-f", layer.branch, layer.old_tip, cwd=cwd)
    if start != "HEAD":
        subprocess.run(["git", "checkout", "-q", start], cwd=cwd, capture_output=True)


def _apply_layers(layers: list[Layer], cwd: Path = REPO) -> tuple[bool, list[str]]:
    """Rebase each layer onto the one below, bottom to top, then compare each
    layer's patch-id with what it was. Any conflict restores every branch."""
    if _git("status", "--porcelain", "--untracked-files=no", cwd=cwd):
        return False, ["the working tree has changes; commit or stash them first"]
    for layer in layers:
        local = subprocess.run(
            ["git", "rev-parse", "--verify", "-q", f"refs/heads/{layer.branch}"],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        if local.returncode != 0:
            _git("branch", layer.branch, layer.old_tip, cwd=cwd)
        elif local.stdout.strip() != layer.old_tip:
            return False, [
                f"local {layer.branch} is {local.stdout.strip()[:8]}, not the recorded "
                f"{layer.old_tip[:8]}; push or reset it first"
            ]

    start = _git("rev-parse", "--abbrev-ref", "HEAD", cwd=cwd)
    for layer in layers:
        done = subprocess.run(
            ["git", "rebase", "-q", "--onto", layer.onto, layer.fork, layer.branch],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        if done.returncode != 0:
            subprocess.run(["git", "rebase", "--abort"], cwd=cwd, capture_output=True)
            _restore(layers, start, cwd)
            conflicts = [
                line
                for line in (done.stdout + done.stderr).splitlines()
                if "CONFLICT" in line
            ]
            return False, [
                f"{layer.branch} conflicts on {layer.onto}; every branch is restored",
                *conflicts,
            ]

    messages = []
    for layer in layers:
        before = _patch_id(layer.fork, layer.old_tip, cwd)
        after = _patch_id(layer.onto, layer.branch, cwd)
        messages.append(
            f"{layer.branch}: identical"
            if before == after
            else f"{layer.branch}: content changed — "
            f"git range-diff {layer.fork[:8]}..{layer.old_tip[:8]} {layer.onto}..{layer.branch}"
        )
    if start != "HEAD":
        subprocess.run(["git", "checkout", "-q", start], cwd=cwd, capture_output=True)
    return True, messages


def _push_command(layers: list[Layer]) -> str:
    leases = " ".join(f"--force-with-lease={x.branch}:{x.old_tip}" for x in layers)
    return f"git push {leases} origin {' '.join(x.branch for x in layers)}"


# ------------------------------------------------------- the watch line


def terminal_states() -> list[str]:
    """The ontology's closed `TerminalState` set, read rather than copied: a
    hand copy missed three of the nine."""
    import rdflib

    graph = rdflib.Graph().parse(ONTOLOGY, format="turtle")
    states = sorted(
        str(s).removeprefix(ONTOLOGY_NS)
        for s in graph.subjects(
            rdflib.RDF.type, rdflib.URIRef(f"{ONTOLOGY_NS}TerminalState")
        )
    )
    if not states:
        raise SystemExit(
            _fail(f"no TerminalState members in {ONTOLOGY.relative_to(REPO)}")
        )
    return states


def watch_pattern() -> str:
    """The Monitor's `grep -E` pattern: phase lines anchored, terminal states
    not — the CLI prints a state after a padded spec id."""
    states = "|".join(terminal_states())
    return f"^({'|'.join(WATCH_PREFIXES)})|({states})|Traceback"


# ------------------------------------------------------------- commands


def cmd_snapshot(args) -> int:
    if ORDER.is_file() and not args.force:
        return _fail(f"{ORDER.relative_to(REPO)} exists — pass --force to re-snapshot")
    carried = _carried() if args.force else []
    candidates, refusals = _scan(ignore_open_prs=args.force)
    ordered, stranded = _order(candidates, refusals, carried)
    if not ordered:
        print("nothing to run: no candidate specs")
        for r in refusals:
            print(f"  {r.path.name}: {r.reason}")
        return 1
    _save(ordered)

    print(f"order: {len(ordered)} spec(s), bottom of the stack first\n")
    for i, p in enumerate(ordered, 1):
        dep = f"  depends_on={p.depends_on}" if p.depends_on else ""
        print(f"  {i}. {p.spec_id}  priority={p.priority}{dep}")
    ordered_paths = {p.path for p in ordered}
    held = [
        r
        for r in refusals
        if _relative(r.path) not in ordered_paths or r.path in stranded
    ]
    if held:
        print(f"\nrefused, and not in the order ({len(held)}):")
        for r in held:
            print(f"  {r.path.name}: {r.reason}")
    print(f"\nwritten to {ORDER.relative_to(REPO)}")
    loose = [p for p in ordered[1:] if not p.depends_on]
    if loose:
        print(
            f"\nnote: {len(loose)} spec(s) declare no depends_on, so their branches are "
            "siblings\n      cut from the default branch; `rebase` chains them if asked."
        )
    return 0


def _next_spec(
    rows: list[OrderRow], *, again: bool
) -> tuple[OrderRow | None, str | None]:
    """The first pending spec no cell has answered, and a note when its parent
    is reviewable: a child's worktree is cut from the parent's branch, so the
    parent's review commits have to be pushed first. A child whose parent in
    the order has no reviewable branch is held back: `saffron cell` does not
    refuse it, and would cut its worktree from main."""
    by_id = {p.spec_id: p for p in rows}
    notes = []
    for p in rows:
        if not (p.pending and (again or p.last_state is None)):
            continue
        unready = [
            (d, by_id[d])
            for d in p.depends_on
            if d in by_id and by_id[d].state != "READY_FOR_REVIEW"
        ]
        if unready:
            d, parent = unready[0]
            why = (
                "dropped"
                if parent.dropped
                else parent.state or parent.last_state or "not run yet"
            )
            notes.append(
                f"held back {p.spec_id}: its parent {d} is {why}, "
                "so a cell would cut it from main"
            )
            continue
        parents = [d for d in p.depends_on if d in by_id]
        if parents:
            notes.append(
                f"{p.spec_id} is cut from {', '.join(parents)}: push "
                f"{'their' if len(parents) > 1 else 'its'} review commits first"
            )
        return p, "; ".join(notes) or None
    return None, "; ".join(notes) or None


def cmd_next(args) -> int:
    """`--again` hands back a spec a cell stopped on without deciding — the
    case is a reopened rate-limit window."""
    rows = _load()
    if reasons := _stale(rows):
        print("the order is stale:", file=sys.stderr)
        for reason in reasons:
            print(f"  {reason}", file=sys.stderr)
        print("re-snapshot with `snapshot --force`.", file=sys.stderr)
        return 1
    chosen, note = _next_spec(rows, again=args.again)
    if note:
        print(f"note: {note}", file=sys.stderr)
    if chosen is not None:
        print(chosen.spec_id)
        return 0
    pending = [p for p in rows if p.pending]
    if not pending:
        print("done: every spec in the order has been run or dropped", file=sys.stderr)
        return 1
    print(
        "nothing untouched left: every pending spec has already had a cell.",
        file=sys.stderr,
    )
    for p in pending:
        print(
            f"  {p.spec_id}  last={p.last_state}  cells={p.undecided_cells}",
            file=sys.stderr,
        )
    print(
        "`next --again` after a reopened rate-limit window; `drop <spec> --why …` otherwise.",
        file=sys.stderr,
    )
    return 1


def cmd_record(args) -> int:
    """What the cell did, read from the ledger (§4.3)."""
    rows = _load()
    match = next((p for p in rows if p.spec_id == args.spec_id), None)
    if match is None:
        return _fail(f"{args.spec_id} is not in the order")

    from saffron.intake import load_spec
    from saffron.reconcile import IN_FLIGHT_STATES
    from saffron.scheduler import DONE_STATES

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
        # Not `tasks[-1]`: a later orphaned or unfinished row must not hide the
        # one that opened a pull request (SA-0013 holds ten rows at one sha).
        urls = {
            row["task_id"]: row["pr_url"]
            for row in ledger.tasks_by_repo(repo_id)
            if row["pr_url"]
        }
        chosen = next(
            (row for row in reversed(tasks) if row["task_id"] in urls), tasks[-1]
        )
        state = chosen["state"]
        url = urls.get(chosen["task_id"], "")
        pr = int(url.rstrip("/").rsplit("/", 1)[-1]) if "/pull/" in url else None

        if state in DONE_STATES:
            match.state, match.pr = state, pr
        else:
            # Nothing was decided. Keep a PR number the ledger still carries: a
            # `CHANGES_REQUESTED` spec has one open.
            match.state = None
            match.pr = pr or match.pr
            match.last_state = state
            if state not in IN_FLIGHT_STATES:
                match.undecided_cells += 1
    finally:
        ledger.close()

    _save(rows)
    where = f"#{match.pr}" if match.pr else "(no PR)"
    print(f"{match.spec_id}  {state}  {where}")
    if match.state is None:
        why = (
            "the cell is still running — wait for it to exit, then record again"
            if state in IN_FLIGHT_STATES
            else "nothing was decided; `next` moves on to the next untouched spec"
        )
        print(f"left pending: {why}.", file=sys.stderr)
    return 0 if state == "READY_FOR_REVIEW" else 1


def cmd_drop(args) -> int:
    """Take a spec out of the loop — the way out when `record` cannot find a
    task and `next` would otherwise hand the same spec back forever."""
    rows = _load()
    match = next((p for p in rows if p.spec_id == args.spec_id), None)
    if match is None:
        return _fail(f"{args.spec_id} is not in the order")
    match.dropped = args.why
    _save(rows)
    print(f"{match.spec_id}  dropped: {args.why}")
    return 0


def cmd_status(_args) -> int:
    rows = _load()
    if not rows:
        return _fail("the order is empty — `snapshot --force`")
    width = max(len(p.spec_id) for p in rows)
    for p in rows:
        pr = f"#{p.pr}" if p.pr else ""
        if p.dropped:
            label, extra = "dropped", f"  ({p.dropped})"
        else:
            label = p.state or "pending"
            extra = (
                f"  (last {p.last_state}, {p.undecided_cells} undecided cell(s))"
                if p.pending and p.last_state
                else ""
            )
        print(f"  {p.spec_id:<{width}}  {label:<18} {pr:<5}{extra}")
    ready = [p for p in rows if p.reviewable]
    print(f"\n{len(ready)}/{len(rows)} reviewable")
    if reasons := _stale(rows):
        print("\nstale — `snapshot --force` before the next cell:")
        for reason in reasons:
            print(f"  {reason}")
    return 0


def cmd_stack(args) -> int:
    order, warnings = _stack_order(_load())
    if len(order) < 2:
        return _fail(
            f"a stack needs two or more reviewable pull requests; have {len(order)}"
        )
    subprocess.run(["git", "fetch", "-q", "origin"], cwd=REPO)

    print("stack, bottom to top:")
    for p in order:
        print(f"  #{p.pr}  {p.spec_id}  ({p.branch})")
    for warning in warnings:
        print(f"\nwarning: {warning}")
    clean = True
    for lower, upper in zip(order, order[1:], strict=False):
        conflicts = _merge_conflicts(f"origin/{lower.branch}", f"origin/{upper.branch}")
        if conflicts:
            clean = False
            print(f"\n{lower.branch} and {upper.branch} do not merge cleanly:")
            for line in conflicts:
                print(f"  {line}")
    if clean:
        print("\nevery adjacent pair merges cleanly (git merge-tree)")

    command = ["gh", "stack", "link", *(str(p.pr) for p in order)]
    print(f"\n  {' '.join(command)}")
    print("\nPRs stay drafts (§5.7); ratifying is `gh pr ready <n>`, the operator's.")
    if not args.execute:
        print("\n(dry run — pass --execute to link)")
        return 0

    done = subprocess.run(command, cwd=REPO, text=True)
    if done.returncode != 0:
        return _fail(f"gh stack link exited {done.returncode}")
    trunk = _trunk().removeprefix("origin/")
    mismatched = 0
    print("\nbases, read back:")
    for i, p in enumerate(order):
        want = trunk if i == 0 else order[i - 1].branch
        got = _gh_pr_field(p.pr, "baseRefName") if p.pr else None
        mismatched += got != want
        print(
            f"  #{p.pr}  base={got}" + ("" if got == want else f"  — expected {want}")
        )
    return 1 if mismatched else 0


def cmd_rebase(args) -> int:
    order, warnings = _stack_order(_load())
    if not order:
        return _fail("no reviewable pull requests to rebase")
    for warning in warnings:
        print(f"warning: {warning}")
    subprocess.run(["git", "fetch", "-q", "origin"], cwd=REPO)
    trunk = _trunk()
    try:
        layers = _layers([p.branch for p in order], trunk)
    except GitError as err:
        return _fail(str(err))

    targets = [trunk] + [f"origin/{layer.branch}" for layer in layers[:-1]]
    moving = [
        layer
        for layer, target in zip(layers, targets, strict=True)
        if layer.fork != _git("rev-parse", target)
    ]
    print(f"rebase, bottom to top (trunk {trunk}):")
    for layer in layers:
        print(f"  {layer.branch}  fork {layer.fork[:8]}  onto {layer.onto}")
    if not moving:
        print("\nevery layer already sits on the one below — nothing to rebase")
        return 0

    push = _push_command(layers)
    if not args.execute:
        print(f"\nthen, with the operator's approval:\n  {push}")
        print("\n(dry run — pass --execute to rebase locally)")
        return 0

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    record = STATE_DIR / f"rebase-{time.strftime('%Y%m%dT%H%M%S')}.json"
    record.write_text(json.dumps([layer.__dict__ for layer in layers], indent=2) + "\n")
    ok, messages = _apply_layers(layers)
    for message in messages:
        print(f"  {message}")
    if not ok:
        return 1
    print(f"\nrecorded SHAs: {record.relative_to(REPO)}")
    print(f"push, with the operator's approval:\n  {push}")
    return 0


def cmd_pattern(_args) -> int:
    print(watch_pattern())
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("snapshot", help="write the loop's order, before any PR exists")
    p.add_argument("--force", action="store_true", help="replace an existing order")
    p.set_defaults(func=cmd_snapshot)

    p = sub.add_parser("next", help="print the next spec to start a cell for")
    p.add_argument(
        "--again",
        action="store_true",
        help="hand back a spec a cell stopped on undecided",
    )
    p.set_defaults(func=cmd_next)

    p = sub.add_parser("record", help="read the ledger for what a cell did")
    p.add_argument("spec_id")
    p.set_defaults(func=cmd_record)

    p = sub.add_parser("drop", help="take a spec out of the loop")
    p.add_argument("spec_id")
    p.add_argument("--why", required=True, help="what the operator should know")
    p.set_defaults(func=cmd_drop)

    p = sub.add_parser("status", help="show the order, what has run, and staleness")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("stack", help="link the reviewable PRs into one GitHub stack")
    p.add_argument("--execute", action="store_true", help="run gh stack link")
    p.set_defaults(func=cmd_stack)

    p = sub.add_parser(
        "rebase", help="chain the stack's branches, each onto the one below"
    )
    p.add_argument("--execute", action="store_true", help="rebase the local branches")
    p.set_defaults(func=cmd_rebase)

    p = sub.add_parser("pattern", help="print the Monitor's grep -E pattern")
    p.set_defaults(func=cmd_pattern)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
