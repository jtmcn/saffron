---
id: b-0703c8
title: A running task has no row in the morning queue until it ends, so the page cannot show what a night is doing
status: open
filed: 2026-10-02
specs: []
prs: []
commits: []
cites: [§5.7, §6]
related: [b-2d09de]
---

## Problem

Found on 2026-10-02 while asking how to see the queue beyond a single task.

`append_queue_line` is called from two places. PACKAGE calls it in
`saffron/phases/package.py`, and `saffron/task.py` calls it for a task that ends
before PACKAGE. Both run once the task is terminal. `_STATE_RANK` in
`saffron/report/index.py` already ranks `REVIEWING` and `REBUTTING`. Nothing
writes a row in either state while the task runs.

The page is also a static file with no refresh. An operator who opens it during a
night sees the tasks that ended before the page loaded. The task in a cell is
missing from it.

## Done looks like

_Not stated in the original item._ One candidate: `run_task` upserts a row as
each phase starts. PACKAGE's final row replaces it under the existing upsert key.
That changes §5.7 step 4, which appends one row at the end. §6 and §5.7 would
have to say so.

## Record

- 2026-10-02: filed from a session that surveyed the operator's views of the queue.
