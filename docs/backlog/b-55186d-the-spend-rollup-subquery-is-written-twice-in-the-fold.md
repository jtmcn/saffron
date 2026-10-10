---
id: b-55186d
title: "The ledger's spend rollup is written twice in the fold, so the two states can sum it differently"
status: open
tier: 3
filed: 2026-10-10
specs: []
prs: [795]
commits: []
cites: []
related: []
---

## Problem

Found by the end review of batch 21 in the spec loop's run 33, on #795.

`SA-0243` added a `task_package` branch to the fold. Its spend subquery
restates the `task_state` branch's subquery verbatim
(`saffron/ledger.py:814`, `:824`). The `set_task_state` docstring says the
figure cannot disagree with its rows because it is derived. That now rests
on two copies staying alike. `SA-0243` sat at 1296 of its 1300 ceiling, so
the loop did not fix it there.

## Done looks like

- One SQL fragment or helper serves both branches.

## Record

- 2026-10-10: filed from the spec loop's run 33.
