---
id: SA-0223
title: A migrated task carries no gate result, so the record loses every attempt's failures and the tier its suite ran at
type: feature
priority: 1
depends_on: [SA-0222]
estimated_lines: 313
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
      `migrate` writes one `gate_result` fact per stored attempt result,
      after its attempt's `attempt_opened`. A result whose
      `gate_results.failures_at_head` is not null keeps its failures and its
      count as stored. A result whose count is null carries what
      `subtract_baseline` leaves of its stored failures against the baseline
      stored on its task's run, and its stored failure count. Where its
      attempt's stored suite aborted or drifted, it keeps every stored
      failure. Each fact carries its attempt's `attempts.earned_risk` as
      `earned_risk`, and every stored value as it is, a null included.
      Folded into a fresh ledger, the record gives back the source's
      `attempts` rows with `earned_risk`. The attempt `gate_results` and
      `failures` rows hold exactly the values above. The witness drives
      twelve members. One is a baseline failure that cancels its match at
      another line. Another is two head copies of one baseline failure, and a
      third is a `witness` failure coded `survived-mutant` at base and at
      head. The fourth is a `tests` baseline failure matching a `lint` head
      failure, and the fifth is a baseline failure stored on another run. The
      sixth is a gate with no failures and a null summary, and the seventh a
      failure with a null message. The eighth is a result stored with a count
      of three over two rows, on an attempt whose tier is `elevated`. The
      ninth is an attempt whose suite holds an `error`, and the tenth one
      whose `lint` tool differs from the baseline's. The eleventh is an
      attempt whose tier is null. The twelfth is a null-tier result on a task
      whose declared tier is `elevated`.
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
      - Each gate result carries the task's `tasks.risk` as its earned tier.
      - An aborted suite is subtracted.
      - A drifted suite is subtracted.
      - Only the result whose status is `error` keeps every failure, not its whole suite.
      - A suite kept whole is counted as its new failures.
      - A null message is carried as an empty one.
      - A null summary is carried as an empty one.
  - claim: >-
      A task whose run stores a baseline result for one gate twice is refused
      where any of its own results has a null count. Nothing is appended
      under its key. `migrate`'s result lists it in `refused` with a reason
      naming that gate, and every other task still migrates. A task on such a
      run whose results all carry a count migrates. The witness drives four
      tasks. Three runs hold `lint` twice and `tests` once. On the first,
      every result is counted, and the task migrates. On the second, one
      result is counted and one is not, and the task is refused. On the
      third, the one uncounted result sits in a suite holding an `error`,
      and the task is refused. The fourth run holds `lint` and `tests` once
      each, with an uncounted result, and the task migrates.
    witness: tests/test_record_migrate.py::test_a_task_whose_run_stores_a_gates_baseline_twice_is_refused_where_it_still_needs_subtracting
    wrong_versions:
      - The task is migrated with both copies subtracted.
      - The refusal raises out of `migrate`, so no task migrates.
      - A run with two baseline results of any gates is refused.
      - Every task on a doubled run is refused, its counts unread.
      - A task is refused only where every one of its results is uncounted.
      - An aborted suite exempts its task from the refusal.
  - claim: >-
      A source whose `gate_results` lacks the `failures_at_head` column and
      whose `attempts` lacks `earned_risk` migrates as if each were null.
      Its stored failures are subtracted and counted, and its earned tier is
      null. The witness migrates such a ledger.
    witness: tests/test_record_migrate.py::test_a_ledger_that_predates_the_head_count_subtracts_its_stored_failures
    wrong_versions:
      - The head count column is read without checking it exists.
      - A missing column is read as a count already taken, so nothing is subtracted.
      - The earned tier column is read without checking it exists.
---

## Context

Backlog item **170**, which cites `DESIGN.md` §4.1, §4.4, §4.6 and §6. Its
design is `docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md`.
This spec is the fourth of five for that design's step 3, the migration.
`SA-0220` changed the gate-result fact. `SA-0221` files a declared tier only
where a spec declared one. `SA-0222` writes every task fact but the gate
results. This spec adds them. `SA-0224` writes the rest of the tables, the
target record per mirror, the push and the `saffron migrate` command.

Line numbers below were read at `ae00877b`. That base carries `SA-0220`,
`SA-0221` and `SA-0222` as queued specs, not as code. This spec is written
against their end states. For `SA-0220` that is its revision after review.
There `record_gate_result` takes a `baseline=` keyword, and a passed one is
the one subtracted, an empty one included. A cell passes `[]` when its suite
drifted or aborted. So a result written after `SA-0220` holds what its cell
kept and a non-null `gate_results.failures_at_head`. Its attempt holds the
suite's tier in a nullable `attempts.earned_risk`.

**What the record keeps of a gate result.** A `gate_result` fact holds new
failures only, plus a count at head
(`docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md:218-224`).
Its §7 applies that to the migration, subtracting the run's stored baseline
(`:351-353`). `DESIGN.md:359` adds that an attempt whose suite drifted or
aborted keeps every failure at head, since §5.4 refuses that subtraction.

**How the cell decides it.** `_compare` returns before it subtracts when a
gate errored, and when `suite_drift` finds the suites differ
(`saffron/gates/suite.py:229-237`). `aborted_gates` names the gates whose
status is `error` (`saffron/gates/suite.py:33-36`). `suite_drift` compares a
gate's `tool` only where it ran on both sides
(`saffron/gates/baseline.py:67-109`). `subtract_baseline` counts, ignores the
line, keeps the gate in the identity and never cancels a `survived-mutant`
failure (`saffron/gates/baseline.py:44-64`).

