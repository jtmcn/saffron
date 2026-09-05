---
id: SA-0045
title: a batch has nowhere to record that it happened
type: feature
priority: 1
depends_on: []
touches:
  - saffron/ledger.py
  - tests/test_ledger.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/cli.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/scheduler.py
  - saffron/report/**
  - saffron/gates/**
  - saffron/events.py
  - saffron/replay.py
budget_usd: 6
max_attempts: 3
max_turns: 60
risk: elevated
acceptance:
  - claim: >-
      A `batches` table exists carrying the seven fields §4.2.1 names —
      `batch_id`, `started_at`, `ended_at`, `budget_usd`, `spent_usd_est`,
      `until_ts` and `status` — and no others. `concurrency` is not among them:
      §4.2.1 defers it until K has a second position.
    witness: tests/test_ledger.py::test_the_batches_table_carries_exactly_the_fields_4_2_1_names
  - claim: >-
      `status` admits exactly `DRAINED`, `BUDGET`, `UNTIL` and
      `INFRASTRUCTURE`, one per stop condition, and rejects a fifth value.
      Tested through `ledger._db` with raw SQL — no `create_batch` method
      exists yet, and the spec that adds the loop adds it with its caller.
    witness: tests/test_ledger.py::test_a_batch_status_outside_the_four_stop_reasons_is_rejected
  - claim: >-
      `runs` carries a nullable `batch_id`. A run created outside a batch
      leaves it NULL rather than inventing a batch that did not happen.
    witness: tests/test_ledger.py::test_a_run_created_outside_a_batch_has_a_null_batch_id
  - claim: >-
      An existing ledger gains the new column rather than silently keeping the
      old shape. `CREATE TABLE IF NOT EXISTS` does not alter, so a database
      that already holds `runs` needs the guarded `ALTER TABLE` this module
      already uses for `pushed_sha` and `pr_url`.
    witness: tests/test_ledger.py::test_a_ledger_built_by_the_previous_schema_gains_batch_id
  - claim: >-
      A ledger written before this change opens, reads, and accepts a new run
      — the property that makes this safe to land on a database holding every
      task this repo has run.
    witness: tests/test_ledger.py::test_a_ledger_built_by_the_previous_schema_still_opens_and_writes
  - claim: >-
      No column arrives without a reader. `batches` has no `concurrency` and
      `tasks` gains no `priority` — both are §4.2.1's explicit cuts, and a
      column written at scan and read by nobody is item 18's pattern wearing a
      schema.
    witness: tests/test_ledger.py::test_the_schema_adds_no_column_that_nothing_reads
---

## Context

§4.2.1 names the schema a batch needs, and says why it is not the same call as
`tasks.priority`: *"The batch's window and its stop reason have to survive for
§6's morning queue to render the night."* Neither exists. This module declares
seven tables — `repos`, `runs`, `tasks`, `attempts`, `gate_results`, `failures`
and `findings` — and no `batches`. Its own docstring says so, and says why:
*"`batches` and `decisions` wait for a scheduler and an operator to have
something to put in them."* Backlog item 58 is the scheduler arriving.

This is the first of the five specs in the batch-orchestration plan and the one
the other four record into. It lands **only** the schema. Nothing writes a
`batches` row when this merges, and that is deliberate: the writer is the loop,
and the loop is three specs away.

## Problem

- **A night cannot be rendered.** §6's batch header needs the window and the
  stop reason. No row carries either, so the header would render a confident
  em-dash — the failure §6's own rule names.
- **`runs` cannot be grouped.** Every run is standalone. Nothing can ask which
  runs belonged to one night, which is the question the morning queue exists to
  answer.
- **The module docstring is about to become false.** It says seven of ten
  tables and names `batches` as waiting.

## Out of scope

**Writing a `batches` row.** Nothing runs a batch yet. This lands the table;
`SA-0049` writes the row and adds the method that does it.

**`tasks.policy_sha` and backlog item 16.** `SA-0046`, which is where the two
writers live. Split from this spec deliberately: the two share a location — a
migration in `Ledger.__init__` — and no mechanism.

**Rendering any of it.** `saffron/report/**` is `forbidden`.

**Backfilling `batch_id` on existing runs.** A batch invented for runs nobody
grouped is the "column named for a measurement it cannot make" failure §4.1
warns about. They stay NULL.

## Notes for the agent

**There are three migration shapes in this module, not two. Read all three
before writing a fourth.**

1. `CREATE TABLE IF NOT EXISTS` in `SCHEMA`, for a table that does not exist.
2. The guarded `PRAGMA table_info` + `ALTER TABLE ADD COLUMN` block — for a new
   column on a table that already exists. Its comment states the trap in as
   many words: *"An existing ledger predates these columns, and `IF NOT
   EXISTS` does not alter."*
3. The `gate_results_new` rebuild, for changing a constraint.

**`batches` is the first. `runs.batch_id` is the second, and getting that
wrong is the whole risk in this spec.** Adding `batch_id` to the `SCHEMA`
string alone is a silent no-op on every ledger that already exists — including
the operator's `~/.saffron/ledger.db`, which holds every task this repo has
run. It would pass its tests, merge, and then fail the next `saffron cell` with
`no such column: batch_id`. The fourth witness above exists to catch exactly
that, and it must be written against a database built by the *previous* schema,
not a fresh one.

**Any new parameter on `create_run` must be optional and default to `None`.**
`saffron/replay.py` calls it and is `forbidden` here, so a required parameter
breaks a caller this spec cannot legally repair — the attempt would then burn
its repair turns on a `scope` failure with no fix available.

**Fix the module docstring in the same diff.** It says seven of ten tables and
names `batches` as waiting. It is in `touches`, so this is free, and it is the
kind of line that stays wrong for months.

**Column types are yours to choose but say why in a comment.** §4.1 gives names
only. `started_at`/`ended_at`/`until_ts` should follow whatever this module
already does for timestamps rather than inventing a second representation —
read `runs` and `tasks` first. `ended_at` and `spent_usd_est` are unset while a
batch is running, so they are nullable; `budget_usd` is known at start.

**Every new test here runs with no network and no cell.** This spec touches
one module and a schema; nothing in it needs a container.

`risk: elevated` because `saffron/ledger.py` is in this repo's `elevate_on`.
