#!/usr/bin/env python3
"""ty -> the gate contract.

`concise` rather than ty's `gitlab` format, which is its only JSON: that name
describes a schema, not a destination, and a flag naming the wrong forge in a
repo that has none would read as an integration it is not. The cost is a
parser, and the parser is made total by reconciling against ty's own count —
see below.
"""

import json
import re
import subprocess
import sys
from typing import NoReturn

LINE = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+):\d+: (?:error|warning)\[(?P<code>[^\]]+)\] (?P<message>.*)$"
)
COUNT = re.compile(r"^Found (\d+) diagnostics?$", re.MULTILINE)


def emit(payload) -> NoReturn:
    # NoReturn, so a guard that ends in `emit` narrows: without it every
    # post-guard read is `T | None` to the checker, including this gate's own.
    print(json.dumps(payload))
    sys.exit(0)


try:
    version = subprocess.run(["ty", "--version"], capture_output=True, text=True)
except FileNotFoundError:
    emit({"gate": "types", "status": "error", "summary": "ty not on PATH"})
if version.returncode != 0:
    emit({"gate": "types", "status": "error", "summary": "ty not on PATH"})
tool = version.stdout.strip()
if not tool:
    # A tool that runs and identifies nothing cannot produce the field that
    # separates a gate that ran from one that did not (§5.4, Appendix H).
    emit({"gate": "types", "status": "error", "summary": "ty reported no version"})

proc = subprocess.run(
    ["ty", "check", "--output-format", "concise"], capture_output=True, text=True
)

# ty exits 0 clean and 1 on diagnostics. Anything else is ty itself failing —
# an unresolvable configured environment, an unreadable file — and that is
# `error`, charged to nobody, not a verdict on the repo's code (§5.4).
if proc.returncode not in (0, 1):
    emit(
        {
            "gate": "types",
            "status": "error",
            "tool": tool,
            "summary": f"ty exited {proc.returncode}: {proc.stderr.strip()[:200]}",
        }
    )
if proc.returncode == 0:
    emit(
        {
            "gate": "types",
            "status": "pass",
            "tool": tool,
            "failures": [],
            "summary": "no type errors",
        }
    )

failures = [
    {
        "file": m["file"],
        "line": int(m["line"]),
        "code": m["code"],
        "message": m["message"],
    }
    for m in (LINE.match(one) for one in proc.stdout.splitlines())
    if m
]

# §5.4: partial results are not results. ty prints what it found; a diagnostic
# this parser drops (one carrying no line, a message shape that moved) would
# otherwise be reported as a smaller repair target than the real one, and a
# dropped failure can never be counted as new by the baseline subtraction.
counted = COUNT.search(proc.stdout)
if counted is None:
    emit(
        {
            "gate": "types",
            "status": "error",
            "tool": tool,
            "summary": f"ty exited {proc.returncode} and reported no count",
        }
    )
if len(failures) != int(counted[1]):
    emit(
        {
            "gate": "types",
            "status": "error",
            "tool": tool,
            "summary": f"ty reported {counted[1]} diagnostics, parsed {len(failures)}",
        }
    )

plural = "" if len(failures) == 1 else "s"
emit(
    {
        "gate": "types",
        "status": "fail",
        "tool": tool,
        "failures": failures,
        "summary": f"{len(failures)} diagnostic{plural}",
    }
)
