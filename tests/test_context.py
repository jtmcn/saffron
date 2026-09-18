from __future__ import annotations

import re
from pathlib import Path

import pytest

from saffron.agents import artifacts, context
from saffron.phases import implement, rebut, review

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


def test_the_declared_witnesses_reach_the_prompt_verbatim():
    """They are exact strings the implementer has to name its tests. A gate
    that blocks on a target the agent was never shown burns every attempt for
    a reason no repair turn can diagnose."""
    from saffron.intake import Criterion

    block = context.witnesses_block(
        [
            Criterion(claim="the box ticks", witness="tests/test_criteria.py::test_a"),
            Criterion(
                claim="nothing broke",
                witness="tests/test_intake.py::test_b",
                preserves=True,
            ),
        ]
    )
    assert "tests/test_criteria.py::test_a" in block
    assert "tests/test_intake.py::test_b" in block
    assert "the box ticks" in block
    assert "preserves" in block


def test_a_spec_declaring_no_witnesses_gets_no_witness_heading():
    """A heading over nothing reads as withheld and invites an invented list —
    `constraints_block`'s own rule, and a default witness is exactly the defect
    SA-0011 exists to close."""
    assert context.witnesses_block([]) == ""


def test_criteria_section_round_trips_through_intakes_own_parser():
    """Finding 1, PR #48 review: intake requires the markdown `## Acceptance
    criteria` section absent when `acceptance:` is declared, so a witnessed
    spec's claims live only in frontmatter, which only the IMPLEMENT prompt
    reads. `criteria_section` restores what the critic loses — the same shape
    `intake._acceptance_criteria` parses out of a markdown spec, pinned by
    parsing this function's own output with it."""
    from saffron import intake
    from saffron.intake import Criterion

    acceptance = [
        Criterion(claim="the box ticks", witness="tests/test_criteria.py::test_a"),
        Criterion(
            claim="nothing broke",
            witness="tests/test_intake.py::test_b",
            preserves=True,
        ),
    ]
    section = context.criteria_section(acceptance)
    assert intake._acceptance_criteria(section) == ["the box ticks", "nothing broke"]
    # Claims only — the witness name and the naming instruction are
    # `witnesses_block`'s remit, aimed at the implementer, not the critic.
    assert "tests/test_criteria.py::test_a" not in section


def test_criteria_section_is_empty_for_no_acceptance():
    assert context.criteria_section([]) == ""


def _assembled_implement_prompt() -> str:
    """The IMPLEMENT system prompt as `session.py` assembles it (DESIGN.md §5.3).

    The real `CONTEXT.md` through the real template, because the defect this
    guards was invisible in either half alone: the template offers the scope
    proposal, the vocabulary said proposing was DIAGNOSE's job, and only the
    assembled string carries both.
    """
    root = Path(__file__).parent.parent
    return context.build_system_prompt(
        "IMPLEMENT",
        (root / "CONTEXT.md").read_text(),
        template=(root / "saffron/agents/prompts/implement.md").read_text(),
        spec="(the task body)",
        constraints=context.constraints_block(["src/**"], [], []),
        witnesses="",
        standing_instructions="",
    )


def test_claude_md_reaches_the_implement_prompt_verbatim():
    root = Path(__file__).parent.parent
    rules = "- Never collapse `error` into `fail`.\n- A literal {vocabulary} stays literal.\n"
    prompt = context.build_system_prompt(
        "IMPLEMENT",
        (root / "CONTEXT.md").read_text(),
        template=(root / "saffron/agents/prompts/implement.md").read_text(),
        spec="(the task body)",
        constraints="",
        witnesses="",
        standing_instructions=context.standing_instructions(rules),
    )
    assert "## This repository's standing instructions" in prompt
    assert "- Never collapse `error` into `fail`." in prompt
    assert "A literal {vocabulary} stays literal." in prompt


@pytest.mark.parametrize("absent", [None, "", "  \n\n"])
def test_a_repo_with_no_claude_md_gets_no_standing_instructions_heading(absent):
    assert context.standing_instructions(absent) == ""


def _definition(prompt: str, term: str) -> str:
    """One term's paragraph, delimited the way the model reads it."""
    marker = f"**{term}**"
    start = prompt.find(marker)
    assert start != -1, f"{marker} is not in the assembled prompt at all"
    return prompt[start:].split("\n\n", 1)[0]


def test_the_implement_prompt_offers_the_scope_proposal_door():
    """The premise of the test below: without the door there is no contradiction."""
    assert "scope_proposal" in _assembled_implement_prompt()


def test_the_implement_prompt_never_calls_scope_proposal_diagnose_only():
    """The defect is what reaches the model, so that is what this reads.

    The same prompt offered any IMPLEMENT attempt the scope-proposal door and
    told it, in §3's `Touches` entry, that proposing is DIAGNOSE's job on bug
    specs. The stale half wins that argument by being the specific one.
    """
    touches = _definition(_assembled_implement_prompt(), "Touches")
    assert "propose" in touches.lower(), "the entry no longer describes proposal"
    assert "IMPLEMENT" in touches, (
        "the IMPLEMENT prompt names DIAGNOSE as the only proposer of `touches` "
        f"while offering the implementer the same door: {touches!r}"
    )
    # Naming IMPLEMENT is not enough on its own: "IMPLEMENT never proposes
    # scope" satisfies the assertion above and reinstates the defect.
    assert "on bug specs" not in touches, (
        "the plural confines proposal to a spec type again, which is the "
        f"restriction this test exists to keep out of the prompt: {touches!r}"
    )


