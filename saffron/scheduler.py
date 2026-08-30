"""The queue scan — which specs on disk are worth running tonight, and in
what order (DESIGN.md §4.2.1).

This is the second and third of `SA-0009`'s split. `SA-0015` built the
`spec_sha`-keyed done/re-queue filter and the ordering, refusing only a spec
`discover_specs` could not parse. `SA-0016` (here) adds the other four of
§4.2.1's six refusals: an open pull request from another task already
targeting this spec, a `touches` overlap with an open pull request's changed
files, an acceptance criterion naming a path no `touches` pattern matches,
and a non-empty `depends_on`. That is five of the six refusals gate 0
describes — the sixth, a repo that failed preflight, is a batch-level check
outside `build_queue`'s job.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from saffron.gates.core.scope import matches
from saffron.intake import Spec, discover_specs
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
    an in-flight state (a corpse this spec does not stamp `ORPHANED`; that
    write belongs to the half of `SA-0009` that runs a cell). It is set only
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
    criteria naming a path outside `touches`, and a non-empty `depends_on`
    (`SA-0016`, all four here). The sixth, a repo that failed preflight, is a
    batch-level check outside `build_queue`."""

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
            # ponytail: open PR 101 and beyond is invisible to both
            # GitHub-backed refusals.
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

    ponytail: a spec that genuinely needs a forbidden path now runs to
    `max_attempts` and ends `EXHAUSTED` instead — a whole task, not one
    attempt. Measured, that trade is right (two of seventeen falsely
    refused, and a false refusal costs a night), but it is a trade.
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


def _refuse(candidate: Candidate, *, open_prs: list[dict]) -> str | None:
    """The first of §4.2.1's remaining refusals this candidate earns, or
    `None`. Order matches the acceptance criteria's own listing."""
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
        url = same_spec_pr.get("url", own_branch)
        return (
            f"an open pull request from another task already targets this spec: {url}"
        )

    for pr in open_prs:
        if pr.get("headRefName") == own_branch:
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

    if candidate.spec.depends_on:
        return f"depends_on is not scheduled: {', '.join(candidate.spec.depends_on)}"

    return None


def build_queue(
    directory: Path,
    repo_id: int | None,
    ledger: Ledger,
    *,
    repo_slug: str | None = None,
    gh: GhRunner = run_gh,
) -> tuple[list[Candidate], list[Refusal]]:
    """Turn the specs `discover_specs` found in `directory` into an ordered
    queue and a list of refusals.

    `repo_id` is `resolve_repo_id`'s answer, and `None` is a real case — a repo
    with no ledger row has no history to filter against, so every parseable
    spec is a fresh candidate.

    `repo_slug` is `owner/repo` for the two refusals that need GitHub's
    state. `None` — the default, and what every caller before `SA-0017`
    wires the CLI gets — skips both outright rather than erroring: nothing
    reaching this function yet knows the real slug, and a refusal gate that
    cannot check GitHub must not pretend it did.

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

    open_prs = _open_prs(repo_slug, gh) if repo_slug is not None else []

    refusals = [Refusal(path=f.path, reason=f.reason) for f in failures]
    kept: list[Candidate] = []
    for candidate in candidates:
        reason = _refuse(candidate, open_prs=open_prs)
        if reason is not None:
            refusals.append(Refusal(path=candidate.path, reason=reason))
        else:
            kept.append(candidate)
    kept.sort(key=lambda c: c.spec.priority)

    return kept, refusals
