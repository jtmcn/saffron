#!/usr/bin/env python3
"""ty -> the gate contract.

ty has no JSON output (full/concise/gitlab/github/junit), so this parses
`concise`: `path:line:col: severity[rule] message`.
"""

import json
import re
import subprocess
import sys

LINE = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+):\d+: (?:error|warning)\[(?P<code>[^\]]+)\] (?P<message>.*)$"
)


def emit(payload):
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
if not failures:
    # Non-zero exit and nothing parsed: the output shape changed. Silence is
    # bit-for-bit a pass, so this is `error` and is charged to nobody (§5.4).
    emit(
        {
            "gate": "types",
            "status": "error",
            "tool": tool,
            "summary": f"ty exited {proc.returncode}, parsed no diagnostics",
        }
    )
emit(
    {
        "gate": "types",
        "status": "fail",
        "tool": tool,
        "failures": failures,
        "summary": f"{len(failures)} type errors",
    }
)
