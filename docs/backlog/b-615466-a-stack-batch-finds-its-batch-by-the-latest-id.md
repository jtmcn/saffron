---
id: b-615466
title: A stack batch finds its own batch by the latest id, and nothing enforces one batch at a time
status: partial
tier: 3
filed: 2026-09-26
specs: []
prs: [934]
commits: []
cites: [§4.2.1]
related: [b-792ab2, b-a714d2]
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
- 2026-11-07: groomed. `run_stack_batch` now holds the batch id it creates and hands it to its end review (`6a50eb23`, `SA-0304`, #934). The measured case is gone. The first exit is one reader short. `cli.py` renders the stack view after a stack batch with no id, so `write_stack_view` still reads `latest_batch_id`. The second exit, a lock, is b-a714d2's whole Done, so a lock there closes this item too.
