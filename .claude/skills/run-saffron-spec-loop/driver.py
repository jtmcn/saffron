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
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from saffron.gates.contract import GateResult
    from saffron.intake import Spec

REPO = Path(__file__).resolve().parents[3]
STATE_DIR = REPO / ".saffron-loop"
SPECS_DIR = REPO / ".saffron" / "specs"
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
    # Neither a phase nor a state, and `budget:` is what says a turn-ceiling
    # line is the end (SA-0087).
    "PLAN",
    "budget:",
    # Every `events.LineLabel` member, held to that closed set by a test:
    # `SALVAGE` was missing, so the watcher saw a salvage start and never
    # whether it recovered anything, and `SCOPE`/`REPAIR` were never shown
    # at all (item 139). `SCOPE` covers `SCOPE_REVIEW` as a prefix.
    "SALVAGE",
    "SCOPE",
    "REPAIR",
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
    # What PACKAGE pushed, from the ledger; a branch head past it carries
    # review commits. Empty in an order written before `record` stored it.
    pushed_sha: str = ""
    # The spec's sha on disk when a re-snapshot found it edited with its pull
    # request still open. The row is kept at `spec_sha` — the sha its task
    # actually ran at — and this records the edit as acknowledged, so the
    # order does not read as stale forever and `next` is not deadlocked by a
    # spec that cannot be re-queued until its pull request closes (item 137).
    edited_sha: str = ""
    # Why `next` passes over this spec: its edit is open as a pull request, so
    # a cell would run the old text. A re-snapshot releases it.
    held: str | None = None

    title: str = ""
    budget_usd: float = 0.0
    risk: str = "standard"

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


def _hiding(gh, branches: frozenset[str]):
    """`gh`, with every pull request from `branches` left out of what it lists."""

    def run(argv):
        done = gh(argv)
        try:
            listed = json.loads(done.stdout)
        except (TypeError, ValueError):
            return done
        if done.returncode != 0 or not isinstance(listed, list):
            return done
        kept = [
            pr
            for pr in listed
            if not (isinstance(pr, dict) and pr.get("headRefName") in branches)
        ]
        return subprocess.CompletedProcess(argv, 0, json.dumps(kept), done.stderr)

    return run


def _scan(*, loop_branches: frozenset[str]):
    """`build_queue` over the specs on disk. A re-snapshot mid-loop looks past
    the loop's own open pull requests, each of which would refuse its
    siblings on the conflict set, and no one else's."""
    from saffron.phases import package as package_phase
    from saffron.scheduler import build_queue, run_gh

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
            gh=_hiding(run_gh, loop_branches),
        )
    finally:
        ledger.close()


def _relative(path: Path) -> str:
    return str(path.relative_to(REPO)) if path.is_absolute() else str(path)


def _order(
    candidates,
    refusals,
    carried: Sequence[OrderRow] = (),
    exclude: frozenset[str] = frozenset(),
) -> tuple[list[OrderRow], list[Path]]:
    """Parents before children, then priority, then id. A spec refused only
    for an unmet `depends_on` on a parent in the order is admitted; every
    other refusal stands. A `carried` row outranks the scan's row for its id,
    and an `exclude`d id is admitted by neither."""
    from saffron.intake import load_spec

    def row_for(spec, path: Path) -> OrderRow:
        return OrderRow(
            spec_id=spec.id,
            path=_relative(path),
            priority=spec.priority,
            depends_on=list(spec.depends_on),
            spec_sha=load_spec(REPO / _relative(path))[1],
            branch=f"saffron/{spec.id}",
            title=spec.title,
            budget_usd=spec.budget_usd,
            risk=spec.risk,
        )

    admitted = {p.spec_id: p for p in carried}
    for c in candidates:
        if c.spec.id not in exclude:
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
            if (
                spec.id not in admitted
                and spec.id not in exclude
                and all(d in admitted for d in spec.depends_on)
            ):
                admitted[spec.id] = row_for(spec, path)

    stranded = [path for spec, path in deferred if spec.id not in admitted]
    return _sequence(list(admitted.values())), stranded + [r.path for r in unreadable]


def _sequence(rows: list[OrderRow]) -> list[OrderRow]:
    """Parents before children; among the rows ready at each turn, priority,
    then the most descendants, then id. A parent that sorts late leaves its
    children nothing independent to run beside its review (stack #251)."""
    children: dict[str, list[str]] = {}
    for p in rows:
        for d in p.depends_on:
            children.setdefault(d, []).append(p.spec_id)

    def descendants(spec_id: str) -> int:
        seen: set[str] = set()
        stack = list(children.get(spec_id, []))
        while stack:
            child = stack.pop()
            if child not in seen:
                seen.add(child)
                stack.extend(children.get(child, []))
        return len(seen)

    ordered: list[OrderRow] = []
    remaining = {p.spec_id: p for p in rows}
    while remaining:
        ready = [
            p
            for p in remaining.values()
            if all(d not in remaining for d in p.depends_on)
        ]
        if not ready:  # a dependency cycle; emit the rest stably rather than hang
            ready = sorted(remaining.values(), key=lambda p: p.spec_id)
        ready.sort(key=lambda p: (p.priority, -descendants(p.spec_id), p.spec_id))
        ordered.append(ready[0])
        del remaining[ready[0].spec_id]
    return ordered


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
    on_disk = load_spec(path)[1]
    if p.spec_sha and on_disk != p.spec_sha and on_disk != p.edited_sha:
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
    reasons = [reason for p in rows for reason in _stale_reasons(p, pr_state)]
    return reasons + _edit_traps(rows, pr_state)


