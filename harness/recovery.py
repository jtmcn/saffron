"""Rebuild a fixture's range and gate tools from the ledger and the batch tree.

`docs/superpowers/specs/2026-09-08-lens-corpus-design.md`. Every `head_sha`
recorded in `patch.json` is gone from live history — the branch was deleted
after merge — so a fixture's range is recovered rather than read off:

    head  the ledger's `pushed_sha` for the task that actually pushed one
    base  `patch.json`'s own `tree_base`, verified by byte-identity against
          the batch tree's recorded `patch.diff` before it is trusted

Byte-identity is the acceptance test, not a heuristic. `tree_base` is
recorded beside `base_sha` precisely for a stacked child, where the patch is
relative to the previous task's head rather than to `base_sha`
(`docs/BACKLOG.md` item 33: "`SA-0022` records `tree_base` beside `base_sha`
precisely so that read can be made correct"). The batch tree's own record was
right on all eight shipped fixtures; reading `base_sha` instead of `tree_base`
was this module's bug, not a gap in what got recorded. `recover_range`'s
ancestry walk is kept only as a fallback for a `tree_base` that fails to
verify — an inconsistency in the record, not the case any shipped fixture is.

Shared by the two dated scripts under `docs/evidence/scripts/`: a Python
module name cannot begin with a digit, so neither of those `2026-09-0*.py`
files can import the other, and this module is their common home instead
(`docs/evidence/scripts/2026-09-08-recover-fixture.py`,
`docs/evidence/scripts/2026-09-08-sa0062-gate-tools.py`).
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path

from saffron.agents import context
from saffron.cell.worktree import DIFF_FLAGS
from saffron.gates.contract import GateResult
from saffron.intake import DisclosedMutantError, parse_spec
from saffron.ledger import Ledger
from saffron.phases import review

# Bounds the fallback walk in `recover_range`. Exercised by none of the eight
# shipped fixtures — each verifies on `tree_base` directly. Before that fix,
# the candidate that verified sat at `rev-list`'s index 1 (the head's
# immediate parent) in every one of the eight, so this stays an unmeasured
# guess for anything more divergent rather than being cut to 1.
WALK_DEPTH = 60

FIXTURE_FILES = (
    "diff.patch",
    "recorded-findings.json",
    "gates.txt",
    "spec_body.md",
    "context.md",
    "fixture.toml",
)


class RecoveryError(RuntimeError):
    """A range that cannot be reproduced exactly. Never a warning."""


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True
    ).stdout


def pinned_diff(repo: Path, base: str, head: str) -> str:
    """`git diff base..head`, pinned against every host git config measured
    to move it — the only spelling of `git diff` this module allows for
    comparing against a recorded `patch.diff`.

    Starts from the cell's own export (`saffron/cell/worktree.py`'s
    `DIFF_FLAGS` and its `_git`'s two `-c` overrides), which is not enough by
    itself: measured against all eight shipped fixtures, `DIFF_FLAGS` plus
    those two overrides still differs from the recorded patch under
    `core.abbrev=12` or `diff.context=5` (`diff.noprefix=true`,
    `diff.algorithm=patience` and `diff.suppressBlankEmpty=true` are already
    covered by `--src-prefix`/`--dst-prefix`, the diff itself, and the
    `-c diff.suppressBlankEmpty=false` override, respectively — verified,
    not assumed). `--abbrev=7`, `--unified=3` and `--diff-algorithm=myers`
    close the remaining two — `7` is not "git's default", which is
    `core.abbrev=auto` and scales with the repo's object count, but what
    `auto` actually emitted: all 28 `index` lines across all eight recorded
    patches are 7 hex digits on both sides. Pinning what was measured, not
    what `auto` happens to be today, is what keeps this working after this
    repo outgrows auto-7 — copying `auto` would silently start failing at
    that point instead. `3` matches every recorded patch's hunk headers the
    same way. If a future fixture's recorded patch used a different width,
    this would need to know that width rather than guess.
    """
    return _git(
        repo,
        "-c",
        "core.quotePath=false",
        "-c",
        "diff.suppressBlankEmpty=false",
        "diff",
        *DIFF_FLAGS,
        "--abbrev=7",
        "--unified=3",
        "--diff-algorithm=myers",
        f"{base}..{head}",
    )


def _task_row(ledger: Ledger, spec_id: str) -> sqlite3.Row:
    """The one ledger row for `spec_id` that actually pushed a branch.

    A requeued spec can carry more than one row — `SA-0064` does: task 60,
    `PREFLIGHT_FAILED` with `pushed_sha` NULL, and task 61, `MERGED` with a
    real one. Filtered on `pushed_sha` rather than on `state == "MERGED"`:
    `pushed_sha` is the one fact both `recover_range` (the branch to diff)
    and `_reviewed_results` (the attempt whose gates ran) actually need, and
    the failed attempt never has it — so the filter that picks the right row
    is the same fact that explains why the other one was never a candidate.
    """
    rows = [
        r for r in ledger.queue_lines() if r["spec_id"] == spec_id and r["pushed_sha"]
    ]
    if len(rows) != 1:
        raise RecoveryError(
            f"{len(rows)} tasks with a pushed_sha for {spec_id}, want 1"
        )
    return rows[0]


def recover_range(spec_id: str, home: Path, repo: Path) -> tuple[str, str]:
    """`(base, head)` for a spec, verified against its recorded patch."""
    batch_dir = home / "batches" / "v0" / spec_id
    recorded = (batch_dir / "patch.diff").read_text()
    ledger = Ledger(home / "ledger.db")
    try:
        head = _task_row(ledger, spec_id)["pushed_sha"]
    finally:
        ledger.close()

    tree_base = json.loads((batch_dir / "patch.json").read_text())["tree_base"]
    if pinned_diff(repo, tree_base, head) == recorded:
        return tree_base, head

    # Fallback only: no shipped fixture reaches this line (see module and
    # `WALK_DEPTH` docstrings).
    for candidate in _git(repo, "rev-list", f"--max-count={WALK_DEPTH}", head).split():
        if pinned_diff(repo, candidate, head) == recorded:
            return candidate, head
    raise RecoveryError(
        f"{spec_id}: neither the recorded tree_base ({tree_base[:8]}) nor any "
        f"ancestor within {WALK_DEPTH} of {head[:8]} reproduces the recorded "
        "patch. The range is not recoverable and the fixture must not ship."
    )


def splice_tools(results: list[GateResult], baseline: list[dict]) -> list[GateResult]:
    """Head-suite results carrying the tools the same run's baseline recorded.

    Base and head ran the same binaries from the same cell image in the same
    run, so a version string in the baseline suite is the version string at
    head. `revert` skipped at base and inherits the tool of the `tests` re-run
    it performs (`revert.py:244`, `:350`/`:370`); every other miss is a host-side core gate
    that executes nothing, and None renders as "no tool reported".
    """
    tools = {row["gate"]: row["tool"] for row in baseline if row["tool"]}
    return [
        result.model_copy(
            update={
                "tool": tools.get(
                    result.gate,
                    tools.get("tests") if result.gate == "revert" else None,
                )
            }
        )
        for result in results
    ]


def _spec_path_at(repo: Path, sha: str, spec_id: str) -> str:
    """The tracked path of `spec_id`'s spec file at `sha` — the filename
    carries a title suffix, so it is found rather than guessed."""
    names = _git(repo, "ls-tree", "-r", "--name-only", sha, ".saffron/specs/").split(
        "\n"
    )
    matches = [n for n in names if Path(n).name.startswith(f"{spec_id}-")]
    if len(matches) != 1:
        raise RecoveryError(
            f"{len(matches)} spec files for {spec_id} at {sha[:8]}, want 1: {matches}"
        )
    return matches[0]


def _spec_content_off_branch(repo: Path, head: str, spec_id: str) -> str:
    """A spec's text when `base`'s own tree never carries it.

    `base` is the previous task's head for a stacked task, not main — main
    kept reviewing specs while the queue drained, so a spec can be written
    (and revised) on disk after its task's base was cut and still be what
    `saffron cell` was pointed at. Found by the last commit, anywhere, that
    touched the file before `head` was committed: a spec does not change
    after review, so the latest revision at that moment is the one shown.
    """
    head_date = _git(repo, "log", "-1", "--format=%cI", head).strip()
    log = _git(
        repo,
        "log",
        "--all",
        f"--before={head_date}",
        "--name-only",
        "--pretty=format:%H",
        "--",
        f":(glob).saffron/specs/**/{spec_id}-*.md",
    ).strip()
    if not log:
        raise RecoveryError(
            f"{spec_id}: no commit anywhere carries its spec before {head_date}"
        )
    sha, path = log.split("\n")[:2]
    return _git(repo, "show", f"{sha}:{path}")


def spec_body_at(repo: Path, base: str, head: str, spec_id: str) -> str:
    """The exact `spec_body=` REVIEW was shown, rebuilt from git alone.

    Exposed (not folded into `recover_fixture`) so a hermetic test can
    reproduce a shipped `spec_body.md` from `base`/`head` the same way the
    byte-identity test reproduces `diff.patch` — needing this repo's git
    history and nothing under `~/.saffron`.
    """
    try:
        spec_path = _spec_path_at(repo, base, spec_id)
        spec_text = _git(repo, "show", f"{base}:{spec_path}")
    except RecoveryError:
        spec_text = _spec_content_off_branch(repo, head, spec_id)
    try:
        spec = parse_spec(spec_text)
    except DisclosedMutantError as exc:
        # Item 82's disclosure check postdates every spec recovered here — it
        # exists *because of* SA-0063 — so it refuses a historical spec as a
        # candidate for a new task, not as unreadable. `exc.spec` is the same
        # parse `discover_specs` keeps for exactly this case (intake.py:308).
        spec = exc.spec
    # The way session.py's REVIEW call assembles `spec_body=` at both sites.
    return spec.body + context.criteria_section(spec.acceptance)


def _reviewed_results(
    ledger: Ledger, spec_id: str
) -> tuple[sqlite3.Row, list[GateResult]]:
    """The suite REVIEW was shown: the last attempt that ran one.

    `session.py` keeps `green` from the gate call that decided the task was
    reviewable, and REVIEW's own attempts run no gates — so the last attempt
    holding results is that suite.
    """
    task = _task_row(ledger, spec_id)
    for attempt in reversed(ledger.attempts(task["task_id"])):
        results = ledger.attempt_results(attempt["attempt_id"])
        if results:
            return task, results
    raise RecoveryError(f"{spec_id} has no attempt carrying gate results")


def _pr_number(pr_url: str) -> int:
    return int(pr_url.rstrip("/").rsplit("/", 1)[-1])


def _toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def recover_fixture(spec_id: str, home: Path, repo: Path) -> dict[str, str]:
    """The six frozen files' content, keyed by filename — a dict, not a write,
    so a dry run costs nothing and `main` owns the filesystem side.

    No `[[defects]]` block: the backlog row that names the mutation proving a
    defect is the only place that predicate is chosen, and a generated guess
    would be a predicate nobody chose. `load_fixture` refuses a fixture with
    none, so a half-recovered one cannot be scored by accident.
    """
    base, head = recover_range(spec_id, home, repo)
    batch_dir = home / "batches" / "v0" / spec_id

    ledger = Ledger(home / "ledger.db")
    try:
        task, results = _reviewed_results(ledger, spec_id)
    finally:
        ledger.close()

    baseline = json.loads((batch_dir / "baseline.json").read_text())
    # No trailing newline: `gate_summary` returns none, `session.py` hands the
    # lens what it returns, and `load_fixture` reads the file verbatim.
    gates_txt = review.gate_summary(splice_tools(results, baseline))

    spec_body = spec_body_at(repo, base, head, spec_id)

    context_md = _git(repo, "show", f"{base}:CONTEXT.md")

    fixture_toml = (
        f"spec_id = {_toml_string(spec_id)}\n"
        f"pr = {_pr_number(task['pr_url'])}\n"
        f"base_sha = {_toml_string(base)}\n"
        f"head_sha = {_toml_string(head)}\n"
        # Not derivable from the ledger or batch tree — the backlog row that
        # cites this range is filled in by hand once the fixture is reviewed.
        f"source = {_toml_string('')}\n"
        "recorded_seen = 0\n"
        "recorded_graded = 0\n"
    )

    return {
        "diff.patch": (batch_dir / "patch.diff").read_text(),
        "recorded-findings.json": (batch_dir / "findings.json").read_text(),
        "gates.txt": gates_txt,
        "spec_body.md": spec_body,
        "context.md": context_md,
        "fixture.toml": fixture_toml,
    }
