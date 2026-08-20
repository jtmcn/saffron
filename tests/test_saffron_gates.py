"""Saffron's own gates satisfy the contract they are declared against.

This file is the §2.1 boundary test in miniature: it exercises .saffron/ and
imports nothing from saffron/ except the contract parser.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from saffron.gates.runner import run_gate
from saffron.repos.policy import load_policy

REPO = Path(__file__).resolve().parent.parent
GATES = REPO / ".saffron" / "gates"


def test_the_policy_parses():
    policy, _ = load_policy(REPO)
    assert set(policy.gates) == {"format", "lint", "types", "tests"}


def test_types_skips_because_saffron_declares_no_type_checker():
    result = run_gate("types", GATES / "types", REPO)
    assert result.status == "skip"


@pytest.mark.parametrize("name", ["format", "lint"])
def test_the_fast_gates_name_their_tool_and_pass_on_a_clean_tree(name):
    result = run_gate(name, GATES / name, REPO, timeout_s=120)
    assert result.status == "pass", result.summary
    assert result.tool and result.tool.startswith("ruff")