def _edit_traps(
    rows: list[OrderRow], pr_state: Callable[[int], str | None] = _pr_state
) -> list[str]:
    """What a spec edit costs when that spec's pull request is already open.

    `spec_sha` is what the order and the dependency check key on, so editing a
    spec that has already run stops the ledger's task matching it: the next
    `snapshot --force` holds the spec out of the order *and* refuses every
    dependent, and the held-out spec loses its recorded outcome, so `stack`
    later omits its pull request. The bare "the spec changed" line above says
    none of that, and an operator reading a review is exactly who edits one
    (item 137). Two pull requests, 2026-09-16."""
    from saffron.intake import load_spec

    edited: list[OrderRow] = []
    for p in rows:
        path = REPO / p.path
        if not path.is_file() or not p.spec_sha:
            continue
        on_disk = load_spec(path)[1]
        if on_disk == p.spec_sha or on_disk == p.edited_sha:
            continue  # unedited, or edited and already kept by a re-snapshot
        if p.pr and pr_state(p.pr) not in {"MERGED", "CLOSED"}:
            edited.append(p)
    if not edited:
        return []

    out = []
    for p in edited:
        blocked = _dependents_of(p.spec_id, rows)
        refuses = f" and refuses {', '.join(blocked)}" if blocked else ""
        out.append(
            f"{p.spec_id}: editing it with its pull request open leaves it held "
            f"out of the order, and #{p.pr} with it{refuses}. Revert the edit to "
            "the `spec_sha` its task ran at, or let the pull request merge "
            "first (item 137)."
        )
    return out


def _dependents_of(spec_id: str, rows: list[OrderRow]) -> list[str]:
    """Every row a re-snapshot would refuse for reaching `spec_id` through
    `depends_on`, nearest first.

    Every entry, not `depends_on[0]`: the base resolver consults only the
    first, but the refusal does not — `scheduler._refuse` loops the whole list
    and `_order` admits a deferral only when *all* of them are in, so a spec
    naming the edited one second would go unnamed here. A row that already ran
    is not refused at all: `_carried` keeps it and `_order` seeds `admitted`
    with it, so the walk stops rather than claim a reviewable subtree is about
    to be lost."""
    blocked: list[str] = []
    frontier = {spec_id}
    while frontier:
        nxt = {
            p.spec_id
            for p in rows
            if any(d in frontier for d in p.depends_on)
            and p.spec_id not in blocked
            and p.spec_id != spec_id
            and not (p.state or p.dropped or p.last_state)
        }
        blocked.extend(sorted(nxt))
        frontier = nxt
    return blocked


def _previous() -> list[OrderRow]:
    try:
        return _parse_order() if ORDER.is_file() else []
    except (TypeError, ValueError):
        return []  # an order this driver cannot read has nothing to carry


def _carried(previous: list[OrderRow]) -> tuple[list[OrderRow], dict[str, str]]:
    """The rows a re-snapshot keeps, every recorded outcome still true, and
    the specs it holds out, with why. `build_queue` passes over a spec with a
    finished task, so an order rebuilt from the scan alone dropped every
    reviewable PR; and it hands back a spec edited while its PR is open as new."""
    from saffron.intake import load_spec

    kept, held = [], {}
    for p in previous:
        if not (p.state or p.dropped or p.last_state):
            continue
        reasons = _stale_reasons(p)
        if not reasons:
            kept.append(p)
        elif p.pr and _pr_state(p.pr) not in {"MERGED", "CLOSED"}:
            held[p.spec_id] = f"{'; '.join(reasons)}, and #{p.pr} is still open"
            # Kept, not dropped. Excluding it lost the outcome with it: the
            # spec left the order, `stack` printed a stack missing that pull
            # request, and every dependent was refused for a parent with no
            # task at its current sha. The row stays at the sha its task ran
            # at; `edited_sha` records the edit so the order is not stale on
            # its account, and its recorded state keeps `next` from re-running
            # it while the pull request is open (item 137).
            path = REPO / p.path
            if path.is_file():
                p.edited_sha = load_spec(path)[1]
            kept.append(p)
    return kept, held


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
            # `visit` already put `want` further down, so the merge base is its
            # head and the PR's diff is the child's own (measured on #249).
            warnings.append(
                f"{upper.spec_id} sits above its sibling {lower.spec_id}, not "
                f"directly above its parent {want}; #{upper.pr}'s diff is "
                "unaffected, and `rebase` would chain them if asked"
            )
    for i, p in enumerate(order):
        below = order[i - 1].branch if i else "the trunk"
        for dep in p.depends_on:
            if dep in by_id and dep not in ids:
                warnings.append(
                    f"{p.spec_id}'s parent {dep} is not in the stack; `link` "
                    f"retargets #{p.pr} onto {below}, where it shows {dep}'s changes"
                )
    return order, warnings


def _trunk(cwd: Path = REPO) -> str:
    try:
        return _git("symbolic-ref", "--short", "refs/remotes/origin/HEAD", cwd=cwd)
    except GitError:
        return "origin/main"


def _own_base(upper: str, others: Sequence[str], trunk: str, cwd: Path = REPO) -> str:
    """The merge base nearest `upper` among the trunk and the loop's other
    branches: a parent, a sibling it was rebased onto, or the trunk. Measured
    from the trunk, stack #251's chained SA-0080 counted three specs below it."""
    best: tuple[int, str] | None = None
    for other in (trunk, *others):
        if other == upper:
            continue
        try:
            base = _git("merge-base", other, upper, cwd=cwd)
        except GitError:
            continue
        behind = int(_git("rev-list", "--count", f"{base}..{upper}", cwd=cwd))
        if best is None or behind < best[0]:
            best = (behind, base)
    if best is None:
        raise GitError(f"{upper} shares no history with {trunk}")
    return best[1]


def _bases_below(spec_id: str, rows: list[OrderRow]) -> list[str]:
    """The loop branches `spec_id` can have been cut or rebased from: those
    below it in the stack. A child above it shares its whole tip, and as a
    candidate it had a parent measure 0 changed lines."""
    order, _warnings = _stack_order(rows)
    ids = [p.spec_id for p in order]
    below = [p.branch for p in order[: ids.index(spec_id)]] if spec_id in ids else []
    # The order is not the only source of a parent: a spec held out of it by
    # item 137 leaves this empty, and the size then falls through to the trunk
    # and counts the parent's diff as the child's (item 138).
    for ancestor in _depends_on_chain(spec_id):
        branch = f"saffron/{ancestor}"
        if branch not in below:
            below.append(branch)
    return below


