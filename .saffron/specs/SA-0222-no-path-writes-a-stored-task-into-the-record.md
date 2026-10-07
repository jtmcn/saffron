---
id: SA-0222
title: No path writes a stored task into the record, so the ledger's tasks cannot move to `refs/saffron/*` without importing a defaulted tier as declared
type: feature
priority: 1
depends_on: [SA-0221]
estimated_lines: 362
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
budget_usd: 26
max_attempts: 3
max_turns: 180
acceptance:
  - claim: >-
      `migrate(source, record)` in a new `saffron/record/migrate.py` appends
      every task of the ledger at `source` to `record`, each under its own
      `tasks.record_key`. It writes every task fact kind but `gate_result`.
      Folded into a fresh ledger, that record gives back the source's `tasks`
      and `findings` rows, and its `attempts` rows but for `earned_risk`, as
      multisets with every id column left out. One column changes by rule. A
      task's `spent_usd_est` is the sum of its attempts' `cost_usd_est`. On
      the facts themselves, each `task_created` fact carries a null `risk`
      where the column reads `standard`, and `elevated` where it reads
      `elevated`. Every fact carries the task's repo name, and as `batch_key`
      its run's `batch_id` as text, or null for a run with no batch. Every
      `at` is the ledger time in the `T` form with `+00:00`. Where the runs
      started in `task_id` order, the fold lists the tasks in that order. The
      witness runs with local time away from UTC, over four tasks. The first
      is `standard`, on a batched run, packaged with a diff stat, merged, and
      holds four findings. One is rebutted, one carries a verdict alone, one
      a rebuttal alone and one neither. The second is `elevated`, pushed with
      no pull request, and holds a closed attempt after its last state, so
      its stored spend is stale, and an open attempt. The third has no
      attempt and no push. The fourth is `MERGE_FAILED` with an empty
      `pr_url` and a branch that differs from its creation.
    witness: tests/test_record_migrate.py::test_a_migrated_ledger_folds_back_to_the_rows_its_tasks_held
    wrong_versions:
      - The `task_created` fact copies `tasks.risk`, so a defaulted `standard` reads as declared.
      - Every `task_created` fact carries a null tier, so `elevated` is lost.
      - A fact's time is the ledger's text with no offset, so the fold reads it as local time.
      - A fact's time uses a space where the live form has `T`.
      - No closing `task_state` fact, so a merged task folds to its packaged state.
      - A task pushed with no pull request gets no push fact.
      - An empty `pr_url` is read as no pull request, so the task gets a push fact instead.
      - An open attempt gets an `attempt_closed` fact.
      - A rebuttal fact is written only where the rebuttal text is not null.
      - A rebuttal fact is written only where the verdict is not null.
      - No `task_merged_head` fact.
      - The `task_package` fact leaves out the diff stat.
      - The `task_created` fact is timed at the task's `updated_at`, so the fold reorders the tasks.
      - An unanchored finding is left out.
      - Every fact carries a null `batch_key`.
      - The `batch_key` is the integer `batch_id` rather than its text.
      - Every fact carries the repo's origin as its repo.
  - claim: >-
      Before it appends, `migrate` reads the facts a key already holds. Where
      they equal the start of the list it would write, it appends only the
      rest and lists the key in `migrated`, a key it had nothing left to add
      to included. Where they do not, it appends nothing under that key and
      lists it in `refused`, and the other keys still migrate. The witness
      migrates one ledger of five tasks. Every fact it holds has been through
      `Fact.to_json` and `Fact.from_json`, as `RefsRecord.read` returns them.
      It holds nothing for the first task, the first two facts for the second
      and every fact for the third. For the fourth it holds a first fact
      whose `spec_sha` differs, then the true second fact. For the fifth it
      holds the true first two facts, then a third whose `cost_usd_est`
      differs.
    witness: tests/test_record_migrate.py::test_a_rerun_completes_a_migration_cut_short_and_refuses_a_record_that_disagrees
    wrong_versions:
      - A key that holds any fact is skipped.
      - Every fact is appended whatever the key holds.
      - Only the lengths are compared.
      - Only the fact kinds are compared.
      - Only the `task_created` fact is compared.
      - A key that disagrees raises out of `migrate`.
      - A key that holds every fact is left out of `migrated`.
  - claim: >-
      `migrate` opens the source with SQLite's read-only mode, so the source
      file's bytes are the same after it runs. The witness migrates a ledger
      whose `gate_results` lacks `failures_at_head` and whose `attempts`
      lacks `earned_risk`, and compares the file's SHA-256 before and after.
      That task and its attempt still migrate.
    witness: tests/test_record_migrate.py::test_a_ledger_that_predates_the_head_count_migrates_and_is_left_unwritten
    wrong_versions:
      - The source is opened through `Ledger`, whose open adds the missing columns.
