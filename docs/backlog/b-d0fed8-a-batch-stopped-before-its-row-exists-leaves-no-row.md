---
id: b-d0fed8
title: "A batch sent SIGTERM during readiness or its first queue scan exits 143 with no ledger row"
status: open
tier: 2
filed: 2026-10-11
specs: []
prs: []
commits: []
cites: [§4.2.1]
related: [95, b-5df2a7]
---

## Problem

Measured by the Spec seat on #812 (`SA-0258`), in the spec loop's run 34.

`SA-0258` wraps the whole of `_batch` in the SIGTERM handler
(`saffron/cli.py:274`). `_batch` runs `preflight.check_readiness` and the
first `_resolve_queue` before `run_batch` calls `ledger.create_batch`
(`saffron/batch.py:147`). A signal in that window unwinds cleanly and exits
143. No batch row exists to close. The seat drove it and read `rc 143` with
the batches table empty.

Item 95 closed the same gap for a queue that fails to resolve. A night
stopped this early leaves nothing in `~/.saffron/ledger.db` to say it began.
`docs/HOST-HARDENING.md` now says the row closes "once it has one".

## Done looks like

A batch stopped before its first scan ends leaves a closed row, or the
operator decides a night that never scanned leaves none. A test sends the
signal inside `check_readiness` and reads the ledger.

## Record

- 2026-10-11: filed from the spec loop's run 34 (#812).
