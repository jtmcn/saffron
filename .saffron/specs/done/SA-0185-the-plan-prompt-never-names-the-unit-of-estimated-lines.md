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
estimated_lines: 152
acceptance:
  - claim: >-
      In the IMPLEMENT system prompt that `build_system_prompt` assembles from
      the real `implement.md` and `CONTEXT.md`, the bullet defining the plan's
      `estimated_lines` field says four things. It is read case-insensitively,
      sentence by sentence, with the field's own name removed. The first
      sentence holds "changed lines", or both "added" and "removed", and
      holds "line" and never "token". One sentence holds the `size` gate, the
      number `_TOKENS_PER_LINE` holds as digits, and "token" before its first
      "line". One sentence holds "divid" and "token", and "line" after that
      number. At least one sentence holds "reject". Each such sentence either
      puts "only" after "reject" and before a `size` that blocks, or pairs
      "not" before "reject" with a `size` that does not block. The bullet runs
      from its own first line to the line before the next bullet or blank
      line.
    witness: tests/test_context.py::test_the_plan_field_says_estimated_lines_counts_lines_not_tokens
  - claim: >-
      `run_task` hands the cell a spec body made of the spec's own body,
      unchanged, followed by a section that starts and ends with a newline.
      Read case-insensitively, the section holds the spec's declared
      `estimated_lines` followed by "lines", "line" or "changed lines", and
      never followed by "tokens". The sentence holding that number also
      holds "estimat". A spec declaring no `estimated_lines` reaches the cell
      with its own body alone. The witness drives the declared values 37 and
      1210, and one spec declaring none.
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
`PLAN_REJECTED` at $1.44. Those three figures are the item's own
(`docs/backlog/b-efdf1f-plan-read-a-specs-token-count-as-lines-so-the-checkpoint-priced-it-four-times-over.md:21-24`),
and 8400 is 2100 times 4. The whole change later measured 2094 tokens, well
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
  so they see the appended section too. No lens prompt changes. The
  end-of-stack review reads the intake spec's body
  (`saffron/end_review.py:288`), and PACKAGE reads the intake spec too, so
  neither sees it. `spec_sha` is hashed from the file and does not move.
- **`judge_estimate`, the ceilings and `_TOKENS_PER_LINE`.** The pricing
  stays as it is.
- **The design record's size paragraph.** The operator amends it by hand
  in this spec's own pull request (§3.2). The amendment says the
  estimate joins the spec body, and IMPLEMENT, REVIEW and REBUT all read it.
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
fields. Its first sentence defines the field as changed lines, added plus
removed, and names no tokens. A later sentence says the unit is never
tokens. The `size` gate counts about 4 changed tokens a line, and the host
multiplies the estimate by that rate before it compares with the ceiling.
A size a spec states in tokens is divided by 4 to give lines. A plan over
the ceiling is rejected only where `size` blocks
(`saffron/agents/artifacts.py:319-336`). The existing sentence says it is
rejected with no such limit. Write the rate as the digit, since the
witness reads `_TOKENS_PER_LINE`. Keep every added line inside the bullet,
indented like its first line, with no blank line before the next bullet.

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
takes. Call the number an estimate in the sentence that holds it, so it
never reads as a cap. Start and end that section with a newline. REVIEW and REBUT append
`criteria_section` straight after the body
(`saffron/cell/session.py:2656`, `saffron/cell/session.py:2850`). That
section opens with its heading and no newline
(`saffron/agents/context.py:129-131`). A section with no final newline
glues that heading onto its last line. In `run_task`, append its result to the spec body that the
`body` keyword passes (`saffron/task.py:367`). Import `context` from
`saffron.agents` at module scope in `saffron/task.py`.

**The witnesses.** Put the first in `tests/test_context.py`, beside
`test_the_implement_prompt_never_calls_scope_proposal_diagnose_only`
(`tests/test_context.py:314`). Build the prompt with
`_assembled_implement_prompt` (`tests/test_context.py:258-275`). Find the
line whose stripped text starts with the backticked field name after a
bullet dash. Take it and each following line up to the next bullet or
blank line. Join the stripped lines with spaces, lower-case the text,
remove the backticked field name, and split it into sentences after each
full stop. Match `saffron.gates.core.size._TOKENS_PER_LINE`'s value as a
whole number. Then assert four things.

