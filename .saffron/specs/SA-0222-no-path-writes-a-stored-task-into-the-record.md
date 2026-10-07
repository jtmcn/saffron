---
id: SA-0222
title: No path writes a stored task into the record, so the ledger's tasks cannot move to `refs/saffron/*` without importing a defaulted tier and every failure the baseline cancels
type: feature
priority: 1
depends_on: [SA-0221]
estimated_lines: 517
estimate_measured: true
touches:
  - saffron/record/migrate.py
  - tests/test_record_migrate.py
pending_symbols:
  - saffron/record/migrate.py::migrate
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
  - harness/**
  - records/**
  - hooks/**
  - images/**
  - saffron/ledger.py
  - saffron/cli.py
  - saffron/gates/**
  - saffron/record/__init__.py
  - saffron/record/contract.py
  - saffron/record/fold.py
  - saffron/record/memory.py
  - saffron/record/refs.py
  - tests/test_fold.py
  - tests/test_ledger.py
  - tests/test_ledger_appends.py
  - tests/test_ledger_fold_task.py
  - tests/test_record.py
  - tests/test_record_refs.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 30
max_attempts: 3
max_turns: 180
acceptance:
  - claim: >-
      `migrate(source, record)` in a new `saffron/record/migrate.py` appends
      every task of the ledger at `source` to `record`, each under its own
      `tasks.record_key`. Folded into a fresh ledger, that record gives back
      the source's `tasks`, `attempts` and `findings` rows as multisets, with
      every id column left out. One column changes by rule. A task's
      `spent_usd_est` is the sum of its attempts' `cost_usd_est`. Each
      task's `task_created` fact carries a null `risk` where the column reads
      `standard`, and `elevated` where it reads `elevated`. Every fact
      carries the task's repo name, and as `batch_key` its run's `batch_id`
      as text, or null for a run with no batch. Where the runs started in
      `task_id` order, the fold lists the tasks in that order. The witness
      runs with local time away
      from UTC, over three tasks. The first is `standard`, on a batched run,
      packaged with a diff stat, merged, and holds three findings. One is
      rebutted, one carries a verdict alone and one neither. The second is
      `elevated`, pushed with no pull request, and holds a closed attempt
      after its last state, so its stored spend is stale, and an open
      attempt. The third has no attempt and no push.
    witness: tests/test_record_migrate.py::test_a_migrated_ledger_folds_back_to_the_rows_its_tasks_held
    wrong_versions:
      - The `task_created` fact copies `tasks.risk`, so a defaulted `standard` reads as declared.
      - Every `task_created` fact carries a null tier, so `elevated` is lost.
      - A fact's time is the ledger's text with no offset, so the fold reads it as local time.
      - No closing `task_state` fact, so a merged task folds to its packaged state.
      - A task pushed with no pull request gets no push fact.
      - An open attempt gets an `attempt_closed` fact.
      - A rebuttal fact is written only where the rebuttal text is not null, so a lone verdict is lost.
      - No `task_merged_head` fact.
      - Each gate result carries the task's `tasks.risk` as its earned tier.
      - The `task_package` fact leaves out the diff stat.
      - The `task_created` fact is timed at the task's `updated_at`, so the fold reorders the tasks.
      - An unanchored finding is left out.
      - Every fact carries a null `batch_key`.
      - The `batch_key` is the integer `batch_id` rather than its text.
  - claim: >-
      Each `gate_result` fact `migrate` writes carries, as `failures`, what
      `subtract_baseline` leaves of that result's stored failures against the
      baseline stored on its task's run. Its `failures_at_head` is the stored
      failure count. A result whose `gate_results.failures_at_head` is not
      null was subtracted when it was written. Its failures and its count are
      copied as stored. Every fact carries its attempt's `attempts.earned_risk`
      as `earned_risk`. Folded, the `gate_results` and `failures` rows hold
      exactly those values. The witness drives eight members. One is a
      baseline failure that cancels its match at another line. Another is
      two head copies of one baseline failure, and a third is a `witness`
      failure coded `survived-mutant` at base and at head. The fourth is a
      `tests` baseline failure matching a `lint` head failure, and the fifth
      is a baseline failure stored on another run. The sixth is a gate with
      no failures. The seventh is a result stored with a count of three over
      two rows, on an attempt whose tier is `elevated`. The eighth is an
      attempt whose tier is null.
    witness: tests/test_record_migrate.py::test_a_migrated_attempt_keeps_only_the_failures_its_runs_baseline_did_not_cancel
    wrong_versions:
      - Every stored failure is kept.
      - The subtraction is a set difference, so one baseline failure cancels both head copies.
      - The comparison includes the line, so a failure the diff moved stays new.
      - The baseline of every run in the ledger is subtracted.
      - The gate is left out of the identity, so a `tests` baseline failure cancels a `lint` one.
      - A `survived-mutant` failure at base cancels the one at head.
      - "`failures_at_head` counts the new failures rather than the stored ones."
      - A gate with no failures carries a null count.
      - A result stored with a count is subtracted again.
      - A result stored with a count carries its row count instead.
      - The stored earned tier is dropped.
  - claim: >-
      A task whose run stores a baseline result for one gate twice is
      refused. Nothing is appended under its key. `migrate`'s result lists
      it in `refused` with a reason naming that gate, and every other task
      still migrates. The witness drives a run holding `lint` twice and
      `tests` once, whose task holds an attempt with a gate result. Beside
      it is a run holding `lint` and `tests` once each.
    witness: tests/test_record_migrate.py::test_a_task_whose_run_stores_a_gates_baseline_twice_is_refused_and_the_rest_migrate
    wrong_versions:
      - The run is migrated with both copies subtracted.
      - The refusal raises out of `migrate`, so no task migrates.
      - A run with two baseline results of any gates is refused.
  - claim: >-
      Before it appends, `migrate` reads the facts a key already holds. Where
      they equal the start of the list it would write, it appends only the
      rest. Where they do not, it appends nothing under that key and lists it
      in `refused`, and the other keys still migrate. The witness migrates
      one ledger of four tasks into a record that holds nothing for the
      first, the first two facts for the second and every fact for the
      third. For the fourth it holds a first fact whose `spec_sha` differs,
      then the true second fact.
    witness: tests/test_record_migrate.py::test_a_rerun_completes_a_migration_cut_short_and_refuses_a_record_that_disagrees
    wrong_versions:
      - A key that holds any fact is skipped.
      - Every fact is appended whatever the key holds.
      - Only the lengths are compared.
      - Only the fact kinds are compared.
      - A key that disagrees raises out of `migrate`.
  - claim: >-
      `migrate` opens the source with SQLite's read-only mode, so the source
      file's bytes are the same after it runs. A source whose `gate_results`
      lacks the `failures_at_head` column and whose `attempts` lacks
      `earned_risk` migrates as if each were null. Its stored failures are
      subtracted and counted. The witness migrates such a ledger and compares
      the file's SHA-256 before and after.
    witness: tests/test_record_migrate.py::test_a_ledger_that_predates_the_head_count_migrates_and_is_left_unwritten
    wrong_versions:
      - The source is opened through `Ledger`, whose open adds the missing columns.
      - The head count column is read without checking it exists.
      - A missing column is read as a count already taken, so nothing is subtracted.
---

## Context

Backlog item **170**, which cites `DESIGN.md` §4.1, §4.4, §4.6 and §6. Its
design is `docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md`.
That design's steps 1 and 2 are built. This spec is the third of four for its
step 3, the migration. `SA-0220` changed the gate-result fact. `SA-0221`
files a declared tier only where a spec declared one. This spec builds the
facts from a stored ledger. `SA-0223` writes the rest of the tables, the
target record per mirror, the push and the `saffron migrate` command.

Line numbers below were read at `15fc7c74`. That base carries `SA-0220` and
`SA-0221` as queued specs, not as code. This spec is written against their
end state. For `SA-0220` that is its revision after review. There
`record_gate_result` takes a `baseline=` keyword, and a passed one is the one
subtracted, an empty one included. A cell passes `[]` when its suite drifted
or aborted. So a result written after `SA-0220` holds its new failures and a
non-null `gate_results.failures_at_head`. Its attempt holds the suite's tier
in a nullable `attempts.earned_risk`.

**What design §7 asks.** All stored tasks move into the record. A field the
ledger cannot vouch for is absent, not defaulted
(`docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md:326-327`).
A tier is written where the spec declared one (`:329-330`). The migration
writes each attempt's new failures, subtracting the run's stored baseline
(`:351-353`). §4's test is to rebuild the ledger and get the same rows
(`:251`).

**A stored `standard` is a default.** `tasks.risk` is
`NOT NULL DEFAULT 'standard'` (`saffron/ledger.py:128`). The fold writes
`standard` into it for a null declared tier (`saffron/ledger.py:669`). So a
null `risk` on the fact folds back to the same column value.

**The fold already rebuilds these rows from facts.** `fold` reads every key
and calls `Ledger.fold_task` (`saffron/record/fold.py:42-66`). It orders keys
by their `task_created` fact's `at` (`saffron/record/fold.py:95-118`).
`_apply` turns each kind into rows (`saffron/ledger.py:663-906`). Three of its
branches decide the fact list below.

- `task_created` takes `origin`, `mirror_path` and `base_sha` from the payload
  to find or make the run (`saffron/ledger.py:594-622`).
- `task_state` sets `updated_at` and recomputes `spent_usd_est` as the sum of
  the task's attempts (`saffron/ledger.py:743-750`). No fact carries a stored
  spend.
- `finding` refuses a position that is not the next one
  (`saffron/ledger.py:807-813`).

**Fact times.** `_ledger_time` reads `Fact.at` with `fromisoformat` and
converts it to UTC (`saffron/ledger.py:318-321`). A ledger time is UTC text
with no offset. Read without one, it is taken as local time.

**The closest prototype applies neither rule.**
`docs/evidence/scripts/2026-09-20-fold-rebuild-time.py:34-79` replays a
ledger through `Ledger`'s write methods. It passes `risk=task["risk"]`
(`:53`), so a default reads as declared, and it never stores a baseline.

**Measured on a copy of `~/.saffron/ledger.db`, 2026-10-06.** 234 tasks, all
on one repo, all with a `record_key`. No run holds two tasks, and no run
stores any gate's baseline twice. One task was in flight, and its stored
spend was stale. The runs' `started_at` rose with `task_id`, with no tie. The
prototype below migrated all 234 into a `MemoryRecord` in 152 s. The fold gave
back `tasks`, `attempts`, attempt `gate_results` and `findings` as criterion 1
states them. 2,129,429 stored attempt failures became 785.

## Problem

1. **The module.** Add `saffron/record/migrate.py` with
   `migrate(source: Path, record: Record) -> Migration`. `Migration` is a
   dataclass of `migrated`, a list of task keys in source order, and
   `refused`, a list of `(key, reason)` pairs. Open `source` with
   `sqlite3.connect(f"{source.resolve().as_uri()}?mode=ro", uri=True)`.
   Read with explicit SQL. Never construct a `Ledger` on the source, and
   never use `Ledger`'s write methods. Build each `Fact` directly.
2. **The facts, per task in `task_id` order.**
   - `task_created`, at the run's `started_at`. Its payload carries the
     keys `create_task` files (`saffron/ledger.py:1272-1316`), from the task,
     run and repo rows. `risk` is null where the column reads `standard`.
   - Per attempt, by `attempt_id`: `attempt_opened` at `started_at`. Then
     one `gate_result` per result, by `gate_result_id`. Then
     `attempt_closed` at `ended_at`, only where `ended_at` is not null. Its
     payload carries the keys `close_attempt` files
     (`saffron/ledger.py:1373-1398`).
   - One `finding` per finding by `finding_id`, `position` from 1. Then a
     `rebuttal` for each finding whose `verdict` or `rebuttal` is not null.
   - `task_merged_head` where `merged_head_sha` is not null.
   - `task_package` where `pr_url` is not null, else `task_push` where
     `pushed_sha` is not null.
   - `task_state` last, at `updated_at`.
   Every `at` is the ledger time with `+00:00`. A fact with no time of its
   own takes the attempt's `ended_at` or `started_at`, or the task's
   `updated_at`.
3. **A gate result.** Its payload carries `gate`, `status`, `tool`,
   `duration_ms`, `summary`, `failures`, `failures_at_head`, `earned_risk`,
   `phase` and `n`. Where the stored count is null or its column is absent,
   subtract with `subtract_baseline` (`saffron/gates/baseline.py:44-66`)
   against the run's stored results, and count the stored rows. Otherwise
   copy both as stored. Read each column's presence from `PRAGMA table_info`.
4. **Refusal.** Read the run's baseline before anything is appended for the
   task. A gate stored twice refuses the task.
5. **A rerun.** For each key, compare `record.read(key)` with the start of
   the list. Append the rest where they agree. Refuse the key where they do
   not.

## Out of scope

- The six key-filed tables, `stack_layers`, `end_reviews`, `spec_reviews`,
  `qualifications`, `spec_texts` and `stack_finishes`. Each is `SA-0223`'s,
  with the `RefsRecord` per mirror, the push and the `saffron migrate`
  command. `SA-0223` must list `saffron/record/migrate.py::migrate` under
  `pending_symbols`, since this spec retires first.
- Run-scoped gate results, `baseline_names`, `batches`, and a run's status
  and preflight. They are design step 4's. The fold makes its own `runs` rows
  (`saffron/ledger.py:594-622`), and this spec compares none of them.
- The `adjudication` column of `findings`. No fact carries it. The schema
  says "Nothing produces an adjudication yet" (`saffron/ledger.py:208-209`).
- A task with no record key. The ledger's open backfills one where
  `record_key IS NULL` (`saffron/ledger.py:373-382`). The measured ledger
  has none.
- `docs/evidence/scripts/2026-09-20-fold-rebuild-time.py` keeps its own
  synthesis.
- `DESIGN.md` §10's layout gains `migrate.py` by hand in this spec's pull
  request, since `DESIGN.md` is protected.

## Notes for the agent

**This change is new code.** No text at base fixes how the module is
spelled. So each criterion declares a witness and no mutant, and the
`witness` gate reports `skip` for all five. The wrong versions under each
criterion are what its witness must kill. Do not run them yourself.

**Commit as each witness passes.** Five witnesses, five commits at least.

**Every witness must fail with the source reverted.** Import
`saffron.record.migrate` inside each test, never at module scope.

**Build each source with `Ledger`'s write methods, then close it.** Write
attempt results with `baseline=[]`, so every head failure is stored. Then
set `failures_at_head` to null on the results that stand for a ledger written
before `SA-0220`. Fold with `saffron.record.fold.fold` into a fresh `Ledger`.
Compare with `collections.Counter` over row tuples. Join each child row to its
task's `record_key`, and to its attempt's `phase` and `n`. No criterion reads
`~/.saffron`.

**Criterion 1.** Set `TZ` to `America/Los_Angeles` with `monkeypatch` and
call `time.tzset()`, then again after `undo()`. Set each run's `started_at`
an hour apart through `_db`, so the creation order is not a tie. Give the
third task an `updated_at` earlier than the other two tasks' `updated_at`. A
creation timed at `updated_at` then sorts it first. Read the expected `tasks` rows
from the source with the spend replaced by
`(SELECT COALESCE(SUM(cost_usd_est), 0.0) FROM attempts a WHERE a.task_id = t.task_id)`.
Attach the first task's run with `create_batch` and `attach_run_to_batch`.

**Criterion 2.** Store a `types` baseline failure on another run made first.
Give the task's run a `lint`, `tests`, `witness` and empty `types` baseline.
On the first attempt, record `lint`, `witness` and `types` results and a
`format` result with no failures, then null their counts. On a second attempt, record three `lint`
copies of one baseline failure with a one-copy `baseline=` and
`earned_risk="elevated"`. That stores two rows and a count of three. A second
subtraction would leave one.

**Criterion 4.** Migrate the ledger once into a fresh `MemoryRecord` for the
expected lists. Build the second record from them, then migrate into it.

**Criterion 5.** Make the source with `Ledger`, then drop both columns with
`ALTER TABLE ... DROP COLUMN` and close it. Hash the file itself. A read-only
open of a WAL ledger leaves `-wal` and `-shm` files beside it, so do not
hash the directory.

**Where the claims stop.** Criterion 5 drives a path under `tmp_path`. The
`as_uri()` form also escapes a `?` or `#` in a path, and no witness drives
one. It drives a ledger that predates both columns. Measured on the
prototype, reopening a current ledger through `Ledger` left its bytes as
they were, so only the older shape shows that wrong version. A task whose
stored rows change between two runs is refused on the second, by criterion
4's rule. Criterion 1
orders tasks by their runs' `started_at`. The measured ledger's runs started
in `task_id` order, and no witness drives a source whose runs did not.

**Measured on a prototype at `15fc7c74`.** The prototype added `SA-0220`'s
two columns, its fold and its `baseline=` and `earned_risk=` keywords to
`saffron/ledger.py` as a stand-in. On it, all five witnesses passed, and each
failed with the module removed. Its module and witnesses measured 2066
changed tokens under `size_gate`. Each of the 36 wrong versions above was
applied to it as an edit. Each failed its own criterion's witness, on the
assertion its sentence names.
