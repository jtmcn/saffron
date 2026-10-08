---
id: b-a04cc8
title: A stack batch whose every layer's seed raised reports `DRAINED` and exits 0
status: open
tier: 1
filed: 2026-10-08
specs: []
prs: []
commits: []
cites: [§4.4, §7]
related: [b-60a399, b-6cd3c2]
---

## Problem

Measured in the spec loop's run 31.

Batches 17 and 18 each started SA-0225 first. Its cell seed raised
`CellRuntimeError: seeding the worktree failed`, and the batch refused
SA-0228 because it reaches SA-0225. Both batches then printed
`batch: DRAINED` and exited 0, with no cell run.

Batch 16 met the same raise and exited 2 as `INFRASTRUCTURE`. The difference
was only that batch 16 had a layer before the raise. A night that ran nothing
because the cell runtime could not seed reads the same as a night that ran its
whole order.

## Done looks like

A batch whose layers all ended in an infrastructure raise exits 2 and names
the raise. A test drives a stack batch whose runner raises
`CellRuntimeError` on its only runnable layer and asserts the stop reason
is not `DRAINED`.

## Record

- 2026-10-08: filed from the spec loop's run 31.
