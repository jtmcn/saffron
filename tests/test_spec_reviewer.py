"""The spec review's agent definition. Its prose is judged by the backtest; this
holds the one property a reader cannot see from a report: it has no edit tool."""

from __future__ import annotations

import re
from pathlib import Path

AGENT = Path(__file__).resolve().parents[1] / ".claude" / "agents" / "spec-reviewer.md"


def test_the_spec_review_agent_has_no_edit_tool():
    front = AGENT.read_text().split("---")[1]
    tools = re.search(r"^tools:(.*)$", front, re.MULTILINE)
    assert tools is not None
    assert {t.strip() for t in tools.group(1).split(",")} == {
        "Read",
        "Grep",
        "Glob",
        "Bash",
    }


PROMPT = AGENT.parents[2] / "saffron" / "agents" / "prompts" / "spec-review.md"


def _flat(path: Path) -> str:
    return " ".join(path.read_text().split())


def test_both_spec_reviews_check_each_named_symbol_exists_at_base():
    """b-cd41ac: a spec named five helpers absent at its base, and two
    spec reviews passed it."""
    assert "A missing one is a `build` blocker (b-cd41ac)." in _flat(AGENT)
    assert (
        "Does every function, test helper or other name the spec tells the cell "
        "to reuse exist at this snapshot." in _flat(PROMPT)
    )
