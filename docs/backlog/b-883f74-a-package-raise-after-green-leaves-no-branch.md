---
id: b-883f74
title: PACKAGE raising after a cell went `READY_FOR_REVIEW` leaves no branch and no way to resume it
status: open
tier: 1
filed: 2026-10-08
specs: [SA-0226]
prs: [745]
commits: []
cites: [§5.7]
related: [b-6cd3c2, b-2247dd]
---

## Problem

Measured in the spec loop's run 31.

SA-0226's cell ended `READY_FOR_REVIEW` at $13.29 and exported its
`patch.diff`. PACKAGE's re-verify seed then raised `CellRuntimeError`. The
ledger kept `READY_FOR_REVIEW` with no pull request, and nothing was pushed.
The batch counted the layer missed and refused SA-0227 and SA-0229.

Nothing re-runs PACKAGE alone. The delegate applied the patch to
`958db033` by hand, ran `make check`, pushed, and opened #745 as a draft with
a hand-written body. PACKAGE's in-cell re-verify never judged that tree. The
loop driver's `size` and `stack` then refused the task, because no PR was
recorded for it.

## Done looks like

A task can be left `READY_FOR_REVIEW` with an exported patch and no pull
request. A command then runs PACKAGE alone on it, re-verify included.

## Record

- 2026-10-08: filed from the spec loop's run 31.
