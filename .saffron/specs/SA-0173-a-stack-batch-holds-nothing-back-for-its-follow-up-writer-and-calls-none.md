---
id: SA-0173
title: A stack batch holds nothing back for its follow-up writer, calls none, and hands its end review a revised spec's queued text
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
max_turns: 130
estimated_lines: 129
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
      given. `end_review` still receives `reserve_usd` alone as its
      reserve. The batch row still records the whole budget it was given.
      The witness drives a task the share alone stops, with
      `follow_ups` and without. It drives a revision the share alone
      refuses, and a second round the share alone refuses after a first it
      admits.
    witness: tests/test_batch.py::test_a_stack_batch_hands_its_end_review_to_follow_ups_and_holds_the_writer_share
    wrong_versions:
      - "`writer_usd` is not held back in the task loop, or is held back there in place of `reserve_usd`."
      - "`writer_usd` is not held back before a revision round, or is held back twice there."
      - "`writer_usd` is held back only when `follow_ups` is given."
      - "`end_review` is handed `reserve_usd` plus `writer_usd` as its reserve."
      - "`run_batch` is handed `budget_usd` less `writer_usd`, so the batch row records less than its budget."
      - "`follow_ups` is called before `end_review`, or with no `end_review` given."
  - claim: >-
      `run_stack_batch` hands `end_review` each spec of the order by its id.
      A spec whose task this call minted, and whose task holds a recorded
      spec text, maps to `parse_spec` of that task's latest text in place
      of its queued `Spec`. One whose latest text `parse_spec` refuses keeps
      its queued `Spec`. Every other spec keeps its queued `Spec`. The
      witness drives a spec revised twice, a spec with no text, and a spec
      whose latest text is no spec.
    witness: tests/test_batch.py::test_a_stack_batch_hands_its_end_review_each_revised_specs_latest_text
    wrong_versions:
      - "Every spec maps to its queued `Spec`, whatever its task recorded."
      - "A revised spec maps to its queued `Spec` with only the latest body copied in."
      - "A spec revised twice maps to its first recorded text in place of its latest."
      - "The text is read through the candidate's own `task_id`, which is `None`."
      - "A `SpecError` from a latest text that is no spec propagates out of `run_stack_batch`."
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
a share of its own, `writer_usd`. It sits beside `reserve_usd`, not inside
it. The operator decided that on 2026-09-29, and the delegate amends that
paragraph by hand in the pull request that adds this spec.

**This spec is the second of three for follow-up writing.** `SA-0161`
builds `follow_up.write_follow_ups` and `WRITER_SHARE`. This spec adds the
two `run_stack_batch` keywords it needs. `SA-0165` passes both from
`saffron batch --stack`, with `writer_usd` of `--budget` times
`WRITER_SHARE`. It split from `SA-0161` to keep that spec's size under
the margin. This spec imports nothing from `saffron/follow_up.py`.

**It also hands the end review a revised spec's latest text.** A revised
spec's cell holds its base text. ADR 7 names the end-review Spec lens
among the sessions that read it. The implement prompt carries the revision. So
the Spec lens judges a revised layer rightly only against it. `SA-0153` and `SA-0154`
read each layer's body and criteria from the `specs` mapping
`run_stack_batch` hands `end_review`. That mapping holds the order's
queued `Spec`s, read at `base_sha`. `SA-0182` builds `Ledger.spec_text`
above both of them in the chain, so neither can read it. This is the
first spec above `SA-0164`, which records the revisions, to edit that
`end_review` call.

**What the base holds.** Every name below is on `origin/main` at
`3f8775f2`, and every line number was read there. This spec's tree base
is `SA-0161`'s head, which adds `saffron/follow_up.py` and its tests above it.

- `run_stack_batch` (`saffron/batch.py:360`) takes the order, the ledger,
  the budget, `until` and a runner, and the keywords `run_batch` takes.
  Its runner takes a candidate and its predecessor.
- `reserve_usd` and `end_review` (`:370-371`). `run_stack_batch` passes
  `reserve_usd` to `run_batch` (`:653`), which holds it back from each
  budget comparison (`:232-233`). `end_review` is typed
  `Callable[[str, float, Mapping[str, Spec]], object] | None`. `end_review`
  runs once the loop returns, handed the batch's id as text, the reserve
  and each spec of the order by its id (`:656-658`). The return is
  discarded. A raise out of the loop propagates, and `end_review` does
  not run.
- `StackReview` (`saffron/end_review.py:497`).
  `saffron/end_review.py` imports nothing from `saffron/batch.py`.
