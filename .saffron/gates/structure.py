#!/usr/bin/env python3
"""ast-grep scan -> the gate contract.

The rules live in `.saffron/rules/` and encode invariants that were prose in
CLAUDE.md and enforced by nothing: which module may name the cell runtime, which
file may import the Agent SDK, and that a gate's `tool` field is executed rather
than written. Structural rather than textual because every one of those has a
legitimate textual near-miss in the tree — a comment naming apple/container, a
string passing `import claude_agent_sdk` to `python -c` (Appendix G, §2.1, §5.4).
"""

import json
import pathlib
import re
import subprocess
import sys
from typing import NoReturn

# Anchored on this file, not on the cwd, and passed to ast-grep as `-c` rather
# than left to be discovered: a `sgconfig.yml` found by walking up from the cwd
# is whichever one is nearest, and one planted at the repo root — outside
# `.saffron/**`, so outside everything `integrity` and `protected` guard — points
# `ruleDirs` at a decoy and reports a clean scan over rules nobody wrote. This is
# also `shacl.py`'s reason for resolving its own paths rather than trusting cwd.
CONFIG = pathlib.Path(__file__).resolve().parent.parent / "sgconfig.yml"
RULES = CONFIG.parent / "rules"


def emit(payload) -> NoReturn:
    print(json.dumps(payload))
    sys.exit(0)


try:
    version = subprocess.run(["ast-grep", "--version"], capture_output=True, text=True)
# Not just FileNotFoundError: a present-but-unrunnable binary raises
# PermissionError, and a traceback writes nothing this gate's contract can parse.
except OSError as exc:
    emit(
        {
            "gate": "structure",
            "status": "error",
            "summary": f"ast-grep could not be run: {exc}",
        }
    )
if version.returncode != 0:
    emit({"gate": "structure", "status": "error", "summary": "ast-grep not on PATH"})
tool = version.stdout.strip()
# A tool that runs and identifies nothing cannot produce the field that separates
# a gate that ran from one that did not, so it is `error` rather than a pass
# carrying `tool: ""` (§5.4, Appendix H).
if not tool:
    emit(
        {
            "gate": "structure",
            "status": "error",
            "summary": "ast-grep reported no version",
        }
    )

# The rules are checked before the code is. A rule weakened until its own invalid
# snippet no longer matches leaves `scan` exiting 0 — a clean report from a rule
# that has stopped guarding anything, which is the shape of Appendix I. `integrity`
# fails a diff that touches `.saffron/**` (`gate-config-changed`), but that check
# exempts a task whose spec declared the touch, and it cannot see a rule broken by
# anything other than a diff. Milliseconds, so there is no reason to trust instead.
tests = subprocess.run(
    ["ast-grep", "test", "-c", str(CONFIG)], capture_output=True, text=True
)
# `ast-grep test` prints "Running 0 tests" and exits 0 when `testConfigs` is
# missing or the directory is empty: measured. Exit status alone would read that
# as every rule verified. Count them instead, against the rules on disk —
# measured, ast-grep loads a rule directory recursively and takes `.yaml` as
# readily as `.yml`, so a narrower count would read a rule it runs as absent.
counted = re.search(r"(\d+) passed; (\d+) failed", tests.stdout)
expected = sum(1 for p in RULES.rglob("*") if p.suffix in (".yml", ".yaml"))
if tests.returncode != 0 or counted is None:
    emit(
        {
            "gate": "structure",
            "status": "error",
            "tool": tool,
            "summary": f"rule tests did not pass (exit {tests.returncode})",
        }
    )
elif int(counted.group(1)) != expected or int(counted.group(2)) != 0:
    emit(
        {
            "gate": "structure",
            "status": "error",
            "tool": tool,
            "summary": (
                f"{counted.group(1)} of {expected} rules verified, "
                f"{counted.group(2)} failed"
            ),
        }
    )

# `--no-ignore hidden` is load-bearing, not tidiness: measured, a bare `ast-grep
# scan` walks past `.saffron/` because it is a dot-directory, and `.saffron/gates/`
# is where the `tool` rule matters most. A mutant planted there went unreported
# until this flag was added. It does not disable the gitignore filter, so `.venv`
# and `.claude/worktrees/` stay out.
#
# The other three are for a different reason. Measured, a violating *tracked* file
# disappears from this scan if any ignore file names it: ast-grep walks with the
# `ignore` crate, which has no notion of what git tracks. `.gitignore` is the one
# such source this repo keeps — it is what holds `.venv` out — and it is reachable,
# so `integrity.gate_config` routes an edit to it to a person. The rest are refused
# outright, because no policy list can reach them: `.ignore` is honoured even
# outside a repo, and `.git/info/exclude` and `core.excludesFile` never appear in a
# diff at all — the last one is not even in the repository. Measured with
# `core.excludesFile` naming a tracked violating file: scanned clean without
# `global`, reported with it.
#
# `--no-ignore parent` is deliberately absent. Measured at ast-grep 0.45.3, with a
# `.gitignore` one directory above the scan root and with and without a `.git`:
# the file was reported either way, so the flag changes nothing and would be a
# claim no test could falsify. Re-measure before adding it.
proc = subprocess.run(
    [
        "ast-grep",
        "scan",
        "-c",
        str(CONFIG),
        "--no-ignore",
        "hidden",
        "--no-ignore",
        "dot",
        "--no-ignore",
        "exclude",
        "--no-ignore",
        "global",
        "--json=compact",
    ],
    capture_output=True,
    text=True,
)
# Exit status cannot separate the two: `scan` exits non-zero *because* it found
# error-severity matches, which is a `fail`, not an `error`. The JSON parsing is
# what says the tool ran at all.
try:
    matches = json.loads(proc.stdout)
except json.JSONDecodeError:
    matches = None
# Valid JSON of the wrong shape is the same failure as no JSON: `{}` would
# iterate its keys below and raise on `m.get`, writing a traceback and no
# contract — the `PermissionError` defect one layer down.
if not isinstance(matches, list):
    emit(
        {
            "gate": "structure",
            "status": "error",
            "tool": tool,
            "summary": f"ast-grep emitted no JSON array (exit {proc.returncode})",
        }
    )

failures = [
    {
        "file": m.get("file"),
        # ast-grep counts lines from zero; every other gate here reports them
        # from one.
        "line": ((m.get("range") or {}).get("start") or {}).get("line", -1) + 1,
        "code": m.get("ruleId") or "ast-grep",
        "message": m.get("message", ""),
    }
    for m in matches
]
emit(
    {
        "gate": "structure",
        "status": "fail" if failures else "pass",
        "tool": tool,
        "failures": failures,
        "summary": f"{len(failures)} violations",
    }
)