**What the parent leaves.** `SA-0222`'s criterion 1 claims the `attempts`
rows but for `earned_risk`, because without results the fold never writes
the tier. `_apply`'s `gate_result` branch at base inserts the result and its
failure rows from the fact (`saffron/ledger.py:718-742`). `SA-0220` adds the
count and the tier to it.

**A run can hold a gate's baseline twice.** A stack batch keeps a task for
its rerun (`saffron/batch.py:462-464`). So the rerun's baseline lands on the
same run. Subtracting both would cancel each failure twice, and
`suite_drift` keys the baseline by gate, so it would read only one.

**Measured on a copy of `~/.saffron/ledger.db`, 2026-10-06.** No run stores
any gate's baseline twice. The drift and abort arm keeps one attempt whole.
It aborted, and it stores three failures where the subtraction would leave
two. No attempt drifted. The operator measured the same ledger. Its only
tool differences between an attempt and its baseline are `revert` and
`witness`, from `tool: null` to a real tool. `suite_drift` skips a gate that
did not run at base. A prototype of this
spec migrated all 234 tasks. The fold gave back `tasks`, `attempts`,
`findings` and all 5,150 attempt `gate_results` rows. 2,129,429 stored
attempt failures became 786.

## Problem

1. **The results.** Read each attempt's stored results by `gate_result_id`,
   with their failure rows by `failure_id`. Write one `gate_result` fact per
   result, after its attempt's `attempt_opened` and before any
   `attempt_closed`. Time it at the attempt's `ended_at`, or its
   `started_at` where that is null. Its payload carries `gate`, `status`,
   `tool`, `duration_ms`, `summary`, `failures`, `failures_at_head`,
   `earned_risk`, `phase` and `n`. Each failure carries `file`, `line`,
   `code` and `message`. Every value is the stored value as it is, a null
   included. Build a `Failure` for the subtraction only, with a null message
   read as empty.
2. **The count.** Read each column's presence from `PRAGMA table_info`.
   Where `failures_at_head` is present and not null, copy the failures and
   the count as stored. Otherwise the count is the stored rows. Subtract
   with `subtract_baseline` against the run's stored results, unless the
   attempt's suite aborted or drifted. Use `aborted_gates` and `suite_drift`
   over the attempt's stored results and the run's, with each result's
   `tool`.
3. **The tier.** Each fact carries the attempt's `earned_risk` where the
   column exists, and null otherwise.
4. **Refusal.** Before anything is appended for a task, read its run's
   baseline. Refuse the task where a gate is stored twice and any of the
   task's results has a null count or no count column.

## Out of scope

- The six key-filed tables, the `RefsRecord` per mirror, the push and
  `saffron migrate`. They are `SA-0224`'s, which must list
  `saffron/record/migrate.py::migrate` under `pending_symbols`.
- Run-scoped gate results and `baseline_names`. They are design step 4's.
- `SA-0222`'s witnesses. Their fixtures hold no case this spec changes, so
  they stay as they are. A record that a migration without results already
  filled now disagrees at the first `gate_result`, and the rerun rule
  refuses it. No migration has written a real record yet.
- `DESIGN.md` and `CONTEXT.md` need no edit. `DESIGN.md:359` already states
  the drift rule. The layout at `DESIGN.md:1538` lists `migrate.py`.

## Notes for the agent

**This change is new code inside an existing module.** No text at base
fixes how the results are spelled. So each criterion declares a witness and
no mutant, and the `witness` gate reports `skip` for all three. The wrong
versions under each criterion are what its witness must kill. Do not run
them yourself.

**Commit as each witness passes.** Three witnesses, three commits at least.

**Every witness must fail with `SA-0222`'s module.** It writes no
`gate_result` fact, so each new witness reads rows it never folds.

**Build each source with `Ledger`'s write methods, then close it.** Write
attempt results with `baseline=[]`, so every head failure is stored. Then
null `failures_at_head` through `_db` on the results that stand for a ledger
written before `SA-0220`. Reuse the module's `_source`, `_task`, `_close`,
`_migrated` and `_rows`. Join each child row to its task's `record_key` and
its attempt's `phase`. No criterion reads `~/.saffron`.

**Criterion 1.** Store a `types` baseline failure on another run made first.
Give the task's run a `lint`, `tests`, `witness` and empty `types` baseline.
On the first attempt, record `lint`, `witness` and `types` results and a
`format` result with no failures. On a second attempt, record three `lint`
copies of one baseline failure with a one-copy `baseline=` and
`earned_risk="elevated"`. That stores two rows and a count of three. On a
third, record a `lint` failure the baseline cancels beside a `tests` result
whose status is `error`. On a fourth, record a cancelled `lint` failure
under another `tool`. Null the counts of the first, third and fourth. Null
the `types` failure's message and the `format` summary through `_db`. Give a
second, `elevated` task one closed attempt holding one passing result. Then
compare the folded `attempts` rows, `earned_risk` included, with the
source's.

**Criterion 2.** Null the counts explicitly, as the four tasks need them.
Assert `migrated` and `refused` as exact lists.

**Criterion 3.** Make the source with `Ledger`, then drop both columns with
`ALTER TABLE ... DROP COLUMN` and close it.

**Where the claims stop.** The arm's members are one aborted and one
drifted attempt. A gate that ran at head and was skipped there is the other
shape `suite_drift` reports, and no witness drives it. A doubled run whose
task has no result at all migrates, and no witness drives that either.

**Measured on a prototype at `ae00877b`.** The prototype was `SA-0222`'s,
with `SA-0220`'s stand-in in `saffron/ledger.py`. On it, all three new
witnesses passed, and each failed with `SA-0222`'s module. `SA-0222`'s three
witnesses passed on both. The change measured 1253 changed tokens under
`size_gate`. Each of the 27 wrong versions above was applied to it as an
edit. Each failed its own criterion's witness, on the assertion its sentence
names.
