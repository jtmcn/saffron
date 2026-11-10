---
id: SA-0364
title: "`migrate` derives no `rebuttal` fact for a finding REBUT left with no verdict and no rebuttal, so it refuses the ref a live cell wrote"
type: bug
priority: 2
estimated_lines: 43
estimate_measured: true
touches:
  - saffron/record/migrate.py
  - tests/test_record_migrate.py
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
  - saffron/record/__init__.py
  - saffron/record/contract.py
  - saffron/record/fold.py
  - saffron/record/memory.py
  - saffron/record/refs.py
  - saffron/record/routed.py
  - saffron/ledger.py
  - saffron/cli.py
  - saffron/task.py
  - saffron/view/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/phases/**
  - tests/test_fold.py
  - tests/test_cli.py
  - tests/test_ledger.py
budget_usd: 30
max_attempts: 3
max_turns: 150
risk: standard
acceptance:
  - claim: >-
      `migrate` derives a `rebuttal` fact for every finding whose row's
      `answer` is set, a null `verdict` and a null `rebuttal` included. The
      fact carries the row's `answer`, and its `rebuttal_error` as `error`.
      `migrate` derives a task's `rebuttal` facts in REBUT's own order: every
      blocker's in position order, then every other one in position order.
      The witness's source is written by a `Ledger` holding a live record.
      Two tasks each hold a blocker, a note and a concern. REBUT recorded the
      blocker and the concern with no verdict and no rebuttal. On one task
      both read `unread` with an error. On the other both read `unanswered`
      with none. A third task holds, in position order,
      lens A's concern, lens A's blocker, lens B's concern and lens B's
      blocker. REBUT recorded both blockers first, then both concerns, all
      `unread`. A fourth task holds a concern at position 1 and, at position
      2, an unanchored blocker whose claim starts with `review.HOST_FILED`.
      REBUT recorded that blocker first, both `unread`. The blocker group is
      chosen by the row's `severity` alone. `migrate` against that live
      record counts all four tasks as migrated,
      refuses none, and appends nothing. Into an empty record it derives, per
      task, the two `rebuttal` payloads the live `Ledger` wrote, in its order.
      A fold of that record gives back each finding's `verdict`, `rebuttal`,
      `answer` and `rebuttal_error` as the source holds them.
    witness: tests/test_record_migrate.py::test_a_live_ref_whose_rebut_reached_no_verdict_and_no_rebuttal_tops_up
    wrong_versions:
      - The fact is derived where `answer` is set, but its payload leaves out `answer` and `error`.
      - A fact is derived only where `answer` reads `unread`, so an `unanswered` finding gets none.
      - A fact is derived only where the row's `rebuttal_error` is set.
      - A null verdict and a null rebuttal derive a fact for a blocker only, so the concern gets none.
      - The fact's `error` is read from the row's `rebuttal` column.
      - The fact's `answer` and `error` are swapped.
      - A `rebuttal` fact's `position` counts only the findings REBUT asked about, so the concern reads 2.
      - The `rebuttal` facts are derived in position order, so a concern recorded before a blocker comes first.
      - The blockers' facts are derived in reverse position order, or lens by lens in reverse.
      - The blocker group holds only anchored blockers, so an unanchored host-filed blocker falls among the rest.
  - claim: >-
      `migrate` derives no `rebuttal` fact for a finding whose row holds no
      `verdict`, no `rebuttal` and no `answer`. The witness drives three
      tasks holding only such rows. One holds a concern and a note and no
      blocker. One holds a blocker and ended before REBUT. One holds a
      blocker, opened a `REBUTTING` attempt, and ended `ORPHANED` before
      recording any rebuttal. Each derives none. A fourth task holds a blocker, a
      note and a concern, in that position order, and its REBUT recorded the
      blocker and the concern `unread`.
      It derives two, at positions 1 and 3, through the same count. Against
      the live record its `Ledger` wrote, all four tasks are migrated, none is
      refused, and no ref gains a fact.
    witness: tests/test_record_migrate.py::test_migrate_derives_no_rebuttal_fact_where_no_rebut_recorded_one
    wrong_versions:
      - A fact is derived for every blocker and every concern.
      - A fact is derived for every blocker.
      - A fact is derived for every blocker and concern of a task holding a `REBUTTING` attempt.
      - A fact is derived only where `verdict` or `rebuttal` is set, as at base.
  - claim: >-
      The top-up compares a `rebuttal` fact's `answer` and `error` instead of
      setting them aside. A key a held fact lacks reads as null, as the fold
      reads it. Against a row REBUT recorded `unread` with an error, four held
      facts are refused: one whose `answer` differs, one whose `error`
      differs, one whose `error` is null, and one lacking both keys. The fact
      the live `Ledger` wrote agrees and gains nothing. Against a row recorded
      with a verdict and a rebuttal and no answer, a held fact lacking both
      keys agrees and gains nothing. One whose `answer` is set is refused, and
      so is one whose `error` is set.
    witness: tests/test_record_migrate.py::test_the_top_up_compares_a_rebuttals_answer_and_error
    wrong_versions:
      - "`answer` and `error` stay set aside on a `rebuttal` fact."
      - "`answer` is compared and `error` stays set aside."
      - A held fact is compared as stored, so one lacking both keys disagrees with a derived fact whose two keys are null.
  - claim: >-
      A source whose `findings` table predates both the `answer` and the
      `rebuttal_error` column still migrates. Its row with a verdict and a
      rebuttal derives one `rebuttal` fact, whose `answer` and `error` are
      null, and its other rows derive none.
    witness: tests/test_record_migrate.py::test_a_ledger_that_predates_the_rebuttal_answer_migrates_its_rebuttals
    wrong_versions:
      - Both columns are read from every row whatever the source holds, so an older source raises.
      - An older source's fact leaves out `answer` and `error` rather than carrying them null.
---

## Context

Backlog item b-3cf039, filed 2026-11-07 from `SA-0340`'s second spec review.
`SA-0360` has since given each concern REBUT asks about a fact of its own.

**A live cell writes a `rebuttal` fact for every finding REBUT asked
about.** After REBUT returns, `saffron/cell/session.py:3762` builds
`answers = rebut.blocker_answers(result.rebuttal, total)`. The loop at
`:3763-3770` calls `ledger.record_rebuttal` for each blocker. The loop at
`:3773-3780` calls it for each concern, with `verdict=None`. Each call
passes `answer=answers.get(n)` and `error=result.rebuttal.error`.
`blocker_answers` (`saffron/phases/rebut.py:692-705`) maps every number from
1 to the count it is given. Each reads `unread` when the turn's `error` is
set (`:700-701`), and `answered` or `unanswered` otherwise. So since
`SA-0340`, every `rebuttal` fact a live cell writes carries a non-null
`answer`.

**The ledger keeps that answer on the row.** `record_rebuttal`
(`saffron/ledger.py:2181-2214`) builds a fact whose payload holds `position`,
`verdict`, `rebuttal`, `answer` and `error`. It goes through
`_commit_and_append` (`:700-705`), which applies it before appending it.
`_apply`'s `rebuttal` branch (`:1116-1137`) writes `verdict`, `rebuttal`,
`answer` and `rebuttal_error` onto the finding's row, reading the last two
with `payload.get`. The `findings` table declares `answer` and
`rebuttal_error` (`:241-242`). A ledger built before them gains both on open
(`:506`, `:508`).

**`migrate` reads neither.** `_finding_facts`
(`saffron/record/migrate.py:519-556`) derives a `rebuttal` fact only when
the row's `verdict` or `rebuttal` is set (`:544`). Its payload holds
`position`, `verdict` and `rebuttal` alone. It follows each finding's own
fact, so the `rebuttal` facts come in position order.
`_top_up` (`:137-167`) compares each kind by count, then fact by fact in
order (`:150-152`). It refuses a ref holding more facts of one kind than
`migrate` derives (`len(held_k) > len(truth_k)`,
`saffron/record/migrate.py:148`). It sets
aside `answer` and `error` on a `rebuttal` fact through
`_REBUTTAL_SET_ASIDE` (`:89-91`), applied in `_normalized` (`:101-102`).

**REBUT records in its own order.** REVIEW records the findings lens by
lens (`saffron/cell/session.py:3415-3419`). So a concern can precede a
blocker. REBUT then records every
blocker's rebuttal before any concern's (`:3763`, `:3773`).

**REBUT can record a finding with no verdict and no rebuttal.**
A failed fix or extraction turn returns with only its `error` set
(`saffron/phases/rebut.py:286`, `:304`). Every finding then reads `unread`.
A readable turn that answers nothing leaves each finding `unanswered`, with
no `rebuttal`. A turn that moved nothing and argued nothing returns before
any verdict runs (`:912`). A concern never gets a verdict. Since `SA-0360`,
each concern the implementer leaves unanswered is recorded this way.

## Problem

- **A live ref holding such a fact is refused whole.** `migrate` derives
  fewer `rebuttal` facts than the ref holds, so `_top_up` returns `None`.
  The task reads "the record holds N fact(s) that disagree". None of that
  task's later facts reaches its ref.
- **A concern recorded before a blocker is refused too.** Its ref holds
  the blocker's `rebuttal` fact first. `migrate` derives the concern's
  first, so the first pair compared disagrees.
- **The set-aside hides a real disagreement.** A held `answer` of
  `answered` agrees with a row that says `unread`, because neither side's
  `answer` is compared.

The ledger already tells the two cases apart. Only `record_rebuttal` writes
`answer`, and it writes a non-null one on every call since `SA-0340`. A row
whose `answer` is set had a fact written for it. A row with all three null
had none written since `SA-0340`, whether REBUT never started or ended
before recording. `SA-0362`'s own ref went from `REBUTTING` to `ORPHANED` and
holds no `rebuttal` fact.

Measured 2026-11-10 against a copy of the home ledger and the 405 task refs
on `~/.saffron/mirrors/saffron-f6b7e296a444.git`, read into a
`MemoryRecord`. `migrate` refused 3 at base and the same 3 with the
prototype. All three disagree on `task_package`'s `state`, not on
`rebuttal` (Out of scope). No cell has yet run on `SA-0360`'s code, so no
ref holds a concern's fact.

## Out of scope

**A fact written before `SA-0340` with no verdict and no rebuttal.** Its row
holds all three null. A REBUT whose cell died before recording leaves the
same row. `SA-0057` and `SA-0087` are `ORPHANED`, with a `REBUTTING`
attempt and null rows. `SA-0362` is the same shape after `SA-0340`, and its
ref holds no `rebuttal` fact. A `REBUTTING` attempt therefore cannot mark
the fact. The measurement above found no ref refused for want of one.

**A ref holding an answer-less fact base `migrate` added.** Comparing
`answer` refuses it where the row's `answer` is set. On 2026-11-10 none
of the 325 `rebuttal` facts on the 405 refs lacked `answer` on a row that
holds one.

**The `answered` shape with a null rebuttal.** Criterion 1 drives `unread`
and `unanswered` only. `answered` means `first_answers` holds the number
(`saffron/phases/rebut.py:702-705`). The cell writes `rebuttal` from that
same map (`saffron/cell/session.py:3752-3756`). So such a row always holds
a `rebuttal`.

**The three refs refused on `task_package`.** `SA-0338`, `SA-0353` and
`SA-0360` are `MERGED`. Each ref's package fact says `EXHAUSTED` where
`_outcome_facts` derives `READY_FOR_REVIEW`. That is a separate defect.

**The live cell, the ledger and the fold.** `saffron/cell/**`,
`saffron/ledger.py` and `saffron/record/fold.py` are forbidden. The fold
already places both keys.

## Notes for the agent

**No criterion carries a mutant yet.** The ref does not exist at origin.
Creating it is the operator's call, though mutants for criteria 2 and 3 are
written. So keep the derivation's check on the row's
`rebuttal`, and the `rebuttal` branch in `_normalized`, where they are, as
edits of those lines. A later mutant can then pin them. Expect `witness` to
report `skip` on every criterion.

**Read each column only where the source has it.** `migrate` already reads
optional columns that way (`saffron/record/migrate.py:205-206`, through
`_columns` at `:188`). A missing one reads as null. Always write both keys
on a derived fact, null included, so every derived `rebuttal` fact has one
shape.

**Replace the set-aside with a null default.** In `_normalized`, a
`rebuttal` fact lacking `answer` or `error` reads that key as null. Then
compare the payloads as stored. Remove `_REBUTTAL_SET_ASIDE` and the comment
above it, which says `_finding_facts` derives neither key. `_normalized`'s
docstring must keep the phrase "the four `gate_result` keys":
`test_the_normalized_docstring_counts_every_set_aside_gate_result_key` reads
it.

**One existing test asserts the old rule.** It is
`test_the_top_up_sets_aside_a_live_rebuttals_answer_and_error`
(`tests/test_record_migrate.py:2700`). It asserts that a derived fact
carries neither key (`tests/test_record_migrate.py:2727-2728`). It also
asserts that a held `answer` of `answered` or `unread` agrees with a row
holding none (`tests/test_record_migrate.py:2737-2746`). Keep its name,
because `census` refuses a test that disappears. Rewrite its docstring
and its body to what still holds. A held `rebuttal` fact lacking both keys agrees with a row whose two
columns are null. The same keys on a `finding` fact disagree. A differing
`verdict` disagrees.

**Build each witness's source with a live record.** `Ledger(path,
record=live)` with `live = MemoryRecord()` writes the facts a cell would.
`_task`, `_key` and `_migrated` already exist in the test file.
`_assert_agrees_and_gains_nothing` asserts `migrated == [key]`, and
`_assert_disagrees` asserts the refused keys are `[key]`
(`tests/test_record_migrate.py:2224-2225`). So give each source they read
one task. Write the fourth criterion's older source as
`test_a_ledger_that_predates_the_head_count_migrates_and_is_left_unwritten`
does, by dropping the two columns with `ALTER TABLE findings DROP COLUMN`.
Prefix every new helper with `_`.
