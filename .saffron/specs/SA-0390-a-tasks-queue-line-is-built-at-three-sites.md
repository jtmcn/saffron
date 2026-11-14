---
id: SA-0390
title: "A task's queue line is built at three sites, so a new `QueueLine` field must be added three times"
type: refactor
priority: 3
estimated_lines: 211
estimate_measured: true
touches:
  - saffron/task.py
  - saffron/phases/package.py
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
  - harness/**
  - images/**
  - records/**
  - hooks/**
  - saffron/agents/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/record/**
  - saffron/report/**
  - saffron/view/**
  - saffron/phases/review.py
  - saffron/phases/rebut.py
  - saffron/replay.py
  - saffron/cli.py
  - saffron/batch.py
  - tests/fixtures/**
  - tests/test_package.py
  - tests/test_report.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 36
max_attempts: 3
max_turns: 180
acceptance:
  - claim: >-
      `saffron/phases/package.py` gains `queue_line`, which takes a cell's
      outcome first, then keyword-only `repo_name`, `spec_id` and `state`, and
      `note`, `added`, `removed` and `link` defaulting to `""`, `0`, `0` and
      `""`. It returns a `QueueLine`. It derives eight fields from the
      outcome: `attempts`, `cost_usd_est` from `spent_usd`, `risk` from
      `effective_risk`, `unread`, `unanswered`, `concerns` as
      `anchored_concerns` over `reviews`, and `sustained` and `unkept` as
      `sustained_blockers` and `unkept_fixes` over `rebut_result`. Every other
      field is its caller's. The witness builds one outcome whose counts all
      differ: 13 attempts, $17.50, `elevated`, 7 unread and 11 unanswered. Its
      review holds two anchored concerns, an unanchored concern, an anchored
      note and an anchored blocker. Its rebuttal leaves 3 blockers sustained
      and 5 unkept. The witness compares the whole row as a dict for a call
      that names every caller field, for one that names none of the four
      defaulted ones, and for the same outcome with no `rebut_result`.
    witness: tests/test_task.py::test_queue_line_builds_a_tasks_row_from_its_outcome
    wrong_versions:
      - "`concerns` counts every concern, anchored or not, so it reads 3."
      - "`concerns` counts every anchored finding, so it reads 4."
      - "`sustained` and `unkept` are swapped."
      - "`sustained` is left out, so it reads 0."
      - "`unkept` is left out, so it reads 0."
      - "`unread` and `unanswered` are swapped."
      - "`unread` is left out, so it reads 0."
      - "`unanswered` is left out, so it reads 0."
      - "`risk` is left out, so it reads `standard`."
      - "`attempts` and `cost_usd_est` are swapped."
      - "`cost_usd_est` is `None`."
      - "`added` and `removed` are swapped."
      - "`link` is always empty."
      - "`note` is never passed on."
      - "`repo` and `spec_id` are swapped."
      - "`note` defaults to `-`."
      - "`added` defaults to `None`."
  - claim: >-
      The three sites that write a task's queue line after its cell returns
      each build it with `queue_line` and write the row it returns. They are
      `run_task`'s unpackaged row and its `EXHAUSTED` row, and `_finish`'s row
      in PACKAGE. Each site's row equals base's on every field. The witness
      wraps the real `queue_line` in a spy. It sets the spy on
      `saffron.phases.package`, and on `saffron.task` where that name exists,
      so either spelling of the call reaches it. Every outcome it drives
      carries criterion 1's values: 13 attempts, $17.50, `elevated` against a
      spec declaring `standard`, 7 unread, 11 unanswered and the five-finding
      review. A rebutted outcome also carries criterion 1's rebuttal, with 3
      sustained and 5 unkept. It drives `run_task` to the unpackaged row for
      a `NOT_IMPLEMENTED` cell with and without that rebuttal, and to the
      `EXHAUSTED` row for a refused PACKAGE with none. It drives `_finish`
      over a rebutted outcome twice. One result is `READY_FOR_REVIEW` with the
      note `opened`, a link, 19 added and 23 removed. The other is
      `MERGE_FAILED` with the note `gone`, no link and no diff stat. It
      compares each landed row in full with the row base writes. It also
      asserts that the spy returned those five rows in that order, each with
      its state. Last, it compares the rows on the ten fields the sites
      share, each field but `state`, `note`, `added`, `removed` and `link`,
      in two groups. The rebutted unpackaged row and both `_finish` rows
      agree on all ten. The `EXHAUSTED` row and the unpackaged row with no
      rebuttal agree on all ten, with `sustained` and `unkept` at 0.
    witness: tests/test_task.py::test_every_row_a_tasks_end_writes_comes_from_queue_line
    wrong_versions:
      - "The unpackaged site keeps its own `QueueLine` construction."
      - "The `EXHAUSTED` site keeps its own `QueueLine` construction."
      - "`_finish` keeps its own `QueueLine` construction."
      - "The `EXHAUSTED` site's note drops the pushed branch's note."
      - "The `EXHAUSTED` site's note is the pushed branch's note alone."
      - "The unpackaged site's note is empty."
      - "The unpackaged site always passes the state `EXHAUSTED`."
      - "`_finish` passes `result.added` and `result.removed` unchanged, so a `MERGE_FAILED` row reads `None`."
      - "`_finish` swaps `added` and `removed`."
      - "`_finish` passes no link."
      - "`_finish` passes no note."
      - "`_finish` always passes the state `READY_FOR_REVIEW`."
      - "The unpackaged site replaces the row's `risk` with the spec's declared one."
      - "The `EXHAUSTED` site replaces the row's `concerns` with 0."
      - "`_finish` replaces the row's `unread` with 0."
      - "`queue_line` swaps `sustained` and `unkept`."
      - "`queue_line` counts every concern, anchored or not."
  - claim: >-
      In `saffron/task.py` and `saffron/phases/package.py`, a `QueueLine` is
      constructed in exactly two functions, once each: `queue_line` and
      `run_task`'s `_live_row`. The witness parses both files. It lists every
      call to `QueueLine`, spelled as an attribute or as a bare name, beside
      the innermost function that holds it, and compares that list exactly.
    witness: tests/test_task.py::test_only_queue_line_and_the_live_row_construct_a_queue_line
    wrong_versions:
      - "The unpackaged site keeps its own `QueueLine` construction."
      - "The `EXHAUSTED` site keeps its own `QueueLine` construction."
      - "`_finish` keeps its own `QueueLine` construction."
      - "The unpackaged site calls `queue_line`, discards its row and writes its own `QueueLine`."
  - claim: >-
      `run_task`'s unpackaged row still counts anchored concerns, sustained
      blockers and unkept fixes, each as its own number.
    witness: tests/test_task.py::test_an_unpackaged_row_counts_its_review_and_rebuttal
    preserves: true
    wrong_versions:
      - "`sustained` and `unkept` are swapped."
      - "`concerns` reads 0."
  - claim: >-
      Both rows `run_task` writes itself still carry the outcome's `unread`
      and `unanswered` counts.
    witness: tests/test_task.py::test_both_run_task_rows_carry_the_outcomes_unread_and_unanswered_counts
    preserves: true
    wrong_versions:
      - "`unread` and `unanswered` are swapped."
      - "The `EXHAUSTED` site replaces the row's `unread` with 0."
  - claim: >-
      An `EXHAUSTED` task whose PACKAGE opened nothing still lands a row in
      `EXHAUSTED` with no link, whose note holds PACKAGE's note and the
      pushed branch's note.
    witness: tests/test_task.py::test_an_exhausted_package_that_opened_nothing_still_pushes_its_work
    preserves: true
    wrong_versions:
      - "The `EXHAUSTED` site's note drops the pushed branch's note."
      - "The `EXHAUSTED` site's note is the pushed branch's note alone."
  - claim: >-
      A packaged row still counts its sustained blockers and unkept fixes.
    witness: tests/test_package.py::test_the_queue_line_carries_the_unkept_fix_count
    preserves: true
    wrong_versions:
      - "`unkept` reads 0."
      - "`sustained` reads 0."
  - claim: >-
      A packaged row still carries the tier re-verification computed, never
      the spec's declared one.
    witness: tests/test_package.py::test_the_queue_line_carries_the_effective_tier_not_the_specs_declared_one
    preserves: true
    wrong_versions:
      - "`risk` is left out, so it reads `standard`."
  - claim: >-
      `run_task`'s unpackaged row and `_finish`'s row each still pass the
      trailing accept rate in the page header.
    witness: tests/test_task.py::test_both_queue_writers_put_the_trailing_accept_rate_in_the_header
    preserves: true
    wrong_versions:
      - "The unpackaged site writes its row with no `header`."
      - "`_finish` writes its row with no `header`."
---

## Context

Backlog item **b-990bd9**, filed 2026-09-18 from the spec loop's review of
`SA-0100` (#339). It cites `DESIGN.md` §6, whose queue lines this change
builds. b-edcab7 records the third site `SA-0204` (#678) added. Every line
number below was read at `3495ef85`.

**The three sites.** Each passes the same fifteen `QueueLine` fields and
repeats the same three derivations.

- `run_task`'s `EXHAUSTED` row, for a cell whose exhausted PACKAGE opened no
  pull request (`saffron/task.py:1077-1097`). Its state is the literal
  `EXHAUSTED`, and its note joins PACKAGE's note and the pushed branch's note
  (`saffron/task.py:1074`).
- `run_task`'s unpackaged row, for a cell PACKAGE never ran
  (`saffron/task.py:1118-1138`). Its state is `outcome.state`, and its note
  is the pushed branch's note.
- `_finish`'s row in PACKAGE (`saffron/phases/package.py:1061-1081`). Its
  state, note and link come from the `PackageResult`. Its `added` and
  `removed` read `result.added or 0` and `result.removed or 0`, since a
  `PackageResult` defaults both to `None` (`saffron/phases/package.py:645-646`).

The two `run_task` sites pass `added=0`, `removed=0` and `link=""`. All three
derive `concerns` with `anchored_concerns(outcome.reviews)`, and `sustained`
and `unkept` with `sustained_blockers` and `unkept_fixes` over
`outcome.rebut_result`. Each passes the outcome's `attempts`, `spent_usd`,
`effective_risk`, `unread` and `unanswered`. Each writes with
`header=index_report.accept_rate_header(ledger)`.

`QueueLine` defaults its last six fields (`saffron/report/index.py:102-121`).
So a field added there and missed at one site is a silent zero rather than a
`TypeError`.

**Where the builder goes.** `saffron/phases/package.py` already imports the
three derivations (`saffron/phases/package.py:38-39`) and `index_report`
(`saffron/phases/package.py:40`). `saffron/task.py` already imports the
module as `package_phase` (`saffron/task.py:79`) and calls
`package_phase.push_unpackaged_work` and `package_phase.package` through it.
So the builder adds no import edge. In `saffron/report/index.py` it would add
two: today that module imports only `saffron.cell.session`, `saffron.ledger`
and `saffron.scheduler` from this package (`saffron/report/index.py:20-22`).

## Problem

1. **`saffron/phases/package.py`.** Add `queue_line` as criterion 1 names it,
   at module scope. Leave its `outcome` parameter unannotated, as `_finish`'s
   is (`saffron/phases/package.py:1048`). An annotation would add an import
   of `saffron.cell.session` that this module lacks today. Its body is the one `QueueLine` construction a task's end
   uses. Replace `_finish`'s construction with a call to it, passing
   `result.added or 0` and `result.removed or 0` as today. Leave `_finish`'s
   `append_queue_line` call and its `header` as they are.
2. **`saffron/task.py`.** Replace the constructions at `:1079` and `:1120`
   with calls to `package_phase.queue_line`, handing each what differs: the
   state and the note. Leave both `append_queue_line` calls and their
   `header` as they are. `sustained_blockers`, `unkept_fixes` and
   `anchored_concerns` then have no use left in `saffron/task.py`. Drop them
   from its imports at `:86`, `:88` and `:94`, since `lint` fails an unused
   import. Leave `_live_row` (`saffron/task.py:935-947`) as it is.
3. **`tests/test_task.py`.** Add the three new witnesses. Leave every existing
   test unedited.

## Out of scope

- **`_live_row`** (`saffron/task.py:935-947`). It writes the live row while
  the cell runs, before any outcome exists. It reads `spec.risk` and zero
  attempts, and shares no derivation with the three sites. `DESIGN.md` §6
  names it apart from the queue line that later replaces it.
- **`saffron/replay.py:128`.** v0's agent-free replay builds its row from a
  replayed pull request, with no cell outcome. It passes one attempt, no
  cost and a link to `pr_body.md`. `CLAUDE.md` says v1 deletes the module.
- **`docs/evidence/scripts/2026-08-25-queue-from-ledger.py:67`**, an evidence
  script that rebuilds rows from the ledger, and every `QueueLine` a test
  builds by hand.
- **`saffron/report/index.py:428`.** `_existing_queue_rows` rebuilds each stored
  row with `QueueLine(**item)` as it reads `queue.json` back. That builds no
  row from an outcome, and the file lies outside criterion 3's walk.
- **b-edcab7's three stale sentences.** They are in files this spec forbids.

## Notes for the agent

**This is a refactor.** Criteria 4 to 9 are `preserves`. Each names a test
that passes at base, and each must pass unedited. Criteria 1 to 3 are new
witnesses, and each fails at base. Criteria 1 and 2 fail there with
`AttributeError`, since `saffron.phases.package` has no `queue_line`.
Criterion 3 fails because three constructions sit in `run_task` and
`_finish`. `refs/saffron/mutants` is absent from origin
(`git ls-remote origin refs/saffron/mutants` prints nothing), so no criterion
carries a mutant. The `witness` gate reports `skip` for each. The wrong
versions under each criterion are what its witness must kill. Do not apply them
yourself.

**Reach `queue_line` by module attribute in the witnesses.** Call it as
`package_phase.queue_line` inside each test. An import of the name at module
scope makes `revert`'s pass over the reverted source a collection error,
which it reads as `skip`.

**Criterion 1's outcome.** Build `CellOutcome` with `spent_usd=17.5`,
`attempts=13`, `effective_risk="elevated"`, `unread=7` and `unanswered=11`.
Use one `LensReview` holding five `Finding`s: two anchored concerns, one
unanchored concern, one anchored note and one anchored blocker. Give the
`RebutResult` a `RebuttalTurn` that argues findings 1 to 3 and fixes 4 to 8,
a `LensVerdicts` confirming 1 to 8, and `moved=False`. `_confirmed_with`
(`saffron/phases/rebut.py:747-767`) then counts 3 sustained and 5 unkept.
Compare `dataclasses.asdict` of each row with a full dict, never field by
field. The call naming every caller field passes non-default, distinct
values: `repo_name="r"`, `spec_id="SY-1"`, `state="READY_FOR_REVIEW"`,
`note="opened"`, `added=19`, `removed=23` and `link="https://x/pull/1"`.

**Criterion 2's drive.** `_drive`, `_push` and `_rows` at
`tests/test_task.py:44-129` already drive `run_task` with `run_one_cell` and
`push_unpackaged_work` replaced. Replace the push with
`_push(monkeypatch, PushResult(pushed=False, note=_NO_COMMITS))`, as
`test_both_queue_writers_put_the_trailing_accept_rate_in_the_header` does
(`tests/test_task.py:316`), so the unpackaged row's note is not empty. Give each of the five rows its own
`out_dir` and the spec id `SY-1`. Each `queue.json` then holds one row, and
`spec_id` is a shared field. Build every outcome from one helper holding
criterion 1's values, so `_drive`'s spec keeps its default `standard` while
each outcome is `elevated`. For the `EXHAUSTED` row, replace
`package_phase.package` with one returning
`PackageResult(state="EXHAUSTED", note="conflicts with main")`. Keep the
anchored blocker in the review and give that outcome no `rebut_result`, as
`exhausted_package` requires (`saffron/task.py:1011-1015`). Its `sustained`
and `unkept` are then 0. So compare it with the unpackaged row driven with no
rebuttal, and compare the rebutted unpackaged row with the two `_finish`
rows. For `_finish`, create the task on a `Ledger` of the test's own, since
`set_task_package` writes its row (`saffron/phases/package.py:1052-1060`).
Then call `package_phase._finish` positionally, as
`tests/test_task.py:366` does, with `"target-repo"` as its repo name, so
`repo` matches `run_task`'s rows (`tests/test_task.py:106`). Set the spy with
`monkeypatch.setattr(package_phase, "queue_line", spy)` and
`monkeypatch.setattr(task_module, "queue_line", spy, raising=False)`. Have
it call the real function it wrapped and record the row it returns.

**Criterion 3's walk.** Use `ast`, reading each file from the repo root.
Descend through every node, carrying the name of the innermost
`FunctionDef` or `AsyncFunctionDef` above it. Count a `Call` whose `func` is
an `Attribute` with `attr` `QueueLine` or a `Name` with `id` `QueueLine`.
Compare the sorted list of `(path, function)` pairs exactly, so a walk that
finds nothing fails.

**Docstrings and comments.** The `prose` gate reads each one you add. Keep
the builder's docstring to a line or two naming why it exists.
