---
id: SA-0380
title: An `ORPHANED` task whose cell went green and was reviewed has no command that packages its patch, and its line names none
type: feature
priority: 2
estimated_lines: 380
estimate_measured: true
touches:
  - saffron/task.py
  - saffron/cli.py
  - saffron/batch.py
  - tests/test_task.py
  - README.md
  - CLAUDE.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
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
  - saffron/cell/**
  - saffron/phases/**
  - saffron/ledger.py
  - saffron/record/**
  - saffron/scheduler.py
  - saffron/reconcile.py
  - saffron/report/**
  - saffron/view/**
  - tests/test_batch.py
  - tests/test_cli.py
  - tests/test_session.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
  - tests/conftest.py
  - tests/fixtures/**
budget_usd: 50
max_attempts: 3
max_turns: 245
risk: standard
acceptance:
  - claim: >-
      `task.ready_task`, the rebuild `saffron package` runs, rebuilds an
      `ORPHANED` task whose cell recorded a `REVIEWING` turn and whose
      review reported no blocker and no errored lens. The `ReadyTask` it
      returns equals the one the same task rebuilds to once its row reads
      `READY_FOR_REVIEW`, so its outcome's state is `READY_FOR_REVIEW`.
      The rebuild writes no `tasks` row. The witness drives one such task
      whose review carries one anchored concern.
    witness: tests/test_task.py::test_ready_task_rebuilds_an_orphaned_task_whose_cell_went_green
    wrong_versions:
      - The outcome's state is copied from the row, so an `ORPHANED` task rebuilds to an `ORPHANED` outcome.
      - The rebuild writes `READY_FOR_REVIEW` to the row as soon as it admits an `ORPHANED` task.
      - The spend for an `ORPHANED` task leaves out its `REVIEWING` turns.
  - claim: >-
      `ready_task` refuses an `ORPHANED` task whose cell recorded no
      `REVIEWING` turn, and the reason names the task id, `ORPHANED` and
      `REVIEWING`. "This cell" is every turn at or after the cutoff
      `ready_task` already reads from `baseline.json`. The witness drives
      two such tasks. One has passing gate results on two suite turns of
      this cell and no `REVIEWING` turn. The other has a `REVIEWING` turn
      only before the cutoff. The same task with a `REVIEWING` turn after
      the cutoff is admitted.
    witness: tests/test_task.py::test_ready_task_refuses_an_orphaned_task_whose_cell_recorded_no_review_turn
    wrong_versions:
      - Any suite turn of this cell holding gate results reads as green.
      - A `REVIEWING` turn from any cell of the task reads as green, with no cutoff.
      - Any turn of this cell reads as green.
      - An `ORPHANED` task is admitted with no check of its turns.
  - claim: >-
      `ready_task` refuses an `ORPHANED` task whose review would not end
      `READY_FOR_REVIEW`. A lens that errored in `findings.json` is refused
      with a reason naming `ORPHANED` and that lens. A blocker
      `review.anchored_blockers` selects is refused, naming `ORPHANED` and
      `REBUT`, unless a `rebuttal.json` no older than `baseline.json`
      records the state `READY_FOR_REVIEW`. So is an entry of a
      `criterion-probes.json` or `wrong-versions.json` no older than
      `baseline.json` whose `error` is the text `review._review_pool_cut`
      writes, with a reason naming `ORPHANED` and that entry's witness.
      The witness drives an errored lens. It drives an anchored blocker with
      no rebuttal, a stale `READY_FOR_REVIEW` one, a fresh `EXHAUSTED` one
      and a fresh `REBUTTAL_UNJUDGED` one, and an unanchored `HOST_FILED`
      survivor with no rebuttal. In each of the two probe files it drives a
      fresh cut entry, a stale cut entry and a fresh entry whose `error` is
      another failure. The anchored blocker with a fresh `READY_FOR_REVIEW`
      rebuttal is admitted, and its outcome carries that rebuttal. So are
      the stale cut and the other failure. The errored lens, the survivor
      and the fresh cut in `wrong-versions.json` are each rebuilt once the
      row reads `READY_FOR_REVIEW`.
    witness: tests/test_task.py::test_ready_task_refuses_an_orphaned_task_whose_review_would_not_end_ready
    wrong_versions:
      - An `ORPHANED` task's review is not read at all.
      - Only blockers are read, so an errored lens is admitted.
      - Any `rebuttal.json` on disk is read, so a stale one admits the task.
      - Any fresh rebuttal admits the task, whatever its state.
      - Only an `EXHAUSTED` rebuttal is refused, so `REBUTTAL_UNJUDGED` is admitted.
      - Only anchored blockers are read, so an unanchored `HOST_FILED` survivor is admitted.
      - The probe files are not read, so a pool cut there is admitted.
      - A pool cut is read from a probe file older than `baseline.json`.
      - Any entry with an `error` refuses the task.
      - Only `criterion-probes.json` is read for a pool cut.
      - The review checks also run for a `READY_FOR_REVIEW` task.
  - claim: >-
      A `READY_FOR_REVIEW` task whose `findings.json` carries an errored
      lens is rebuilt as at base.
    witness: tests/test_task.py::test_ready_task_rebuilds_every_field_package_reads_from_the_cells_record
    preserves: true
    wrong_versions:
      - The review checks run for a `READY_FOR_REVIEW` task too, so its errored lens refuses it.
  - claim: >-
      `ready_task` still refuses a task in every state other than
      `READY_FOR_REVIEW` and `ORPHANED`, with a reason naming the state.
    witness: tests/test_task.py::test_ready_task_refuses_with_a_reason_and_writes_nothing
    preserves: true
    wrong_versions:
      - Every state reaches the record checks.
  - claim: >-
      When `run_one_cell` raises an `Exception` and `ready_task` then
      admits the spec's newest task, `run_task` prints one line holding
      `ORPHANED` and `saffron package <spec id>`. It marks the same
      exception with `mark_raised_in_package` and re-raises it. When
      `ready_task` refuses, or itself raises, `run_task` prints no such line,
      and the cell's own exception re-raises unmarked. The witness drives a
      `CellRuntimeError` and a `RuntimeError` past an admitted task, a
      `CellRuntimeError` past a task with no `REVIEWING` turn, and a
      `CellRuntimeError` while `ready_task` raises `GitError`. No live row
      is written in any of them.
    witness: tests/test_task.py::test_a_raising_cell_whose_orphaned_task_is_green_names_saffron_package
    wrong_versions:
      - The line is printed and the exception is left unmarked.
      - The exception is marked and no line is printed.
      - Every raise names `saffron package`, whatever `ready_task` answers.
      - A raise from `ready_task` replaces the cell's own exception.
      - Only a `CellRuntimeError` is checked.
      - The check runs only when a live row was written.
---

## Context

Backlog item b-f582ee, left `partial` by `SA-0232` and `SA-0369`. Its done
line has a half still open. A task that ends after a green cell keeps its
patch where a later command can package it, and says which command does.
`SA-0369` keeps the patch: a cell the runtime cannot exec in now has its
patch read from its worktree volume. `SA-0362` (the spec loop's run 59) went
green, finished REBUT and ended `ORPHANED` at $31.46. #1127 rebuilt it by
hand, and no task owns that pull request.

**An `ORPHANED` raise leaves the patch on disk.** `_drive_cell` stamps
`ORPHANED` in its `except BaseException` and re-raises
(`saffron/cell/session.py:4046-4053`). Its `finally` then exports the
patch when the container was created (`saffron/cell/session.py:4077-4088`).
So `patch.diff` and `patch.json` sit in the task directory beside
`findings.json` and `rebuttal.json` when those phases ran.

**`saffron package` refuses every `ORPHANED` task.** `_package` calls
`package_ready_task` and prints a refusal's reason
(`saffron/cli.py:3312-3341`). `package_ready_task` returns `ready_task`'s
refusal untouched (`saffron/task.py:1451-1480`). `ready_task` refuses
any state but `READY_FOR_REVIEW` (`saffron/task.py:1326-1329`). It then
needs `baseline.json`, and `patch.diff`, `patch.json` and
`findings.json` no older than it (`saffron/task.py:1335-1348`). It reads
this cell's turns as those at or after `baseline.json`'s mtime
(`saffron/task.py:1357-1359`). It rebuilds `reviews` from `findings.json`
(`saffron/task.py:1377-1385`) and `rebut_result` from a fresh
`rebuttal.json` (`saffron/task.py:1391`). The outcome it builds always
reads `READY_FOR_REVIEW` (`saffron/task.py:1431-1433`).

**A `REVIEWING` turn is the ledger's record that a suite went green.**
`repair_loop` returns `READY_FOR_REVIEW` only on a `green` decision
(`saffron/cell/session.py:889-890`). `_drive_cell` sets `REVIEWING` only on
that outcome (`saffron/cell/session.py:3230-3231`), and no other line in
`saffron/` writes it. Every agent turn opens an `attempts` row through
`record_attempts` (`saffron/cell/session.py:283-305`,
`saffron/cell/session.py:2585-2586`). Its phase defaults to the task's
state (`saffron/ledger.py:1601-1623`). REVIEW's lens sessions run through
that `agent` (`saffron/cell/session.py:3409-3428`). So a `REVIEWING` row
exists only after a green suite.

**A passing gate row is not that record.** `gate_results` keeps each
gate's failures after baseline subtraction. No column says the gate was
advisory (`saffron/ledger.py:189-205`, `saffron/ledger.py:2294-2295`).
`terms` is declared `blocking: false` (`.saffron/policy.yaml:29`), and
`size` is advisory at `standard` (§5.6). A green suite can carry either
failure.

**A REVIEW its pool cut leaves its mark in three records.** A lens the
pool cannot cover is filed as an errored `LensReview`
(`saffron/phases/review.py:425`). A criterion probe or a wrong-version
session is filed as an entry whose `error` is `_review_pool_cut`'s text
(`saffron/phases/review.py:576-581`, `saffron/phases/review.py:795-801`).
That text begins `REVIEW's pool held ` and ends `— <witness> never
started` (`saffron/phases/review.py:386-393`). `pool.cut` then ends a live
cell `REVIEW_INCOMPLETE` (`saffron/cell/session.py:3591`,
`saffron/phases/review.py:1084-1088`). Neither probe file records
`pool.cut` itself.

**`anchored_blockers` takes a host-filed survivor unanchored.** A blocker
whose claim begins `HOST_FILED` is selected whatever its anchor
(`saffron/phases/review.py:975-990`).

**The review's verdict lives in two records.** `findings.json` is written
at REVIEW's end (`saffron/cell/session.py:3576-3578`), and
`review.review_state` reads the task's state from it
(`saffron/phases/review.py:1071-1098`, `saffron/cell/session.py:3591`). A
blocker routes to REBUT. REBUT writes `rebuttal.json`
(`saffron/cell/session.py:3906-3908`), and the task's outcome becomes that
result's state (`saffron/cell/session.py:3949`). The one override is a
pool cut, which needs the state `REBUTTAL_UNJUDGED`
(`saffron/cell/session.py:3883`, `saffron/cell/session.py:3964-3966`).

**The `ORPHANED` raise names no command.** `run_task`'s `except
BaseException` around `run_one_cell` writes an `ORPHANED` live row when an
earlier one landed, then re-raises (`saffron/task.py:960-981`). `saffron
cell` then prints `saffron: <type>: <message>` and exits 2
(`saffron/cli.py:455-462`). A batch prints a `raised` line. For an
exception `raised_in_package` marks, it adds an `unpackaged` line naming
`saffron package <spec id>` (`saffron/batch.py:342-352`). It never offers
that spec again that night (`saffron/batch.py:353-356`). The stack
batch's order counts it as missed (`saffron/batch.py:950-958`), and the
batch closes `INFRASTRUCTURE` (`saffron/batch.py:1105-1106`). An unmarked
`CellRuntimeError` in a stack batch is offered again at once
(`saffron/batch.py:353-356`). Its cell rewrites `baseline.json`
(`saffron/cell/session.py:2508`), which makes the green patch stale to
`ready_task`.

**The mark exists.** `mark_raised_in_package` sets it on the exception
object (`saffron/task.py:627-635`). `run_task` marks a raise from its own
PACKAGE for a `READY_FOR_REVIEW` cell (`saffron/task.py:1011-1030`).

**What PACKAGE does with the admitted task.** `package_phase.package`
re-verifies the patch. It writes the task's state through
`set_task_package` (`saffron/phases/package.py:1052`). So a packaged
`ORPHANED` row leaves that state.

## Problem

- **Green, reviewed work is stranded.** An `ORPHANED` task can hold an
  exported patch, a review and a rebuttal. No command packages it, and
  `saffron adopt` refuses it too (`saffron/cli.py:3133-3135`,
  `saffron/cli.py:3217-3221`).
- **The way out is unnamed.** The line a raising cell prints sends the
  operator nowhere. In a stack batch a new cell starts on the same spec
  at once, and that cell stales the patch.

## Out of scope

**A runtime death read as `EXHAUSTED`** (b-f582ee, the spec loop's run
61). That task already reaches PACKAGE in its exhausted mode.

**A task orphaned before REVIEW wrote `findings.json`.** That is
`SA-0161`'s shape. `ready_task` keeps refusing it on the missing file,
since packaging it opens a pull request no lens read.

**A task whose newest row is not this cell's.** A cell that raises
before `create_task` leaves an older task newest. `ready_task` then
judges that older task, and the line names `saffron package` only when
the older task is admitted too. With `repo_id` `None`, as on a repo's
first cell, `ready_task` refuses and nothing is named.

**The double line in a batch log.** A batch prints `run_task`'s line,
then its own `unpackaged` line for the same marked raise. Both name
`saffron package <spec id>`.

**A later scan.** `ORPHANED` is in `REQUEUE_STATES`
(`saffron/scheduler.py:156-165`), so a later batch starts a new cell on
the spec. That cell writes the same task directory, `<batch tree>/<spec
id>` (`saffron/cell/session.py:2321`), and stales the patch. Package it
before the next batch.

**`saffron adopt`.** It still refuses an `ORPHANED` task.

**An interrupt.** A `KeyboardInterrupt` or SIGTERM is not an
`Exception`, and `run_task` asks nothing for it.

**The mark's name.** `mark_raised_in_package` keeps its name. Its
docstring widens instead.

## Notes for the agent

**This change is new behaviour.** No criterion has a mutant on the ref.
Each new witness reads a rebuild, a refusal or a line the base never
produces. Expect `witness` to report `skip` for criteria 1, 2, 3 and 6.

**Where `ready_task` changes.** Admit `ORPHANED` beside `READY_FOR_REVIEW`
at the state check. Keep the state named in the refusal for every other
state. Check the `REVIEWING` turn right after `this_cells` is built, so
the cutoff decides it. Check the review once `reviews` and `rebut_result`
exist. Read the two probe files only when fresh, by the rebuild's own
`_fresh`, and match an entry's `error` on both ends of
`_review_pool_cut`'s text. Import `review_state` from
`saffron.phases.review`. A `READY_FOR_REVIEW` task skips every new check. Update the docstring's
refusal list, and keep it within ten lines.

**Where `run_task` changes.** In the `except` around `run_one_cell`, after
the live row, and only for an `Exception`. Call `ready_task` with the
spec's id, `repo`, `repo_id`, `ledger`, `out_dir` and `base.mirror`.
Catch any `Exception` it raises and name nothing, so the cell's own
exception still reaches the caller. On a `ReadyTask`, print the line,
then call `mark_raised_in_package`. The success line at
`saffron/task.py:1032` and the batch's line at `saffron/batch.py:349-352`
show the shape. Widen `mark_raised_in_package`'s docstring to name this
second case.

**Criterion 4 is narrowed.** Its existing witness reaches the errored
lens and never a blocker, so the claim names only the lens. Criterion 3
drives the other checks against a `READY_FOR_REVIEW` row.

**`saffron/batch.py` is in `touches` for two docstrings only.** No batch
behaviour changes, and `tests/test_batch.py` stays forbidden.

**Sentences that become false.** Correct each, keeping its length:

- `CLAUDE.md:65` and `CLAUDE.md:160-161` describe `saffron package` as
  for a task whose PACKAGE raised.
- `saffron/task.py:1142-1143`, the `ReadyTask` docstring, says the same.
- `saffron/task.py:628-634`, `mark_raised_in_package`'s docstring, names
  one marked case.
- `saffron/batch.py:29-32`, the module docstring, and
  `saffron/batch.py:445-447`, `_is_layer`'s docstring, give the mark that
  one meaning.
- `tests/test_task.py:2370-2373` says a `run_one_cell` raise reads as
  unmarked. Its case has no task, so say so.

**The existing test that changes.**
`test_ready_task_refuses_with_a_reason_and_writes_nothing` loops over
every state but `READY_FOR_REVIEW` (`tests/test_task.py:3647`). Its
`ORPHANED` task has no files, so it now fails on `baseline.json` with
no state in the reason. Leave `ORPHANED` out of that loop too, since
criteria 2 and 3 drive it. Rename no test, since `census` compares names.

**The witnesses.**

- Build on the `_rt_` helpers (`tests/test_task.py:2760-2867`).
  `_rt_attempt` with `with_gate=True` gives a suite turn a passing gate
  row. Record the spec text with `ledger.record_spec_text`, so
  `_spec_for_task` needs no spec file. Pin every record file's mtime about
  five seconds in the past with `_rt_seed_records(task_dir, when=...)`.
  The cell's turns then fall after the cutoff, and a rebuttal can be
  pinned before or after `baseline.json`. Move an earlier cell's turn
  with `_rt_backdate`.
- Criterion 1: build the rebuild with the row `ORPHANED`, then set
  `READY_FOR_REVIEW` and build it again. Compare the two `ReadyTask`s with
  `==`, and the `tasks` rows before and after with `_rt_tasks_snapshot`.
- Criterion 3: write `rebuttal.json` from `RebutResult.as_dict`, as the
  rebuild test does (`tests/test_task.py:2973-2983`). Build a cut entry's
  `error` with `review._review_pool_cut` over a `ReviewPool` under its
  floor, and a survivor's claim from `review.HOST_FILED`.
- Criterion 6: drive `run_task` as `tests/test_task.py:2504-2523` does.
  The `run_one_cell` double writes the task through the `ledger` it is
  handed, then raises. `upsert_repo` on that empty ledger returns 1, the
  `repo_id` `run_task` is handed. Read the line with `capsys`, and the
  mark with `raised_in_package`. Import `CellRuntimeError` and
  `raised_in_package` inside the test, as `tests/test_task.py:2376-2377`
  does. Stub `task_module.ready_task` to raise for the last case.

**Documents.** Update the `package` subcommand's help
(`saffron/cli.py:247-251`), `README.md`'s sentence before the `saffron
package` example (`README.md:178-179`) and `CLAUDE.md`'s command comment
(`CLAUDE.md:65`). `CONTEXT.md` and `DESIGN.md` are protected. The
operator amends their sentences on `saffron package` and the mark, so
leave them.
