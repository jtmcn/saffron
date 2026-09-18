---
id: b-eac388
title: A NULL `runs.preflight` means three things, and the batch header spec will inherit all three
status: open
tier: 2
filed: 2026-09-18
specs: []
prs: []
commits: []
cites: [§4.1, §6]
related: [164, b-7431a2]
---

## Problem

Found in the spec loop's run 7, 2026-09-18, reviewing #338 (`SA-0099`).

#338 writes `runs.preflight` where the baseline suite's outcome is known
(`saffron/cell/session.py:1417` and `:1430` at `origin/saffron/SA-0099`). A run
that never reaches that point keeps NULL. After #338, NULL covers three cases.

- A preflight probe raised inside `cell_up`. `cell_up` runs
  `preflight.assert_proxy_reaches_upstream` and
  `preflight.assert_host_is_unreachable` (`saffron/cell/session.py:875` and
  `:904`). A raise there reaches the `except BaseException` at `:2329`, which
  closes the run `ABORTED` and writes no preflight value.
- The run is still going. `create_run` inserts `status = 'RUNNING'`
  (`saffron/ledger.py:423-424`) and no preflight value.
- The row predates #338. `SA-0099` left every earlier row NULL on purpose.

The first case is the one §6's per-repo preflight field exists to show. A
header rendered from this column will print the same blank for a machine that
would not start and a run that is still unfinished.

## Done looks like

A run whose preflight probe raised is told apart from a run still in progress
and from an old row. Either the `cell_up`/abort path writes a value, or the
closed set gains a third one. The header spec names which it reads.

## Record

- 2026-09-18: filed from the spec loop's run 7 (stack #335 ← #338 ← #339 ←
  #342 ← #340). Surfaced by #338.
