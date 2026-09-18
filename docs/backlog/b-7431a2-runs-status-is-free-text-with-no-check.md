---
id: b-7431a2
title: '`runs.status` is free text with no CHECK, the shape #338 fixed one column over'
status: open
tier: 3
filed: 2026-09-18
specs: []
prs: []
commits: []
cites: [§4.1]
related: [164]
---

## Problem

Found in the spec loop's run 7, 2026-09-18, reviewing #338 (`SA-0099`).

At `origin/saffron/SA-0099`, `saffron/ledger.py:58` gives `runs.preflight` a
`CHECK` built from `RUN_PREFLIGHT_OUTCOMES`, and `set_run_preflight` refuses any
other value. Three lines down, `runs.status` is a bare `TEXT` column
(`saffron/ledger.py:61`). `finish_run` at `saffron/ledger.py:430` writes
whatever string it is handed.

Today the writers pass `RUNNING`, `COMPLETE` and `ABORTED`. A typo at a new call
site would land in the ledger unrefused, and a reader counting `ABORTED` rows
would miss it. `batches.status` already carries a `CHECK` for the same reason.

## Done looks like

`runs.status` takes a closed set, declared once and read by both the `CHECK`
and `finish_run`, in the shape `runs.preflight` uses. A witness shows
`finish_run` refusing a value outside it. Existing rows are left as they are.

## Record

- 2026-09-18: filed from the spec loop's run 7 (stack #335 ← #338 ← #339 ←
  #342 ← #340). Surfaced by #338.