def _depends_on_chain(spec_id: str) -> list[str]:
    """Every ancestor of `spec_id` by `depends_on`, nearest first. Reads the
    spec files, so it holds for a parent already retired to `done/`."""
    specs = _known_specs()
    seen: list[str] = []
    current = specs.get(spec_id)
    while current is not None and current.depends_on:
        parent = current.depends_on[0]
        if parent in seen:  # nothing validates depends_on for cycles
            break
        seen.append(parent)
        current = specs.get(parent)
    return seen


def _size(
    lower: str, upper: str, spec_type: str, touches: list[str], *, cwd: Path = REPO
) -> GateResult:
    """The `size` gate's own verdict from `lower` to `upper`. It runs only in
    the cell, so review commits can take a branch past it unseen (item 40)."""
    from saffron.cell.worktree import DIFF_FLAGS
    from saffron.gates.core.size import size_gate

    diff = _git("diff", *DIFF_FLAGS, f"{lower}...{upper}", cwd=cwd)
    return size_gate(diff, spec_type, touches, blocking=False)


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


def _held_elsewhere(cwd: Path) -> dict[str, str]:
    """Each branch checked out in a worktree other than `cwd`'s, and where."""
    here = Path(_git("rev-parse", "--show-toplevel", cwd=cwd)).resolve()
    held: dict[str, str] = {}
    path = ""
    for line in _git("worktree", "list", "--porcelain", cwd=cwd).splitlines():
        if line.startswith("worktree "):
            path = line.removeprefix("worktree ")
        elif line.startswith("branch refs/heads/") and Path(path).resolve() != here:
            held[line.removeprefix("branch refs/heads/")] = path
    return held


def _restore(layers: list[Layer], start: str, cwd: Path) -> list[str]:
    """Put back every layer that moved, and name any that could not be: a
    restore that raised halfway left HEAD detached and said nothing."""
    subprocess.run(["git", "checkout", "-q", "--detach"], cwd=cwd, capture_output=True)
    failed = []
    for layer in layers:
        try:
            if (
                _git("rev-parse", f"refs/heads/{layer.branch}", cwd=cwd)
                != layer.old_tip
            ):
                _git("branch", "-f", layer.branch, layer.old_tip, cwd=cwd)
        except GitError as err:
            failed.append(f"{layer.branch}: {err}")
    if start != "HEAD":
        subprocess.run(["git", "checkout", "-q", start], cwd=cwd, capture_output=True)
    return failed