- The `review`, `mint` and `revise` keywords (`:376-388`). Before each
  revision round the wrapper checks the budget left, which is the budget
  less `reserve_usd` and `batch_spend` (`:565-585`). A shortfall emits an
  ` unrevised  ` line and returns a `Refused`, and `revise` is not called.
  After `revise` returns, the wrapper opens and closes one attempt on the
  spec's task, at the session's `cost_usd` (`:593-604`). It records each
  revision with `record_spec_text` (`:617-623`).
- `task_ids` (`:413`) maps each spec id to the task `mint` gave it this
  call. It is a local of `run_stack_batch` itself, so it is in scope once
  `run_batch` returns.
- `Ledger.spec_text(task_id)` (`saffron/ledger.py:1517`) returns the
  task's latest row or `None`.
- `run_task` refuses a latest text `parse_spec` refuses
  (`_recorded_spec_text`, `saffron/task.py:340`), so that spec adds no
  layer.
- `run_batch` (`saffron/batch.py:80`) compares each candidate's
  `budget_usd` with the budget less `reserve_usd` and the batch's spend
  (`:232-233`). `tests/test_batch.py` has `_candidate` (`:45`), `_outcome`
  (`:78`) and `_spend` (`:87`), and the stack helpers `_package_runner`
  (`:1752`) and `_logging_end_review` (`:1787`).

## Problem

1. **`writer_usd: float = 0.0`.** Add it to the held amount, so both the
   task loop and the pre-revision check subtract it beside `reserve_usd`.
   `end_review` still gets `reserve_usd` alone. Generation 1 releases both
   reserves in `SA-0162`, so it is out of scope here.
2. **`follow_ups`, `None` by default.** It takes the batch's key and the
   `StackReview`, and returns a list of `Candidate`s. `run_stack_batch`
   calls it once, right after `end_review`, when both are given. It calls
   it and discards the return. Import `StackReview` under `TYPE_CHECKING`
   alone, since `saffron/batch.py` builds none.
3. **The texts the end review reads.** Build `end_review`'s mapping as
   criterion 2 states. Read each minted task's text with
   `ledger.spec_text` through `task_ids` once `run_batch` returns, and
   parse it with `intake.parse_spec`. Catch `SpecError` alone. `task_ids`
   is already in `run_stack_batch`'s own scope, so nothing moves.

## Out of scope

- **Running the follow-ups.** `SA-0162` appends the list on top, releases
  both reserves for generation 1, and moves the batch row's close after
  them.
- **The wiring.** `SA-0165` passes `follow_ups` and `writer_usd`, and its
  callable catches every raise, so `follow_ups` never raises in
  production. A raise here propagates.
- **The batch row's spend.** It closes before the end review (`SA-0153`),
  so its stored spend lacks the writer's.
- **A revised spec's title and ceilings elsewhere.** Only `end_review`'s
  mapping takes the latest text. The runner reads it through `run_task`.
- **`end_review`'s declared return type and `saffron/cli.py`.** Both stay
  as they are. See the typing note below.

## Notes for the agent

**The typing path.** `end_review`'s declared return is `object`, and so is
the production callable in `saffron/cli.py`, which is forbidden here. A
`follow_ups` typed on `StackReview` cannot take that return unchanged, so
the `types` gate would flag the call. Wrap it at the call that hands it on:
`follow_ups(key, typing.cast("StackReview", end_review(...)))`. The string
form needs no runtime import, and `saffron/ledger.py:1620` already casts
that way. Leave `end_review`'s type and `saffron/cli.py` alone. This is
reasoned from the source, and `ty` did not run on it.

**Criteria 1 and 2 are new code** in `run_stack_batch`, so each declares a
witness and no mutant, and `witness` reports `skip` for each. Criteria 3
and 4 are `preserves`, and name tests that pass now. Import every new name
inside the test body.

**Criterion 1's witness** follows `_candidate`, `_outcome` and `_spend`.
The runner makes a run, a task and an attempt of 0.5, and returns
`READY_FOR_REVIEW` on that task and run. `end_review` and `follow_ups`
record their calls, and `follow_ups` returns one more candidate.