_PROMPTS = context.PROMPTS_DIR


@pytest.mark.parametrize(
    ("source", "field", "table"),
    [
        ("review-correctness.md", "claim", "findings"),
        ("review-contract.md", "claim", "findings"),
        ("review-adequacy.md", "claim", "findings"),
        ("rebut-verdict.md", "reason", "disagreements"),
        ("turns/rebut-extract.md", "argument", "disagreements"),
    ],
)
def test_prose_bound_for_the_pr_body_is_asked_for_in_plain_language(
    source, field, table
):
    """Each of these fields is a cell of a table in the PR body.

    `pr_body.py` prints `claim` in `### Findings` and prints `reason` and
    `argument` in `### Disagreements`, so the table a prompt names is a fact
    about the report and not a turn of phrase.
    """
    flat = " ".join((_PROMPTS / source).read_text().split())
    assert f"A person reads your `{field}`" in flat or (
        f"A person reads each `{field}`" in flat
    )
    assert f"the pull request's {table} table" in flat
    assert "plain, specific language and state each fact once" in flat
    # A recipe, not a prohibition list: a trailing "no X, no Y" measurably
    # produces more of what it bans, so the ban must not come back (item 162).
    assert "no analogies" not in flat


# Every turn prompt, and the constant that loads it. A name here and no file on
# disk is a prompt nothing can serve; a file here and no name is dead prose.
TURN_PROMPTS = {
    "plan": implement.PLAN_PROMPT,
    "implement": implement.IMPLEMENT_PROMPT,
    "salvage": implement.SALVAGE_PROMPT,
    "review": review.REVIEW_PROMPT,
    "rebut": rebut.REBUT_PROMPT,
    "rebut-extract": rebut.EXTRACT_PROMPT,
    "verdict": rebut.VERDICT_TURN_PROMPT,
    "notes": artifacts.NOTES_PROMPT,
    "extraction": artifacts.EXTRACTION_PROMPT,
}


def test_every_turn_prompt_file_is_loaded_by_something():
    """A file nothing loads is prose the gate counts and no cell ever reads."""
    assert {path.stem for path in context.TURNS_DIR.glob("*.md")} == set(TURN_PROMPTS)


@pytest.mark.parametrize(("name", "constant"), sorted(TURN_PROMPTS.items()))
def test_a_turn_prompt_constant_is_its_file(name, constant):
    assert constant == context.turn_prompt(name)


@pytest.mark.parametrize("name", sorted(TURN_PROMPTS))
def test_a_loaded_turn_prompt_keeps_no_unfilled_slot(name):
    """`{extraction}` is filled at load. Only `rebut` carries a runtime slot."""
    rendered = context.turn_prompt(name)
    assert re.findall(r"\{[a-z_]+\}", rendered) == (
        ["{blockers}"] if name == "rebut" else []
    )


@pytest.mark.parametrize(
    "name", ["plan", "review", "verdict", "rebut-extract", "notes"]
)
def test_a_prompt_declaring_the_slot_gets_the_extraction_rules(name):
    assert context.turn_prompt("extraction") in context.turn_prompt(name)


def test_the_rebuttal_prompt_still_formats_its_blockers():
    """Filling `{extraction}` with `str.format` would consume this slot too."""
    filled = rebut.REBUT_PROMPT.format(blockers="1. [lens] a.py:1 — a claim")
    assert "1. [lens] a.py:1 — a claim" in filled
    assert "{blockers}" not in filled


def test_the_prompt_sha_covers_every_prompt_file(tmp_path, monkeypatch):
    """The digest is over the tree as authored, so editing any prompt moves it."""
    tree = tmp_path / "prompts"
    (tree / "turns").mkdir(parents=True)
    (tree / "implement.md").write_text("system\n")
    (tree / "turns" / "plan.md").write_text("turn\n")
    monkeypatch.setattr(context, "PROMPTS_DIR", tree)

    before = context.prompt_sha()
    assert len(before) == 64

    (tree / "turns" / "plan.md").write_text("turn, edited\n")
    assert context.prompt_sha() != before


def test_the_prompt_sha_is_stable_across_calls():
    assert context.prompt_sha() == context.prompt_sha()


def test_the_prompt_sha_ignores_a_file_that_is_not_a_prompt(tmp_path, monkeypatch):
    tree = tmp_path / "prompts"
    tree.mkdir(parents=True)
    (tree / "implement.md").write_text("system\n")
    monkeypatch.setattr(context, "PROMPTS_DIR", tree)

    before = context.prompt_sha()
    (tree / "notes.txt").write_text("not a prompt\n")
    assert context.prompt_sha() == before
