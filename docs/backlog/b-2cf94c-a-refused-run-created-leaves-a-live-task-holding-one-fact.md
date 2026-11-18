---
id: b-2cf94c
title: A refused run_created append leaves a live task whose record holds task_created alone
status: open
tier: 3
filed: 2026-11-18
closed:
specs: []
prs: []
commits: []
cites: [§4.3]
related: [b-cafacd, b-3e0dbe]
---

## Problem

Found in the spec loop's run 79, on #1262 (`SA-0414`). `create_task`
commits the task row and appends `task_created`, then appends
`run_created` as a second write (`saffron/ledger.py:1670`). A record that
refuses the second append leaves the task live with one fact. A ledger
folded from that record then reads the task as bare and puts it on a
shared row (b-15c480).

The cell's critic raised it, and REBUT documented it with
`test_a_refused_run_created_still_leaves_the_task_created` rather than
fixing it. The `Record` protocol appends one fact at a time, and
`saffron/record/contract.py` was forbidden to the spec. `finish_run` and
`record_findings` carry the same commit-then-append shape. Batch 96's
finish pooled the concern.

## Done looks like

Either the two facts reach the record together, or a fold reads a task
holding `task_created` alone as unplaced rather than bare. The
documenting test is flipped to assert the new behaviour.
