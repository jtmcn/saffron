---
id: SA-0143
title: A batch cannot hand a task the branch of the task below it, so a stack batch yields siblings
type: feature
priority: 1
depends_on: [SA-0142]
touches:
  - saffron/task.py
  - saffron/batch.py
  - saffron/cli.py
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
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/ledger.py
  - saffron/events.py
  - saffron/record/**
  - saffron/repos/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - tests/test_scheduler.py
  - tests/test_consumes.py
  - tests/test_package.py
budget_usd: 27
max_attempts: 3
max_turns: 160
pending_symbols:
  - saffron/batch.py::run_stack_batch
  - saffron/cli.py::_stack_runner
acceptance:
  - claim: >-
      `run_task` takes a keyword `handoff`. Given a `Handoff` with both
      halves set, it never calls `_resolve_stacked_on`. It builds the
      `CellSpec` with that `stacked_on` and packages with that
      `target_branch` as `parent_branch`. Given a `Handoff` with both halves
      `None`, it never calls `_resolve_stacked_on`, and both values are
      `None`. Given no `handoff`, it calls `_resolve_stacked_on` once and uses
      its answer, as it does today.
    witness: tests/test_task.py::test_a_handoff_replaces_the_stacking_resolver
  - claim: >-
      A `Handoff` carries both halves or neither. One with `stacked_on` set
      and `target_branch` `None` raises `ValueError`, and so does the
      reverse. Both set, and both `None`, construct.
    witness: tests/test_task.py::test_a_handoff_carries_both_halves_or_neither
  - claim: >-
      `run_stack_batch` runs, in the order given, each spec it does not
      refuse, and none twice. In the witness no spec has a `depends_on`.
      It hands each task the last task before it that returned
      `READY_FOR_REVIEW`, and `None` before any has. A task adds no layer
      when it returns any other state, a `Refused`, or raises. The witness drives `EXHAUSTED`,
      `MERGE_FAILED`, `GATE_ERROR`, a `Refused` and a raise.
    witness: tests/test_batch.py::test_a_stack_batch_hands_each_task_the_last_task_that_reached_review
  - claim: >-
      `run_stack_batch` never runs a spec that reaches, through a
      `depends_on` entry at any position, a spec that ran in this batch and
      missed `READY_FOR_REVIEW`. It reaches it directly or through a spec
      refused this way. The batch emits one line for each such spec, its id
      padded to ten, then ` refused  `, then a reason naming every spec it
      reaches that missed. A spec that reaches none of them still runs. The
      witness drives a child, a grandchild and a later entry, each of a
      spec that ended `EXHAUSTED`. It drives a spec that reaches two that
      missed, one by a raise and one by a `Refused`.
    witness: tests/test_batch.py::test_a_stack_batch_refuses_every_descendant_of_a_task_that_missed_review
  - claim: >-
      A runner that raises counts toward the breaker in a stack batch. Two
      raises in a row end it `INFRASTRUCTURE` before the third spec starts.
    witness: tests/test_batch.py::test_a_stack_batch_counts_a_raise_as_an_abort
  - claim: >-
      `cli._stack_runner` returns a runner that takes a candidate and its
      predecessor. Given a predecessor, it fetches that task's branch from
      the origin into the mirror first. It then calls `run_task` with a
      `Handoff` of the fetched head and that branch. Given `None`, it
      passes a `Handoff` with both halves `None`. A predecessor branch the
      origin lacks raises `ParentGone`, and `run_task` is never called.
    witness: tests/test_cli.py::test_the_stack_runner_hands_each_task_its_predecessors_fetched_branch
  - claim: >-
      `run_batch` still rescans after every task, so a child refused at
      the opening scan runs once its parent packages.
    witness: tests/test_batch.py::test_a_child_refused_at_the_opening_scan_runs_after_its_parent_packages
    preserves: true
---

## Context

Backlog item **b-792ab2**, step 1 of its Done. It cites `DESIGN.md` §4.2
and §4.2.1. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides a stack batch. Section 1 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md` is the design.

A stack batch runs the queued specs into one pull request stack. It plans
its order once, at batch start. Each task is cut from the head of the task
below it, its **predecessor**. That is the last task before it to reach
`READY_FOR_REVIEW`. "Parent" keeps its one referent, `depends_on[0]`. A
task that misses `READY_FOR_REVIEW` adds no layer, and the batch refuses
its `depends_on` descendants.

**This spec is the second of four.** `SA-0142` builds the stack order as
`build_queue(..., stack=True)`. This spec runs an order and hands each
task its predecessor's branch. `SA-0144` adds `saffron batch --stack`,
which calls what this spec builds, and `saffron queue --stack`. `SA-0145`
records the stack's layers.

**What the tree base holds.** This spec's tree base is `SA-0142`'s head,
and `SA-0142` stacks on `SA-0136`. Only `depends_on[0]` stacks
(`saffron/task.py:133-136`), so that chain is what puts both in this
tree. `SA-0135` adds `Refused` to `saffron/task.py` and widens
`run_task`'s return to `CellOutcome | Refused`. It adds a check in
`run_task` that runs after `_resolve_stacked_on`. So `task.py`,
`batch.py` and `cli.py` are cited by symbol below, and every line number
was read at `012f8aab`.

**How a task is stacked today.** `run_task` calls `_resolve_stacked_on`
(`saffron/task.py:286-294`). That reads `depends_on[0]`'s newest waiting
task from the ledger (`:179-186`). It fetches that task's branch with
`package_phase.fetch_parent_branch` (`:202`). It returns the fetched head
and the branch, or `(None, None)` together (`:127-131`). `run_task` puts
the head in `CellSpec.stacked_on` (`:314`). It passes the branch to
`package` as `parent_branch` (`:340`). A spec with no `depends_on` is cut
from `base_sha` (`:179-180`).

**Why the fetch has to happen.** `fetch_parent_branch` fetches
`refs/heads/<branch>` from the origin into the mirror and returns its head
(`saffron/phases/package.py:172-204`). The cell's seed fetches the
mirror's own refs and checks out the tree base
(`saffron/cell/worktree.py:86-95`). So a head no mirror ref reaches is not
in the cell. PACKAGE checks the predecessor out detached in a mirror
worktree (`saffron/repos/mirror.py:119`).

**How a batch runs today.** `run_batch` drives `_drive`
(`saffron/batch.py:56-139`). `_drive` takes the first candidate not yet
started (`:177`). It checks `--until`, then the budget, then the breaker
(`:191-199`). It calls the runner with the candidate alone (`:208`). A
raise counts as an abort (`:209-227`). After every task it replaces the
pending list with a rescan (`:253-255`). `cli._batch` builds the runner
with `_batch_runner` and a rescan through `_resolve_queue`
(`saffron/cli.py:841-861`).

## Problem

Build four things.

1. **The handoff.** Add a frozen, keyword-only dataclass `Handoff` to
   `saffron/task.py`, with `stacked_on: str | None` and
   `target_branch: str | None`. The two are adjacent strings, as
   `PinnedBase`'s are (`saffron/task.py:57-60`). Its
   construction raises `ValueError` when exactly one is `None`. Add a
   keyword `handoff: Handoff | None = None` to `run_task`. Given one,
   `run_task` takes the pair from it and never calls
   `_resolve_stacked_on`. Given none, nothing changes.
2. **The stack loop.** Add `run_stack_batch` to `saffron/batch.py`. It
   takes the order, the ledger, the budget, `until` and a runner, and the
   keywords `readiness_check`, `clock` and `emit` as `run_batch` does.
   Its runner takes a candidate and the predecessor's `Candidate`, or
   `None`. It runs the order once with no rescan. It keeps `--until`, the
   budget check, the breaker, the batch row and the in-flight naming
   exactly as `run_batch` keeps them.
3. **The refusal of descendants.** Take a spec in that loop with any
   `depends_on` entry that missed `READY_FOR_REVIEW` in this batch. An
   entry refused this way counts too. The loop refuses the spec, and it
   never reaches the runner. Its line names each spec it reaches that ran
   and missed.
4. **The stack runner.** In `saffron/cli.py`, beside `_batch_runner`,
   add `_stack_runner`. It takes the same keywords and returns the runner
   `run_stack_batch` takes. Given a predecessor, it calls
   `fetch_parent_branch` on the pinned mirror and url with the branch
   `run_task` gave that predecessor's task. It lets any exception from the
   fetch propagate. It calls `run_task` with the resulting `Handoff`.

No production code calls `run_stack_batch` or `_stack_runner` until
`SA-0144`. So both are `pending_symbols`, and the `dead` gate defers them
while this spec is open.

## Out of scope

- **The `--stack` flags.** `saffron batch --stack`, `saffron queue
  --stack` and `_resolve_queue`'s `stack` keyword are `SA-0144`'s.
- **The record of the layers.** That is `SA-0145`'s. Its fact kind,
  `stack_layer`, is already in `KINDS` (`saffron/record/contract.py:38`).
- **Gate 0's overlap exemption for the batch's own tasks.** That is step 2
  of b-792ab2. A stack batch resolves its queue once, before any of its
  own pull requests is open. So nothing here needs the exemption yet.
- **The later steps of b-792ab2.** They are the end review, the
  rate-limit wait and spec review in the batch. Follow-up specs, the
  finishing layer and the queue page's stack view are later steps too.
- **`repo_id` after the first task.** A stack batch never rescans, so the
  runner keeps the opening scan's `repo_id`. On a repo's first night it is
  `None`. At `be9a9f90`, with a handoff, `run_task` reads it only in
  `push_unpackaged_work`, which looks for another waiting task of the same
  spec (`saffron/phases/package.py:1097-1104`). A stack batch runs each
  spec once, so that check has nothing to find.
- **The vocabulary.** `CONTEXT.md` has no entry for a stack batch or a
  predecessor. Backlog item b-466005 files both by hand.
- **`SA-0141`.** It is queued on another branch and also edits
  `saffron/cli.py`. If its pull request is still open when this cell
  starts, gate 0's open pull request overlap refusal holds this spec back
  until it merges. So no `depends_on` names it.

## Notes for the agent

**Every criterion but the last is new code.** Nothing at the tree base
holds the stack path's text. So criteria 1 to 6 declare a witness and no
mutant, and `witness` reports `skip` for them. Criterion 7 is
`preserves` and names a test that passes now.

**Import every new name inside the test body.** `Handoff`,
`run_stack_batch` and the stack runner do not exist at the tree base. A
module-scope import of one fails collection when the source is reverted,
and `revert` reads that as `skip`. `Refused` exists there, so import it
at the top.

**One loop, not two.** Do not copy `_drive`'s checks into the stack path.
One way is to let `run_stack_batch` call `run_batch`. It wraps the runner
in a closure that passes the predecessor and records each result. The
rescan it passes returns the order minus the refused specs, and emits
their lines. `_drive` counts a raise as an abort
(`saffron/batch.py:209-227`). From `SA-0135` it also skips the attach and
the breaker's count for a `Refused`.

**Name the branch once.** `run_task` names each task's branch
`saffron/<spec id>` (`saffron/task.py:306`). Put that in one function in
`task.py` that `run_task` and the stack runner both call.
`saffron/phases/package.py:649` keeps its own copy, and `phases/` is
forbidden here.

**Criterion 1's witness** follows `_drive` in `tests/test_task.py:23-83`.
It replaces `run_one_cell` with a double that records the `CellSpec` and
returns `READY_FOR_REVIEW`. It replaces `package_phase.package` with one
that records `parent_branch`. It replaces `task_module._resolve_stacked_on`
with one that records its calls and returns `("c" * 40, "saffron/TE-9")`.
The spec declares `depends_on: [TE-9]`. It drives three calls.

- `Handoff(stacked_on="d" * 40, target_branch="saffron/TE-8")`: no
  resolver call. `stacked_on` is `"d" * 40`, and `parent_branch` is
  `"saffron/TE-8"`.
- `Handoff(stacked_on=None, target_branch=None)`: no resolver call, and
  both are `None`.
- no `handoff`: one resolver call, `"c" * 40` and `"saffron/TE-9"`.

These fail it:

- a handoff that sets `stacked_on` and leaves `parent_branch` to the
  resolver
- a handoff of two `None`s read as no handoff
- a resolver still called, its answer discarded

**Criterion 2's witness** constructs the four shapes. A dataclass with no
check fails it.

**Criteria 3 to 5 drive `run_stack_batch`** with a fake runner that
records `(candidate.spec.id, predecessor.spec.id or None)` and returns a
canned result or raises. Build candidates with `tests/test_batch.py`'s
`_candidate`, and each outcome that ran with `_outcome` and a run from
`_spend` at $1. Use its `ledger` and `repo_id` fixtures and `_ready`. The
budget is 100.

**Criterion 3's witness** passes this order, whose ids are not sorted.

| order | spec | result | predecessor |
|---|---|---|---|
| 1 | `TE-7` | `READY_FOR_REVIEW` | `None` |
| 2 | `TE-3` | `EXHAUSTED` | `TE-7` |
| 3 | `TE-9` | `MERGE_FAILED` | `TE-7` |
| 4 | `TE-1` | `GATE_ERROR` | `TE-7` |
| 5 | `TE-5` | a `Refused` | `TE-7` |
| 6 | `TE-8` | `READY_FOR_REVIEW` | `TE-7` |
| 7 | `TE-2` | raises `RuntimeError` | `TE-8` |
| 8 | `TE-6` | `READY_FOR_REVIEW` | `TE-8` |
| 9 | `TE-4` | `READY_FOR_REVIEW` | `TE-6` |

It asserts the calls are exactly the table's spec and predecessor pairs,
row by row, and the stop reason is `DRAINED`. These fail it:

- the previous task as predecessor, whatever it returned
- every state outside `ABORT_STATES` counted as a layer
- `MERGE_FAILED` counted as a layer, since it packaged
- a raise or a `Refused` that leaves the task as predecessor
- the order sorted by id or priority

**Criterion 4's witness** passes this order.

- `TE-11` returns `EXHAUSTED`.
- `TE-12` depends on `TE-11`. `TE-13` depends on `TE-12`.
- `TE-14` returns `READY_FOR_REVIEW`.
- `TE-15` depends on `TE-14` and `TE-11`, in that order.
- `TE-16` raises. `TE-17` returns a `Refused`.
- `TE-18` depends on `TE-16` and `TE-17`.
- `TE-19` depends on `TE-14` and returns `READY_FOR_REVIEW`.

It collects `emit`'s lines. It asserts the runner saw `TE-11`, `TE-14`,
`TE-16`, `TE-17` and `TE-19` only, and `TE-19`'s predecessor is `TE-14`.
It asserts exactly one refused line each for `TE-12`, `TE-13`, `TE-15`
and `TE-18`. It asserts none for `TE-11`, `TE-14`, `TE-16` and `TE-19`.
It asserts nothing about a line for `TE-17`'s own `Refused`. `TE-12`'s
and `TE-13`'s name `TE-11`. `TE-15`'s names `TE-11` and not `TE-14`. `TE-18`'s names
`TE-16` and `TE-17`. These fail it:

- a check of `depends_on[0]` alone, which runs `TE-15`
- children refused and grandchildren run, which runs `TE-13`
- a grandchild's reason that names only `TE-12`
- a raise, or a `Refused`, not counted as a miss
- a refused line printed and not emitted

**What criteria 3 and 4 leave undriven.** They drive `EXHAUSTED`,
`MERGE_FAILED`, `GATE_ERROR`, a `Refused` and a raise. The in-flight
states, `RATE_LIMITED`, `PREFLIGHT_FAILED`, `NOT_IMPLEMENTED`,
`PLAN_REJECTED` and `SCOPE_REVIEW` are not driven. Test for
`READY_FOR_REVIEW` alone, so each of them misses too.

**Criterion 5's witness** passes `TE-1` and `TE-2`, which both raise, and
`TE-3`. It expects `INFRASTRUCTURE` and no call for `TE-3`. A wrapper that
turns a raise into a `Refused` fails it.

**Criterion 6's witness** follows
`test_the_adapter_stacks_a_child_on_its_parents_branch`
(`tests/test_cli.py:3169-3215`), with `_local_origin`,
`_push_parent_branch`, `_mirror_of`, `_seed_repo` and `_seed_task`.

- It pushes `saffron/SY-9000` and `saffron/SY-5555` to the origin. It then
  deletes the local `saffron/SY-9000` with `git branch -D` before
  `_mirror_of`. `ensure_mirror` prunes the mirror against the local
  checkout, so the mirror starts without that branch.
- It seeds `SY-5555` at `READY_FOR_REVIEW` with a recorded push, so
  `_resolve_stacked_on` would stack on it. The candidate `SY-1` declares
  `depends_on: [SY-5555]`. The ledger holds no row for `SY-9000`.
- It replaces `cli.run_task` with a double that records `handoff`.

It asserts the mirror has no `refs/heads/saffron/SY-9000`, then drives
three calls.

- With predecessor `SY-9000`, the handoff is the pushed head and
  `saffron/SY-9000`. The mirror's `refs/heads/saffron/SY-9000` is that head.
- With `None`, the handoff's halves are both `None`.
- With predecessor `SY-7777`, never pushed, the call raises
  `package.ParentGone` and the double is never called.

These fail it:

- `run_task` called with no handoff, which stacks on `SY-5555`
- a head read from the ledger in place of the fetch
- a `ParentGone` caught and run unstacked
- the branch taken from the candidate's `depends_on[0]`

Measured on 2026-09-23 at `be9a9f90`, with these helpers and
`fetch_parent_branch` called directly. Before the fetch the mirror had no
such ref. After it, the ref and the returned head both equalled the pushed
head. `saffron/SY-7777` raised `ParentGone`.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** About 125 changed lines of source and 280 of test. `SA-0131`'s
cell measured 4.3 tokens a line in `saffron/cli.py` and 4.0 in
`tests/test_cli.py` (`50ef269d`). At 4.5 and 3.8 that is about 1630
tokens of the 3000 ceiling (`saffron/gates/core/size.py:26`). Keep test
docstrings short.
