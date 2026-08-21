#!/usr/bin/env python3
"""ruff check -> the gate contract."""

import json
import subprocess
import sys


def emit(payload):
    print(json.dumps(payload))
    sys.exit(0)


try:
    version = subprocess.run(["ruff", "--version"], capture_output=True, text=True)
except FileNotFoundError:
    emit({"gate": "lint", "status": "error", "summary": "ruff not on PATH"})
if version.returncode != 0:
    emit({"gate": "lint", "status": "error", "summary": "ruff not on PATH"})
tool = version.stdout.strip()

proc = subprocess.run(
    ["ruff", "check", "--output-format", "json", "."],
    capture_output=True,
    text=True,
)
try:
    findings = json.loads(proc.stdout)
except json.JSONDecodeError:
    emit(
        {
            "gate": "lint",
            "status": "error",
            "tool": tool,
            "summary": f"ruff emitted no JSON (exit {proc.returncode})",
        }
    )

failures = [
    {
        "file": f["filename"],
        "line": (f.get("location") or {}).get("row"),
        "code": f.get("code") or "ruff",
        "message": f.get("message", ""),
    }
    for f in findings
]
emit(
    {
        "gate": "lint",
        "status": "fail" if failures else "pass",
        "tool": tool,
        "failures": failures,
        "summary": f"{len(failures)} violations",
    }
)
