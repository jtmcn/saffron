---
id: b-32f492
title: A refusal from run_task leaves a Ceilings event with nothing after it
status: open
tier: 3
filed: 2026-09-23
specs: []
prs: []
commits: []
cites: [§6]
related: [b-602d00]
---

## Problem

Found 2026-09-23, in the spec review of `SA-0135`.

`run_task` emits `Ceilings` first, for every task (`saffron/task.py:269-280`).
`SA-0135` adds a refusal after that event, when a consumed entry does not
resolve at the tree base. The refused task's `events.jsonl` then ends on a
lone `Ceilings`, with no event that says the task was refused.

`saffron watch` cuts a log at its last `Ceilings`, as the newest task's
boundary (`saffron/watch.py:116-132`). On a refused task it opens on that
lone event. It shows a task that never started and hides the task before it.

`SA-0135` cannot fix it, because `saffron/events.py` is forbidden there.

## Done looks like

A refusal from `run_task` leaves an event that says so, and `saffron watch`
renders it. Or the `Ceilings` event moves after the refusal, so a refused
task writes no event at all. A test drives a refused task through
`saffron watch` and reads what it prints.

## Record

- 2026-09-23: filed with `SA-0135`'s first revision.
