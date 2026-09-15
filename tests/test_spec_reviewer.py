"""The spec reviewer's definition. Its prose is judged by the backtest; this
holds the one property a reader cannot see from a report: it has no edit tool."""

from __future__ import annotations

import re
from pathlib import Path

AGENT = Path(__file__).resolve().parents[1] / ".claude" / "agents" / "spec-reviewer.md"


def test_the_spec_reviewer_has_no_tool_that_writes():
    front = AGENT.read_text().split("---")[1]
    tools = re.search(r"^tools:(.*)$", front, re.MULTILINE)
    assert tools is not None
    assert {t.strip() for t in tools.group(1).split(",")} == {
        "Read",
        "Grep",
        "Glob",
        "Bash",
    }
