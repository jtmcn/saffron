---
id: SA-0199
title: A running task has no row in the morning queue until it ends, and the page never refreshes
type: feature
priority: 2
depends_on: [SA-0198, SA-0197]
estimated_lines: 480
estimate_measured: true
touches:
  - saffron/cell/session.py
  - saffron/task.py
  - saffron/report/index.py
  - saffron/cli.py
  - tests/test_session.py
  - tests/test_task.py
  - tests/test_report.py
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
  - saffron/ledger.py
  - saffron/reconcile.py
  - saffron/batch.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/events.py
  - saffron/replay.py
  - saffron/record/**
  - saffron/repos/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/phases/**
  - saffron/report/pr_body.py
  - saffron/report/stack.py
  - saffron/cell/runtime.py
  - saffron/cell/worktree.py
  - saffron/cell/proxy.py
  - saffron/cell/runtimes/**
  - tests/test_batch.py
  - tests/test_events.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_stack_view.py
  - tests/test_queued_specs.py
budget_usd: 33
max_attempts: 3
max_turns: 200
acceptance:
  - claim: >-
      `run_one_cell` takes a keyword `on_state`, `None` by default, and
      hands it to `_drive_cell`. `_drive_cell` calls it once with
      `IMPLEMENTING`, `REPAIRING`, `REVIEWING` or `REBUTTING` each time it
      writes that state to the ledger, in the order it writes them. The
      witness drives a cell through all four, and a cell that repairs
      twice and hears `REPAIRING` twice. It drives three more cells, and
      `on_state` hears none of their end states: a green cell that ends
      `READY_FOR_REVIEW`, a cell that ends `REBUTTING`, and a cell that
      ends `EXHAUSTED` after one repair turn.
    witness: tests/test_session.py::test_a_cell_reports_each_phase_state_as_it_enters_it
    wrong_versions:
      - "`on_state` is called only at `IMPLEMENTING`."
      - "`on_state` is called at the end state too, so a cell ending `REBUTTING` hears it twice."
      - "`on_state` is called at `READY_FOR_REVIEW` or `EXHAUSTED`."
      - "`on_state` is called from `_phase_start`, so a phase is heard once per progress line."
      - Only the first `REPAIRING` of a task is reported, so a second repair turn is not heard.
  - claim: >-
      `run_task` passes `run_one_cell` an `on_state` that upserts the task's
      row through `append_queue_line` with the state it was given. The row
      holds `repo.name`, the spec's id, the spec's declared `risk`,
      `attempts` 0, `cost_usd_est` `None`, zero concerns, zero sustained
      blockers and unkept fixes, zero lines added and removed, and an
      empty link and note.
      `index.html` names the state as soon as the call returns, and its
      header holds `trailing accept rate`. No row for
      the task exists before the first call. Each later call replaces the
      row, and the task's end replaces it last, leaving one row: the
      early-end row for a task that never packaged, and PACKAGE's row for
      one that did. A row of another spec stays as it was. The witness
      drives `IMPLEMENTING` then `REVIEWING` for a task ending `EXHAUSTED`
      and for one ending `READY_FOR_REVIEW`.
    witness: tests/test_task.py::test_a_running_task_holds_one_queue_row_that_its_end_replaces
    wrong_versions:
      - The row is keyed by the repo's path rather than its name, so the end leaves two rows.
      - The row carries `risk` `standard` whatever the spec declared.
      - "`run_task` writes a row before calling `run_one_cell`, such as `QUEUED`."
      - The row is written to `queue.json` and `index.html` is not rendered again.
      - Only the first state reaches the row.
      - A live write that passes no header, so the page drops the rate until the task ends.
  - claim: >-
      When `run_one_cell` raises after `on_state` wrote a row, `run_task`
      writes that row again with the state `ORPHANED` and every other field
      unchanged, then re-raises the same exception object. The witness
      drives a `RuntimeError` and a `KeyboardInterrupt`. A raise before any
      `on_state` call writes no row and no page, and re-raises that same
      exception object.
    witness: tests/test_task.py::test_a_cell_that_raises_leaves_its_running_row_orphaned
    wrong_versions:
      - The handler catches `Exception` only, so a `KeyboardInterrupt` leaves the row at `REVIEWING`.
      - An `ORPHANED` row is written for a raise before any phase started.
      - The raise is swallowed, or a different exception is raised in its place.
      - The `ORPHANED` row is built with the default `risk`.
  - claim: >-
      `orphan_rows(out_dir, repo, spec_ids)` in `saffron/report/index.py`
      rewrites to `ORPHANED` each row whose repo is `repo`, whose spec id is
      in `spec_ids`, and whose state is `IMPLEMENTING`, `REPAIRING`,
      `REVIEWING` or `REBUTTING`. Each rewritten row keeps its other fields
      and its place in `queue.json`, and every other row stays as it was.
      It then renders `index.html` again with the counted `tasks` and
      `spend` header `append_queue_line` writes. A named spec's row in
      `READY_FOR_REVIEW`, `EXHAUSTED` or `ORPHANED` stays, as does a row of
      another spec or of another repo. When no row changes, it writes
      neither file. With no `queue.json` in `out_dir`, it creates nothing
      there, the lock file included.
    witness: tests/test_report.py::test_orphaning_rewrites_only_a_live_row_of_the_named_specs
    wrong_versions:
      - Every row of a named spec is rewritten whatever its state, so a `READY_FOR_REVIEW` row reads `ORPHANED`.
      - The repo is not compared, so another repo's row of the same spec id reads `ORPHANED`.
      - The rewritten row moves to the end of `queue.json`.
      - The rewritten row is rebuilt with default fields, losing its `risk`, `note` or `cost_usd_est`.
      - Both files are written again when no row changed.
      - The lock is taken before the store is checked, leaving `.queue.lock` in an empty directory.
  - claim: >-
      The page `render_index` returns carries
      `<meta http-equiv="refresh" content="60">` exactly once, before its
      `<title>`. So does every `index.html` that `append_queue_line` writes,
      and every one `orphan_rows` writes, which the fourth criterion's
      witness checks.
    witness: tests/test_report.py::test_the_queue_page_refreshes_itself_every_minute
    wrong_versions:
      - The tag is added by `append_queue_line` alone, so the page `render_index` returns lacks it.
      - The interval is `0`, or any value other than 60.
      - The tag is placed after the table.
  - claim: >-
      `saffron.cell.session.LiveState` names exactly `IMPLEMENTING`,
      `REPAIRING`, `REVIEWING` and `REBUTTING`. Each member is a key of
      `_STATE_RANK` in `saffron/report/index.py` and a member of
      `IN_FLIGHT_STATES` in `saffron/reconcile.py`.
    witness: tests/test_report.py::test_every_live_state_is_ranked_and_in_flight
    wrong_versions:
      - "`LiveState` also names `READY_FOR_REVIEW`, which `_STATE_RANK` does not rank and no scan orphans."
      - "`LiveState` leaves out `REPAIRING`."
  - claim: >-
      `saffron batch` and `saffron batch --stack` each call `orphan_rows`
      once the opening scan's `_resolve_queue` returns with
      `stamp_orphaned=True`, before the night's loop runs. They pass
      `out_dir`, the repo's name, and the spec id of each task the scan's
      `reconciled.orphaned` names. A row of a spec the scan did not stamp
      stays. The page it writes carries `trailing accept rate` in its
      header. The queue page is a rendered convenience, so a failed rewrite
      never stops the night. When `orphan_rows` raises an `Exception`, the
      night prints one line starting `batch: the queue page could not be
      rewritten:` with the error, then runs its loop. The witness drives
      both forms, one stamped task beside one unstamped, and a raising
      `orphan_rows` on the form without `--stack`.
    witness: tests/test_cli.py::test_the_batch_scan_orphans_the_queue_row_of_each_task_it_stamps
    wrong_versions:
      - The rewrite runs only on the form without `--stack`.
      - The rewrite runs after the loop returns, so the loop sees the row at `REVIEWING`.
      - The rewrite names every task in the repo, so the unstamped task's row reads `ORPHANED`.
      - "`orphan_rows` called with no `header`, so the page after the scan has no trailing accept rate."
      - "The raise left to the scan's own `try`, so the night prints `batch: the queue could not be resolved:` and exits 2."
      - The raise left uncaught, so it reaches `main` and prints `saffron:` instead.
  - claim: >-
      A live row's write never stops the cell. When `append_queue_line`
      raises an `Exception` inside `on_state`, the callback prints one line
      naming the spec, the state and the error, and returns. The cell goes
      on, `run_task` returns its outcome, and the end-of-task row is
      written as before. A state whose write failed does not count as
      written, so a cell that raises after only failed writes leaves no
      row. When the `ORPHANED` write raises, the row keeps its last live
      state and `run_task` re-raises the cell's own exception object.
    witness: tests/test_task.py::test_a_failed_live_row_write_never_stops_the_cell
    wrong_versions:
      - The live write is not caught, so its `OSError` escapes `on_state` and orphans a running cell.
      - The written flag is set before the write, so a cell that raises after a failed write gets an `ORPHANED` row.
      - The `ORPHANED` write is not caught, so its `OSError` replaces the cell's exception.
      - The failure is swallowed with no line printed.
---

## Context

Backlog item **b-0703c8**. It cites `DESIGN.md` §5.7 and §6. The operator
decided the change on 2026-10-02 and wrote it into `DESIGN.md` at
`8ca7cba0`, restacked onto `main` as `8294e413`. §5.7 step 4 now reads
"The line replaces the task's live row, the one written as each phase started (§6)". §6 has a new paragraph
headed "**A running task has a live row.**" The row is written as each
phase starts. The end-of-task line replaces it under the same repo and
spec key, and so does the row of a task that ends before PACKAGE. A batch
scan that stamps a task `ORPHANED` rewrites its row to `ORPHANED`. The
page refreshes itself.

**Line numbers.** Every line number below was read at `8ca7cba0`, which is
not on `main`, before `SA-0152`, `SA-0197` and `SA-0198` landed. The cell's
base carries all three, so the lines cited in `task.py`, `index.py`,
`cli.py`, `package.py`, `test_task.py` and `test_cli.py` sit elsewhere in it. Each citation names its function or test
beside the line. Find it by that name.

**Where rows come from today.** Two calls write a batch's row, and both run
once the task is over. Replay's call (`saffron/replay.py:143`) is v0's
and stays as it is. PACKAGE's `_finish` calls `append_queue_line`
(`saffron/phases/package.py:964-995`, the call at `:977`). `run_task`
calls it for a task that never packaged (`saffron/task.py:611-628`).
`append_queue_line` upserts on repo and spec id, then renders
`index.html` from every row under a lock
(`saffron/report/index.py:226-269`). It counts the `tasks` and `spend`
header fields itself (`:257-261`).

**Where phase states come from.** `_drive_cell` writes four of them with
`ledger.set_task_state`: `IMPLEMENTING` (`saffron/cell/session.py:2032`),
`REPAIRING` inside `_repair` (`:2494`), `REVIEWING` (`:2614`) and
`REBUTTING` (`:2918`). It writes the task's end state at `:3048`,
`RATE_LIMITED` at `:3084`, and `ORPHANED` at `:3105`, in the handler that
re-raises whatever escaped the cell. No call writes `GATING` or
`DIAGNOSING`. `run_one_cell` (`:834-875`) is a thin wrapper over
`_drive_cell`. `run_task` is its only caller (`saffron/task.py:567-574`),
which `CLAUDE.md` gates.

**How a state sorts.** `_STATE_RANK` ranks all four phase states at 4,
beside elevated risk (`saffron/report/index.py:47-54`). It ranks
`ORPHANED` at 2, with the states that need the operator (`:38`).
`tests/test_report.py:1984` holds `_STATE_RANK` and `_RANKED_BY_RISK` to
every `RowState`.

**How the scan orphans.** Only when `stamp_orphaned` is true, `reconcile`
stamps `ORPHANED` on every task in a state of `IN_FLIGHT_STATES`
(`saffron/reconcile.py:56-67`). It lists those task ids in
`result.orphaned` (`:191-195`). Only `_batch`'s opening scan passes true
(`saffron/cli.py:1529-1536`), on both forms of `saffron batch`. The
rescan passes false (`:1600-1602`). `_resolve_queue` has no `out_dir`.
`_batch` does, and a raise inside the scan's `try` becomes
`resolution_error` (`:1537-1540`), which prints
`batch: the queue could not be resolved: ...` and exits 2 (`:1655-1661`).
`Ledger.tasks_by_repo` returns each task's `task_id` and `spec_id`
(`saffron/ledger.py:954-969`).

**The page.** `render_index` returns a static page whose second line is
`<meta charset="utf-8">` (`saffron/report/index.py:142-148`). Nothing
reloads it.

## Problem

1. **The cell reports each phase.** Add `LiveState` to
   `saffron/cell/session.py`, a `Literal` of the four phase states.
   `run_one_cell` takes `on_state: Callable[[LiveState], None] | None = None`
   and hands it to `_drive_cell`. Right after each of the four
   `set_task_state` writes above, `_drive_cell` calls `on_state` with that
   state when it is given. No other write calls it. The host reads nothing
   from the cell for this: each call follows a ledger write the host
   already makes.
2. **`run_task` writes the live row.** It passes an `on_state` that calls
   `append_queue_line` with the row the second criterion's claim describes.
   When `run_one_cell` raises after at least one such write succeeded, it
   writes the same row with the state `ORPHANED` and re-raises. Catch
   `BaseException` there, as `_drive_cell`'s own handler does at
   `saffron/cell/session.py:3096-3106`.

   A live row is a convenience and never stops a running cell. `on_state`
   runs inside `_drive_cell`'s `try`, so a raise from it would orphan the
   task. Wrap each live write, the `ORPHANED` one included, in a catch of
   `Exception`. On a failure, print one line naming the spec, the state and
   the error, and return. Record a state as written only after its write
   returns. So the `ORPHANED` write is skipped when no write succeeded, and
   its own failure never replaces the cell's exception. The end-of-task
   row keeps today's behaviour, uncaught.
3. **`orphan_rows`.** Add it to `saffron/report/index.py` with the
   signature the fourth criterion names, plus the keyword `header`
   `append_queue_line` takes. Return early when `queue.json` is absent,
   before taking the lock. Read rows through `_existing_queue_rows`.
   Write through the same code `append_queue_line` writes through, so the
   counted header is computed in one place. Factor that code out of
   `append_queue_line` rather than copying it. Rewrite a row only when its
   state is one of `get_args(LiveState)`, the four states criterion 4
   names. Import `LiveState` from `saffron.cell.session` at module scope.
   The prototype measured no import cycle there.
4. **The refresh.** `render_index` puts
   `<meta http-equiv="refresh" content="60">` on the line after
   `<meta charset="utf-8">`. Sixty seconds, because a phase lasts
   minutes. Each turn's wall bound is at least `TURN_TIMEOUT_S`, 900
   seconds (`saffron/cell/session.py:63`). So the page shows each phase
   start within a minute of its write. A page read in ten seconds is
   seldom reloaded under its reader.
5. **The scan.** The opening `_resolve_queue` call already sits in a `try`
   (`saffron/cli.py:1579-1591`). In its `else` branch, map the task ids in
   `resolved.reconciled.orphaned` to spec ids. Read them from
   `ledger.tasks_by_repo(resolved.repo_id)`. Call `orphan_rows` with
   `out_dir`, `repo.name`, those ids and the header. Give that call its
   own `try`, which catches `Exception`, prints the
   `batch: the queue page could not be rewritten:` line, and goes on. Skip
   the call when no task was stamped or `resolved.repo_id` is `None`. Import `orphan_rows` by name
   into `saffron/cli.py`, so a test can replace `cli.orphan_rows`.

**The header.** `SA-0198`, this spec's parent, makes `run_task`'s
end-of-task call pass `header={"trailing accept rate": ...}`, read with
its `trailing_accept_rate(ledger)`. The live and `ORPHANED` writes in
`run_task` pass the same header inside their catch. Each write reads the
rate again at that moment. A header built once before `run_one_cell` and
reused for the end-of-task write is `SA-0198` criterion 4's wrong version,
and its witness turns red. One cached for the live writes alone passes
both witnesses, so build the header inside each write.
`_batch` builds it the same way and passes it to `orphan_rows`. Otherwise
each live write would drop the field from the page until the task ends.
Criterion 2's witness checks the field on each live write.

## Out of scope

- **A PACKAGE that raises.** `_finish` writes no row then, by design
  (`saffron/phases/package.py:965-967`). The live row stays at its last
  phase, `REVIEWING` or `REBUTTING`, until the spec runs again. The ledger
  holds `READY_FOR_REVIEW` for that task, so neither `ORPHANED` nor any
  other state would be true of the row.
- **`GATING`, `DIAGNOSING` and PACKAGE.** No call writes the first two,
  and PACKAGE has no state. A task in PACKAGE shows its last phase's row
  until `_finish` replaces it.
- **The live row's cost and attempts.** The row carries neither. The end
  row carries both.
- **A failed end-of-task write.** Only live writes are caught. A raise
  from the end-of-task `append_queue_line`, in `run_task` or in
  `_finish`, still reaches `main` as it does today.
- **The header's spend while a spec runs again.** A live row has no cost,
  and it replaces the spec's previous end row. So the counted `spend`
  drops by that row's cost until the task ends. The operator accepted
  this. Sorting under §6 is unaffected.
- **Rows written before this change.** A task that ended before this
  change has no live row, so a scan that stamps it rewrites nothing.
- **The `saffron cell` path.** It runs no scan, so it never stamps a task
  `ORPHANED` and never calls `orphan_rows`.
- **`CONTEXT.md`.** Its **Queue line** entry already covers a live row.
  It was edited by hand in this spec's own pull request.

## Notes for the agent

**Every criterion is new code.** `on_state`, `LiveState`, `orphan_rows`
and the refresh tag do not exist at base, so no text there fixes their
spelling. No criterion declares a mutant, and the `witness` gate reports
`skip` for each.

**Every test you add must fail with this diff's source reverted.** Import
`orphan_rows` and `LiveState` inside the test functions, never at module
scope. Otherwise the reverted run is a collection error, which `revert`
reads as `skip`. At base, `run_one_cell` refuses the keyword `on_state`, and a
fake's `k["on_state"]` is a `KeyError`. So each witness fails on its own
assertion or call.

**Criterion 1's witness.** Add a keyword `on_state=None` to `_drive` in
`tests/test_session.py` (`:1229`) and pass it to `run_one_cell` on the
path that passes `emit` (`:1400-1407`). Drive five cells, each under its
own `tmp_path` subdirectory, with `on_state=heard.append`.

- All four states. Copy the stub and turns of
  `test_the_gate_check_after_the_rebuttal_continues_the_gate_count`
  (`tests/test_session.py:4354-4382`). Expect
  `["IMPLEMENTING", "REPAIRING", "REVIEWING", "REBUTTING"]`.
- Green. `_stub_the_runtime(monkeypatch)` with the turns
  `[_turn(_block(_PLAN)), _turn()]`. Assert the end is
  `READY_FOR_REVIEW` and expect `["IMPLEMENTING", "REVIEWING"]`.
- A `REBUTTING` end. Copy
  `test_a_rebuttal_that_claims_a_fix_and_commits_nothing_stops_at_rebutting`
  (`:3525-3541`). Expect `["IMPLEMENTING", "REVIEWING", "REBUTTING"]`.
- An `EXHAUSTED` end. Suites `([], _results(failing), _results(failing))`
  and turns `[_turn(_block(_PLAN)), _turn(), _turn()]`. Expect
  `["IMPLEMENTING", "REPAIRING"]`.
- Two repairs. Two failures that differ, such as `a.py` and `b.py`, so the
  second attempt is not read as no progress. Suites
  `([], _results(first), _results(second), [])` and turns
  `[_turn(_block(_PLAN)), _turn(), _turn(), _turn()]`. Assert the end is
  `READY_FOR_REVIEW` and expect
  `["IMPLEMENTING", "REPAIRING", "REPAIRING", "REVIEWING"]`.

**Criteria 2 and 3's witnesses.** Call `task_module.run_task` directly,
shaped like `_drive` in `tests/test_task.py:29-95`. Give its `Spec`
`risk="elevated"`, so the row's `risk` is not the default.
Seed the store first with a row of another spec. Replace `run_one_cell`
with a fake that reads `queue.json` on entry, before any call, and again
after each `k["on_state"]` call. Compare each read with the whole list of
row dicts, not one field. The entry read holds only the other spec's row.
After each call, also assert `index.html` holds `<code>STATE</code>` for
that state. For the packaged end, replace `package_phase.package` the way
`test_a_later_package_replaces_the_unpackaged_row_and_keeps_its_link`
(`tests/test_task.py:211-270`) does.

For criterion 3, raise each exception from the fake after one
`on_state("REVIEWING")`, and assert `raised.value is error`. Then, in a
fresh `out_dir`, raise from the fake before any `on_state` call. Assert
the same exception object is raised and neither `queue.json` nor
`index.html` exists there. The task's own `events.jsonl` directory does.

**Criterion 4's witness.** Upsert nine rows with `append_queue_line`, in
this order.

| repo | spec | state | other fields |
|---|---|---|---|
| `r` | `A-1` | `IMPLEMENTING` | risk `elevated`, a note |
| `r` | `A-2` | `REPAIRING` | a cost |
| `r` | `A-3` | `REVIEWING` | |
| `r` | `A-4` | `REBUTTING` | |
| `r` | `A-5` | `READY_FOR_REVIEW` | |
| `r` | `A-6` | `EXHAUSTED` | |
| `r` | `A-7` | `ORPHANED` | |
| `r` | `B-1` | `REVIEWING` | |
| `s` | `A-1` | `REVIEWING` | |

Call `orphan_rows(tmp_path, "r", {"A-1", ..., "A-7"})`. Assert the stored
rows equal the nine in order, with only the first four's state changed.
Assert the page holds five `<code>ORPHANED</code>`, the header fields
`tasks <strong>9</strong>` and `spend <strong>$1.50</strong>` for a cost
of 1.5 on `A-2`, and the refresh tag once. Then overwrite `index.html` with a sentinel,
call it for `{"A-5", "A-6", "A-7"}` and for repo `t`, and assert the
sentinel and `queue.json`'s bytes are unchanged. Last, call it on an
empty directory and assert the directory is still empty.

**Criterion 7's witness.** Build each night the way
`test_the_batch_rescans_through_the_pinned_base_without_stamping_orphans`
(`tests/test_cli.py:3042-3108`) does: `_readiness_passes`, a fake
`_resolve_queue`, and a stubbed `real_remote`. Give each form its own
home. Seed its ledger with `_seed_repo` on `https://github.com/o/r.git`
and two tasks. Seed its `batches/v0` store with a `REVIEWING` row for
each spec under the repo `tmp_path.resolve().name`. After
`monkeypatch.chdir(tmp_path)`, that is the name of the path `--repo`
defaults to (`saffron/cli.py:133`). When told to stamp, the fake
`_resolve_queue` stamps one task `ORPHANED` in the ledger it is handed.
It returns `_fake_batch_resolution` with that `repo_id` and a
`ReconcileResult` naming the task. Replace `run_batch` and
`run_stack_batch` with one fake that calls `readiness_check`, records
the stored states, and returns `DRAINED`. After the scan, assert
`trailing accept rate` in the store's `index.html`. For the raise, replace
`cli.orphan_rows` with a function raising `OSError`. Assert the printed
`batch: the queue page could not be rewritten:` line, that the fake loop
ran, and that no line reads `batch: the queue could not be resolved:`.

**Criterion 8's witness.** Replace `index_report.append_queue_line` with
a wrapper. It raises `OSError` for a row whose state is in a set the test
controls, and calls the real one otherwise. Drive three cases.

- `IMPLEMENTING` fails. The fake calls `on_state("IMPLEMENTING")`, notes
  that it went on, and returns an `EXHAUSTED` outcome. Assert `run_task`
  returns it and the fake went on. The store holds one `EXHAUSTED` row.
  Exactly one printed line holds the spec id, `IMPLEMENTING` and the
  error text.
- `ORPHANED` fails. The fake calls `on_state("REVIEWING")` and raises.
  Assert the same exception object is raised and the store holds the
  `REVIEWING` live row.
- `REVIEWING` fails. The same fake. Assert the same exception object is
  raised and the store holds no row.

**Measured on a prototype, 2026-10-02.** A prototype of this change, cut
from `8ca7cba0`, passed all eight witnesses described above. Each of the
eight failed on an assertion with its source reverted. It passed the rest
of the suite, apart from tests that read this repository's git history,
which the prototype's copy did not carry. `types`, `dead` and `structure`
passed on it. Then 29 of the 34 wrong versions listed then were applied to
it as edits, and each failed its own criterion's witness. The header
clauses of criteria 2 and 7 and criterion 7's go-on-after-a-raise came
later and are unmeasured.

Its source and witnesses measured 1615 tokens under `size_gate`'s counter,
with few docstrings and comments. `estimated_lines` is 480: that figure
plus about 300 tokens for them, over four.

**The prose gate** counts every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense, a hedge or a
sentence over 25 words.

**Commit as each witness passes**, before the full suite runs.
