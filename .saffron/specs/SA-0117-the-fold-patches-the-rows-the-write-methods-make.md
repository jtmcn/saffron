---
id: SA-0117
title: The fold replays each fact through the ledger's write methods and then patches their rows through `_db`, so no one method turns a fact into rows
type: refactor
priority: 1
touches:
  - saffron/ledger.py
  - saffron/record/fold.py
  - tests/test_fold.py
  - tests/test_ledger_fold_task.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/record/contract.py
  - saffron/record/refs.py
  - saffron/record/memory.py
  - saffron/record/__init__.py
  - saffron/projection.py
  - saffron/chain_walk.py
  - saffron/cli.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/reconcile.py
  - saffron/replay.py
  - saffron/task.py
  - saffron/batch.py
  - tests/test_ledger.py
  - tests/test_ledger_appends.py
  - tests/test_record.py
  - tests/test_record_refs.py
budget_usd: 26
max_attempts: 3
max_turns: 180
risk: elevated
acceptance:
  - claim: >-
      `Ledger.fold_task(key, facts)`, given one task's key and the facts its
      writes appended, rebuilds that task's rows column for column. It holds
      for each of the eleven task kinds: `task_created`, `task_state`,
      `task_package`, `task_push`, `task_merged_head`, `task_policy`,
      `attempt_opened`, `attempt_closed`, `gate_result`, `finding` and
      `rebuttal`. It holds after every write, not only after the last, so a
      column a later write overwrites is still compared. The witness writes
      one task through all eleven, one fact per write. After each write it
      folds every fact so far into one fresh ledger and compares `tasks`,
      `attempts`, `gate_results`, `failures` and `findings` with the writing
      ledger's. Every `*_id` column and every timestamp column is left out.
      Each child row is compared through its parent's natural key instead: a
      task through its run's `base_sha`, an attempt and a finding through the
      task's `record_key`, a gate result through its attempt's `phase` and
      `n`, and a failure through its gate result's `gate`. A second attempt
      opens and closes after the last `task_state`, so `spent_usd_est` rolled
      up when `task_state` is applied differs from one rolled up at the end.
      A second task declares no risk and folds back with the `standard`
      default.
    witness: tests/test_ledger_fold_task.py::test_every_task_fact_kind_folds_back_to_the_rows_its_write_made
  - claim: >-
      Folding a record into a ledger that has that same record attached
      appends no fact to it. Today the fold replays through the write methods
      and each one appends again, so one task's eleven facts become 21.
    witness: tests/test_ledger_fold_task.py::test_folding_into_a_ledger_with_a_record_appends_nothing
  - claim: >-
      `fold_task` is one transaction. When one of a task's facts cannot be
      placed, it raises, and the ledger holds what it held before the call. A
      fresh ledger holds no row for the task. A ledger that held the task's
      rows from an earlier fold still holds those rows unchanged.
    witness: tests/test_ledger_fold_task.py::test_a_fact_the_ledger_cannot_place_leaves_the_ledger_as_it_was
  - claim: >-
      A task fact of any of the seven kinds the ledger does not place makes
      the fold raise an error that names the kind, with `strict` and without
      it. The seven are `decision`, `run_created`, `run_finished`,
      `run_preflight`, `batch_created`, `batch_closed` and `repo_upserted`.
      The error is never recorded in `Fold.skipped` and never raised as
      `UnreadableTask`. The witness drives each of the seven under each mode,
      in one plain test. Today the fold passes over such a fact and reports
      the task folded.
    witness: tests/test_ledger_fold_task.py::test_a_kind_the_ledger_cannot_place_aborts_the_fold_in_either_mode
  - claim: >-
      A rebuttal fact whose finding no earlier fact of its task placed makes
      the whole task unreadable. A strict fold raises `UnreadableTask` naming
      the task. A fold without `strict` records the task in `Fold.skipped`,
      writes none of its rows and folds the next task. Today the fold without
      `strict` drops only the rebuttal and folds the rest of the task.
    witness: tests/test_ledger_fold_task.py::test_a_rebuttal_with_no_finding_skips_its_whole_task
  - claim: >-
      A task that a ledger holds from an earlier fold, and whose record then
      becomes unreadable, holds no rows after the next fold, with `strict` and
      without it. The fold drops it with `fold_task(key, [])`. The witness
      makes the record unreadable three ways: an entry that is not a fact, a
      log with no `task_created` fact, and a rebuttal whose finding is gone.
      A second task shares the record. In both modes, the five tables then
      hold exactly that second task's rows from the earlier fold, compared row
      for row and counted table by table. Today a task found unreadable while
      the fold orders tasks keeps the rows of its earlier fold.
    witness: tests/test_ledger_fold_task.py::test_a_task_that_became_unreadable_leaves_a_surviving_ledger
  - claim: >-
      A folded row's timestamps come from the facts that set them.
      `runs.started_at` is the `task_created` fact's time when the fold
      creates the run. `attempts.started_at` and `attempts.ended_at` are the
      times of that attempt's open and close facts. `tasks.updated_at` is the
      time of the last fact of the six kinds whose write sets that column:
      `task_created`, `task_state`, `task_package`, `task_push`,
      `task_merged_head` and `task_policy`. A later fact of the other five
      kinds does not move it. The witness makes each of the six the last of
      them in turn. After it come an `attempt_opened`, a `gate_result`, an
      `attempt_closed`, a `finding` and a `rebuttal`.
    witness: tests/test_ledger_fold_task.py::test_a_folded_task_is_dated_by_the_facts_that_set_each_column
  - claim: >-
      `fold()` reaches the ledger through `fold_task` alone. It reads no
      `_db` and calls no other `Ledger` method, for a readable task and for
      an unreadable one, with `strict` and without it. The witness hands
      `fold()` a stand-in that forwards `fold_task` to a real ledger and
      raises on any other attribute.
    witness: tests/test_ledger_fold_task.py::test_the_fold_reaches_the_ledger_only_through_fold_task
  - claim: >-
      Tasks are still folded oldest first, by their `task_created` fact.
    witness: tests/test_fold.py::test_tasks_are_folded_oldest_first
    preserves: true
  - claim: >-
      A task whose record cannot be read still names itself under `strict`,
      and is still skipped without it while the other tasks fold.
    witness: tests/test_fold.py::test_an_unreadable_task_names_itself_and_folds_the_rest
    preserves: true
  - claim: >-
      A log with no `task_created` fact still says so, in both modes.
    witness: tests/test_fold.py::test_a_log_with_no_creation_fact_says_what_is_missing
    preserves: true
  - claim: >-
      A second fold into the same ledger still leaves one copy of each row.
    witness: tests/test_fold.py::test_folding_twice_into_one_ledger_does_not_double_the_rows
    preserves: true
  - claim: >-
      A fold into a surviving ledger still keeps the `repos.policy_sha` that
      no fact carries.
    witness: tests/test_fold.py::test_a_fold_leaves_a_policy_it_cannot_reproduce
    preserves: true
  - claim: >-
      A fold that breaks for a reason of its own still exits 2.
    witness: tests/test_fold.py::test_a_fold_that_breaks_still_exits_two
    preserves: true
