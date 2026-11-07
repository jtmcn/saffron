---
id: b-bff156
title: "`ready_task` returns `Refused` for a task that already ran a cell, though `CONTEXT.md` keeps Refusal for before any cell starts"
status: superseded
tier: 3
filed: 2026-10-12
closed: 2026-11-07
specs: []
prs: [1012]
commits: []
cites: [§5.7]
related: [b-c86c4b, b-e4cb58]
superseded_by: b-e4cb58
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
- 2026-11-07: superseded in grooming by b-e4cb58, filed in #1012 from the
  spec loop's run 52. It names the same clash and the same two exits, with
  newer evidence: `SA-0329` added a damaged `revert-exempt.json` as another
  `Refused` cause. The clash still stands: `ready_task` returns `Refused`
  (`saffron/task.py`), and `CONTEXT.md`'s **Refusal** still reads "before any
  cell starts".
