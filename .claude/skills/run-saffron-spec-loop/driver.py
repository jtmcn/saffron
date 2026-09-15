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
from typing import TYPE_CHECKING

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
    kept, held = [], {}
    for p in previous:
        if not (p.state or p.dropped or p.last_state):
            continue
        reasons = _stale_reasons(p)
        if not reasons:
            kept.append(p)
        elif p.pr and _pr_state(p.pr) not in {"MERGED", "CLOSED"}:
            held[p.spec_id] = f"{'; '.join(reasons)}, and #{p.pr} is still open"
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
    return [p.branch for p in order[: ids.index(spec_id)]] if spec_id in ids else []


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
    if ORDER.is_file() and not args.force:
        return _fail(f"{ORDER.relative_to(REPO)} exists — pass --force to re-snapshot")
    previous = _previous() if args.force else []
    carried, held_out = _carried(previous)
    candidates, refusals = _scan(loop_branches=frozenset(p.branch for p in previous))
    ordered, stranded = _order(candidates, refusals, carried, frozenset(held_out))
    if held_out:
        print(f"held out of the order ({len(held_out)}):")
        for reason in held_out.values():
            print(f"  {reason}")
        print("  close the PR to run the edited spec, or revert the edit to keep it\n")
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


@dataclass
class PastCell:
    """One past cell's spend by phase, for the reviewer's ceilings and size checks."""

    spec_id: str
    spec_type: str
    touches: int
    criteria: int
    started_at: str
    state: str
    budget_usd: float | None
    plan: (
        tuple[int, float] | None
    )  # the first IMPLEMENTING attempt: the plan checkpoint
    implement: tuple[int, float]  # every other IMPLEMENTING and REPAIRING attempt
    peak_turns: int  # the largest single attempt of any phase; max_turns bounds each
    review_usd: float
    rebut_usd: float
    endings: list[str]  # "<phase> <subtype>" for every attempt that did not succeed
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


def _criteria_count(spec: Spec) -> int:
    return len(spec.acceptance) or len(spec.acceptance_criteria)


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
            implementing = [
                a for a in attempts if a["phase"] in ("IMPLEMENTING", "REPAIRING")
            ]
            first = implementing[0] if implementing else None
            rest = implementing[1:]
            sizes = [
                r.summary
                for r in ledger.task_results(row["task_id"])
                if r.gate == "size"
            ]
            cells.append(
                PastCell(
                    spec_id=spec_id,
                    spec_type=spec.type,
                    touches=len(spec.touches),
                    criteria=_criteria_count(spec),
                    started_at=attempts[0]["started_at"],
                    state=row["state"],
                    budget_usd=budgets.get(row["task_id"]),
                    plan=(first["num_turns"] or 0, first["cost_usd_est"] or 0.0)
                    if first is not None
                    else None,
                    implement=(
                        sum(a["num_turns"] or 0 for a in rest),
                        sum(a["cost_usd_est"] or 0.0 for a in rest),
                    ),
                    peak_turns=max(a["num_turns"] or 0 for a in attempts),
                    review_usd=sum(
                        a["cost_usd_est"] or 0.0
                        for a in attempts
                        if a["phase"] == "REVIEWING"
                    ),
                    rebut_usd=sum(
                        a["cost_usd_est"] or 0.0
                        for a in attempts
                        if a["phase"] == "REBUTTING"
                    ),
                    endings=[
                        f"{a['phase']} {a['subtype']}"
                        + (f" ({a['terminal_reason']})" if a["terminal_reason"] else "")
                        for a in attempts
                        if a["subtype"] not in (None, "success")
                    ],
                    size=sizes[-1] if sizes else None,
                )
            )
    return cells


def _cell_line(c: PastCell) -> str:
    plan = f"plan {c.plan[0]}t ${c.plan[1]:.2f}" if c.plan else "plan -"
    budget = f"${c.budget_usd:.2f}" if c.budget_usd is not None else "-"
    ended = f"  ended: {'; '.join(c.endings)}" if c.endings else ""
    size = f"  size: {c.size}" if c.size else ""
    return (
        f"{c.spec_id}  {c.spec_type}  touches={c.touches} criteria={c.criteria}  "
        f"{c.started_at[:10]}  {c.state}  budget {budget}  {plan}  "
        f"implement {c.implement[0]}t ${c.implement[1]:.2f}  peak {c.peak_turns}t  "
        f"review ${c.review_usd:.2f}  rebut ${c.rebut_usd:.2f}{size}{ended}"
    )


def _history_lines(target: Spec, cells: list[PastCell], limit: int = 12) -> list[str]:
    """The target's own shape and ceilings, then past cells of its type, the
    closest in `touches` and criteria count first, newest first on a tie."""
    criteria = _criteria_count(target)
    header = (
        f"{target.id}  {target.type}  touches={len(target.touches)} "
        f"criteria={criteria}  max_turns={target.max_turns} "
        f"budget_usd={target.budget_usd}  max_attempts={target.max_attempts}"
    )
    same = [c for c in cells if c.spec_type == target.type]
    same.sort(key=lambda c: c.started_at, reverse=True)
    same.sort(
        key=lambda c: abs(c.touches - len(target.touches)) + abs(c.criteria - criteria)
    )
    return [header, *(_cell_line(c) for c in same[:limit])]


def cmd_history(args) -> int:
    """What cells of this spec's shape spent before, for the spec reviewer.
    `--before` is a blind run: the spec as it stood then, and none of its own
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

    p = sub.add_parser("size", help="a branch's changed lines against its ceiling")
    p.add_argument("spec_id")
    p.set_defaults(func=cmd_size)

    p = sub.add_parser("history", help="what cells of this spec's shape spent before")
    p.add_argument("spec_id")
    p.add_argument("--before", help="only cells that started before this commit")
    p.add_argument("--limit", type=int, default=12)
    p.set_defaults(func=cmd_history)

    p = sub.add_parser("pattern", help="print the Monitor's grep -E pattern")
    p.set_defaults(func=cmd_pattern)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
