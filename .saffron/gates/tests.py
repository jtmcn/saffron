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

# §5.4's `census` compares the names collected before the task against the
# names collected after. `-q --collect-only` prints one node id per line;
# 0.38s against this suite, measured, against a full run of ~36s.
#
# Same argv as the run below, so both see the same selection — pyproject's
# `-m "not cell"` deselects thirteen tests, and a census comparing a
# deselected list against a full one would report every cell test removed.
collect = subprocess.run(
    ["pytest", "-q", "--collect-only", "-p", "no:cacheprovider", *subset],
    capture_output=True,
    text=True,
)
# A collection that failed reports no names at all rather than a short list:
# a partial census is a mass deletion (§5.4, "partial results are not
# results"). `census` turns names-at-base and none-at-head into `error`.
collected = (
    [line for line in collect.stdout.splitlines() if "::" in line]
    if collect.returncode == 0
    else None
)

proc = subprocess.run(
    ["pytest", "-q", "--no-header", "-p", "no:cacheprovider", *subset],
    capture_output=True,
    text=True,
)
out = proc.stdout + proc.stderr

# A lost worker is the gate's mechanism breaking, not the repo's code being
# wrong. Partial results are not results (§5.4). Keyed on xdist's own wording:
# `-q` echoes node ids, so "worker" and "crashed" anywhere in the output made
# any repo with a `test_worker_crashed` abort on every red run.
if "node down" in out or "replacing crashed worker" in out:
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
        "collected": collected,
        "failures": failures,
        "summary": summary or f"exit {proc.returncode}",
    }
)
