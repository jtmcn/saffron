---
id: SA-0192
title: The conventions lens names no edge with the other three, and judges a repo with no CLAUDE.md against an empty section
type: feature
priority: 1
depends_on: [SA-0191]
estimated_lines: 185
touches:
  - saffron/phases/review.py
  - saffron/agents/prompts/review-conventions.md
  - saffron/agents/prompts/review-correctness.md
  - saffron/agents/prompts/review-contract.md
  - saffron/agents/prompts/review-adequacy.md
  - tests/test_review.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - records/**
  - harness/**
  - saffron/phases/rebut.py
  - saffron/end_review.py
  - saffron/qualify.py
  - saffron/cell/**
  - saffron/agents/context.py
  - saffron/agents/prompts/end-review-standards.md
  - saffron/agents/prompts/end-review-spec.md
  - saffron/agents/prompts/rebut-verdict.md
  - tests/test_end_review.py
budget_usd: 24
max_attempts: 3
max_turns: 150
acceptance:
  - claim: >-
      Each of the four lens prompts names every other lens's remit as not its
      own. The correctness, contract and adequacy prompts each end their
      Not-yours list with the conventions lens's remit. The conventions
      prompt's list sits in the section right after its remit. It names the
      other three lenses and the retired blast-radius lens, and hands a
      docstring that misstates a public interface's documented contract to
      the contract lens.
    witness: tests/test_review.py::test_the_four_lenses_declare_disjoint_remits
  - claim: >-
      For a repo with no `CLAUDE.md`, or a blank one, the conventions prompt
      says the repo declares no standing instructions and still asks it to
      judge each comment, docstring and citation. A repo with a `CLAUDE.md`
      gets its standing instructions there instead. The correctness, contract
      and adequacy prompts keep an empty section for a repo with none.
    witness: tests/test_review.py::test_the_conventions_lens_says_a_repo_without_claude_md_declares_none
  - claim: >-
      The adequacy prompt is still the only one that claims the test-adequacy
      remit.
    witness: tests/test_review.py::test_exactly_one_prompt_claims_the_test_adequacy_remit
    preserves: true
---

## Context

Backlog items **b-abeb74** and **b-17d0d5**. The first cites `DESIGN.md`
§5.5. This is the third of three specs. `SA-0191` declares the conventions
lens and its prompt, `saffron/agents/prompts/review-conventions.md`, with
no Not-yours list. ADR 8 records the decision. Every line number below was
read at `a4299786`, and the code is unchanged at `40dc7f8f`. `SA-0187`,
`SA-0190` and `SA-0191` edit `saffron/phases/review.py` and
`tests/test_review.py` before this spec runs. Find a test by its name.

**The remits are disjoint by construction.** That is why any single
blocker routes to REBUT with no vote (§5.5). Each lens prompt carries a
paragraph opening "Not yours." whose bullets name every other lens's
territory. `saffron/agents/prompts/review-correctness.md:44-61`,
`saffron/agents/prompts/review-contract.md:51-66` and
`saffron/agents/prompts/review-adequacy.md:68-83` carry one each. Each ends with an edge sentence
opening "The test at the edge". `test_the_lenses_declare_disjoint_remits`
reads the three lists (`tests/test_review.py:378-392`).

**The contract lens already owns a docstring promise.** Its remit names a
documented contract, promised in a docstring, that the diff makes untrue
(`saffron/agents/prompts/review-contract.md:43-45`). The edge the
operator set keeps that there. A docstring that misstates a public
interface's documented contract is `contract`. A comment, docstring or
citation that misstates its own code or its cited text is `conventions`.

**Blast radius is retired, and every prompt still names it.** §5.5.1 keeps
that on purpose, so the class stays suppressed rather than scattered. The
conventions list names it too.

**A repo with no standing instructions.** `lens_prompt` fills
`{standing_instructions}` with `context.standing_instructions(claude_md)`
(`saffron/phases/review.py:179-199`). That returns an empty string for no
`CLAUDE.md` or a blank one (`saffron/agents/context.py:152-159`). The
conventions prompt then tells the lens to judge against standing
instructions that are not there. Item b-17d0d5 names the defect for the
end review's Standards lens. This spec takes its second arm for the
conventions lens only, and leaves the end review's half open.

## Problem

The conventions lens names no edge with the other three, and none of them
names it. A repo with no `CLAUDE.md` gives it an empty standing-instructions
section.

1. **The conventions edges.** Insert a section headed `## Its edges` right
   after the `## Your remit` section of `review-conventions.md`. It holds
   the text under **The conventions list** in the notes, word for word.
2. **The other three lists.** Append the bullet under **The appended
   bullet** as the last bullet of the Not-yours list in
   `review-correctness.md`, `review-contract.md` and `review-adequacy.md`.
3. **The empty section.** Say `context.standing_instructions(claude_md)`
   returns an empty string. `lens_prompt` then fills the conventions
   prompt's `{standing_instructions}` slot with the block under **No
   standing instructions**. Every other lens keeps the empty string. A repo with a
   `CLAUDE.md` gets its usual block.

## Out of scope

- **The end review's Standards lens.** Its half of item b-17d0d5 stays
  open.
- **`context.standing_instructions`.** It keeps returning an empty string,
  so every other prompt is unchanged.
- **The protected text.** This spec's pull request needs none.
- **REBUT's verdict session for a conventions blocker.** For a repo with
  no `CLAUDE.md`, its standing-instructions section stays empty
  (`saffron/phases/rebut.py:280`). `rebut.py` is forbidden here. That
  gap sits next to b-17d0d5's open end-review half.

## Notes for the agent

**Neither criterion declares a mutant.** Criterion 1 is new prompt text,
and intake refuses a mutant whose text the spec body carries. Criterion 2
edits the existing `lens_prompt`, but the spec does not fix the spelling of
that edit, so no mutant can name it. The `witness` gate reports `skip` for
both. Criterion 3 is `preserves`, and names a test that passes now.

**Commit as each witness passes.**

### The conventions list

```text
Not yours. Another lens reports these, so leave them alone even when you see
them, and do not mention them in your findings:

- Whether the computation is right: timezones, boundaries, null handling,
  units, ordering. That is the correctness & data-semantics lens.
- A docstring that misstates a public interface's documented contract, and
  every other promise to something outside the change. That is the contract
  & schema lens.
- Whether a test would notice this code being wrong. That is the
  test-adequacy lens.
- What else in the repository calls the changed code, and what breaks
  downstream of it. That is the blast-radius lens.

The test at the edge: if fixing the defect means changing the comment, the
citation or the import rather than what the code does, it is yours.
```

### The appended bullet

```text
- A comment, docstring or citation that misstates its own code or the text
  it cites, or a constant or helper restated rather than imported. That is
  the conventions lens.
```

### No standing instructions

The block, as the exact string `lens_prompt` substitutes, with no trailing
newline:

```text
## This repository's standing instructions

This repository declares no standing instructions: no `CLAUDE.md` stood at this task's base commit. Judge each comment, docstring and citation against the code or text it describes.
```

### The witnesses

- **Criterion 1** is a new test beside
  `test_the_lenses_declare_disjoint_remits`, which stays under its name and
  still passes. `census` fails any test collected at base and absent at
  head (`saffron/gates/core/census.py:69-86`), so rename nothing. In the
  conventions prompt, the new test finds the first heading after
  `## Your remit`. It asserts that heading is `## Its edges`, and that
  "Not yours." comes after it. It reads each prompt's Not-yours list, from the line
  opening "Not yours." to the edge sentence. It splits the list into
  bullets, each joined on whitespace. For correctness, contract and
  adequacy, the last bullet equals the appended bullet exactly. For conventions, the bullets equal
  the four above, exactly and in order, and its edge sentence equals the
  one above. Table the rows by lens, and assert the table's keys equal
  `set(review.LENSES)`.
- **Criterion 2** compares each whole prompt for equality with
  `context.build_system_prompt` over the same template and values. Table
  seven rows. The conventions lens with `None`, with `""` and with
  `" \n\t\n"` expects the block above, blank line included. The conventions
  lens with a one-line `CLAUDE.md` expects `context.standing_instructions`
  of it. Correctness, contract and adequacy with `None` expect `""`.

At this spec's base, criterion 1 fails on the conventions prompt, which has
no Not-yours list, and criterion 2 fails on its empty section.

**Wrong versions these witnesses must kill.**

- The appended bullet added to two of the three other lists.
- The appended bullet placed first rather than last.
- A conventions list placed after the `{spec}` slot, or anywhere but the
  section after the remit.
- A conventions list that keeps the public-interface docstring for itself.
- A no-instructions block given to every lens.
- A block given for `None` and not for a blank file.
- A block that replaces a real `CLAUDE.md`.
- A block that lives in `context.standing_instructions`, which the end
  review also reads.

**The prose gate** counts every new line of a prompt. The other three
prompts carry old hits, and `prose` fails only on a hit the base lacks.
The appended bullet measured at zero. Write no new comment or docstring
with an em dash, a semicolon, a contraction, the perfect tense, a hedge or
a sentence over 25 words.

**Size.** A prototype of this change measured about 700 tokens under
`size_gate`'s counter. `estimated_lines` is that over four, with no overrun
added.
