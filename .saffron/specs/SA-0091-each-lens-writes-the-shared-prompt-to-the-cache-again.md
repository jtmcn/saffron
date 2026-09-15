---
id: SA-0091
title: every REVIEW lens writes the same vocabulary, standing instructions, gate table, diff and task to the prompt cache again, because its own remit comes first
type: feature
priority: 3
depends_on: []
touches:
  - saffron/agents/prompts/review-correctness.md
  - saffron/agents/prompts/review-contract.md
  - saffron/agents/prompts/review-adequacy.md
  - tests/test_review.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/agents/context.py
  - saffron/agents/artifacts.py
  - saffron/agents/findings.py
  - saffron/agents/prompts/implement.md
  - saffron/agents/prompts/rebut-verdict.md
  - saffron/phases/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/report/**
  - saffron/task.py
  - saffron/cli.py
  - saffron/batch.py
budget_usd: 5
max_attempts: 3
max_turns: 40
acceptance:
  - claim: >-
      The three lens system prompts built for one task are identical from
      their first character through the vocabulary, the repo's standing
      instructions, the gate table, the diff and the task, and differ only
      after all five. Today they differ from the first sentence, so every lens
      writes the text they share to the prompt cache again instead of reading
      what the lens before it wrote.
    witness: tests/test_review.py::test_the_lens_prompts_share_every_substituted_block_as_one_prefix
  - claim: >-
      Each lens still declares its own remit and names the other lenses' remits
      as not its own, so no two lenses claim the same defect class, as today.
    witness: tests/test_review.py::test_the_lenses_declare_disjoint_remits
    preserves: true
---

## Context

Found 2026-09-14 while checking REVIEW against the prompt-cache advice in
`keli-wen/agentic-harness-patterns-skill`: sibling sessions should share a
byte-identical prompt prefix, so each one reads what the one before it wrote.

`run_review` (`saffron/phases/review.py`) runs the three lenses one after
another, each a fresh session with the same `REVIEW_TOOLS`. Each system prompt
is `lens_prompt`'s render of the lens's own template. All three templates open
with one lens-specific sentence of about 360 characters and only then reach
`{vocabulary}`, `{standing_instructions}`, `{gates}`, `{diff}` and `{spec}`.
Those five values are identical across the three lenses of one task. On this
repo, measured 2026-09-14, the vocabulary sections are about 5,400 tokens and
`CLAUDE.md` about 3,100, before the diff and the task.

A prompt cache matches from the first byte, so today the lenses share only the
tool definitions. `agent_options` sets the one-hour TTL on every session
(`saffron/phases/implement.py`), and a one-hour cache write is priced at twice
base input where a read is a tenth of it. So each lens pays the top rate to
write text the lens before it had just written. That is reasoned from the
pricing, not measured. `SA-0090` records the counts that measure it.

Anthropic's long-context guidance puts long documents above the instructions
that refer to them. The order this spec asks for is that order.

**This pull request is not ratified on a green review.** A lens prompt is its
remit, and moving its instructions below 10,000 tokens of shared text can change
what it finds. Before `gh pr ready`, the operator runs the lens-scoring driver
(`docs/evidence/scripts/2026-09-07-lens-scoring.py`) on the base and on this
branch and compares **seen** and **graded** per lens. After `SA-0090`'s runner
is in the base image, the operator also reads one night's event log for the
second and third lens's cache reads. A cell cannot run either check.

## Problem

The part of the lens prompt that is the same for every lens is placed after the
part that differs, so it can never be read from the cache.

## Out of scope

**The verdict template.** `rebut-verdict.md` has the same shape, with the
per-lens blockers and rebuttal above the diff. `SA-0092` edits that file, and
the same move there is a later spec.

**The one-hour TTL on lens sessions.** With a shared prefix, the third lens
starts minutes after the first wrote the cache, which is what the longer TTL is
for. Whether to keep it on lens sessions is settled with `SA-0090`'s numbers.

**`build_system_prompt` and `lens_prompt`.** Both already substitute each value
wherever the template places it, `{spec}` included. The change is to the
templates.

## Notes for the agent

**The first criterion carries a witness and no mutant; the second is
`preserves`.** A template reordering has no single line a mutant could pin.
`witness` will report `skip` on the first, and that is expected.

**Move the shared blocks up rather than the instructions down.** It is the
smaller diff: the five blocks and their headings, from wherever each template
has them to the top, in the same order in all three. The headings above them
must be the same bytes in all three files too, or the prefix ends at the first
heading that differs.

**Fix every sentence that points at the moved text.** Each template says "the
diff below" in its "What to emit" section, and each opens by saying what is in
the prompt. Read all three for anything that locates a block, and make it true
of the new order. Keep each lens's first sentence, the one naming it as a
critic; it moves below the shared blocks, it is not deleted.

**Build the witness's prompts with every block non-empty.** A repo with no
`CLAUDE.md` renders `{standing_instructions}` as nothing, which would let a
test pass without that block being in the shared prefix at all. Pass a
`claude_md`, a gate table, the module's `DIFF` and a spec body, render all three
lenses with `review.lens_prompt`, and assert that the common prefix of the three
contains each of the five. Reverted, the common prefix ends a few words into the
first sentence, so an honest test fails there.

**Every existing test in `tests/test_review.py` must still pass.** Several
assert the framing sentences and the `<output>` field names in each prompt, so
they check that you moved text and did not drop it.

**The `size` gate counts tests.** A `feature` gets 600 changed lines, tests
included.
