---
id: SA-0177
title: A stack batch's finishing layer has no ledger row, so nothing can record its branch or read back its pull request
type: feature
priority: 1
depends_on: [SA-0174]
touches:
  - saffron/ledger.py
  - tests/test_ledger.py
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
  - saffron/batch.py
  - saffron/cli.py
  - saffron/finish.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/events.py
  - saffron/end_review.py
  - saffron/record/**
  - saffron/repos/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - tests/test_finish.py
  - tests/test_cli.py
  - tests/test_batch.py
  - tests/test_fold.py
  - tests/test_scheduler.py
  - tests/test_ledger_fold_task.py
budget_usd: 20
max_attempts: 3
max_turns: 130
estimated_lines: 213
pending_symbols:
  - saffron/ledger.py::record_stack_finish
  - saffron/ledger.py::stack_finish
acceptance:
  - claim: >-
      `Ledger.record_stack_finish(batch_id, *, branch, head_sha,
      pr_url=None)` files one `stack_finish` fact under the batch's top
      layer, the `stack_layers` row of highest `position` whose `batch_key`
      is `str(batch_id)`. The fact's `batch_key` is `str(batch_id)`, whatever
      batch the top layer's run names. It commits one `stack_finishes` row
      for the batch, keyed on that `batch_key`, and appends the fact. A
      second call for the same batch replaces the row whole. A batch with no
      layer raises `ValueError`, and writes no row and no fact.
      `Ledger.stack_finish(batch_id)` returns the row as a `sqlite3.Row`,
      whose `branch`, `head_sha` and `pr_url` read by key, or `None` for a
      batch with no row. A fold of the record into a fresh ledger rebuilds
      every row, and so does a fold into the ledger that wrote them.
      `fold_task` with no facts removes the row its key filed. A ledger file
      whose table was dropped gains it again on open. The witness writes
      through one `Ledger` and reads through a fresh `Ledger` on the same
      path, with the writer still open. It drives a three-layer batch whose
      top layer is neither first nor last by task id or by recording. It
      writes that batch with no URL, then with a URL, then with none again.
      It drives a one-layer batch, a batch with no layer, and an id no
      `batches` row holds. Every run shares one `base_sha`, and the last
      write follows a fold that hangs the one-layer batch's task on another
      batch's run.
    witness: tests/test_ledger.py::test_a_stack_finish_is_one_fact_under_the_top_layer_and_folds_back_by_batch
    wrong_versions:
      - A write that never commits, so the fresh reader reads `None` or its open waits on the writer's lock until it raises.
      - An upsert that updates `head_sha` and `pr_url` and keeps the old `branch`.
      - The fact filed under the bottom layer, found by `position` ascending, so the row's `task_key` names `TE-1`.
      - The top layer found with no `ORDER BY`, so the first row of the scan files under `TE-2`.
      - The fact's `batch_key` stamped from `_build_fact`'s run, so after the re-fold the last write files `b2` under `str(b1)`.
      - A `_drop_task_rows` that leaves `stack_finishes` alone, so `fold_task(key, [])` keeps the three-layer batch's row.
      - A row written with no fact, so a fold into a fresh ledger rebuilds nothing.
---

## Context

Backlog item **b-792ab2**, step 8 of its Done. It cites `DESIGN.md` §4.1
and §5.7. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides that the host commits the batch's revised and follow-up specs in
its own finishing layer, which it adds above every task. Section 4 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md`, "The finishing
layer", is the design.

A stack batch runs the queued specs into one pull request stack. Each task
that reaches `READY_FOR_REVIEW` is a **layer**. The finishing layer sits
above them, on a branch of its own, with a pull request of its own. It
has no task.

**Step 8 is five specs.** `SA-0151` builds the finishing commit, and
`SA-0174` the findings file. This spec gives the finishing layer a ledger
row and a record fact. `SA-0167` pushes the finishing commit to its own
branch, opens its draft pull request, and records both here. `SA-0170`
reads the row to link the stack, the finishing layer included. This spec
was split from `SA-0167` on size.

**What the tree base holds.** `SA-0151` and `SA-0174` are merged, so the
tree base is `main`. Line numbers below were read at `4e8dd982`. Any change
that lands first can move them, so each is cited with its symbol too. The
ledger holds a `stack_layers` table keyed on `task_key`
(`saffron/ledger.py:218-228`). Its `batch_key` is the batch id as text,
and it references no other table. `Ledger.stack_layers(batch_id)` reads a
batch's rows by `batch_key` equal to the id as text, lowest `position`
first (`:1428-1445`).

**The summary is a fact.** The design lists what a batch's summary shows,
"the PR" among them, and says "here each is a fact"
(`docs/superpowers/specs/2026-09-23-stack-batch-design.md:273-278`). Item
170 makes the record on `refs/saffron/*` authoritative and the ledger an
index folded from it (`DESIGN.md:521`). So the finishing layer's branch,
pushed sha and pull request are a fact, and a fold rebuilds the row. The
operator decided this in the spec's first review.

**Where the fact is filed, and why.** A `Fact` carries a required
`task_key` (`saffron/record/contract.py:71-78`, `Fact`). A backend stores
facts per task key (`Record.append`, `:136`). The fold reads each key and
refuses one with no `task_created` fact (`saffron/record/fold.py:68-80`,
`_facts_of`). So a fact under a key of the batch's own is an unreadable
task to every fold. No batch-scoped fact has a precedent either.
`batch_created` and `batch_closed` are in `KINDS`, but nothing appends them
(`saffron/record/fold.py:8-13`).

So this spec files the finishing fact under the batch's **top layer**, the
task the finishing commit sits on. `SA-0151`'s `commit_finish` takes the
same layer, `layers[-1]` of `stack_layers` (`saffron/finish.py:56-59`).
`_apply` keys the row on the fact's `batch_key`, and keeps the filing key
in a `task_key` column. Then `fold_task`'s drop of that key removes the
row, and its replay puts it back. The fold module itself needs no edit,
since it reaches rows only through `fold_task`. The finishing commit's
parent is the top layer's `pushed_sha` in `SA-0151` and `SA-0167`, so the
top layer always exists when `SA-0167` records. A batch with no layer has
no finish to record, and the write raises.

**Why the write stamps the batch itself.** `_build_fact` stamps
`batch_key` from the task's run, not from any layer
(`saffron/ledger.py:488-507`). A fold breaks that link. `_run_for`
reuses the first run with the fact's repo and `base_sha`, by a `SELECT`
with no `ORDER BY` (`:569`, the query at `:585`). A fold also sets no
`runs.batch_id` (`saffron/record/fold.py:8-13`). So after a fold, a task's
run can belong to another batch, or to none. A probe at `4e8dd982` folded
four tasks on four runs of one `base_sha` back into their own ledger. All
four then hung on run 1. `stack_layers` keeps the right batch, because
its `batch_key` comes from the fact. So the write takes the batch it was
asked for. It replaces the built fact's `batch_key` with `str(batch_id)`
through `dataclasses.replace`, since `Fact` is a frozen dataclass.

**The fact kind is already in.** `stack_finish` is in `KINDS`
(`saffron/record/contract.py:43`), `ontology/factory.ttl:207` and
`CONTEXT.md:750`. `729133f6` added it by hand, as `30636ea7` added
`spec_text`. `CONTEXT.md` is protected, so no cell can add a kind. So
`Fact(kind="stack_finish", ...)` constructs at the tree base, and this spec
edits no file of the record.

**Why a table of its own.** `task_key` is the primary key of
`stack_layers`, and the top layer already has its row there. A column on
`batches` would break a rebuild the ledger already runs.
`_widen_batch_status` builds `batches` afresh from `SCHEMA`'s definition,
then copies seven named columns into it (`saffron/ledger.py:408-432`). A
column added to that definition makes the copy fail on any ledger from
before `INCOMPLETE`. `SCHEMA` runs on every open (`:332`), and each table
in it is `IF NOT EXISTS`. So a table of its own reaches a ledger file from
before with no migration. `foreign_keys` is on (`:331`), so a reference to
`batches` would refuse a row a fold rebuilt. The fold rebuilds no
`batches` row (`saffron/record/fold.py:8-13`).

**What the base already offers.** `Ledger(path, record=None)` opens its
file with `row_factory` set to `sqlite3.Row` (`saffron/ledger.py:325-332`),
and `close` closes the connection (`:479-480`). `_commit_and_append`
applies a fact, commits, then appends it (`:515-520`). `_drop_task_rows`
deletes every row under one key (`:530-557`). `create_run` takes a
`batch_id` (`:978-985`). `tests/test_batch.py`,
`test_the_stack_layers_fold_back_from_the_record_alone`, folds
`stack_layers` from a `MemoryRecord` into a fresh ledger.

## Problem

Build four things in `saffron/ledger.py`.

1. **The table.** Add `stack_finishes` to `SCHEMA`, with no reference to
   another table:

   | column | type |
   |---|---|
   | `batch_key` | `TEXT PRIMARY KEY` |
   | `task_key` | `TEXT NOT NULL` |
   | `branch` | `TEXT NOT NULL` |
   | `head_sha` | `TEXT NOT NULL` |
   | `pr_url` | `TEXT` |

2. **The write.** `record_stack_finish(batch_id, *, branch, head_sha,
   pr_url=None)` finds the top layer's task id. That is one `SELECT`
   joining `stack_layers` to `tasks` on `record_key`, where `batch_key` is
   `str(batch_id)`, by `position` descending, first row. With no row it
   raises `ValueError` starting `no stack layer in batch <batch_id>`.
   Otherwise it builds the fact with `_build_fact(task_id, "stack_finish",
   {"branch": ..., "head_sha": ..., "pr_url": ...})`. Then it sets the
   fact's `batch_key` with `dataclasses.replace(fact,
   batch_key=str(batch_id))`, and passes that fact to `_commit_and_append`.
3. **The fold.** `_apply` gains a `stack_finish` branch. It runs one
   `INSERT OR REPLACE` into `stack_finishes`, with `fact.batch_key`,
   `fact.task_key` and the three payload values. `_drop_task_rows` deletes
   `stack_finishes` rows `WHERE task_key = ?` with the other key-filed
   tables, and its docstring counts six.
4. **The read.** `stack_finish(batch_id)` is one `SELECT` on `batch_key`
   equal to `str(batch_id)`, and `fetchone`.

The `_drop_task_rows` docstring says the five tables are "keyed on `key`
itself" (`saffron/ledger.py:531-535`). `stack_finishes` is keyed on
`batch_key`, so that is false of it. Say the six are **filed under** `key`
instead.

The module docstring says "the sixteen kinds `_append` writes fold back"
(`saffron/ledger.py:6-7`). Make it seventeen. Do not add `stack_finishes` to
the sentence that lists the extra tables (`:11-15`). Add a separate short
sentence after it instead, naming `stack_finishes` as a sixteenth table
outside that count. The `prose` gate identifies a sentence by a hash of its
whole text (`.saffron/gates/prose.py`). So a longer list sentence is a new
sentence.

No production code calls either method until `SA-0167` calls the write
and `SA-0170` the read. So both are `pending_symbols`, and the `dead` gate
defers them while this spec is open (`.saffron/gates/dead.py:4-5`,
`pending`, `:113`).

## Out of scope

- **Writing the row.** `SA-0167` calls `record_stack_finish` after the push
  and again once the pull request opens.
- **Reading it for the link.** `SA-0170` reads `pr_url`.
- **The fact kind itself.** It is already in, as the Context says.
- **`_build_fact`'s run-derived `batch_key` for other kinds.** Every other
  fact still takes the run's batch. This spec stamps only its own fact.
  `_apply` gains no refusal of a `None` `batch_key`.
- **The batch's own row in the record.** `batches` still folds from no
  fact (`saffron/record/fold.py:8-13`). A fold rebuilds `stack_finishes`
  with no `batches` row, since the table references none.
- **Two layers at one `position` in a batch.** Nothing writes that, and
  the witness drives none. The write takes whichever row SQLite returns
  first.
- **`DESIGN.md` §4.1's schema sketch.** It gains no `stack_finishes` here.
  `DESIGN.md` is protected.
- **The vocabulary.** `CONTEXT.md` has no entry for the finishing layer.
  Backlog item b-466005 files it by hand.

## Notes for the agent

**The criterion is new code.** No text at the tree base names the table or
either method. So it declares a witness and no mutant, and `witness`
reports `skip` for it. The witness calls both methods on a `Ledger`, so
the reverted run fails with `AttributeError` rather than failing to
collect.

**If `KINDS` lacks `stack_finish` at the tree base, stop and say so.**
Do not edit `saffron/record/**` or `ontology/**`. Both are forbidden, and
`CONTEXT.md` is protected.

**The arrangement.** A `MemoryRecord` (`saffron/record/memory.py`) is the
record. The writer is `Ledger(tmp_path / "ledger.db", record=record)`, left
open. After each write the witness opens a fresh `Ledger` on the same path
as the reader, reads, and closes the reader. The writer calls
`upsert_repo` once and `create_batch` three times, for `b1`, `b2` and
`b3`. Each task is `create_run(repo_id, base_sha="a" * 40,
batch_id=<batch>)`, then `create_task`. Every run takes that same
`base_sha`. Do not vary it. The shared value is what lets the re-fold in
step 9 hang `TE-4` on a `b1` run. That needs run 1 to be `TE-1`'s, in
`b1`, so create no run ahead of its task. Each layer is
`record_stack_layer` with `generation=0`.

Batch `b1` has `TE-1` at position 1, `TE-2` at 2 and `TE-3` at 3, each
the next one's predecessor. Batch `b2` has `TE-4` at position 1. Batch
`b3` has no layer. Create the tasks in the order `TE-1`, `TE-3`, `TE-2`,
`TE-4`. Record the layers in the order `TE-2`, `TE-3`, `TE-1`, `TE-4`.

**The arithmetic.** This is worked by arithmetic, and a probe at
`4e8dd982` confirmed each pick below. `tasks.task_id` is
`INTEGER PRIMARY KEY`, so on a fresh file ids rise in creation order.
`TE-1` gets 1, `TE-3` gets 2, `TE-2` gets 3 and `TE-4` gets 4.
`stack_layers` is a rowid table, so its rowids rise in recording order.
`TE-2` gets 1, `TE-3` gets 2, `TE-1` gets 3 and `TE-4` gets 4. Within
`b1`, each way to pick a layer then gives:

| pick | layer |
|---|---|
| `ORDER BY sl.position DESC`, the build | `TE-3` |
| `ORDER BY sl.position` | `TE-1` |
| `MIN(t.task_id)`, or `ORDER BY t.task_id` | `TE-1` |
| `MAX(t.task_id)`, or `ORDER BY t.task_id DESC` | `TE-2` |
| `ORDER BY sl.rowid`, the first recorded | `TE-2` |
| `ORDER BY sl.rowid DESC`, the last recorded | `TE-1` |
| no `ORDER BY` | `TE-2` |

`TE-3` sits second of three by task id and by rowid, so no first or last
pick reaches it. The no-`ORDER BY` row follows the plan the probe printed,
`SCAN sl` then `SEARCH t USING COVERING INDEX tasks_by_record_key`. That
scan reads rowid order. Had the planner scanned `tasks` first in rowid
order, it would pick `TE-1`. Neither is `TE-3`.

Read `stack_finishes` rows with a `sqlite3` connection of the test's own,
as `tests/test_ledger_qualifications.py` does, never through `_db`.

**The witness**, in this order:

1. It records `b1` with `saffron/batch-<b1>-finish`, `a`×40 and no URL.
   The reader's row is a `sqlite3.Row` holding those, with `pr_url`
   `None`.
2. It records `b1` again with `saffron/batch-<b1>-finish-2`, `b`×40 and
   `https://github.com/o/r/pull/200`. The reader reads all three new
   values.
3. It records `b1` once more with `saffron/batch-<b1>-finish`, `c`×40 and
   no URL. The reader reads that branch, `c`×40 and `pr_url` `None`.
4. It records `b2` with `saffron/batch-<b2>-finish`, `d`×40 and
   `https://github.com/o/r/pull/201`. The reader reads `b2`'s values, and
   `b1`'s are unchanged.
5. Only now, with both batches written, it reads `batch_key` and
   `task_key` from `stack_finishes` directly, ordered by `batch_key`. The
   rows are exactly `(str(b1), <TE-3's key>)` and `(str(b2), <TE-4's
   key>)`, compared as strings.
6. The reader's `stack_finish(b3)` and `stack_finish(999)` are `None`.
7. `record_stack_finish` for `b3` and for `999` each raise `ValueError`
   matching `no stack layer`. The table still holds two rows.
8. The record's `stack_finish` facts, read key by key, are three under
   `TE-3`'s key and one under `TE-4`'s. None is under `TE-1`'s or
   `TE-2`'s. Each carries its batch's `batch_key` as text, and the
   payloads of steps 1 to 4 in order.
9. It folds the record into `Ledger(tmp_path / "fresh.db")` with
   `saffron.record.fold.fold`. Every `stack_finishes` row there equals the
   writer's, all five columns. It folds the record into the writer's
   ledger again, and the writer's rows are unchanged. Then
   `fresh.fold_task(<TE-3's key>, [])` leaves `fresh.stack_finish(b1)`
   `None` and `b2`'s row as it was.

Last, it closes every ledger and drops `stack_finishes` with `sqlite3`
directly. It opens a fresh `Ledger` on the writer's path with
`record=record` and records `b2` with `saffron/batch-<b2>-finish-2`,
`e`×40 and no URL. `stack_finish(b2)` then holds those values, and
`stack_finish(b1)` is `None`. The newest `stack_finish` fact under
`TE-4`'s key carries `batch_key` `str(b2)`. Folding the record into a
third fresh `Ledger` gives a `stack_finish(b2)` holding the `e`×40 values.
The re-fold of step 9 hung `TE-4` on run 1, a `b1` run. So a write that
kept `_build_fact`'s `batch_key` files this row under `str(b1)`. A write
that keys the live row on an argument, as `_apply`'s `run_id` does, still
appends its fact under `str(b1)`. The last two reads fail it.

Step 1b runs these against the witness too, beyond the declared seven:

- a plain `INSERT` in the write or in `_apply`, which raises on the second
  write or in the fold's replay
- an `UPDATE` alone, which writes nothing the first time
- `batch_key` as an integer referencing `batches`, which step 5 reads as
  an integer
- a read with no `WHERE`, which returns another batch's row
- a read that returns a `dict` or a tuple
- a write that stores a row for a batch with no layer
- the top layer taken as the highest task id, which files under `TE-2`
- the top layer taken as the first layer recorded, which files under
  `TE-2`
- the top layer taken as the last layer recorded, which files under
  `TE-1`
- an upsert by `COALESCE`, which keeps step 2's URL in step 3
- the live row keyed on a `batch_id` keyword to `_apply`, with the fact
  left on the run's batch (the last step's two reads fail it)
- the top layer taken by `ORDER BY sl.task_key` (random hex, so it
  reaches `TE-3` one time in three and a reviewer reads for it)

This criterion is unmeasured. A prototype was not run. Only the picks in
the table and the re-fold onto run 1 were probed. A table created outside
`SCHEMA` with `IF NOT EXISTS` also regains a dropped table, so the witness
does not tell it apart. Put the table in `SCHEMA` all the same.

**The `prose` gate** reads every new comment and docstring
(`.saffron/gates/prose.py`). Write no em dash, semicolon, contraction,
perfect tense, hedge or sentence over 25 words. Keep each docstring within
ten lines. The new table's SQL comment inside `SCHEMA` is at most two
lines, as for every table beside it. The gate reads a comment there too
(`tests/test_prose_gate.py:623-630`,
`test_an_sql_comment_in_a_string_is_held_to_the_comment_rules`).

**Commit as the witness passes**, before the full suite runs.

**Size.** `saffron/ledger.py` is in `elevate_on`, so `size` blocks at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). The
estimate is not measured. `estimated_lines` is the total below.

| part | lines | tokens |
|---|---|---|
| the table, write, `_apply` branch, drop, read and docstrings | 68 | 252 |
| the witness and its two helpers | 145 | 464 |
| total | 213 | 716 |

The rates are `SA-0167`'s measured 3.7 tokens a line in code and 3.2 in
tests. The total is 24% of the ceiling. `SA-0145`, which added
`stack_layers`, its fact and its fold, measured 1672 tokens.
