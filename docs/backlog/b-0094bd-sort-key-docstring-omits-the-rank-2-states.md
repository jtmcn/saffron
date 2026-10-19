---
id: b-0094bd
title: "`sort_key`'s docstring lists five states that need you, and `_STATE_RANK` ranks eleven there"
status: open
tier: 3
filed: 2026-10-19
specs: []
prs: []
commits: []
cites: [§6]
related: [120, b-032c3e]
---

## Problem

Found by the Standards seat on #903, in the spec loop's run 44.

`sort_key`'s docstring names the states that need you as `MERGE_FAILED`,
`PLAN_REJECTED`, `PREFLIGHT_FAILED`, `GATE_ERROR` and `NOT_IMPLEMENTED`
(`saffron/report/index.py:122-124`). `_STATE_RANK` gives rank 2 to more
states than those. `REBUTTAL_UNJUDGED` and `REVIEW_INCOMPLETE` are two of them
(`saffron/report/index.py:52-55`). The docstring was stale before `SA-0276`,
and `saffron/report/**` was forbidden to it.

## Done looks like

The docstring names the rank-2 set by pointing at `_STATE_RANK`, so it
cannot drift from it again.

## Record

- 2026-10-19: filed from the spec loop's run 44.
