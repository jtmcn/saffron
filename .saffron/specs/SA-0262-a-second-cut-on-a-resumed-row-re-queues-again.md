---
id: SA-0262
title: A batch resumes a cut's own row, so the re-queue cap finds no earlier cut and a second cut re-queues again
type: bug
priority: 1
depends_on: [SA-0259]
estimated_lines: 205
estimate_measured: true
touches:
  - saffron/cell/session.py
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
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/reconcile.py
  - saffron/record/**
  - saffron/report/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/phases/**
  - saffron/cell/runtime.py
  - saffron/cell/worktree.py
  - tests/test_ledger.py
  - tests/test_scheduler.py
  - tests/test_task.py
  - tests/test_cli.py
budget_usd: 30
max_attempts: 3
max_turns: 140
acceptance:
  - claim: >-
      A second zero-commit cut on a resumed row ends `NOT_IMPLEMENTED`
      when the row's last cell ended it `ORPHANED` by a cut. Its cut-again
      line names the row's own task id, and no new task row is minted.
      Each bound drives each side once. A wall cut then a turn-ceiling
      cut, a turn-ceiling cut then a budget-cap cut, and a budget-cap cut
      then a wall cut. A resumed row is no earlier cut when a raise left
      it `ORPHANED` with its run `ABORTED`, or a scan left it `ORPHANED`
      with its run still `RUNNING`. Each of those two holds one
      `IMPLEMENTING` attempt, its latest. Neither is a row left
      `GATE_ERROR` after a salvaged turn-ceiling cut. Each of those three
      ends `ORPHANED` on its own first zero-commit cut, with no cut-again
      line.
    witness: tests/test_session.py::test_a_second_cut_on_a_resumed_row_settles_the_spec
    wrong_versions:
      - The row's own cut read at the cut itself, after the cell set the row `IMPLEMENTING`, so it never counts.
      - Every resumed row counted as an earlier cut.
      - A resumed row counted when its state is `ORPHANED`, whatever its run's status.
      - A resumed row counted when its run is not `ABORTED`, so a scan's stamp counts.
      - A resumed row counted on its run and its attempts alone, whatever its state, so the `GATE_ERROR` row counts.
      - A resumed row counted when an earlier `IMPLEMENTING` attempt carries a turn ceiling's or a budget cap's fields, which misses a first wall cut and counts the salvaged row.
  - claim: >-
      The cap counts an `ORPHANED` row whose run finished `COMPLETE` and
      whose latest attempt, by `attempt_id`, is in phase `IMPLEMENTING`.
      The phases its earlier attempts reached do not matter. The witness
      drives four earlier shapes. Three open with three `IMPLEMENTING`
      attempts, then add `REPAIRING`, or `REVIEWING`, or `REPAIRING`,
      `REVIEWING` and `REBUTTING`. The fourth is `SPEC_REVIEW` then
      `SPEC_WRITING`. Each is driven on another row at the same
      `spec_sha` and on the resumed row itself. Every seeded row's
      `started_at` runs backwards against its `attempt_id`. With a
      trailing `IMPLEMENTING` attempt, the next zero-commit cut ends
      `NOT_IMPLEMENTED` and names that row. Without one, the row does not
      count, and the next cut ends `ORPHANED` with no cut-again line.
    witness: tests/test_session.py::test_a_cut_after_a_repair_a_review_or_a_rebuttal_still_counts
    wrong_versions:
      - Today's phase rule kept for another row, where any attempt outside `IMPLEMENTING`, `SPEC_REVIEW` and `SPEC_WRITING` disqualifies it.
      - The widened rule used for another row while the resumed row keeps today's rule.
      - The phase rule dropped, so a row whose latest attempt is `REBUTTING` counts.
      - The rule widened to allow `REBUTTING` alone, so a row that went through `REPAIRING` or `REVIEWING` still never counts.
      - A row counted when any of its attempts is `IMPLEMENTING`, so a row whose latest attempt is `REVIEWING` counts.
      - A row disqualified only when its latest attempt is `REBUTTING`, so a latest `REPAIRING` or `REVIEWING` attempt counts.
      - The latest attempt found by `started_at`, which has one-second resolution and ties.
      - The latest attempt found by the highest `n`, which numbers within one phase only.
      - A latest `SPEC_REVIEW` or `SPEC_WRITING` attempt counted as well as `IMPLEMENTING`.
---

## Context

Backlog item **b-3bba0f**, found by the first review of `SA-0230`. It
cites `DESIGN.md` §4.5 and §4.2.1. Every line number below was read at
`dfdc807e`.

**The cap looks for the earlier cut on another row.** §4.5 lets the first
zero-commit cut at a `spec_sha` end `ORPHANED`. A second ends
`NOT_IMPLEMENTED`. At the cut, `_drive_cell` calls `previous_cut_orphan`
(`saffron/cell/session.py:2565-2574`). That query excludes the row it runs
for (`saffron/cell/session.py:501`). It counts a row in state `ORPHANED`
whose run finished `COMPLETE` (`:502-503`). It also refuses a row with any
attempt outside `IMPLEMENTING`, `SPEC_REVIEW` and `SPEC_WRITING`
(`:504-508`).

**A batch resumes the cut's own row.** `ORPHANED` is in `REQUEUE_STATES`
(`saffron/scheduler.py:111-120`). The scan hands the newest such row to
the candidate as its `task_id` (`saffron/scheduler.py:909-911`).
`run_task` puts it on the `CellSpec` (`saffron/task.py:533-549`). The
cell then reads that row's run and mints no row
(`saffron/cell/session.py:1961-1966`). So the second cut runs on the first
cut's row. The query excludes that row and finds no other. The row ends
`ORPHANED` again, and the next scan queues the spec again.

**What a cut leaves on its row.** The row enters `IMPLEMENTING` before
the plan turn (`saffron/cell/session.py:2114`). `record_attempts` opens
each turn's attempt under the row's state at that time
(`saffron/cell/session.py:251-272`, `saffron/ledger.py:1441-1467`). So a cut
cell's attempts are all `IMPLEMENTING`, and they are the row's latest. The
cut finishes the run `COMPLETE` (`saffron/cell/session.py:2575-2576`). A
raise finishes it `ABORTED` instead (`:3301-3307`). Once a run exists, only
`finish_run` changes its status (`saffron/ledger.py:1149-1154`), so a resumed run
keeps its last cell's status until the next cell ends.

**The bound is not on the attempt.** A wall cut produces no result event.
Its attempt closes with subtype `error` and no terminal reason
(`saffron/phases/implement.py:389-405`). `_close_attempt` keeps no
`bound` field (`saffron/cell/session.py:278-292`). An attempt row cannot
tell a wall cut from a crash. A turn-ceiling cut that the salvage turn
rescues leaves the same attempts as one it does not. Commits are not on
the attempt either. So the attempts alone cannot say the last cell was a
zero-commit cut. The row's state and its run's status, read before the
next cell moves them, can.

**Which attempt is latest.** `attempt_id` is the only order. The fold
writes `started_at` from the fact's time (`saffron/ledger.py:751-755`).
`_ledger_time` truncates that time to whole seconds
(`saffron/ledger.py:343-346`). `n` numbers attempts within one phase only
(`saffron/ledger.py:1447-1453`).

**Only `IMPLEMENTING` ends a cut row.** `SPEC_REVIEW` and `SPEC_WRITING`
attempts open before a cell. They open at `saffron/batch.py:595` and
`:703`, and at `saffron/follow_up.py:255`. They also open at
`saffron/draft.py:137`, called at `:203`, `:232` and `:267`. A cell sets the row
`IMPLEMENTING` before its plan turn (`saffron/cell/session.py:2114`). So
every cut row's latest attempt is `IMPLEMENTING`.

**One test asserts today's phase rule.**
`test_a_task_orphaned_by_anything_but_a_cut_leaves_the_retry` seeds its
task 4 with `IMPLEMENTING`, `REBUTTING` and `IMPLEMENTING` attempts, run
`COMPLETE` (`tests/test_session.py:2812-2820`). It asserts the next cut
still ends `ORPHANED` (`:2870-2871`). Under this change that row is a cut
after a rebuttal, and counts.

## Problem

Make the cap count the resumed row's own earlier cut. Then widen its
phase rule to a row that reached REPAIR, REVIEW or REBUT before its cut.

**The resumed row.** When `_drive_cell` takes a given `task_id`, read
whether that row was cut before the cell changes its state. It was cut
when its state is `ORPHANED`, its run finished `COMPLETE`, and its latest
attempt by `attempt_id` is `IMPLEMENTING`. At a zero-commit cut, settle
`NOT_IMPLEMENTED` when another row counts, or when this read said so. The
cut-again line names a row that counted. Make no schema change.

**The phase rule.** Judge a row by its latest attempt by `attempt_id`,
not by every attempt it holds. It counts only when that attempt is
`IMPLEMENTING`. Apply the same rule to another row and to the resumed row
itself.

Then edit task 4 in
`test_a_task_orphaned_by_anything_but_a_cut_leaves_the_retry` so it still
does not count. Drop its trailing `IMPLEMENTING` attempt, and make its
comment say it stopped at `REBUTTING` and a scan stamped it. Keep every
other assertion in that test. Then rewrite the docstring of
`test_a_revised_specs_second_cut_settles_on_its_task_rows_spec_sha`
(`tests/test_session.py:3022-3025`). It says the phase clause allows
`SPEC_REVIEW` and `SPEC_WRITING`, and that any `REVIEWING` or `REPAIRING`
attempt disqualifies a row. Say instead that a row counts only when its
latest attempt is `IMPLEMENTING`.

## Out of scope

- **A fact carrying the run's status.** A ledger folded from the record
  still loses `runs.status`. Backlog item b-cafacd owns that.
- **One cut remembered per row.** The resumed row's read sees only the
  cell that ended it last. A cut, then a cell ending the row
  `RATE_LIMITED`, `PROVIDER_UNREACHABLE`, `PREFLIGHT_FAILED`,
  `GATE_ERROR`, `CHANGES_REQUESTED` or `ORPHANED` by a raise, erases it.
  The next cut then ends `ORPHANED` again, and the delay can repeat.
- **A cell killed without a raise on a resumed row.** At base the cap
  never reads the resumed row. This change makes it read one whose
  previous cell finished its run `COMPLETE`. Those are rows left
  `RATE_LIMITED`, `PROVIDER_UNREACHABLE`, `PREFLIGHT_FAILED`,
  `GATE_ERROR`, `CHANGES_REQUESTED` or `ORPHANED` by a cut. Suppose the
  next cell dies in IMPLEMENT with no raise. The run keeps `COMPLETE`, and
  a scan stamps the row `ORPHANED` (`saffron/reconcile.py:195-198`). The
  row then reads as a cut, against §4.5's kill or scan exclusion. Base has
  no SIGTERM handler. The only `signal.` call in `saffron/` is
  `saffron/gates/runner.py:78`. Queued `SA-0245` and `SA-0258` make
  SIGTERM raise `KeyboardInterrupt` in `saffron cell` and `saffron batch`.
  That reaches the `except BaseException` that finishes the run `ABORTED`
  (`saffron/cell/session.py:3301-3307`). So once both merge, a SIGTERM no
  longer reads as a cut. A SIGKILL or a host crash still does. This spec
  does not depend on either.
- **`saffron/ledger.py`.** Read the tables through `ledger._db`, as
  `previous_cut_orphan` does today.
- **`DESIGN.md`.** §4.5 is edited by hand with this spec.

## Notes for the agent

**Both criteria are new code**, so each declares a witness and no
mutant, and `witness` will report `skip`. The resumed row's read does not
exist at base. The phase clause it replaces is rewritten, so no text of
it survives for a mutant to name.

**Which row the cut-again line names** is unpinned when another row
and the resumed row both count. Either is an earlier cut at this
`spec_sha`, and the state is the same. No code reads the id.
`saffron/events.py:966` matches the line's prefix alone.

**Read the resumed row early.** Read it inside the branch that takes
`spec.task_id`, before any `set_task_state` call. Read at the cut, the row
is already `IMPLEMENTING` and never counts.

**At base both witnesses fail in the test body.** Neither imports a name
the change adds. Criterion 1's second cell ends `ORPHANED` at base.
Criterion 2's trailing-`IMPLEMENTING` cases end `ORPHANED` at base.

**Criterion 1** drives `_drive` twice per bound pair, on one ledger per
pair, in one plain test. Use `_spec(task_id=...)` with the first
outcome's `task_id`. The three bounds are `_wall_cut_turn`, an
`implement.AgentFailed` around `_cut_off_turn`, and `_budget_cut_turn`.
Give each cut a salvage turn after it, as
`test_a_second_cut_at_one_spec_sha_settles_the_spec` does. Seed the three
rows that are no earlier cut through the `Ledger` API, each on its own
ledger. The `GATE_ERROR` row holds three `IMPLEMENTING` attempts, the
second closed with a turn ceiling's subtype and terminal reason. Its run
finishes `COMPLETE`, as a real `GATE_ERROR` does
(`saffron/cell/session.py:3238-3241`). Left `RUNNING`, it no longer
kills the fifth wrong version. The
raised row and the scanned row each hold one `IMPLEMENTING` attempt, so
it is their latest. Without it the state and run checks go untested. The
scanned row's run is never finished.

**Criterion 2** loops over the four shapes, with and without the
trailing `IMPLEMENTING` attempt, on another row and on the resumed row.
That is sixteen cells, each on its own ledger. Seed each row `ORPHANED`
with its run `COMPLETE`. Then write each attempt's `started_at` through
`ledger._db`, latest first for the lowest `attempt_id`. Commit that
write with `ledger._db.commit()` before `ledger.close()`. An uncommitted
write is lost on close, and every attempt then shares one second. Before
driving each cell, open the ledger again and assert one seeded row's
`started_at` values fall as its `attempt_id` rises. Opening the
non-`SPEC_*` shapes with three `IMPLEMENTING` attempts gives a trailing
`REVIEWING` a lower `n` than an earlier `IMPLEMENTING` attempt. On
another row, the cell mints its own row. On
the resumed row, pass the seeded row's id as `task_id`. Copy the seeding
shape from `test_a_revised_specs_second_cut_settles_on_its_task_rows_spec_sha`.

**`saffron/cell/**` is in `elevate_on`,** so this task runs `elevated`
and `size` blocks.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Update `previous_cut_orphan`'s docstring where it
describes the phase rule and says it excludes `task_id` itself.

**Size.** A prototype with both witnesses and both test edits measured
769 tokens with `size_gate`'s counter, against the `bug` ceiling of 1300.
`estimated_lines` is that count over four, plus a margin for docstrings.
