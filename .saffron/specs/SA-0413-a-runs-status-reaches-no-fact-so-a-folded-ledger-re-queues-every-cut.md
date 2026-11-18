---
id: SA-0413
title: A run's status reaches no fact, so a ledger folded from the record re-queues every cut
type: bug
priority: 3
risk: elevated
estimated_lines: 97
estimate_measured: true
retired_first: []
depends_on: [SA-0408, SA-0411]
touches:
  - saffron/ledger.py
  - saffron/record/fold.py
  - tests/test_fold.py
  - tests/test_ledger_appends.py
  - tests/test_ledger_events.py
  - tests/test_ledger_fold_task.py
  - tests/test_ledger_qualifications.py
  - tests/test_record_routed.py
  - tests/test_follow_up.py
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
  - saffron/cell/**
  - saffron/cli.py
  - saffron/task.py
  - saffron/scheduler.py
  - saffron/replay.py
  - saffron/record/contract.py
  - saffron/record/migrate.py
  - saffron/record/routed.py
  - tests/test_session.py
  - tests/test_ledger.py
  - tests/test_record_migrate.py
budget_usd: 61
max_attempts: 3
max_turns: 290
acceptance:
  - claim: >-
      A ledger folded from the record gives each task's `runs` row the status
      the live ledger gave it, for each of `RUNNING`, `COMPLETE` and
      `ABORTED`. A row that ended keeps a non-null `ended_at`, and a
      `RUNNING` one keeps a null one. So `SA-0126`'s cap reads the folded
      ledger as it reads the live one. Of three cuts of one spec at one
      `spec_sha` and one `base_sha`, `row_is_orphaned_cut` holds only for the
      one whose row finished `COMPLETE`. A later task of that spec, minted in
      the folded ledger, finds that one through `previous_cut_orphan`. The
      cap settles a second cut `NOT_IMPLEMENTED` on that answer.
    witness: tests/test_fold.py::test_a_folded_ledger_finds_the_earlier_cut_by_its_runs_own_status
    wrong_versions:
      - "`finish_run` appends no fact, as at base, so every folded row reads `RUNNING`."
      - The fold ignores `run_created` and lets a later task share a `RUNNING` row at its `base_sha`, so the `RUNNING` cut takes the `COMPLETE` cut's status.
      - "`finish_run` files `COMPLETE` whatever status it was given, so the `ABORTED` cut reads `COMPLETE` in both ledgers."
      - Placing `run_finished` leaves `ended_at` null, in the live ledger as in the fold.
      - Placing `run_finished` names no row, so every `runs` row takes the last status applied.
  - claim: >-
      A task whose record holds `run_created` folds onto a `runs` row of its
      own, finished or not, and folding the same record again into the same
      ledger leaves one row per task. A record that holds neither run fact
      folds as at base. Its tasks at one `base_sha` share one row, `RUNNING`
      with a null `ended_at`, through a second fold as well. In a record
      where one task holds the run facts and another does not, the one that
      does not never joins the other's finished row. It reads `RUNNING` with
      a null `ended_at`, whether it is the older task or the younger, through
      a second fold as well. Folded back into the ledger that wrote it, a
      task whose row holds a baseline gate result raises nothing, and the
      gate result keeps its row.
    witness: tests/test_fold.py::test_a_task_whose_record_holds_run_created_folds_onto_a_run_of_its_own
    wrong_versions:
      - The fold gives a task its own row only when its record holds `run_finished`, so two unfinished tasks share one row.
      - The fold gives every task its own row, so the record without run facts folds to three rows.
      - The fold never gives a task its own row, so the first unfinished task and the finished one share a row.
      - A dropped task's row is never deleted, so the second fold of the record with run facts leaves six rows.
      - A dropped task's row is deleted while another task still names it, so the second fold of the record without run facts raises.
      - "`create_task` appends no `run_created`, so the record with run facts folds to one row."
      - A dropped task's row is deleted while a gate result still names it, so folding back into the writer raises.
      - A task with no `run_created` reuses any row at its `base_sha`, a finished one included, so in the mixed record it reads the other task's status.
  - claim: >-
      `create_task` appends `run_created` straight after `task_created`.
      `finish_run` appends one `run_finished` fact, whose payload is exactly
      the status, to each task its row holds, for a row holding two tasks and
      for one holding one. A row holding no task gains no fact and still takes
      the status. A row finished twice appends both facts in order, and a
      fold keeps the later status.
    witness: tests/test_ledger_appends.py::test_finishing_a_run_appends_its_status_to_each_task_it_holds
    wrong_versions:
      - "`finish_run` appends to the row's first task only."
      - "`finish_run` writes the status only through the facts it appends, so a row holding no task stays `RUNNING`."
      - The fold applies a `run_finished` only to a row still `RUNNING`, so the row finished twice reads its first status.
      - The payload carries the status under another key.
      - The payload carries another key beside the status.
      - "`create_task` appends no `run_created`."
  - claim: >-
      A `run_finished` append the record refuses raises `RecordError` out of
      `finish_run` after the row's status is committed, and emits no
      `RecordAppend`. An accepted one emits one, naming `run_finished`. That
      is how `set_task_state` already behaves.
    witness: tests/test_ledger_events.py::test_a_refused_run_finished_raises_after_the_runs_status_is_written
    wrong_versions:
      - "`finish_run` catches the `RecordError`, so nothing raises."
      - "`finish_run` appends before it commits the status, so the refused case leaves the row `RUNNING`."
      - "`finish_run` appends through the record directly rather than through `_append`, so the accepted case emits no event."
---

## Context

Backlog item **b-cafacd**, tier 2, cites `DESIGN.md` §4.1 and §4.2.1. It was
found revising `SA-0126` against its review. Item 170 makes the record on
`refs/saffron/*` authoritative and the ledger a fold of it. Every line below
was read at the base this spec was written on.

**The cap this breaks.** `SA-0126` settles the second zero-commit cut at one
`spec_sha`. `previous_cut_orphan` looks for an earlier task of the spec at
that `spec_sha` (`saffron/cell/session.py:546-575`). `row_is_orphaned_cut`
asks the same of one row (`saffron/cell/session.py:577-593`). Both test
`_CUT_ROW`: the task is `ORPHANED`, its `runs` row is `COMPLETE`, and its
latest attempt is phase `IMPLEMENTING` (`saffron/cell/session.py:536-543`).
A second cut ends `NOT_IMPLEMENTED` when the cap finds an earlier cut, and
`ORPHANED` otherwise (`saffron/cell/session.py:3058-3072`). The
cut path sets the state and then finishes the row `COMPLETE`
(`saffron/cell/session.py:3073-3074`). A kill finishes it `ABORTED` and then
stamps `ORPHANED` (`saffron/cell/session.py:4129-4132`). A cell that died in
flight leaves it `RUNNING`.

**No fact carries a row's status.** `run_created` and `run_finished` are
declared kinds (`saffron/record/contract.py:33-34`), and nothing appends
either. `finish_run` is one `UPDATE` and a commit
(`saffron/ledger.py:1289-1294`). `create_run` inserts the row `RUNNING`
before any task exists (`saffron/ledger.py:1273-1287`). The fold's own
header says neither method appends a fact (`saffron/record/fold.py:8-13`).
`_apply` raises for both kinds today (`saffron/ledger.py:1137`), and
`tests/test_ledger_fold_task.py:554-562` lists them among the kinds the fold
cannot place.

**The fold shares a row by `base_sha`.** `_run_for` reuses any row of the
repo at the fact's `base_sha`. It inserts a `RUNNING` one only when none
exists (`saffron/ledger.py:772-785`). Its own `ponytail:` says `base_sha`
stands in for a run's identity and "collapses some" (`saffron/ledger.py:778`).
Every live caller opens one row and creates one task on it:
`saffron/cell/session.py:2448`, `saffron/cli.py:1612`,
`saffron/cli.py:1778` and `saffron/replay.py:54`. A resumed task reuses its
own task's row (`saffron/cell/session.py:2445`). A batch pins one
`base_sha` for the night (`saffron/cli.py:2514-2516`), and each cell's
`CellSpec` takes it (`saffron/task.py:863`). So each task of one night
folds onto one shared row. A status filed on that row would be the last one
applied, and a night's kill would hide its earlier cut.

**Why a fact needs a task.** A fact is filed under a task's record key
(`saffron/record/contract.py:122-128`). `RoutedRecord` finds a key's mirror
through its task's row (`saffron/ledger.py:627-641`). The fold starts each
task from its `task_created` fact (`saffron/record/fold.py:68-80`). No key
exists when `create_run` runs. `create_task` builds `task_created` and
commits it with `_commit_and_append` (`saffron/ledger.py:1544-1572`), which
writes the row, commits, then appends (`saffron/ledger.py:700-705`). A
refused append raises out of `_append` and emits no event
(`saffron/ledger.py:675-698`).

## Problem

1. **`create_task` appends `run_created`** under the new task's key, straight
   after `task_created`. Its payload is empty. It marks a task whose `runs`
   row is its own, which no record written before this change says.
2. **`finish_run` appends `run_finished`** to each task its row holds, with
   the status as the whole payload. It still writes the row's status when
   no task holds it. The row is committed before any append, as
   `_commit_and_append` does.
3. **The fold reads both.** A task whose facts hold `run_created` folds onto
   a new row of its own, never one `_run_for` would share. `run_finished`
   sets that task's row's status and its `ended_at` from the fact's time.
   Dropping a task in `fold_task` also deletes its row once no task and no
   gate result names it. So a second fold leaves no empty row behind. A task with neither fact
   still shares a row by `base_sha`, as at base. It never shares a row a
   `run_finished` has set, which only a task with the facts can own.

## Out of scope

- **A stored ledger's rows.** `saffron migrate` derives sixteen kinds and
  neither run fact (`saffron/record/migrate.py:10-16`). A migrated task
  folds as at base. Its top-up compares thirteen kinds and passes over
  every other kind a live ref holds (`saffron/record/migrate.py:65-81`,
  `saffron/record/migrate.py:116-121`).
- **`run_preflight`, `batch_id` and the batch facts.** `set_run_preflight`,
  `create_batch` and `attach_run_to_batch` still append nothing, so a fold
  leaves `runs.preflight` and `runs.batch_id` unset as at base.
- **The kill path's order.** `_drive_cell` finishes the row `ABORTED` before
  it stamps `ORPHANED` (`saffron/cell/session.py:4129-4132`). With a record
  that refuses the `run_finished` append, `finish_run` now raises there, and
  the task keeps its earlier state. At base `set_task_state` commits
  `ORPHANED` and then raises. This spec forbids `saffron/cell/**`, which
  `SA-0407` and `SA-0411` edit.
- **A row two live tasks share.** No live caller makes one. A record from a
  test that does folds each task onto its own row.
- **`DESIGN.md` and `CONTEXT.md`.** §4.6 says every state read comes from
  the ledger until "the batch and run folds land" (`DESIGN.md:610`), and
  `CONTEXT.md:1046-1047` says the same. Both stay true: the batch fold and the
  rest of the run fold are still open.

## Notes for the agent

**All four criteria are new code.** Each declares a witness and no mutant,
so `witness` reports `skip` for each.

**Where each witness goes.** Criteria 1 and 2 go in `tests/test_fold.py`,
which has the `record` fixture. Criterion 3 goes in
`tests/test_ledger_appends.py`, beside its `ledger` and `record` fixtures.
Criterion 4 goes in `tests/test_ledger_events.py`, which has
`_RecordingRecord` and its `refuse` predicate. Import `CellSpec`,
`previous_cut_orphan` and `row_is_orphaned_cut` from
`saffron.cell.session`, and call neither query with an edit to it.

**Criterion 1's arrangement.** One live `Ledger` with a `MemoryRecord`. One
repo, then three cuts in this order: `RUNNING`, `COMPLETE`, `ABORTED`. Each
cut is its own `create_run` at `"a" * 40`, then `create_task` for one spec
id at one `spec_sha`. Then `set_task_state` `IMPLEMENTING`, one attempt
opened in that phase and closed, `set_task_state` `ORPHANED`, and
`finish_run` with the cut's status, skipped for `RUNNING`. Read each row's
status and whether `ended_at` is set, through the task's `record_key`. Read
them in the live ledger, then in a fresh `Ledger` the record is folded into.
Both lists must be exactly the three in order. Then `row_is_orphaned_cut`
over the three folded task ids must be `[False, True, False]`. Mint one more
task of the spec in the folded ledger, on its own `create_run`, and assert
`previous_cut_orphan` returns the middle task's folded id. The `COMPLETE`
cut sits in the middle on purpose. A `RUNNING` row the `COMPLETE` cut shares
takes its status, so the cut that died in flight reads as a cut.

**Criterion 2's arrangement.** Three cuts as above, `RUNNING`, `COMPLETE`
and `RUNNING`. Fold the record twice into one ledger, and after each fold
count every `runs` row and read the three statuses. Expect three rows. Copy
every fact but the two run kinds into a second `MemoryRecord`, under the
same keys, and fold that twice into another ledger. Expect one row. Then a
second live ledger and record hold two cuts, `COMPLETE` then `ABORTED`.
Copy that record twice, each copy without the run facts of one task, the
older and then the younger. Fold each copy twice into its own ledger.
Expect two rows, the stripped task `RUNNING` and the other its own status.
Last, a third live ledger cuts once, `COMPLETE`, and records a baseline
gate result with `run_id` on that cut's row. Fold its record into that same
ledger twice. Each time, expect the status kept and that gate result still
on its row. `record_gate_result` stores a baseline result by `run_id`
(`saffron/ledger.py:2296-2299`).

**Criterion 3's arrangement.** Two tasks on one row, a row with none, and a
row with one task finished `ABORTED` and then `COMPLETE`. Count every fact
the record holds across its keys before and after each `finish_run`. The
two-task row is the positive case for the row with none.

**Criterion 4's arrangement.** Drive it twice in one test, the record
accepting and then refusing `run_finished`. Read the row's status after
each, and the kinds the event sink caught.

**Tests the change moves.** Each pins the facts a task holds, and each must
change with the code. Each one failed on the prototype, on `run_created` at
index 1 or on the kinds the fold cannot place.
- `tests/test_ledger_appends.py:48` and `:74` list a task's kinds. Add
  `run_created` after `task_created`.
- `tests/test_ledger_events.py`: `_ALL_KINDS` (`:26-47`) and the count of
  facts (`:217`) in the test that drives every kind. Have
  `_drive_every_kind` finish a row as well, so `run_finished` is in the
  set. `:244` counts the events after `create_task`.
- `tests/test_ledger_fold_task.py:554-562`: `_FOLD_BLIND` loses both run
  kinds. `test_a_folded_task_is_dated_by_the_facts_that_set_each_column`
  (`:700`) counts facts by position, so its expected minute moves by one.
- `tests/test_record_routed.py:69`, `:304` and `:464` list a ref's kinds.
- `tests/test_ledger_qualifications.py:191` lists a task's kinds.
- `tests/test_follow_up.py`:
  `test_an_accepted_follow_up_is_a_minted_task_with_its_text_and_its_writers_cost`
  lists a task's kinds and reads three facts by index.
- `tests/test_cli.py`:
  `test_every_command_pushes_the_facts_it_appended_before_it_exits` lists the
  kinds each command pushed, twelve times.
- The module docstring of `saffron/ledger.py` counts "the twenty kinds"
  that fold back (`saffron/ledger.py:7-8`). The docstring of
  `_drive_every_kind` counts "the twenty fact kinds"
  (`tests/test_ledger_events.py:98`). The fold's header
  (`saffron/record/fold.py:8-13`) and `_run_for`'s `ponytail:`
  (`saffron/ledger.py:778-779`) stop being true as written.

**Why two parents.** `SA-0408` and `SA-0411` both edit `tests/test_cli.py`,
which the last test above lives in. `SA-0411` depends on `SA-0407`,
`SA-0408` and `SA-0409`. Nothing live reads a folded ledger yet, so the wait
costs order and nothing else.

**Measured on a prototype, 2026-11-17.** The change above and the four
witnesses were built at the base this spec was written on. Neither parent
had a diff to apply. Each witness failed with `saffron/` reverted. One
harness applied each wrong version above as one edit, and each of the
twenty-two failed its own criterion's witness. The whole suite passed,
5371 tests, with the tests listed above changed. That was before criterion
2's witness took its last case, the baseline gate result. By `size_gate` the diff
counted 387 changed tokens, with 960 more under the declared
`tests/**` test paths.

**The `types` gate and `_apply`.** `_commit_and_append` forwards
`**apply_kwargs: int | None` to `_apply` (`saffron/ledger.py:700`). So a
`bool` keyword added to `_apply` fails `ty`. Measured on the prototype, which
passes `fold_task`'s own `run_id` for such a task instead.

**The `prose` gate** reads every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.

**Size.** The `bug` ceiling is 1300 changed tokens. `saffron/ledger.py` is
in `elevate_on`, so `size` blocks here.
