---
id: b-e4cb58
title: "`CONTEXT.md` defines a Refusal as before any cell starts, and `ready_task` returns `Refused` after one"
status: done
tier: 3
closed: 2026-11-08
by_hand: true
filed: 2026-11-02
specs: []
prs: []
commits: []
cites: [§5.7]
related: [b-74a122]
---

## Problem

Found by the Standards seat on #1008 in the spec loop's run 52.

`CONTEXT.md` defines a Refusal as "A task rejected before any cell starts".
But `ready_task` (`saffron/task.py`) returns a `Refused` when it rebuilds an
outcome for `saffron package`, which runs after a cell. `SA-0329` added one
more cause to it, a damaged `revert-exempt.json`.

## Done looks like

Either the entry covers a refusal after a cell, or the type takes another
name.

## Record

- 2026-11-02: filed from the spec loop's run 52. `CONTEXT.md` was forbidden
  to `SA-0329`.
- 2026-11-08: done by hand. The entry now covers `saffron package`'s refusals after the cell. The `Refused` docstring in `saffron/task.py` still says before any cell starts, which a cell can fix.