- The order is `SY-1` at a budget of 12 and `SY-2` at 12.25. The budget is
  20, `reserve_usd` 3 and `writer_usd` 4.5. `SY-1` has 12.5 left and runs.
  `SY-2` has 12 left after the 0.5 spent, and stops. It asserts `BUDGET`,
  one runner call for `SY-1`, then `end_review` and `follow_ups` in that
  order. Each got the batch's key, and `follow_ups` got `end_review`'s
  return. It asserts `end_review` got 3.0 as its reserve, with `==`. A
  build that hands it 7.5 fails there. It asserts the batch row's
  `budget_usd` is 20.0, as `tests/test_batch.py:1826` does for the reserve.
  A build that hands `run_batch` the budget less `writer_usd` records 15.5
  and fails there.
- A batch with `follow_ups` and no `end_review` calls no `follow_ups`. A
  readiness check that raises propagates, and calls neither.
- `SY-4` alone at a budget of 12.75, with budget 20, `reserve_usd` 3,
  `writer_usd` 4.5, and neither `end_review` nor `follow_ups`. It stops
  `BUDGET` and never reaches the runner.
- Let `need` be `SPEC_WRITER_SESSION_USD`, `SPEC_REVIEW_SESSION_USD` and 12
  together. One spec `SY-3` at a budget of 12 runs with a budget of
  `3 + need + 2` and `reserve_usd` 3. Every review of it blocks with one
  `build` blocker, as `SA-0164`'s arrangement scripts it, and costs
  nothing. The `mint` double creates the task on a run in the batch. The
  `revise` double returns a `SpecWriterSession` whose `cost_usd` is 1.0,
  and records no attempt itself. The wrapper's own `close_attempt` carries
  that 1.0, so each round spends it once.
  - With `writer_usd` 4.0, and no `end_review` or `follow_ups`, `revise` is
    never called. The first round's check leaves `need` less 2.
  - With `writer_usd` 1.5, and both `end_review` and `follow_ups` passed,
    `revise` is called once. The first round leaves `need` plus 0.5. The
    second review blocks again, and its round leaves `need` less 0.5.

Beyond criterion 1's `wrong_versions`, a follow-up passed to the runner
fails it too.

**How the list was measured.** A throwaway prototype ran on 2026-09-24. It
stood in for `run_stack_batch`, with `SA-0153`'s reserve and `SA-0164`'s
pre-revision check as their specs state them. The right build passed.
Each wrong version was applied as a text edit, and each failed the
witness. The reserve handed to `end_review` was not in that list. The
real `run_stack_batch` is on `origin/main` now, and the list did not run
against it. The re-review at `SA-0161`'s branch worked it by arithmetic
instead, because `writer_usd` does not exist at that base. With `need` at
38.5, each entry leaves a figure the right build does not. Each wrong
version therefore fails the witness. That is arithmetic, not a run.

**Criterion 2's witness** follows `SA-0164`'s arrangement for the
`review` and `mint` doubles. Every review returns a clean read, so no
`revise` runs. The order is `SY-1`, `SY-2` and `SY-3`, each at a budget of
1, with a batch budget of 20. The mint creates a run and a task. For
`SY-1` it records two `revision` texts on that task, at
`.saffron/specs/SY-1.md`. The first is `---`, `id: SY-1`, `title: t`,
`type: chore`, `---`, then the body `rev one`. The second, `REV_TWO`, has
the same three fields and `touches: [src/two.py]`. It declares one
criterion, whose claim is `two holds` and whose witness is
`tests/test_two.py::test_two`. Its body is `rev two`. For `SY-3` it
records one text of origin `revision`, `not a spec`, at
`.saffron/specs/SY-3.md`. The runner returns `READY_FOR_REVIEW` on the
task it is handed. `end_review` records its third argument. It asserts
that mapping's keys are the three ids. `SY-1`'s value equals
`intake.parse_spec(REV_TWO)` with `==`, and is not the queued `Spec`.
`SY-2`'s and `SY-3`'s are the queued `Spec` objects, by `is`. The
`wrong_versions` under criterion 2 were reasoned, not run. A mapping
built before the loop fails it too, since it sees no recorded text.

**What criterion 2 leaves undriven.** A batch with no `mint`. Its mapping
holds each queued `Spec`, as `SA-0153`'s criterion 4 witness asserts.
Catching `SpecError` alone is not driven either. A bare `except` passes
the witness, and so does one over `Exception`.

**The `prose` gate** reads every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense, a hedge or a
sentence over 25 words.

**Size.** No path here is in `elevate_on`, so `size` is advisory at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). The
prototype measured 275 changed tokens with `size_gate` itself:
`saffron/batch.py` 53 and `tests/test_batch.py` 222. Criterion 2 adds
about 40 in `saffron/batch.py` and 200 in its witness, unmeasured. The
cast and the reserve assertion add about 10. That is about 525, 18% of
the ceiling.
