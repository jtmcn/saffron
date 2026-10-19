---
id: b-d149c6
title: "`saffron migrate` writes no `task_engine` fact, so a migrated task folds with no engine"
status: open
tier: 3
filed: 2026-10-19
specs: []
prs: []
commits: []
cites: [§4.1]
related: [b-2e0b97, b-d28fd8, 170]
---

## Problem

Found by both seats on #909, in the spec loop's run 44. `SA-0281` named it
in its Out of scope.

`SA-0281` (#909) adds a `tasks.engine_commit` column and a `task_engine`
fact. The migration's docstring lists the sixteen kinds it writes
(`saffron/record/migrate.py:9-15`), and `task_engine` is not one. A task
written to the ledger before `SA-0278` wired the record folds back from a
migration with a NULL engine.

## Done looks like

`migrate` writes a `task_engine` fact for each task whose row carries an
engine. A migrated ledger folds back to the same `engine_commit` values.

## Record

- 2026-10-19: filed from the spec loop's run 44.
