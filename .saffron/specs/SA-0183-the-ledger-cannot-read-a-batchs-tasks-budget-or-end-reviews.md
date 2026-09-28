---
id: SA-0183
title: The ledger cannot read a batch's tasks, its budget or its layers' end reviews
type: feature
priority: 2
depends_on: [SA-0170]
touches:
  - saffron/ledger.py
  - tests/test_ledger_stack_reads.py
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
  - saffron/task.py
  - saffron/batch.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/events.py
  - saffron/record/**
  - saffron/report/**
  - saffron/repos/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - tests/test_ledger.py
  - tests/test_ledger_fold_task.py
  - tests/test_stack_view.py
  - tests/test_cli.py
budget_usd: 20
max_attempts: 3
max_turns: 130
estimated_lines: 105
pending_symbols:
  - saffron/ledger.py::batch_tasks
  - saffron/ledger.py::batch_budget
  - saffron/ledger.py::end_reviews
acceptance:
  - claim: >-
      `Ledger.batch_tasks(batch_id)` returns every task whose run has that
      `batch_id`, ordered by `run_id`, then `task_id`, each as its
      `task_id`, `spec_id`, `state` and `record_key`, or an empty list.
      `Ledger.batch_budget(batch_id)` returns the batch's `budget_usd`, or
      `None` for a batch with no row. `Ledger.end_reviews(batch_id)`
      returns every `end_reviews` row whose `task_key` is a
      `stack_layers` row filed under that batch, as its `task_key`, `lens`
      and `status`, or an empty list. The witness drives two batches, a
      run outside both, a batch id with no row, a `join` row, and an end
      review on a task that is no layer and on a later task of a layer's
      spec id.
    witness: tests/test_ledger_stack_reads.py::test_a_batchs_tasks_budget_and_end_reviews_read_only_that_batch
---

## Context

Backlog item **b-792ab2**, step 9 of its Done. It cites `DESIGN.md` §6.
`SA-0152` adds the stack view to the morning queue page. It reads each
layer of a stack batch, the batch's tasks in run order, its budget, and
each layer's end-review status.

**This spec was split from `SA-0152`.** A pricing of the queue on
2026-09-27 put `SA-0152` at 82% of the `feature` ceiling of 3000 changed
tokens. Its three reads in `saffron/ledger.py` alone made it `elevated`,
where `size` blocks a plan over the ceiling. So the reads are this spec,
and `SA-0152` runs at `standard` on top of it.

**What the tree base holds.** This spec's tree base is `SA-0170`'s head.
Every line number below was read at `f492629e`, `SA-0168`'s head. The
chain between edits `saffron/ledger.py`, so read it by symbol at the tree
base.

- `SA-0145`'s `stack_layers` table keys each layer on its `task_key`, with
  `batch_key`, the batch id as text (`saffron/ledger.py:180-189`).
  `record_stack_layer` writes it (`:1314`).
- `SA-0153`'s `end_reviews` table keys a lens's outcome on `task_key` and
  `lens` (`:193-200`). `record_end_review` writes it (`:1389`), and holds
  no check that the task is a layer.
- `batch_spend` already joins `end_reviews` to `stack_layers` on
  `task_key` and filters on `batch_key` (`:1059-1083`). This spec's
  `end_reviews` read uses the same join.
- `batches.budget_usd` holds a batch's budget (`:55-63`), and no read
  method returns it.
- `latest_batch_id()` already exists (`:1032-1040`). `SA-0152` reads it,
  and this spec adds no second one.

## Problem

Add three read methods to `Ledger`, beside `batch_spend`, as the
criterion states. Each is one `SELECT`, returns `sqlite3.Row`s or a
float, and writes nothing.

- `batch_tasks(batch_id)` joins `tasks` to `runs` and filters on
  `runs.batch_id`.
- `batch_budget(batch_id)` reads `batches`.
- `end_reviews(batch_id)` joins `end_reviews` to `stack_layers` on
  `task_key` and filters on `batch_key` as text. Match on the record key,
  never on a spec id.

**The seam `SA-0152` builds on.** Its `stack_view` calls all three.

- `batch_tasks(batch_id: int) -> list[sqlite3.Row]`, keys `task_id`,
  `spec_id`, `state` and `record_key`, in `run_id` then `task_id` order.
- `batch_budget(batch_id: int) -> float | None`.
- `end_reviews(batch_id: int) -> list[sqlite3.Row]`, keys `task_key`,
  `lens` and `status`, in no set order. A `join` row is among them.
  `SA-0152` decides what a lens means.

## Out of scope

- **The view, the page and the call.** They are `SA-0152`'s.
- **`Ledger.stack_layers`.** It is `SA-0151`'s.
- **The end-review status rule.** `SA-0152` reads a layer's `spec` and
  `standards` rows into one status. This spec returns the rows alone.
- **The dead code.** No code in `saffron/` calls the three reads until
  `SA-0152`. So each is a `pending_symbols` entry, and the `dead` gate
  defers it while this spec is open (`.saffron/gates/dead.py:4-6`,
  `:113-127`). A prototype's `dead` gate reported all three.

## Notes for the agent

**The criterion is new code.** No read at the tree base returns a
batch's tasks, its budget or its layers' end reviews. So it declares a
witness and no mutant, and `witness` reports `skip` for it. The witness
file is new, and imports only `Ledger`, which the tree base has.

**The witness** opens a `Ledger` in `tmp_path` and upserts one repo. It
creates batch `a` with budget 50 and batch `b` with budget 100. It
creates each task on a run of its own, and sets its state. In run order
they are `TE-7` in `b` as `READY_FOR_REVIEW`, `TE-3` in `b` as
`GATE_ERROR`, and `TE-2` in `a` as `READY_FOR_REVIEW`. Then a second
`TE-7` on a run with no batch, and `TE-9` in `b` as `EXHAUSTED`. The runs
of `TE-7` and `TE-3` come first, and their tasks after, `TE-3`'s first.
So task id order differs from run order there. It
records `TE-7` in `b` and `TE-2` as layers at position 1. It records end
reviews on:

- `TE-7` in `b`, `spec` `reviewed` and `join` `error`
- `TE-2`, `spec` `error`
- `TE-3`, `spec` `reviewed`, a task that is no layer
- the second `TE-7`, `standards` `reviewed`

It asserts `batch_tasks(b)` as whole tuples, `TE-7`, `TE-3`, `TE-9`, each
with its task id, state and record key. `batch_tasks(a)` is `TE-2`
alone, and a batch id past both gives an empty list. `batch_budget` gives
50.0, 100.0 and `None`. `end_reviews(b)`, sorted, is exactly `TE-7`'s two
rows. `end_reviews(a)` is `TE-2`'s one row, and a batch id past both
gives an empty list. These fail it:

- `batch_tasks` with no batch filter, which brings in `TE-2`
- `batch_tasks` ordered by spec id, or by task id alone, either way
- `batch_tasks` with no `ORDER BY`, which the host's SQLite returned in
  task id order, measured
- `batch_budget` giving 0.0 for a batch with no row
- `end_reviews` with no batch filter, which brings in `TE-2`'s row
- `end_reviews` matched on a layer's spec id, which brings in the second
  `TE-7`'s row
- `end_reviews` with no join to `stack_layers`, which brings in `TE-3`'s
  row

**How the list was measured.** A prototype ran on 2026-09-27 at
`f492629e`. The witness passed, and `ty` stayed green. Each wrong version
above was applied as a text edit, with no bytecode cache, and each
failed the witness. A review round reversed the two tasks' creation. The
witness before that let `ORDER BY task_id` and no `ORDER BY` through, and
now kills both. With `saffron/ledger.py` reverted, the witness failed
on a missing method, not at collection.

**What the witness leaves undriven.** Two tasks on one run of a batch.
`ORDER BY run_id, task_id` orders them by task id, and one run per task
cannot tell that from `run_id` alone.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.

**Size.** `saffron/ledger.py` is in `elevate_on`, so `size` blocks at the
`feature` ceiling of 3000 changed tokens (`saffron/gates/core/size.py:26`).
The prototype, formatted with `ruff format`, measured 417 changed tokens
with `size_gate`'s own count: 135 tokens in `ledger.py` and 282 in the
test. Sibling cells landed at 1.4 times their authors' estimates,
so about 584 tokens, 19% of the ceiling. The plan's `estimated_lines`
counts lines, and the checkpoint prices each line at 4 tokens
(`saffron/gates/core/size.py:39`). So plan this at about 146 changed
lines, which is 584 tokens divided by 4.