---

## Context

Backlog item **b-fd1468**, from an architecture review of the record and the
fold on 2026-09-20. Its parent is item **170**, whose test is "delete the
ledger, rebuild it, and get the same rows". Section 4 of
`docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md` names that
test and the end state it leads to, where nothing writes the ledger directly.
The ledger's schema is `DESIGN.md` §4.1, and this spec changes none of it.

This is the first of two stacked specs. It builds the half that reads facts:
one private `Ledger._apply(fact)` and one `Ledger.fold_task(key, facts)`, with
`saffron/record/fold.py` cut down to call only that. The second spec routes
the write methods through `_apply` as well. It then names attempts and
findings by their place in the task rather than by the writing ledger's ids,
and gives every task a `record_key`. Until it lands, the write methods keep
their own SQL. That is what lets this spec's round trip compare two
independent halves.

What the code does today, read at this spec's base:

- `_fold_task` (`saffron/record/fold.py:112-144`) replays each fact by calling
  the ledger's own write methods, one per kind, in an `if` chain with no
  `else` (`:119-143`). A fact of a kind the chain does not name is passed
  over.
- Those methods stamp `datetime('now')` (for one, `saffron/ledger.py:741`),
  so `_retime` (`fold.py:154-165`) rewrites each timestamp through
  `ledger._db`. The task's `updated_at` gets the time of its last fact of any
  kind (`fold.py:144`).
- For a ledger with no record, `create_task` mints no key
  (`ledger.py:681`). So `_upsert_task` writes the key in afterwards
  (`fold.py:290-295`).
- Every write method commits on its own (for one, `ledger.py:747`). A `with`
  block around the replay cannot roll it back, which
  `docs/evidence/2026-09-20-fold-rebuild-time.md` measured in its section "One
  measurement the fold's code cites". `_discard_task` (`fold.py:201-215`)
  deletes the rows instead. The fold calls it for a task that fails its
  second read (`fold.py:48-52`). A task that fails the first read, in
  `_creation_order` (`fold.py:101-106`), is skipped and never discarded.
- With a record attached, each write method also appends its fact
  (`ledger.py:353-382`). Folding a record into the ledger that wrote it
  therefore appends every fact but `task_created` a second time. Measured at
  base on `a_night`: 11 facts before the fold, 21 after.
