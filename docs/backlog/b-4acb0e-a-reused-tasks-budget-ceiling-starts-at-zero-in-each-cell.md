---
id: b-4acb0e
title: A reused task's budget ceiling starts at zero in each cell, so a task can spend its budget once per cell
status: open
tier: 2
filed: 2026-09-27
closed:
specs: [SA-0241]
prs: []
commits: []
cites: [§4.3]
related: [b-792ab2]
---

## Problem

Found in the spec loop's run 19, 2026-09-27, reviewing `SA-0168` (#546).

`_over_budget` holds `spent` against `spec.budget_usd`
(`saffron/cell/session.py:2108`). `spent` starts at 0.0 in each cell
(`:1851`). `SA-0168` runs a stack batch's cell on the task its spec review is
recorded on. That cell starts its count at zero, so the review's spend is
outside the ceiling. A task resumed across cells gets a fresh budget each time.

`DESIGN.md` §4.3 names task and batch ceilings. The in-cell correctness lens
and both seats raised it, and review kept it as no regression.

## Done looks like

A cell on an existing task starts `spent` at the task's recorded spend. A test
holds a second cell on one task that stops at the task's ceiling.

## Record

- 2026-09-27: filed from the spec loop's run 19.
- 2026-10-07: specced as `SA-0241`. The operator kept each cell's own spend
  apart from the task's, and a task resumed at its ceiling ends `EXHAUSTED`.
