---
id: SA-0173
title: A stack batch holds nothing back for its follow-up writer, and calls none
type: feature
priority: 1
depends_on: [SA-0161]
touches:
  - saffron/batch.py
  - tests/test_batch.py
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
  - saffron/cli.py
  - saffron/follow_up.py
  - saffron/task.py
  - saffron/ledger.py
  - saffron/spec_review.py
  - saffron/end_review.py
  - saffron/scheduler.py
  - saffron/record/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - tests/test_cli.py
  - tests/test_follow_up.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_spec_review.py
budget_usd: 16
max_attempts: 3
max_turns: 100
acceptance:
  - claim: >-
      `run_stack_batch` takes `writer_usd`, 0 by default, and holds it back
      beside `reserve_usd`. It holds it back from each generation-0 budget
      comparison, and from the check before each revision round. Given
      `follow_ups` and `end_review`, it calls `follow_ups` once, after
      `end_review`, with the batch's key and what `end_review` returned. It
      discards the return, and none of its candidates reaches the runner.
      It never calls `follow_ups` without `end_review`, nor after a raise
      out of the loop. The share is held whether or not `follow_ups` is
      given. The witness drives a task the share alone stops, with
      `follow_ups` and without. It drives a revision the share alone
      refuses, and a second round the share alone refuses after a first it
      admits.
    witness: tests/test_batch.py::test_a_stack_batch_hands_its_end_review_to_follow_ups_and_holds_the_writer_share
  - claim: >-
      `run_batch` still holds nothing back from its budget comparison.
    witness: tests/test_batch.py::test_the_budget_gate_is_one_comparison_before_each_task
    preserves: true
  - claim: >-
      `run_batch` still runs the next task after one that overshot its own
      budget, while the batch's budget less its spend covers it.
    witness: tests/test_batch.py::test_a_task_overshooting_its_own_budget_does_not_stop_the_batch
    preserves: true
---

## Context

