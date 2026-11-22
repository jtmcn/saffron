---
id: SA-0423
title: "An unpackaged queue line hides its pushed branch's diff stat, and a failed queue line write turns a failed task into exit 2"
type: bug
priority: 2
depends_on: [SA-0422]
estimated_lines: 50
estimate_measured: true
touches:
  - saffron/task.py
  - saffron/phases/package.py
  - tests/test_task.py
  - tests/test_package.py
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
  - saffron/report/**
  - saffron/repos/**
  - saffron/record/**
  - saffron/cell/**
  - saffron/ledger.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/events.py
  - tests/test_report.py
  - tests/test_cli.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
budget_usd: 60
max_attempts: 3
max_turns: 260
acceptance:
  - claim: >-
      A pushed `PushResult` from `push_unpackaged_work` carries the diff stat
      of `tree_base` to the pushed commit, in two new fields `added` and
      `removed`. The stat is read after the push and after
      `ledger.record_push`. A stat that cannot be read leaves the result
      pushed and the push recorded, emits a line carrying the error's text,
      and sets both fields to `None`. The witness moves the default branch
      one commit past `tree_base` and points `patch.json`'s `base_sha` at that
      commit, so a stat read from either of them differs. A first push has
      `diff_stat` replaced by a spy that records its arguments and raises
      `GitError`. When called, the spy reads the remote branch and the
      ledger's `pushed_sha`, and both already hold the commit it was handed.
      The push returns pushed, with `None` for both counts, and both the
      remote branch and the ledger's `pushed_sha` hold its `pushed_sha`. A
      second push has `diff_stat` raise `OSError`. It returns pushed, with
      `None` for both counts, and emits a line carrying that error's text. A
      third push, with the real stat, carries the fixture's +2/−1.
    witness: tests/test_package.py::test_pushed_unpackaged_work_carries_its_branchs_diff_stat_against_its_tree_base
    positive_case: >-
      The spy records exactly one call, with `tree_base` and the result's
      `pushed_sha`, so the witness sees the stat read that then fails.
    wrong_versions:
      - "The stat is read from `patch.json`'s `base_sha`, not `tree_base`."
      - "The stat is read from the default branch's head, as PACKAGE reads its own."
      - "The two counts are unpacked swapped."
      - "The stat is read inside the push's `try`, after `push_with_lease`, so a failed stat returns a refusal for a branch that was pushed."
      - "The stat is read inside the push's `try`, before `push_with_lease`, so a failed stat pushes nothing."
      - "A failed stat raises out of `push_unpackaged_work`."
      - "A failed stat is swallowed with nothing emitted."
      - "A failed stat catches `GitError` alone."
      - "The stat is read before `ledger.record_push`, and a failed stat returns before the push is recorded."
      - "The stat is read in a guard of its own before `push_with_lease`."
      - "The stat is read in a guard of its own after `push_with_lease` and before `ledger.record_push`."
      - "`PushResult` carries no stat, as at your base."
    covers:
      - set: the commit the stat is read from
        members:
          - member: "`tree_base`"
            driven_by: tests/test_package.py::test_pushed_unpackaged_work_carries_its_branchs_diff_stat_against_its_tree_base
          - member: "`patch.json`'s `base_sha`"
            driven_by: "The stat is read from `patch.json`'s `base_sha`, not `tree_base`."
          - member: the default branch's head
            driven_by: "The stat is read from the default branch's head, as PACKAGE reads its own."
      - set: the order of the two counts
        members:
          - member: added, then removed
            driven_by: "The two counts are unpacked swapped."
      - set: when the stat is read
        members:
          - member: after the push
            driven_by: "The stat is read in a guard of its own before `push_with_lease`."
          - member: after `ledger.record_push`
            driven_by: "The stat is read in a guard of its own after `push_with_lease` and before `ledger.record_push`."
      - set: what a stat that cannot be read leaves
        members:
          - member: the result still pushed
            driven_by: "The stat is read inside the push's `try`, after `push_with_lease`, so a failed stat returns a refusal for a branch that was pushed."
          - member: the remote branch at the pushed commit
            driven_by: "The stat is read inside the push's `try`, before `push_with_lease`, so a failed stat pushes nothing."
          - member: the push recorded in the ledger
            driven_by: "The stat is read before `ledger.record_push`, and a failed stat returns before the push is recorded."
          - member: no raise, for a `GitError`
            driven_by: "A failed stat raises out of `push_unpackaged_work`."
          - member: no raise, for an `OSError`
            driven_by: "A failed stat catches `GitError` alone."
          - member: a line through `emit`
            driven_by: "A failed stat is swallowed with nothing emitted."
  - claim: >-
      Both queue lines `run_task` writes after `push_unpackaged_work` carry
      the `added` and `removed` its `PushResult` holds. One is the line for a
      task PACKAGE never ran. The other is the `EXHAUSTED` line for a task
      whose PACKAGE opened no pull request. The witness hands each a pushed
      `PushResult` of +2/−1. The second task's `package` returns a refusal
      carrying its own stat of +9/−9, and its line still reads +2/−1.
    witness: tests/test_task.py::test_both_rows_after_a_push_carry_the_pushed_branchs_diff_stat
    positive_case: >-
      Each line reads the +2/−1 of the `PushResult` the witness handed it,
      and the second reads it beside a refusal's +9/−9.
    wrong_versions:
      - "Only the line for a task PACKAGE never ran carries the stat."
      - "Only the `EXHAUSTED` line carries the stat."
      - "The two counts are passed swapped."
      - "The `EXHAUSTED` line takes the stat from PACKAGE's refusal rather than from the push."
    covers:
      - set: the queue lines written after a push
        members:
          - member: the line for a task PACKAGE never ran
            driven_by: "Only the `EXHAUSTED` line carries the stat."
          - member: the `EXHAUSTED` line after an exhausted PACKAGE opened nothing
            driven_by: "Only the line for a task PACKAGE never ran carries the stat."
      - set: where the stat comes from
        members:
          - member: the `PushResult` over PACKAGE's refusal
            driven_by: "The `EXHAUSTED` line takes the stat from PACKAGE's refusal rather than from the push."
      - set: the order of the two counts
        members:
          - member: added, then removed
            driven_by: "The two counts are passed swapped."
  - claim: >-
      An `Exception` raised while `run_task` writes either queue line at a
      task's end is printed and never leaves `run_task`. It returns its
      outcome as it does when the write lands, so `saffron cell` exits by
      the outcome's own state. This covers a raise out of
      `append_queue_line` and one out of `accept_rate_header`, on the line
      for a task PACKAGE never ran and on the `EXHAUSTED` line. The printed
      line names the spec id, the line's state and the error's text. It
      comes before the task's status line, which still prints. A
      `KeyboardInterrupt` still leaves `run_task` from either line. The
      witness drives eleven failures, with `_Unlisted` a test-local
      `Exception` subclass. Five hit a `NOT_IMPLEMENTED` task: an `OSError`,
      a `ValueError`, a `CellRuntimeError` and an `_Unlisted` from
      `append_queue_line`, and an `sqlite3.OperationalError` from
      `accept_rate_header`. Five hit an `EXHAUSTED` task whose PACKAGE
      refused: an `OSError`, a `ValueError` and an `_Unlisted` from the
      first, and an `sqlite3.OperationalError` and a `RuntimeError` from the
      second. One hits a `GATE_ERROR` task with an `OSError`. Each returns its outcome at
      its own state, which `CELL_EXIT` maps to 1, and to 2 for `GATE_ERROR`.
      Then a `KeyboardInterrupt` subclass from `append_queue_line` leaves
      `run_task`, once on each line.
    witness: tests/test_task.py::test_a_failed_end_row_write_is_said_and_run_task_still_returns
    positive_case: >-
      Each failing fake records that it was reached, and the task's status
      line prints after the report, so the witness sees the write tried and
      the task's end reached.
    wrong_versions:
      - "Neither write is guarded, as at your base."
      - "The guard catches `OSError` alone."
      - "`accept_rate_header` is called outside the guard."
      - "Only the line for a task PACKAGE never ran is guarded."
      - "Only the `EXHAUSTED` line is guarded."
      - "A failed write is swallowed with nothing printed."
      - "The guard catches `BaseException`."
      - "One guard wraps the write and the status line, so a failed write skips the status line."
      - "The guard catches `(OSError, ValueError, sqlite3.Error)`."
      - "The `EXHAUSTED` line alone catches `BaseException`."
      - "The printed line names the spec id and the error, but not the state."
      - "The guard catches `(OSError, ValueError, sqlite3.Error, RuntimeError)`."
      - "The `EXHAUSTED` line catches `OSError`, `sqlite3.Error` and `RuntimeError` alone."
    covers:
      - set: the queue lines `run_task` writes at a task's end
        members:
          - member: the line for a task PACKAGE never ran
            driven_by: "Only the `EXHAUSTED` line is guarded."
          - member: the `EXHAUSTED` line after an exhausted PACKAGE opened nothing
            driven_by: "Only the line for a task PACKAGE never ran is guarded."
      - set: where the raise comes from
        members:
          - member: "`append_queue_line`"
            driven_by: "Neither write is guarded, as at your base."
          - member: "`accept_rate_header`"
            driven_by: "`accept_rate_header` is called outside the guard."
      - set: the kind of raise
        members:
          - member: "`OSError`"
            driven_by: "Neither write is guarded, as at your base."
          - member: "`ValueError` and `sqlite3.Error`"
            driven_by: "The guard catches `OSError` alone."
          - member: a `RuntimeError`
            driven_by: "The guard catches `(OSError, ValueError, sqlite3.Error)`."
          - member: "an `_Unlisted`, so any `Exception`"
            driven_by: "The guard catches `(OSError, ValueError, sqlite3.Error, RuntimeError)`."
          - member: a `ValueError` on the `EXHAUSTED` line
            driven_by: "The `EXHAUSTED` line catches `OSError`, `sqlite3.Error` and `RuntimeError` alone."
          - member: "`KeyboardInterrupt` on the line for a task PACKAGE never ran, which still leaves"
            driven_by: "The guard catches `BaseException`."
          - member: "`KeyboardInterrupt` on the `EXHAUSTED` line, which still leaves"
            driven_by: "The `EXHAUSTED` line alone catches `BaseException`."
      - set: what a failed write leaves
        members:
          - member: a printed line
            driven_by: "A failed write is swallowed with nothing printed."
          - member: the line's state in it
            driven_by: "The printed line names the spec id and the error, but not the state."
          - member: the status line
            driven_by: "One guard wraps the write and the status line, so a failed write skips the status line."
  - claim: >-
      `_finish` hands an `Exception` raised while it writes its queue line
      to a new keyword-only parameter `say`, and returns its result. The
      ledger write before it stands. The line names the result's state and
      the error's text. On a pull request PACKAGE opened and on a credential
      refusal, it reaches `emit`. A `KeyboardInterrupt` still leaves
      `package()`. A raise out of `set_task_package` still leaves `package()`.
      The witness calls `package()` on the `packageable` fixture seven times,
      each with one failing fake, and `_Unlisted` is a test-local `Exception`
      subclass. First `append_queue_line`
      raises `OSError` and `gh` opens a pull request. `package()` returns
      `READY_FOR_REVIEW`, the ledger holds that state and the pull request's
      URL, and an emitted line carries the state and the error's text. Then
      a credential in the patch reaches `_finish` as `MERGE_FAILED` four
      times, with the ledger moved back to `READY_FOR_REVIEW` before each.
      They raise a `ValueError` from `append_queue_line`, an
      `sqlite3.OperationalError` from `accept_rate_header`, and a
      `CellRuntimeError` and an `_Unlisted` from `append_queue_line`. Each
      returns `MERGE_FAILED`, the ledger holds `MERGE_FAILED`, and an emitted
      line carries the state and the error's text. Then a
      `KeyboardInterrupt` subclass from `append_queue_line` leaves
      `package()`. Last, `set_task_package` raises an `_Unlisted`, and
      `package()` raises that same object.
    witness: tests/test_package.py::test_a_failed_queue_row_in_finish_is_said_and_its_result_still_returns
    positive_case: >-
      Each failing fake records that it was reached, in order, so the witness
      sees each write tried before it reads the result and the events.
    wrong_versions:
      - "`_finish` guards nothing, as at your base."
      - "`_finish` catches `OSError` alone."
      - "`_finish` swallows a failed write with nothing emitted."
      - "`_finish` prints the line rather than handing it to `say`."
      - "Only a `_finish` whose result carries a pull request is guarded."
      - "`_finish` calls `accept_rate_header` outside the guard."
      - "`_finish` catches `(OSError, ValueError, sqlite3.Error)`."
      - "One guard wraps `set_task_package` and the header, so a failed header skips the ledger write."
      - "`_finish` catches `BaseException`."
      - "`_finish`'s line names the error, but not the state."
      - "`_finish` catches `(OSError, ValueError, sqlite3.Error, CellRuntimeError)`."
      - "A `_finish` guard whose try also wraps `set_task_package`, with the ledger write still before the header and the append."
    covers:
      - set: the paths into `_finish`
        members:
          - member: a pull request PACKAGE opened
            driven_by: "`_finish` guards nothing, as at your base."
          - member: a refusal
            driven_by: "Only a `_finish` whose result carries a pull request is guarded."
      - set: where the raise comes from
        members:
          - member: "`append_queue_line`"
            driven_by: "`_finish` guards nothing, as at your base."
          - member: "`accept_rate_header`"
            driven_by: "`_finish` calls `accept_rate_header` outside the guard."
      - set: the kind of raise
        members:
          - member: "`OSError`"
            driven_by: "`_finish` guards nothing, as at your base."
          - member: "`ValueError` and `sqlite3.Error`"
            driven_by: "`_finish` catches `OSError` alone."
          - member: a `CellRuntimeError`
            driven_by: "`_finish` catches `(OSError, ValueError, sqlite3.Error)`."
          - member: "an `_Unlisted`, so any `Exception`"
            driven_by: "`_finish` catches `(OSError, ValueError, sqlite3.Error, CellRuntimeError)`."
          - member: "`KeyboardInterrupt`, which still leaves"
            driven_by: "`_finish` catches `BaseException`."
      - set: what a failed write leaves
        members:
          - member: the ledger written, even when the header raised
            driven_by: "One guard wraps `set_task_package` and the header, so a failed header skips the ledger write."
          - member: the result's state in the line
            driven_by: "`_finish`'s line names the error, but not the state."
          - member: a raise out of `set_task_package`, which still leaves
            driven_by: "A `_finish` guard whose try also wraps `set_task_package`, with the ledger write still before the header and the append."
      - set: how a failed write is said
        members:
          - member: through `emit`
            driven_by: "`_finish` swallows a failed write with nothing emitted."
          - member: never by `print`
            driven_by: "`_finish` prints the line rather than handing it to `say`."
---

## Context

Backlog item **b-bc54d1**, tier 2. It cites `DESIGN.md` §6 and §5.7. Every
line below was read at `344de2af`. This spec depends on `SA-0422`, and
`SA-0421` before it, which both edit `saffron/task.py`. `SA-0421` edits
`saffron/phases/package.py` too. So find each cited line by the function
named beside it.

**Who writes a task's queue line.** `run_task` writes two at a task's end.
The `EXHAUSTED` line for a task whose exhausted-mode PACKAGE opened no pull
request is at `saffron/task.py:1074-1084`. The line for a task PACKAGE never
ran is at `saffron/task.py:1105-1115`. `_finish` writes the third, for every
result `package()` returns (`saffron/phases/package.py:1094-1107`). All three
build it with `package_phase.queue_line` (`saffron/phases/package.py:1049`).

**The stat a pushed branch loses.** Both `run_task` lines follow a call to
`push_unpackaged_work` (`saffron/task.py:1059`, `:1092`). Neither passes
`added` or `removed`, and `queue_line` defaults both to 0
(`saffron/phases/package.py:1056-1057`). So a pushed branch's line reads
+0/−0. `push_unpackaged_work` reads `tree_base` from `patch.json`
(`saffron/phases/package.py:1214`), pushes at `:1319`, and records the push
at `:1329`. `PushResult` holds no stat field (`:1112-1121`). PACKAGE
reads its own stat with `mirror_ops.diff_stat` (`saffron/phases/package.py:861`).

**What a failed write does.** Nothing guards either `run_task` write. A
raise there leaves `run_task`. The comment on `CELL_EXIT` says a crash
takes exit 2, never 1 (`saffron/cli.py:94-96`). `_run_cell` maps
a returned outcome by its state instead (`saffron/cli.py:800`).
`push_unpackaged_work` "Never raises" for this reason
(`saffron/phases/package.py:1162-1166`). The live rows already guard
theirs with `except Exception` (`saffron/task.py:957`, `:981`).

`_finish` writes the ledger first (`saffron/phases/package.py:1085`), then
its queue line. A raise out of that write reaches `run_task`'s
`except BaseException` (`saffron/task.py:1045`). For a cell that ended
`READY_FOR_REVIEW`, that branch rewrites the task's state to
`READY_FOR_REVIEW` and marks the raise (`:1048-1050`). So a `MERGE_FAILED`
refusal whose line failed reads `READY_FOR_REVIEW` in the ledger, and the
task exits 2.

**A test asserts the raise.** Case 5 of
`tests/test_task.py::test_a_raise_that_escapes_run_task_from_package_is_marked_and_kept`
raises `CellRuntimeError` from `append_queue_line` on a `GATE_ERROR` cell. It
expects that raise to leave `run_task` unmarked (`tests/test_task.py:2563-2584`).
Its docstring says so (`:2407-2409`). The mark matters only to a batch,
which reads `raised_in_package` under `except Exception`
(`saffron/batch.py:327`, `:344`, `:958-962`). The `push_unpackaged_work`
call on that branch sits outside the new guard (`saffron/task.py:1092`).

**Why `say`.** `package.py` writes to no stream outside `emit`.
`tests/test_package.py::test_only_the_line_no_kind_carries_writes_to_a_stream_outside_emit`
fails a `print` there (`tests/test_package.py:1658-1691`). `_finish` holds no
`emit` today (`saffron/phases/package.py:1081`). Three tests call it
directly (`tests/test_task.py:401`, `:5473`, `:5505`).

## Problem

A pushed branch's queue line hides its diff stat, and a failed queue line
write turns a failed task into an infrastructure exit. Make these changes.

1. **The stat travels on `PushResult`.** Add `added` and `removed` to
   `PushResult`, both `int | None` and `None` by default. On a push that
   lands, read `mirror_ops.diff_stat(mirror, tree_base, pushed_sha)` after
   `ledger.record_push`, outside the push's `try`. Catch a
   `mirror_ops.GitError` or an `OSError` there. Report it through `_say`,
   and leave both fields `None`.
2. **Both `run_task` lines pass it.** Each line written after
   `push_unpackaged_work` passes the `PushResult`'s `added` and `removed`,
   with `None` as 0, since a `QueueLine` holds integers.
3. **`run_task` guards both writes.** Catch `Exception` around each write,
   with `accept_rate_header` inside the guard. Print one line naming the
   spec id, the state and the error, as `_write_live` does. Then go on to
   the status line and the rest of the branch. One local helper for both
   lines is fine.
4. **`_finish` guards its write.** Add a keyword-only `say` parameter,
   taking one string. Catch `Exception` around the write, with
   `accept_rate_header` inside the guard, and hand `say` a line naming the
   state and the error. Keep `set_task_package` outside the guard, so a
   raise out of the ledger write still leaves. Return the result. Pass `say=_emit_package` at
   every `_finish` call in `package()`. Add one sentence to `_finish`'s
   docstring saying a failed write is handed to `say`.
5. **The tests that call `_finish` or assert the raise.** Pass `say` at the
   three direct `_finish` calls in `tests/test_task.py`. Rewrite case 5 of
   `test_a_raise_that_escapes_run_task_from_package_is_marked_and_kept` to
   raise `CellRuntimeError` from the `push_unpackaged_work` double on its
   `GATE_ERROR` cell, and expect that same object, unmarked. Reword that
   case's sentence in the docstring to match.

## Out of scope

- **The ledger keeps no stat for an unpackaged push.** The stat reaches
  `queue.json` alone. `tasks.added` and `tasks.removed` stay what
  `set_task_package` last wrote. Carrying it there needs a field on the
  `task_push` fact (`saffron/ledger.py:1795-1801`), a fold change, and
  `saffron/ledger.py`, which is forbidden here.
- **A failed end write leaves the last live row standing.** The store keeps
  whatever `_write_live` last wrote, so the page still shows that phase.
  The printed line is the record of the miss.
- **A refused push's line.** A refused `PushResult` carries `None`, so its
  line still reads +0/−0. Nothing was pushed for it to describe.
- **The `EXHAUSTED` line replaces a refusal's `_finish` line.** That line
  carried PACKAGE's own stat, and the replacement now carries the push's.
  The comment at `saffron/task.py:1072-1073` already names the replacement.
- **One hand edit, landed in this spec's pull request.** `DESIGN.md` is
  forbidden here. In §6's paragraph on what the queue's rows read, two
  sentences changed, and this spec's pull request amended each. The first
  said PACKAGE appends a `QueueLine` per task. It was amended to the text
  below.

  > At a task's end, two writers append its `QueueLine` to a store in the
  > batch tree, and the page renders from it. PACKAGE appends one for every
  > result it returns. `run_task` appends one for a task that never reached
  > PACKAGE, and for an `EXHAUSTED` task whose PACKAGE opened no pull
  > request (`SA-0100`, `SA-0204`).

  The paragraph's sentence on `SA-0124` and the mock's stat was amended in
  this spec's pull request to the text below.

  > Since `SA-0124` PACKAGE's diff stat, the one this section's mock shows
  > (`+180/−22`), also lands in `tasks.added` and `tasks.removed`. A line
  > `run_task` writes after a push carries the stat of the branch it
  > pushed, and only `queue.json` holds that stat (`SA-0423`).

## Notes for the agent

**Edit or new.** Criterion 1 edits an existing read: the witness's spy pins
`tree_base`, which `push_unpackaged_work` already selects, so a mutant on
the ref swaps that selection. Criteria 2 to 4 are new guards and a new
parameter. No `find` written now pins their spelling, so each stands on its
witness alone, and `witness` reports `skip` for them.

**No `retired_first`.** Nothing here adds or widens a refusal.

**The `_finish` calls the fourth witness leaves.** `package()` calls
`_finish` at six sites. The witness reaches two: the pull request it opens
(`saffron/phases/package.py:1008`) and the credential refusal (`:821`). Four
more pass `say` too: a gone parent (`:758`), a conflict (`:805`), new
failures on re-verification (`:914`) and a rejected lease (`:980`). No
witness here drives them. The claim names only the two it drives.

**`tests/test_package.py`.**

- **The first witness.** Commit a five-line `g.txt` on the fixture's `main`
  in `packageable.work`, push it to `origin`, and `git fetch` in
  `packageable.mirror`. Write `patch.json` with that commit as `base_sha` and
  `packageable.base` as `tree_base`. A stat from the moved commit then reads
  +2/−6. Set `packageable.outcome.state` to `EXHAUSTED`. Push with the
  failing spy first, so the ledger holds no `pushed_sha` before it. Replace
  `saffron.repos.mirror.diff_stat`, since `package.py` reads it through its
  module. Restore it before the second push, which the fixture's ledger
  admits as a same-task push.
- **The fourth witness.** Use `_no_gh` for the refusals, and copy
  `test_a_credential_in_the_patch_is_refused_before_anything_is_pushed` for
  the credential. Replace `append_queue_line` and `accept_rate_header` on
  `saffron.report.index`. Read the events with `describe` from
  `packageable.events`, and clear that list between calls. Before each
  refusal, move the task back with
  `packageable.ledger.set_task_state(packageable.task_id, "READY_FOR_REVIEW")`,
  so each refusal's own ledger write shows. Match the state and the error's
  text in one emitted line. For the last call, replace `set_task_package`
  on `packageable.ledger` itself, the object `package()` is handed.

**`tests/test_task.py`.** Drive the second and third witnesses through
`_drive` and `_push`. An `EXHAUSTED` outcome reaches PACKAGE's exhausted mode
with an anchored blocker in `reviews` and `rebut_result=None`, as
`test_both_run_task_rows_carry_the_outcomes_unread_and_unanswered_counts`
does. Replace `package_phase.package` there with a refusal that opens
nothing. Read the printed lines with `capsys`, and match the spec id, the state and
the error's text in one line. An
`EXHAUSTED` task prints
its `EXHAUSTED` status line twice, so compare the report with the last one.
Import `sqlite3` at module scope. `PushResult(added=…)` sits inside a test
body, so a reverted source fails the test rather than its collection.

**Size.** A prototype on `SA-0422`'s and `SA-0421`'s prototype diffs at
`344de2af` measured 200 changed tokens outside the test paths with
`size_gate`. `estimated_lines` is that over four. It held all five steps and
the four witnesses. `ty check`, ruff, `prose_limit --tree` and
`.saffron/gates/structure` were clean. Each witness failed with the source
reverted. Every wrong version listed above failed its witness there. The
whole suite passed on that stacked prototype, 5457 tests.