---

## Context

Backlog item **170**, which cites `DESIGN.md` §4.1, §4.4, §4.6 and §6. Its
design is `docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md`.
That design's steps 1 and 2 are built. This spec is the third of five for its
step 3, the migration. `SA-0220` changed the gate-result fact. `SA-0221`
files a declared tier only where a spec declared one. This spec builds every
task fact but the gate results from a stored ledger. `SA-0223` adds the
`gate_result` facts, with the baseline subtraction and its refusal. `SA-0224`
writes the rest of the tables, the target record per mirror, the push and the
`saffron migrate` command.

Line numbers below were read at `3addd3c7`. That base carries `SA-0220` and
`SA-0221` as queued specs, not as code. This spec reads no column either of
them adds.

**What design §7 asks.** All stored tasks move into the record. A field the
ledger cannot vouch for is absent, not defaulted
(`docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md:326-327`).
A tier is written where the spec declared one (`:329-330`). §4's test is to
rebuild the ledger and get the same rows (`:251`).

**A stored `standard` is a default.** `tasks.risk` is
`NOT NULL DEFAULT 'standard'` (`saffron/ledger.py:128`). The fold writes
`standard` into it for a null declared tier (`saffron/ledger.py:669`). So a
null `risk` on the fact folds back to the same column value, and only the
fact shows the difference.

**The fold already rebuilds these rows from facts.** `fold` reads every key
and calls `Ledger.fold_task` (`saffron/record/fold.py:42-66`). It orders keys
by their `task_created` fact's `at`, sorted as text
(`saffron/record/fold.py:95-118`). `_apply` turns each kind into rows
(`saffron/ledger.py:663-906`). Three of its branches decide the fact list
below.

- `task_created` takes `origin`, `mirror_path` and `base_sha` from the payload
  to find or make the run (`saffron/ledger.py:594-622`).
- `task_state` sets `updated_at` and recomputes `spent_usd_est` as the sum of
  the task's attempts (`saffron/ledger.py:743-750`). No fact carries a stored
  spend.
- `finding` refuses a position that is not the next one
  (`saffron/ledger.py:807-813`).

**Fact times.** `_ledger_time` reads `Fact.at` with `fromisoformat` and
converts it to UTC (`saffron/ledger.py:318-321`). A ledger time is UTC text
with no offset. Read without one, it is taken as local time. A live fact's
`at` is `datetime.now(UTC).isoformat()` (`saffron/ledger.py:524-530`), so it
carries a `T`.

**An empty pull request URL is stored.** `PackageResult` defaults `pr_url`
to `""` (`saffron/phases/package.py:594-600`), and PACKAGE's failure paths
reach `set_task_package` with it.

**The closest prototype applies no rule.**
`docs/evidence/scripts/2026-09-20-fold-rebuild-time.py:34-79` replays a
ledger through `Ledger`'s write methods. It passes `risk=task["risk"]`
(`:53`), so a default reads as declared.

**Measured on a copy of `~/.saffron/ledger.db`, 2026-10-06.** 234 tasks, all
on one repo, all with a `record_key`. One task was in flight, and its stored
spend was stale. The runs' `started_at` rose with `task_id`, with no tie. A
prototype of this spec migrated all 234 into a `MemoryRecord`. The fold gave
back `tasks`, `attempts` and `findings` as criterion 1 states them.

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
     `attempt_closed` at `ended_at`, only where `ended_at` is not null. Its
     payload carries the keys `close_attempt` files
     (`saffron/ledger.py:1373-1398`).
   - One `finding` per finding by `finding_id`, `position` from 1. Then a
     `rebuttal` for each finding whose `verdict` or `rebuttal` is not null.
   - `task_merged_head` where `merged_head_sha` is not null.
   - `task_package` where `pr_url` is not null, an empty one included, else
     `task_push` where `pushed_sha` is not null.
   - `task_state` last, at `updated_at`.
   Every `at` is the ledger time parsed with `fromisoformat`, given UTC, and
   written with `isoformat()`. Findings and the outcome facts take the task's
   `updated_at`. Every payload value is the stored value as it is, a null
   included.
3. **A rerun.** For each key, compare `record.read(key)` with the start of
   the list. Append the rest where they agree, and list the key in
   `migrated`. Refuse the key where they do not.

## Out of scope

