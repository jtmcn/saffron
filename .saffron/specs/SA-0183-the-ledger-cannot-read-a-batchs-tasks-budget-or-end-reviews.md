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
estimated_lines: 112
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
      run outside both, two tasks on one run, a batch id with no row, a
      `join` row, and an end review on a task that is no layer and on a
      later task of a layer's spec id.
    witness: tests/test_ledger_stack_reads.py::test_a_batchs_tasks_budget_and_end_reviews_read_only_that_batch
    wrong_versions:
      - "`batch_tasks` ordered by task id alone, so `TE-5` comes before `TE-7`."
      - "`batch_tasks` ordered by run id, then spec id, so `TE-3` comes before `TE-5`."
      - "`batch_budget` giving 0.0 for a batch with no row."
      - "`end_reviews` matched on a layer's spec id, which brings in the second `TE-7`'s row."
      - "`end_reviews` with no join to `stack_layers`, which brings in `TE-3`'s row."
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
Every line number below was read at `a1148c1e`, `origin/main`. The
chain between edits `saffron/ledger.py`, so read it by symbol at the tree
base.

- `SA-0145`'s `stack_layers` table keys each layer on its `task_key`, with
  `batch_key`, the batch id as text (`saffron/ledger.py:191-199`).
  `record_stack_layer` writes it (`:1357`).
- `SA-0153`'s `end_reviews` table keys a lens's outcome on `task_key` and
  `lens` (`:204-211`). `record_end_review` writes it (`:1515`), and holds
  no check that the task is a layer.
- `batch_spend` already joins `end_reviews` to `stack_layers` on
  `task_key` and filters on `batch_key` (`:1102-1125`). This spec's
  `end_reviews` read uses the same join.
- The `batches` table holds a batch's `budget_usd` (`:66-75`), and no
  read method returns it.
- `latest_batch_id` already exists (`:1075-1083`). `SA-0152` reads it,
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
  defers it while this spec is open (`.saffron/gates/dead.py:4-6`). Its
  `pending` reads each open spec's entries (`:113-127`). A prototype's
  `dead` gate reported all three.

## Notes for the agent

**The criterion is new code.** No read at the tree base returns a
batch's tasks, its budget or its layers' end reviews. So it declares a
witness and no mutant, and `witness` reports `skip` for it. The witness
file is new, and imports only `Ledger`, which the tree base has.

**The witness** opens a `Ledger` in `tmp_path` and upserts one repo. It
creates batch `a` with budget 50 and batch `b` with budget 100. It
creates the tasks below and sets each one's state. Every task has a run
of its own except `TE-5` and `TE-3`, which share one. In run order they
are:

- `TE-7` in `b` as `READY_FOR_REVIEW`
- `TE-5` then `TE-3`, both in `b`, as `RATE_LIMITED` and `GATE_ERROR`
- `TE-2` in `a` as `READY_FOR_REVIEW`
- a second `TE-7` on a run with no batch
- `TE-9` in `b` as `EXHAUSTED`

The runs of `TE-7` and of `TE-5` and `TE-3` come first. Their tasks come
after, in the order `TE-5`, `TE-7`, `TE-3`. So task id order differs from
run order across runs. Inside the shared run, spec id order differs from
task id order. It records `TE-7` in `b` and `TE-2` as layers at
position 1. It records end reviews on:

- `TE-7` in `b`, `spec` `reviewed` and `join` `error`
- `TE-2`, `spec` `error`
- `TE-3`, `spec` `reviewed`, a task that is no layer
- the second `TE-7`, `standards` `reviewed`

It asserts `batch_tasks(b)` as whole tuples, `TE-7`, `TE-5`, `TE-3`,
`TE-9`, each with its task id, spec id, state and record key.
`batch_tasks(a)` is `TE-2` alone, and a batch id past both gives an empty
list. `batch_budget` gives 50.0, 100.0 and `None`. `end_reviews(b)`,
sorted, equals `TE-7`'s two rows as whole `(task_key, lens, status)`
tuples, so a row carrying more columns fails. `end_reviews(a)` is
`TE-2`'s one row, compared the same way, and a batch id past both gives
an empty list. These fail it, and the first five are the criterion's
`wrong_versions`:

- `batch_tasks` with no batch filter, which brings in `TE-2`
- `batch_tasks` ordered by spec id, by task id alone, or by run id then
  spec id
- `batch_tasks` with no `ORDER BY`, which the host's SQLite returned in
  task id order, measured
- `batch_budget` giving 0.0 for a batch with no row
- `end_reviews` with no batch filter, which brings in `TE-2`'s row
- `end_reviews` matched on a layer's spec id, which brings in the second
  `TE-7`'s row
- `end_reviews` with no join to `stack_layers`, which brings in `TE-3`'s
  row

**How the list was measured.** A prototype ran on 2026-09-27 at
`f492629e`, with no `TE-5`. The witness passed, and `ty` stayed green.
Each wrong version above was applied as a text edit, with no bytecode
cache, and each failed the witness. With `saffron/ledger.py` reverted,
the witness failed on a missing method, not at collection.

A second review round added `TE-5`. On 2026-09-29 at `a1148c1e`, the
`batch_tasks` query ran bare against that arrangement on SQLite 3.53.1,
through `Ledger._db`. `ORDER BY r.run_id, t.task_id` gave `TE-7`, `TE-5`,
`TE-3`, `TE-9`. Order by task id and no `ORDER BY` both put `TE-5`
first. Order by run id then spec id puts `TE-3` before `TE-5`. The
witness itself was not rebuilt with `TE-5`. The re-review at the parent
branch reruns the list against it there.

**What the witness cannot kill.** `ORDER BY run_id` alone returned the
right rows, measured, with `reverse_unordered_selects` both off and on.
SQLite breaks the tie in task id order, which is the order the criterion
asks for. So no arrangement of rows tells it apart, and it is no
`wrong_versions` entry. Write `task_id` as the second key all the same.

**For the parent-branch re-review.** The witness calls `create_batch`,
`create_run`, `create_task`, `set_task_state`, `record_stack_layer` and
`record_end_review` as `a1148c1e` spells them. Confirm those signatures
and the two tables' columns at `SA-0170`'s head.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.

**Size.** `saffron/ledger.py` is in `elevate_on`, so `size` blocks at the
`feature` ceiling of 3000 changed tokens (`saffron/gates/core/size.py:26`).
The prototype, formatted with `ruff format`, measured 417 changed tokens
with `size_gate`'s own count: 135 tokens in `ledger.py` and 282 in the
test. `TE-5` adds about 30 tokens to the test, so about 447 in all. The
checkpoint prices each line at 4 tokens (`saffron/gates/core/size.py:39`).
So `estimated_lines` is 112, which is 447 tokens divided by 4, with no
overrun added. `driver.py check` applies the measured overrun itself.
Sibling cells landed at 1.4 times their authors' estimates, so about
626 tokens, 21% of the ceiling. Plan this at about 112 changed lines.
