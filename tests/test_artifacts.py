from __future__ import annotations

import pytest

from saffron.agents.artifacts import (
    Plan,
    PlanRejected,
    ScopeProposalNotSchema,
    ScopeProposalRefused,
    extract_notes,
    extraction_kind,
    hash_artifact,
    parse_output_block,
    validate_plan,
    validate_scope_proposal,
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
        "estimated_lines": 10,
    }
    payload.update(overrides)
    import json

    return "<output>" + json.dumps(payload) + "</output>"


def _lines_diff(n: int, path: str = "src/x.py") -> str:
    """A single-file diff of `n` single-token added lines: `size_gate`
    counts it as exactly `n` changed tokens."""
    return (
        "\n".join(
            [
                f"diff --git a/{path} b/{path}",
                f"--- a/{path}",
                f"+++ b/{path}",
                f"@@ -0,0 +1,{n} @@",
                *(f"+line{i}" for i in range(n)),
            ]
        )
        + "\n"
    )


def test_the_output_block_is_extracted_from_surrounding_prose():
    text = 'Here you go:\n<output>{"a": 1}</output>\nHope that helps.'
    assert parse_output_block(text) == '{"a": 1}'


def test_extract_notes_returns_the_blocks_stripped_text():
    raw = "some preamble\n<output>\n  Saw a hardcoded secret.  \n</output>"
    assert extract_notes(raw) == "Saw a hardcoded secret."


def test_extract_notes_is_empty_when_the_block_is_empty():
    assert extract_notes("<output>\n\n</output>") == ""


def test_extract_notes_is_empty_when_there_is_no_block_at_all():
    """A turn the provider walled, or one that crashed before answering, must
    read as "nothing to report" — not as a rejection of a shape nobody asked
    this turn to have (there is no `PlanRejected` here at all)."""
    assert extract_notes("no output tags in this response") == ""


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


def test_a_plan_missing_estimated_lines_is_rejected():
    """An estimate that can be omitted is not a control."""
    payload = {
        "understanding": "u",
        "approach": "a",
        "files_to_change": ["saffron/gates/core/size.py", "tests/test_size.py"],
        "test_strategy": "t",
        "risks": [],
        "blocking_questions": [],
    }
    import json

    with pytest.raises(PlanRejected):
        validate_plan(
            "<output>" + json.dumps(payload) + "</output>",
            touches=TOUCHES,
            forbidden=[],
            protected=[],
            spec_type="feature",
        )


