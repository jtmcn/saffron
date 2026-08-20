#!/usr/bin/env python3
"""pytest -> the gate contract. Accepts a test-subset argument from day one.

The subset argument is the single most constraining line in the contract and it
costs nothing to honour before `revert` — the gate that needs it — exists.
"""

import json
import re
import subprocess
import sys


def emit(payload):
    print(json.dumps(payload))
    sys.exit(0)


try:
    version = subprocess.run(["pytest", "--version"], capture_output=True, text=True)
except FileNotFoundError:
    emit({"gate": "tests", "status": "error", "summary": "pytest not on PATH"})
if version.returncode != 0:
    emit({"gate": "tests", "status": "error", "summary": "pytest not on PATH"})
tool = version.stdout.strip().splitlines()[0]

subset = sys.argv[1:]
proc = subprocess.run(
    ["pytest", "-q", "--no-header", "-p", "no:cacheprovider", *subset],
    capture_output=True,
    text=True,
)
out = proc.stdout + proc.stderr

# A lost worker is the gate's mechanism breaking, not the repo's code being
# wrong. Partial results are not results (§5.4).
if "worker" in out and "crashed" in out:
    emit(
        {
            "gate": "tests",
            "status": "error",
            "tool": tool,
            "summary": "a test worker crashed; the run is not trustworthy",
        }
    )
if "INTERNALERROR" in out or "error: unrecognized arguments" in out:
    emit(
        {
            "gate": "tests",
            "status": "error",
            "tool": tool,
            "summary": "pytest failed to run",
        }
    )

failures = [
    {
        "file": m.group(1),
        "line": int(m.group(2)),
        "code": m.group(3),
        "message": m.group(4).strip(),
    }
    for m in re.finditer(r"^(\S+?):(\d+): (\w+): (.*)$", out, re.MULTILINE)
]
if proc.returncode != 0 and not failures:
    for line in out.splitlines():
        if line.startswith("FAILED "):
            name = line.split(" ", 1)[1].split(" - ")[0]
            path = name.split("::")[0]
            failures.append({"file": path, "code": name, "message": line})

if proc.returncode != 0 and not failures:
    emit(
        {
            "gate": "tests",
            "status": "error",
            "tool": tool,
            "summary": f"pytest exited {proc.returncode} with no parsed failures",
        }
    )

summary = next(
    (
        line.strip()
        for line in reversed(out.splitlines())
        if " passed" in line or " failed" in line
    ),
    "",
)
emit(
    {
        "gate": "tests",
        "status": "fail" if failures else "pass",
        "tool": tool,
        "failures": failures,
        "summary": summary or f"exit {proc.returncode}",
    }
)
