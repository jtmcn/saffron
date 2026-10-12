---
id: b-bff156
title: "`ready_task` returns `Refused` for a task that already ran a cell, though `CONTEXT.md` keeps Refusal for before any cell starts"
status: open
tier: 3
filed: 2026-10-12
specs: []
prs: []
commits: []
cites: [§5.7]
related: [b-c86c4b]
---

## Problem

Found by the conventions lens and the Standards seat on #845 (`SA-0266`),
in the spec loop's run 35.

`CONTEXT.md` defines a Refusal as a task rejected before any cell starts.
`saffron/task.py`'s `ready_task` returns `Refused` for a
`READY_FOR_REVIEW` task whose PACKAGE raised. That task ran a cell. The
spec told it to return `Refused`, and `CONTEXT.md` was forbidden to it.

## Done looks like

The operator chooses one. `CONTEXT.md` widens Refusal to cover a task
`saffron package` declines, or `ready_task` returns its own type.

## Record

- 2026-10-12: filed from the spec loop's run 35 (#845).
