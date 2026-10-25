---
id: SA-0316
title: "A batch whose PACKAGE raised still exits 0, and a stack batch offers that task again"
type: feature
priority: 2
depends_on: [SA-0315]
estimated_lines: 395
estimate_measured: true
touches:
  - saffron/task.py
  - saffron/batch.py
  - tests/test_task.py
  - tests/test_batch.py
  - tests/test_cli.py
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
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/reconcile.py
  - saffron/preflight.py
  - saffron/phases/**
  - saffron/record/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/repos/**
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 36
max_attempts: 3
max_turns: 180
risk: standard
acceptance:
  - claim: >-
      `run_task` marks every exception that escapes it from its
      `package_phase.package` call for a `READY_FOR_REVIEW` cell. It
      re-raises that same object with its type unchanged.
      `saffron.task.raised_in_package(exc)` reads the mark and returns
      `True` for it. The witness drives two such raises, a `PackageError`
      and a `CellRuntimeError`. Six raises escape unmarked, each the same
      object. One is a `CellRuntimeError` from the PACKAGE call in the
      exhausted mode. One is a `CellRuntimeError` from
      `push_unpackaged_work` after the exhausted mode's `package` refused.
      One comes from `run_one_cell`. One comes from the queue-line write
      of a `GATE_ERROR` cell, which reaches no PACKAGE call. The last two
      are a fresh `CellRuntimeError` and a fresh `PackageError`.
    witness: tests/test_task.py::test_a_raise_that_escapes_run_task_from_package_is_marked_and_kept
    wrong_versions:
      - "`run_task` wraps the raise in a new exception type, so the caller no longer sees a `CellRuntimeError`."
      - "Only a `PackageError` is marked, so run 46's `CellRuntimeError` from re-verification reaches the batch unmarked."
      - "The exhausted mode's `except BaseException` branch marks its raise too, so a batch logs a `saffron package` command that refuses an `EXHAUSTED` task."
      - "`raised_in_package` is true for any `PackageError`."
      - "The exhausted mode's push is wrapped in a handler that marks its raise."
      - "Every exception that escapes `run_task` is marked, the cell's own included."
      - "One `except BaseException` around everything after `run_one_cell` returns marks the raise, so a raise from `append_queue_line` is marked too."
      - "The mark is set on the exception's class rather than on the object, so a fresh `CellRuntimeError` reads as marked."
  - claim: >-
      `run_batch` closes its row `INFRASTRUCTURE`, and returns it, once its
      runner raised a marked exception, whatever reason the loop stopped
      on. The loop still runs every later candidate it would have run. The
      log carries a line naming the command `saffron package <spec id>` for
      the spec that raised, and for no other spec. That spec keeps its
      `raised` line beside the command line. A later candidate whose runner
      raised an unmarked `CellRuntimeError` or `PackageError` gets its
      `raised` line and no command line. Two marked raises in a row still
      fire the breaker, so a third candidate never runs. The witness drives each
      of the four reasons the loop can stop on besides the breaker:
      `DRAINED`, `BUDGET`, `UNTIL` and `INCOMPLETE`. The `DRAINED` case
      raises a marked `PackageError` and the other three a marked
      `CellRuntimeError`.
    witness: tests/test_batch.py::test_a_batch_whose_package_raised_closes_infrastructure_whatever_it_stopped_on
    wrong_versions:
      - "`_drive` returns `INFRASTRUCTURE` at the raise, so the candidates after it never run."
      - "The promotion runs only for `DRAINED`, so a batch that stopped on `BUDGET` or `UNTIL` still exits 0."
      - "`INCOMPLETE` outranks the marked raise, so that case closes `INCOMPLETE`."
      - "Only a marked `CellRuntimeError` is promoted, so a marked `PackageError` drains at exit 0."
      - "The log line names `saffron package` with no spec id, or names every spec the batch started."
      - "The command line is emitted beside the `raised` line for every runner raise, marked or not."
      - "The command line replaces the `raised` line for a marked raise."
      - "A marked raise is not counted toward the breaker, so a third candidate runs after two marked raises."
      - "`raised_in_package` is true for any `PackageError`, so a `PackageError` from the stack runner's fetch is named."
      - "The returned reason is promoted but the row is closed with the loop's own reason."
  - claim: >-
      A stack batch treats a marked raise from its runner as a miss. It
      calls the runner once for that spec, refuses each spec whose
      `depends_on` reaches it, and closes its row `INFRASTRUCTURE`. Its end
      review and follow-ups still run, and the log names `saffron package
      <spec id>`. A resumed tail under `saffron finish` runs the runner
      once for a follow-up whose raise is marked, and returns
      `INFRASTRUCTURE`. It still writes nothing to the batch row. The
      witness drives three batches. An order spec raises in one batch. A
      follow-up raises in a second batch whose order all reached
      `READY_FOR_REVIEW`. A follow-up raises in a resumed tail with no
      `sleep` given.
    witness: tests/test_batch.py::test_a_stack_batch_misses_a_spec_whose_package_raised_and_closes_infrastructure
    wrong_versions:
      - "`wrapped` still offers a marked `CellRuntimeError` again, so the order spec runs twice."
      - "`_drive` still takes a marked `CellRuntimeError` back out of `started` with `sleep` set, so the follow-up runs twice."
      - "The reason is promoted before `run_stack_batch` reads it, so the end review's follow-ups never run."
      - "A fresh list of marked raises is kept for the follow-ups' `_drive` call, and only the order's list reaches `_stop`."
      - "The spec's dependents still run, because the miss is never recorded in `missed`."
      - "The resumed tail returns `_promote_in_flight`'s reason alone, so `saffron finish` exits 0 after a marked raise."
  - claim: >-
      `saffron batch` exits 2 and prints `saffron package <spec id>` when
      `run_task` raised a marked exception, and the batch row closes
      `INFRASTRUCTURE`.
    witness: tests/test_cli.py::test_saffron_batch_exits_2_and_names_the_package_command_when_package_raised
    wrong_versions:
      - "The log line goes to a stream `saffron batch` does not print."
  - claim: >-
      An unmarked `CellRuntimeError` from a stack batch's runner is still
      offered again until the breaker fires. A plain batch whose runner
      raises one unmarked still drains.
    witness: tests/test_batch.py::test_a_cell_runtime_failure_is_offered_again_only_until_the_breaker
    preserves: true
  - claim: >-
      An exhausted-mode `PackageError` is still caught inside `run_task`,
      which pushes the branch and raises nothing.
    witness: tests/test_task.py::test_an_exhausted_package_that_opened_nothing_still_pushes_its_work
    preserves: true
---

## Context

Backlog item **b-066901**, under `DESIGN.md` §4.2.1 and §5.7. That item
asks for three things. `SA-0313` has `saffron adopt` record a pushed sha.
`SA-0315` lets `saffron package` take a stack layer cut from a review
commit. This spec takes the last: a batch whose PACKAGE raised exits 2.

In run 46, `SA-0302`'s PACKAGE raised a `CellRuntimeError` during
re-verification, when the container service failed. Batch 43 still exited
0. `_drive` emits only a `raised` line for such a raise
(`saffron/batch.py:301`), and names no command to finish the task.

Every line cited below was read at `af2831e8`. `SA-0313` and `SA-0315`
edit `saffron/task.py`, `tests/test_task.py` and `tests/test_cli.py` before
this spec runs, so find each function and test there by name.

**`run_task` lets a raise from PACKAGE escape.** It calls
`package_phase.package` inside a `try` (`saffron/task.py:657-673`). A
`PackageError` from a `READY_FOR_REVIEW` cell sets the task's state and
re-raises (`:674-681`). In the exhausted mode the same error is swallowed.
The branch is then pushed by `package_phase.push_unpackaged_work`
instead (`:693-708`). Any other
exception, `KeyboardInterrupt` included, re-raises in either mode
(`:684-689`). A raise from `run_one_cell` takes its own path and
re-raises at `:618-644`, before PACKAGE. `PackageError` and
`CellRuntimeError` both subclass `RuntimeError`
(`saffron/phases/package.py:67`, `saffron/cell/runtime.py:35`).

**`_drive` counts the raise as an abort and goes on.** Its
`except Exception` adds one to `consecutive_aborts` and emits a
`raised` line (`saffron/batch.py:286-301`). It then attaches the run to
the batch (`:302`). With `sleep` set, a `CellRuntimeError` is
taken back out of `started`, so it is offered again (`:303-306`). Only
`run_stack_batch` passes `sleep` (`:114-116`, `:893`). After every task it
calls `pending = rescan()` and picks again (`:356-358`).

**A stack batch's `wrapped` records no miss for a `CellRuntimeError`.**
Its runner handler records any other raise as a miss
(`saffron/batch.py:843-850`). That adds the spec to `missed` and removes
it from `remaining`. `resolve_prefix` refuses each
later spec whose `depends_on` reaches a missed one (`:586-596`). For a
follow-up it records no miss at all (`:845-850`). The follow-ups' own
`rescan=lambda: follow_up_candidates` returns that list unchanged (`:934`).

**The row closes on the loop's own reason.** `run_batch` calls `_stop` once
with the reason `_drive` returned (`saffron/batch.py:175`). An unresumed
`run_stack_batch` calls `_drive` for its order, then runs its end review,
then its follow-ups only when the reason is `DRAINED` (`:898-944`). It then
calls `_stop` (`:963`). `_stop` passes the reason through
`_promote_in_flight`, which promotes it to `INCOMPLETE` when a task was
left in flight (`:970-1005`). A raise that escapes either function closes
the row `INFRASTRUCTURE` in its `finally` (`:178-185`, `:965-967`).

**`saffron batch` maps the reason to an exit.** It exits 2 for
`INCOMPLETE` and for `INFRASTRUCTURE`, and 0 for the rest
(`saffron/cli.py:2394-2409`). Both forms reach that mapping.

**`saffron finish` runs a resumed tail.** It calls `run_stack_batch` with
no `sleep` (`saffron/cli.py:2577-2596`), so the default `time.sleep`
applies (`saffron/batch.py:460`). It exits 2 for `INCOMPLETE` and
`INFRASTRUCTURE` (`saffron/cli.py:2600`). The resumed tail returns
`_promote_in_flight`'s reason and closes no row (`saffron/batch.py:959-962`).
Its `stop_reason` is the row's `status` (`saffron/cli.py:2529`). The tail runs
follow-ups only when that reason is `DRAINED` (`saffron/batch.py:921`).

**The tests.**
- `tests/test_task.py`'s `_drive` helper runs `run_task` with
  `run_one_cell` replaced (`:43-118`). `on_cell` writes the task row the
  raise path needs, as `_mint_sy5` does (`:435-446`).
  `test_an_exhausted_package_that_opened_nothing_still_pushes_its_work`
  builds an exhausted-mode outcome in a nested `_exhausted_outcome`, with
  one anchored blocker and `rebut_result=None` (`:2087-2097`).
  A cell that is neither `READY_FOR_REVIEW` nor exhausted-mode reaches no
  PACKAGE call. It calls `push_unpackaged_work` and then
  `append_queue_line` (`saffron/task.py:737-776`).
- `tests/test_batch.py` has `FakeRunner` (`:114`), `FakeClock`,
  `_latest_batch_id`, `_batch_row`, `_ready` and `_candidate`.
  `test_a_task_left_in_flight_outranks_an_ordinary_stop` drives `BUDGET`
  and `UNTIL` behind an in-flight task (`:641-689`). `StackDoubles`
  (`:5158`) offers follow-ups from its `__follow_ups__` row.
  `RaisingStackDoubles` (`:6610`) raises a queued exception per seat and
  spec id. `_resumable_batch` (`:7369`) and `_row_window` (`:7412`) build
  and read a resumable batch.
- `tests/test_cli.py` has `_readiness_passes` (`:5671`),
  `_fake_batch_resolution` (`:5693`) and `_tasks_and_latest_batch_status`.
  `_mint_then_raise` is a `cli.run_task` stub that mints a task and
  raises (`:5791-5795`). It sits in
  `test_a_batch_whose_store_lacks_the_proxy_is_refused_and_mints_no_task_row`.

## Problem

1. **Mark the raise in `run_task`.** Add
   `mark_raised_in_package(exc: BaseException) -> None` and
   `raised_in_package(exc: BaseException) -> bool` to `saffron/task.py`.
   The mark lives on the exception object itself. Mark in both `except`
   branches around the `package_phase.package` call, before each
   `raise`, and only when the cell reached `READY_FOR_REVIEW`. An
   exhausted-mode raise stays unmarked and keeps today's behaviour. Keep `raise` bare, so the same object and traceback escape.
2. **Note it in `_drive`.** `_drive` takes one more list from its caller,
   owned beside `in_flight`. When the runner raised and
   `raised_in_package(exc)` is true, append the spec id. Do not take a
   marked `CellRuntimeError` back out of `started`. Beside the `raised`
   line, which stays as it is, emit one more line naming the spec and the
   command `saffron package <spec id>`. Keep the abort count and the
   orphan attach as they are.
3. **Make it a miss in `wrapped`.** A marked `CellRuntimeError` from the
   runner is recorded in `missed` and removed from `remaining`, as any
   other raise is. An unmarked one keeps today's handling.
4. **Promote at the close of the row.** With that list non-empty, `_stop`
   returns and closes `INFRASTRUCTURE`. `run_batch` and an
   unresumed `run_stack_batch` each pass one list to every `_drive` call
   they make and to `_stop`. `run_stack_batch` still reads `_drive`'s own
   reason to decide its follow-ups. The tasks left in flight are still
   named on the way out. A resumed tail returns `INFRASTRUCTURE` when the
   list is non-empty, and still writes nothing to the row.
5. **Docstrings and comments.** `_is_layer`, `_drive`, `wrapped`'s runner
   handler, `_promote_in_flight` and `_stop` say what a marked raise does.
   The module docstring says `Refused` is imported from `saffron.task` for
   its type alone (`saffron/batch.py:25-26`). Name `raised_in_package`
   there too.

## Out of scope

- An exhausted-mode `PackageError`. It is caught, and
  `package_phase.push_unpackaged_work` pushes the branch
  (`saffron/task.py:674-708`), so it never reaches the batch.
- An exhausted-mode raise that escapes `run_task`. It stays unmarked, so
  a batch handles it as today. `saffron package` refuses a task not in
  `READY_FOR_REVIEW` (`saffron/task.py:911-914`), so naming the command
  for it would send the operator to a refusal.
- `saffron cell`. A PACKAGE raise there still exits 2 through `main` and
  names no `saffron package` command.
- The `_batch` docstring names two causes of `INFRASTRUCTURE`
  (`saffron/cli.py:2110-2114`). A PACKAGE raise is now a third, but
  `cli.py` is forbidden here, so that docstring stays stale.
- `saffron/cli.py`. Its exit mapping already reads the reason.
- `DESIGN.md` §4.2.1, ADR 7 and the `CONTEXT.md` entry for the batch stop
  reason. They change by hand in this spec's own pull request.

## Notes for the agent

No criterion declares a mutant. The change edits existing branches in
both modules, but it rewrites the lines a mutant would pin. Such a mutant
would not match at head, so `witness` reports `skip`. The wrong versions
under each criterion carry that weight. Import `raised_in_package` and `mark_raised_in_package` inside each
witness's body, never at module scope. A module-scope import of a name the
change adds turns the reverted run into a collection error, which `revert`
reads as `skip`.

**Criterion 1's witness.** Drive `run_task` three times with
`package_phase.package` replaced by a function that raises a prepared
exception. Assert `excinfo.value is` that exception and its type is
unchanged. `raised_in_package` is true for the two `READY_FOR_REVIEW`
raises and false for the exhausted one. A `READY_FOR_REVIEW` raise needs
the task row, as `_mint_sy5` writes it. For the exhausted mode, pass
`reviews` with one anchored blocker and `rebut_result=None` through
`_drive`'s `**outcome_fields`. Then let the exhausted mode's `package`
return a refusal and `push_unpackaged_work` raise, and assert that raise
escapes unmarked. Then replace `run_one_cell` with one that raises a
`CellRuntimeError`, and assert that one is unmarked. Drive a `GATE_ERROR`
cell with `append_queue_line` replaced by one that raises a
`CellRuntimeError`, and assert it escapes unmarked. Assert a fresh
`CellRuntimeError` and a fresh `PackageError` are unmarked too.

**Criterion 2's witness.** Build each marked exception with
`mark_raised_in_package`, then hand it to `FakeRunner`. In each case the
first candidate raises and a second candidate follows.
- `DRAINED`: the second returns `READY_FOR_REVIEW`. Assert both ran.
- `BUDGET`: give the second a `budget_usd` above what is left.
- `UNTIL`: a `FakeClock` passes the deadline before the second.
- `INCOMPLETE`: the second returns an in-flight state, such as
  `REVIEWING`.

Assert the returned reason, `_batch_row(...)["status"]`, a line holding
`saffron package <first id>`, and no line holding the second id's command.
In the `DRAINED` case, assert the first spec's `raised` line too. Match
it on its exception type and message, so the command line cannot stand in.
Add two more batches whose first candidate raises marked and whose second
raises unmarked, once a `CellRuntimeError` and once a `PackageError`.
Assert each second spec's `raised` line appears and no command names it.
Add a last batch of three candidates whose first two raise marked. Assert
it returns `INFRASTRUCTURE` and the third never ran.

A `PackageError` reaches the batch from outside PACKAGE too. The stack
runner's `fetch_parent_branch` raises one before any cell
(`saffron/cli.py:797`), and so can the check `_stack_base_alive` builds
(`saffron/cli.py:759-770`). Neither is marked, so neither is named.

**Criterion 3's witness.** Use `RaisingStackDoubles` with marked
`CellRuntimeError`s and `sleep=_fail_sleep`. In the first batch, the order
is three specs: one raises, one depends on it, and one stands alone. A
`__follow_ups__` row offers one follow-up that reaches `READY_FOR_REVIEW`.
Assert the runner saw the raising spec once, the dependent was refused
naming it, and the follow-up ran. Assert the status reads `INFRASTRUCTURE`.
In the second batch, every order spec reaches `READY_FOR_REVIEW`, and the
follow-up raises. Assert the runner saw it once, and the status reads
`INFRASTRUCTURE`. In the third, build a `DRAINED` resume with
`_resumable_batch` and pass no `sleep`. Its one follow-up raises. Assert the
runner saw it once, the return is `INFRASTRUCTURE`, and `_row_window` is
unchanged.

A deferred stack batch whose order saw a marked raise closes its row
`INFRASTRUCTURE`. `saffron finish` then reads that `status` and runs the end
review with no follow-ups. `DESIGN.md` §4.2.1 accepts the same for a row
closed `INCOMPLETE`.

**Criterion 4's witness.** Follow the plain-batch half of
`test_a_batch_whose_store_lacks_the_proxy_is_refused_and_mints_no_task_row`,
with `_readiness_passes` in place of the failing probe. The stub mints a
task, then raises a marked `CellRuntimeError`. Assert `main` returns 2, the
printed output holds `saffron package SY-1`, and the row reads
`INFRASTRUCTURE`. The `--stack` form shares the same exit mapping, and
criterion 3 drives its batch.

Criterion 1's set is every exception the PACKAGE call lets escape for a
`READY_FOR_REVIEW` cell. Its witness drives `PackageError` and
`CellRuntimeError`. A `KeyboardInterrupt` takes the same `except
BaseException` branch and is marked too, but no witness drives it. `_drive` catches only `Exception`,
so a batch never reads that mark.

Criterion 3's witness raises a marked `CellRuntimeError` alone. A marked
`PackageError` is a miss at base already, and its promotion goes through
the same `_stop` that criterion 2 drives with one.

The marked raise still counts toward the breaker, as every raise does
(`saffron/batch.py:298`). Leave that count alone. Criterion 2 drives it.