- A rebuttal is placed through a map from the writing ledger's `finding_id`
  to the one the fold minted (`fold.py:118`, `:139-141`). Without `strict`,
  a rebuttal the map cannot place is dropped and the task folds without it
  (`fold.py:185-198`).
- `ledger._db` appears 14 times in `saffron/record/fold.py`.

## Problem

Each task kind is written into rows by one module and read back into rows by
another. A column one half forgets is dropped only on the fold's side. No test
compares every column of every kind, so the loss shows only if a test happens
to read that column.

Build the reading half as one method:

1. **`Ledger._apply(fact)`** is private and is the only code that turns a
   task fact into rows, for the eleven kinds above. It raises on any other
   kind. It returns the id of any row it inserts, and `None` otherwise. It
   commits nothing.
2. **`Ledger.fold_task(key, facts)`** drops the rows of the task `key` names,
   applies every fact through `_apply`, and commits once. All or nothing. An
   empty `facts` only drops the task's rows.
3. **`fold()`** keeps what it owns today: creation order
   (`_creation_order`), reading each task at the seam (`_facts_of`),
   `UnreadableTask` and `strict` against skip. `fold_task` is the only
   ledger method it calls. Wherever it finds a task unreadable, and in
   either mode, it calls `fold_task(key, [])` before it skips the task or
   raises. So an unreadable task is absent from a surviving ledger, as
   `_discard_task` meant it to be. `_fold_task`, `_retime`, `_discard_task`,
   `_clear_replayed`, `_upsert_task`, `_run_for`, `_rebut`, `_finding` and
   `_gate_result` go from `fold.py`.
4. **What `_apply` derives, and what the fact carries.** Timestamps come from
   `fact.at`, in the ledger's `%Y-%m-%d %H:%M:%S` UTC form. `_ledger_time`
   (`fold.py:147-151`) already converts it, so move it to `ledger.py`. The
   `standard` risk default and the `spent_usd_est` roll-up are derived from
   the rows, as the write methods derive them (`ledger.py:680`,
   `:742-743`).
5. **A rebuttal naming a missing finding makes its task unreadable**, under
   the rule criterion 5 states.

## Out of scope

**The write methods.** They keep their SQL, their per-call commits and their
appends. Routing them through `_apply` is the second spec. So is every change
to what a fact's payload carries.

**`record_key` for a ledger with no record.** The second spec mints a key for
every task. It also backfills a `NULL` key when the ledger opens. The writer
needs both before it can build a fact for every write. The fold needs neither.

**Attempt and finding identity.** A fact still names its finding by the
writing ledger's `finding_id`. `fold_task` keeps the map from that id to the
one `_apply` returns. An `attempt_closed` or `gate_result` fact names no attempt,
and `_apply` places it on the task's last-opened attempt, as `_fold_task` does
today (`fold.py:117-127`). Mark both with `ponytail:` comments that name the
second spec's fix.

**The per-kind tests the round trip supersedes.** `tests/test_ledger_appends.py`
and the `_db` queries in `tests/test_fold.py` stay until the second spec. Two
exceptions follow in the notes, where this spec changes the premise a test
rests on.

**The run, batch, repo and decision kinds** (item 177, and section 5 of the
record design). **`saffron/projection.py` and `saffron/chain_walk.py`**, which
read `_db` too (item b-e9db0e). **The vocabulary entry for the fact kinds**
(item b-25766a).

**`docs/evidence/scripts/2026-09-20-fold-rebuild-time.py`.** It records what
was measured at its own commit. This spec leaves its calls working. The
operator accepts that the second spec breaks them.

## Notes for the agent

**Every criterion here is new code, so none carries a mutant.** `_apply` and
`fold_task` do not exist at base. No text there fixes how you will spell
them. So `witness` reports `skip` for each, and that skip is honest. The
operator asked for one check by hand in its place. Before you trust criterion
1's witness, delete one column from one `_apply` statement, run the witness,
see it fail, and put it back. Do it twice: once for a column no later write
touches, and once for one of the four overwritten columns below. Say in your
notes which columns you dropped.

**The round trip compares two independent halves, and that is its worth.**
The writing ledger's rows come from the write methods' own SQL. The folded
rows come from `_apply`. A column `_apply` forgets differs between them.
Give every column the eleven writes set a value that is neither `NULL` nor
the schema's default. Where the column's type allows it, make the value
distinct from every other column's too. `attempts.n` and `findings.anchored`
cannot be. On the final snapshot only, assert that no compared column is
`NULL` on the writing side. `findings.adjudication` is the one exception,
since no fact sets it. `gate_results.run_id` is left out with every `*_id`
column, and the table's `CHECK` makes it `NULL` on every attempt's result
(`ledger.py:133`).

