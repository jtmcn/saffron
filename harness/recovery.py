"""Rebuild a fixture's range and gate tools from the ledger and the batch tree.

`docs/superpowers/specs/2026-09-08-lens-corpus-design.md`. Every `head_sha`
recorded in `patch.json` is gone from live history — the branch was deleted
after merge — so a fixture's range is recovered rather than read off:

    head  the ledger's `pushed_sha` for the task
    base  the first ancestor of that head where `git diff base..head` is
          byte-identical to the batch tree's recorded `patch.diff`

Byte-identity is the acceptance test, not a heuristic. Four of the eight
fixtures need the walk because their recorded `tree_base` is not an ancestor of
their head at all: they were stacked pull requests, and SA-0048's true base is
SA-0046's head (backlog item 33, visible in the archive).

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
from saffron.gates.contract import GateResult
from saffron.intake import DisclosedMutantError, parse_spec
from saffron.ledger import Ledger
from saffron.phases import review

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


def recover_range(spec_id: str, home: Path, repo: Path) -> tuple[str, str]:
    """`(base, head)` for a spec, verified against its recorded patch."""
    recorded = (home / "batches" / "v0" / spec_id / "patch.diff").read_text()
    ledger = Ledger(home / "ledger.db")
    try:
        rows = [r for r in ledger.queue_lines() if r["spec_id"] == spec_id]
    finally:
        ledger.close()
    if len(rows) != 1:
        raise RecoveryError(f"{len(rows)} tasks for {spec_id}, want 1")
    head = rows[0]["pushed_sha"]
    if not head:
        raise RecoveryError(f"{spec_id} has no pushed_sha; its branch is unrecoverable")
    for candidate in _git(repo, "rev-list", f"--max-count={WALK_DEPTH}", head).split():
        if _git(repo, "diff", f"{candidate}..{head}") == recorded:
            return candidate, head
    raise RecoveryError(
        f"{spec_id}: no ancestor within {WALK_DEPTH} of {head[:8]} reproduces the "
        "recorded patch. The range is not recoverable and the fixture must not ship."
    )


def splice_tools(results: list[GateResult], baseline: list[dict]) -> list[GateResult]:
    """Head-suite results carrying the tools the same run's baseline recorded.

    Base and head ran the same binaries from the same cell image in the same
    run, so a version string in the baseline suite is the version string at
    head. `revert` skipped at base and inherits the tool of the `tests` re-run
    it performs (`revert.py:307`); every other miss is a host-side core gate
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


def _reviewed_results(
    ledger: Ledger, spec_id: str
) -> tuple[sqlite3.Row, list[GateResult]]:
    """The suite REVIEW was shown: the last attempt that ran one.

    `session.py` keeps `green` from the gate call that decided the task was
    reviewable, and REVIEW's own attempts run no gates — so the last attempt
    holding results is that suite.
    """
    tasks = [r for r in ledger.queue_lines() if r["spec_id"] == spec_id]
    if len(tasks) != 1:
        raise RecoveryError(f"{len(tasks)} tasks in the ledger for {spec_id}, want 1")
    for attempt in reversed(ledger.attempts(tasks[0]["task_id"])):
        results = ledger.attempt_results(attempt["attempt_id"])
        if results:
            return tasks[0], results
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
    spec_body = spec.body + context.criteria_section(spec.acceptance)

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
