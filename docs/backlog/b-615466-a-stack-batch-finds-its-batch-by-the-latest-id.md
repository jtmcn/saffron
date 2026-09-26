---
id: b-615466
title: A stack batch finds its own batch by the latest id, and nothing enforces one batch at a time
status: open
tier: 3
filed: 2026-09-26
specs: []
prs: []
commits: []
cites: [§4.2.1]
related: [b-792ab2]
---

## Problem

Found in the spec loop's run 18, 2026-09-26, reviewing #527 (`SA-0153`).

`run_stack_batch` hands its end review `ledger.latest_batch_id()`, not the id
`run_batch` created. The two agree only while one batch runs on the ledger at
a time. `cli.py` states that premise and no lock holds it.

The Spec seat measured it: a runner that also calls `create_batch` mid-loop
sends the end review to the other batch's layers (`['2'] != ['1']`).

## Done looks like

- `run_batch` hands its batch id to its caller, and `latest_batch_id` goes.
- Or a lock holds one batch per ledger, and a test shows a second refused.

## Record

- 2026-09-26: filed from the spec loop's run 18 (stack #531). Kept as written
  on #527.
