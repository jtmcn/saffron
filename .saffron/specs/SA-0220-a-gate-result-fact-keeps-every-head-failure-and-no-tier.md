---
id: SA-0220
title: A gate-result fact keeps every failure at head and no tier, so the record carries what the baseline cancels and drops the tier the suite ran at
type: feature
priority: 1
estimated_lines: 295
estimate_measured: true
touches:
  - saffron/ledger.py
  - saffron/cell/session.py
  - tests/test_ledger.py
  - tests/test_ledger_appends.py
  - tests/test_ledger_fold_task.py
  - tests/test_fold.py
  - tests/test_session.py
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
  - saffron/view/**
  - saffron/record/**
  - saffron/gates/**
  - saffron/projection.py
  - saffron/chain_walk.py
  - saffron/replay.py
  - saffron/intake.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/follow_up.py
  - tests/test_view_graph.py
  - tests/test_view_server.py
  - tests/test_replay.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 32
max_attempts: 3
max_turns: 180
risk: elevated
acceptance:
  - claim: >-
      `Ledger.record_gate_result(result, attempt_id=...)` writes, as the
      `gate_result` fact's `failures` and as that result's `failures` rows,
      only what `subtract_baseline([result], baseline)` leaves. Here
      `baseline` is the baseline results stored for the run of the attempt's
      own task. The fact's `failures_at_head` key and a new nullable
      `gate_results.failures_at_head` column hold `len(result.failures)`,
      and `0` for a result with none. A run's baseline result keeps every
      failure and a null count. The witness drives six members. One is a
      baseline failure that cancels its match at another line. Another is two
      head copies of one baseline failure, and a third is a `witness`
      failure coded `survived-mutant` at base and at head. The fourth is a
      `tests` baseline failure matching a `lint` head failure, the fifth is
      a baseline failure stored on another run, and the sixth is a gate
      with no failures.
    witness: tests/test_ledger_appends.py::test_an_attempts_gate_result_keeps_only_its_new_failures
    wrong_versions:
      - The fact and the rows carry every failure at head.
      - The subtraction is a set difference, so one baseline failure cancels both head copies.
      - The comparison includes the line number, so a failure the diff moved stays new.
      - The baseline of every run in the ledger is subtracted.
      - A baseline failure of any gate cancels a head failure with the same file, code and message.
      - A `survived-mutant` failure at base cancels the one at head.
      - "`failures_at_head` counts the new failures rather than the failures at head."
      - A gate with no failures stores a null count.
      - A run's baseline result is given a count of its own.
  - claim: >-
      `record_gate_result` takes a keyword `earned_risk`, `None` by default,
      and writes it as the `gate_result` fact's `earned_risk` key, a null
      value included. A non-null value sets a new nullable
      `attempts.earned_risk` on that attempt alone, and the last non-null
      value wins. A null value leaves the column as it was. The witness drives
      `standard` and `elevated` on one attempt, the argument omitted, and
      three attempts of one task.
    witness: tests/test_ledger_appends.py::test_a_gate_result_carries_the_tier_its_suite_ran_at
    wrong_versions:
      - The first non-null tier wins.
      - A null tier clears the column.
      - The tier reaches the fact and never the column.
      - The tier is written on every attempt of the task.
      - The key is left out of the fact when the tier is null.
  - claim: >-
      A fold into a fresh ledger writes `gate_results.failures_at_head`, the
      `failures` rows and `attempts.earned_risk` exactly as the facts carry
      them. A `gate_result` fact with neither key, as every fact written
      before this change is, folds to a null count and leaves the attempt's
      tier as it was. The witness drives a `standard` attempt, an `elevated`
      one and a fact with neither key.
    witness: tests/test_fold.py::test_the_fold_keeps_new_failures_the_head_count_and_the_tier
    wrong_versions:
      - The fold writes a null count whatever the fact carries.
      - The fold writes no tier.
      - A fact with no `failures_at_head` key raises.
      - A fact with no `earned_risk` key clears the attempt's tier.
  - claim: >-
      Each gate result a cell's suite records against an attempt carries the
      tier that suite ran at, `SuiteRun.effective_risk`. Its `failures` rows
      keep only what the run's baseline did not cancel. An attempt no suite
      judged reads a null tier. The witness drives a spec whose diff matches
      `elevate_on`, which reads `elevated`, and one whose diff does not,
      which reads `standard`.
    witness: tests/test_session.py::test_an_attempts_rows_carry_its_suites_tier_and_only_its_new_failures
    wrong_versions:
      - The suite records no tier.
      - The suite records the tier the spec declared.
      - The suite records the baseline run's tier.
      - The tier lands on the task's first attempt rather than the judged one.
      - The cell's attempt rows keep every failure at head.
  - claim: >-
      A ledger whose tables predate both columns gains both when it is
      opened. A row written before reads null in each, and a row written
      after carries its values. The witness drives a ledger whose
      `gate_results` already references `attempts`, and a v0.5 ledger whose
      `gate_results` the open rebuilds.
    witness: tests/test_ledger.py::test_a_ledger_that_predates_the_head_count_and_the_tier_gains_both
    wrong_versions:
      - No column is added to `gate_results` on open.
      - No column is added to `attempts` on open.
      - The v0.5 rebuild lists its columns without the new one, so the column added before it is dropped.
---

## Context

Backlog item **170**, which cites `DESIGN.md` §4.1, §4.4, §4.6 and §6. Its
design is `docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md`.
That design's steps 1 and 2 are built. This spec is the first of four for its
step 3, the migration. It changes the facts the migration will write, so the
migration, `SA-0222` and `SA-0223`, writes them in their final shape. `SA-0221`
writes a task's declared tier only where the spec declared one.

Line numbers below were read at `d938eab5`.

**A gate result keeps new failures only.** The design's §3 decided it on
2026-10-04
(`docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md:218-239`). A `gate_result` fact holds the failures left after
baseline subtraction, plus `failures_at_head`, the count before it. A baseline
result keeps its full list, since it names a run and is no task fact.
The measurement behind it is 1,820,645 attempt failures at head and 668 new.

**Today every head failure is kept.** `record_gate_result`
(`saffron/ledger.py:1844-1895`) builds an attempt's fact from
`result.model_dump(mode="json")` at `:1890`, which carries every failure.
`_commit_and_append` (`:539-544`) applies that fact through `_apply`, whose
`gate_result` branch (`:718-742`) inserts one `failures` row per entry. So the
live write path and the fold write the same rows from the same payload.

**The tier the suite ran at reaches no record.** `GateSuite._run` computes it
from the run's own changed files (`saffron/gates/suite.py:142-145`) and returns
it as `SuiteRun.effective_risk` (`:207`). `_judge` (`saffron/cell/session.py:2528-2543`)
keeps that run as `latest` and records each result with
`attempt_id=attempt_id` alone. The attempt it records against closed before
the suite ran. Its close comes from the wrapper at `saffron/cell/session.py:254-263`, which
is why the operator put the tier on the gate-result fact, not the close fact.

**The baseline is stored first.** The cell runs `suite.baseline(tree)` at
`saffron/cell/session.py:2020`. It records each result with
`run_id=run_id` at `saffron/cell/session.py:2037-2038`, before any attempt's
results. `subtract_baseline` (`saffron/gates/baseline.py:44-66`)
is the one subtraction the repair loop already uses. It counts, ignores the
line, compares on the gate as part of the identity, and never cancels a
`survived-mutant` failure. `Ledger.task_run` (`saffron/ledger.py:1143`) and
`Ledger.baseline_results` (`:1899`) read a task's run and its stored baseline.

## Problem

1. **New failures.** In `record_gate_result`'s attempt branch, read the stored
   baseline of the attempt's task's run. Write the fact's `failures` as what
   `subtract_baseline` leaves, and add `failures_at_head`. The run branch is
   unchanged and writes no count.
2. **The two columns.** Add `failures_at_head INTEGER` to `gate_results` and
   `earned_risk TEXT` to `attempts`, both nullable, in `SCHEMA`. Add each
   with an `ALTER` on open for a ledger that lacks it (`saffron/ledger.py:398-411`).
   `_add_gate_result_reference` (`:458-501`) rebuilds a v0.5 `gate_results` from a
   column list written by hand (`:474-487`). It must carry the new column, or
   the column added before it is dropped.
3. **The tier.** `record_gate_result` gains `earned_risk`. The fact carries it
   under that key, and `_apply`'s `gate_result` branch sets the attempt's
   column when it is not null. `_judge` passes `latest.effective_risk`.
4. **The fold.** `_apply` writes `failures_at_head` from the fact with
   `.get`, so a fact written before this change folds to null.
5. **The tests this changes.** `tests/test_ledger.py:713-730` pins
   `gate_results`'s columns to §4.1's listing, so it gains the new one. The
   `cost_floor_usd_est` test at `:1312-1321` builds an old schema by replacing
   text that this change moves. The loop at
   `tests/test_ledger_fold_task.py:229-234` asserts every folded column is not
   null. So the two `record_gate_result` calls at
   `tests/test_ledger_fold_task.py:183` and `:210` pass a tier.

## Out of scope

- The view. `factory:failureCount` (`saffron/view/graph.py:291-294`) and the
  task page's failure list (`saffron/view/server.py:427-433`) now read new
  failures only. That is the operator's call, and `SA-0219` edits the view.
  `failures_at_head` is stored and not shown.
- `saffron/replay.py:84-90` records a baseline and then an attempt's results.
  It needs no edit. Its attempt now keeps new failures and passes no tier.
- The declared tier on `task_created`, which is `SA-0221`'s.
- The migration, `SA-0222` and `SA-0223`. No production caller constructs a
  `Ledger` with a record, and this spec adds none.
- `DESIGN.md` §4.1's schema listing gains both columns by hand in this spec's
  pull request, since `DESIGN.md` is protected.

## Notes for the agent

**This change is new code inside existing functions.** No text at base fixes
the spelling of what it adds. So each criterion declares a witness and no
mutant, and the `witness` gate reports `skip` for all five. The wrong versions
under each criterion are what its witness must kill. Do not run them yourself.

**Commit as each witness passes.** Five witnesses, five commits at least.

**Every witness must fail at base.** At base no fact carries either key and
neither column exists. Write each witness against the ledger's public methods
and its own `_db`. Import nothing at module scope that this change adds.

**Criterion 1.** Build it on `tests/test_ledger_appends.py`'s `ledger` and
`record` fixtures. Make a second run with a baseline failure of its own before
the task's run, so a lookup that reads the wrong run cancels it. Give the task's
run a `lint`, a `tests` and a `witness` baseline. Record `lint`, `witness` and
an empty `types` at head. Assert the fact's `failures`, `attempt_results` and
the column, gate by gate, and assert the baseline results keep their counts.

**Criterion 2.** Open three attempts before any result, so a write that
reaches the whole task shows on the other two.

**Criterion 3.** Write through a record-backed source ledger, then fold its
`MemoryRecord` into a fresh one. Make the stale fact with
`dataclasses.replace` on a real `gate_result` fact, with a payload holding no
`failures_at_head` and no `earned_risk`. Point it at the first attempt, so a
fold that clears the tier shows.

**Criterion 4.** Use `tests/test_session.py`'s `_stub_the_runtime` with
`suites=(base, head, head)`, `_drive`, and `gates=("lint",)` under
`lint: { blocking: false }`. The baseline holds one `lint` failure and the
head holds it and one more. Drive once with `elevate_on: [src/**]` in the
policy, since `_stub_the_runtime` reports `src/x.py` changed, and once without.
Give each drive its own directory. Read the one attempt holding gate results,
and assert every other attempt reads a null tier.

**Criterion 5.** Build each old ledger from `SCHEMA`. Drop the two columns
with `ALTER TABLE ... DROP COLUMN`, so the test does not depend on how the
schema text spells them. The v0.5 shape replaces the `attempt_id` reference
as `tests/test_ledger.py:611-620` does. SQLite 3.51.0 breaks a `DROP COLUMN`
on a table whose last column has a comment above it (`saffron/ledger.py:166-167`).
Put a new column's comment below it.

**Measured on a prototype at `d938eab5`.** A prototype passed all five
witnesses, and each failed with its source reverted. Its diff measured 1179
changed tokens. Each of the 26 wrong versions above was applied to it as an
edit, and each failed its own criterion's witness. The rest of the suite
passed on it.
