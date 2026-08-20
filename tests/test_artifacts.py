from __future__ import annotations

import fnmatch

import pytest

from saffron.agents.artifacts import (
    Plan,
    PlanRejected,
    hash_artifact,
    parse_output_block,
    validate_plan,
)

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


# --- fnmatch semantics for `touches`/`forbidden`/`protected` patterns ---
#
# These document fnmatch's actual behaviour rather than assuming it. The same
# `touches` patterns feed the `scope` gate elsewhere, so a mismatch here would
# let a plan pass validation and then fail the gate mechanically.


def test_double_star_matches_a_nested_file():
    """`saffron/gates/**` matches a file two directories deeper."""
    assert fnmatch.fnmatch("saffron/gates/core/size.py", "saffron/gates/**")


def test_double_star_matches_a_direct_child():
    """`saffron/gates/**` also matches a file directly in the directory."""
    assert fnmatch.fnmatch("saffron/gates/runner.py", "saffron/gates/**")


def test_single_star_also_crosses_directory_separators():
    """Surprising but acceptable: fnmatch's `*` is not shell-glob `*`.

    It compiles to regex `.*`, so unlike shell globbing (and unlike
    pathlib.Path.match), a single `*` crosses `/` — `saffron/gates/*` matches
    a file nested arbitrarily deep, not just a direct child. `**` therefore
    buys nothing over `*` under fnmatch; both patterns behave identically
    here, which is why the brief specifies `**` for readability, not because
    fnmatch treats it specially.
    """
    assert fnmatch.fnmatch("saffron/gates/core/size.py", "saffron/gates/*")


def test_single_star_matches_a_direct_child_too():
    assert fnmatch.fnmatch("saffron/gates/runner.py", "saffron/gates/*")
