"""Phase 2 — IMPLEMENT, with a plan checkpoint (DESIGN.md §5.3).

The planner and the implementer are the same session: they are not adversaries,
and splitting them pays full context cost twice for the same file reads.
"""

from __future__ import annotations

from dataclasses import dataclass

from saffron.cell.worktree import STATE_MOUNT, WORKTREE_MOUNT

# Explicit, and deliberately without the network tools. The cell has no route
# to reach them anyway — this saves the turns spent discovering that.
IMPLEMENT_TOOLS = ["Read", "Write", "Edit", "Glob", "Grep", "Bash", "TodoWrite"]


@dataclass
class AttemptResult:
    session_id: str | None
    subtype: str
    terminal_reason: str | None
    num_turns: int
    cost_usd_est: float


def agent_options(
    *,
    system_prompt: str,
    cwd: str = WORKTREE_MOUNT,
    max_turns: int,
    budget_usd: float,
    resume: str | None = None,
) -> dict:
    """ClaudeAgentOptions as a plain dict, so it is assertable without the SDK.

    `permission_mode="dontAsk"` is the load-bearing one. The obvious mode
    auto-accepts file *edits* — which covers Edit and Write and nothing else; a
    shell command outside `allowed_tools` still raises a prompt, and at 03:00
    inside a cell there is nobody to answer it. The attempt would burn its idle
    timeout and read as a stall. `bypassPermissions` is the wrong fix: it removes
    the wasted-turn saving along with the prompt and buys nothing safety-wise,
    since the real controls are structural.
    """
    options = {
        "system_prompt": system_prompt,
        "allowed_tools": list(IMPLEMENT_TOOLS),
        "permission_mode": "dontAsk",
        "cwd": cwd,
        "max_turns": max_turns,
        # An in-cell ceiling, evaluated by a process inside the cell. It saves
        # turns; it is not what N2 rests on. The supervisor's bound is (§4.3).
        "max_budget_usd": budget_usd,
        "env": {
            # The repair loop resumes the same session across a gate run, and a
            # gate run is minutes. At the five-minute default the cache has
            # expired on every attempt and the whole accumulated context is
            # re-billed as fresh input (§7.1).
            "ENABLE_PROMPT_CACHING_1H": "1",
            # Never under /work: the agent must not be able to read its own
            # session state, and the secret scan must not trip on it (§5.1).
            "CLAUDE_CONFIG_DIR": STATE_MOUNT,
        },
    }
    if resume:
        options["resume"] = resume
    return options


def _reconcile_cost(*, reported: float, last_good: float, subtype: str) -> float:
    """A crashed session may report every cost field as zero (§4.1).

    An attempt that burned $4 and then crashed records $0 unless the supervisor
    falls back to the last good figure it saw. Unattended, this is the
    difference between a budget that holds and one that silently stops counting.
    """
    if subtype != "success" and reported == 0.0 and last_good > 0.0:
        return last_good
    return reported
