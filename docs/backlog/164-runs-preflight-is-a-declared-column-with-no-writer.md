---
id: 164
title: runs.preflight is a declared column with no writer, so the batch header's preflight field has no source
status: open
filed: 2026-09-17
specs: [SA-0099]
prs: []
commits: []
cites: [§4.1, §6]
related: []
awaiting: [338]
---

## Problem

Found 2026-09-17, reading what a single execution can be seen through.

§4.1 gives `runs` a `preflight` column. `saffron/ledger.py:52` declares it as
`preflight  TEXT,`. §6 lists per-repo preflight status among the batch header's
six fields, and calls this one a column that exists and is never written.

Measured against `~/.saffron/ledger.db`: 0 of 99 runs carry a non-NULL value.
The word occurs twice in `saffron/ledger.py`, at `:52` in the schema and at
`:318` inside a comment about a different subject. There is no writer.

The write was never wired, rather than never designed.
`saffron/cell/session.py:1331` mints the row through `create_run`, which inserts
four columns and not five (`saffron/ledger.py:404-418`). The outcome is known in
two places and discarded at both. `saffron/cell/session.py:1256-1261` emits a
`Preflight` event per step, and `saffron/cell/session.py:1408-1418` decides the
machine was unfit and stamps the task `PREFLIGHT_FAILED`.

`runs.status` is no substitute, and the code says so itself. The abort path at
`saffron/cell/session.py:2317-2327` calls a preflight that raises "the path an
operator hits first" and closes such a run "ABORTED, not COMPLETE". So `ABORTED`
already carries a machine that would not start, folded together with Ctrl-C and
every other `BaseException` from anywhere in a long task. Measured the same day,
`runs.status` reads `COMPLETE` on 94 rows and `ABORTED` on 5. Which of those
five never started is not recoverable.

`tests/test_ledger.py:797` is the guard against a column written at scan and
read by nobody. It asserts over `batches` and `tasks` only, and reaches no
column of `runs`. That is why this survived.

This item is Task 4 of
`docs/superpowers/plans/2026-08-31-operator-visibility.md`, which specified it as
`SA-0032`. Parts 2 and 3 of that plan were never built. `.saffron/specs/done/`
runs `SA-0031` and then `SA-0040`, so `SA-0032` through `SA-0039` do not exist.

## Done looks like

`runs.preflight` is non-NULL on every run a driven cell creates, written where
the outcome is known rather than re-derived from a task state. The value is one
of a closed set, refused at the write, in the shape `batches.status` already
uses. A run that passes preflight and aborts later records a passing preflight,
because an interrupt during REVIEW says nothing about the machine an hour
earlier. The 99 existing rows stay NULL.

## Record

**Filed 2026-09-17**, from an inventory of what one execution can be seen
through. `SA-0099` carries it.

- 2026-09-18: open as PR #338 (`SA-0099`, spec loop run 7), stacked in
  #335 ← #338 ← #339 ← #342 ← #340.