def _apply_layers(layers: list[Layer], cwd: Path = REPO) -> tuple[bool, list[str]]:
    """Rebase each layer onto the one below, bottom to top, then compare each
    layer's patch-id with what it was. Any conflict restores every branch."""
    if _git("status", "--porcelain", "--untracked-files=no", cwd=cwd):
        return False, ["the working tree has changes; commit or stash them first"]
    # git cannot move a branch another worktree holds (step 2c's review fixes).
    elsewhere = _held_elsewhere(cwd)
    if held := [layer.branch for layer in layers if layer.branch in elsewhere]:
        return False, [
            f"{b} is checked out in {elsewhere[b]}; switch that worktree off it first"
            for b in held
        ]
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
            failed = _restore(layers, start, cwd)
            output = (done.stdout + done.stderr).splitlines()
            detail = [line for line in output if "CONFLICT" in line] or output[-1:]
            restored = (
                "every branch is restored"
                if not failed
                else "reset these to their recorded SHAs by hand:"
            )
            return False, [
                f"{layer.branch} did not rebase onto {layer.onto}; {restored}",
                *failed,
                *detail,
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
    """The Monitor's `grep -E` pattern. A terminal state is anchored where the
    CLI prints one — column 0, or after a padded spec id — because an agent
    line grepping for `SCOPE_REVIEW` fired it unanchored."""
    states = "|".join(terminal_states())
    return (
        f"^({'|'.join(WATCH_PREFIXES)})|^SA-[0-9]+ +({states})\\b|^({states})\\b"
        "|^Traceback"
    )


# ------------------------------------------------------------- commands


def cmd_snapshot(args) -> int:
    if ORDER.is_file() and not (args.force or args.new):
        return _fail(
            f"{ORDER.relative_to(REPO)} exists — pass --force to re-snapshot this "
            "loop, or --new to start another"
        )
    if args.add is not None and not args.force:
        return _fail("--add takes in specs new to a re-snapshot: pass --force too")
    previous = _previous() if (args.force or args.new) else []
    if args.new:
        # A drop is this loop's call, so a new loop carries none (item 172);
        # an open pull request would leave the stack with it.
        still_open = [
            f"#{p.pr}"
            for p in previous
            if p.pr and _pr_state(p.pr) not in {"MERGED", "CLOSED"}
        ]
        if still_open:
            return _fail(
                f"the last loop still has {', '.join(still_open)} open — "
                "`snapshot --force` to keep it in this loop"
            )
        carried, held_out = [], {}
    else:
        carried, held_out = _carried(previous)
    for p in carried:
        p.held = None  # the edit a hold waited on has merged, or will be held again
    candidates, refusals = _scan(loop_branches=frozenset(p.branch for p in previous))
    ordered, stranded = _order(candidates, refusals, carried, frozenset(held_out))
    # A spec whose parent became reviewable joins a re-snapshot unasked, with no
    # spec review (item b-afec7c): name it, and keep it out unless `--add`.
    known = {p.spec_id for p in previous}
    arrived = [p for p in ordered if args.force and known and p.spec_id not in known]
    wanted = {p.spec_id for p in arrived} if args.add == [] else set(args.add or ())
    if unknown := wanted - {p.spec_id for p in arrived}:
        return _fail(f"not new since the last snapshot: {', '.join(sorted(unknown))}")
    added = [p for p in arrived if p.spec_id in wanted]
    left_out = [p for p in arrived if p.spec_id not in wanted]
    ordered = [p for p in ordered if p not in left_out]
    if held_out:
        print(f"edited while its pull request is open ({len(held_out)}):")
        for reason in held_out.values():
            print(f"  {reason}")
        print(
            "  kept in the order at the sha its task ran at, so its pull request "
            "stays in the stack;\n  it will not be re-run until the PR closes or "
            "the edit is reverted"
        )
        for trap in _edit_traps(previous):
            print(f"  {trap}")
        print()
    for verb, specs in (("added", added), ("left out", left_out)):
        if specs:
            print(f"new since the last snapshot, {verb} ({len(specs)}):")
            for p in specs:
                print(f"  {p.spec_id}  {p.title}")
    if left_out:
        print("  `snapshot --force --add SA-NNNN` takes one in; review each spec first")
    if arrived:
        print()
    if not ordered:
        print("nothing to run: no candidate specs")
        for r in refusals:
            print(f"  {r.path.name}: {r.reason}")
        return 1
    _save(ordered)

    print(f"order: {len(ordered)} spec(s), bottom of the stack first\n")
    for i, p in enumerate(ordered, 1):
        dep = f"  depends_on={p.depends_on}" if p.depends_on else ""
        print(
            f"  {i}. {p.spec_id}  priority={p.priority}  risk={p.risk}  "
            f"${p.budget_usd:.2f}{dep}  {p.title}"
        )
    total = sum(p.budget_usd for p in ordered)
    print(
        f"\nspec budgets: ${total:.2f} in total; a cell can overrun its own by up "
        "to one attempt (DESIGN.md §3; 67% on SA-0059)"
    )
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
    roots = [p for p in ordered if not p.depends_on]
    if len(roots) > 1:
        print(
            f"\nnote: {len(roots)} specs declare no depends_on, so their branches are "
            "siblings\n      cut from the default branch; `rebase` would chain the "
            f"{len(roots) - 1} above the bottom one if asked."
        )
    return 0


def _origin_head(branch: str) -> str | None:
    try:
        return _git("rev-parse", f"origin/{branch}")
    except GitError:
        return None


def _next_spec(
    rows: list[OrderRow],
    *,
    again: bool,
    head_of: Callable[[str], str | None] | None = None,
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
        if p.held:
            notes.append(f"held {p.spec_id}: {p.held}")
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
        parents = [by_id[d] for d in p.depends_on if d in by_id]
        names = ", ".join(q.spec_id for q in parents)
        if parents and all(q.pushed_sha for q in parents):
            head_of = head_of or _origin_head
            heads = {q.spec_id: head_of(q.branch) for q in parents}
            unpushed = [q for q in parents if heads[q.spec_id] in (None, q.pushed_sha)]
            if unpushed:
                notes.append(
                    f"{p.spec_id} waits on {unpushed[0].spec_id}'s review commits: "
                    "none are pushed yet"
                )
                continue
            pushed = ", ".join((heads[q.spec_id] or "")[:8] for q in parents)
            notes.append(
                f"{p.spec_id} is cut from {names}, whose review commits are pushed "
                f"({pushed})"
            )
        elif parents:  # an order `record` wrote before it stored `pushed_sha`
            notes.append(
                f"{p.spec_id} is cut from {names}: push "
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
    if any(p.last_state is None for p in pending):
        return 1  # every untouched spec waits on a parent; the note said which
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


def _cell_running(spec_id: str) -> bool:
    """Whether a `saffron cell` for this spec is still alive. Without one, an
    in-flight state is a halt: SA-0087's REBUT ran out of budget and the task
    stayed `REBUTTING` after the process exited (§5.6)."""
    done = subprocess.run(
        ["pgrep", "-f", f"saffron cell .*{spec_id}"], capture_output=True, text=True
    )
    return done.returncode == 0


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
    running, pushed = False, ""
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
        # `queue_lines`, not `tasks_by_spec`: only it carries the spend and the
        # pushed sha, and a task id is unique across repos.
        lines = {row["task_id"]: row for row in ledger.queue_lines()}
        urls = {tid: row["pr_url"] for tid, row in lines.items() if row["pr_url"]}
        chosen = next(
            (row for row in reversed(tasks) if row["task_id"] in urls), tasks[-1]
        )
        state = chosen["state"]
        url = urls.get(chosen["task_id"], "")
        pr = int(url.rstrip("/").rsplit("/", 1)[-1]) if "/pull/" in url else None

        line = lines[chosen["task_id"]]
        spent, budget = line["spent_usd_est"], line["budget_usd"]
        if state in DONE_STATES:
            match.state, match.pr = state, pr
            match.pushed_sha = line["pushed_sha"] or ""
        else:
            # Nothing was decided. Keep a PR number the ledger still carries: a
            # `CHANGES_REQUESTED` spec has one open.
            match.state = None
            match.pr = pr or match.pr
            match.last_state = state
            running = state in IN_FLIGHT_STATES and _cell_running(args.spec_id)
            if not running:
                match.undecided_cells += 1
            pushed = line["pushed_sha"] or ""
    finally:
        ledger.close()

    _save(rows)
    where = f"#{match.pr}" if match.pr else "(no PR)"
    cost = f"  ${spent:.2f} of ${budget:.2f}" if spent is not None and budget else ""
    print(f"{match.spec_id}  {state}  {where}{cost}")
    if match.state is None:
        if running:
            why = "the cell is still running — wait for it to exit, then record again"
        elif state in IN_FLIGHT_STATES:
            branch = f", its branch pushed at {pushed[:12]}" if pushed else ""
            why = (
                f"halted at {state}: the cell has exited and nothing decided the "
                f"task{branch}. The operator's call — raise the spec's ceilings and "
                "re-run, take the branch by hand, or drop it; a child cannot stack "
                "on it (GOTCHAS, Recording)"
            )
        else:
            why = "nothing was decided; `next` moves on to the next untouched spec"
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


# pytest's exit codes: 1 is a failed test; 2-5 are an interrupt, an internal
# error, a usage error and no tests collected, none of which is a verdict.
_PYTEST_NOT_A_VERDICT = {2, 3, 4, 5}
_ERROR_KILL = re.compile(r" - (?!AssertionError)\w+Error\b")
# One space: a captured log line pads its level (`ERROR    root:...`).
_SUMMARY_ROW = re.compile(r"^(FAILED|ERROR) \S")


def cmd_probe(args) -> int:
    """One vacuity probe, applied only if its find text matches exactly once,
    and always restored. A find that misses, or an edit that never lands,
    prints a result that reads like "survived" (run 7, #338)."""
    command = args.run
    if not command:
        return _fail("give the command to run after --")
    target = args.root / args.file
    try:
        original = target.read_bytes()
    except OSError as err:
        return _fail(f"cannot read {target}: {err}")
    text = original.decode()
    count = text.count(args.find)
    if count != 1:
        return _fail(f"--find matches {count} times in {args.file}; a probe needs one")
    target.write_bytes(text.replace(args.find, args.replace).encode())
    try:
        if target.read_bytes() == original:
            return _fail("the replacement left the file unchanged")
        # pytest cuts a summary row at COLUMNS, and with it the error's name.
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "COLUMNS": "10000"}
        try:
            done = subprocess.run(
                command, cwd=args.root, env=env, capture_output=True, text=True
            )
        except OSError as err:
            return _fail(f"cannot run {command[0]}: {err}")
    finally:
        target.write_bytes(original)
    if target.read_bytes() != original:
        return _fail(f"{args.file} was not restored — check it by hand")
    output = (done.stdout + done.stderr).splitlines()
    failed = [line for line in output if _SUMMARY_ROW.match(line)]
    is_pytest = any("pytest" in part for part in command)
    if done.returncode == 0:
        verdict = "survived"
    elif is_pytest and done.returncode in _PYTEST_NOT_A_VERDICT:
        verdict = f"no verdict (pytest exited {done.returncode})"
    elif failed and all(_ERROR_KILL.search(line) for line in failed):
        # A mutant that raises is not one a test caught (REVIEW-PROMPT.md).
        verdict = "killed only by errors, not by an assertion"
    else:
        verdict = "killed"
    print(f"{verdict}: {output[-1] if output else f'exit {done.returncode}'}")
    for line in failed[:5]:
        print(f"  {line}")
    return 0


def cmd_hold(args) -> int:
    """Keep `next` off a spec whose edit is still an open pull request."""
    rows = _load()
    match = next((p for p in rows if p.spec_id == args.spec_id), None)
    if match is None:
        return _fail(f"{args.spec_id} is not in the order")
    if not args.release and not args.why:
        return _fail("say why with --why, or pass --release")
    match.held = None if args.release else args.why
    _save(rows)
    print(f"{match.spec_id}  {'released' if args.release else f'held: {args.why}'}")
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
        elif p.held and p.pending:
            label, extra = "held", f"  ({p.held})"
        else:
            label = p.state or "pending"
            extra = (
                f"  (last {p.last_state}, {p.undecided_cells} undecided cell(s))"
                if p.pending and p.last_state
                else ""
            )
            if p.reviewable and p.pushed_sha:  # item 14: what is left to review
                head = _origin_head(p.branch)
                extra = (
                    f"  reviewed {head[:8]}"
                    if head and head != p.pushed_sha
                    else "  no review commits pushed"
                )
        print(f"  {p.spec_id:<{width}}  {label:<18} {pr:<5}{extra}")
    ready = [p for p in rows if p.reviewable]
    print(f"\n{len(ready)}/{len(rows)} reviewable")
    if edited := [p for p in rows if p.edited_sha]:
        print("\nedited since its task ran, and kept at the sha that ran:")
        for p in edited:
            pr = f"#{p.pr}" if p.pr else "its branch"
            print(
                f"  {p.spec_id}: {pr} stays in the stack; it is not re-run until "
                "the pull request closes or the edit is reverted"
            )
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
    print(
        "\nPACKAGE opens drafts (§5.7); --execute marks each ready once its base reads back."
    )
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
    if mismatched:
        return 1
    # A reviewed stack is ready for the operator; the draft was the cell's.
    unready = [
        p.pr
        for p in order
        if subprocess.run(["gh", "pr", "ready", str(p.pr)], cwd=REPO).returncode
    ]
    if unready:
        return _fail(f"gh pr ready failed for {', '.join(f'#{n}' for n in unready)}")
    print(f"\nmarked ready: {' '.join(f'#{p.pr}' for p in order)}")
    return 0


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
    try:
        ok, messages = _apply_layers(layers)
    except GitError as err:
        ok, messages = False, [str(err)]
    for message in messages:
        print(f"  {message}")
    print(f"\nrecorded SHAs: {record.relative_to(REPO)}")
    if not ok:
        return 1
    print(f"push, with the operator's approval:\n  {push}")
    return 0


def cmd_size(args) -> int:
    from saffron.intake import load_spec

    rows = _load()
    match = next((p for p in rows if p.spec_id == args.spec_id), None)
    if match is None:
        return _fail(f"{args.spec_id} is not in the order")
    if not match.reviewable:
        return _fail(f"{match.spec_id} is not reviewable, so it has no stack to sit in")
    spec, _sha = load_spec(REPO / match.path)
    subprocess.run(["git", "fetch", "-q", "origin"], cwd=REPO)
    upper = f"origin/{match.branch}"
    below = [f"origin/{b}" for b in _bases_below(match.spec_id, rows)]
    try:
        lower = _own_base(upper, below, _trunk())
    except GitError as err:
        return _fail(str(err))
    result = _size(lower, upper, spec.type, spec.touches)
    ask = "" if result.status == "pass" else "; ask the operator (item 40)"
    print(f"{match.spec_id} since {lower[:8]}: {result.summary}{ask}")
    return 0 if result.status == "pass" else 1


class Spend(NamedTuple):
    turns: int
    usd: float


def _cut_off_at_turn_ceiling(attempt) -> bool:
    """`saffron.cell.session.cut_off_at_turn_ceiling`'s rule over a ledger row.
    Both fields, not just the subtype: that file reads `terminal_reason` as the
    primary and keeps the subtype so a result event arriving without one does
    not skip the control in silence."""
    return attempt["terminal_reason"] == "max_turns" or (
        attempt["subtype"] == "error_max_turns"
    )


@dataclass
class PastCell:
    """One past cell's spend by phase, for a spec review's ceilings and size checks."""

    spec_id: str
    spec_type: str
    touches: int
    criteria: int
    started_at: str
    state: str
    budget_usd: float | None
    # The first IMPLEMENTING attempt; a checkpoint re-prompt counts as implement.
    plan: Spend | None
    implement: Spend  # every other IMPLEMENTING attempt
    repair: Spend
    peak_turns: int  # the largest single attempt of any phase; max_turns bounds each
    review_usd: float
    rebut_usd: float
    endings: list[str]  # "<phase> <subtype>" for every attempt that did not succeed
    # Whether the attempt `peak_turns` came from is the one that hit the turn
    # ceiling. `endings` is flat over every attempt and `peak_turns` is a max
    # over every attempt, so the two do not line up: this repo's own fixture
    # peaks at 45 on a REBUTTING attempt that ran out of *budget* while its
    # `error_max_turns` attempt ran 41, and calling 45 a turn floor is false.
    peak_cut_off: bool
    size: str | None  # the last `size` gate summary, verbatim: it names the ceiling


def _known_specs() -> dict[str, Spec]:
    """Every spec by id, live or retired. The ledger's `spec_sha` is not a git
    blob, so a past spec's shape is read from its text as it stands now."""
    from saffron.intake import discover_specs

    found: dict[str, Spec] = {}
    for directory in (SPECS_DIR / "done", SPECS_DIR):
        if not directory.is_dir():  # a repo with nothing retired yet has no `done/`
            continue
        specs, _failures = discover_specs(directory)
        found.update({d.spec.id: d.spec for d in specs})
    return found


def _spec_at(spec_id: str, commit: str, cwd: Path = REPO) -> Spec | None:
    """The spec as it stood at `commit`, live or retired: a blind review's
    header must not show ceilings raised after the version it reviews."""
    from saffron.intake import DisclosedMutantError, parse_spec

    names = _git(
        "ls-tree", "-r", "--name-only", commit, ".saffron/specs", cwd=cwd
    ).splitlines()
    found = [
        n
        for n in names
        if str(Path(n).parent) in (".saffron/specs", ".saffron/specs/done")
        and Path(n).name.startswith(f"{spec_id}-")
    ]
    if not found:
        return None
    if len(found) > 1:
        raise GitError(f"{len(found)} spec files for {spec_id}: {', '.join(found)}")
    try:
        return parse_spec(_git("show", f"{commit}:{found[0]}", cwd=cwd))
    except DisclosedMutantError as exc:
        # A header only needs shape, not queue admission; scheduler._retired_ids
        # credits the same carried spec for the same reason.
        return exc.spec


def _specs_at(commit: str, specs: dict[str, Spec], cwd: Path = REPO) -> dict[str, Spec]:
    """Each of `specs` as it stood at `commit`, so a blind review ranks past cells
    by no text later than its base. Today's stands in where none then parses."""
    from saffron.intake import SpecError

    shapes = {}
    for spec_id, today in specs.items():
        try:
            shapes[spec_id] = _spec_at(spec_id, commit, cwd) or today
        except (GitError, SpecError):
            shapes[spec_id] = today
    return shapes


def _criteria_count(spec: Spec) -> int:
    return len(spec.acceptance) or len(spec.acceptance_criteria)


def _spend(attempts: list, phase: str) -> Spend:
    """Turns and cost summed over `attempts` in `phase`."""
    mine = [a for a in attempts if a["phase"] == phase]
    return Spend(
        sum(a["num_turns"] or 0 for a in mine),
        sum(a["cost_usd_est"] or 0.0 for a in mine),
    )


def _commit_time(commit: str, cwd: Path = REPO) -> str:
    """`commit`'s committer time the way the ledger writes `started_at`:
    UTC, `YYYY-MM-DD HH:MM:SS`, so the two compare as strings."""
    epoch = int(_git("log", "-1", "--format=%ct", commit, cwd=cwd))
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(epoch))


def _past_cells(
    ledger,
    repo_id: int,
    specs: dict[str, Spec],
    *,
    before: str | None = None,
    exclude: str | None = None,
) -> list[PastCell]:
    budgets = {row["task_id"]: row["budget_usd"] for row in ledger.queue_lines()}
    cells = []
    for (spec_id, _sha), rows in ledger.tasks_by_spec(repo_id).items():
        if spec_id == exclude or spec_id not in specs:
            continue
        spec = specs[spec_id]
        for row in rows:
            attempts = ledger.attempts(row["task_id"])
            if not attempts or (
                before is not None and attempts[0]["started_at"] >= before
            ):
                continue
            implementing = [a for a in attempts if a["phase"] == "IMPLEMENTING"]
            checkpoint = implementing[0] if implementing else None
            sizes = [
                r.summary
                for r in ledger.task_results(row["task_id"])
                if r.gate == "size"
            ]
            peak_attempt = max(attempts, key=lambda a: a["num_turns"] or 0)
            cells.append(
                PastCell(
                    spec_id=spec_id,
                    spec_type=spec.type,
                    touches=len(spec.touches),
                    criteria=_criteria_count(spec),
                    started_at=attempts[0]["started_at"],
                    state=row["state"],
                    budget_usd=budgets.get(row["task_id"]),
                    plan=_spend([checkpoint], "IMPLEMENTING")
                    if checkpoint is not None
                    else None,
                    implement=_spend(implementing[1:], "IMPLEMENTING"),
                    repair=_spend(attempts, "REPAIRING"),
                    peak_turns=peak_attempt["num_turns"] or 0,
                    peak_cut_off=_cut_off_at_turn_ceiling(peak_attempt),
                    review_usd=_spend(attempts, "REVIEWING").usd,
                    rebut_usd=_spend(attempts, "REBUTTING").usd,
                    endings=[
                        f"{a['phase']} {a['subtype']}"
                        + (f" ({a['terminal_reason']})" if a["terminal_reason"] else "")
                        for a in attempts
                        # Coalesced rather than the record's bare
                        # `!= "completed"`: `terminal_reason` is NULL on every
                        # clean attempt and on a row never closed, and marking
                        # all 451 of those abnormal is worse than missing one.
                        if a["subtype"] not in (None, "success")
                        or (a["terminal_reason"] or "completed") != "completed"
                    ],
                    size=sizes[-1] if sizes else None,
                )
            )
    return cells


def _cell_line(c: PastCell) -> str:
    plan = f"plan {c.plan.turns}t ${c.plan.usd:.2f}" if c.plan else "plan -"
    budget = f"${c.budget_usd:.2f}" if c.budget_usd is not None else "-"
    ended = f"  ended: {'; '.join(c.endings)}" if c.endings else ""
    size = f"  size: {c.size}" if c.size else ""
    return (
        f"{c.spec_id}  {c.spec_type}  touches={c.touches} criteria={c.criteria}  "
        f"{c.started_at[:10]}  {c.state}  budget {budget}  {plan}  "
        f"implement {c.implement.turns}t ${c.implement.usd:.2f}  "
        f"repair {c.repair.turns}t ${c.repair.usd:.2f}  peak {c.peak_turns}t  "
        f"review ${c.review_usd:.2f}  rebut ${c.rebut_usd:.2f}{size}{ended}"
    )


def _pre_review_total(c: PastCell) -> float:
    """Plan + implement + repair: what a cell spent before REVIEW touched it,
    and so what the budget must have covered before that (item 123)."""
    return (c.plan.usd if c.plan else 0.0) + c.implement.usd + c.repair.usd


def _ceilings_line(target: Spec, rows: list[PastCell]) -> str:
    """`max_turns` against the highest `peak_turns` among `rows`, and
    `budget_usd` against the highest pre-review total among them — the
    comparison a spec review used to redo by eye and get wrong both ways
    (SA-0031, SA-0087@24edb32, and the false blockers on SA-0060, SA-0027)."""
    if not rows:
        return "ceilings: no past cells of this shape to compare against"

    turns_row = max(rows, key=lambda c: c.peak_turns)
    turns_diff = target.max_turns - turns_row.peak_turns
    # Three-way, where the budget half below is two: check 4's blocker is
    # `max_turns` "at or below" the peak but `budget_usd` only "below"
    # (.claude/agents/spec-reviewer.md), so equality is a blocker here and not
    # there — and "above by 0t" reads as headroom at exactly that threshold.
    if turns_diff == 0:
        turns_gap = "level with it"
    else:
        turns_gap = f"{'above' if turns_diff > 0 else 'below'} by {abs(turns_diff)}t"
    cut_off = turns_row.peak_cut_off
    turns_label = "a floor — cut off at its own ceiling" if cut_off else "used"
    turns_part = (
        f"max_turns={target.max_turns} vs {turns_row.spec_id}'s peak "
        f"{turns_row.peak_turns}t ({turns_label}), {turns_gap}"
    )

    budget_row = max(rows, key=_pre_review_total)
    budget_total = _pre_review_total(budget_row)
    budget_diff = target.budget_usd - budget_total
    budget_word = "above" if budget_diff >= 0 else "below"
    budget_part = (
        f"budget_usd={target.budget_usd} vs {budget_row.spec_id}'s pre-review "
        f"total ${budget_total:.2f}, {budget_word} by ${abs(budget_diff):.2f}"
    )

    return f"ceilings: {turns_part}; {budget_part}"


def _select_rows(
    target: Spec, cells: list[PastCell], limit: int = 12
) -> list[PastCell]:
    """Past cells of `target`'s own type, closest in `touches` and criteria
    count first, newest first on a tie, cut at `limit` — the selection
    `history` prints and `check` must judge the same rows as (item 145)."""
    criteria = _criteria_count(target)
    same = [c for c in cells if c.spec_type == target.type]
    same.sort(key=lambda c: c.started_at, reverse=True)
    same.sort(
        key=lambda c: abs(c.touches - len(target.touches)) + abs(c.criteria - criteria)
    )
    return same[:limit]


def _history_lines(target: Spec, cells: list[PastCell], limit: int = 12) -> list[str]:
    """The target's own shape and ceilings, then past cells of its type, the
    closest in `touches` and criteria count first, newest first on a tie, then
    a `ceilings:` line comparing the target's own ceilings with what the
    printed rows show (item 123)."""
    criteria = _criteria_count(target)
    header = (
        f"{target.id}  {target.type}  touches={len(target.touches)} "
        f"criteria={criteria}  max_turns={target.max_turns} "
        f"budget_usd={target.budget_usd}  max_attempts={target.max_attempts}"
    )
    rows = _select_rows(target, cells, limit)
    return [header, *(_cell_line(c) for c in rows), _ceilings_line(target, rows)]


def _turns_blocker(target: Spec, rows: list[PastCell]) -> str | None:
    """Check 4's turns rule: a blocker when `max_turns` is at or below the
    worst peak among `rows` — equality included."""
    row = max(rows, key=lambda c: c.peak_turns)
    if target.max_turns <= row.peak_turns:
        return (
            f"max_turns={target.max_turns} at or below {row.spec_id}'s peak "
            f"{row.peak_turns}t"
        )
    return None


def _budget_blocker(target: Spec, rows: list[PastCell]) -> str | None:
    """Check 4's budget rule: a blocker only when `budget_usd` is strictly
    below the worst pre-review total among `rows` — equality is headroom."""
    row = max(rows, key=_pre_review_total)
    total = _pre_review_total(row)
    if target.budget_usd < total:
        return (
            f"budget_usd={target.budget_usd} below {row.spec_id}'s pre-review "
            f"total ${total:.2f}"
        )
    return None


def _review_rebut_concern(target: Spec, rows: list[PastCell]) -> str | None:
    """What's left of `budget_usd` after the same worst-case pre-review total
    `_budget_blocker` names, against one row's worst REVIEW+REBUT sum — not
    the sum of two different rows' maxima, and not a mean of the rows'."""
    remainder = target.budget_usd - _pre_review_total(max(rows, key=_pre_review_total))
    worst = max(rows, key=lambda c: c.review_usd + c.rebut_usd)
    worst_cost = worst.review_usd + worst.rebut_usd
    if remainder < worst_cost:
        return (
            f"${remainder:.2f} left after the pre-review total may not cover "
            f"{worst.spec_id}'s review+rebut ${worst_cost:.2f}"
        )
    return None


def cmd_check(args) -> int:
    """Judge a spec's ceilings against cells of its own shape, before a cell
    runs — the arithmetic `_ceilings_line` renders, turned into a verdict."""
    specs = _known_specs()
    target = specs.get(args.spec_id)
    if target is None:
        return _fail(f"no spec declares {args.spec_id}")
    ledger, repo_id, _url = _ledger_and_repo()
    try:
        if repo_id is None:
            return _fail("this repo has no ledger row yet")
        cells = _past_cells(ledger, repo_id, specs)
    finally:
        ledger.close()
    rows = _select_rows(target, cells)
    print(_ceilings_line(target, rows))
    if not rows:
        return 0
    blockers = [
        b for b in (_turns_blocker(target, rows), _budget_blocker(target, rows)) if b
    ]
    for blocker in blockers:
        print(f"blocker: {blocker}")
    concern = _review_rebut_concern(target, rows)
    if concern:
        print(f"concern: {concern}")
    if not blockers and not concern:
        print("check: ceilings clear this shape's history")
    return 1 if blockers else 0


def cmd_history(args) -> int:
    """What cells of this spec's shape spent before, for a spec review.
    `--before` is blind: every spec as it stood then, and none of this one's
    cells; live use shows them, the best evidence for a re-queued spec."""
    from saffron.intake import SpecError

    specs = _known_specs()
    before = None
    if args.before:
        try:
            target = _spec_at(args.spec_id, args.before)
            before = _commit_time(args.before)
        except (GitError, SpecError) as err:
            return _fail(f"--before {args.before}: {err}")
        specs = _specs_at(args.before, specs)
    else:
        target = specs.get(args.spec_id)
    if target is None:
        at = f" at {args.before}" if args.before else ""
        return _fail(f"no spec declares {args.spec_id}{at}")
    ledger, repo_id, _url = _ledger_and_repo()
    try:
        if repo_id is None:
            return _fail("this repo has no ledger row yet")
        cells = _past_cells(
            ledger,
            repo_id,
            specs,
            before=before,
            exclude=args.spec_id if args.before else None,
        )
    finally:
        ledger.close()
    print("\n".join(_history_lines(target, cells, args.limit)))
    return 0


def cmd_pattern(_args) -> int:
    print(watch_pattern())
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("snapshot", help="write the loop's order, before any PR exists")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument(
        "--force",
        action="store_true",
        help="re-snapshot this loop, keeping its outcomes",
    )
    mode.add_argument(
        "--new",
        action="store_true",
        help="start another loop once every pull request of the last has closed",
    )
    p.add_argument(
        "--add",
        nargs="*",
        metavar="SA-NNNN",
        help="with --force, take in specs new since the last snapshot: those named, "
        "or every one",
    )
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

    p = sub.add_parser("hold", help="keep next off a spec whose edit is still open")
    p.add_argument("spec_id")
    p.add_argument("--why", help="the pull request the edit is waiting in")
    p.add_argument("--release", action="store_true", help="let next name it again")
    p.set_defaults(func=cmd_hold)

    p = sub.add_parser(
        "probe",
        help="apply one find/replace, run a command, restore",
        usage="driver.py probe file --find F --replace R [--root DIR] -- command ...",
    )
    p.add_argument("file", help="the file to edit, relative to --root")
    p.add_argument("--find", required=True)
    p.add_argument("--replace", required=True)
    p.add_argument("--root", type=Path, default=Path.cwd(), help="default: the cwd")
    p.set_defaults(func=cmd_probe, run=[])

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

    p = sub.add_parser("size", help="a branch's changed lines against its ceiling")
    p.add_argument("spec_id")
    p.set_defaults(func=cmd_size)

    p = sub.add_parser("history", help="what cells of this spec's shape spent before")
    p.add_argument("spec_id")
    p.add_argument("--before", help="only cells that started before this commit")
    p.add_argument("--limit", type=int, default=12)
    p.set_defaults(func=cmd_history)

    p = sub.add_parser(
        "check", help="judge a spec's ceilings against cells of its shape"
    )
    p.add_argument("spec_id")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("pattern", help="print the Monitor's grep -E pattern")
    p.set_defaults(func=cmd_pattern)

    # Split by hand: 3.12.3's argparse (CI's) left everything after `--`
    # unrecognized once a `nargs="*"` positional had matched empty.
    argv = sys.argv[1:]
    cut = argv.index("--") if "--" in argv else len(argv)
    args = parser.parse_args(argv[:cut])
    if cut < len(argv):
        if args.command != "probe":
            parser.error("only probe takes a command after --")
        args.run = argv[cut + 1 :]
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
