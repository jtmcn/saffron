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
# `--color=no`: a host gate inherits FORCE_COLOR, and escapes break both parses.
def collect(args):
    done = subprocess.run(
        [
            "pytest",
            "-q",
            "--collect-only",
            "--color=no",
            "-p",
            "no:cacheprovider",
            *args,
        ],
        capture_output=True,
        text=True,
    )
    return done.returncode, [line for line in done.stdout.splitlines() if "::" in line]


def node_file(name):
    return name.split("::")[0]


returncode, names = collect(subset)
# A collection that failed reports no names at all rather than a short list:
# a partial census is a mass deletion (§5.4, "partial results are not
# results"). `census` turns names-at-base and none-at-head into `error`.
collected = names if returncode == 0 else None

# A handed subset is the exception §5.4 names (SA-0127): account for each name
# as collected or `uncollected`, so one id absent at base skips no other (item 50).
uncollected = None
if collected is None and subset and not any(n.startswith("-") for n in subset):
    known, clean = set(), set()
    for path in dict.fromkeys(node_file(n) for n in subset):
        path_code, path_names = collect([path])
        # INTERNAL_ERROR is the mechanism breaking, whatever the subset held.
        if path_code == 3:
            emit(
                {
                    "gate": "tests",
                    "status": "error",
                    "tool": tool,
                    "summary": "pytest failed to run",
                }
            )
        # Only its own file's ids: a leaked `zzz::bogus` line names no file here (item 51).
        known.update(n for n in path_names if node_file(n) == path)
        if path_code == 0:
            clean.add(path)
    uncollected = [
        n for n in subset if n not in known and not ("::" not in n and n in clean)
    ]
    subset = [n for n in subset if n not in uncollected]
    if subset:
        returncode, names = collect(subset)
        collected = (
            [n for n in names if n not in uncollected] if returncode == 0 else None
        )
    else:
        collected = []

if uncollected is not None and not subset:
    emit(
        {
            "gate": "tests",
            "status": "fail",
            "tool": tool,
            "collected": [],
            "uncollected": uncollected,
            "failures": [
                {"file": node_file(n), "code": n, "message": "could not be collected"}
                for n in uncollected
            ],
            "summary": f"none of {len(uncollected)} handed name(s) could be collected",
        }
    )

proc = subprocess.run(
    ["pytest", "-q", "--no-header", "--color=no", "-p", "no:cacheprovider", *subset],
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
# pytest's own exit codes, INTERNAL_ERROR and USAGE_ERROR. A test that prints
# either word exits 1, where a substring match read its output as the gate's.
if proc.returncode in (3, 4):
    emit(
        {
            "gate": "tests",
            "status": "error",
            "tool": tool,
            "summary": "pytest failed to run",
        }
    )

# Keyed on node ids when `uncollected` is reported: `revert` reads both lists
# together, and an exception type beside a node id reads a failure as a pass.
if uncollected is not None:
    failures = [
        {"file": node_file(name), "code": name, "message": line}
        for line in out.splitlines()
        if line.startswith(("FAILED ", "ERROR "))
        for name in [line.split(" ", 1)[1].split(" - ")[0]]
    ]
else:
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

if uncollected:
    failures += [
        {"file": node_file(n), "code": n, "message": "could not be collected"}
        for n in uncollected
    ]

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
        "uncollected": uncollected,
        "failures": failures,
        "summary": (summary or f"exit {proc.returncode}")
        + (f", {len(uncollected)} handed name(s) not collected" if uncollected else ""),
    }
)