- `gate_result` facts. They are `SA-0223`'s, with the baseline subtraction
  and the drift and abort arm. The earned tier and the refusal of a doubled
  baseline are its too. Until then a folded ledger has no attempt
  `gate_results`, no `failures` and a null `attempts.earned_risk`.
- The six key-filed tables, `stack_layers`, `end_reviews`, `spec_reviews`,
  `qualifications`, `spec_texts` and `stack_finishes`. Each is `SA-0224`'s,
  with the `RefsRecord` per mirror, the push and the `saffron migrate`
  command. `SA-0223` and `SA-0224` must each list
  `saffron/record/migrate.py::migrate` under `pending_symbols`, since this
  spec retires first.
- Run-scoped gate results, `baseline_names`, `batches`, and a run's status
  and preflight. They are design step 4's. The fold makes its own `runs` rows
  (`saffron/ledger.py:594-622`), and this spec compares none of them.
- The `adjudication` column of `findings`. No fact carries it. The schema
  says "Nothing produces an adjudication yet" (`saffron/ledger.py:208-209`).
- A task with no record key. The ledger's open backfills one where
  `record_key IS NULL` (`saffron/ledger.py:373-382`). The measured ledger
  has none.
- Events. The design's rule that every append also emits an event binds once
  a production `Ledger` holds a record
  (`docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md:365-367`).
  None does, so the migration emits no events.
- `docs/evidence/scripts/2026-09-20-fold-rebuild-time.py` keeps its own
  synthesis.

## Notes for the agent

**This change is new code.** No text at base fixes how the module is
spelled. So each criterion declares a witness and no mutant, and the
`witness` gate reports `skip` for all three. The wrong versions under each
criterion are what its witness must kill. Do not run them yourself.

**Commit as each witness passes.** Three witnesses, three commits at least.

**Every witness must fail with the source reverted.** Import
`saffron.record.migrate` inside each test, never at module scope.

**Build each source with `Ledger`'s write methods, then close it.** Fold
with `saffron.record.fold.fold` into a fresh `Ledger`. Compare with
`collections.Counter` over row tuples. Join each child row to its task's
`record_key`, and to its attempt's `phase` and `n`. No criterion reads
`~/.saffron`.

**Criterion 1.** Set `TZ` to `America/Los_Angeles` with `monkeypatch` and
call `time.tzset()`, then again after `undo()`. Set each run's `started_at`
an hour apart through `_db`, so the creation order is not a tie. Give the
third task an `updated_at` earlier than the other tasks' `updated_at`. A
creation timed at `updated_at` then sorts it first. Read the expected `tasks`
rows from the source with the spend replaced by
`(SELECT COALESCE(SUM(cost_usd_est), 0.0) FROM attempts a WHERE a.task_id = t.task_id)`.
Attach the first task's run with `create_batch` and `attach_run_to_batch`.
Read the facts from the record as well as the rows. Assert each task's
declared `risk`, each fact's `repo` and `batch_key`, and the first task's
`task_created` time as the exact string. Package the fourth task with
`set_task_package(task, "MERGE_FAILED", <another branch>, <sha>, "")`.

**Criterion 2.** Migrate the ledger once into a fresh `MemoryRecord`, and
pass each fact through `Fact.from_json(fact.to_json())` for the expected
lists. Build the second record from them, then migrate into it. Assert
`migrated` and `refused` as exact lists.

**Criterion 3.** Make the source with `Ledger`, then drop both columns with
`ALTER TABLE ... DROP COLUMN` and close it. Hash the file itself. A read-only
open of a WAL ledger leaves `-wal` and `-shm` files beside it, so do not
hash the directory.

**Where the claims stop.** Criterion 3 drives a path under `tmp_path`. The
`as_uri()` form also escapes a `?` or `#` in a path, and no witness drives
one. It drives a ledger that predates both columns. Measured on the
prototype, reopening a current ledger through `Ledger` left its bytes as
they were, so only the older shape shows that wrong version. A task whose
stored rows change between two runs is refused on the second, by criterion
2's rule. Criterion 1 orders tasks by their runs' `started_at`. The measured
ledger's runs started in `task_id` order, and no witness drives a source
whose runs did not. No witness drives a stored null `model` or `line`.

**Measured on a prototype at `3addd3c7`.** The prototype added `SA-0220`'s
two columns to `saffron/ledger.py` as a stand-in, so criterion 3 could drop
them. On it, all three witnesses passed, and each failed with the module
removed. Its module and witnesses measured 1446 changed tokens under
`size_gate`. Each of the 25 wrong versions above was applied to it as an
edit. Each failed its own criterion's witness, on the assertion its sentence
names.
