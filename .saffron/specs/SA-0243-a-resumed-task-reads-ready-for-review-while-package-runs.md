---
id: SA-0243
title: A resumed task's row reads READY_FOR_REVIEW while PACKAGE runs, so a reconcile can hand its live cell back out
type: bug
priority: 2
depends_on: [SA-0242]
estimated_lines: 220
estimate_measured: true
touches:
  - saffron/cell/session.py
  - saffron/task.py
  - saffron/ledger.py
  - saffron/reconcile.py
  - tests/test_session.py
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
  - saffron/cli.py
  - saffron/batch.py
  - saffron/scheduler.py
  - saffron/events.py
  - saffron/report/**
  - saffron/record/**
  - saffron/view/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/phases/**
  - saffron/cell/runtime.py
  - saffron/cell/worktree.py
  - saffron/cell/proxy.py
  - saffron/cell/runtimes/**
  - tests/test_cli.py
  - tests/test_reconcile.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 20
max_attempts: 3
max_turns: 120
acceptance:
  - claim: >-
      A cell that ends `READY_FOR_REVIEW` after a REVIEW with no blocker
      leaves its task row `REVIEWING`. One that ends it after a REBUT whose
      verdict withdrew the blocker, or confirmed it, leaves the row
      `REBUTTING`. So `saffron reconcile`, run after the cell returns and
      before PACKAGE, leaves a resumed task's row where it was, though its
      previous pull request reads `CHANGES_REQUESTED`. The witness drives all
      three paths on a resumed task and runs `saffron reconcile` through
      `cli.main` after each.
    witness: tests/test_session.py::test_a_cell_bound_for_package_leaves_no_row_a_reconcile_can_requeue
    mutant:
      file: saffron/cell/session.py
      find: 'ledger.set_task_state(task_id, "REVIEWING")'
      replace: 'ledger.set_task_state(task_id, "READY_FOR_REVIEW")'
    wrong_versions:
      - The cell's own last write kept, so `saffron reconcile` moves the row to `CHANGES_REQUESTED`.
      - A row written `REVIEWING` on every path, so a REBUT path's row names a phase that ended before REBUT began.
      - A row written some other state outside `PR_PENDING_STATES`, such as `GATING`, which names no phase the cell reached last.
      - The row left as it is but a guard added to `reconcile` instead, which the backlog item rules out and which leaves the row reading `READY_FOR_REVIEW`.
  - claim: >-
      For a cell that ends `READY_FOR_REVIEW`, `run_task` lets the row settle
      only once PACKAGE ends, and PACKAGE sees the row still in flight. A
      PACKAGE that returns leaves the state it wrote, `READY_FOR_REVIEW` or
      `MERGE_FAILED`. A PACKAGE that raises, whether a `PackageError` or
      another exception, leaves `READY_FOR_REVIEW`, and its own exception
      propagates. In all four the row's spend sums every attempt the task
      closed. A cell that ends `EXHAUSTED` with a standing blocker and no
      rebuttal result keeps the `EXHAUSTED` row its cell wrote. That holds
      whether PACKAGE returns or raises a `PackageError`. The witness drives
      all six cases.
    witness: tests/test_task.py::test_a_task_bound_for_package_reads_its_state_only_once_package_ends
    wrong_versions:
      - '`READY_FOR_REVIEW` written in `run_task` just before PACKAGE is called, which reopens the window.'
      - '`READY_FOR_REVIEW` written after every PACKAGE that returns, which overwrites `MERGE_FAILED`.'
      - '`READY_FOR_REVIEW` written only when PACKAGE raises a `PackageError`, so another exception leaves the row `REVIEWING`.'
      - '`READY_FOR_REVIEW` written when PACKAGE raises with `exhausted` set, which overwrites the `EXHAUSTED` row.'
      - Nothing rolling the spend up after the cell, so a row that PACKAGE settled misses the attempts closed after its last in-flight write.
      - A write on the raise path that itself raises, so a different exception replaces PACKAGE's own.
  - claim: >-
      A cell whose REBUT the cap cut short still ends with its row reading
      `EXHAUSTED`.
    witness: tests/test_session.py::test_a_rebut_the_cap_cut_short_ends_exhausted_with_its_blockers_standing
    preserves: true
    wrong_versions:
      - The cell's last state write dropped for every outcome rather than for `READY_FOR_REVIEW` alone, so this row reads `REBUTTING`.
---

## Context

Backlog item **b-dce9a4**, which reopens the window backlog item 29 left
for `SA-0020`. It cites `DESIGN.md` §3.3, §4.2, §4.2.1 and §5.7. Every
line number below was read at `958db033`.

**How a cell ends today.** After REVIEW and REBUT, `_drive_cell` emits the
task's outcome event. It then writes that outcome onto the task row and
finishes the run `COMPLETE` (`saffron/cell/session.py:3159-3170`). The
outcome reaches `READY_FOR_REVIEW` two ways. REVIEW with no blocker
returns it (`saffron/phases/review.py:875`, read at
`saffron/cell/session.py:3010`). REBUT returns it when its verdicts
contradict, confirm or withdraw the blockers (`saffron/phases/rebut.py:532-546`,
read at `saffron/cell/session.py:3134`). Before either, the row was given
`REVIEWING` (`saffron/cell/session.py:2711-2712`). REBUT gives it
`REBUTTING` first (`saffron/cell/session.py:3017-3018`).

**PACKAGE runs after the cell returns.** `run_task` calls `run_one_cell`
(`saffron/task.py:602`). It packages a `READY_FOR_REVIEW` outcome, and an
`EXHAUSTED` one with an anchored blocker and no rebuttal result
(`saffron/task.py:630-638`). `package()` writes its state with the new
`pr_url` through `_finish` (`saffron/phases/package.py:997-1006`). A
`PackageError` with `exhausted` unset propagates to the caller
(`saffron/task.py:654-658`). `saffron cell` and `saffron batch` both arrive
through `run_task`.

**What `reconcile` reads.** It skips a row with no `pr_url` or a state
outside `PR_PENDING_STATES` (`saffron/reconcile.py:49`, `:166-169`).
`READY_FOR_REVIEW` is in that set. A resumed task still carries its previous
attempt's `pr_url` through its next cell. So in the window above, a row
reads `READY_FOR_REVIEW` beside an old pull request whose review decision
is `CHANGES_REQUESTED`. The loop then calls `set_task_state` with that
state (`saffron/reconcile.py:188`). `CHANGES_REQUESTED` is in
`scheduler.REQUEUE_STATES` (`saffron/scheduler.py:111-120`), so the scan
offers the live task again. The command's own call passes `gh` alone
(`saffron/cli.py:1912`). `saffron queue` and a batch's rescans pass
`stamp_orphaned=False` (`saffron/cli.py:1885`, `:1715`).

**Where the spend is rolled up.** A `task_state` fact sets the row's
`spent_usd_est` from its closed attempts (`saffron/ledger.py:768-775`). A
`task_package` fact sets the state, branch, sha, `pr_url` and diff stat,
and leaves the spend alone (`saffron/ledger.py:776-790`). Today the cell's
last write rolls up REVIEW's and REBUT's attempts before PACKAGE's write
lands. `set_task_state`'s docstring says every terminal path calls it
(`saffron/ledger.py:1364-1367`).

**Item 29's witness.** `test_an_in_flight_task_survives_being_looked_at`
seeds a row and runs `queue` and `reconcile` through `cli.main`
(`tests/test_cli.py:2290-2308`). The witness below runs `reconcile` that
way.

## Problem

Order the state write so the row leaves `PR_PENDING_STATES` before PACKAGE
is called. Make these changes.

1. If the outcome is `READY_FOR_REVIEW`, the cell skips its last
   `set_task_state` (`saffron/cell/session.py:3169`). The row keeps
   `REVIEWING` or `REBUTTING`. Every other outcome keeps its write there,
   `EXHAUSTED` included. Keep the outcome event, the `COMPLETE` run row
   and the returned `CellOutcome` exactly as they are.
2. If `package()` raises with `exhausted` unset, `run_task` writes
   `READY_FOR_REVIEW` onto the row and re-raises the same exception. That
   covers a `PackageError` and any other exception. With `exhausted` set,
   write nothing, as today. This keeps the row PACKAGE's raise leaves
   today.
3. **The spend.** Make the `task_package` fact roll the spend up from the
   closed attempts, as `task_state` does. The returning path then needs no
   second write in `run_task`. Update `set_task_package`'s docstring to say
   so, and the last clause of `set_task_state`'s, which stops being true.
4. **The stale docstring.** Rewrite `saffron/reconcile.py`'s paragraph on
   the live task (`:15-27`). Say that a first run carries no `pr_url`, and
   that a cell bound for PACKAGE leaves its row in flight until PACKAGE
   ends. Cite backlog item b-dce9a4. Drop the item 29 and `SA-0020`
   references. Keep the point that a wider state guard here does not close
   it.
5. **Tests your change breaks.** Three tests read the old order. The first
   is `test_a_cell_given_a_task_runs_on_it_and_its_run_and_mints_neither`
   (`tests/test_session.py:2486`). Its last lines compare each row with its
   outcome (`:2602-2606`). Its two cells end `READY_FOR_REVIEW`, so their rows now read
   `REVIEWING`. Two tests in `tests/test_task.py` hand `run_task` a
   `READY_FOR_REVIEW` outcome whose task id their ledger never created, and
   make PACKAGE raise (`tests/test_task.py:365-374`, `:2052-2078`). The
   raise path's write needs that row, so create it in their ledgers.

## Out of scope

- **A corpse-stamping scan.** A batch's opening scan passes
  `stamp_orphaned=True` (`saffron/cli.py:1628`). It stamps any in-flight row
  `ORPHANED` (`saffron/reconcile.py:191-195`), and that state is in
  `REQUEUE_STATES`. Its premise is that one batch runs at a time
  (§4.2.1), so no cell is live when it runs. A second process that breaks
  the premise reaches a cell in IMPLEMENT the same way. This spec moves the
  PACKAGE window into that existing exposure and does not close it.
- **The queue's view of the window.** An in-flight row is neither done nor
  requeued (`saffron/scheduler.py:905-911`). So during PACKAGE the scan
  offers the spec with a fresh task, as it does during every earlier phase.
  Today a first run's `READY_FOR_REVIEW` row hides it.
- **The other commands that reconcile.** `saffron queue` and a batch's
  rescans call the same function without stamping. The stacking resolver
  calls `reconcile` with a `spec_id` (`saffron/task.py:255`). The witness
  drives `saffron reconcile` alone.
- **Other outcomes at the cell's last write.** They keep that write
  unchanged. Criterion 3 drives the `EXHAUSTED` a capped REBUT leaves,
  which PACKAGE sees. `GATE_ERROR`, a `REVIEWING` outcome from an errored
  lens and an `EXHAUSTED` that PACKAGE never sees go undriven.
- **A REBUT whose verdicts contradict each other.** It also ends
  `READY_FOR_REVIEW` and reaches the same skipped write. Criterion 1 drives
  the withdrawn and confirmed paths, and leaves this one undriven.
- **A raise from `_finish` after its ledger write.** The raise path then
  rewrites a `MERGE_FAILED` row to `READY_FOR_REVIEW`. That needs the queue
  line's own write to fail after the fact landed.

## Notes for the agent

**Your base.** This spec stacks on `SA-0242`, which follows other specs that
edit `saffron/cell/session.py` near the REBUT cap, the teardown and the
gate events. Read the file at your base before you edit it. Your edit in
it is one line at the end of the main path.

**Edit or new.** Criterion 1's mutant turns the `REVIEWING` write into
`READY_FOR_REVIEW`, which reopens the window on the REVIEW path. That line
exists at your base and your change leaves it alone. Criterion 2 is new
code in `run_task` and the ledger fold, so it declares a witness and no
mutant. Criterion 3 is `preserves`, an existing test.

**Criterion 1's witness.** Seed a resumed task in a ledger at
`<case>/ledger.db`. Call `set_task_package` with a `pr_url`, then set it
`CHANGES_REQUESTED`. Drive it with the module's `_drive` and
`_spec(task_id=...)`. The REVIEW path scripts `_turn(_block(_PLAN))` and
`_turn()`. The two REBUT paths use `_rebuttable` with `rebut_commits=1`
and `_through_rebut`, as
`test_a_verdict_lands_on_the_finding_the_review_recorded` does. One ends
in a verdict that withdraws finding 1, and the other in one that confirms
it. Close the
ledger, then run `cli.main(["--home", <case>, "reconcile", "--repo",
<case>])`. Monkeypatch `saffron.cli.run_gh` to answer `OPEN` with
`CHANGES_REQUESTED`, and `saffron.cli.package_phase.real_remote` to return
the seeded URL. Assert the outcome is `READY_FOR_REVIEW` and the row reads
`REVIEWING` or `REBUTTING`, outside `PR_PENDING_STATES` and
`REQUEUE_STATES`.

**Criterion 2's witness.** Seed a task in its own ledger per case, with two
closed attempts whose last close follows the last `set_task_state`. Replace
`run_one_cell` and `package_phase.package` at module scope. The `package`
double records the row's state when called. A returning double calls
`ledger.set_task_package`, as `_finish` does. Pass a `Handoff` of two
`None`s so no stacking resolver runs. For the two `EXHAUSTED` cases, give
the outcome an anchored blocker in `reviews` and set the row `EXHAUSTED`
before `run_task`. Replace `push_unpackaged_work` as `_push` does. Catch
with `pytest.raises(BaseException)` and assert the caught exception is the
same object PACKAGE raised, so a substitute fails an assertion. Read the
spend with `ledger.queue_lines()`, since `tasks_by_repo` does not carry it.

**The two broken tests in `tests/test_task.py`.** `_drive`'s `on_cell` is
typed to return `None` (`tests/test_task.py:43`). A lambda that returns a
new task id fails `types`, so mint the row in a function that returns
nothing.

**Witnesses red at base.** Criterion 1's fails at base with the row at
`CHANGES_REQUESTED`. Criterion 2's fails at base on the spend and on the
raise path's state. Neither imports a name your change adds.

**Measured on a prototype, 2026-10-07.** Both new witnesses were written
against `958db033` with the change above, and passed. Each failed with
the source reverted. Each wrong version above was applied and failed its
own witness. The mutant failed criterion 1's witness, and so did the same
edit to the `REBUTTING` write. The six test modules that read these files
passed whole with the change.

**The `prose` gate** reads every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence over
25 words. Keep each docstring within ten lines.

**Size.** `saffron/cell/**` and `saffron/ledger.py` are in `elevate_on`, so
`size` blocks. The prototype counted about 870 changed tokens by `size_gate`,
against the `bug` ceiling of 1300. Keep comments to one or two lines, and
put the two new witnesses' cases in loops, as the shapes above do.
