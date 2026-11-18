---
id: b-15c480
title: A task with no run fact folds onto the first row at its base_sha, off its own batch's row
status: open
tier: 3
filed: 2026-11-18
closed:
specs: []
prs: []
commits: []
cites: [§5]
related: [b-cafacd]
---

## Problem

Found in the spec loop's run 79, on #1262 (`SA-0414`). That spec puts a
task whose record holds a run fact on a `runs` row of its own. A task with
no run fact still shares the first row at its `base_sha`
(`saffron/ledger.py:807`, its `ponytail:` comment). Every task written
before `SA-0414` is such a task, and so is every migrated one.

The Spec seat measured what that costs. Two cuts at one `base_sha`, the
younger's row tied to a batch, were stripped of run facts and folded back
into the writer. Before the fold the rows read `COMPLETE` and `ABORTED`.
After it both tasks sat on the first row and read `COMPLETE`. The same
happens at the spec's base. `SA-0414`'s Problem 3 asked for own-row-first
on every task, and its Out of scope allowed the bare case.

A second concern sits on the same function. `exclude_keys` is every
run-fact key in the whole record, so each bare task's lookup builds an
`IN (...)` list of that size (`saffron/ledger.py:819`). Batch 96's finish
pooled it.

## Done looks like

A bare task folded back into its writer keeps the row it held when no
other task names that row. `exclude_keys` is scoped to the task's repo
and `base_sha`. A test folds the two-cut case above and reads each
task's own row and status.
