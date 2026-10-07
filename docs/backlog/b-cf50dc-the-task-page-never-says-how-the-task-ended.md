---
id: b-cf50dc
title: "The task page never says how the task ended"
status: open
tier: 2
filed: 2026-10-06
specs: [SA-0219]
prs: [708]
commits: []
cites: [§6.2]
related: [b-a1d649, b-d269f4]
---

## Problem

Found 2026-10-06 by the final review of the run record view (ADR 9), on the
real ledger.

The task page shows phase, attempt number, gate, outcome and failure count.
It shows no state, risk, batch, run, times, turns or cost, though V2, V3 and
V5 return each of them. `/task/226` ends in `GATE_ERROR` with no attempts,
and its page is a title and an empty table. ADR 9 exists to answer why a
task ended where it did, and this page cannot.

Gate-result rows, failure lines, the "N more" row and finding rows share one
table, and no page has a header row. A finding row reads the same as a
failure row.

V2 and V5 sort task IRIs as text. So the no-batch list on `/` runs 99, 98,
… 9, 89, and the newest attended tasks sit deep in it.

## Done looks like

A task page heads with the task's state, risk, batch, pull request and total
cost. Each attempt shows its start, turns and cost. Gate results, failure
lines and findings sit in separate tables, and every table has a header row.
Batch and task lists are ordered by id as a number.
