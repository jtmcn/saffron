from __future__ import annotations

from saffron.agents import context

SAMPLE = """# Saffron — terminology

Preamble that belongs to nobody.

## 1. Core

**Saffron**: the orchestrator.

## 4. Verification

**Gate contract**: the interface.

## 9. Flywheel

**Bucket**: one of three.
"""


def test_only_the_declared_sections_are_injected():
    out = context.sections_for("IMPLEMENT", SAMPLE, sections=(1, 4))
    assert "the orchestrator" in out
    assert "the interface" in out
    assert "one of three" not in out


def test_the_preamble_is_never_injected():
    out = context.sections_for("IMPLEMENT", SAMPLE, sections=(1,))
    assert "belongs to nobody" not in out


def test_implement_gets_scope_and_verification():
    assert 3 in context.SECTIONS_BY_PHASE["IMPLEMENT"]
    assert 4 in context.SECTIONS_BY_PHASE["IMPLEMENT"]


def test_no_phase_receives_the_flywheel_or_the_merge_train():
    """Nothing inside a cell can act on either (DESIGN.md §5.3)."""
    for sections in context.SECTIONS_BY_PHASE.values():
        assert 9 not in sections
        assert 6 not in sections


def test_repair_inherits_rather_than_reinjecting():
    """REPAIR resumes a session that already has the implementer's sections."""
    assert "REPAIR" not in context.SECTIONS_BY_PHASE


def test_the_spec_body_is_substituted_not_templated():
    """Spec text is data. A spec containing {{ }} must pass through untouched."""
    out = context.build_system_prompt(
        "IMPLEMENT",
        SAMPLE,
        template="Vocabulary:\n{vocabulary}\n\nSpec:\n{spec}",
        spec="Use {{cookiecutter.name}} and `{}` literally.",
    )
    assert "{{cookiecutter.name}}" in out


def test_the_spec_body_with_a_bare_brace_never_raises():
    """A naive partition-then-format still runs .format() near an unmatched brace."""
    out = context.build_system_prompt(
        "IMPLEMENT",
        SAMPLE,
        template="Vocabulary:\n{vocabulary}\n\nSpec:\n{spec}",
        spec="An unmatched brace: {",
    )
    assert "An unmatched brace: {" in out


def test_the_spec_body_with_an_unmatched_close_brace_never_raises():
    out = context.build_system_prompt(
        "IMPLEMENT",
        SAMPLE,
        template="Vocabulary:\n{vocabulary}\n\nSpec:\n{spec}",
        spec="An unmatched brace: }",
    )
    assert "An unmatched brace: }" in out


def test_the_spec_body_with_a_vocabulary_literal_is_not_expanded():
    """A spec that literally names {vocabulary} must not be substituted."""
    out = context.build_system_prompt(
        "IMPLEMENT",
        SAMPLE,
        template="Vocabulary:\n{vocabulary}\n\nSpec:\n{spec}",
        spec="Replace the {vocabulary} placeholder in our own templating code.",
    )
    assert "Replace the {vocabulary} placeholder in our own templating code." in out
