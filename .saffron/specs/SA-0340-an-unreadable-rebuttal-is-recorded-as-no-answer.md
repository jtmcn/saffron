---
id: SA-0340
title: "An unreadable rebuttal and an unanswered blocker are both recorded as no answer, and the queue counts neither"
type: feature
priority: 1
depends_on: [SA-0339]
estimated_lines: 502
estimate_measured: true
touches:
  - saffron/phases/rebut.py
  - saffron/cell/session.py
  - saffron/ledger.py
  - saffron/record/migrate.py
  - saffron/report/index.py
  - saffron/task.py
  - saffron/phases/package.py
  - tests/test_rebut.py
  - tests/test_session.py
  - tests/test_ledger.py
  - tests/test_ledger_fold_task.py
  - tests/test_record_migrate.py
  - tests/test_report.py
  - tests/test_package.py
  - tests/test_task.py
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
  - saffron/record/contract.py
  - saffron/record/fold.py
  - saffron/record/memory.py
  - saffron/record/refs.py
  - saffron/record/routed.py
  - saffron/cli.py
  - saffron/replay.py
  - saffron/scheduler.py
  - saffron/view/**
  - saffron/gates/**
  - saffron/report/pr_body.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 66
max_attempts: 3
max_turns: 270
risk: elevated
acceptance:
  - claim: >-
      After REBUT, each blocker's `rebuttal` fact records an `answer` and an
      `error`, and the ledger row its fold writes carries both. A blocker the
      readable turn answered reads `answered`. One it named no answer for reads
      `unanswered`. Both carry a null error. Every blocker of a turn whose
      `RebuttalTurn.error` is not `None` reads `unread`, and carries that error
      text, the empty string included. The witness drives two blockers through
      each of four turns. One readable turn answers the first blocker alone.
      Another readable turn answers none. One turn's extraction is not the
      schema, and one turn's session raises with an empty message.
    witness: tests/test_session.py::test_rebut_records_each_blockers_answer_and_an_unread_turns_error
    wrong_versions:
      - The answer is decided once per turn, so every blocker of a turn that answered one reads `answered`.
      - The write reads `unread` whenever the answer list is empty, so a readable turn that answered nothing reads `unread`.
      - The error is tested for truth, so an empty error reads as a readable turn and its blockers read `unanswered`.
      - The error is written on the first blocker of an unread turn and left null on the second.
      - The answer is looked up one position off, so the first blocker reads `unanswered` and the second `answered`.
      - A turn whose error is set records `unanswered` for each blocker, because its empty answer list is all the write consults.
      - The write passes no error, so an unread blocker's row carries a null error.
  - claim: >-
      The fold writes a `rebuttal` fact's `answer` and `error` into the
      finding's row as written, for each of `answered`, `unanswered` and
      `unread`. A fact that carries neither key, as every fact before this
      change does, folds to a null answer and a null error. It never folds to
      `unanswered`. The witness folds a fresh ledger from the record's facts
      alone.
    witness: tests/test_ledger_fold_task.py::test_a_rebuttal_fact_folds_its_answer_and_one_without_it_folds_to_unknown
    wrong_versions:
      - A missing answer folds to `unanswered`.
      - The fold writes the answer and drops the error.
      - "`record_rebuttal` sets both columns on its own row and leaves both keys out of the fact, so a fresh fold reads null."
      - The fold reads the answer with a strict key lookup, so a fact without it raises.
  - claim: >-
      A ledger whose `findings` table predates both columns gains them when it
      opens. Its existing rows keep a null answer and error, and the next
      rebuttal written to it records its own.
    witness: tests/test_ledger.py::test_a_ledger_built_before_the_answer_columns_gains_both_and_records_an_answer
    wrong_versions:
      - The columns are added to the schema text alone, so an existing ledger raises on the first rebuttal write.
      - The open adds the answer column and not the error column.
  - claim: >-
      `rebut.unread_blockers(rebut_result, blockers)` counts the blockers whose
      answer is `unread` and that no verdict withdrew.
      `rebut.unanswered_blockers(rebut_result, blockers)` counts the same for
      `unanswered`. `blockers` is how many blockers REBUT was handed. A blocker
      stands with a `confirmed` verdict, a `contradicted` one, or none. Both
      counts are 0 with no `RebutResult`. On the judged unread turn below,
      `sustained_blockers` and `unkept_fixes` stay 0. The witness drives an
      unread turn judged `confirmed`, `withdrawn` and `contradicted`, an unread
      turn with no verdict, and a turn whose error is the empty string. It
      drives a readable turn with no answer at all. It also drives a readable
      turn of four blockers. That turn answers the first twice and the third
      once, answers a blocker numbered 9, and its fourth blocker is withdrawn.
    witness: tests/test_rebut.py::test_the_unread_and_unanswered_counts_take_each_standing_blocker_by_its_answer
    wrong_versions:
      - A withdrawn blocker of an unread turn is counted.
      - Only a `confirmed` verdict stands, so a `contradicted` blocker is left out.
      - Only a judged blocker stands, so an unread turn with no verdict counts 0.
      - The unanswered count is the blocker count less the number of answers in the turn.
      - A turn whose answer list is empty reads as unread, whether or not its error is set.
      - The error is tested for truth, so a turn whose error is the empty string counts its blockers as unanswered.
      - The unanswered count is decided per turn, so a turn that answered any blocker counts 0.
      - "`sustained_blockers` counts an unread blocker that a verdict confirmed."
  - claim: >-
      `QueueLine` carries `unread` and `unanswered` counts, both 0 by default. A
      line in any state of `_RANKED_BY_RISK`, with either count above 0, ranks
      at level 3 beside a sustained blocker and above an elevated line. Its
      row renders `1 unread blocker` and `2 unread blockers`, and
      `1 unanswered blocker` and `2 unanswered blockers`, each in its own
      cell. A count of 0 renders nothing. The witness drives each state of
      `_RANKED_BY_RISK`.
    witness: tests/test_report.py::test_unread_and_unanswered_blockers_rank_with_sustained_and_render_apart
    wrong_versions:
      - Only `unread` lifts a line to level 3.
      - Only `unanswered` lifts a line to level 3.
      - The counts lift a `READY_FOR_REVIEW` line and no other state.
      - An unread blocker renders under the word "sustained".
      - The cell is always plural, so one renders as `1 unread blockers`.
      - A count of 0 renders as `0 unanswered blockers`.
      - The two words are swapped between the counts.
  - claim: >-
      `CellOutcome` carries `unread` and `unanswered`, both 0 by default. The
      cell sets them from REBUT's result before a pool cut sets
      `rebut_result` to `None`. So a REBUT its pool cut short still carries
      its counts. The witness drives a cut REBUT whose rebuttal turn raised,
      over two blockers, and an uncut readable turn over two that answers the
      first.
    witness: tests/test_session.py::test_a_rebut_carries_its_unread_and_unanswered_counts_past_a_pool_cut
    wrong_versions:
      - The counts are taken after the cut sets the result to `None`, so a cut REBUT carries 0.
      - The outcome never takes the counts, so both stay 0.
      - The two counts are swapped on the outcome.
  - claim: >-
      The queue line `package.package` writes carries `outcome.unread` and
      `outcome.unanswered`. The witness packages an outcome with no
      `rebut_result` and counts of 2 and 3.
    witness: tests/test_package.py::test_the_queue_line_carries_the_unread_and_unanswered_blocker_counts
    wrong_versions:
      - The packaged line passes `unread` and leaves `unanswered` at its default.
      - The packaged line recounts from `rebut_result`, so an outcome a pool cut left without one counts 0.
  - claim: >-
      Both queue lines `run_task` writes itself carry the outcome's two counts.
      One is the line for an `EXHAUSTED` task whose PACKAGE opened nothing, as
      a pool-cut REBUT leaves it. The other is the line for a task PACKAGE
      never ran. The witness drives each with counts that differ, and no
      `rebut_result`.
    witness: tests/test_task.py::test_both_run_task_rows_carry_the_outcomes_unread_and_unanswered_counts
    wrong_versions:
      - The exhausted line leaves both counts at their default.
      - The unpackaged line leaves both counts at their default.
      - The exhausted line recounts from `rebut_result`, so it counts 0.
  - claim: >-
      `ready_task` sets both counts on the outcome it rebuilds, from the
      rebuilt `rebut_result` over `anchored_blockers` of the rebuilt reviews.
      The witness rebuilds an unread turn and then a readable turn that answers
      the first blocker. Its reviews hold two anchored blockers, a host-filed
      survivor, a concern and an unanchored blocker.
    witness: tests/test_task.py::test_a_rebuilt_outcome_counts_the_unread_and_unanswered_blockers_its_record_holds
    wrong_versions:
      - The rebuilt outcome leaves both counts at their default.
      - The blocker count is every finding the reviews hold, the concern included.
      - The blocker count takes anchored blockers alone, so the host-filed survivor is left out.
      - The blocker count takes every blocker, so the unanchored one is counted.
      - The two counts are swapped on the rebuilt outcome.
  - claim: >-
      `saffron migrate`'s top-up sets aside a `rebuttal` fact's `answer` and
      `error` keys, as it sets aside a `gate_result`'s own keys. So a held
      `rebuttal` fact that carries them, an empty error included, agrees with
      the one `migrate` derives for the same row. The same keys on a `finding` fact still
      disagree, and so does a held `rebuttal` whose `verdict` differs. No value
      is backfilled.
    witness: tests/test_record_migrate.py::test_the_top_up_sets_aside_a_live_rebuttals_answer_and_error
    wrong_versions:
      - The top-up compares whole payloads, so a live-written `rebuttal` fact disagrees.
      - The top-up sets aside `answer` and compares `error`.
      - The two keys are set aside on every kind, so a `finding` carrying them agrees.
      - A `rebuttal` fact is set aside whole, so a differing verdict agrees.
---

## Context

Backlog item **42**, under `DESIGN.md` §5.6 and §6. The operator amended §5.6
by hand at `4d65206a`: "An unreadable rebuttal is recorded as unreadable, never
as no answer (item 42)". Under it, the ledger's rebuttal fact names one of
three answers per confirmed blocker. The implementer answered it, left it
unanswered, or answered in a turn nobody could read. §6 is amended at
`e6880cb0`: "An unread or unanswered blocker ranks with a sustained one too,
and keeps its own count". It adds that a REBUT its pool cut short still counts
its unread blockers on its line. `CONTEXT.md`'s **Rebuttal** entry names the
three answers, amended by hand at `ae9c9dc3`. Item 42's visible half landed as
`SA-0071`, in the pull request body. This spec is its recording half.
`SA-0341` re-prompts the extraction once, and depends on this spec. Every line
below was read at `05d4875a`.

**What REBUT writes.** `saffron/cell/session.py:3730-3734` builds `argued` from
`rebut.first_answers(result.rebuttal)`. `saffron/cell/session.py:3738-3743`
then calls `ledger.record_rebuttal` once per blocker, with
`rebuttal=argued.get(n)`. `saffron/ledger.py:2146-2162` writes a `rebuttal`
fact whose payload is `position`, `verdict` and `rebuttal`. The fold at
`saffron/ledger.py:1101-1111` sets `findings.verdict` and `findings.rebuttal`.
The table at `saffron/ledger.py:228-240` has no other column for an answer.

**Why two shapes read as one.** A turn whose error is set carries no answers.
`saffron/phases/rebut.py:253`, `:270` and `:279-281` return a `RebuttalTurn`
with `error` set and an empty `rebuttals` list. `:253` and `:270` set it to
`str(failed)`, which is empty for an exception with no message.
`saffron/report/pr_body.py:250-252` tests it with `is not None` for that
reason, and `tests/test_report.py:471` pins it. A readable turn that skipped a
blocker carries no entry for it either. So both write `rebuttal=NULL` at
`saffron/cell/session.py:3742`, and the ledger cannot tell them apart.
`rebuttal.json` can, since `saffron/cell/session.py:3717-3719` writes the
turn's error there.

**Why the queue reads neither.** `sustained_blockers` returns 0 when the
turn's error is set (`saffron/phases/rebut.py:641-642`), and so does
`unkept_fixes` (`saffron/phases/rebut.py:663-664`). A blocker with no answer
never enters `_confirmed_with`'s answered set
(`saffron/phases/rebut.py:614-618`). Both counts reach `QueueLine` at three
sites: `saffron/task.py:1009-1010`, `saffron/task.py:1052-1053` and
`saffron/phases/package.py:1070-1071`. `sort_key` lifts a line to level 3 on
those two alone (`saffron/report/index.py:140-141`). `tests/test_rebut.py:858`
and `:956` pin the zero for a turn whose error is set.

**Why a pool cut counts nothing.** `saffron/cell/session.py:3697` marks a cut,
and `saffron/cell/session.py:3759-3761` then sets `rebut_result` to `None`,
after the ledger write. The outcome at `saffron/cell/session.py:3779-3796`
carries that `None`. Such a task reaches `run_task`'s exhausted PACKAGE, which
needs `outcome.rebut_result is None` (`saffron/task.py:931-934`). So the line at
`saffron/task.py:995-1011`, and PACKAGE's own, count from no result.

**The record.** The fact kind `rebuttal` exists at
`saffron/record/contract.py:31` and `ontology/factory.ttl:208`.
`saffron/record/migrate.py:534-545` writes one only when a row's verdict or
rebuttal is set, with the same three keys. Its top-up compares a held fact's
whole payload with the one it derives (`saffron/record/migrate.py:96-105`).
`saffron/record/migrate.py:84` and `:87-93` set aside three `gate_result` keys
alone.

## Problem

Seven edits. The answer is computed once, in `rebut.py`, and every reader takes
it from there.

1. **The answer.** In `saffron/phases/rebut.py`, add a `Literal` alias for the
   three values `answered`, `unanswered` and `unread`. Add a function that maps
   a `RebuttalTurn` and a blocker count to each blocker's answer, numbered
   from 1. A turn's error is set when `error is not None`, the empty string
   included, here and in every new test of it. Such a turn makes every
   blocker `unread`. Otherwise a blocker is `answered` when `first_answers`
   holds its number, and `unanswered` when it does not. Add
   `unread_blockers(rebut_result, blockers)` and
   `unanswered_blockers(rebut_result, blockers)`, counting the blockers no
   verdict withdrew.
2. **The write.** At `saffron/cell/session.py:3738-3743`, pass each blocker's
   answer and the turn's `error` to `record_rebuttal`, under the keyword names
   `answer` and `error`.
3. **The ledger.** `record_rebuttal` takes both as keywords, each defaulting to
   `None`, and the fact's payload carries both keys. Add `answer` and
   `rebuttal_error` columns to `findings` in `SCHEMA`, and add them on open to
   a ledger that lacks them. `saffron/ledger.py:486-494` adds `attempts`
   columns that way. The fold reads both keys with `payload.get`, so an old
   fact folds to null.
4. **The outcome.** `CellOutcome` gains `unread` and `unanswered`, each an
   `int` defaulting to 0, after `revert_exempt`
   (`saffron/cell/session.py:467`). The cell sets both from REBUT's result,
   over `len(blockers)`, before `saffron/cell/session.py:3759-3761`. Bind both
   to 0 beside `rebut_result` (`saffron/cell/session.py:3418`), so a task with
   no REBUT carries 0. `ready_task` sets both on the outcome it rebuilds
   (`saffron/task.py:1373-1387`), over
   `len(anchored_blockers(reviews))`. `saffron/phases/review.py:891` holds that
   rule, and REBUT's blockers come from it (`saffron/cell/session.py:3431`).
5. **The queue.** `QueueLine` gains `unread` and `unanswered`, each an `int`
   defaulting to 0, after `unkept`. `sort_key` lifts a risk-ranked line to
   `_SUSTAINED` when any of the four counts is above 0. Tiebreak the two new
   counts after `unkept`, `unread` first. `_row` renders each in its own cell,
   empty at 0, as `sustained` and `unkept` do.
6. **The callers.** All three `QueueLine` sites pass `outcome.unread` and
   `outcome.unanswered`. None recounts from `rebut_result`, since a pool cut
   leaves none.
7. **The top-up.** In `saffron/record/migrate.py`, `_normalized` drops
   `answer` and `error` from a `rebuttal` fact's payload, beside the
   `gate_result` set-aside. It writes no value.

**What each count now means.** `sustained` still counts a blocker argued and
then confirmed or contradicted. `unkept` still counts a blocker claimed
fixed, then confirmed or contradicted, with HEAD unmoved. Neither counts an
unread blocker, as today. `unread` now counts those, and `unanswered` counts a
standing blocker that a readable turn skipped. A blocker a verdict withdrew
counts in none of the four.

## Out of scope

- The re-prompt on a schema error. That is `SA-0341`.
- A backfill. `saffron/record/migrate.py:534-545` still derives a three-key
  `rebuttal` fact, so a migrated fact folds to an unknown answer, by the
  operator's decision.
- A held `rebuttal` fact whose verdict and rebuttal are both null. The cell
  writes one per blocker (`saffron/cell/session.py:3738-3743`), and
  `saffron/record/migrate.py:534` derives none for such a row. The top-up then
  holds more `rebuttal` facts than it derives and refuses the ref. That holds
  at `e6880cb0` already, and this spec leaves it.
- The pull request body. `saffron/report/pr_body.py:311-329` already renders a
  turn with an error apart (`SA-0071`).
- `CONTEXT.md` and the ontology. The answer values stay a `Literal` in code.

## Notes for the agent

**No criterion carries a mutant.** Every criterion's behaviour is new code: a
new function, a new keyword, two new columns, four new fields and a new
set-aside. So each declares a witness alone, and `witness` reports `skip` for
each.

**Keep each witness able to fail with the source reverted.** Reach every new
name through its module, as `rebut.unread_blockers` and the like.
`tests/test_rebut.py:12` and `tests/test_package.py:24` import `rebut` as a
module. Import no new name at module scope.

**Comments that turn false.** Rewrite the `_SUSTAINED` comment
(`saffron/report/index.py:84-86`), `sort_key`'s docstring and its return
annotation (`:120-148`), and `_normalized`'s docstring
(`saffron/record/migrate.py:88-89`).

**Fixtures.** In `tests/test_session.py`, `_stub_the_runtime`, `_rebuttable`
(`:5052`) and `_drive` build a REBUT, and `_BLOCKER` (`:5028`) is a one-blocker
lens reply. Copy `_through_rebut` (`:5070`) with one lens filing two blockers
on `src/x.py` line 1, which `_ANCHORING_DIFF` anchors. In criterion 6's fixture
one lens also files a concern, so a count over every finding reads 3 where the
blockers read 2. A readable turn that
answers needs `rebut_commits=1` and one verdict turn. An extraction reply that
is not the schema, or `{"rebuttals": []}`, with `rebut_commits=0`, ends at the
early exit with no verdict. So does a rebuttal turn scripted as
`implement.AgentFailed("", _cut_off_turn(cost=0.4))`, which leaves an empty
error. Read the expected error from the run's `rebuttal.json`.
`_rebut_capped` (`tests/test_session.py:5115`) drives a pool cut. Script its
rebuttal turn as `implement.AgentFailed` costing $10.25, and follow it with
three costs. That cuts a REBUT over two lenses' blockers. Case `"a"` at
`tests/test_session.py:5360` cuts one over a single blocker. Both pass
`rebut_commits=0`, since a moved HEAD opens the verdict pool and clears the cut. In
`tests/test_ledger_fold_task.py`, `_minimal`, `_find`, `_key` and
`record._facts` build and edit a task's facts. `dataclasses.replace` rebuilds
a `Fact` with its payload's two keys removed. `tests/test_ledger.py:1773` drops
a column from an opened ledger with `ALTER TABLE ... DROP COLUMN`. In
`tests/test_package.py`, `packageable` (`:1010`) builds a packaged outcome. In
`tests/test_task.py`, `_drive` (`:44`) passes extra outcome fields through.
Replace `package_phase.package` with one that returns an `EXHAUSTED`
`PackageResult` and no `pr_url`, and the exhausted line is reached.
`_rt_ledger`, `_rt_task`, `_rt_write_patch`, `_rt_seed_records` and
`_rt_set_mtime` (`:2665-2768`) build a ready task, and one fixture serves both
members if `rebuttal.json` is rewritten between calls. A host-filed survivor
is an unanchored blocker whose claim opens with `review.HOST_FILED`
(`saffron/phases/review.py:56`), and `anchored_blockers` keeps it. Import
`review` inside the test. `tests/test_report.py:22` imports `_RANKED_BY_RISK`.
In `tests/test_record_migrate.py`, `_rich_task` (`:2002`) records two
rebuttals, and `_assert_agrees_and_gains_nothing` and `_assert_disagrees`
(`:2203-2232`) judge a held list.

**Two hand-built outcomes.** `tests/test_package.py:876-895` and
`tests/test_session.py:13869-13890` build a `SimpleNamespace` in place of a
`CellOutcome`. Each needs `unread=0` and `unanswered=0`, or every test that
packages one raises `AttributeError`. On the prototype that was 43 tests.

**What criterion 1 leaves undriven.** A turn's error is set three ways: its
session raises (`saffron/phases/rebut.py:253`), its extraction session raises
(`:270`), or its reply is not the schema (`:279-281`). The witness drives the
first and the last. The second sets the same `error` field the answer reads.

**A docstring at its limit.** `sustained_blockers`'s docstring runs ten lines
(`saffron/phases/rebut.py:631-640`), the `prose` gate's limit. A line naming
the new counts there replaces one.

**An existing test that changes.**
`tests/test_ledger_fold_task.py::test_every_task_fact_kind_folds_back_to_the_rows_its_write_made`
asserts every `findings` column but `adjudication` is non-null
(`tests/test_ledger_fold_task.py:233-236`). Its two `record_rebuttal` calls at
`:193` and `:195` must pass an answer and an error, or it fails on the new
columns.

**Stack order.** `depends_on: [SA-0339]` orders the stack, and this spec uses no
code `SA-0339` adds. `SA-0338` also edits `saffron/ledger.py`, its fold and
`saffron/task.py`. Keep this spec's ledger edits to `findings` and the
`rebuttal` fact.

**Measured.** Every wrong version above ran on a prototype of this spec, and
each failed its witness. Do not run them yourself. `size_gate` priced that
prototype's whole diff at 2005 changed tokens, tests counted, and 479 with
the declared test paths set aside. The first figure over four is
`estimated_lines`.
