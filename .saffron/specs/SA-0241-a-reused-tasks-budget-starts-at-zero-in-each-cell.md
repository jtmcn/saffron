---
id: SA-0241
title: A reused task's budget ceiling starts at zero in each cell, so a task can spend its budget once per cell
type: bug
priority: 2
depends_on: [SA-0249]
estimated_lines: 232
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
  - saffron/events.py
  - saffron/ledger.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/cli.py
  - saffron/scheduler.py
  - saffron/follow_up.py
  - saffron/record/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/phases/**
  - saffron/report/**
  - saffron/view/**
  - saffron/cell/runtime.py
  - saffron/cell/worktree.py
  - saffron/cell/proxy.py
  - saffron/cell/runtimes/**
  - tests/test_events.py
  - tests/test_batch.py
  - tests/test_ledger.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 22
max_attempts: 3
max_turns: 120
acceptance:
  - claim: >-
      A cell on a task already on record holds the task's recorded spend plus
      its own against `budget_usd` at every check that decides whether a turn
      starts. Those checks are the one before the implement turn, the one
      before the salvage turn, the one before each repair turn and the one
      before the notes turn. The `Budget` line each stop emits, and the
      `cut_off_no_salvage_room` detail, carry that sum. The outcome's
      `spent_usd` and the `Terminal` event's `spent_usd_est` keep this cell's
      own spend. The witness drives each of the four checks, the first both
      past the budget and at exactly it.
    witness: tests/test_session.py::test_a_carried_tasks_spend_counts_at_every_budget_check
    mutant:
      file: saffron/cell/session.py
      find: "start_spend = ledger.task_spend(task_id)"
      replace: "start_spend = 0.0"
    wrong_versions:
      - The cell's running spend starts at the task's recorded spend, so the outcome reports the task's whole spend as this cell's.
      - Only the check before the implement turn reads the recorded spend, and the salvage, repair and notes checks still read this cell's spend alone.
      - The notes check alone still reads this cell's spend.
      - The comparison is `>` rather than `>=`, so a task at exactly its budget buys the implement turn.
      - The `Budget` event's `value` stays this cell's spend.
      - The `cut_off_no_salvage_room` detail still prints this cell's spend.
  - claim: >-
      A cell on a task whose recorded spend already meets or passes
      `budget_usd` opens no agent turn. It ends `EXHAUSTED` in the outcome and
      the ledger's task row, with `spent_usd` $0.00, no attempt row added and
      its run row `COMPLETE`. It emits one `Budget` line whose `value` is the
      recorded spend. The witness drives a `CHANGES_REQUESTED` task at exactly its budget and one
      past it, and a stack batch's minted task carrying only a spec review's
      spend. A task $0.125 under its budget still runs its plan turn.
    witness: tests/test_session.py::test_a_task_resumed_at_its_ceiling_opens_no_turn
    mutant:
      file: saffron/cell/session.py
      find: "start_spend = ledger.task_spend(task_id)"
      replace: "start_spend = 0.0"
    wrong_versions:
      - The check is `>` rather than `>=`, so a task at exactly its budget runs its plan turn.
      - No check before the plan turn, so the plan turn runs and the check after it stops the task.
      - The outcome reports the recorded spend as its `spent_usd`.
      - The check runs only for a task whose state is `CHANGES_REQUESTED`, so a minted stack task plans.
      - The task stops with no `Budget` line.
      - Any task with a recorded spend is refused, so one under its budget never plans.
  - claim: >-
      The plan, implement, repair and notes turns each carry `budget_usd` less
      the task's recorded spend as their `max_budget_usd`. So a task carrying
      $1.00 at a $5.00 budget gives each of the four the cap a fresh task at
      $4.00 gives it. The witness drives one cell through all four turns.
    witness: tests/test_session.py::test_a_carried_tasks_implementer_turns_are_capped_at_what_the_task_has_left
    mutant:
      file: saffron/cell/session.py
      find: "start_spend = ledger.task_spend(task_id)"
      replace: "start_spend = 0.0"
    wrong_versions:
      - IMPLEMENT's options keep the whole `budget_usd`.
      - The repair and notes turns get options at the whole `budget_usd`, so only the plan and implement turns are capped.
  - claim: >-
      REBUT holds the task's recorded spend plus this cell's against
      `budget_usd` when it decides whether it runs past the budget. A task
      carrying $1.00 at a budget $1.00 higher runs REBUT under the same cap,
      with the same sessions' `max_budget_usd`, as a fresh task. Its `Budget`
      line after REBUT carries that sum and REBUT's own spend. The outcome's
      `spent_usd` and the `TaskOutcome` event keep this cell's own spend. The
      witness drives a REBUT that starts past the budget and one at exactly
      it.
    witness: tests/test_session.py::test_a_carried_tasks_rebut_runs_past_the_budget_as_a_fresh_one_does
    mutant:
      file: saffron/cell/session.py
      find: "start_spend = ledger.task_spend(task_id)"
      replace: "start_spend = 0.0"
    wrong_versions:
      - REBUT's overrun test still reads this cell's spend alone.
      - The `Budget` line after REBUT carries this cell's spend as its `value`.
      - The outcome's `spent_usd` and the `TaskOutcome` event carry the task's whole spend.
---

## Context

Backlog item **b-4acb0e**, found in the spec loop's run 19 on 2026-09-27. It
cites `DESIGN.md` §4.3. Every line number below was read at `958db033`.

**Which cells run on a task already on record.** `CellSpec.task_id` names
one. Only `saffron batch --stack` passes it, as `task_id=candidate.task_id`
(`saffron/cli.py:616`). The plain batch runner passes none
(`saffron/cli.py:563-573`). The queue sets a candidate's `task_id` to the
newest task at its `spec_sha` in a re-queueing state
(`saffron/scheduler.py:910-919`). Those states include `CHANGES_REQUESTED`
(`saffron/scheduler.py:111-119`). A stack batch that reviews its specs
replaces it with the task it minted and recorded the spec review on
(`saffron/batch.py:530-543`, `:588`).

**What the cell reads of that task.** Given a `task_id`, the cell reads the
task's run and its recorded spend, `ledger.task_spend`, into `start_spend`
(`saffron/cell/session.py:1954-1958`). A fresh task sets `start_spend` to 0.0
(`saffron/cell/session.py:1977`). `ledger.task_spend` sums every attempt row
of the task, spec review rows included (`saffron/ledger.py:1428-1438`). Only
the rate-limit path reads `start_spend`. It subtracts it from the task's
spend to report this cell's own (`saffron/cell/session.py:3194`).

**What the budget reads instead.** The cell's running spend starts at 0.0
(`saffron/cell/session.py:1996`). These reads hold it against `budget_usd`.

- `_over_budget` returns `False` while it is under `budget_usd`. At or past
  it, it emits a `Budget` event whose `value` is that spend
  (`saffron/cell/session.py:2280-2295`). Four places call it. The first
  two sit before the implement turn (`:2297`) and the salvage turn
  (`:2364`). `_over_budget` also guards each repair turn (`:2588`) and the
  notes turn (`:2662`).
- The salvage check's `cut_off_no_salvage_room` detail prints that spend
  against `budget_usd` (`saffron/cell/session.py:2366-2375`).
- IMPLEMENT's options carry the whole `budget_usd` as their per-turn cap
  (`saffron/cell/session.py:2089-2094`). The plan turn, the implement turn,
  each repair turn and the notes turn all pass `options=options`
  (`saffron/cell/session.py:2138-2146`, `:2313-2321`, `:2594-2601`,
  `:2664-2671`).
- REBUT's overrun test compares that spend with `budget_usd`
  (`saffron/cell/session.py:3024`). It picks `_RebutCap` past the budget
  (`:3048`). The `Budget` event after a capped REBUT carries that spend
  (`saffron/cell/session.py:3137-3146`).

The first check runs after the plan turn, never before it
(`saffron/cell/session.py:2138`, `:2297`). So a task resumed past its budget
buys at least a plan turn.

**What keeps this cell's own figure.** The outcome's `spent_usd`
(`saffron/cell/session.py:2307`, `:3176`), the `TaskOutcome` event
(`:3165`), each `Attempt` event (`:2346`) and the `Terminal` event's
`spent_usd_est` (`:2370`). `run_task` writes the outcome's figure into the
queue line as `cost_usd_est=outcome.spent_usd` (`saffron/task.py:690`,
`:731`). The ledger records each turn's own cost on its attempt row
(`saffron/cell/session.py:242-266`).

## Problem

A task resumed across cells gets its whole budget again in each cell. In a
stack batch, a `CHANGES_REQUESTED` task that spent $20 of a $22 budget runs
its next cell with $22 to spend. A stack batch's spec review is outside the ceiling.

**The fix.** The item's "Done looks like" says to start the running spend at
the recorded spend. The operator chose to keep the two figures apart on
2026-10-07. Every read that decides whether to spend holds the task's
recorded spend plus this cell's against `budget_usd`. Every figure that
reports a run keeps this cell's own.

1. **The checks.** `_over_budget` compares the sum with `budget_usd`, at
   `>=` as today. Its `Budget` event's `value` is the sum. All four callers
   take it from there.
2. **The salvage detail.** The `cut_off_no_salvage_room` detail prints the
   sum before `of`.
3. **A task already at its ceiling.** Before the plan turn, a cell on a task
   whose recorded spend meets or passes `budget_usd` ends `EXHAUSTED`. It
   opens no agent turn and adds no attempt row. It emits one `Budget` event,
   `ceiling` `budget_usd`, `value` the recorded spend and `limit`
   `budget_usd`, so its line is the base's stopping line. The outcome's
   `spent_usd` is $0.00, and the run row reads `COMPLETE`. The operator
   decided this on 2026-10-07. `EXHAUSTED` is a done state
   (`saffron/scheduler.py:69-83`), so the queue stops offering the spec.
4. **IMPLEMENT's per-turn cap.** IMPLEMENT's options carry `budget_usd` less
   the recorded spend as `max_budget_usd`. It is computed once, from the
   recorded spend at the cell's start, as the options are today.
5. **REBUT's overrun test.** To decide whether it runs past the budget,
   REBUT reads the sum. The `Budget` event after a capped REBUT carries
   the sum as its `value`.
6. **What reports a run.** The outcome's `spent_usd`, the `TaskOutcome`,
   `Attempt` and `Terminal` events' figures and the rate-limit read-back
   keep this cell's own spend, unchanged.

**A fresh task is unchanged.** Its recorded spend is 0.0, so every sum
equals the base's figure.

**With the specs before this one.** `SA-0230` holds a salvage reserve back
from IMPLEMENT's budget, and `SA-0231` gives REBUT a fixed cap of its own.
This spec reads neither's code. The reserve comes out of what the task's
whole budget leaves, the recorded spend included. So IMPLEMENT's per-turn cap
is `budget_usd`, less the recorded spend, less any reserve a parent declares.
Wherever a parent decides whether the salvage turn starts, it reads the sum.
REBUT's own cap keeps its amount and its sharing across sessions. Only the
reading of whether the task is past its budget changes.

## Out of scope

- **REVIEW's and REBUT's per-session remainder.** `critic_budget(spec.budget_usd,
  spent)` sizes each lens session and each REBUT session under the budget
  (`saffron/cell/session.py:2805`, `:3087`). It keeps this cell's spend.
  REVIEW is never stopped for money, and its floor is $2.00
  (`saffron/cell/session.py:74-83`, `:149-151`).
- **The salvage turn's own per-turn cap.** Its options carry the whole
  `budget_usd` (`saffron/cell/session.py:2389-2394`). `SA-0230` owns that
  turn's budget.
- **A batch's budget gate.** It admits a task on the task's declared
  ceiling. A resumed task now spends at most what that ceiling leaves, so the
  gate reserves more than the task can spend. No change to
  `saffron/batch.py`.

## Notes for the agent

**New or edit.** Every criterion edits code the base already has. Each
declares a mutant on the line that reads the recorded spend for a task on
record, which this change keeps. Under it every sum equals this cell's spend
again.

**Each witness compares two cells.** One runs a fresh task at a budget B. The
other runs a task carrying $1.00 at B plus $1.00. The carried cell must do
what the fresh one did. So a parent's change to a fresh cell's figures moves
both cells alike. Use costs that are exact in binary, such as $0.125, $0.5
and $1.0, and compare dollars with `==`.

**Two helpers** go beside `_rebut_capped` (`tests/test_session.py:3965`).

- One files a task on record in the ledger `_drive` opens,
  `Ledger(tmp_path / "ledger.db"` (`tests/test_session.py:1475`). It
  upserts the repo, creates a run and a task for `SY-1` at `spec_sha`
  `"a" * 64`, and closes one attempt costing the carried amount. The phase defaults to `IMPLEMENTING` and the state to
  `CHANGES_REQUESTED`. `test_a_cell_given_a_task_runs_on_it_and_its_run_and_mints_neither`
  builds the same rows (`tests/test_session.py:2497-2524`).
- One runs the fresh cell and then the carried one, each in its own
  directory under `tmp_path`. It returns each outcome, its stubbed cell and
  its `capture` list. It then asserts these hold for the pair.
  - The two states are equal, and so are the two `cell.turns` lists.
  - The two outcomes' `spent_usd` are equal.
  - The carried cell's `Budget` events, as `value`, `limit` and
    `rebut_spent_usd_est`, equal the fresh cell's with $1.00 added to the
    first two. The fresh list is not empty.
  - The two `TaskOutcome` events' `spent_usd_est` lists are equal.

Give `_rebut_capped` a `task_id` keyword that defaults to `None` and reaches
the `CellSpec`.

**Criterion 1's witness** runs the pair helper five times.

- The plan turn costs $0.5, at B $0.25 and at B $0.5. The fresh cell ends
  `EXHAUSTED` after one turn, and the carried outcome's `spent_usd` is $0.5.
- The salvage check. The stub reports no commits. The plan turn costs
  $0.125, and the implement turn is a cut-off turn costing $0.5
  (`_cut_off_turn`, `tests/test_session.py:1253`), at B $0.5. Each cell's
  one `Terminal` event has a detail starting `$0.62 of $0.50` for the fresh
  cell and `$1.62 of $1.50` for the carried one. The two events'
  `spent_usd_est` are equal.
- The repair check. The suites are a green baseline, then red twice. The
  plan turn costs $0.125 and the implement turn $0.5, at B $0.5. The fresh
  cell ends `EXHAUSTED` after two turns.
- The notes check. The spec declares `forbidden: ["config/legacy.py"]`, and
  the suites stay green. The plan turn costs $0.125 and the implement turn
  $0.5, at B $0.5. The fresh cell's turns hold no `artifacts.NOTES_PROMPT`,
  and REVIEW still runs.

`Terminal` is not imported in the test module yet.

**Criterion 2's witness** files each task with the first helper, then
drives one cell on it with a plan turn scripted.

- Carrying $1.0 at a budget of $1.0, state `CHANGES_REQUESTED`.
- Carrying $1.5 at a budget of $1.0, state `CHANGES_REQUESTED`.
- Carrying $1.0 at a budget of $1.0, its one attempt in phase
  `SPEC_REVIEW`, its state left as minted.

Each asserts `EXHAUSTED`, an empty `cell.turns` and `spent_usd` $0.0. The
task keeps one attempt row and a `task_spend` equal to the carried amount.
Its queue line reads `EXHAUSTED`, and its run row reads `COMPLETE`. The
capture holds exactly one `Budget` event, its `value` the carried amount,
its `limit` the budget and its REBUT figure `None`. Its line is the
stopping line `describe` renders. A fourth task carrying $0.875 at a budget
of $1.0 runs at least one turn.

**Criterion 3's witness** runs the pair helper once at B $4.0, with
`forbidden` declared and the suites green, red, then green. The plan,
implement, repair and notes turns each cost $0.125, and the fourth turn is
the notes prompt. The first four entries of each cell's `turn_options` carry
equal `max_budget_usd` values. The lens sessions after them are not
compared, since `critic_budget` keeps this cell's spend.

**Criterion 4's witness** runs `_rebut_capped` with REBUT costs $3.00,
$2.50 and $1.00 twice. Once fresh at B $0.25 and carried at $1.25, and once
fresh at B $0.75 and carried at $1.75. REBUT starts at $0.75 of this cell's
spend in both. The fresh REBUT sessions' `max_budget_usd` values are $7.00,
$4.00 and $1.50 (`_rebut_turn_options`, `tests/test_session.py:3952`), and
the carried ones equal them. The pair assertions above hold, and the carried
outcome's `spent_usd` is $7.25. Where a parent moves REBUT's cap or its
line, assert the carried cell against the fresh one rather than against
these figures.

**Wrong versions.** On 2026-10-07 every version listed under the criteria
was applied to a prototype of this change. Its witness failed each one, and
each witness failed with the source reverted to the base. The four mutants
each killed their witness.

**The `prose` gate** reads every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence over
25 words.

**Size.** `saffron/cell/**` is in `elevate_on`, so `size` blocks here. The
prototype with all four witnesses, counted by `size_gate`, came to 928
tokens against the `bug` ceiling of 1300. `estimated_lines` is those tokens
over four.
