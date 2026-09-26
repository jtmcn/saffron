---
id: SA-0145
title: A stack batch leaves no record of its layers, so nothing can say which task each one was cut from
type: feature
priority: 1
depends_on: [SA-0144]
touches:
  - saffron/ledger.py
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
  - saffron/task.py
  - saffron/cli.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/events.py
  - saffron/record/**
  - saffron/repos/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - tests/test_task.py
  - tests/test_cli.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_ledger_fold_task.py
budget_usd: 24
max_attempts: 3
max_turns: 140
acceptance:
  - claim: >-
      `run_stack_batch` writes one `stack_layers` row for each task that
      returned `READY_FOR_REVIEW`, and for no other. On a ledger with a
      record it appends one `stack_layer` fact for each, under that task's
      record key. The row holds the batch's id as text, the layer's
      position from 1 among this batch's layers only, the spec id, the
      task's record key, the record key of the layer below in this batch or
      `NULL`, that layer's `pushed_sha` or `NULL`, and generation 0. The
      witness drives `EXHAUSTED`, `MERGE_FAILED`, `GATE_ERROR`, a `Refused`
      and a raise between layers. It drives a ledger with a record and one
      without, and a second batch on a ledger that already holds one. And
      `run_batch`, given the same results, writes no row.
    witness: tests/test_batch.py::test_a_stack_batch_records_one_layer_for_each_task_that_reached_review
  - claim: >-
      Folding the record rebuilds the `stack_layers` rows as written. A fold
      into a fresh ledger whose task ids differ from the writer's gives the
      same rows. A fold into the ledger that wrote them leaves them as they
      were, four and no more. A row keeps the record key and the head it
      was written with, after a later push to the layer below. A row
      written at generation 1 folds back at 1. `fold_task` with a layer's
      key and no facts removes that layer's row and no other. The witness
      drives the three layers of criterion 1 and one row written directly
      at generation 1.
    witness: tests/test_batch.py::test_the_stack_layers_fold_back_from_the_record_alone
---

## Context

Backlog item **b-792ab2**, step 1 of its Done. It cites `DESIGN.md` §4.1
and §4.2.1. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides a stack batch. Section 1 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md` is the design,
and its **Recording** paragraph names this table.

A stack batch runs the queued specs into one pull request stack. Each task
that reaches `READY_FOR_REVIEW` is a **layer**, and the next task is cut
from its head. That task is the next layer's **predecessor**. A task that
misses `READY_FOR_REVIEW` adds no layer.

**This spec is the last of four.** `SA-0142` builds the stack order.
`SA-0143` builds `run_stack_batch` in `saffron/batch.py`, which runs that
order and hands each task its predecessor's branch. `SA-0144` adds
`saffron batch --stack`, which calls it. This spec records each layer, so
the driver's `stack` and `status` can read the stack from the ledger in a
later step.

**What the tree base holds.** This spec's tree base is `SA-0144`'s head.
Only `depends_on[0]` stacks (`saffron/task.py:144-147`), and the chain
`SA-0142`, `SA-0143`, `SA-0144` is what puts `run_stack_batch` and
`Refused` there. Every line number below was read at `642a26c3`. The
chain edits `batch.py`, so read its lines there by symbol.

**The fact kind exists and nothing places it.** `stack_layer` is in `KINDS`
(`saffron/record/contract.py:38`). `Ledger._apply` places eleven kinds and
raises on any other (`saffron/ledger.py:508-649`). So a `stack_layer` fact
today aborts the fold (`saffron/record/fold.py:59-63`).

**How a write reaches the record.** Each write method builds one fact with
`_build_fact` and hands it to `_commit_and_append`
(`saffron/ledger.py:372-404`). That applies the fact through `_apply`,
commits, then appends it when the ledger holds a record. No production
caller builds a `Ledger` with a record yet (`saffron/ledger.py:3-4`). So in
production the row is written and no fact is kept. A test builds one with
`MemoryRecord` (`saffron/record/memory.py`).

**Why the row is keyed on record keys.** `fold_task` drops a task's rows and
applies its facts again (`saffron/ledger.py:406-434`). Each task row is
inserted again and takes a new `task_id`, which a fresh ledger mints in its
own sequence. The record key is carried on the fact
(`saffron/ledger.py:517-529`). The fold rebuilds no `batches` row
(`saffron/record/fold.py:8-13`), so a reference to `batches` fails on a
fresh ledger, with `foreign_keys=ON` (`saffron/ledger.py:215`).

**Where the batch id is known.** `_build_fact` takes the fact's
`batch_key` from `runs.batch_id` (`saffron/ledger.py:374-391`). In
`_drive`, `runner(candidate)` (`saffron/batch.py:212`) returns before
`ledger.attach_run_to_batch` runs (`:242`). So a fact built inside a runner wrapper,
before that attach, carries no batch.

## Problem

Build three things.

1. **The table.** Add `stack_layers` to `SCHEMA` in `saffron/ledger.py`,
   with no reference to another table:

   | column | type |
   |---|---|
   | `task_key` | `TEXT PRIMARY KEY` |
   | `batch_key` | `TEXT` |
   | `position` | `INTEGER NOT NULL` |
   | `spec_id` | `TEXT NOT NULL` |
   | `predecessor_key` | `TEXT` |
   | `predecessor_head` | `TEXT` |
   | `generation` | `INTEGER NOT NULL` |

   `SCHEMA` runs on every open (`saffron/ledger.py:216`), so a ledger file
   from before gains the table.
2. **The fact and its placement.** Add
   `Ledger.record_stack_layer(task_id, *, position, predecessor_task_id,
   generation)`. It takes the layer's `task_id`, its position, the
   predecessor's `task_id` or `None`, and the generation. It looks up the predecessor's record key
   and `pushed_sha`, and builds one `stack_layer` fact under the layer's
   own key. The payload carries the position, the spec id, the
   predecessor's key and head, and the generation, never a `task_id`. It
   writes through `_commit_and_append`. `_apply` places the fact as one
   `stack_layers` row, with `batch_key` from the fact and every other
   value from the payload. It takes no value from another row. `_drop_task_rows`
   deletes the task's `stack_layers` row. So a fold into a ledger that
   already holds it replaces it, and the fold's skip path,
   `fold_task(key, [])` (`saffron/record/fold.py:48`, `:56`, `:62`),
   leaves no row behind.
3. **The writer.** `run_stack_batch` calls `record_stack_layer` once for
   each task that returns `READY_FOR_REVIEW`. The row names the batch
   `run_stack_batch` opened. Generation is 0, because every task here is
   a queued spec.

One docstring sentence in `saffron/ledger.py` becomes false. "Only the
eleven kinds" (`:6`) becomes twelve. "Eight of the nine tables" (`:11`)
counts the tables `DESIGN.md` §4.1 lists, and §4.1 does not gain this
one. Keep that count, and add a sentence naming `stack_layers` as a table
§4.1 does not list.

## Out of scope

- **Reading the table.** The driver's `status` and `stack`, and the queue
  page's stack view, are later steps of b-792ab2.
- **The handoff's own head.** The row holds the predecessor's
  `pushed_sha`, the head PACKAGE pushed. `cli._stack_runner` fetches the
  branch head from the origin, and hands the layer that head. The two
  differ only after a hand push to the branch before the fetch.
  `saffron/cli.py` is forbidden here, so the fetched head is left to the
  finishing layer, step 8.
- **Generation 1.** Follow-up specs are step 7 of b-792ab2.
- **Gate 0's overlap exemption.** That folded into step 7.
- **The `batches` row in a fold.** The fold rebuilds no batch
  (`saffron/record/fold.py:8-13`). The row keeps the batch's id as text,
  as the fact carries it.
- **`DESIGN.md` §4.1's schema sketch.** It lists no `record_key` column
  today, and it gains no `stack_layers` here. `DESIGN.md` is protected.
- **The vocabulary.** `CONTEXT.md` has no entry for a layer. Backlog item
  b-466005 files it by hand.

## Notes for the agent

**Both criteria are new code.** No text at the tree base places a
`stack_layer` fact or names the table. So both declare a witness and no
mutant, and `witness` reports `skip` for them.

**Import every new name inside the test body.** `run_stack_batch` and
`Refused` are at the tree base. `record_stack_layer` and the table are
not.

**How `run_stack_batch` learns its batch is your choice.** A fact built
before `_drive`'s attach has no `batch_key`, and criterion 1 fails. One
way is a keyword on `_drive` that receives each outcome after the attach,
with the batch id. `run_batch` must pass none, and write no row.
`run_stack_batch`'s own signature stays as `SA-0143` left it, because
its caller in `saffron/cli.py` is forbidden here. Any new keyword goes on
`_drive` or `run_batch`, with a default of `None`.

**Both witnesses share one arrangement.** Write a runner class in
`tests/test_batch.py` that takes the ledger, a repo id and a script of
results. Each call records the spec id and the predecessor's, or `None`.
For a `Refused` it returns one and creates nothing. For any other result
it creates a run and a task for the spec id. It records a push of a sha
unique to that spec. For `READY_FOR_REVIEW` and `MERGE_FAILED` it calls
`set_task_package` with that state and sha. It then returns
`_outcome(state=..., run_id=..., task_id=...)`, or raises after creating
the task. Its predecessor argument defaults to `None`, so `run_batch` can
call it too. Use `_candidate` and `_ready`, a budget of 100 and
`until=None`.

The script, in order:

| order | spec | result | layer |
|---|---|---|---|
| 1 | `TE-7` | `READY_FOR_REVIEW` | 1, below it nothing |
| 2 | `TE-3` | `GATE_ERROR` | none |
| 3 | `TE-9` | `READY_FOR_REVIEW` | 2, below it `TE-7` |
| 4 | `TE-1` | raises `RuntimeError` | none |
| 5 | `TE-5` | `EXHAUSTED` | none |
| 6 | `TE-8` | `MERGE_FAILED` | none |
| 7 | `TE-2` | a `Refused` | none |
| 8 | `TE-6` | `READY_FOR_REVIEW` | 3, below it `TE-9` |

No two aborts are adjacent, so the breaker never fires, and the stop
reason is `DRAINED`.

**Criterion 1's witness** runs the script through `run_stack_batch` on a
`Ledger` built with a `MemoryRecord`. It reads `stack_layers` ordered by
`position`. It asserts exactly three rows, each column equal to the table
above. `batch_key` is `str` of the batch's id, read as `_latest_batch_id`
does. `task_key` is `ledger.record_key` of that spec's task.
`predecessor_head` is the sha pushed for the spec below. It asserts
exactly three `stack_layer` facts in the record, one under each layer's
key, and none under another task's key. It runs the script again on a
`Ledger` with no record, and asserts the same three rows by the same
rules. It then runs the script a second time through `run_stack_batch` on
that same no-record ledger. The second batch's three rows have positions
1, 2 and 3, the second batch's `batch_key`, and a `NULL` predecessor
below its `TE-7`. The first batch's rows are unchanged. Then it runs the
script through `run_batch` on a third ledger,
with a rescan that returns the same candidates, and asserts no row.
These fail it:

- a row for every task run, which gives more than three rows
- a position counted over every task started, which gives 1, 3 and 8
- a position counted over every returned outcome, which gives 1, 3 and 7
- a position counted over `READY_FOR_REVIEW` and `MERGE_FAILED`, which
  gives 1, 2 and 4
- a module-level position counter, which gives the second ledger 4, 5
  and 6
- a row for `MERGE_FAILED`, which packaged and pushed
- a predecessor from `depends_on[0]`, which `_candidate` leaves empty, so
  every `predecessor_key` is `NULL`
- a predecessor from the `Candidate` handed in, whose `task_id` is `None`
- a predecessor taken as the last task run, `TE-3`, or the last with a
  push, `TE-5` or `TE-8`
- a hook that reads the predecessor after it moves to this task, which
  makes each layer its own predecessor
- the layer's own `pushed_sha` as `predecessor_head`
- a `task_id` stored where a record key goes
- a fact built before the attach, whose `batch_key` is `None`
- a hook in `_drive` that `run_batch` fires too
- a row written and no fact appended, or a fact appended and no row
- a position counted over the whole table, or kept on the `Ledger`
  instance, which gives the second batch 4, 5 and 6
- a predecessor read from the table's last row, which puts the first
  batch's `TE-6` below the second batch's `TE-7`

This half is unmeasured. `run_stack_batch` does not exist at
`874632f2`, so nothing ran it. The list above is two spec reviews' hand
trace. Run it against the witness once `SA-0143` lands.

**Criterion 2's witness** runs the script through `run_stack_batch` on a
`Ledger` built with a `MemoryRecord`. It then writes one more layer by
hand. It creates a run and a task for `TE-4` and packages it
`READY_FOR_REVIEW`. It calls `record_stack_layer` for it with position 4,
`TE-6`'s task as predecessor and generation 1. It reads the four rows as
dicts, and takes each layer's record key now, before any fold. Then it
calls `record_push` on `TE-7`'s task with a new sha.

It opens a fresh `Ledger` with no record and creates one unrelated repo,
run and task there first. So every folded task gets a different
`task_id` from its source row. It calls `saffron.record.fold.fold` with
the record and the fresh ledger. It asserts the rows equal the source's
four. It asserts `TE-9`'s row names `TE-7`'s record key and the sha first
pushed for `TE-7`, and `TE-4`'s row has generation 1. It then calls
`fold` with the record and the source ledger itself, and asserts the
source's rows are unchanged, four and no more. Last, it calls
`fold_task` on the fresh ledger with `TE-9`'s key and an empty list. It
asserts the rows left are `TE-7`'s, `TE-6`'s and `TE-4`'s.

Take the keys before the second fold. It drops and inserts every task
again, so a key looked up afterwards by the old `task_id` names another
task, or none. These fail it:

- `_apply` with no branch for `stack_layer`, which aborts the fold
- a predecessor stored as a `task_id`
- a predecessor carried as a `task_id` and resolved to a key at fold time
- `_drop_task_rows` that leaves the row, which raises on the primary key
- `INSERT OR REPLACE` with `_drop_task_rows` untouched, which leaves
  `TE-9`'s row after `fold_task(key, [])`
- a reference from `batch_key` to `batches`, which a fresh ledger lacks
- a head looked up by `predecessor_key` at apply time, which reads the
  new sha
- a generation left out of the payload, or written as a literal 0

Measured on 2026-09-23 at `874632f2`, by a throwaway script. It
subclassed `Ledger` with the table and each build, wrote the layers with
`record_stack_layer` in place of `run_stack_batch`, and ran the steps
above. The right build passed. All nine wrong builds failed, since the
last bullet is two builds. The missing branch failed on `fold cannot
place fact kind`, the kept row on `UNIQUE constraint failed`, and the
reference on `FOREIGN KEY constraint failed`. The other six failed an
assertion.

**What the witnesses leave undriven.** A layer whose predecessor has no
`pushed_sha` is not driven. PACKAGE writes `READY_FOR_REVIEW` through
`set_task_package`, whose `pushed_sha` is a required `str`
(`saffron/ledger.py:1109-1119`). Record `NULL` there all the same. The
in-flight states,
`RATE_LIMITED` and `PREFLIGHT_FAILED` are not driven. Test for
`READY_FOR_REVIEW` alone, so each of them adds no layer.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** `saffron/ledger.py` is in `elevate_on`, so `size` blocks at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). About
75 changed lines in `ledger.py` at 4.8 tokens a line, and 35 in
`batch.py` at 6.3, are about 580 tokens. About 185 lines of test at 3.4
are about 630. That is about 1210 tokens.
