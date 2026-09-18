---
id: b-60732c
title: A `RATE_LIMITED` outcome carries 0 attempts, so its index row reads as a task that never tried
status: open
tier: 2
filed: 2026-09-18
specs: []
prs: []
commits: []
cites: [§6]
related: [165]
---

## Problem

Found in the spec loop's run 7, 2026-09-18, by #339's correctness lens.
Both review seats confirmed it.

At `origin/saffron/SA-0103`, the `except RateLimited` handler in
`saffron/cell/session.py:2297-2323` returns a `CellOutcome` with
`state="RATE_LIMITED"` and `spent_usd=ledger.task_spend(task_id)`. It passes no
`attempts`, so the field takes its default of 0 (`saffron/cell/session.py:324`).

Before #339 no unpackaged task reached the index, so the 0 went unread. #339
writes a row for every unpackaged task, with `attempts=outcome.attempts`
(`saffron/task.py:363` at `origin/saffron/SA-0100`). So every rate-limited row
reads `0 att`. `sort_key` tiebreaks on `-line.attempts`
(`saffron/report/index.py:107`), which ranks that row below every other row of
its rank.

The handler already reads spend back from the ledger, because the in-memory
tally loses the walled turn. Attempts are lost the same way.

## Done looks like

A `RATE_LIMITED` outcome carries the number of attempts its task recorded,
read back from the ledger the way its spend is. A witness drives a cell to a
rate limit after one or more attempts and reads that count from the index row.
This needs a spec whose `touches` include `saffron/cell/session.py`.

## Record

- 2026-09-18: filed from the spec loop's run 7 (stack #335 ← #338 ← #339 ←
  #342 ← #340). Surfaced by #339.