- The first sentence matches `changed` then whitespace then `line`, or
  holds both `added` and `removed`. It holds `line` and no `token`.
- Some sentence holds the backticked `size` and the value, and its first
  `token` comes before its first `line`.
- Some sentence holds `divid` and `token`, and matches the value followed
  later by a whole-word `line`.
- At least one sentence holds `reject`. Each one matches `reject`, later a
  whole-word `only`, later the backticked `size`, later `block`, and has no
  backticked `size` followed by `not block` or `does not block`. Or it
  matches `not` then whitespace, an optional `be`, then `reject`, and has a
  backticked `size` followed by `not block` or `does not block`.

Put the second in `tests/test_task.py`, after
`test_a_handoff_replaces_the_stacking_resolver`. Replace `run_one_cell`
with a double that records `cell_spec.body`, as that test does
(`tests/test_task.py:527-536`). Stub the push with `_push`
(`tests/test_task.py:93-94`). Call `run_task` three times with an intake
`Spec` whose `body` you pass, declaring 37, then 1210, then nothing. For
none, assert the body equals the one you passed. For each declared value,
assert the body starts with the one you passed and ends with a newline.
Take the text after the one you passed. Assert it starts with a newline.
Assert it matches the value as a whole number, then non-word characters,
then an optional `changed`, then `line` or `lines` as a whole word. Assert
it has no match for the value followed by optional spaces and `tokens`.
Match both case-insensitively. Split that text into sentences after each
full stop and at each newline. Assert some sentence holds the value as a
whole number and holds `estimat`. Import nothing the change adds at module scope in
either test file. A missing name at collection makes the reverted run an
error, and `revert` reads that as `skip`.

**Wrong and right versions, measured.** The author ran each against a
prototype of both witnesses, the first built on
`_assembled_implement_prompt`. You need not run them. These bullets must
pass, and each did:

- The prototype's bullet, and the same bullet capitalising "Changed Lines"
  and "Tokens".
- A bullet reading "your best guess at changed lines, added plus removed,
  across the whole diff". It goes on to say `size` counts about 4 changed
  tokens a line and the host multiplies the estimate by 4. It says a size
  in tokens is divided by 4 to give lines. It ends that a plan over the
  ceiling is rejected only where `size` blocks, and elsewhere stands.
- The division sentence as "Divide a size stated in tokens by 4 to get
  lines."
- The rejection sentence as "Where `size` does not block, a plan over the
  ceiling is not rejected."

Each of these failed its witness:

- `implement.md` unchanged.
- A bullet asking for the size in tokens, which the host divides by 4.
- A division sentence turning lines into tokens.
- The rejection sentence left as it stands, or saying a plan is rejected
  even where `size` does not block.
- A first sentence defining the field in tokens.
- A first sentence reading "the number of lines in the files you change".
- A first sentence reading "changed lines, added plus removed, never
  tokens".
- The rate given as "4 lines per token".
- The guidance added to `turns/plan.md` alone.
- The guidance moved to its own paragraph, or to a new bullet after the
  field's.
- The rate written as the word "four".
- The division sentence left out.
- Every mention of tokens left out.
- No text appended to the body.
- The estimate stated as tokens, 4 times the declared value, with no line
  unit.
- The declared value in tokens, with lines in brackets after it.
- The declared value followed by "changed tokens".
- A section with no final newline, or none at its start.
- A section appended for a spec declaring none.
- The section put before the spec body, or in place of it.
- A section appended only above some threshold.
- A fixed number in place of the declared one.
- A section saying "The plan must stay within 37 lines", with "estimate"
  only in its heading or in another sentence.

**Size.** A `bug` gets 1300 changed tokens. The author's prototype
measured 607 with `size`'s own counter over the five files, at base
`853d3012`. That is about 152 lines at 4 tokens a line, the figure
`estimated_lines` declares, with no allowance added.

**Another spec edits `saffron/task.py`.** `SA-0186` touches it too. This
spec declares no `depends_on` on it, and the operator orders the two
cells.

**Commit** the bullet and its witness first, then the helper, the call and
theirs.
