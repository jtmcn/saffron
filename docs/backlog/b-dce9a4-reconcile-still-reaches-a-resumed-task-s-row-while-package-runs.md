---
id: b-dce9a4
title: Reconcile still reaches a resumed task's row while PACKAGE runs
status: open
tier: 2
filed: 2026-09-24
specs: []
prs: []
commits: []
cites: [§3.3, §4.2, §4.2.1, §5.7]
related: [29]
---

## Problem

Item 29 left one window open on purpose, for `SA-0020` to close. A resumed
task escapes the in-flight guard. `_drive_cell` (`saffron/cell/session.py`)
writes `READY_FOR_REVIEW` and calls `finish_run` before PACKAGE runs, so the
row still carries the previous
attempt's `pr_url` while the cell is alive. Reconciling in that window asks
about the old PR and reads its `CHANGES_REQUESTED`. Writing it onto a live row
hands the task back out as resumable, because `CHANGES_REQUESTED` is in
`scheduler.REQUEUE_STATES`. A second cell on the same branch is the shape that
blocked item 29's first attempt.

`SA-0020` shipped as the dependency gate and closed none of this. No open item
carries the window. `saffron/reconcile.py`'s docstring still points at item 29
for it, and item 29 is closed. Item 29 named `cli.py` as the ordering's owner.
The packaging call lives in `run_task` (`saffron/task.py`) today, where both
commands arrive.

The reach widened since the record was written. `saffron queue` runs at will,
mid-phase included, and its scan starts no cell. One batch's rescans run
between tasks, so the overlap needs a second invocation: another batch, or an
attended `saffron cell`. A second batch's opening resolve stamps in-flight
rows `ORPHANED`, but `READY_FOR_REVIEW` is outside `reconcile.IN_FLIGHT_STATES`.
The corpse half skips the row and the PR half writes `CHANGES_REQUESTED` onto
it. The scan then offers a task whose cell is inside PACKAGE.

The row reads `READY_FOR_REVIEW` in that window, so no state test can tell it
from a finished one. Item 29 recorded that reasoning against a wider guard
inside `reconcile`. The shape it named stands: the row leaves
`PR_PENDING_STATES` before PACKAGE is called.

## Done looks like

A reconcile running between a resumed task's last state write and PACKAGE's
first write cannot move its row into a `REQUEUE_STATES` value.
The fix orders the state write, and a wider state guard inside `reconcile`
does not count.

A witness test reconciles inside that window, driven the way item 29's
witnesses drive the CLI.

Every gate that reads the row still reads a state that says what is true.

## Record

- 2026-09-24: filed after checking item 29's closure against the tree, where
  the window stands as written and nothing owns it.
