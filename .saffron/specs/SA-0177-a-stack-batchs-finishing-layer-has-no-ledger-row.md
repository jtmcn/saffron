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
  - saffron/record/**
  - saffron/repos/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - tests/test_finish.py
  - tests/test_cli.py
  - tests/test_batch.py
  - tests/test_scheduler.py
  - tests/test_ledger_fold_task.py
budget_usd: 16
max_attempts: 3
max_turns: 100
pending_symbols:
  - saffron/ledger.py::record_stack_finish
  - saffron/ledger.py::stack_finish
acceptance:
  - claim: >-
      `Ledger.record_stack_finish(batch_id, *, branch, head_sha,
      pr_url=None)` writes and commits one `stack_finishes` row for the
      batch, keyed on `str(batch_id)`. A second call for the same batch
      replaces the row whole. `Ledger.stack_finish(batch_id)` returns that
      row as a `sqlite3.Row`, whose `branch`, `head_sha` and `pr_url` read
      by key, or `None` for a batch with no row. The row needs no `batches`
      row. A ledger file whose table was dropped gains it again on open.
      The witness writes through one `Ledger` and reads through a fresh
      `Ledger` on the same path, with the writer still open. It drives a
      row with no URL, then the same batch with a URL, then with none
      again. It drives a second batch, a batch with no row, and a batch id
      no `batches` row holds.
    witness: tests/test_ledger.py::test_a_stack_finish_is_committed_replaced_whole_and_read_back_by_batch
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
row. `SA-0167` pushes the finishing commit to its own branch, opens its
draft pull request, and records both here. `SA-0170` reads the row to link
the stack, the finishing layer included. This spec was split from
`SA-0167` on size.

**What the tree base holds.** This spec's tree base is `SA-0174`'s head.
Only `depends_on[0]` stacks (`saffron/task.py:144-147`). None of the chain
from `SA-0142` on exists at `ead4c8ee`, where every line number below was
read. So chain names are cited by symbol. From `SA-0145`, the ledger holds
a `stack_layers` table keyed on `task_key`. Its `batch_key` is the batch
id as text, and it references no other table. `SA-0145` names
`stack_layers` in the module docstring as a table `DESIGN.md` §4.1 does
not list.

**Why a table of its own.** The finishing layer has no task, so it takes
no `stack_layers` row. `task_key` is that table's primary key, and
`SA-0145` files each `stack_layer` fact under a task's key. A column on
`batches` would break a rebuild the ledger already runs.
`_widen_batch_status` builds `batches` afresh from `SCHEMA`'s definition,
then copies seven named columns into it (`saffron/ledger.py:292-316`). A
column added to that definition makes the copy fail on any ledger from
before `INCOMPLETE`. `SCHEMA` runs on every open (`saffron/ledger.py:216`),
and each table in it is `IF NOT EXISTS`. So a table of its own reaches a
ledger file from before with no migration. `foreign_keys` is on
(`:215`), so a reference to `batches` would refuse a row a fold never
rebuilt. The fold rebuilds no `batches` row (`saffron/record/fold.py:8-13`).

**Why no fact.** A fact is filed under a task's key
(`saffron/record/contract.py:71-77`), and the finishing layer has no task.
So the row is the ledger's alone, as the batch's own row is.

**What the base already offers.** `Ledger(path)` opens its file with
`row_factory` set to `sqlite3.Row` (`saffron/ledger.py:209-216`), and
`close` closes the connection (`:363-364`). `tests/test_ledger.py` builds
a ledger on a `tmp_path` file (`:12-15`).

## Problem

Build two things in `saffron/ledger.py`.

1. **The table.** Add `stack_finishes` to `SCHEMA`, with no reference to
   another table:

   | column | type |
   |---|---|
   | `batch_key` | `TEXT PRIMARY KEY` |
   | `branch` | `TEXT NOT NULL` |
   | `head_sha` | `TEXT NOT NULL` |
   | `pr_url` | `TEXT` |

   Name `stack_finishes` in the module docstring beside `stack_layers`, as
   a table `DESIGN.md` §4.1 does not list.
2. **The write and the read.** Add `record_stack_finish` and
   `stack_finish`, as the criterion states. The write is one `INSERT OR
   REPLACE` and a commit. The read is one `SELECT` on `batch_key`, and
   `fetchone`. Neither builds a fact.

No production code calls either method until `SA-0167` calls the write
and `SA-0170` the read. So both are `pending_symbols`, and the `dead` gate
defers them while this spec is open (`.saffron/gates/dead.py:4-5`,
`:113-127`).

## Out of scope

- **Writing the row.** `SA-0167` calls `record_stack_finish` after the push
  and again once the pull request opens.
- **Reading it for the link.** `SA-0170` reads `pr_url`.
- **The row in the record.** No fact carries it, and a fold loses it, as it
  loses the batch's row.
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

**The witness** opens `Ledger(tmp_path / "ledger.db")` as the writer, and
leaves it open. It never creates a batch. After each write it opens a
fresh `Ledger` on the same path as the reader, reads, and closes the
reader.

- It records batch 3 with `saffron/batch-3-finish`, `a`×40 and no URL.
  The reader's row is a `sqlite3.Row` holding those, with `pr_url`
  `None`.
- It records batch 3 again with `b`×40 and `https://github.com/o/r/pull/200`.
  The reader reads both new values.
- It records batch 3 once more with `c`×40 and no URL. The reader reads
  `c`×40 and `pr_url` `None`.
- It records batch 4 with its own values. The reader reads batch 4's
  values, and batch 3's are unchanged.
- The reader's `stack_finish(5)` is `None`.

Last, it closes the writer, drops `stack_finishes` with `sqlite3`
directly, opens a fresh `Ledger`, records batch 6, and reads it back.

These fail it:

- a write that never commits, which the fresh reader cannot see
- a plain `INSERT`, which raises on the second write
- an `UPDATE` alone, which writes nothing the first time
- an upsert that keeps a column the call leaves out
- `batch_key` as an integer referencing `batches`, which refuses a batch
  with no row
- a read with no `WHERE`, which returns another batch's row
- a read that returns a `dict` or a tuple
- the table created outside `SCHEMA`, which a dropped table never regains

This criterion is unmeasured. A prototype was not run.

**The `prose` gate** reads every new comment and docstring
(`.saffron/gates/prose.py`). Write no em dash, semicolon, contraction,
perfect tense, hedge or sentence over 25 words. Keep each docstring within
ten lines.

**Commit as the witness passes**, before the full suite runs.

**Size.** `saffron/ledger.py` is in `elevate_on`, so `size` blocks at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). The
estimate is not measured. The table and the two methods, with their
docstrings, come to about 30 lines. The witness comes to about 50. At
`SA-0167`'s measured rates of 3.7 tokens a line in code and 3.2 in tests,
that is about 270 tokens, 9% of the ceiling.