**Fold every prefix, not only the whole log.** Four columns have two writers
in one task, and the last write wins. They are `branch` (`create_task`, then
`set_task_package`), `policy_sha` (`create_task`, then `record_policy`),
`pushed_sha` (`record_push`, then `set_task_package`) and `state`
(`set_task_state`, then `set_task_package`). So an `_apply` that ignores
`policy_sha` on `task_created` matches the final rows. After each write, fold
every fact so far into the same fresh ledger and compare. That also drives
`fold_task` dropping the rows it folded a moment before.

Leave the timestamp columns out of this comparison, because the write
methods read the wall clock and the fold reads `fact.at`. Criterion 7 covers
them.

**Read rows in the new test module through a `sqlite3` connection of its
own**, opened on the ledger file, never through `ledger._db`. Import nothing
at module scope that this change adds. `revert` runs the new tests with the
source reverted. An import of a new name there is then a collection error,
which `revert` reads as `skip`. Every witness above fails at base for a
reason in its own body. Criteria 1 and 3 call `fold_task`, which base lacks,
and the rest observe behaviour the base fold does not have.

**Criterion 8's witness is a stand-in, not a scan of the source.** Write a
class whose `fold_task` forwards to a real `Ledger`. Its `__getattr__` raises
on every other name, `_db` included. Pass it as
`cast(Ledger, stand_in)` so the `types` gate accepts the call. Give it one
readable task and one unreadable one, under each mode, so `fold_task(key, [])`
goes through it too.

**Criterion 6's witness folds both tasks first, then breaks one.** The drop
matters only for a ledger that already holds the task. Test each of the three
breakages under each mode on a fresh pair. At base the first two breakages
fail in `_creation_order`, which never discards.

**`_apply` cannot call a write method.** `upsert_repo`, `create_run` and the
rest commit (`ledger.py:400`, `:511`), and a commit inside `fold_task` ends
its transaction early. Write the SQL `_apply` needs in `_apply`.
`_run_for`'s repo and run lookup moves with it (`fold.py:248-268`). Keep its
`ponytail:` about `base_sha` standing in for a run's identity. Keep
`upsert_repo`'s rule that a fold never clears a `repos.policy_sha` it cannot
reproduce, since a `preserves` criterion reads it.

**`fold_task` finds the task by `key`, never by a fact.** An empty `facts`
has no fact to read a key from. It deletes the task's
failures, gate results, attempts and findings, then the task row. Its run and
its repo belong to other tasks too and stay. A refold is free to give the
task a new `task_id`. The rows the `preserves` criteria compare leave the ids
out.

**Two tests in `tests/test_fold.py` rest on a fault this spec removes.**
`test_a_task_that_fails_mid_replay_leaves_no_rows_behind` and
`test_a_replay_that_breaks_is_not_skipped_as_unreadable` inject an unknown
payload key through `_with_unplaceable_payload`. They expect the `TypeError`
a keyword call raises on it. `_apply` reads payload keys by name, so the
extra key raises nothing. Delete both tests and the helper. Criteria 3 and 4
test the same two properties with a fault `_apply` must refuse.
`test_a_rebuttal_with_no_finding_fact_raises_under_strict` asserts the rule
criterion 5 replaces. Delete it too.

**Criterion 4's error and criterion 5's are different kinds of failure.** An
unplaced kind is the fold's own gap and aborts the fold. `saffron fold`
already exits 2 on any exception but `UnreadableTask`
(`saffron/cli.py:181-185`). A rebuttal with nothing to rebut is the record's defect, priced like a record git cannot read. So
`fold()` has to tell the two apart by exception type, and a bare
`ValueError` for both will not do.

**Criterion 5's witness folds a second, whole task beside the broken one**,
so "folds the next task" is observed rather than assumed.

**Criterion 7's witness goes through `fold()`**, with each fact's `at` moved
to a distinct minute. At base the fold dates `updated_at` by the last fact,
so the case with a rebuttal last fails there. For the `task_created` case, the
log holds none of the other five kinds.

**Size.** A prototype of this change measured 892 changed lines. It spent 254
in `ledger.py` and 223 in `fold.py`. The new test module took 364, and 51
went from `tests/test_fold.py`. The `refactor` ceiling is 1000, and `size`
blocks at `elevated`. That leaves about 100 lines for prose. Keep comments
and docstrings short, and share one row reader across the new witnesses.

**Prose.** `tests/test_ledger_fold_task.py` is a new file, so the `prose`
ratchet starts it at zero. Its comments and docstrings take no em-dash,
semicolon, contraction, perfect tense or hedge. In `ledger.py` and `fold.py`
a new comment adds hits to a file's count, and a count above base fails.
Check each file with `python3 hooks/prose_limit.py --file <path>`.
