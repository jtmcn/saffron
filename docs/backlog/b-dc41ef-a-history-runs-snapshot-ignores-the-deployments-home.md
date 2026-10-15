---
id: b-dc41ef
title: A History run's snapshot goes under the real ~/.saffron whatever `--home` says
status: open
tier: 3
filed: 2026-10-14
specs: [SA-0272]
prs: [875]
commits: []
cites: [§3.2]
related: [b-a8270f]
---

## Problem

Found by the critic's contract lens and both review seats on #875, in the
spec loop's run 39.

`session.HISTORY_SOURCE_ROOT` is `Path.home() / ".saffron" / "history"`.
That restates `cli.DEFAULT_HOME`. A batch run with `--home X` still writes
its ledger snapshot under the user's real home. `Ledger` keeps no path, so
`run_history` cannot derive the root from its `ledger`. The spec dictated
the literal, and `task.py` and `cli.py` were forbidden to it.

## Done looks like

`run_task` passes the deployment's home through to `run_history`. A test
drives a non-default home and finds the snapshot under it.

## Record

- 2026-10-14: filed from the spec loop's run 39.
