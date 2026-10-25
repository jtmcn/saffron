---
id: b-92fdbe
title: "driver.py record reads a task mid-PACKAGE and records a halt, because nothing checks whether the batch still runs"
status: open
tier: 3
filed: 2026-10-25
specs: []
prs: []
commits: []
cites: []
related: []
---

## Problem

Found in the spec loop's run 48.

The delegate ran `driver.py record SA-0316` after the cell's terminal line
but before PACKAGE finished. It printed "halted at REBUTTING" with no PR.
A second `record` after the batch exited read #966 correctly. The skill
says to wait for the exit, and a wait that matched the batch's header line
let the early read through.

## Done looks like

`record` refuses while the batch or cell that owns the task still runs,
and names the process.

## Record

- 2026-10-25: filed from the spec loop's run 48.
