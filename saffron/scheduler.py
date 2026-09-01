"""The queue scan — which specs on disk are worth running tonight, and in
what order (DESIGN.md §4.2.1).

This is the second and third of `SA-0009`'s split. `SA-0015` built the
`spec_sha`-keyed done/re-queue filter and the ordering, refusing only a spec
`discover_specs` could not parse. `SA-0016` (here) adds the other four of
§4.2.1's six refusals: an open pull request from another task already
targeting this spec, a `touches` overlap with an open pull request's changed
files, an acceptance criterion naming a path no `touches` pattern matches,
and a `depends_on` no `MERGED` task satisfies. That is five of the six refusals gate 0
describes — the sixth, a repo that failed preflight, is a batch-level check
outside `build_queue`'s job.

`SA-0023` adds a seventh, beyond §4.2.1's own six: `protected_touch_refusal`
refuses a spec whose declared `touches` collides with a literal entry in the
repo's `policy.yaml` `protected` list. Measured on `SA-0021` (task 18):
run as a cell, that collision was discovered by `validate_plan` after a
mirror fetch, an image build and one model turn — $0.82 to learn what both
declarations already said before any of that started. It is the cheapest
refusal here, needing no ledger and no `gh`, so `_refuse` checks it first.
`build_queue` never reads `policy.yaml` itself — the caller already holds the
export its specs come from, and hands the `protected` list in.

`SA-0027` adds an eighth, and it belongs beside the fifth
(`_unmatched_criterion_path`): both are the same defect — a path an
acceptance criterion or a `saffron:retired-by` marker names that no
`touches` pattern reaches — read from two different sources. A guard
asserting "`SA-0026` will retire this" in a file `SA-0026`'s `touches` did
not cover was measured twice in one run (docs/BACKLOG.md item 35) and fixed
by hand both times; `retirement_refusal` reads that fact from the repository
rather than the spec's own prose, from `mirror.retirement_markers` handed in
by the caller, the same shape `protected` already takes.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from saffron.gates.core.scope import matches
from saffron.intake import DiscoveryFailure, Spec, discover_specs
from saffron.ledger import Ledger

# Same shape `saffron/phases/package.py` already uses for the same reason —
# a `gh` call the host makes, injectable so a test never reaches the network
# or whoever `gh` happens to be logged in as. Not imported from there: that
# module is forbidden to this spec, so the shape is copied, not shared.
GhRunner = Callable[[list[str]], subprocess.CompletedProcess[str]]


def run_gh(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, capture_output=True, text=True, check=False)


# A spec is queued unless a task at *this* spec_sha is in one of these states
# — done with it, in the sense that running it again learns nothing new
# (§4.2.1). Keyed on spec_sha, not spec_id: an edited spec (a new spec_sha)
# is unaffected by a stale task's disposition.
DONE_STATES = frozenset(
    {
        "READY_FOR_REVIEW",
        "APPROVED",
        "MERGE_TRAIN",
        "MERGED",
        "MERGE_FAILED",
        "REJECTED",
        "EXHAUSTED",
        "NOT_IMPLEMENTED",
        "PLAN_REJECTED",
        "SCOPE_REVIEW",
    }
)

# What always satisfies a dependency, independent of stacking: merging is
# permanent, so this is read across every `spec_sha` — a parent's spec text
# moving afterwards does not un-merge its code. §4.2's other admission,
# `DEPENDENCY_WAITING_STATES` below, used to be narrower than §4.2's own rule
# until a dependent had something to stack on; `SA-0026` resolves it, so both
# admissions are live now.
DEPENDENCY_MERGED = "MERGED"

# Reached review and not landed, and §4.2 admits it outright: a dependent
# stacks on this parent's branch instead of cutting from `base_sha`
# (`CellSpec.stacked_on`, resolved by `cli._resolve_stacked_on`, `SA-0026`),
# so these three no longer refuse — only `DEPENDENCY_DEAD_STATES` and the
# fallthrough below still do.
DEPENDENCY_WAITING_STATES = frozenset({"READY_FOR_REVIEW", "APPROVED", "MERGE_TRAIN"})

# Will not merge as it stands. Read only at the parent's *current* `spec_sha`:
# a dead row under a superseded sha is a fact about text that has since been
# edited, and says nothing about the spec on disk (measured, SA-0020's first
# attempt, 2026-08-30).
DEPENDENCY_DEAD_STATES = frozenset({"REJECTED", "EXHAUSTED"})


# The other side of the same rule: re-queue when nothing was learned about
# the spec. A spec whose task is in one of these states is queued again,
# resuming that same task_id rather than minting a new one.
REQUEUE_STATES = frozenset(
    {
        "CHANGES_REQUESTED",
        "RATE_LIMITED",
        "GATE_ERROR",
        "PREFLIGHT_FAILED",
        "ORPHANED",
    }
)


@dataclass(frozen=True)
class Candidate:
    """One spec worth running tonight.

    `task_id` is `None` when there is no existing task to resume — either
    none was ever created at this `spec_sha`, or every one that exists is in
    an in-flight state. `SA-0019` ended the deferral this sentence used to
    record: `reconcile` stamps `ORPHANED`, but only when a caller asserts
    §4.2.1's batch-scan premise, and neither `queue` nor `reconcile` is a batch
    scan — so a corpse still reaches this function unstamped. It is set only
    when a task at this `spec_sha` is in a `REQUEUE_STATES` state, so the resumed
    work reattaches to the row it was sent back to fix rather than a fresh
    one gate 0 (`SA-0016`) would refuse on its own PR.
    """

    path: Path
    spec: Spec
    spec_sha: str
    task_id: int | None


@dataclass(frozen=True)
class Refusal:
    """One path refused before any cell starts — five of §4.2.1's six
    reasons: a parse failure (`SA-0015`), an open pull request from another
    task, a `touches` overlap with an open pull request's files, acceptance
    criteria naming a path outside `touches`, and a `depends_on` the ledger
    does not show merged (`SA-0016`, all four here). The sixth, a repo that failed preflight, is a
    batch-level check outside `build_queue`.

    A parse failure also reaches here from `specs/done/`, where the path is
    not a candidate at all: that file is refused *credit* rather than refused
    a cell. It is still a refusal row, because the alternative is a dependent
    refused for a parent whose spec is sitting right where the operator put
    it, with nothing anywhere saying why."""

    path: Path
    reason: str


# A task's branch is always this, keyed on the spec rather than the task
# (`cli.py`'s `_run_cell`) — which is exactly why refusal has to be keyed on
# `task_id` instead: a re-queued task's own still-open PR must not refuse it.
def _branch(spec_id: str) -> str:
    return f"saffron/{spec_id}"


def _open_prs(repo_slug: str, gh: GhRunner) -> list[dict]:
    """Every open pull request in `repo_slug`, or `[]` on anything that keeps
    this from being a trustworthy answer.

    Best-effort, deliberately: this is the cheapest gate in the system
    (§4.2), not the one that owns GitHub's ground truth. A `gh` that fails or
    prints something unparseable is treated the same as "nothing found" —
    the auth check that would turn a broken `gh` into a hard stop belongs to
    preflight (§4.2.1), not here.

    Elements are filtered, not just the top level. `[1, 2]` and a `files` of
    `null` are both valid JSON that reach `.get` and raise mid-scan, and
    §4.2.1 gives a refusal defined handling where an exception has none — a
    `gh` whose output shape moves would take the whole night's scan with it.
    """
    # ponytail: `gh pr list` orders newest first, so past 100 it is the oldest
    # open pull requests that fall out of both GitHub-backed refusals — and a
    # stale long-lived PR is the kind a refusal most wants to see.
    done = gh(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            repo_slug,
            "--state",
            "open",
            "--json",
            "number,headRefName,url,files",
            "--limit",
            "100",
        ]
    )
    if done.returncode != 0:
        return []
    try:
        parsed = json.loads(done.stdout)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [pr for pr in parsed if isinstance(pr, dict)]


_BACKTICKED = re.compile(r"`([^`\n]+)`")
# `ledger.py:225`, `ledger.py:225-233` and an editor's `ledger.py:225:9` are
# citations of a path, not paths. Repeated, or `:225:9` strips to `:225`.
_LINE_SUFFIX = re.compile(r"(?::\d+(?:-\d+)?)+$")
_GLOB_CHARS = frozenset("*?[")


def _criteria_texts(spec: Spec) -> list[str]:
    """The criteria as prose, the same selection `report/pr_body.py` makes:
    `acceptance:` when the spec declares it, the markdown checklist
    otherwise — `parse_spec` refuses both at once, so this is never a merge
    of two lists, only a choice between them."""
    return [c.claim for c in spec.acceptance] or spec.acceptance_criteria


def _path_tokens(text: str) -> list[str]:
    """The repo-relative path tokens named in one criterion's prose.

    Backtick-quoted spans only, split on whitespace so a span like
    `` `pytest tests/test_scheduler.py -k refusal` `` yields its path word
    rather than failing to match as one string with a command name stuck to
    the front of it.

    Restricted to words carrying a `/` and not ending in one. A bare
    `word.ext` is *not* enough: this repo's own specs backtick bare
    filenames in prose without meaning to declare a touches requirement —
    `SA-0008`'s own acceptance criteria say `` `rebut.py` `` while its
    `touches` is `saffron/phases/rebut.py`, and
    `scope.matches("rebut.py", "saffron/phases/rebut.py")` is `False`.
    Flagging every bare mention would refuse a spec that is not broken. A
    token is only "repo-relative" once it says which directory it is
    relative to.

    A directory mention (`` `saffron/` ``) is *not* enough either, for the
    same reason: `SA-0001`'s own criteria say "no file under `` `saffron/` ``
    is changed" — a constraint on the diff, not a path the diff must reach —
    and `touches` names files and globs, never a bare directory to disprove.

    A trailing `:123` is stripped: this repo cites files as `path.py:123`
    throughout its prose, and `scope.matches` compares whole strings, so the
    line number would make every citation unmatchable against a `touches`
    entry that in fact covers it.

    A token carrying a glob metacharacter is dropped rather than checked.
    `SA-0011`'s criteria name `` `tests/fixtures/*.md` `` to say the fixture
    is *not* a file — and a pattern is not a path `scope.matches` can answer
    for, since it takes a concrete path on the left.

    ponytail: dropped unconditionally, so a criterion naming a whole tree it
    will not touch (`` `saffron/report/**` ``) is ignored rather than refused.
    """
    tokens = []
    for span in _BACKTICKED.findall(text):
        for word in span.split():
            word = _LINE_SUFFIX.sub("", word)
            if "/" not in word or word.endswith("/"):
                continue
            if _GLOB_CHARS.intersection(word):
                continue
            tokens.append(word)
    return tokens


def _unmatched_criterion_path(spec: Spec) -> str | None:
    """The first path token an acceptance criterion names that no `touches`
    pattern matches, or `None`.

    Skipped when `touches` is empty — the documented shape for a bug
    awaiting DIAGNOSE (§5.2); every criterion names a path outside an empty
    list, so the unguarded form would refuse the entire bug class. Matched
    with `scope.matches`, the same function `scope`, `integrity` and `size`
    all reuse, so "declared" means one thing in every gate — never a second,
    more permissive rule invented here.

    A token the spec's own `forbidden` covers is a citation, not a target —
    `SA-0016`'s own criteria name `saffron/phases/package.py` for a shape to
    copy while forbidding that directory, so the unguarded form refused this
    very spec.

    ponytail: a spec that genuinely needs a forbidden path now ends
    `EXHAUSTED` instead — two attempts, since `session.py`'s no-progress rule
    catches a `scope` failure that repeats with the same identity, and up to
    `max_attempts` only if the repair turns keep moving the failure set. A
    whole task either way, not one attempt. Measured, the trade is right (two
    of seventeen falsely refused, and a false refusal costs a night).
    """
    if not spec.touches:
        return None
    for text in _criteria_texts(spec):
        for token in _path_tokens(text):
            if any(matches(token, pattern) for pattern in spec.forbidden):
                continue
            if not any(matches(token, pattern) for pattern in spec.touches):
                return token
    return None


def protected_touch_refusal(touches: list[str], protected: Sequence[str]) -> str | None:
    """Why this spec's own `touches` collides with the repo's global deny
    list, or `None`.

    Matched with `scope.matches`, the same glob every other `touches`
    comparison in this module uses (`_unmatched_criterion_path`, the
    open-pull-request overlap in `_refuse`) — a string compare here would
    repeat `SA-0016`'s fifth refusal's own mistake, where a criterion naming a
    nested file string-compared to no match against a `**` pattern that
    plainly covered it. `matches(entry, pattern)`, not the reverse: `entry` is
    a concrete path, `pattern` is `touches`' own glob, and `scope.matches`
    only interprets glob syntax on its right-hand side.

    ponytail: only a *literal* `protected` entry is decided here. An entry
    that is itself a glob (`.saffron/**`) would need `matches` to answer
    whether two patterns can ever intersect, which needs the file list at
    `base_sha` — neither the scan nor the attended run has that before a cell
    starts. This repo's own `policy.yaml` marks three of its four `protected`
    entries as literal paths, and a literal one is what `SA-0021` hit. An
    entry left undecided here still meets `validate_plan`'s own
    protected-path rejection once a plan names a concrete file — the backstop
    this refusal does not replace, only gets in front of.
    """
    for entry in protected:
        if _GLOB_CHARS.intersection(entry):
            continue
        if any(matches(entry, pattern) for pattern in touches):
            return (
                f"touches names {entry!r}, which policy.yaml's protected list "
                "denies for every spec in this repo — not this spec's own "
                "forbidden list"
            )
    return None


def retirement_refusal(spec: Spec, markers: Sequence[tuple[str, str]]) -> str | None:
    """Why one of this spec's own `saffron:retired-by` markers cannot be
    reached by it, or `None`.

    `markers` is every `(path, spec_id)` pair `mirror.retirement_markers`
    found at `base_sha` — the whole repository's, not this spec's own. A
    marker naming a different spec id is not this candidate's problem and is
    skipped outright; `_dangling_marker_refusals` is where an id nothing
    declares gets its own line.

    Matched with `scope.matches`, the same function `scope`, `integrity`,
    `size` and `_unmatched_criterion_path` all use — "declared" means one
    thing in every gate, never a second and more permissive rule invented
    here. `forbidden` is checked first and named differently from `touches`:
    a spec that may not touch the file at all is a different mistake from
    one whose `touches` merely does not reach it, and the two are fixed by an
    operator in different ways.

    The `touches` half is skipped when `spec.touches` is empty —
    `_unmatched_criterion_path`'s own guard: empty is the documented shape
    for a bug awaiting DIAGNOSE (§5.2), and every marker reads as unreached
    against it, which would refuse the whole bug class before the one phase
    that could ever populate `touches` gets to run. `forbidden` is not
    skipped alongside it — a bug spec can declare it before `touches`, and a
    file it may never touch is a fact DIAGNOSE cannot change.
    """
    for path, marker_spec_id in markers:
        if marker_spec_id != spec.id:
            continue
        if any(matches(path, pattern) for pattern in spec.forbidden):
            return (
                f"{path} asserts saffron:retired-by {spec.id}, but this "
                f"spec's own forbidden list denies it: "
                f"{', '.join(spec.forbidden)} — it may not touch that file at "
                "all, a different mistake from touches not reaching it"
            )
        if spec.touches and not any(matches(path, pattern) for pattern in spec.touches):
            return (
                f"{path} asserts saffron:retired-by {spec.id}, but no "
                f"touches pattern reaches it: {', '.join(spec.touches)}"
            )
    return None


def _dangling_marker_refusals(
    markers: Sequence[tuple[str, str]],
    known_ids: frozenset[str],
    unreadable: int = 0,
) -> list[Refusal]:
    """One `Refusal` per marker naming a spec id nothing in this directory —
    live or retired to `done/` — declares, SA-0024's `done/` rule applied to
    this class of dangling reference instead of a `depends_on`.

    Not a candidate's own refusal: no spec here owns a marker naming an id
    that never existed, or one that shipped and was retired under a
    different id than the one still written in the comment. Silence would be
    the alternative, and silence is exactly what this whole spec exists to
    end.

    `unreadable` is how many spec files — live or in `done/` — did not parse,
    and so declare no id at all. `known_ids` is built from the ones that did,
    so a marker naming an id declared *only* by an unparseable file lands here
    and would otherwise be called dangling, which is a claim about a file this
    scan never read. `_dependency_refusal` qualifies the identical case rather
    than asserting past it (§4.2.1): every branch names the state it read.
    """
    blind = ""
    if unreadable:
        plural = "s" if unreadable > 1 else ""
        blind = (
            f", and {unreadable} spec file{plural} here did not parse, so it "
            "declares no id either way"
        )
    return [
        Refusal(
            path=Path(path),
            reason=(
                f"saffron:retired-by {spec_id} at {path}, but no spec in "
                f"this directory or {RETIRED_DIRNAME}/ declares {spec_id} — "
                f"a dangling reference{blind}"
            ),
        )
        for path, spec_id in markers
        if spec_id not in known_ids
    ]


RETIRED_DIRNAME = "done"


def _retired_ids(directory: Path) -> tuple[frozenset[str], list[DiscoveryFailure]]:
    """Spec ids the operator has retired to `specs/done/` as shipped.

    That directory means one thing (`.saffron/specs/done/README.md`): the
    spec's work is in the default branch. It is the same fact `MERGED`
    establishes, and the only one this gate needs — a child is cut from that
    branch, not stacked on its parent (§4.2). The ledger cannot always state
    it: only a cell writes a task, so work done by hand leaves no row at all.

    Read from frontmatter, never the filename — the id is declared, and a
    file renamed on retirement would otherwise credit the wrong spec. A
    retired spec that no longer parses is not credited: the refusal stands,
    which is the direction that cannot admit a child whose parent is absent.

    Its failures come back with the ids for that reason. Silently discarded,
    an unparseable file here produces a refusal that contradicts the
    filesystem — the child is told its parent is "not retired to `done/` as
    shipped" while the spec sits in `done/` — and §4.2.1's rule is that every
    branch names the state it actually read. `README.md` is not one of them:
    the directory's own documentation is a resident, not a broken spec.
    """
    retired = directory / RETIRED_DIRNAME
    if not retired.is_dir():
        return frozenset(), []
    # `discover_specs` globs non-recursively, so this reads `done/` alone and
    # cannot turn it into a second scan directory.
    shipped, unparseable = discover_specs(retired)
    # `README.md` is a permanent resident, not a spec that stopped parsing —
    # it is the file this directory's meaning is written in.
    stopped = [f for f in unparseable if f.path.name != "README.md"]
    return frozenset(discovered.spec.id for discovered in shipped), stopped


def _dependency_refusal(
    dep: str,
    *,
    merged_anywhere: frozenset[str],
    states_oldest_first: dict[str, list[str]],
    retired: frozenset[str],
    unreadable_retired: int,
) -> str | None:
    """Why `dep` does not satisfy a dependency yet, or `None` if it does.

    `states_oldest_first` maps a spec id to the states of its tasks *at the
    sha that spec has on disk now*, oldest first — `tasks_by_spec` orders by
    `task_id`, so `[-1]` is the newest. A spec id absent from it was not in
    the scanned directory at all, which is a different fact from having no
    task, and the two get different reasons.

    Every branch names the state it actually read. The old refusal said
    "depends_on is not scheduled" about a spec whose state it never looked up,
    which reads as a verdict on the parent and sends an operator to investigate
    a spec with nothing wrong with it (§4.2.1).
    """
    if dep in merged_anywhere:
        return None

    # The operator's own assertion, where the ledger has no row to make it.
    if dep in retired:
        return None

    if dep not in states_oldest_first:
        # Not "no task at its current spec_sha" — it has no spec_sha here at
        # all. `discover_specs` globs `*.md` non-recursively, so a parent
        # retired to `specs/done/`, or an id that never existed, lands here.
        # Saying it had not run would name a check this scan cannot perform.
        # A file in `done/` that does not parse declares no id, so this
        # branch is reachable with the parent sitting in `done/`.
        blind = ""
        if unreadable_retired:
            plural = "s" if unreadable_retired > 1 else ""
            blind = (
                f" — and {unreadable_retired} file{plural} in "
                f"{RETIRED_DIRNAME}/ could not be read as a spec, so it "
                "declares no id to credit"
            )
        return (
            f"depends_on {dep} is not among the specs in this directory, not "
            f"retired to {RETIRED_DIRNAME}/ as shipped, and no task in the "
            f"ledger says it merged{blind}"
        )

    states = states_oldest_first[dep]
    if not states:
        return (
            f"depends_on {dep} has no task at its current spec_sha, so nothing "
            "says it merged: it has not run, or not since it was last edited"
        )

    # Waiting outranks dead whatever the row order: a live task at
    # `READY_FOR_REVIEW` may still land, and a sibling row that did not is not
    # a fact about the one that might — so any row still waiting satisfies
    # the dependency, not just the newest row overall. `cli._resolve_stacked_on`
    # (`SA-0026`) is what turns "satisfies" into a real `CellSpec.stacked_on`;
    # this function only decides whether the dependent may run at all.
    if any(state in DEPENDENCY_WAITING_STATES for state in states):
        return None

    dead = [s for s in states if s in DEPENDENCY_DEAD_STATES]
    if dead:
        return (
            f"depends_on {dep} is {dead[-1]}, which will not merge as it stands "
            "— a different fact about the night from a parent not yet run"
        )

    return f"depends_on {dep} is {states[-1]}, which is not {DEPENDENCY_MERGED}"


def _refuse(
    candidate: Candidate,
    *,
    open_prs: list[dict],
    merged_anywhere: frozenset[str],
    states_at_current_sha: dict[str, list[str]],
    retired: frozenset[str],
    unreadable_retired: int,
    protected: Sequence[str],
    markers: Sequence[tuple[str, str]],
) -> str | None:
    """The first of §4.2.1's remaining refusals this candidate earns, or
    `None`. Order matches the acceptance criteria's own listing — except the
    `SA-0023` check below, which runs first because it is the cheapest: no
    `gh`, no ledger, nothing but the spec and the policy already in hand."""
    if (
        reason := protected_touch_refusal(candidate.spec.touches, protected)
    ) is not None:
        return reason

    own_branch = _branch(candidate.spec.id)
    same_spec_pr = next(
        (pr for pr in open_prs if pr.get("headRefName") == own_branch), None
    )
    # *Another* task: a candidate resuming its own `task_id` keeps its open PR,
    # or the refusal would refuse the re-queue it exists to resume (§4.2.1).
    # ponytail: "is a resume" stands in for "owns that PR" — the branch is
    # spec-keyed, so a second re-queueing task at this sha inherits the first
    # one's PR rather than being refused on it. Recovering the owner needs the
    # ledger, which this function does not take.
    if same_spec_pr is not None and candidate.task_id is None:
        # `or`, not a `.get` default: `_open_prs` filters shapes, not fields,
        # so a present-but-null url would otherwise print "None" at an operator.
        url = same_spec_pr.get("url") or own_branch
        return (
            f"an open pull request from another task already targets this spec: {url}"
        )

    # K=1, the same first entry `cli._resolve_stacked_on` stacks on: a child
    # cut from its parent's branch starts with the parent's changes already in
    # its tree, so an overlap with the parent's own pull request is what
    # stacking is *for*. Left in, this refusal shadows the dependency
    # admission below entirely — a parent at `READY_FOR_REVIEW` has an open
    # pull request by definition, and almost every spec here touches
    # `docs/BACKLOG.md` (`SA-0026`).
    parent_branch = (
        _branch(candidate.spec.depends_on[0]) if candidate.spec.depends_on else None
    )
    for pr in open_prs:
        if pr.get("headRefName") in (own_branch, parent_branch):
            continue
        # `or []`, not a `.get` default: a `files` of `null` stores None.
        changed = [
            f.get("path", "") for f in (pr.get("files") or []) if isinstance(f, dict)
        ]
        overlap = [
            path
            for path in changed
            if any(matches(path, pattern) for pattern in candidate.spec.touches)
        ]
        if overlap:
            # The url, like the sibling refusal above: two lines in one morning
            # queue naming the same pull request two different ways is a reread.
            where = pr.get("url") or pr.get("headRefName", "")
            files = ", ".join(overlap[:3])
            if len(overlap) > 3:
                files += f", … ({len(overlap)} files)"
            return (
                f"touches overlaps open pull request {where}'s changed files: {files}"
            )

    if (escaped := _unmatched_criterion_path(candidate.spec)) is not None:
        return f"acceptance criteria name {escaped!r}, which no touches pattern matches"

    # The eighth refusal, beside the fifth: the same "touches doesn't reach
    # what this spec claims it will" defect, read from the repository's own
    # `saffron:retired-by` markers instead of the spec's acceptance criteria.
    if (retirement := retirement_refusal(candidate.spec, markers)) is not None:
        return retirement

    unmet = []
    for dep in candidate.spec.depends_on:
        reason = _dependency_refusal(
            dep,
            merged_anywhere=merged_anywhere,
            states_oldest_first=states_at_current_sha,
            retired=retired,
            unreadable_retired=unreadable_retired,
        )
        if reason is not None:
            unmet.append(reason)
    if unmet:
        # The count, not just the first reason: an operator who clears one
        # dependency and rediscovers the next tomorrow has lost a night to a
        # line that could have said there were two.
        suffix = f" (+{len(unmet) - 1} more unmet)" if len(unmet) > 1 else ""
        return unmet[0] + suffix

    return None


def build_queue(
    directory: Path,
    repo_id: int | None,
    ledger: Ledger,
    *,
    repo_slug: str | None = None,
    gh: GhRunner = run_gh,
    protected: Sequence[str] = (),
    markers: Sequence[tuple[str, str]] = (),
) -> tuple[list[Candidate], list[Refusal]]:
    """Turn the specs `discover_specs` found in `directory` into an ordered
    queue and a list of refusals.

    `repo_id` is `resolve_repo_id`'s answer, and `None` is a real case — a repo
    with no ledger row has no history to filter against, so every parseable
    spec is a fresh candidate — except one with a `depends_on` that only the
    ledger could satisfy, which is refused, because no row can say its parent
    merged. `specs/done/` is read either way, and `SA-0020` is why: retirement
    is the operator's assertion, not the ledger's, and a repo with no rows at
    all is exactly the repo whose work was done by hand.

    `repo_slug` is `owner/repo` for the two refusals that need GitHub's
    state. `None` — the default, and what every caller before `SA-0017`
    wires the CLI gets — skips both outright rather than erroring: nothing
    reaching this function yet knows the real slug, and a refusal gate that
    cannot check GitHub must not pretend it did.

    `protected` is the repo's `policy.yaml` `protected` list (`SA-0023`).
    This function never reads `policy.yaml` itself — the caller already
    exports the tree its specs come from, and `policy.yaml` sits right beside
    them in it. `()`, the default, is what every caller before `SA-0023`
    gets, and reproduces exactly the queue they already had: nothing is
    protected, so nothing is refused on that account.

    `markers` is every `saffron:retired-by` marker `mirror.retirement_markers`
    found at `base_sha`, repository-wide (`SA-0027`). This function never
    reads the mirror itself, the same reason it never reads `policy.yaml` —
    the caller already has it open. `()`, the default, reproduces exactly the
    queue every caller before `SA-0027` got.

    Ordered by `spec.priority` (lower runs first), then by `discover_specs`'
    filename order to break ties — `sorted` is stable and `discover_specs`
    already returns its specs in that order, so no second key is needed.
    """
    specs, failures = discover_specs(directory)
    existing = ledger.tasks_by_spec(repo_id) if repo_id is not None else {}

    candidates: list[Candidate] = []
    for discovered in specs:
        rows = existing.get((discovered.spec.id, discovered.spec_sha), ())
        # Existential, not last-row-wins: §4.2.1 asks whether the spec has *a*
        # task that is done with it, and one key holds many (`tasks_by_spec`).
        if any(row["state"] in DONE_STATES for row in rows):
            continue
        resumable = [row for row in rows if row["state"] in REQUEUE_STATES]
        # Oldest first out of the query, so the last is the newest send-back.
        task_id = int(resumable[-1]["task_id"]) if resumable else None
        candidates.append(
            Candidate(
                path=discovered.path,
                spec=discovered.spec,
                spec_sha=discovered.spec_sha,
                task_id=task_id,
            )
        )

    # Read across every `spec_sha` — merging is permanent, and a parent's spec
    # text moving afterwards does not un-merge its code.
    merged_anywhere = frozenset(
        spec_id
        for (spec_id, _sha), rows in existing.items()
        if any(row["state"] == DEPENDENCY_MERGED for row in rows)
    )
    # Every other state is read only at the sha the spec has on disk now.
    states_at_current_sha = {
        discovered.spec.id: [
            row["state"]
            for row in existing.get((discovered.spec.id, discovered.spec_sha), ())
        ]
        for discovered in specs
    }

    retired, retired_failures = _retired_ids(directory)
    open_prs = _open_prs(repo_slug, gh) if repo_slug is not None else []

    # Every id this directory declares, live or retired to `done/` — the same
    # union `_dependency_refusal` already treats as satisfied. A marker naming
    # anything else is a dangling reference, not any candidate's own refusal.
    known_ids = frozenset(discovered.spec.id for discovered in specs) | retired

    refusals = [Refusal(path=f.path, reason=f.reason) for f in failures]
    refusals += [
        Refusal(
            path=f.path,
            reason=(
                f"retired to {RETIRED_DIRNAME}/ but does not parse, so it "
                f"credits no dependency: {f.reason}"
            ),
        )
        for f in retired_failures
    ]
    refusals += _dangling_marker_refusals(
        markers, known_ids, len(failures) + len(retired_failures)
    )
    kept: list[Candidate] = []
    for candidate in candidates:
        reason = _refuse(
            candidate,
            open_prs=open_prs,
            merged_anywhere=merged_anywhere,
            states_at_current_sha=states_at_current_sha,
            retired=retired,
            unreadable_retired=len(retired_failures),
            protected=protected,
            markers=markers,
        )
        if reason is not None:
            refusals.append(Refusal(path=candidate.path, reason=reason))
        else:
            kept.append(candidate)
    kept.sort(key=lambda c: c.spec.priority)

    return kept, refusals
