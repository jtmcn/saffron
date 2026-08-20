from __future__ import annotations

from saffron.phases import implement


def test_the_permission_mode_denies_rather_than_asks():
    """In an unattended system, 'ask the operator' is not a fallback, it is a
    hang (DESIGN.md §5.3)."""
    options = implement.agent_options(
        system_prompt="s", cwd="/work", max_turns=40, budget_usd=12.0
    )
    assert options["permission_mode"] == "dontAsk"


def test_permissions_are_never_bypassed():
    options = implement.agent_options(
        system_prompt="s", cwd="/work", max_turns=40, budget_usd=12.0
    )
    assert options["permission_mode"] != "bypassPermissions"


def test_every_host_side_bound_is_set():
    options = implement.agent_options(
        system_prompt="s", cwd="/work", max_turns=40, budget_usd=12.0
    )
    assert options["max_turns"] == 40
    assert options["max_budget_usd"] == 12.0


def test_the_cache_ttl_outlives_a_gate_run():
    """The repair loop resumes across a gate run, and a gate run is minutes.
    The five-minute default expires every time (DESIGN.md §7.1)."""
    options = implement.agent_options(
        system_prompt="s", cwd="/work", max_turns=40, budget_usd=12.0
    )
    assert options["env"]["ENABLE_PROMPT_CACHING_1H"] == "1"


def test_agent_state_is_not_under_the_worktree():
    options = implement.agent_options(
        system_prompt="s", cwd="/work", max_turns=40, budget_usd=12.0
    )
    assert not options["env"]["CLAUDE_CONFIG_DIR"].startswith("/work")


def test_the_tool_list_is_explicit_and_excludes_the_network():
    assert "WebFetch" not in implement.IMPLEMENT_TOOLS
    assert "WebSearch" not in implement.IMPLEMENT_TOOLS
    assert {"Read", "Write", "Edit", "Bash", "Glob", "Grep"} <= set(
        implement.IMPLEMENT_TOOLS
    )


def test_a_crashed_attempt_falls_back_to_the_last_good_cost():
    """The runtime may report every cost field as zero on crash (§4.1)."""
    result = implement._reconcile_cost(
        reported=0.0, last_good=4.12, subtype="error_during_execution"
    )
    assert result == 4.12


def test_a_clean_finish_keeps_its_reported_cost():
    assert (
        implement._reconcile_cost(reported=3.5, last_good=2.0, subtype="success") == 3.5
    )