Backlog item **b-792ab2**, step 7 of its Done. It cites `DESIGN.md` §4.2.1
and §5.5. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides that qualified end-review findings become follow-up specs, one
generation deep. The **Money** paragraph of section 3 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md` gives the writer
a sub-cap of its own.

**This spec is the second of three for follow-up writing.** `SA-0161`
builds `follow_up.write_follow_ups` and `WRITER_SHARE`. This spec adds the
two `run_stack_batch` keywords it needs. `SA-0165` passes both from
`saffron batch --stack`, with `writer_usd` of `--budget` times
`WRITER_SHARE`. It split from `SA-0161` to keep that spec's size under
the margin.

**What the tree base holds.** This spec's tree base is `SA-0161`'s head.
The chain puts these names there, so they are cited by symbol. Every line
number below was read at `f2a08a9f`, where none of them exist.

- `SA-0143`: `run_stack_batch` in `saffron/batch.py`. It takes the order,
  the ledger, the budget, `until` and a runner, and the keywords
  `run_batch` takes. Its runner takes a candidate and its predecessor.
- `SA-0153`: `reserve_usd` and `end_review`. The task loop holds the
  reserve back from each budget comparison. `end_review` runs once after
  the loop returns, with the batch's id as text, the reserve and each spec
  of the order by its id. `run_stack_batch` calls it and discards the
  return. A raise out of the loop propagates, and `end_review` does not
  run.
- `SA-0154`: `end_review.StackReview`.
- `SA-0149`, `SA-0155` and `SA-0164`: the `review`, `mint` and `revise`
  keywords. Before each revision round, `SA-0164` checks the budget left:
  the budget less one held amount and `batch_spend`. It computes that
  amount where the task loop computes its own, and it is `reserve_usd`. A
  shortfall returns a `Refused` with an ` unrevised  ` line, and `revise`
  is not called.

**What the base holds.** `run_batch` compares each candidate's
`budget_usd` with the budget less the batch's spend
(`saffron/batch.py:194-195`). `tests/test_batch.py` has `_candidate`,
`_outcome` and `_spend` (`:34-75`).

## Problem

1. **`writer_usd: float = 0.0`.** Add it to the held amount, so both the
   task loop and `SA-0164`'s pre-revision check subtract it beside
   `reserve_usd`. Generation 1 releases both reserves in `SA-0162`, so it
   is out of scope here.
2. **`follow_ups`, `None` by default.** It takes the batch's key and the
   `StackReview`, and returns a list of `Candidate`s. `run_stack_batch`
   calls it once, right after `end_review`, when both are given. It calls
   it and discards the return. Import `StackReview` under `TYPE_CHECKING`
   alone, since `saffron/batch.py` builds none.

## Out of scope

- **Running the follow-ups.** `SA-0162` appends the list on top, releases
  both reserves for generation 1, and moves the batch row's close after
  them.
- **The wiring.** `SA-0165` passes `follow_ups` and `writer_usd`, and its
  callable catches every raise, so `follow_ups` never raises in
  production. A raise here propagates.
- **The batch row's spend.** It closes before the end review (`SA-0153`),
  so its stored spend lacks the writer's.

## Notes for the agent

**Criterion 1 edits `run_stack_batch`**, whose text is not at `f2a08a9f`,
so no `find` can be pinned there. It declares a witness and no mutant, and
`witness` reports `skip` for it. Criteria 2 and 3 are `preserves`, and
name tests that pass now.

**Criterion 1's witness** follows `_candidate`, `_outcome` and `_spend`.
The runner makes a run, a task and an attempt of 0.5, and returns
`READY_FOR_REVIEW` on that task and run. `end_review` and `follow_ups`
record their calls, and `follow_ups` returns one more candidate.

- The order is `SY-1` at a budget of 12 and `SY-2` at 12.25. The budget is
  20, `reserve_usd` 3 and `writer_usd` 4.5. It asserts `BUDGET`, one runner
  call for `SY-1`, then `end_review` and `follow_ups` in that order. Each
  got the batch's key, and `follow_ups` got `end_review`'s return.
- A batch with `follow_ups` and no `end_review` calls no `follow_ups`. A
  readiness check that raises propagates, and calls neither.
- `SY-4` alone at a budget of 12.75, with budget 20, `reserve_usd` 3,
  `writer_usd` 4.5, and neither `end_review` nor `follow_ups`. It stops
  `BUDGET` and never reaches the runner.
- Let `need` be `SPEC_WRITER_SESSION_USD`, `SPEC_REVIEW_BUDGET_USD` and 12
  together. One spec `SY-3` at a budget of 12 runs with a budget of
  `3 + need + 2` and `reserve_usd` 3. Every review of it blocks with one
  `build` blocker, as `SA-0164`'s arrangement scripts it, and costs
  nothing. Each `revise` records one attempt at 1.0 on a run in the batch.
  - With `writer_usd` 4.0, and no `end_review` or `follow_ups`, `revise` is
    never called. The first round's check leaves `need` less 2.
  - With `writer_usd` 1.5, and both `end_review` and `follow_ups` passed,
    `revise` is called once. The first round leaves `need` plus 0.5. The
    second review blocks again, and its round leaves `need` less 0.5.

These fail it, each measured on a stand-in:

- `writer_usd` not held back in the task loop, or held in place of the
  reserve
- `writer_usd` not held back before a revision, or held back twice there
- `writer_usd` held back only beside a `follow_ups`, in the task loop or
  before a revision
- `follow_ups` called before `end_review`, or with no stack
- `follow_ups` called with no `end_review`
- a follow-up passed to the runner

**How the list was measured.** A throwaway prototype ran on 2026-09-24. It
stood in for `run_stack_batch`, with `SA-0153`'s reserve and `SA-0164`'s
pre-revision check as their specs state them. The right build passed.
Each wrong version was applied as a text edit, and each failed the
witness. The chain's own `run_stack_batch` is not at `f2a08a9f`, so the
list ran on the stand-in alone.

**The `prose` gate** reads every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense, a hedge or a
sentence over 25 words.

**Size.** No path here is in `elevate_on`, so `size` is advisory at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). The
prototype measured 275 changed tokens with `size_gate` itself:
`saffron/batch.py` 53 and `tests/test_batch.py` 222.
