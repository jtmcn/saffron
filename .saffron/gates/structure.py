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

RULES = pathlib.Path(__file__).resolve().parent.parent / "rules"


def emit(payload):
    print(json.dumps(payload))
    sys.exit(0)


try:
    version = subprocess.run(["ast-grep", "--version"], capture_output=True, text=True)
except FileNotFoundError:
    emit({"gate": "structure", "status": "error", "summary": "ast-grep not on PATH"})
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
tests = subprocess.run(["ast-grep", "test"], capture_output=True, text=True)
# `ast-grep test` prints "Running 0 tests" and exits 0 when `testConfigs` is
# missing or the directory is empty: measured. Exit status alone would read that
# as every rule verified. Count them instead, against the rules on disk.
counted = re.search(r"(\d+) passed; (\d+) failed", tests.stdout)
expected = len(list(RULES.glob("*.yml")))
if tests.returncode != 0 or counted is None:
    emit(
        {
            "gate": "structure",
            "status": "error",
            "tool": tool,
            "summary": f"rule tests did not pass (exit {tests.returncode})",
        }
    )
# `elif`, not a second `if`: `emit` exits, but it is not annotated `NoReturn` and
# the `types` gate is blocking, so only the branch narrows `counted` off `None`.
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
# stays out.
proc = subprocess.run(
    ["ast-grep", "scan", "--no-ignore", "hidden", "--json=compact"],
    capture_output=True,
    text=True,
)
# Exit status cannot separate the two: `scan` exits non-zero *because* it found
# error-severity matches, which is a `fail`, not an `error`. The JSON parsing is
# what says the tool ran at all.
try:
    matches = json.loads(proc.stdout)
except json.JSONDecodeError:
    emit(
        {
            "gate": "structure",
            "status": "error",
            "tool": tool,
            "summary": f"ast-grep emitted no JSON (exit {proc.returncode})",
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
