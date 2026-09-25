---
id: SA-0168
title: A stack batch's cell mints a second task beside the one its spec review is recorded on
type: feature
priority: 1
depends_on: [SA-0155]
touches:
  - saffron/cell/session.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/phases/package.py
  - tests/test_session.py
  - tests/test_task.py
  - tests/test_cli.py
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
  - saffron/batch.py
  - saffron/spec_review.py
  - saffron/end_review.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/events.py
  - saffron/reconcile.py
  - saffron/record/**
  - saffron/report/**
  - saffron/repos/**
  - saffron/cell/runtime.py
  - saffron/cell/runtimes/**
  - saffron/cell/worktree.py
  - saffron/cell/proxy.py
  - saffron/gates/**
  - saffron/phases/implement.py
  - saffron/phases/review.py
  - saffron/phases/rebut.py
  - saffron/agents/**
  - tests/test_batch.py
  - tests/test_spec_review.py
  - tests/test_end_review.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_ledger_fold_task.py
  - tests/test_review.py
budget_usd: 25
max_attempts: 3
max_turns: 180
acceptance:
  - claim: >-
      Given a `CellSpec` whose `task_id` is set, `run_one_cell` creates no
      run and no task. Its attempts and state go on that task, and its
      outcome carries that task and the task's run. After it loads the
      exported policy, it calls `Ledger.record_policy` only where the
      task's `policy_sha` differs, a task with another recorded policy
      included. A `task_id` that names no task raises `ValueError` before
      any cell comes up. A `RATE_LIMITED` outcome's `spent_usd`, and its
      `TaskOutcome` event's `spent_usd_est`, are `Ledger.task_spend` at the
      rate limit less `task_spend` when the cell took the task. So they
      count every attempt this cell opened, and no earlier one. With
      `task_id` unset, the cell mints its own run and task. The witness
      drives a minted task holding a `SPEC_REVIEW` attempt, walled at its
      plan turn, then walled at its implement turn after a plan turn with a
      cost, then run. It also drives a task on an older run with another
      policy, a missing task, and no task.
    witness: tests/test_session.py::test_a_cell_given_a_task_runs_on_it_and_its_run_and_mints_neither
  - claim: >-
      The re-queue cap finds an earlier cut at the cell's task row's
      `spec_sha`, not at `CellSpec.spec_sha`. An attempt in phase
      `SPEC_REVIEW` or `SPEC_WRITING` disqualifies no earlier task, and one
      in any other phase but `IMPLEMENTING` still does. The witness drives a
      revised spec, whose `CellSpec.spec_sha` differs from its row's, cut
      tonight on a fresh task after last night's task was cut. That earlier
      task holds `SPEC_WRITING` and `SPEC_REVIEW` attempts. It also drives
      an earlier cut at the revision's hash alone, one with a `REVIEWING`
      attempt, and one with a `REPAIRING` attempt.
    witness: tests/test_session.py::test_a_revised_specs_second_cut_settles_on_its_task_rows_spec_sha
  - claim: >-
      A task orphaned by anything but a zero-commit cut still feeds no
      re-queue cap. That covers a raise, a scan's stamp, an attempt in
      another phase, another state and another repository.
    witness: tests/test_session.py::test_a_task_orphaned_by_anything_but_a_cut_leaves_the_retry
    preserves: true
  - claim: >-
      `run_task` takes a keyword `task_id`, `None` by default, and builds
      its `CellSpec` with that `task_id`. The witness drives `9` and the
      default.
    witness: tests/test_task.py::test_run_task_hands_its_cell_the_task_it_was_given
  - claim: >-
      `cli._stack_runner`'s runner passes `run_task` the candidate's
      `task_id`, never its predecessor's, with a predecessor and with none.
      `cli._batch_runner`'s runner passes `run_task` no `task_id`, even for a
      candidate that carries one.
    witness: tests/test_cli.py::test_only_the_stack_runner_hands_run_task_the_candidates_task
  - claim: >-
      `push_unpackaged_work` counts the outcome's own task's recorded
      `pushed_sha` as this spec's push. So a cell run again on one task
      replaces that task's earlier unpackaged push. A branch head no task of
      this spec recorded is still refused. The witness drives a remote at
      the task's own push, then one an operator moved past it.
    witness: tests/test_package.py::test_a_rerun_on_one_task_replaces_that_tasks_own_unpackaged_push
---

## Context

Backlog item **b-792ab2**, step 6 of its Done. It cites `DESIGN.md`
§4.2.1 and §4.3. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides that spec review runs inside a stack batch, before each spec's
first cell.

A stack batch runs the queued specs into one pull request stack. Each task
that reaches `READY_FOR_REVIEW` is a **layer**, and the next task is cut
from the last layer, its **predecessor**.

**Where this sits.** `SA-0155` mints a fresh task for each spec through an
injected `mint`, before its first review, whatever `task_id` the candidate
carries. The operator decided that on 2026-09-24. It records the review on
that task, and hands the runner the candidate with `task_id` set. This spec
has the cell run on that task. `SA-0156` then builds the production review
and mint and passes them from `saffron batch --stack`. The split came from
the size of `SA-0156`'s first draft.

**What the tree base holds.** This spec's tree base is `SA-0155`'s head.
The chain below it runs `SA-0135`, `SA-0136`, `SA-0142` to `SA-0146`,
`SA-0153`, `SA-0154`, `SA-0157`, `SA-0159`, `SA-0147`, `SA-0148`,
`SA-0149` and `SA-0155`. Every line number below was read at
`f2a08a9f`, where none of their code exists. The chain edits `cli.py`,
`ledger.py`, `task.py` and `session.py`, so read those there by symbol.
This spec consumes these names.

- From `SA-0143`: `cli._stack_runner`. The runner takes a candidate and
  its predecessor, fetches the predecessor's branch, and calls `run_task`
  with a `Handoff`.
- From `SA-0148`: a `RATE_LIMITED` task in a stack batch waits, and its
  spec runs again next. `SA-0155` hands both calls the same task.
- From `SA-0155`: the phase label `SPEC_REVIEW` on each review's attempt,
  and a run for each minted task that the stack path attaches to
  tonight's batch. `Ledger.task_run(task_id)` returns a task's `run_id`,
  and raises `ValueError` for a task that does not exist.

**How a cell comes by its task today.** `_drive_cell` exports `.saffron/`
at `base_sha` and loads the policy from it
(`saffron/cell/session.py:1650`, `:1662`). It upserts the repo, creates
a run at `base_sha`, and creates a task with that `policy_sha` and
`context.prompt_sha()` (`:1688-1707`). Nothing reads a task id from
`CellSpec` (`:249-303`). `run_task` builds the `CellSpec` and calls
`run_one_cell` (`saffron/task.py:303-326`). So a spec `SA-0155` reviewed
on a task gets a second task, and the review sits on a task no cell ran.
`Ledger.record_policy` writes a task's policy after it exists
(`saffron/ledger.py:1100-1107`). PACKAGE calls it only when the value
differs (`saffron/phases/package.py:800-801`).
`Ledger.task_policy_sha` reads that column alone
(`saffron/ledger.py:1090-1098`).

**What a cell on a given task meets.** Three paths assume a cell mints
its own task. Each is wrong on a given task.

- **The re-queue cap.** `previous_cut_orphan` looks for another task at
  this repo, spec id and `CellSpec.spec_sha`
  (`saffron/cell/session.py:388-421`, `:408`, `:420`). That task ended
  `ORPHANED` on a `COMPLETE` run, and every attempt it holds is in phase
  `IMPLEMENTING` (`:412-415`). The cut settles `NOT_IMPLEMENTED` when it
  finds one, and `ORPHANED` otherwise (`:2201-2214`). Every stack task
  holds a `SPEC_REVIEW` attempt, and a revised one a spec-writing attempt
  too, so the phase clause refuses each. `SA-0150` makes a revised task's
  `CellSpec.spec_sha` the hash of its revision text, which never equals
  its task row's. So a revised spec cut each night re-queues each night.
- **The rate limit's read-back.** On `RATE_LIMITED` the cell reports
  `ledger.task_spend(task_id)` (`saffron/cell/session.py:2813`). That sums
  every attempt on the task (`saffron/ledger.py:1053-1063`). On a given
  task it counts the review, and on `SA-0148`'s rerun the first cell too.
- **The unpackaged push.** `push_unpackaged_work` pushes over a branch
  head that another task of this spec recorded, and refuses any other
  head. It leaves the outcome's own task out of that set
  (`saffron/phases/package.py:1097-1116`). `SA-0148`'s rerun on one task
  then refuses its own earlier push as a head "this spec never pushed".

**What the operator's decision removes.** A task given to a cell is
always tonight's. It is minted with no batch, and holds no attempt but
its reviews and, from `SA-0164`, its `SPEC_WRITING` revisions.
So its run is tonight's, `_drive`'s plain attach is right, and the budget
check sees all of it. A cut is always on an earlier night's task. The
cap needs no check of the given task itself, since a fresh task is never
`ORPHANED`.

## Problem

Build five things.

1. **The cell on the given task.** Add `task_id: int | None = None` to
   `CellSpec`. In `_drive_cell`, where the run and task are created, a set
   `task_id` takes that task and its run instead, as criterion 1 states.
   Read the run with `SA-0155`'s `Ledger.task_run`, whose `ValueError`
   stops a missing task before any cell comes up.
2. **The rate limit's read-back.** Read `ledger.task_spend(task_id)` once,
   as the cell takes its task. On `RATE_LIMITED`, report `task_spend`
   less that figure, as criterion 1 states. `task_spend` keeps its one
   production caller, so the `dead` gate stays green.
3. **The re-queue cap.** As criterion 2 states. Compare the earlier
   task's `spec_sha` with the cell's own task row's. Allow `SPEC_REVIEW`
   and `SPEC_WRITING` beside `IMPLEMENTING` in the phase clause, spelled
   as literals. `SA-0164` names the writing phase, and it lands after this
   spec. Reword the docstring's phase and `spec_sha` sentences.
4. **The task through `run_task`.** Add `task_id` to `run_task`, as
   criterion 4 states. `_stack_runner` passes `candidate.task_id` to it.
5. **The unpackaged push.** Add the outcome's own task's `pushed_sha` to
   the recorded set, as criterion 6 states. The awaiting-review check
   still reads the other tasks alone.

One docstring in `saffron/ledger.py` becomes false. `tasks_by_spec` says
`cell/session.py` mints a run and a task on each invocation
(`:690-691`), which a set `task_id` now stops. Reword it.

## Out of scope

- **`saffron batch` without `--stack`.** `_batch_runner` passes no
  `task_id`, so a plain batch still mints a task for a re-queued spec.
  `DESIGN.md:387` says such a spec "resumes that task row". Gate 0 already
  exempts a candidate that carries its `task_id`
  (`saffron/scheduler.py:650-656`). A stack batch now mints too. The
  departure goes to the backlog as its own item.
- **A revision on last night's task.** Tonight's task is fresh, so a
  revision `SA-0164` recorded on last night's task does not carry over.
  Tonight's review revises again.
- **A baseline per cell on one run.** Each cell records its baseline
  under its run (`saffron/cell/session.py:1762-1763`), and
  `baseline_results(run_id)` returns every row
  (`saffron/ledger.py:1248-1249`). `SA-0148`'s same-night rerun shares
  one task and run, so that run holds two baselines. `SA-0147` reads a
  layer's baseline by run, and the subtraction counts identities, so it
  can cancel a failure twice. That is `SA-0147`'s baseline read to settle,
  and it goes to the backlog.
- **The run's columns on a rerun.** `SA-0148`'s rerun writes the shared
  run's `status`, `preflight` and `ended_at` again
  (`saffron/cell/session.py:1782-1795`, `saffron/ledger.py:781-800`). The
  first cell's values do not survive. No reader tells the two cells apart.
- **The repository row.** The cell upserts its repo by
  `package.real_remote(repo)` (`saffron/cell/session.py:1683-1688`). The
  cap scopes its search to that repo id. `SA-0156`'s mint upserts by the
  pinned url. Where the two spellings differ, the minted task hangs from
  another repo row than the one the cap searches.
- **The production `review` and `mint`.** They are `SA-0156`'s.

## Notes for the agent

**Five criteria are new behaviour.** No text at the tree base reads a
task id from `CellSpec` or runs a cell on one. The edits to the cap and
the push each take a spelling of your own. So each declares a witness and
no mutant, and `witness` reports `skip`. Criterion 3 is `preserves`. It
names a test that passes now and must still pass.

**Every new witness fails with the source reverted, measured.** Criteria
1 and 2 build `CellSpec(task_id=...)`, which raises `TypeError` there.
Criterion 4 passes `run_task` a `task_id`, which raises too. Criterion 5's
stack half asserts a `task_id` the reverted runner never passes.
Criterion 6's reverted push refuses the task's own head. Import each new
name inside the test body.

**A `run_task` double that names its keywords.** `_stack_runner` now
passes `task_id`. A double in `tests/test_cli.py` that declares its
keywords with no `**kwargs` then raises `TypeError`. Add `task_id=None`
to each such double and change nothing else in it.

**Criterion 1's witness** follows
`test_a_wall_on_the_plan_turn_is_not_the_task_failing`
(`tests/test_session.py:4161-4180`), with `_stub_the_runtime`, `_drive`,
`_spec`, `_turn`, `_block`, `_PLAN` and `_rejected`. `_drive` opens
`tmp_path / "ledger.db"` itself (`:1307`). So the witness opens that
file first and closes it before the first drive.

- It upserts a repo at `str(tmp_path / "repo")`, the origin `_drive`'s
  cell records. On a run at `"e" * 40`, an older task for `SY-1` has
  `policy_sha` `"p" * 64`, one closed `IMPLEMENTING` attempt of 2.0, and
  state `GATE_ERROR`.
- On a second run at `"b" * 40`, a task with no policy holds one closed
  `SPEC_REVIEW` attempt of 0.75. This is the minted task.
- It wraps `Ledger.record_policy` to record `(task_id, policy_sha)` and
  then call through.

It drives the minted task three times. The first walls its plan turn at
a cost of 0.25. The second accepts a plan turn at 0.5 and walls the
implement turn at 0.125. The third runs a plan and an implement turn. It
then drives the older task the same way, and last task 999. It captures each drive's events. It
asserts:

- the first two outcomes are the minted task and its run,
  `RATE_LIMITED`. Their `spent_usd` are 0.25 then 0.625, and each drive's
  one `TaskOutcome` carries the same. The third outcome is the minted
  task and its run, and the fourth the older task and the older run.
- task 999 raises `ValueError`, and its cell created no network.
- `record_policy` was called exactly twice, for the minted task and then
  the older task, each with the SHA-256 of `gates: {}\n`. `_drive`
  writes that policy by default (`:1221`).
- two tasks and two runs. Each task's state is its last outcome's, so the
  older task is no longer `GATE_ERROR`.

It then drives once with no `task_id` and asserts a new task on a new
run. These fail it, each measured:

- a run created for a given task, which makes three runs
- `record_policy` called always, never, or only for a task with none
- the given task ignored, which mints a task per drive
- the read-back of the whole task, or no start figure, which gives 1.0
  then 1.625
- the start figure read at the rate limit, which gives 0.0
- the read-back less `SPEC_REVIEW` attempts, which gives 0.875 second
- the read-back of the last attempt alone, which gives 0.125 second
- the outcome right and the event reading the whole task

**Criterion 2's witness** runs four cases, each in its own directory
under `tmp_path`, so each has its own ledger. Each seeds last night's task
for `SY-1`, on a run at `"b" * 40`, with closed attempts in the phases
below. It sets that task `ORPHANED` and finishes its run `COMPLETE`. It
then seeds tonight's task at `"a" * 64` on a new run, with closed
`SPEC_REVIEW`, `SPEC_WRITING` and `SPEC_REVIEW` attempts. The cell runs on
tonight's task, with `CellSpec.spec_sha` `"f" * 64`, the revision's hash.
Each case drives a plan turn, a wall cut and a salvage turn with no
commits, as `test_a_second_cut_at_one_spec_sha_settles_the_spec` does
(`tests/test_session.py:2005-2062`).

| case | last night's row `spec_sha` | its attempts | outcome | line names |
|---|---|---|---|---|
| `revised` | `"a" * 64` | `SPEC_WRITING`, `SPEC_REVIEW`, `IMPLEMENTING` | `NOT_IMPLEMENTED` | last night's task |
| `other_sha` | `"f" * 64` | the same | `ORPHANED` | none |
| `reviewed` | `"a" * 64` | `SPEC_REVIEW`, `IMPLEMENTING`, `REVIEWING` | `ORPHANED` | none |
| `repaired` | `"a" * 64` | `SPEC_REVIEW`, `IMPLEMENTING`, `REPAIRING` | `ORPHANED` | none |

Each asserts the outcome's task and state. It asserts exactly one `cut
again at this spec_sha` line naming last night's task where the table
names one, and none elsewhere. These fail it, each measured:

- the cell's `spec_sha`, which fails `revised`
- either `spec_sha`, the row's or the cell's, which fails `other_sha`
- no `SPEC_WRITING` in the phase clause, or no `SPEC_REVIEW`
- the phase clause dropped, which fails `reviewed`
- a phase denylist of `REVIEWING` and `REBUTTING`, which fails `repaired`
- the sub-select bound to `CellSpec.task_id`, which reads `NULL` on the
  plain path. `test_a_second_cut_at_one_spec_sha_settles_the_spec`
  (`tests/test_session.py:2005`) fails it, since its third task then
  ends `ORPHANED`.

**Criterion 4's witness** follows `_drive` in `tests/test_task.py:24-86`,
with `_push`. It wraps `task_module.CellSpec` to record each one built.
It replaces `task_module.run_task` with `functools.partial(run_task,
task_id=9)` for one drive, then restores it for a second. It asserts the
two `task_id`s are 9 then `None`. A `CellSpec` built without the keyword
fails it, measured.

**Criterion 5's witness** replaces `cli.run_task` with a double that
records its keywords. It replaces the fetch `_stack_runner` makes, where
`_stack_runner` reads it, with one that returns `"d" * 40`. It calls
`_stack_runner`'s runner on `SY-1` with `task_id` 7 and no predecessor,
then on `SY-2` with `task_id` 8 and the predecessor `SY-1` with `task_id`
3. It calls `_batch_runner`'s runner on `SY-5` with `task_id` 5. It
asserts `run_task` got 7, then 8, then no `task_id` or `None`. These fail
it, measured against a stand-in runner that fetches nothing:

- the stack runner that drops the candidate's `task_id`
- the predecessor's `task_id` passed, which runs `SY-2` on `SY-1`'s task
- the same pass-through added to `_batch_runner`

**Criterion 6's witness** follows
`test_unpackaged_work_replaces_its_own_earlier_unpackaged_push`
(`tests/test_package.py:3330-3348`), with the `packageable` fixture. It
pushes `packageable.base` to `saffron/SA-0005` and records that push on
`packageable.task_id`, the outcome's own task. With the outcome
`RATE_LIMITED`, it asserts the push lands. The remote head is the
result's `pushed_sha`, not `packageable.base`, and the task's row
records it. An operator then pushes a commit on top of that head. A
second call is refused `not ours to replace`, and the remote keeps the
operator's head. These fail it, each measured:

- the own task left out of the recorded set, which refuses the first call
- an own push that lets any head through, which pushes the second call

**How the lists were measured.** A throwaway prototype ran on 2026-09-24
at `f2a08a9f`, on the host's git. It stood in for `_stack_runner` as a
runner that fetches nothing and calls `run_task`. The right build passed
the five new witnesses and the existing `test_session.py`,
`test_package.py`, `test_batch.py`, `test_task.py`, `test_ledger.py` and
`test_cli.py`. Each wrong version above was applied as a text edit, and
each failed its own witness. With the source reverted, each new witness
failed.

**What the witnesses leave undriven.**

- A given task on a run of another repository.
- A `RATE_LIMITED` cell run through `run_stack_batch`. Criterion 1 drives
  `run_one_cell` directly.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** `saffron/ledger.py` and `saffron/cell/**` are in `elevate_on`,
so `size` blocks at the `feature` ceiling of 3000 tokens
(`saffron/gates/core/size.py:26`). The prototype, formatted by
`ruff format`, measured 1004 changed tokens with `size_gate`'s own count.
`session.py` took 118, `package.py` 41, `ledger.py` 10, `task.py` 7 and
`cli.py` 1. The witnesses took 827. That is 33% of the ceiling.
