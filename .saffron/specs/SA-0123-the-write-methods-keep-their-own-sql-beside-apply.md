---
id: SA-0123
title: The ledger's write methods keep their own SQL beside `_apply`, so a fact and the row it stands for are written by two pieces of code
type: refactor
priority: 1
touches:
  - saffron/ledger.py
  - tests/test_ledger.py
  - tests/test_ledger_appends.py
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
  - saffron/record/**
  - saffron/projection.py
  - saffron/chain_walk.py
  - saffron/cli.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/reconcile.py
  - saffron/replay.py
  - saffron/task.py
  - saffron/batch.py
  - tests/test_record.py
  - tests/test_record_refs.py
budget_usd: 32
max_attempts: 3
max_turns: 180
risk: elevated
acceptance:
  - claim: >-
      Every write method dates the rows it writes by its own fact's `at`, so a
      written task folds back with the same `tasks.updated_at`,
      `attempts.started_at` and `attempts.ended_at` as every other column. The
      witness replaces the clock `saffron.ledger` reads with one that starts
      in 2001 and moves one minute on each read. It writes one task through
      the eleven kinds in criterion 1 of `SA-0117`'s order: create, open
      attempt 1, its gate result, close it, `set_task_state`, two
      `record_findings` calls, a rebuttal of the second finding then of the
      first, `record_policy`, `record_push`, `set_task_package`,
      `record_merged_head`, then open, gate and close attempt 2. After each
      write it folds every fact so far into a second ledger. The two ledgers'
      rows of this task then match on every column but the `*_id` columns,
      with the three timestamp columns included. Each of those three that is
      set on either side reads a time the clock gave, never the wall's. The
      witness then makes the same writes on a ledger with no record attached,
      under a fresh clock of the same kind. Each of that ledger's three
      timestamp columns that is set reads a time its clock gave. Today each
      write stamps SQLite's `datetime('now')` while its fact carries Python's
      clock.
    witness: tests/test_ledger_fold_task.py::test_a_written_task_folds_back_with_the_times_its_facts_carry
  - claim: >-
      An `attempt_closed` or `gate_result` fact lands on the attempt its
      `(phase, n)` names, and a rebuttal on the finding at its position in the
      task. That holds in the writing ledger's rows and in the rows a fold
      into a fresh ledger makes. The witness writes to a ledger that already
      holds an unrelated task with a finding and an `IMPLEMENT` 1 attempt of
      its own. It opens
      `IMPLEMENT` 1, `IMPLEMENT` 2 and `REPAIR` 1, then writes each one's gate
      result and close in the order `IMPLEMENT` 2, `REPAIR` 1, `IMPLEMENT` 1.
      Each gate result has its own gate name, and each close its own
      `num_turns`. It records two findings in one call and a third in a
      second call, then rebuts them third, first, second, each with its own
      text. Both ledgers must place every gate name, every `num_turns` and
      every rebuttal on the attempt or finding the witness wrote it for.
      Today the fold places every close and gate result on the last attempt
      opened.
    witness: tests/test_ledger_fold_task.py::test_each_fact_lands_on_the_attempt_or_finding_it_names
  - claim: >-
      No fact carries an id the writing ledger minted. Two ledgers that make
      the same writes to one task append the same facts, kind and payload,
      whatever else each ledger holds. The witness drives all five kinds that
      name an attempt or a finding: `attempt_opened`, `attempt_closed`,
      `gate_result`, `finding` and `rebuttal`. One ledger first holds two
      other tasks. Each sits on a run of its own and has an attempt, a gate
      result with a failure, and a finding. The other ledger holds nothing. So
      every run, task, attempt, gate result, failure and finding id differs
      between the two for the tracked task. The
      task records two findings in one call and a third in a second call, and
      rebuts all three out of order. Each `attempt_closed` and `gate_result`
      fact carries the `phase` and `n` of its attempt, spelled as its
      `attempt_opened` fact spells them. Today `attempt_opened`, `finding`
      and `rebuttal` facts carry the writing ledger's `attempt_id` or
      `finding_id`.
    witness: tests/test_ledger_fold_task.py::test_two_ledgers_making_the_same_writes_append_the_same_facts
  - claim: >-
      Every task carries a `record_key`. `create_task` mints one with a
      record attached and without one. Opening a ledger gives each task that
      has none its own key. The witness creates a task on a ledger with a
      record and on one without. It opens both kinds of old ledger file with
      no record attached:
      one whose `record_key` column holds `NULL`, and one with no such column
      at all. Each holds two tasks, and after the open both carry distinct
      keys. Every key the witness reads is 32 lowercase hex characters, the
      form `new_task_key` mints. Today a ledger with no record mints no key,
      and opening a ledger fills none in.
    witness: tests/test_ledger_fold_task.py::test_every_task_carries_a_record_key_with_or_without_a_record
  - claim: >-
      A task whose key was filled in when its ledger opened, and which that
      ledger then writes with a record attached, appends facts under that key
      with no `task_created` fact before them. A fold then reports the task
      unreadable. The witness builds a ledger file holding one task with a
      `NULL` key, opens it with a record and calls `set_task_state`. The
      record then holds one key, the 32-character key the open gave the
      task, with one `task_state` fact under it. A fold
      without `strict` folds nothing and skips that key with
      `ValueError: no task_created fact`. Today such a write appends nothing.
    witness: tests/test_ledger_fold_task.py::test_a_backfilled_task_written_with_a_record_folds_as_unreadable
  - claim: >-
      A write that names a task, attempt or finding the ledger does not hold
      raises `ValueError`. It writes no row and appends no fact. The witness
      drives all ten such writes on a ledger with a record attached, then on
      one with no record:
      `set_task_state`, `set_task_package`, `record_push`,
      `record_merged_head`, `record_policy`, `record_findings` with one
      finding or more, `open_attempt`, `close_attempt`, `record_gate_result` naming an
      attempt, and `record_rebuttal`. After each write on the first ledger
      it asserts the record holds no key. At the end, neither ledger's
      `tasks`, `attempts`, `gate_results` or `findings` holds a row. Today seven of the ten return without a word.
      `record_findings` and `record_gate_result` raise the foreign key's
      `sqlite3.IntegrityError`, and only `open_attempt` raises `ValueError`.
    witness: tests/test_ledger_fold_task.py::test_a_write_naming_nothing_the_ledger_holds_raises_and_files_nothing
  - claim: >-
      Each task fact kind still folds back to the rows its write made, column
      for column but the ids and timestamps, after every write.
    witness: tests/test_ledger_fold_task.py::test_every_task_fact_kind_folds_back_to_the_rows_its_write_made
    preserves: true
  - claim: >-
      A task whose record lost the fact of the finding a rebuttal names is
      still unreadable when a later finding survives it. That later finding
      no longer sits at the position its fact names.
    witness: tests/test_ledger_fold_task.py::test_a_rebuttal_with_no_finding_skips_its_whole_task
    preserves: true
  - claim: >-
      A task that becomes unreadable still leaves no rows in a surviving
      ledger, for all three breakages, in both modes.
    witness: tests/test_ledger_fold_task.py::test_a_task_that_became_unreadable_leaves_a_surviving_ledger
    preserves: true
  - claim: >-
      A folded task is still dated by the facts that set each column.
    witness: tests/test_ledger_fold_task.py::test_a_folded_task_is_dated_by_the_facts_that_set_each_column
    preserves: true
  - claim: >-
      A task still hangs from the run its caller passed to `create_task`,
      where another run of its repo shares the same `base_sha`. The witness
      mints two runs of one repo at one `base_sha`, with a task and a billed
      attempt on each. A prototype whose writer placed both tasks by the
      fold's `base_sha` lookup failed it.
    witness: tests/test_batch.py::test_a_task_overshooting_its_own_budget_does_not_stop_the_batch
    preserves: true
  - claim: >-
      An attempt opened against no task still raises rather than naming
      another task's attempt.
    witness: tests/test_ledger.py::test_an_attempt_against_no_task_raises_rather_than_naming_another
    preserves: true
  - claim: >-
      Every write of a task fact kind applies its fact through `_apply`, with
      a record attached and with none. On each ledger the witness writes one
      task with an attempt, a gate result and a finding through the real
      methods. It then replaces `Ledger._apply` with a function that raises
      an exception of the witness's own. It makes one call of each of the
      eleven write methods criterion 1 drives, and asserts each raises that
      exception. Today
      no write calls `_apply`, so each one returns.
    witness: tests/test_ledger_fold_task.py::test_every_task_write_applies_its_fact_through_apply
---

## Context

Backlog item **b-fd1468**, the second of the two specs its record plans.
`SA-0117` built the half that reads facts and merged as #418. This spec builds
the half that writes them. The ledger's schema is `DESIGN.md` §4.1, and this
spec changes none of it. Every write still lands in SQLite first, and no
production caller attaches a record.

What the code does today, read at this spec's base:

- `Ledger._apply` (`saffron/ledger.py:493-623`) turns each of the eleven task
  fact kinds into rows. `fold_task` (`:395-430`) is its only caller.
- Every write method still writes its own rows with its own SQL, commits, and
  then calls `_append` (`:364-393`). `create_task` is one case
  (`:923-953`). So a fact and its row are written by two pieces of code.
- The write methods stamp SQLite's `datetime('now')`. For one,
  `set_task_state` does it at `:982`, and `close_attempt` at `:1038`. The
  schema defaults do it for `tasks.updated_at` (`:89`) and
  `attempts.started_at` (`:110`). The fact's `at` comes from Python's clock
  instead (`:388`).
- With no record attached, `create_task` mints no `record_key` (`:922`), and
  `_run_facts` returns nothing (`:960-961`).
- `_append` files no fact for an unknown task or a `NULL` key (`:381-384`).
  `close_attempt` and `record_rebuttal` look up an owner and file nothing when
  there is none (`:1053-1056`, `:1214-1218`). Their `UPDATE`s match nothing
  and return. So do `set_task_state`, `set_task_package`, `record_push`,
  `record_merged_head` and `record_policy` on an unknown task, one of them at
  `:980-989`. `open_attempt` raises `ValueError` (`:1008-1009`).
  `record_findings` and an attempt's `record_gate_result` hit a foreign key
  and raise `sqlite3.IntegrityError`.
- An `attempt_opened` fact carries `attempt_id` (`:1019`). A `finding` fact
  carries `finding_id` (`:1196`), and so does a `rebuttal` (`:1222`). An
  `attempt_closed` fact names no attempt (`:1056-1065`), and nor does a
  `gate_result` (`:1271-1275`).
- So `fold_task` keeps a map from the writing ledger's `finding_id` to the one
  it mints (`:415-426`). It places a close or a gate result on the last
  attempt opened (`:428-430`). Both carry a `ponytail:` that points at this spec.
- A gate result naming both an attempt and a run is refused by the table's
  `CHECK` (`:133`), as `sqlite3.IntegrityError`.
- No production caller constructs a `Ledger` with a record.
  `saffron/cli.py:187` and `:878` are the only constructions in `saffron/`,
  and neither passes one. `docs/evidence/2026-09-20-fold-rebuild-time.md:41`
  records that no ref held a record when it was measured.

## Problem

Each task kind is still written by one piece of code and read back by
another, only now both live in `saffron/ledger.py`. A column a write method
sets and `_apply` forgets is lost only on the fold's side.

Route the writes through `_apply`:

1. **Each write method builds its fact and applies it through `_apply`.** It
   commits once. Then, with a record attached, it appends the fact. The append
   comes after the commit, as `_append`'s docstring says today
   (`saffron/ledger.py:368-370`).
   `record_findings` applies all its facts in one transaction.
2. **`_apply` takes the run a writer already holds.** A `task_created` fact
   from `create_task` goes on the `run_id` the caller passed. The fold passes
   none, and `_apply` looks the run up by `base_sha` as it does today
   (`_run_for`, `saffron/ledger.py:463-491`). That lookup picks the first run
   with the `base_sha`, which is the wrong one for a writer holding the second.
   Criterion 11 holds this. A prototype whose writer used the lookup failed
   its witness and five other tests.
3. **Timestamps come from `fact.at`.** Each fact reads the clock once, as it
   is built, and its rows take that time through `_apply`. `runs` rows are not
   facts, so `create_run` keeps its own clock.
4. **Every task gets a `record_key`.** `create_task` mints one with or
   without a record. Opening a ledger fills in a key for every task that has
   none, with `new_task_key()`.
5. **A fact names an attempt by `(phase, n)` and a finding by its position in
   the task**, 1 for the first. `_apply` finds a task by the fact's
   `task_key`, not by an id `fold_task` hands it. The finding map and the
   last-opened rule go from `fold_task`, with their two `ponytail:` notes.
6. **A finding fact out of place makes its task unreadable.** `_apply` places
   a finding only at the next position in its task. A position past that means
   the record lost a finding fact. `_apply` then raises the exception `fold()`
   already reads as the record's defect (`UnplacedRebuttal`,
   `saffron/ledger.py:179`). A rebuttal with no finding at its position raises
   it too, as today.
7. **A write naming a missing task, attempt or finding raises `ValueError`.**
   A write cannot build a fact without the row it names.
   `record_gate_result` naming both an attempt and a run raises `ValueError`
   before it writes. One naming neither still raises the `CHECK`'s
   `sqlite3.IntegrityError`.

### The consequence for tasks written before this change

The operator asked for this to be stated, not hidden. After step 4, a task
created before this change gets a key when its ledger next opens. If a ledger
with a record attached then writes to it, the record holds that key's later
facts and no `task_created` fact. `fold()` reports the task unreadable, as
criterion 5 pins. No production ledger has a record attached today, so no such
log exists yet. It will exist for every old task a record-backed ledger
writes to.

### Records already written

A record appended before this change names attempts and findings by id, and
its `attempt_closed` and `gate_result` facts carry no `(phase, n)`. This spec
does not migrate them and does not read the old form. Measured on a prototype
of this change, a base-format record with one attempt and one finding made
`saffron fold` print `saffron: KeyError: 'phase'` and exit 2. It did so with
and without `--skip-unreadable`, since the fold aborts rather than skipping
the task (`saffron/cli.py:181-185`). No criterion pins this. An `_apply` that
read a missing `(phase, n)` or position as the record's own defect would make the task unreadable and
exit 1 instead.
Such records exist only in tests and in the scratch record
`docs/evidence/scripts/2026-09-20-fold-rebuild-time.py` builds. That script
rebuilds its record from the ledger each time it runs, and its calls keep
working.

## Out of scope

**The run, batch, repo and decision kinds** (item 177). `create_run`,
`finish_run`, `upsert_repo` and the batch writes keep their SQL. So does a
baseline gate result, which names a run and is no task fact.

**`saffron/record/`.** `fold()` already reaches the ledger only through
`fold_task`, and `Fact` needs no change. Keep `UnplacedRebuttal`'s name, since
`saffron/record/fold.py:22` imports it. Rewrite its docstring
(`saffron/ledger.py:180-181`) to cover a finding out of place too.

**`saffron/projection.py` and `saffron/chain_walk.py`**, which read `_db`
(item b-e9db0e). **The vocabulary entry for the fact kinds** (item b-25766a).

**The packed SQL `SA-0117` left in `_apply`** (item b-89ec93). Leave those
lines as they are.

**Deleting tests.** The item asks for the per-kind payload asserts and the
`_db` queries in `tests/test_fold.py` to be deleted. `census` fails any test
collected at base and missing at head, with no override
(`saffron/gates/core/census.py:34-38`). So every test keeps its name, and the
notes say what changes inside it. The `tests/test_fold.py` rewrite waits for
a later change, as its note says.

## Notes for the agent

**No criterion carries a mutant.** Each one not marked `preserves` is new
code. The fact builder, the backfill and the new raises do not exist at
base. So `witness` reports `skip` for each, and that skip is honest.

**Commit as each witness passes.** A long cell can reach its turn limit before
its first commit.

**Nine tests fail against a prototype of this change.** Seven rest on a
premise this spec removes. Two rest on a helper that reads a `finding_id`.
Keep every name and rewrite the body, never delete one.

- `tests/test_ledger.py::test_a_gate_result_must_belong_to_exactly_one_of_them`
  expects `ValueError` for both ids and keeps `sqlite3.IntegrityError` for
  neither.
- `test_a_gate_result_cannot_name_an_attempt_that_does_not_exist` expects
  `ValueError`, and then that the task holds no gate result.
- `test_a_ledger_that_predates_attempts_gains_the_reference`
  (`tests/test_ledger.py:557`) and
  `test_a_ledger_that_predates_both_migrations_opens_and_keeps_its_rows`
  prove the foreign key with `record_gate_result` on attempt 90210. The
  writer now raises before the insert. Prove it with a direct `INSERT` into
  `gate_results` naming that attempt instead, through a connection with
  foreign keys on.
- `tests/test_ledger_appends.py::test_a_ledger_with_no_record_still_writes_rows`
  asserts a 32-character key where it asserted `None`.
- `test_a_pre_record_task_files_no_fact` sets its task's key to `NULL` before
  the reopen. It then asserts the record holds the backfilled key with one
  `task_state` fact. The name now reads against its body. Say so in a
  comment, since `census` keeps the name.
- `test_an_unknown_task_id_files_no_fact` expects `ValueError`, then no key.
- `tests/test_ledger_fold_task.py`'s `_without_finding` (`:74`) filters
  finding facts by `payload["finding_id"]`, and `_break` (`:333`) hands it an
  id. Make `_without_finding` drop the task's nth finding fact. Pass 1 where
  the two preserved tests pass `finding1` or `finding_a`. Each keeps its fault:
  the first finding's fact is gone, and the second stays.

In `tests/test_ledger.py`, `test_two_tasks_cannot_share_one_record_key`'s
comment says both keys start `NULL`. It still passes, but the comment is
false after step 4. Fix the comment.

**The payload asserts in `tests/test_ledger_appends.py`.** Drop each assert
on a payload key that criterion 7's round trip reads back. Where a test then
has none left, assert the kinds its writes appended. Keep
`test_a_declared_risk_and_an_absent_one_are_distinguishable` whole. A `None`
risk and a declared `standard` fold to the same row, so no round trip sees it.
Keep `test_a_gate_error_is_not_recorded_as_a_failure` whole too. Criterion 7's
round trip writes only `fail` results (`tests/test_ledger_fold_task.py:97`).

**`tests/test_fold.py` keeps reading `ledger._db`.** The item asks its
`rows` and `_read` helpers to read the file through a connection of their
own. That rewrite serves no criterion and spent 90 lines on the prototype, so
it waits for a later change. The file is out of `touches`. Its
`test_a_rebuttal_with_no_finding_fact_raises_under_strict` matches
"rebuttal" in the `UnplacedRebuttal` message, so the rewritten message keeps
that word.

**Criterion 1's witness needs a clock it controls.** Read the wall clock as
`datetime.now(UTC)` through `saffron.ledger`'s own `datetime` name, as
`_append` does at `saffron/ledger.py:388`. The witness replaces that name with
a `datetime` subclass whose `now` starts at 2001-01-01 and adds a minute per
call. `_ledger_time` still reaches `fromisoformat` through the subclass. The
minute per call makes
a row dated by a second read of the clock differ from its fact. At base the
writer's rows carry SQLite's clock, so the witness fails there for its own
reason. Share the write sequence with criterion 7's test through one helper.
Leave `_compact` dropping timestamps, so that test stays exact at base. Only
criterion 1's witness compares timestamps.

**Criterion 1 compares whole rows, and so does criterion 7.** Both sides now
run `_apply`, so equality alone cannot see a fault inside it. That is why
criterion 1 also checks each time against the clock, and criterion 2 checks
each placement against what the witness wrote. Run each new witness against
two wrong versions before you trust it: `_apply` stamping `datetime('now')`
for `task_push` alone, and `_apply` finding an attempt by `n` alone. Criterion
1's witness must fail the first, and criterion 2's the second. Say in your
notes what each run printed.

**What each new witness excludes, measured.** A prototype of this change
carried the six witnesses as this spec describes them. Each line below is one
run of all six against the base source or one wrong version of the prototype,
and the witnesses that failed.

- Base source: C1, C2, C3, C4, C5, C6.
- `_apply` stamps `datetime('now')` for `task_push` alone: C1.
- `_apply` stamps `datetime('now')` for every kind: C1.
- The writer dates its row by a second read of the clock: C1.
- An attempt found by `n` alone: C2.
- An attempt found by `phase` alone: C2.
- An attempt taken as the last one opened: C2.
- An attempt found by `(phase, n)` in any task: C2.
- A finding position counted over every task: C2, C3.
- A rebuttal placed on the latest finding: C2.
- A `task_created` fact that carries its `run_id`: C3.
- A `gate_result` fact that carries its `attempt_id`: C3.
- An `attempt_opened` fact that carries the id the insert will mint: C3.
- No key filled in on open: C4, C5.
- `create_task` with no record attached mints no key: C4.
- One key given to every task the open fills in: C4, C5.
- A write to a task with no `task_created` fact appends nothing: C5.
- `record_rebuttal` on an unknown finding returns: C6.
- `close_attempt` on an unknown attempt returns: C6.
- `record_findings` on an unknown task raises `sqlite3.IntegrityError`: C1,
  C2, C3, C6.

The unrelated task's `IMPLEMENT` 1 attempt in criterion 2's writing ledger is
what catches `(phase, n)` looked up in any task. Its finding is what catches a
position counted over every task.

**Criterion 4's witness builds its old files with `sqlite3` and `SCHEMA`.**
The file without the column removes the `record_key` line from `SCHEMA`.
Assert the removal changed the text, as the migration tests in
`tests/test_ledger.py` do.

**Criterion 6's writes need no rows but the empty schema.** Use one id that
no table holds for all ten.

**Read rows in the new witnesses through `_raw_rows`**
(`tests/test_ledger_fold_task.py:43`), never through `ledger._db`. Import
nothing at module scope that this change adds. `revert` runs the new tests with the source reverted, and an import of a new name is
then a collection error it reads as `skip`. All six new witnesses failed
against the base source when measured with a prototype of the change.

**Three halves and one criterion are unmeasured.** The prototype ran before
three parts were added: the ledgers with no record in criteria 1 and 6, and
criterion 13. Each must fail a writer that keeps base's
`if self._record is None` path: criterion 1 when that path still stamps
`datetime('now')`, criterion 6 when it still returns. Criterion 13 must fail
a write method that writes its rows with its own SQL instead of calling
`_apply`.
Criterion 4's old files are opened with no record, so a backfill that runs
only with a record attached fails it. Say in your notes what each run
printed.

**Size.** A prototype of this change measured 865 changed lines. It wrote
new SQL over several lines, as below, and updated the docstrings the change
makes false, `_key`'s at `tests/test_ledger_fold_task.py:83` among them. It
spent 440 in `ledger.py`, 290 in
`tests/test_ledger_fold_task.py`, 90 in `tests/test_fold.py`, 30 in
`tests/test_ledger_appends.py` and 15 in `tests/test_ledger.py`. This spec
drops the 90 in `tests/test_fold.py` and adds about 70 of witness for the
no-record halves and criterion 13, so expect about 845. The
`refactor` ceiling is 1000, and `size` blocks at `elevated`. Write new SQL the
way the file already writes it, as triple-quoted strings over several lines.
Keep new comments to one or two lines.

**Prose.** In each touched file a new or rewritten comment adds to that
file's `prose` count, and a count above base fails. New comments and
docstrings take no em-dash, semicolon, contraction, perfect tense or hedge.
Check each file with `python3 hooks/prose_limit.py --file <path>`.
