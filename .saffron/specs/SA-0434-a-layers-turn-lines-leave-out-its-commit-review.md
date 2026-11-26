---
id: SA-0434
title: A layer's turn lines on the stack page leave out its commit review's attempts
type: bug
priority: 3
estimated_lines: 9
estimate_measured: true
touches:
  - saffron/report/stack.py
  - tests/test_stack_view.py
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
  - hooks/**
  - saffron/end_review.py
  - saffron/commit_review.py
  - saffron/spec_review.py
  - saffron/report/index.py
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/events.py
  - saffron/intake.py
  - saffron/regate.py
  - saffron/parent_versions.py
  - saffron/report/pr_body.py
  - saffron/phases/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/record/**
  - tests/test_cli.py
  - tests/test_accept_rate.py
  - tests/test_commit_review.py
  - tests/test_report.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
  - tests/test_adopt_stack_layer.py
  - tests/test_ledger_fold_task.py
  - tests/test_witness_gate.py
  - tests/test_suite.py
  - tests/test_session.py
  - tests/test_parent_versions.py
  - tests/test_regate.py
  - tests/test_record_refs.py
  - tests/test_record_routed.py
  - tests/test_record_migrate.py
  - tests/test_events.py
  - tests/test_package.py
  - tests/test_intake.py
budget_usd: 26
max_attempts: 3
max_turns: 120
acceptance:
  - claim: >-
      A layer whose task holds a closed `COMMIT_REVIEW` attempt carries a
      seventh turn line, COMMIT_REVIEW, after REBUT. Its peak is the highest
      `num_turns` among those attempts alone. It reads `COMMIT_REVIEW <peak>
      of <bound> turns`, the bound being `end_review.LENS_MAX_TURNS` read
      when the layer is built. No other line reads those attempts. The line
      reads no attempt of the six other phases the page reads. The witness
      patches the constant to 57. On TE-9 it drives
      three commit review attempts of 5, 25 and 3 turns, where every other
      phase peaks higher but SPEC_WRITING at 0. On TE-4, whose spec the page
      was not handed, it drives three of 3, 7 and 2, where SPEC_WRITING
      peaks at 9 and REPAIRING at 10, and no REVIEW attempt exists. It
      asserts both layers' seven lines whole and in order.
    witness: tests/test_stack_view.py::test_a_commit_review_reads_its_peak_beside_the_lens_bound
    wrong_versions:
      - The bound read from the spec's `max_turns`, which reads `25 of 140 turns` on TE-9.
      - The bound typed as the literal 50, which the patched constant exposes.
      - "`LENS_MAX_TURNS` imported by name, so the patched module attribute never reaches the page."
      - The bound taken from `spec_review.SPEC_REVIEW_MAX_TURNS`.
      - The bound read as `PLACEHOLDER` on a layer with no spec, which reads `7 of P turns` on TE-4.
      - The line printed in the per-turn shape, `turns, extraction turns included, <bound> each`.
      - The line reading `REVIEWING` attempts in place of its own, which reads 38 on TE-9.
      - The line labelled REVIEW rather than COMMIT_REVIEW.
      - The line placed first, before SPEC_REVIEW.
      - The line placed before REBUT.
      - The commit review attempts summed, which reads 33 on TE-9.
      - The last commit review attempt taken for the peak, which reads 3 on TE-9.
      - The first commit review attempt taken for the peak, which reads 5 on TE-9.
      - The line also reading `SPEC_REVIEW` attempts, which reads 31 on TE-9.
      - The line also reading `SPEC_WRITING` attempts, which reads 9 on TE-4.
      - The line also reading `IMPLEMENTING` attempts, which reads 50 on TE-9.
      - The line also reading `REPAIRING` attempts, which reads 27 on TE-9.
      - The line also reading `REVIEWING` attempts, which reads 38 on TE-9.
      - The line also reading `REBUTTING` attempts, which reads 45 on TE-9.
      - REVIEW reading `COMMIT_REVIEW` attempts beside its own, which reads `REVIEW 7 of P turns` on TE-4.
    covers:
      - set: the layers whose closed commit review attempts the line reads
        members:
          - member: a layer with a spec (TE-9)
            driven_by: tests/test_stack_view.py::test_a_commit_review_reads_its_peak_beside_the_lens_bound
          - member: a layer whose spec the page was not handed (TE-4)
            driven_by: The bound read as `PLACEHOLDER` on a layer with no spec, which reads `7 of P turns` on TE-4.
      - set: the commit review attempts of one layer task
        members:
          - member: the first of three
            driven_by: The first commit review attempt taken for the peak, which reads 5 on TE-9.
          - member: the peak, the second of three
            driven_by: tests/test_stack_view.py::test_a_commit_review_reads_its_peak_beside_the_lens_bound
          - member: the last of three
            driven_by: The last commit review attempt taken for the peak, which reads 3 on TE-9.
      - set: the six other phases the page reads
        members:
          - member: SPEC_REVIEW
            driven_by: The line also reading `SPEC_REVIEW` attempts, which reads 31 on TE-9.
          - member: SPEC_WRITING
            driven_by: The line also reading `SPEC_WRITING` attempts, which reads 9 on TE-4.
          - member: IMPLEMENTING
            driven_by: The line also reading `IMPLEMENTING` attempts, which reads 50 on TE-9.
          - member: REPAIRING
            driven_by: The line also reading `REPAIRING` attempts, which reads 27 on TE-9.
          - member: REVIEWING
            driven_by: The line also reading `REVIEWING` attempts, which reads 38 on TE-9.
          - member: REBUTTING
            driven_by: The line also reading `REBUTTING` attempts, which reads 45 on TE-9.
      - set: the other lines that must not read a commit review attempt
        members:
          - member: the REVIEW line
            driven_by: REVIEW reading `COMMIT_REVIEW` attempts beside its own, which reads `REVIEW 7 of P turns` on TE-4.
          - member: the SPEC_REVIEW, SPEC_WRITING, IMPLEMENT, GATE ⇄ REPAIR and REBUT lines
            driven_by: tests/test_stack_view.py::test_a_commit_review_reads_its_peak_beside_the_lens_bound
    positive_case: >-
      "No other line reads those attempts" is read on TE-4, where the same
      render prints `COMMIT_REVIEW 7 of 57 turns` and `REVIEW P of P turns`.
      So the instrument that reads REVIEW empty sees the commit review
      attempts it would wrongly count. "The line reads no attempt of" the
      six phases is read on TE-9 and TE-4, where the same line reads 25 and
      7 from their own attempts.
  - claim: >-
      A layer task with no closed `COMMIT_REVIEW` attempt reads
      `PLACEHOLDER` for that line's peak, keeps the line and still reads
      the lens bound. Its peak is never 0. An attempt left open, whose
      `num_turns` is NULL, counts as no attempt. The witness drives a layer
      with no commit review attempt at all (TE-7) and a layer whose only one
      is open (TE-6). In the same render it reads TE-9's line with its peak
      of 25.
    witness: tests/test_stack_view.py::test_a_layer_with_no_closed_commit_review_reads_it_absent
    wrong_versions:
      - An open commit review attempt counted as 0, which reads `COMMIT_REVIEW 0 of 57 turns` on TE-6.
      - A layer with no commit review attempt read as 0.
      - The line left off a layer with no closed commit review attempt.
    covers:
      - set: the layers with no closed commit review attempt
        members:
          - member: a layer with no commit review attempt at all (TE-7)
            driven_by: tests/test_stack_view.py::test_a_layer_with_no_closed_commit_review_reads_it_absent
          - member: a layer whose only commit review attempt is open (TE-6)
            driven_by: An open commit review attempt counted as 0, which reads `COMMIT_REVIEW 0 of 57 turns` on TE-6.
    positive_case: >-
      The witness first reads TE-9's last turn line as `COMMIT_REVIEW 25 of
      57 turns` from the same render. So the helper that reads TE-7's and
      TE-6's line as absent is one that sees a commit review peak where one
      exists.
---

## Context

Backlog item **b-bc8343**. It cites `DESIGN.md` §4.1, §5.7 and §6.1.

**The glossary half is done.** The item's own record says the hand edits
landed on 2026-11-08, and each is at base. `CONTEXT.md`'s **Phase** entry
names COMMIT_REVIEW beside SPEC_REVIEW and SPEC_WRITING (`CONTEXT.md:352-357`).
**Review commit** (`CONTEXT.md:771-773`) and **Commit review**
(`CONTEXT.md:775-780`) are entries. **End-review lens** names the commit
review as a second reader (`CONTEXT.md:766-769`). `DESIGN.md` §6.1 carries
the `saffron review` paragraph (`DESIGN.md:1507`). What is left is the stack
page's row.

**Where a commit review's facts come from.** `saffron review <task id>`
charges each lens turn to the task. `_charging` opens each agent call's
attempt with `ledger.open_attempt(task_id, phase="COMMIT_REVIEW")`
(`saffron/commit_review.py:174`). It closes it through `_close_attempt`
with that call's own result (`saffron/commit_review.py:175-181`).
`_close_attempt` writes the call's `num_turns` (`saffron/cell/session.py:327-341`).
So each commit review agent call is one attempt row on the task, in the
ledger's attempts table, as a cell's turns are.

**What bounds each of those attempts.** `run_commit_review` passes
`max_turns=end_review.LENS_MAX_TURNS` to `_review_one_layer`
(`saffron/commit_review.py:292`). That constant is 50
(`saffron/end_review.py:52`). `_review_one_layer` hands it to `review_layer`
(`saffron/end_review.py:462-476`). `review_layer` hands it to `run_lens`
(`saffron/end_review.py:400-404`). `run_lens` gives the first agent call
that bound (`saffron/phases/review.py:316-323`). A re-prompt for the schema
is a second agent call with the same bound (`saffron/phases/review.py:266-282`).
`_charging` wraps both, so each is its own attempt. No attempt sums
another's turns, unlike a SPEC_REVIEW or SPEC_WRITING session.

**What the page reads today.** `_build_layer` reads every attempt of the
layer's task through `ledger.attempts(task_id)`
(`saffron/report/stack.py:109`). It builds the layer's `turns` tuple
from those attempts, one entry per table row (`saffron/report/stack.py:111-114`).
`_phase_table` lists six rows: SPEC_REVIEW, SPEC_WRITING, IMPLEMENT, GATE ⇄
REPAIR, REVIEW and REBUT (`saffron/report/stack.py:136-155`). Each row is a
label, the attempt phase it reads, its bound and a flag. The two session
rows read their bound from `spec_review` when called
(`saffron/report/stack.py:144-150`). `_peak_turns` takes the highest closed
`num_turns` in one phase, or `None` (`saffron/report/stack.py:158-164`).
`_turn_line` prints a row whose flag is false as `<label> <peak> of <bound>
turns`, with `PLACEHOLDER` for a `None` (`saffron/report/stack.py:243-251`).
No row reads `COMMIT_REVIEW`, so a commit review's attempts reach no line.
The page shows nothing of a task's commit review.

**The tests that pin the six lines.** `test_each_phase_reads_its_own_peak_beside_its_own_bound`
and `test_a_phase_with_no_closed_attempt_reads_absent_never_zero` assert
each layer's lines as a whole list (`tests/test_stack_view.py:594-621`,
`tests/test_stack_view.py:624-657`).
Both read the shared fixture `_build_batches`
(`tests/test_stack_view.py:97-230`).

## Problem

The glossary half of the item is done at base, as Context reads it. What a
cell can land is the stack page's COMMIT_REVIEW row.

1. **Add the COMMIT_REVIEW row.** Give `_phase_table` a seventh row after
   REBUT. Its label and its attempt phase are both `COMMIT_REVIEW`. Its
   bound is `end_review.LENS_MAX_TURNS`, read from the module when the
   table is built, as the two session rows read theirs. Its flag is false,
   since each attempt is one agent call under that bound. Update the
   docstring's count of six.
2. **Extend the fixture.** In `_build_batches`, give TE-9's task three closed
   `COMMIT_REVIEW` attempts of 5, 25 and 3 turns, in that order. Give
   TE-4's layer task three of 3, 7 and 2. Open one on TE-6's layer task and
   leave it open. Give each a cost of 0.0, so every spend the other
   witnesses pin holds.
3. **Keep the two existing turn-line tests true.** Each list they pin gains
   its seventh line. Patch `end_review.LENS_MAX_TURNS` in each, as they patch
   the two `spec_review` constants.

## Out of scope

- **A closed commit review attempt of 0 turns.** No witness drives one.
  `_peak_turns` already reads a 0 as 0 for every row
  (`saffron/report/stack.py:158-164`).
- **The end review's own lens turns.** The page's `end review` line reads
  each layer's end review rows (`saffron/report/stack.py:75`,
  `saffron/report/stack.py:132`). This spec adds no turn line for them.
- **The spec loop driver's `_MAX_TURNS_PHASES`.** It lists the four cell
  phases a spec's `max_turns` bounds
  (`.claude/skills/run-saffron-spec-loop/driver.py:2312-2314`). A commit
  review attempt is not one of them, so it stays as it is.
- **The other tests that read the stack page.** One reads the page
  against `render_stack`'s own output (`tests/test_cli.py:8852-8857`).
  Another reads only its accept rate header
  (`tests/test_accept_rate.py:212-214`). Neither needs an edit.

## Notes for the agent

**No criterion declares a mutant.** The row is new code, and its spelling is
yours. So `witness` will report `skip`.

**The witnesses.** Each renders `stack_view(ledger, batch_b, specs)` for
the shared fixture and reads lines through `_turn_lines` and
`_layer_section_text`. Import `end_review` inside each test, and patch
`LENS_MAX_TURNS` with `raising=False`. Then both witnesses fail at base
on the missing line, not at collection.

**Measured on the prototype.** At base both witnesses fail. With the row
both pass, and so do the six other tests in the file. Each wrong version
above was applied to `saffron/report/stack.py` alone and failed its own
criterion's witness.
