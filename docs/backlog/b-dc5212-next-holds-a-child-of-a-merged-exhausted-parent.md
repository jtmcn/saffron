---
id: b-dc5212
title: driver.py next holds back a child whose EXHAUSTED parent's code is already on main
status: open
tier: 3
filed: 2026-10-01
by_hand: true
specs: [SA-0151, SA-0174]
prs: [626, 628]
commits: []
cites: []
related: [b-038aef]
---

## Problem

Found in the spec loop's run 24, 2026-10-01.

After #626 merged `SA-0162`'s adopted branch, `next` printed "held back
SA-0151: its parent SA-0162 is EXHAUSTED, so a cell would cut it from main".
Cutting from `main` was right, since `main` held the parent's code. The
delegate started the cell by its path. The cell's own preflight printed
`unstacked` and cut from `main`, as wanted.

## Done looks like

`next` treats a parent whose pull request merged as merged, whatever the
task's terminal state, and names the child.

## Record

- 2026-10-01: filed from the spec loop's run 24.
- 2026-11-07: marked by hand in grooming. The work is in the spec loop's driver under
  `.claude/`, and `SA-0279` refuses any spec that touches that path.
- 2026-11-07: moved to tier 3 in grooming on the operator's ruling of 2026-11-07. It bites only on the driver's attended path, which is now the fallback.
