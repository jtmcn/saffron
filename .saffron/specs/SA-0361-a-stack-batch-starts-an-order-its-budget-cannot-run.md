---
id: SA-0361
title: A stack batch starts an order its budget cannot run, and prints no admission line
type: bug
priority: 2
estimated_lines: 18
estimate_measured: true
touches:
  - saffron/cli.py
  - tests/test_cli.py
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
  - saffron/batch.py
  - saffron/scheduler.py
  - saffron/ledger.py
  - saffron/task.py
  - saffron/spec_review.py
  - saffron/end_review.py
  - saffron/follow_up.py
  - saffron/gates/**
  - saffron/phases/**
  - saffron/cell/**
  - tests/test_batch.py
  - tests/test_scheduler.py
budget_usd: 30
max_attempts: 3
max_turns: 150
risk: standard
acceptance:
  - claim: >-
      `saffron batch --stack` prints the admission block `saffron queue
      --stack` prints, from `_print_stack_admission`, for the order it hands
      `run_stack_batch`. The block follows the plan's `refusals:` lines. It is
      printed in three cases: at the printed total, below the total with
      `--partial`, and below the total when the batch is refused. Patched
      shares and a patched spec review cap move the batch's block as they
      move the function's own output. An empty order prints no block, and
      a plain `saffron batch` over the same order prints none.
    witness: tests/test_cli.py::test_a_stack_batch_prints_the_admission_block_saffron_queue_prints
    wrong_versions:
      - The block is printed only on the refusal path, so a batch at its total prints none.
      - "`_batch` prints its own copy of the block with the shares and the spec review cap written as literals, so a patched share leaves the batch's block unchanged."
      - The block is printed for every batch, so a plain `saffron batch` prints one too.
      - The empty order prints a header line with no candidate under it.
      - The block is printed before `_print_batch_plan`, ahead of the plan's `refusals:` line.
  - claim: >-
      `saffron batch --stack` whose `--budget` is below the printed total, with
      no `--partial`, prints exactly one line starting `batch: refused` after
      the block. That line names the budget and the total, each as dollars to
      the cent. The batch then exits `2`. It never reaches `run_stack_batch`,
      so it writes no `batches` row, starts no layer, prints no stop line and
      writes no stack view. The witness drives a cent below the total, above
      the last layer's threshold, and the default `--budget` with no flag
      given. At the total itself the same instruments see `run_stack_batch`
      reached, one `batches` row, every layer started, a `batch: DRAINED`
      line and one stack view written.
    witness: tests/test_cli.py::test_a_stack_batch_below_its_total_is_refused_before_any_batch_row
    wrong_versions:
      - The comparison is `<=`, so a budget equal to the printed total is refused.
      - The refusal compares the budget with the last layer's threshold rather than the total, so $107.99 starts every layer.
      - The refusal exits `1`, the code §4.2.1 reserves for a task's own failure.
      - The refusal line is printed and the batch goes on into `run_stack_batch`.
      - The refusal is decided after a `batches` row is created, so a refused batch leaves a row behind.
      - The refusal line names the total but not the budget.
  - claim: >-
      `--partial` starts the order at a budget below the total as a stack
      batch did before this change. At $91.99 over the witness's order it
      starts the first two layers, passes the third over and stops `BUDGET`
      with exit `0`, printing no refusal. At the total no flag is needed, and
      every layer starts and the batch stops `DRAINED`.
    witness: tests/test_cli.py::test_partial_runs_a_stack_order_below_its_total
    wrong_versions:
      - "`--partial` is parsed and ignored, so the batch is refused at $91.99."
      - The comparison is `<=`, so a batch at the total without `--partial` is refused.
  - claim: >-
      `saffron batch --partial` without `--stack` exits `2` at parse time.
      Its error line names both flags, and it reaches no readiness probe and
      opens no ledger. The same probe double sees `saffron batch --stack
      --partial` reach readiness and open the ledger.
    witness: tests/test_cli.py::test_partial_without_stack_is_refused_before_readiness
    wrong_versions:
      - "`--partial` without `--stack` is accepted and does nothing, so the plain batch goes on to readiness."
  - claim: >-
      `saffron queue --stack` prints its admission block exactly as before.
    witness: tests/test_cli.py::test_queue_stack_prints_each_layers_admission_threshold_and_the_total
    preserves: true
  - claim: >-
      With `--partial`, `saffron batch --stack` over a chain still starts each
      layer at its printed threshold and stops `BUDGET` a cent below it.
    witness: tests/test_cli.py::test_each_stack_layers_threshold_agrees_with_what_run_stack_batch_admits
    preserves: true
---

## Context

Backlog item **b-fe3488**, under `DESIGN.md` §7.1 and §4.2.1. Related:
b-2f4746. Every line below was read at `ff5b3f98`.

**What the design says.** §7.1 says to set the nightly budget before the
queue depth, and to size it against the queue (`DESIGN.md:1567-1569`).
§4.2.1 maps a batch's exit codes and keeps `1` for a task's own failure
(`DESIGN.md:517`). It sends a preflight failure that takes the whole batch to
`2`. A refusal before any batch row exists is that shape. `_batch` already
refuses an unattended runtime with a `batch: refused` line and `2`
(`saffron/cli.py:2367-2368`).

**What `saffron queue --stack` prints.** `_queue` calls
`_print_stack_admission(resolved.candidates)` under `--stack`
(`saffron/cli.py:2997-2998`). That function prints a header, one threshold
line per candidate and a last line, `--budget $X runs every candidate and
keeps both shares whole` (`saffron/cli.py:2257-2289`). It returns `None`, and
returns early with no output for an empty list (`saffron/cli.py:2268-2269`).

**What `saffron batch --stack` does today.** `_batch` runs readiness
(`saffron/cli.py:2388`), then `_resolve_queue` with `stamp_orphaned=True`
(`saffron/cli.py:2450`). It calls `_print_batch_plan` (`saffron/cli.py:2470`).
When the scan stamped an orphan, `orphan_rows` rewrites the queue page
(`saffron/cli.py:2489`). Under `--stack` it builds the adapters
(`saffron/cli.py:2498`) and calls `run_stack_batch` (`saffron/cli.py:2603`),
then `write_stack_view` (`saffron/cli.py:2624`). It prints no admission
line. `run_stack_batch` creates the `batches` row
(`saffron/batch.py:968`). So a refusal returned from `_batch` before that
call leaves no row, no reserve held, no stack view and no `deferred.json`.

**What it cost.** In the spec loop's run 54, `--budget 230` for four specs
carrying $185 passed $115 to cells. The queue's total was $434. The batch
started two specs and stopped `BUDGET`. In run 57, batch 74 at `--budget 120`
gave tasks $60 for `SA-0343` ($52) and `SA-0356` ($30). It stopped `BUDGET`
before `SA-0356`, and a second batch with its own reserve and finish ran it.

## Problem

1. **Print the block.** Under `--stack`, once the scan resolves, `_batch`
   prints `_print_stack_admission(candidates)` for the order it is about to
   hand `run_stack_batch`. It prints after `_print_batch_plan`. Make the
   function return the total it printed, and `0.0` for an empty order, so
   `_batch` compares against the figure the operator read. `_queue` keeps
   ignoring the return.
2. **Refuse below the total.** A `--budget` below that total, with no
   `--partial`, prints one line starting `batch: refused`. It
   names the budget and the total, each as `$` to the cent, and says
   `--partial` starts the order anyway. Then return `2`. Equal to the total
   is admitted. Decide it before `run_stack_batch`, so no `batches` row, no
   layer, no stop line and no stack view exist for the refused batch.
3. **What the refusal leaves.** Readiness has run by then, which writes no
   ledger row. The scan's reconcile is done as well. It stamps any corpse
   `ORPHANED`, and the queue page is rewritten for it. Those stay. They record
   what the scan found, as `saffron reconcile` would, and say nothing about
   a night. Refuse after the queue page rewrite, so the page agrees with
   the ledger.
4. **`--partial`.** A new `store_true` flag on `saffron batch`. It starts the
   order below the total exactly as today. The batch then passes over what
   its budget cannot cover (#1107), so do not call the order it starts a
   prefix. `--partial` without `--stack` is refused at parse time, as
   `--defer-end-review` is (`saffron/cli.py:343-344`).
5. **Docstrings.** The `_batch` docstring's exit-code paragraph stays as it
   is (`saffron/cli.py:2349`), since the refusal never exits `1`. The
   `_print_stack_admission` docstring is ten lines at base
   (`saffron/cli.py:2257-2267`). The `prose`
   gate counts each line past the tenth, so a line added there is a new
   hit. On the prototype one added line gave one new hit.
6. **Existing tests that drive a stack batch below its total.** A prototype
   failed four tests in `tests/test_cli.py` and no other in
   `tests/test_cli.py` or `tests/test_finish.py`.
   `test_each_stack_layers_threshold_agrees_with_what_run_stack_batch_admits`
   and `test_a_sibling_threshold_is_the_least_budget_every_larger_one_admits`
   drive `_drive_fake_stack_batch`. Pass `--partial` there. The batch now
   prints its own block, so `_parse_admission_block` drains `capsys` before
   its `saffron queue --stack` call.
   `test_saffron_batch_stack_plans_once_and_runs_that_order` (its
   readiness-passes case) and
   `test_a_stack_batch_writes_its_stack_view_into_the_queue_page` (its loop
   over stop reasons and its write-raises case) each drive two $12 specs at
   the default $50. Pass `--partial` in those calls. Keep every assertion.

## Out of scope

- b-2f4746, whether the reserve and writer shares are a floor. It stays open.
- A plain `saffron batch`. It prints no block and refuses nothing.
- `saffron finish`, which resumes a stack batch through `run_stack_batch` and
  never reaches the new check.
- `.claude/skills/run-saffron-spec-loop/`, which a later edit points at
  `--partial`.

## Notes for the agent

**Mutants and new code.** The flag, the refusal and the return value are
new code whose spelling the base does not fix. No criterion declares a
mutant, and `witness` reports `skip` for each. The wrong versions under each
criterion are what REVIEW turns into edits. Do not try them yourself.

**The witnesses.** All four new tests live in `tests/test_cli.py` and import
nothing the change adds, so each collects at base and fails there.

- One shared order: `SY-1` at $10, `SY-2` at $14 on `SY-1`, `SY-3` at $6 on
  `SY-2`, as `Candidate`s. Its thresholds are $20, $64 and $92, and its
  total is $108, the figures
  `test_queue_stack_prints_each_layers_admission_threshold_and_the_total`
  pins.
- One shared driver, shaped like `_drive_fake_stack_batch`. It fakes
  `_resolve_queue` with `_fake_batch_resolution` and readiness with
  `_readiness_passes`. It wraps the real `run_stack_batch` in a spy that
  passes `_AdmissionRunner`, `_review_double` and a `MintDouble`. It also
  spies `cli.write_stack_view`. It returns the exit code, the stdout and
  the spy's call count. It also returns the started ids, the `batches` row
  count, the stop lines and the stack view count. A missing row is no error.
- Criterion 1 reads the batch's block from `admission:` through the total
  line. It compares that with the pinned five lines at $108, at $91.99 with
  `--partial` and at $107.99. Under shares of 0.375 and a $3 cap it
  compares with what `cli._print_stack_admission(order)` prints under the
  same patch. Then an empty order and a plain `saffron batch` with
  `cli.run_batch` faked.
- Criterion 2 drives $108 first, then $107.99 and no `--budget`.
- Criterion 4 makes the readiness double return a failing `Readiness`, so
  the `--stack --partial` call exits `2` after one probe.

A prototype ran these arrangements. Every wrong version listed failed its
witness, and with `saffron/cli.py` reverted all four witnesses failed.

**Words.** Name a turn, an attempt or a batch, never a bare "run". A
candidate is "passed over", never "skipped". New comments and docstrings take
no em-dash, semicolon, contraction or sentence over 25 words.
