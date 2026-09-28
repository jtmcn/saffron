---
id: SA-0185
title: The plan prompt never names the unit of `estimated_lines`, so a plan copied a spec's token count as lines and the checkpoint priced it four times over
type: bug
priority: 1
depends_on: []
touches:
  - saffron/agents/prompts/implement.md
  - saffron/agents/context.py
  - saffron/task.py
  - tests/test_context.py
  - tests/test_task.py
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
  - harness/**
  - records/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/intake.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/agents/artifacts.py
  - saffron/agents/prompts/turns/**
  - saffron/agents/prompts/criterion-probe.md
  - saffron/agents/prompts/rebut-verdict.md
  - saffron/agents/prompts/review-adequacy.md
  - saffron/agents/prompts/review-contract.md
  - saffron/agents/prompts/review-correctness.md
  - tests/test_session.py
  - tests/test_cli.py
  - tests/test_artifacts.py
  - tests/test_scheduler.py
budget_usd: 18
max_attempts: 3
max_turns: 140
estimated_lines: 141
acceptance:
  - claim: >-
      In the IMPLEMENT system prompt that `build_system_prompt` assembles from
      the real `implement.md` and `CONTEXT.md`, the bullet defining the plan's
      `estimated_lines` field names lines as its unit. The same bullet names
      tokens and the `size` gate. It carries the number `_TOKENS_PER_LINE`
      holds, written as digits. It says a size stated in tokens is divided by
      that number. The bullet runs from its own first line to the line before
      the next bullet or blank line.
    witness: tests/test_context.py::test_the_plan_field_says_estimated_lines_counts_lines_not_tokens
  - claim: >-
      `run_task` hands the cell a spec body made of the spec's own body,
      unchanged, followed by text naming the spec's declared `estimated_lines`
      as a number of lines. A spec declaring no `estimated_lines` reaches the
      cell with its own body alone. The witness drives the declared values 37
      and 1210, and one spec declaring none.
    witness: tests/test_task.py::test_run_task_hands_the_cell_the_specs_own_estimate_in_lines
---

## Context

Backlog item **b-efdf1f**, found in the spec loop's run 19. The run's
feedback names what the plan read and what the checkpoint priced
(`docs/evidence/2026-09-27-spec-loop-skill-feedback-run-19.md:44-49`).
Related items are b-43a061, which asks specs to declare `estimated_lines`,
and b-408cf5, which made the checkpoint judge at the tier `size` blocks.

A plan's `estimated_lines` is an integer greater than zero
(`saffron/agents/artifacts.py:77`). Its docstring calls it added plus removed
lines, priced at `_TOKENS_PER_LINE` tokens each
(`saffron/agents/artifacts.py:78-80`). `judge_estimate` multiplies it by
`_TOKENS_PER_LINE` and compares the product with the type's token ceiling
(`saffron/agents/artifacts.py:314-317`). It raises `PlanRejected` only at a
tier where `size_blocks` says the gate blocks
(`saffron/agents/artifacts.py:319-329`). That tier is `elevated` alone
(`saffron/gates/suite.py:212-217`). Elsewhere it returns an advisory sentence
and the plan stands (`saffron/agents/artifacts.py:331-336`).
`_TOKENS_PER_LINE` is 4 (`saffron/gates/core/size.py:39`). The `bug` ceiling
is 1300 changed tokens and the `feature` ceiling 3000
(`saffron/gates/core/size.py:26`).

The plan checkpoint calls `judge_estimate` on every accepted plan
(`saffron/cell/session.py:580-582`). The plan turn sends `PLAN_PROMPT` as a
user message under the session's options
(`saffron/cell/session.py:506-507`). The checkpoint gets those `options`
from its caller (`saffron/cell/session.py:1972-1974`). They carry the
IMPLEMENT system prompt (`saffron/cell/session.py:1943-1948`). That prompt
is `implement.md` with the spec body substituted as `{spec}`
(`saffron/cell/session.py:1928-1942`). The same call adds the declared
paths and witnesses. No other frontmatter field reaches it.

The `CellSpec` a cell runs is built in `run_task`
(`saffron/task.py:360-376`). Its body is the intake spec's own body
(`saffron/task.py:367`). Intake parses the body
as the text after the frontmatter (`saffron/intake.py:228`). So
`estimated_lines` reaches no prompt. Intake reads
that field as an optional strict positive integer
(`saffron/intake.py:170`). `driver.py check` prices it before a cell is paid
for (`.claude/skills/run-saffron-spec-loop/driver.py:1958-1976`).

`run_task` is the one module that drives a task, for `saffron cell` and
`saffron batch` alike (`CLAUDE.md`, "One module drives a task"). The same
`CellSpec.body` reaches REVIEW and REBUT as their spec text
(`saffron/cell/session.py:2655`, `saffron/cell/session.py:2850`). PACKAGE
renders the pull request body from the intake spec instead
(`saffron/task.py:403-405`).

## Problem

The field's bullet in `implement.md` says "your best guess at added +
removed lines across the whole diff"
(`saffron/agents/prompts/implement.md:26-29`). It never says what the host
does with that number. Nothing there tells the plan that `size` counts
tokens, or that a token figure is a different unit.

`SA-0169`'s spec gave its size as about 2080 tokens. Its plan wrote 2100
lines. The checkpoint priced 8400 changed tokens against the `feature`
ceiling of 3000, at `elevated`, where `size` blocks. The cell ended
`PLAN_REJECTED` at $1.44. The whole change later measured 2094 tokens, well
inside the ceiling. The refusal came from the unit, not from the size.

A spec that declares `estimated_lines` states its size in the plan's own
unit. That number reaches no prompt today, so the plan cannot use it.

## Out of scope

- **A far-off plan estimate in the plan record.** It is deferred. The
  item's third bullet asks for one, recorded beside the spec's own. It
  needs a field on the plan record in `saffron/cell/**`, which `elevate_on`
  lists.
- **A field on `CellSpec`.** The estimate travels in the body because the
  body is the one channel `run_task` fills that reaches the prompt.
  `CellSpec` lives in `saffron/cell/session.py`, and this spec forbids
  `saffron/cell/**`.
- **The prompt the body lands in.** The second witness stops at the
  `CellSpec` and drives no cell. At base the IMPLEMENT phase substitutes
  that body into the IMPLEMENT system prompt (`saffron/cell/session.py:1934`). This
  spec forbids `saffron/cell/**`, so the cell cannot change that.
- **What REVIEW and REBUT do with the estimate.** They read the same body,
  so they see the appended text too. No lens prompt changes.
- **`judge_estimate`, the ceilings and `_TOKENS_PER_LINE`.** The pricing
  stays as it is.
- **`DESIGN.md:238`.** It says only `driver.py check` reads the value.
  After this change `run_task` reads it too. `DESIGN.md` is `protected`, so
  the sentence is amended by hand in this spec's own pull request.
- **Measurement.** A diff reaching `saffron/agents/prompts/` asks for a
  measured pass (`.github/pull_request_template.md:35-38`). None is in
  scope, so the effect on plans is recorded as unmeasured.

## Notes for the agent

**Neither criterion declares a mutant.** One rewrites text and one adds a
helper. The bullet's new wording and the helper's text are
yours to spell. A mutant must match text exactly. The `witness` gate will
report `skip` for both criteria, and that is expected.

**The bullet.** Rewrite the `estimated_lines` bullet in
`saffron/agents/prompts/implement.md`, in place, inside the list of plan
fields. It says four things. The unit is changed lines, added plus
removed, never tokens. The `size` gate counts about 4 changed tokens a
line, and the host multiplies the estimate by that rate before it compares
with the ceiling. A size a spec states in tokens is divided by 4 to give
lines. The existing sentence says a plan over the ceiling is rejected.
That holds only where `size` blocks, so keep the sentence true to
`saffron/agents/artifacts.py:319-336`. Write the rate as the digit, since
the witness reads `_TOKENS_PER_LINE`. Keep every added line inside the
bullet, indented like its first line, with no blank line before the next
bullet.

**Prose rules bind `implement.md`.** The `prose` gate reaches it
(`tests/test_prose_gate.py:381-389`). Rewriting the bullet replaces its
em-dash and its semicolon, so the new text must carry neither. It takes no
contraction, perfect tense, hedge or sentence over 25 words either. Run
`python3 hooks/prose_limit.py --file saffron/agents/prompts/implement.md`
before you commit it. A prototype's first draft carried one sentence of 27
words and failed there.

**The estimate in the body.** Add a helper to `saffron/agents/context.py`
beside `criteria_section` (`saffron/agents/context.py:120-131`). It takes
the spec's `estimated_lines`, `int | None`. It returns an empty string for
`None`. Otherwise it returns a short section naming that number as the
author's estimate in changed lines, the unit the plan's `estimated_lines`
takes. In `run_task`, append its result to the spec body that the
`body` keyword passes (`saffron/task.py:367`). Import `context` from
`saffron.agents` at module scope in `saffron/task.py`.

**The witnesses.** Put the first in `tests/test_context.py`, beside
`test_the_implement_prompt_never_calls_scope_proposal_diagnose_only`
(`tests/test_context.py:314`). Build the prompt with
`_assembled_implement_prompt` (`tests/test_context.py:258-275`). Find the
line whose stripped text starts with the backticked field name after a
bullet dash. Take it and each following line up to the next bullet or
blank line. Remove the backticked field name from that text. Then assert
it holds `line`, `token`, the backticked `size` and `divid`. It also holds
`saffron.gates.core.size._TOKENS_PER_LINE`'s value as a whole number.

Put the second in `tests/test_task.py`, after
`test_a_handoff_replaces_the_stacking_resolver`. Replace `run_one_cell`
with a double that records `cell_spec.body`, as that test does
(`tests/test_task.py:527-536`). Stub the push with `_push`
(`tests/test_task.py:93-94`). Call `run_task` three times with an intake
`Spec` whose `body` you pass, declaring 37, then 1210, then nothing. For
none, assert the body equals the one you passed. For each declared value,
assert the body starts with the one you passed. Then, with the field name
removed from the text after it, assert that text holds the value as a whole
number and holds `line`. Import nothing the change adds at module scope in
either test file. A missing name at collection makes the reverted run an
error, and `revert` reads that as `skip`.

**Wrong versions the witnesses must kill.** The author ran each against a
prototype, and each failed its witness. You need not run them.

- `implement.md` unchanged.
- The guidance added to `turns/plan.md` alone.
- The guidance moved to its own paragraph, or to a new bullet after the
  field's.
- The rate written as the word "four".
- The division sentence left out.
- Every mention of tokens left out.
- No text appended to the body.
- The estimate stated as tokens, 4 times the declared value, with no line
  unit.
- A section appended for a spec declaring none.
- The section put before the spec body, or in place of it.
- A section appended only above some threshold.
- A fixed number in place of the declared one.

**Size.** A `bug` gets 1300 changed tokens. The prototype measured 402 with
`size`'s own counter over five files, about 100 lines. Allow 141 lines.

**Commit** the bullet and its witness first, then the helper, the call and
theirs.
