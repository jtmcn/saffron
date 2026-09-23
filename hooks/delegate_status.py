"""SessionStart hook: show the spec loop's status when a delegate session opens.

A plain `claude` session in this repo gets nothing. The input carries
`agent_type` only under `claude --agent <name>` (measured 2026-09-23).
"""

import json
import subprocess
import sys

DRIVER = ".claude/skills/run-saffron-spec-loop/driver.py"
STARTS = {"startup", "clear"}


def main() -> int:
    event = json.load(sys.stdin)
    if event.get("agent_type") != "delegate" or event.get("source") not in STARTS:
        return 0
    run = subprocess.run(
        ["uv", "run", DRIVER, "status"],
        cwd=event.get("cwd") or ".",
        capture_output=True,
        text=True,
        timeout=60,
    )
    status = (run.stdout + run.stderr).rstrip()
    status = status or f"driver status exited {run.returncode} with no output"
    json.dump(
        {
            "systemMessage": f"Spec loop status\n{status}",
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": f"`driver.py status` at session start:\n{status}",
            },
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
