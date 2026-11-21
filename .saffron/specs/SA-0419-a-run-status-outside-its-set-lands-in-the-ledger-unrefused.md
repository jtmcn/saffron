---
id: SA-0419
title: "`runs.status` takes any string `finish_run` or a `run_finished` fact hands it, where `runs.preflight` beside it is a closed set"
type: bug
priority: 3
estimated_lines: 23
estimate_measured: true
touches:
  - saffron/ledger.py
  - tests/test_ledger.py
  - tests/test_ledger_fold_task.py
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
  - docs/**
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/cell/**
  - saffron/task.py
  - saffron/replay.py
  - saffron/record/**
  - saffron/gates/**
  - tests/ontology/**
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
budget_usd: 32
max_attempts: 3
max_turns: 150
acceptance:
  - claim: >-
      `finish_run` writes `COMPLETE` or `ABORTED`, and refuses every other
      status with `ValueError` before it writes. A refused call leaves the
      run's row `RUNNING` with no `ended_at`, and appends no `run_finished`
      fact. The witness drives a run holding a task and a run holding none,
      on a fresh ledger with a record. It also drives a ledger whose `runs`
      table is the home ledger's own, with no `CHECK`. The refused statuses
      are the misspelling `ABORTD`, a lower-case `complete`, `RUNNING`, the
      preflight outcomes `PASSED` and `FAILED`, the batch stop reason
      `DRAINED` and the empty string. On
      that older ledger, an existing row holding NULL and one holding a
      status outside the set read as they did before the ledger opened.
    witness: tests/test_ledger.py::test_a_run_status_outside_the_closed_set_is_refused_before_anything_is_written
    positive_case: >-
      After the refusals, the run holding a task finishes `ABORTED` and the
      empty run finishes `COMPLETE`, on the same fresh ledger. Each row then
      carries its status and an `ended_at`, and the same record holds one
      `run_finished` fact reading `ABORTED`. On the older ledger the refused
      row then finishes `COMPLETE`.
    wrong_versions:
      - "`finish_run` leaves the refusal to the `CHECK`."
      - "`finish_run` refuses after its row commits, before it appends the fact."
      - "`finish_run` refuses only inside its loop over the run's tasks."
      - "`finish_run` compares the status case-insensitively."
      - "`finish_run` admits `RUNNING` as well."
      - "`finish_run` admits the preflight outcomes as well."
      - "`finish_run` admits the batch stop reasons as well."
      - "`finish_run` admits `FAILED` as well."
      - "`finish_run` refuses only a non-empty status outside the set, so the empty string passes."
      - "`finish_run` writes `COMPLETE` whatever status it is handed."
      - Opening a ledger clears an existing status outside the set.
      - Opening a ledger backfills a NULL status to `COMPLETE`.
    covers:
      - set: refused statuses
        members:
          - member: the misspelling `ABORTD`
            driven_by: "`finish_run` leaves the refusal to the `CHECK`."
          - member: a lower-case `complete`
            driven_by: "`finish_run` compares the status case-insensitively."
          - member: "`RUNNING`, the one status a row is minted with"
            driven_by: "`finish_run` admits `RUNNING` as well."
          - member: the preflight outcome `PASSED`
            driven_by: "`finish_run` admits the preflight outcomes as well."
          - member: the preflight outcome `FAILED`
            driven_by: "`finish_run` admits `FAILED` as well."
          - member: the batch stop reason `DRAINED`
            driven_by: "`finish_run` admits the batch stop reasons as well."
          - member: the empty string
            driven_by: "`finish_run` refuses only a non-empty status outside the set, so the empty string passes."
      - set: admitted statuses
        members:
          - member: "`ABORTED`"
            driven_by: "`finish_run` writes `COMPLETE` whatever status it is handed."
          - member: "`COMPLETE`"
            driven_by: tests/test_ledger.py::test_a_run_status_outside_the_closed_set_is_refused_before_anything_is_written
      - set: runs by the tasks they hold
        members:
          - member: a run holding one task
            driven_by: "`finish_run` refuses after its row commits, before it appends the fact."
          - member: a run holding no task
            driven_by: "`finish_run` refuses only inside its loop over the run's tasks."
      - set: ledgers by their `runs` table
        members:
          - member: a fresh ledger, with the `CHECK`
            driven_by: "`finish_run` leaves the refusal to the `CHECK`."
          - member: the home ledger's table, with no `CHECK`
            driven_by: "`finish_run` refuses after its row commits, before it appends the fact."
      - set: existing rows on the older ledger
        members:
          - member: a row holding NULL
            driven_by: Opening a ledger backfills a NULL status to `COMPLETE`.
          - member: a row holding a status outside the set
            driven_by: Opening a ledger clears an existing status outside the set.
  - claim: >-
      A fresh ledger's `runs` table admits `RUNNING`, `COMPLETE`, `ABORTED`
      and NULL as a status, and its `CHECK` refuses any other. The witness
      writes through a `sqlite3` connection of its own, past every method of
      `Ledger`. The row `create_run` mints reads `RUNNING`. An `UPDATE` to
      each admitted value reads back, and an `INSERT` that names no status
      lands. An `UPDATE` and an `INSERT` of `ABORTD`, `complete`, `PASSED`,
      `FAILED`, `DRAINED` or the empty string each raise
      `sqlite3.IntegrityError`.
    witness: tests/test_ledger.py::test_a_fresh_ledgers_runs_table_admits_only_the_closed_set_of_statuses
    positive_case: >-
      Through the same connection, each admitted status written by `UPDATE`
      reads back, and an `INSERT` naming no status adds a row.
    wrong_versions:
      - The `runs` table has no `CHECK` on `status`.
      - The `CHECK` leaves out `RUNNING`.
      - The `CHECK` leaves out `ABORTED`.
      - The column is also `NOT NULL`.
      - The `CHECK` compares the status case-insensitively.
      - The `CHECK` admits the preflight outcomes as well.
      - The `CHECK` admits `FAILED` as well.
      - The `CHECK` admits the batch stop reasons as well.
    covers:
      - set: admitted values
        members:
          - member: "`RUNNING`, as `create_run` mints it"
            driven_by: The `CHECK` leaves out `RUNNING`.
          - member: "`COMPLETE`"
            driven_by: tests/test_ledger.py::test_a_fresh_ledgers_runs_table_admits_only_the_closed_set_of_statuses
          - member: "`ABORTED`"
            driven_by: The `CHECK` leaves out `ABORTED`.
          - member: a NULL status
            driven_by: The column is also `NOT NULL`.
      - set: refused values
        members:
          - member: the misspelling `ABORTD`
            driven_by: The `runs` table has no `CHECK` on `status`.
          - member: a lower-case `complete`
            driven_by: The `CHECK` compares the status case-insensitively.
          - member: the preflight outcome `PASSED`
            driven_by: The `CHECK` admits the preflight outcomes as well.
          - member: the preflight outcome `FAILED`
            driven_by: The `CHECK` admits `FAILED` as well.
          - member: the batch stop reason `DRAINED`
            driven_by: The `CHECK` admits the batch stop reasons as well.
          - member: the empty string
            driven_by: tests/test_ledger.py::test_a_fresh_ledgers_runs_table_admits_only_the_closed_set_of_statuses
      - set: write forms
        members:
          - member: an `UPDATE`
            driven_by: The `runs` table has no `CHECK` on `status`.
          - member: an `INSERT`
            driven_by: The `runs` table has no `CHECK` on `status`.
  - claim: >-
      `fold_task` raises `ValueError` on a `run_finished` fact whose status
      is not `COMPLETE` or `ABORTED`, and the ledger then holds no row for
      that task. The witness reads a task's facts after `finish_run` closed
      its run `ABORTED`. It swaps that fact's status for `ABORTD`,
      `complete`, `RUNNING`, the preflight outcomes `PASSED` and `FAILED`,
      the batch stop reason `DRAINED` and the empty string in turn. It folds
      each into a fresh ledger and into a ledger whose `runs` table is the
      home ledger's own, with no `CHECK`. It reads the task's rows after
      each refused fold.
    witness: tests/test_ledger_fold_task.py::test_a_run_finished_fact_outside_the_closed_set_aborts_its_fold
    positive_case: >-
      The unedited facts then fold into each of the same two ledgers, and the
      task's run reads `ABORTED`.
    wrong_versions:
      - The fold leaves the refusal to the `CHECK`.
      - The fold admits `RUNNING` as well.
      - The fold compares the status case-insensitively.
      - The fold drops the fact and returns without raising.
      - The fold admits the preflight outcomes as well.
      - The fold admits the batch stop reasons as well.
      - The fold admits `FAILED` as well.
      - The fold refuses only a non-empty status outside the set, so the empty string passes.
      - The fold refuses after `fold_task` commits, so the task's rows stay on the older ledger.
      - The fold writes `COMPLETE` whatever status the fact carries.
    covers:
      - set: refused statuses
        members:
          - member: the misspelling `ABORTD`
            driven_by: The fold leaves the refusal to the `CHECK`.
          - member: a lower-case `complete`
            driven_by: The fold compares the status case-insensitively.
          - member: "`RUNNING`"
            driven_by: The fold admits `RUNNING` as well.
          - member: the preflight outcome `PASSED`
            driven_by: The fold admits the preflight outcomes as well.
          - member: the preflight outcome `FAILED`
            driven_by: The fold admits `FAILED` as well.
          - member: the batch stop reason `DRAINED`
            driven_by: The fold admits the batch stop reasons as well.
          - member: the empty string
            driven_by: The fold refuses only a non-empty status outside the set, so the empty string passes.
      - set: ledgers by their `runs` table
        members:
          - member: a fresh ledger, with the `CHECK`
            driven_by: The fold leaves the refusal to the `CHECK`.
          - member: the home ledger's table, with no `CHECK`
            driven_by: The fold leaves the refusal to the `CHECK`.
      - set: what the fold does with the fact
        members:
          - member: it raises rather than skips
            driven_by: The fold drops the fact and returns without raising.
          - member: it writes an admitted status as the fact carries it
            driven_by: The fold writes `COMPLETE` whatever status the fact carries.
          - member: no task row remains after a refused fold
            driven_by: The fold refuses after `fold_task` commits, so the task's rows stay on the older ledger.
---

## Context

Backlog item **b-7431a2**, with item 164. It cites `DESIGN.md` §4.1. Every
line below was read at `f605529d`. This spec's commit adds this spec and one
backlog record, b-60f950. It also edits b-7431a2's `specs:` and `related:`,
the priority order and the queue smoke test in `tests/test_scheduler.py`.

**The column beside it is closed.** `RUN_PREFLIGHT_OUTCOMES` declares the
preflight outcomes once (`saffron/ledger.py:82`). The `runs` table builds its
`CHECK` from that tuple (`:83`, `:132`). `set_run_preflight` refuses any
other value before it writes (`:1396-1399`). Its docstring says why the
refusal lives in Python as well. A ledger built before the `CHECK` keeps its
old `runs` table (`:1394-1395`).

**`runs.status` is not.** The column is bare `TEXT` (`saffron/ledger.py:135`).
`finish_run` writes whatever string it is handed (`:1372-1389`). It commits
the row, then appends one `run_finished` fact per task the run holds,
carrying the same string. The fold writes that fact's status back into
`runs` with no check of its own (`:1211-1218`). `batches.status` carries a
`CHECK` for the same reason (`:121-122`).

**Every writer at base.** `create_run` mints each row `RUNNING`
(`saffron/ledger.py:1364-1366`), and so does the fold's `_insert_run`
(`:798-804`). `finish_run`'s callers pass `COMPLETE` at
`saffron/replay.py:109` and at nine sites in `saffron/cell/session.py`.
They pass `ABORTED` at one, its abort path (`saffron/cell/session.py:4150`).
`saffron/record/migrate.py` writes no `run_finished` fact. A reader counts
on the spelling. `_CUT_ROW` matches `rn.status = 'COMPLETE'`
(`saffron/cell/session.py:537-538`).

**Measured 2026-11-20, read only.** The home ledger's `runs` holds
`COMPLETE` on 396 rows, `RUNNING` on 51 and `ABORTED` on 18, and no NULL.
Its `runs` table predates both `CHECK`s. `preflight` and `status` are each
bare `TEXT` there, with `batch_id` added last. The record in the home mirror
reads 465 task keys, none unreadable, and holds five `run_finished` facts:
four `COMPLETE` and one `ABORTED`.

## Problem

A misspelt status at a new call site lands in the ledger, and a reader
counting `ABORTED` rows misses it. Make these changes.

1. **Declare the set once.** The statuses a run finishes with are
   `COMPLETE` and `ABORTED`. Declare them once in `saffron/ledger.py`,
   beside `RUN_PREFLIGHT_OUTCOMES`. The `CHECK` reads that declaration
   and adds `RUNNING`, the status every row is minted with.
2. **Give `runs.status` a `CHECK`.** It admits `RUNNING`, `COMPLETE`,
   `ABORTED` and NULL. NULL stays admitted, as it is on `runs.preflight`.
   Test fixtures insert `runs` rows with no status.
3. **Refuse in `finish_run`.** Raise `ValueError` naming the refused status
   before the `UPDATE`, so nothing is written and nothing is appended.
   `finish_run` refuses `RUNNING` too. A finished row stamped `RUNNING`
   would carry an `ended_at` and read as still going.
4. **Refuse in the fold.** `_apply` raises `ValueError` on a `run_finished`
   fact whose status is outside the two, before its `UPDATE`.
   `saffron/record/fold.py:62-66` then aborts the fold in either mode, as it
   does for a fact kind the ledger cannot place.

The `CHECK` reaches only a ledger created after this change.
`CREATE TABLE IF NOT EXISTS` leaves an existing `runs` table as it is
(`saffron/ledger.py:532-536` says so of `batches`). This spec adds no
rebuild, so existing rows keep whatever they hold. The refusals in
`finish_run` and in the fold are the control on every ledger. The `CHECK`
is the schema's declaration, and the guard against a write that bypasses
both.

## Out of scope

- **A vocabulary entry for the run statuses.** `RUNNING`, `COMPLETE` and
  `ABORTED` sit in neither `CONTEXT.md` nor `ontology/factory.ttl`. Both
  are forbidden here. Backlog item b-60f950 files the entry and the test
  that binds it to this set, by hand.
- **Rebuilding an existing `runs` table.** The home ledger keeps its table
  without the `CHECK`. `_widen_batch_status` shows the rebuild's shape
  (`saffron/ledger.py:532-556`). No measured row needs one.
- **`create_run` and `_insert_run`.** Each writes the literal `RUNNING`,
  and the `CHECK` admits it. Neither takes a status from a caller.
- **`finish_run`'s callers.** Every one passes a member of the set already,
  so `saffron/cell/session.py` and `saffron/replay.py` stay as they are.
- **Skipping such a fact instead of aborting.** The `CHECK` alone already
  aborts a fold of such a fact into a fresh ledger. The record holds none,
  and `finish_run` now refuses the write that would add one. A skip would
  price it like a rebuttal with no finding (`saffron/record/fold.py:56-61`).
- **What NULL means on a run.** b-eac388 holds that question for
  `runs.preflight`. No row on the home ledger holds a NULL status.

## Notes for the agent

**Edit or new.** The refusals, the declaration and the `CHECK` are new
code. Criteria 1 and 3 each have a mutant on the ref. Criterion 1's sits on
`finish_run`'s parameter line at `saffron/ledger.py:1380`. Criterion 3's sits
on the fold's parameter line at `:1217`. Leave both lines exactly as they
are, and add each refusal above its `UPDATE`. A mutant whose text no longer
matches fails `witness`. Criterion 2 has none, so `witness` reports `skip`
for it.

**What the witnesses leave.** The refused statuses are an open set. The
witnesses drive the values each criterion names, and no other string, nor
`None`. Nothing drives the single declaration either. The `CHECK` is
built into `SCHEMA` at import, so no test can swap the declaration and
watch both move. A `CHECK` and a refusal that spell the same members
separately pass every witness, so keep one declaration that both read.
REVIEW is the only check on it.

**`finish_run`'s docstring.** It says a refused one raises with the status
already written (`saffron/ledger.py:1373-1376`). That sentence means a
refused append. Reword it to say so, since a refused status now writes
nothing.

**Where the `CHECK` sits.** A test finds the first `status TEXT CHECK
(status IN (...))` in `SCHEMA` and holds it to the batch stop reasons
(`tests/ontology/test_vocabulary_agrees_with_code.py:94`). It finds
`batches`, since that table comes first. Keep `runs` after `batches` in
`SCHEMA`, as it is at your base. `tests/ontology/**` is forbidden here.

**No queued spec is refused.** The refusal is of a status, never of a spec.
No queued spec and neither open pull request (#1278, #1279) adds a
`finish_run` call or a run status, so `retired_first` is empty.

**Imports.** `tests/test_ledger.py` and `tests/test_ledger_fold_task.py`
import from `saffron.ledger` at module scope. Import any name this change
adds inside the test body, so the file still collects with the source
reverted.
The witnesses can be written without one.

**The older ledger.** Build it from today's `SCHEMA`, then drop `runs` and
create it again as the home ledger has it. That is the column list at
`saffron/ledger.py:127-136` without either `CHECK`, and with
`batch_id INTEGER REFERENCES batches(batch_id)` last. A plain
`sqlite3.connect` leaves foreign keys off, so the drop succeeds. That was
measured on the host with SQLite 3.54.0. Swapping
one line of `SCHEMA` is fragile here. `batches` declares a `status` line
with a `CHECK` above `runs`.

**What each witness observes.** Pin the exception type. Criterion 1's
fresh ledger expects `ValueError`, never `sqlite3.IntegrityError`. A
`finish_run` that leaves the refusal to the `CHECK` raises the second
there. Read the row's status and whether `ended_at` is set after every
refused call. Read the `run_finished` facts from the same `MemoryRecord`
the positive case reads. Criterion 3 reads the task's rows through a
`sqlite3` connection of its own, as the file's docstring asks
(`tests/test_ledger_fold_task.py:1-6`).

**The `prose` gate.** A new docstring or comment takes no em-dash,
semicolon, contraction or sentence over 25 words. A sentence listing the
statuses in backticks runs long fast.

**Size.** A prototype at `f605529d` measured 90 changed tokens outside the
test paths with `size_gate`, and 667 under them. `estimated_lines` is the
first over four. Each witness failed with `saffron/ledger.py` reverted, and
each wrong version above failed its own witness. The ledger's own test
files, the fold's and the ontology tests passed with the change.