def test_a_plan_estimating_over_the_ceiling_is_rejected():
    """`validate_plan` no longer holds the ceiling check. It clears the
    plan, and `judge_estimate` at `elevated` is what rejects it."""
    from saffron.agents.artifacts import judge_estimate
    from saffron.gates.core.size import _CEILINGS

    ceiling = _CEILINGS["feature"]
    plan = validate_plan(
        _plan(estimated_lines=ceiling // 4 + 1),
        touches=TOUCHES,
        forbidden=[],
        protected=[],
        spec_type="feature",
    )
    with pytest.raises(PlanRejected, match=f"exceeds the feature ceiling of {ceiling}"):
        judge_estimate(plan, "feature", "elevated", [])


def test_a_plan_estimating_at_the_ceiling_is_accepted():
    from saffron.agents.artifacts import judge_estimate
    from saffron.gates.core.size import _CEILINGS

    ceiling = _CEILINGS["feature"]
    plan = validate_plan(
        _plan(estimated_lines=ceiling // 4),
        touches=TOUCHES,
        forbidden=[],
        protected=[],
        spec_type="feature",
    )
    assert plan.estimated_lines == ceiling // 4
    assert judge_estimate(plan, "feature", "elevated", []) is None


def test_validate_plan_and_size_gate_agree_on_the_ceiling():
    """The same table `size_gate` enforces the diff against. A plan
    `judge_estimate` cleared, then blown up by the agent's own diff, is a
    different bug. This one is a plan checked against the wrong number."""
    from saffron.agents.artifacts import judge_estimate
    from saffron.gates.core.size import _CEILINGS

    ceiling = _CEILINGS["bug"]
    plan = validate_plan(
        _plan(estimated_lines=ceiling // 4 + 1),
        touches=TOUCHES,
        forbidden=[],
        protected=[],
        spec_type="bug",
    )
    with pytest.raises(PlanRejected, match=f"exceeds the bug ceiling of {ceiling}"):
        judge_estimate(plan, "bug", "elevated", [])


def test_the_plan_checkpoint_prices_an_estimate_at_four_tokens_a_line():
    """Criterion 4: the plan's own estimate is in lines. `judge_estimate`
    prices it at `_TOKENS_PER_LINE` tokens a line, then compares it to the
    same ceiling `size_gate` reads off the real diff's tokens."""
    import ast
    from pathlib import Path

    from saffron.agents import artifacts
    from saffron.gates.core.size import _CEILINGS, _DEFAULT_CEILING, size_gate

    for spec_type in ("bug", "feature", "refactor", "docs"):
        ceiling = _CEILINGS.get(spec_type, _DEFAULT_CEILING)
        at_ceiling = ceiling // 4
        over_ceiling = at_ceiling + 1

        within = validate_plan(
            _plan(estimated_lines=at_ceiling),
            touches=TOUCHES,
            forbidden=[],
            protected=[],
            spec_type=spec_type,
        )
        assert artifacts.judge_estimate(within, spec_type, "elevated", []) is None

        over = validate_plan(
            _plan(estimated_lines=over_ceiling),
            touches=TOUCHES,
            forbidden=[],
            protected=[],
            spec_type=spec_type,
        )
        gate_result = size_gate(_lines_diff(over_ceiling * 4), spec_type, touches=[])
        assert gate_result.status == "fail"

        with pytest.raises(PlanRejected) as excinfo:
            artifacts.judge_estimate(over, spec_type, "elevated", [])
        assert gate_result.failures[0].message in str(excinfo.value)
        assert excinfo.value.risk_tier == "elevated"

        advisory = artifacts.judge_estimate(over, spec_type, "standard", [])
        assert advisory is not None
        assert str(over_ceiling) in advisory
        assert str(over_ceiling * 4) in advisory
        assert str(ceiling) in advisory
        assert advisory.startswith("advisory estimate: ")
        assert "the tier from the plan's files" in advisory

    tree = ast.parse(Path(artifacts.__file__).read_text())
    imported = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "saffron.gates.core.size"
        and any(
            alias.name == "_TOKENS_PER_LINE" and alias.asname is None
            for alias in node.names
        )
        for node in ast.walk(tree)
    )
    assigned = any(
        isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "_TOKENS_PER_LINE"
            for target in node.targets
        )
        for node in ast.walk(tree)
    )
    assert imported
    assert not assigned

    from saffron.gates.core.size import _TOKENS_PER_LINE

    assert _TOKENS_PER_LINE == 4
    assert type(_TOKENS_PER_LINE) is int


def test_the_advisory_set_and_the_plan_checkpoint_ask_one_function_whether_size_blocks(
    monkeypatch,
):
    """Criterion 4: `_advisory` and `judge_estimate` both decide through
    `size_blocks`, never a copy of its own comparison.

    `tests/test_cli.py::_source_calls` reads the AST, so a comment naming
    `size_blocks` does not satisfy the first half. The monkeypatched
    opposite makes a caller that discards the answer fail the second."""
    from saffron.agents import artifacts
    from saffron.gates import suite
    from saffron.gates.core.size import _CEILINGS
    from saffron.repos.policy import Policy
    from tests.test_cli import _source_calls

    assert _source_calls(suite._advisory, "size_blocks")
    assert _source_calls(artifacts.judge_estimate, "size_blocks")

    def opposite(tier: str) -> bool:
        return tier != "elevated"

    monkeypatch.setattr(suite, "size_blocks", opposite, raising=False)
    monkeypatch.setattr(artifacts, "size_blocks", opposite, raising=False)

    assert "size" in suite._advisory("elevated", Policy(gates={}))

    plan = validate_plan(
        _plan(estimated_lines=_CEILINGS["feature"] // 4 + 1),
        touches=TOUCHES,
        forbidden=[],
        protected=[],
        spec_type="feature",
    )
    with pytest.raises(PlanRejected):
        artifacts.judge_estimate(plan, "feature", "standard", [])


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


# --- scope proposal (SA-0018): an IMPLEMENT attempt's other door out ---


def _proposal(**overrides) -> str:
    payload = {
        "kind": "scope_proposal",
        "proposed_touches": ["saffron/cli.py"],
        "root_cause": "the queue line lives outside touches",
    }
    payload.update(overrides)
    import json

    return "<output>" + json.dumps(payload) + "</output>"


def test_extraction_kind_recognises_a_scope_proposal():
    assert extraction_kind(_proposal()) == "scope_proposal"


def test_extraction_kind_defaults_to_plan_for_anything_else():
    """Every existing plan-only path is unaffected — no `kind` field, or JSON
    that fails to parse at all, both read as a plan attempt."""
    assert extraction_kind(_plan()) == "plan"
    assert extraction_kind("not even json") == "plan"
    assert extraction_kind("<output>{}</output>") == "plan"


def test_a_proposal_naming_a_path_outside_touches_is_accepted():
    proposal = validate_scope_proposal(_proposal(), touches=TOUCHES)
    assert proposal.proposed_touches == ["saffron/cli.py"]
    assert proposal.root_cause


def test_a_proposal_naming_only_paths_already_inside_touches_is_refused():
    """The escape-hatch guard: SA-0018's whole point is that this must not be
    a free way out of a spec the agent finds hard."""
    with pytest.raises(ScopeProposalRefused, match="already inside touches"):
        validate_scope_proposal(
            _proposal(proposed_touches=[TOUCHES[0]]), touches=TOUCHES
        )


def test_a_bugs_empty_touches_always_escapes():
    """A bug with no ratified touches yet has nothing to be outside of."""
    proposal = validate_scope_proposal(_proposal(proposed_touches=["a.py"]), touches=[])
    assert proposal.proposed_touches == ["a.py"]


def test_a_proposal_naming_no_paths_is_refused():
    with pytest.raises(ScopeProposalRefused, match="no paths"):
        validate_scope_proposal(_proposal(proposed_touches=[]), touches=TOUCHES)


def test_a_proposal_with_no_root_cause_is_refused():
    with pytest.raises(ScopeProposalRefused, match="no root cause"):
        validate_scope_proposal(_proposal(root_cause="  "), touches=TOUCHES)


def test_a_malformed_proposal_is_a_schema_failure():
    with pytest.raises(ScopeProposalNotSchema, match="not the schema"):
        validate_scope_proposal(
            '<output>{"kind": "scope_proposal"}</output>', touches=TOUCHES
        )


@pytest.mark.parametrize(
    "path", ["", "   ", "..", "docs/../../etc/passwd", "/etc/passwd", "*", "**"]
)
def test_a_proposal_naming_a_malformed_path_is_refused(path):
    """Path hygiene, which the inside-`touches` rule cannot supply: junk is
    *outside* `touches`, so the escape-hatch guard reads it as a real escape and
    any hard spec can be ended on turn one with `proposed_touches: [""]`.
    `**` is the worst of them — a ratified `touches` of `**` makes the `scope`
    gate vacuous for that task forever."""
    with pytest.raises(ScopeProposalRefused, match="not a usable path"):
        validate_scope_proposal(_proposal(proposed_touches=[path]), touches=TOUCHES)


def test_a_malformed_path_refuses_the_whole_proposal():
    """Refused, not filtered: a control artifact that is partly junk is not a
    record to ratify, and silently dropping an entry would record a scope the
    model never proposed."""
    with pytest.raises(ScopeProposalRefused, match="not a usable path"):
        validate_scope_proposal(
            _proposal(proposed_touches=["saffron/cli.py", ""]), touches=TOUCHES
        )


def test_a_legitimate_glob_outside_touches_is_still_accepted():
    """The hygiene rule must not cost the ordinary case: a proposal *is* a
    `touches` set, and `touches` entries are globs."""
    proposal = validate_scope_proposal(
        _proposal(proposed_touches=["saffron/report/**"]), touches=TOUCHES
    )
    assert proposal.proposed_touches == ["saffron/report/**"]


def test_a_root_cause_of_one_token_is_refused():
    """The criterion asks for a one-paragraph root cause and the operator
    ratifies on it, so `"x"` clearing a `.strip()` check is the whole review
    surface being empty. Crude by design: this rejects a token, not a short
    sentence."""
    with pytest.raises(ScopeProposalRefused, match="root cause"):
        validate_scope_proposal(_proposal(root_cause="x"), touches=TOUCHES)
