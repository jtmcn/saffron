---
id: b-7c1c99
title: One /24 the cell runtime refuses stops every cell, and a network create that hangs waits forever
status: open
tier: 2
filed: 2026-10-23
specs: []
prs: []
commits: []
cites: [§5.1]
related: []
---

## Problem

Found in the spec loop's run 46, on 2026-10-23.

`allocate_network` in `saffron/cell/runtime.py` walks `SUBNETS["pool"]` one
/24 at a time. When a create fails, it asks which network holds that /24. A
holder moves the walk on. No visible holder re-raises the create's error.

On this host `10.200.0.0/24` failed in every mode. The vmnet plugin's job
exited 1, and the runtime then held a pending operation. That operation
blocked every later network call until the service restarted. No interface
or route on the host held the /24. So the walk's first /24 raised, and no
cell could start. Batch 46 failed on it, and the loop waited for a reboot.

Two gaps show. A refused /24 that no visible network holds stops the whole
pool. And no timeout tells a create that hangs from one that refuses.

## Done looks like

A /24 whose create fails with no visible holder is skipped, and the walk
names it on stderr. A network create past a bound raises
`CellRuntimeError` naming the /24 and the bound. A test drives both with a
fake runtime.

## Record

- 2026-10-23: filed from the spec loop's run 46. The reset steps live in
  the run's handoff.
