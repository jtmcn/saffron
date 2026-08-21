from __future__ import annotations

from pathlib import Path

import pytest

from saffron.agents import context

REAL_CONTEXT_MD = (Path(__file__).parent.parent / "CONTEXT.md").read_text()

SAMPLE = """# Saffron — terminology

Preamble that belongs to nobody.

## 1. Core

**Saffron**: the orchestrator.

## 4. Verification

**Gate contract**: the interface.

## 9. Flywheel

**Bucket**: one of three.

## Trailing notes

Not a numbered section — a boundary, never a payload.
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


def test_the_declared_paths_all_reach_the_prompt():
    """The whole defect: the agent is judged against frontmatter it never saw."""
    out = context.build_system_prompt(
        "IMPLEMENT",
        SAMPLE,
        template="{vocabulary}\n\n{constraints}\n\n{spec}",
        spec="do the thing",
        constraints=context.constraints_block(
            ["src/**"], ["alembic/versions/**"], ["DESIGN.md"]
        ),
    )
    assert "- `src/**`" in out
    assert "- `alembic/versions/**`" in out
    assert "- `DESIGN.md`" in out


def test_a_spec_declaring_no_forbidden_gets_no_forbidden_heading():
    """An empty heading reads as withheld and invites an invented list."""
    out = context.constraints_block(["src/**"], [], ["DESIGN.md"])
    assert "forbidden" not in out
    # No dangling blank section where the forbidden list would have gone.
    assert out.endswith("- `DESIGN.md`")


def test_a_declared_path_containing_a_brace_is_not_expanded():
    """Same rule as the spec body: frontmatter is a value, never a template."""
    out = context.build_system_prompt(
        "IMPLEMENT",
        SAMPLE,
        template="{vocabulary}\n\n{constraints}\n\n{spec}",
        spec="do the thing",
        constraints=context.constraints_block(["src/{vocabulary}/**"], [], []),
    )
    assert "- `src/{vocabulary}/**`" in out


def test_a_trailing_non_numbered_heading_is_a_boundary_not_a_payload():
    """The last numbered section must not swallow a trailing '## ...' heading."""
    out = context.sections_for("IMPLEMENT", SAMPLE, sections=(9,))
    assert "one of three" in out
    assert "Not a numbered section" not in out


def test_real_context_md_never_leaks_settled_or_open_naming_decisions():
    """These trailing headings follow §10 and aren't numbered — regression for
    the over-capture bug where the last matched section swallowed everything
    to the end of the document."""
    for phase in context.SECTIONS_BY_PHASE:
        out = context.sections_for(phase, REAL_CONTEXT_MD)
        assert "Settled naming decisions" not in out
        assert "Open naming decisions" not in out


def test_a_template_missing_the_spec_placeholder_raises():
    """A prompt template with no {spec} is a bug in the template file, not a
    prompt with nothing to say — it must not silently drop the spec."""
    with pytest.raises(ValueError, match="spec"):
        context.build_system_prompt(
            "IMPLEMENT",
            SAMPLE,
            template="Vocabulary:\n{vocabulary}\n\nNo task placeholder here.",
            spec="This text has nowhere to go.",
        )


def test_a_template_with_spec_twice_gets_the_same_literal_text_both_times():
    out = context.build_system_prompt(
        "IMPLEMENT",
        SAMPLE,
        template="First:\n{spec}\n\nSecond:\n{spec}",
        spec="Use {{cookiecutter.name}} literally.",
    )
    assert out.count("Use {{cookiecutter.name}} literally.") == 2
