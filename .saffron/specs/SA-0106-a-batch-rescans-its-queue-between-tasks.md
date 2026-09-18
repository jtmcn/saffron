---
id: SA-0106
title: A batch scans its queue once, so a child whose parent packaged at 23:00 waits for the next night
type: feature
priority: 3
depends_on: []
touches:
  - saffron/batch.py
  - saffron/cli.py
  - tests/test_batch.py
  - tests/test_cli.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/phases/**
  - saffron/report/**
  - saffron/replay.py
  - saffron/task.py
  - saffron/scheduler.py
  - saffron/ledger.py
budget_usd: 18
max_turns: 100
acceptance:
  - claim: >-
      A spec refused at the night's opening scan because its `depends_on`
      parent had no task starts later that night, once the parent's task
      reaches `READY_FOR_REVIEW`. It starts right after the parent, ahead of an
      opening candidate of lower priority, and the log names it before it
      starts. A grandchild waiting on that child starts after the child, the
      same night. Today the night runs only the opening candidates.
    witness: tests/test_batch.py::test_a_child_refused_at_the_opening_scan_runs_after_its_parent_packages
  - claim: >-
      After the first task, the latest rescan decides what runs, and a spec is
      started at most once a night. When a rescan offers again a spec whose
      task ended `RATE_LIMITED` earlier that night, the night skips it. An
      opening candidate the rescan no longer offers is not started.
    witness: tests/test_batch.py::test_a_spec_the_rescan_requeues_is_not_started_twice_in_one_night
  - claim: >-
      `saffron batch` rescans through `_resolve_queue`, against the base that
      readiness pinned for the night, and without stamping in-flight tasks
      `ORPHANED`. A task started after a rescan receives the `repo_id` that
      rescan resolved.
    witness: tests/test_cli.py::test_the_batch_rescans_through_the_pinned_base_without_stamping_orphans
  - claim: >-
      A night whose queue nothing changes still runs every opening candidate
      once, in order, and drains.
    witness: tests/test_batch.py::test_a_drained_queue_runs_every_candidate_once_in_order
    preserves: true
---

## Context

Backlog item **b-d6bff7**, found 2026-09-17 asking why the spec loop runs attended
cells rather than `saffron batch`.

`_batch` resolves the queue once, after readiness passes
(`saffron/cli.py:739-766`), and hands `resolved.candidates` to `run_batch`
(`:776`). `_drive` is a `for` loop over that list (`saffron/batch.py:160`), so
the night never looks at the queue again.

A spec with `depends_on` whose parent has no task at its current `spec_sha` is
refused in that scan (`saffron/scheduler.py:595`). A parent at
`READY_FOR_REVIEW`, `APPROVED` or `MERGE_TRAIN` admits it
(`DEPENDENCY_WAITING_STATES`, `saffron/scheduler.py:91`), and `run_task` then
cuts the child from the parent's branch (`task._resolve_stacked_on`,
`saffron/task.py:117`). So the admission and the stacking both exist. Only the
second scan is missing.

## Problem

A parent that packages at 23:00 leaves its child refused until the next night.
A chain of three specs takes three nights, which is the cost §4.2's dependency
gate footnote says stacking removes.

## Out of scope

**The spec loop.** It still runs attended cells, because it pushes review
commits to a parent before the child is cut. Its skill is not this spec's to
edit.

**`build_queue` and its refusals.** They already admit the child. Do not edit
`saffron/scheduler.py`.

**One run per repo** (backlog item 177). Each task still mints its own run.

**Prose in forbidden files that this change makes false.** Item b-d6bff7
updates it by hand after this merges. Do not cite it as a reason to stop:

- `DESIGN.md:385`: nothing is legitimately in flight when a scan happens.
- `DESIGN.md:400`: priority is "sorted once in memory".
- `DESIGN.md:404`: the next scan stamps a task left in flight `ORPHANED`.
- `DESIGN.md:408`: priority is "read exactly once, at scan".
- `task._resolve_stacked_on` (`saffron/task.py:133-136`): a grandchild is out of reach by design.
- The spec loop's `GOTCHAS.md`: `run_batch` resolves its candidates once.

**A rescan that raises.** It ends the night `INFRASTRUCTURE` through
`run_batch`'s existing `finally` (`saffron/batch.py:122-130`), and `_batch`
re-raises it to `main` (`_batch`'s `except`, `saffron/cli.py:786-792`). Printing a rescan's `gh`
gaps, which `_print_scan_gaps` does only for the opening scan
(`saffron/cli.py:668`), is also not this spec's.

## Notes for the agent

This change is **new** code, so every criterion declares a witness and no
mutant.

**Rescan after every task, not when the list runs out.** A child can outrank
opening candidates that are still waiting. Criterion 1's witness is built so
that rescanning only once the list is empty fails it: the opening queue holds
the parent at priority 1 and an unrelated spec at priority 3, and the child is
priority 1. A grandchild at priority 1 waits on the child, so rescanning only
once, after the first task, fails it too. The fake runner records each of the
three chain specs `READY_FOR_REVIEW`. The expected order is parent, child,
grandchild, then the unrelated spec.

**`batch.py` cannot import `cli.py`** (its module docstring,
`saffron/batch.py:10-16`). Hand `run_batch` the rescan as a callable that
returns the current candidates, the way it already takes `runner` and
`readiness_check`. Take the opening list as it does today, so the plan `_batch`
prints matches the first task the night starts.

**The latest rescan decides.** After each task, start the first spec the
rescan offers that has not started tonight. Do not merge its list with the
opening one. A live rescan runs the open-PR overlap refusal
(`saffron/scheduler.py:669-692`), and a draft PACKAGE opened tonight can make
an opening candidate refused. Criterion 2's witness includes an opening
candidate the rescan leaves out, and checks it never starts.

**Skip by spec id.** A rescan returns a new `Candidate`. A spec that ended in a
re-queueing state (`saffron/scheduler.py:103`) comes back with its `task_id`
set, so comparing candidates as values starts it a second time. The pinned
base is fixed for the night, so one spec id is one `spec_sha`.

**Rescan with `stamp_orphaned=False`.** `True` asserts that nothing is in
flight, which holds at the opening scan (`saffron/cli.py:472-477`). Mid-night,
a task this night left in flight is not a corpse: stamping it would re-queue it
into the same night, and `_stop` already names it (`saffron/batch.py:255`).
Pass the same `PinnedBase` the opening scan used (`saffron/cli.py:739`), so no
rescan fetches again.

**The runner reads the latest resolution's `repo_id`.** `_batch_runner` binds
the opening `resolved` (`saffron/cli.py:763`) and passes its `repo_id` to every
task (`:417`). On a repo's first night that is `None`, and the parent's own run
creates the row. `_resolve_stacked_on` returns no parent when `repo_id` is
`None` (`saffron/task.py:179`), so a child the rescan admitted would be cut
from `base_sha` without its parent's changes. In criterion 3's witness, the
second `_resolve_queue` result has a `repo_id` the first lacked, and
`cli.run_task` is a recorder. The fake `run_batch` calls the rescan, then the
runner.

**`_source_calls` stops at the first matching call**
(`tests/test_cli.py:2260`). `test_the_batch_scan_asks_for_the_stamping_the_attended_one_refuses`
(`:2558`) asks it whether `_batch` passes `stamp_orphaned=True`. A second
`_resolve_queue` call with `False` can be the one it finds first. Make the
helper keep looking, or aim the assertion at the opening call, and keep the
test asserting what it asserts today.

**Criterion 1's witness uses the real `build_queue`.** A fake rescan that
returns the child by hand proves the loop and nothing about the admission. Write
the parent, the child and the unrelated spec to a temporary directory (the
frontmatter shape is `_write_spec`, `tests/test_scheduler.py:139`, outside
`touches`: import it or copy it), and rescan
with `build_queue(directory, repo_id, ledger)`. The fake runner records the
parent's outcome in the ledger the way a real task leaves it:
`create_run`, `create_task` at the candidate's `spec_sha`, then
`set_task_state(task_id, "READY_FOR_REVIEW")` (`saffron/ledger.py:610`). Read
the opening candidates from `build_queue` too, so the child is refused there
for the reason a real night refuses it. Capture `emit` and check a line naming
the child comes before the runner's call for it. That line also names the
spec in `test_a_runner_that_raises_says_what_died` (`tests/test_batch.py:830`),
so tighten its assertion to the raised line.

**Criterion 3's witness fakes `_resolve_queue` and `run_batch`**, as
`test_saffron_batch_runs_a_night_with_the_defaults_4_2_1_fixes` does
(`tests/test_cli.py:2522`). The fake `run_batch` calls the rescan it was
given. Assert that the second `_resolve_queue` call received the first call's
`pinned` object and `stamp_orphaned=False`.

**Give every existing `run_batch` call a rescan.** In `tests/test_batch.py`, a
rescan that returns the opening list leaves each test's result unchanged.
Criterion 4 holds one of them to that.

**Update the docstrings the change makes false, in place.** In
`saffron/batch.py`, the module docstring says a K=1 `for` loop runs over
`build_queue`'s candidates. `run_batch`'s says `candidates` is `build_queue`'s
own return value. In `saffron/cli.py`, fix `_batch_runner`'s "paid for once by
`_resolve_queue`" and `_batch`'s "Resolves the queue…". `_resolve_queue`'s
`stamp_orphaned` paragraph (`saffron/cli.py:472-479`) says `False` is what
`saffron queue` passes. The rescan passes it too, so name both callers.
