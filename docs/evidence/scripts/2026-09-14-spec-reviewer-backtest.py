"""Backtest the spec reviewer (docs/superpowers/specs/2026-09-14-spec-reviewer-design.md).

    uv run docs/evidence/scripts/2026-09-14-spec-reviewer-backtest.py controls
    uv run docs/evidence/scripts/2026-09-14-spec-reviewer-backtest.py review [--only SA-NNNN@sha]

Spends money: one headless `claude -p` session per spec version, each in a
detached worktree at that version, so the reviewer can read nothing newer.
`history` is computed here with `--before` and handed in, because the driver at
an old version has no `history` command.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]
DRIVER = REPO / ".claude" / "skills" / "run-saffron-spec-loop" / "driver.py"
AGENT = REPO / ".claude" / "agents" / "spec-reviewer.md"
OUT = REPO / "docs" / "evidence" / "spec-reviewer-backtest"
TOOLS = "Read,Grep,Glob,Bash(git show:*),Bash(git log:*),Bash(git ls-tree:*),Bash(git grep:*)"
FIRST_CELL_OK = {"READY_FOR_REVIEW", "APPROVED", "MERGE_TRAIN", "MERGED"}

# The design's Appendix A, minus its four excluded rows: (spec, pre-cell version, defects).
CASES = [
    ("SA-0005", "351bdd3", ["touches lacked cli.py and package.py, which its criteria needed"]),
    ("SA-0009", "ad94fd2", ["too wide: 990 lines against a 600 ceiling"]),
    ("SA-0011", "1e069af", ["tests/test_package.py Spec fakes outside touches"]),
    ("SA-0014", "e1090dc", ["false claim about SA-0005's criteria"]),
    ("SA-0016", "e1090dc", ["false claim that its refusal fires on SA-0005"]),
    ("SA-0018", "366e377", ["forbade DESIGN.md/CONTEXT.md, which the change made false"]),
    ("SA-0019", "6f8e0d7", ["orphan criterion broke an invariant"]),
    ("SA-0020", "86f0c6e", ["forbade saffron/phases/**, which the fix needed"]),
    ("SA-0025", "2e4f2e6", ["too wide for its ceilings"]),
    ("SA-0026", "0301518", ["test file holding a guard outside touches"]),
    ("SA-0029", "3ed6f83", ["too wide: plan at 1100 lines against 600"]),
    ("SA-0029", "98ce586", ["14 criteria demand tests past the 600 ceiling"]),
    ("SA-0031", "0bcf5ac", ["turn and budget ceilings too low for its width"]),
    ("SA-0043", "a205a90", ["golden fixture, test_events.py, test_session.py outside touches"]),
    ("SA-0044", "6ceb5ba", [
        "criterion 2's witness proves only the half already true",
        "criterion 4's real witness needs tests/test_worktree.py, outside touches",
    ]),
    ("SA-0051", "5177edb", ["three mechanisms; 650 lines against 600"]),
    ("SA-0059", "ab42114", ["nine files at elevated: too wide for its ceilings"]),
    ("SA-0063", "6527f73", [
        "forbade saffron/phases/**, home of the only call site",
        "the body dictates the literals its mutants pin",
    ]),
    ("SA-0065", "d84cab3", ["forbidden excludes a caller the change breaks"]),
    ("SA-0079", "1e2209a", ["missing mutant: the memo witness only answers 'present'"]),
    ("SA-0080", "1e2209a", ["missing mutant: headline witness passes a full re-parse"]),
    ("SA-0081", "1e2209a", ["missing mutant: a misplaced boundary passes"]),
    ("SA-0082", "c0e84c3", ["its table calls a non-equivalent alternative equivalent"]),
    ("SA-0083", "c0e84c3", ["missing mutant: deleting the override stays green"]),
    ("SA-0084", "c0e84c3", ["missing mutant: a partial strip passes 'every control character'"]),
    ("SA-0085", "c0e84c3", ["missing mutant: two witnesses each cover half a claim"]),
    ("SA-0086", "8811f3a", [
        "forbade pr_body.py, which the change made false",
        "no mutants on an edit, so a witness that cannot fail ships",
        "'verdict' used in the sense CONTEXT.md forbids",
    ]),
    ("SA-0087", "24edb32", [
        "60 turns / $8 against a 47-turn plan checkpoint",
        "criterion 3 charges an unappliable binary stub to the task",
    ]),
    ("SA-0087", "14f6357", ["criterion 2's witness passes with read_head on the wrong container"]),
]
# Appendix A and B ids: no control comes from either.
BLAMED = {spec for spec, _v, _d in CASES} | {
    "SA-0001", "SA-0013", "SA-0017", "SA-0021", "SA-0022", "SA-0041", "SA-0042",
    "SA-0045", "SA-0046", "SA-0048", "SA-0049", "SA-0050", "SA-0052", "SA-0058",
    "SA-0064", "SA-0066", "SA-0067", "SA-0068", "SA-0069", "SA-0070", "SA-0071",
    "SA-0072", "SA-0073", "SA-0077", "SA-0088", "SA-0089",
}
# Filled from `controls` in the pre-registration commit, never after a review.
CONTROLS: list[tuple[str, str]] = [
    ("SA-0062", "210b0d4"),
    ("SA-0061", "210b0d4"),
    ("SA-0060", "210b0d4"),
    ("SA-0056", "ee98185"),
    ("SA-0055", "49cc2ef"),
    ("SA-0054", "fdcbbad"),
    ("SA-0030", "59cde3d"),
    ("SA-0040", "98ce586"),
    ("SA-0027", "094cc4e"),
    ("SA-0024", "7455593"),
]


def _git(*args: str, cwd: Path = REPO) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def _driver():
    spec = importlib.util.spec_from_file_location("spec_loop_driver", DRIVER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def cmd_controls(_args) -> int:
    """The 10 most recent done/ specs in neither appendix whose first cell reached
    READY_FOR_REVIEW, each at the last commit touching it before that cell."""
    from saffron.intake import discover_specs

    driver = _driver()
    done = {d.spec.id for d in discover_specs(REPO / ".saffron" / "specs" / "done")[0]}
    ledger, repo_id, _url = driver._ledger_and_repo()
    try:
        first: dict[str, tuple[int, str]] = {}
        for (spec_id, _sha), rows in ledger.tasks_by_spec(repo_id).items():
            for row in rows:
                if spec_id not in first or row["task_id"] < first[spec_id][0]:
                    first[spec_id] = (row["task_id"], row["state"])
        picked = []
        for spec_id, (task_id, state) in first.items():
            if spec_id not in done or spec_id in BLAMED or state not in FIRST_CELL_OK:
                continue
            attempts = ledger.attempts(task_id)
            if attempts:
                picked.append((attempts[0]["started_at"], spec_id))
    finally:
        ledger.close()
    for started, spec_id in sorted(picked, reverse=True)[:10]:
        version = _git(
            "log", "-1", "--format=%h", f"--before={started} +0000", "--",
            f":(glob).saffron/specs/**/{spec_id}-*.md", f":(glob).saffron/specs/{spec_id}-*.md",
        )
        print(f"| {spec_id} | {version} | {started} |")
    return 0


def _agent_json() -> str:
    _, front, body = AGENT.read_text().split("---", 2)
    meta = yaml.safe_load(front)
    return json.dumps({"spec-reviewer": {"description": meta["description"], "prompt": body.strip()}})


def _spec_path(spec_id: str, version: str) -> str:
    names = _git("ls-tree", "-r", "--name-only", version, ".saffron/specs").splitlines()
    match = [n for n in names if n.rsplit("/", 1)[-1].startswith(f"{spec_id}-")]
    if len(match) != 1:
        raise SystemExit(f"{spec_id}@{version}: {len(match)} spec files, expected 1")
    return match[0]


def _review(spec_id: str, version: str) -> None:
    path = _spec_path(spec_id, version)
    history = subprocess.run(
        ["uv", "run", str(DRIVER), "history", spec_id, "--before", version],
        cwd=REPO, check=True, capture_output=True, text=True,
    ).stdout
    prompt = (
        f"spec: {path}\nbase: HEAD (this checkout is the base commit)\n"
        f"history (precomputed; do not run the command):\n{history}"
    )
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp) / f"{spec_id}-{version}"
        _git("worktree", "add", "-q", "--detach", str(tree), version)
        try:
            done = subprocess.run(
                ["claude", "-p", "--agents", _agent_json(), "--agent", "spec-reviewer",
                 "--output-format", "json", "--permission-prompts", "none",
                 "--allowedTools", TOOLS],
                cwd=tree, input=prompt, capture_output=True, text=True, timeout=1800,
            )
        finally:
            _git("worktree", "remove", "--force", str(tree))
    if done.returncode != 0:
        raise SystemExit(f"{spec_id}@{version}: claude exited {done.returncode}: {done.stderr[-500:]}")
    result = json.loads(done.stdout)
    OUT.mkdir(parents=True, exist_ok=True)
    stem = OUT / f"{spec_id}-{version}"
    stem.with_suffix(".md").write_text(result.get("result") or "")
    keep = {k: result.get(k) for k in ("total_cost_usd", "num_turns", "is_error", "subtype")}
    stem.with_suffix(".json").write_text(json.dumps(keep, indent=1) + "\n")
    print(f"{spec_id}@{version}  ${keep['total_cost_usd'] or 0:.2f}  {keep['num_turns']} turns")


def cmd_review(args) -> int:
    targets = [(s, v) for s, v, _d in CASES] + CONTROLS
    if args.only:
        targets = [t for t in targets if f"{t[0]}@{t[1]}" == args.only]
    for spec_id, version in targets:
        if (OUT / f"{spec_id}-{version}.md").exists():
            continue  # resumable: a finished review is never re-bought
        _review(spec_id, version)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("controls").set_defaults(func=cmd_controls)
    p = sub.add_parser("review")
    p.add_argument("--only", help="SA-NNNN@sha")
    p.set_defaults(func=cmd_review)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
