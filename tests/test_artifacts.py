from __future__ import annotations

import pytest

from saffron.agents.artifacts import (
    Plan,
    PlanRejected,
    hash_artifact,
    parse_output_block,
    validate_plan,
)
from saffron.gates.core.scope import matches

TOUCHES = ["saffron/gates/**", "tests/**"]


def _plan(**overrides) -> str:
    payload = {
        "understanding": "u",
        "approach": "a",
        "files_to_change": ["saffron/gates/core/size.py", "tests/test_size.py"],
        "test_strategy": "t",
        "risks": [],
        "blocking_questions": [],
    }
    payload.update(overrides)
    import json

    return "<output>" + json.dumps(payload) + "</output>"


def test_the_output_block_is_extracted_from_surrounding_prose():
    text = 'Here you go:\n<output>{"a": 1}</output>\nHope that helps.'
    assert parse_output_block(text) == '{"a": 1}'


def test_missing_output_block_raises():
    with pytest.raises(ValueError):
        parse_output_block("no block here")


def test_the_last_output_block_wins():
    """EXTRACTION_PROMPT asks for the block *last*, so a draft followed by the
    real one would otherwise validate the draft (§5.3)."""
    text = '<output>{"draft": true}</output>\nOn reflection:\n<output>{"a": 1}</output>'
    assert parse_output_block(text) == '{"a": 1}'


def test_a_valid_plan_inside_touches_is_accepted():
    plan = validate_plan(
        _plan(), touches=TOUCHES, forbidden=[], protected=[], spec_type="feature"
    )
    assert isinstance(plan, Plan)


def test_a_file_outside_touches_is_rejected_with_no_model_call():
    with pytest.raises(PlanRejected, match="outside touches"):
        validate_plan(
            _plan(files_to_change=["saffron/cli.py"]),
            touches=TOUCHES,
            forbidden=[],
            protected=[],
            spec_type="feature",
        )


def test_a_forbidden_path_is_rejected():
    with pytest.raises(PlanRejected, match="forbidden"):
        validate_plan(
            _plan(),
            touches=TOUCHES,
            forbidden=["saffron/gates/**"],
            protected=[],
            spec_type="feature",
        )


def test_a_protected_path_is_rejected():
    with pytest.raises(PlanRejected, match="protected"):
        validate_plan(
            _plan(),
            touches=TOUCHES,
            forbidden=[],
            protected=["saffron/gates/**"],
            spec_type="feature",
        )


def test_blocking_questions_reject_the_plan():
    with pytest.raises(PlanRejected, match="blocking question"):
        validate_plan(
            _plan(blocking_questions=["which database?"]),
            touches=TOUCHES,
            forbidden=[],
            protected=[],
            spec_type="feature",
        )


def test_a_feature_with_no_test_file_is_rejected():
    with pytest.raises(PlanRejected, match="no test file"):
        validate_plan(
            _plan(files_to_change=["saffron/gates/core/size.py"]),
            touches=TOUCHES,
            forbidden=[],
            protected=[],
            spec_type="feature",
        )


def test_a_docs_change_needs_no_test_file():
    validate_plan(
        _plan(files_to_change=["saffron/gates/core/size.py"]),
        touches=TOUCHES,
        forbidden=[],
        protected=[],
        spec_type="docs",
    )


def test_schema_invalid_output_raises_plan_rejected():
    with pytest.raises(PlanRejected):
        validate_plan(
            '<output>{"understanding": 1}</output>',
            touches=TOUCHES,
            forbidden=[],
            protected=[],
            spec_type="feature",
        )


def test_the_artifact_is_hashed_at_validation():
    """Nothing downstream trusts a file the agent could have rewritten."""
    raw = _plan()
    assert hash_artifact(raw) == hash_artifact(raw)
    assert hash_artifact(raw) != hash_artifact(_plan(approach="different"))


# --- shared matcher semantics for `touches`/`forbidden`/`protected` patterns ---
#
# validate_plan uses saffron.gates.core.scope.matches — the same matcher
# scope_gate enforces the diff with — not fnmatch. fnmatch's `*` crosses `/`
# (see R9 fix round 1), which would let a plan pass this checkpoint and then
# fail scope_gate mechanically on the same pattern. These tests pin the
# shell-glob semantics `matches` actually provides, and that both callers now
# share by construction (one import, one implementation).


def test_double_star_matches_a_nested_file():
    """`saffron/gates/**` matches a file two directories deeper."""
    assert matches("saffron/gates/core/size.py", "saffron/gates/**")


def test_double_star_matches_a_direct_child():
    """`saffron/gates/**` also matches a file directly in the directory."""
    assert matches("saffron/gates/runner.py", "saffron/gates/**")


def test_single_star_does_not_cross_directory_separators():
    """Shell-glob semantics: `*` stops at `/`, unlike fnmatch's `*`.

    `saffron/gates/*` matches a direct child but not a nested file — this is
    the behaviour a developer writing `saffron/gates/*.py` in a policy file
    actually expects (this directory only), and it's why scope.py hand-rolls
    `matches` instead of using fnmatch.
    """
    assert not matches("saffron/gates/core/size.py", "saffron/gates/*")


def test_single_star_matches_a_direct_child():
    assert matches("saffron/gates/runner.py", "saffron/gates/*")


def test_validate_plan_and_scope_gate_agree_on_a_bare_star():
    """The specific divergence from R9: fnmatch said True, scope.matches says False.

    A plan naming a nested file under a bare-`*` touches pattern must now be
    rejected by validate_plan exactly as scope_gate would reject the diff —
    no more "passes the checkpoint, fails the gate mechanically".
    """
    assert matches("saffron/gates/core/size.py", "saffron/gates/*") is False
    with pytest.raises(PlanRejected, match="outside touches"):
        validate_plan(
            _plan(files_to_change=["saffron/gates/core/size.py"]),
            touches=["saffron/gates/*"],
            forbidden=[],
            protected=[],
            spec_type="docs",
        )


def test_empty_touches_is_a_deliberate_rejection_not_a_mystery():
    """scope_gate skips on empty touches; validate_plan must fail closed instead —
    but legibly, not as a false "outside touches" on the first file."""
    with pytest.raises(PlanRejected, match="no touches"):
        validate_plan(_plan(), touches=[], forbidden=[], protected=[], spec_type="docs")


def test_a_path_that_merely_contains_test_does_not_name_a_test_file():
    """`"test" in path` accepts `latest_config.py`, `contest.py`, `attest.py` —
    a rule a plan satisfies by accident is not a rule."""
    with pytest.raises(PlanRejected, match="names no test file"):
        validate_plan(
            _plan(files_to_change=["saffron/gates/latest_config.py"]),
            touches=TOUCHES,
            forbidden=[],
            protected=[],
            spec_type="feature",
        )
    # A real test file in the same plan still passes.
    validate_plan(
        _plan(
            files_to_change=["saffron/gates/latest_config.py", "tests/test_latest.py"]
        ),
        touches=TOUCHES,
        forbidden=[],
        protected=[],
        spec_type="feature",
    )
