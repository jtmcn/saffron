---
id: b-5abe53
title: "A stack batch's spec review routed `run` leaves no line in the batch log"
status: open
tier: 2
filed: 2026-10-09
specs: []
prs: [777]
commits: []
cites: []
related: [b-4e1b6d]
---

## Problem

Found in the spec loop's run 32.

The stack batch prints a line for a spec review only when it escalates,
errors or leads to a revision (`saffron/batch.py:627`, `:636` and `:736`). A
review routed `run` adds the spec to `reviewed` and prints nothing
(`saffron/batch.py:643`). Batch 20 ran a spec review for every layer. Its log
showed only `SA-0232`'s and `SA-0245`'s revisions. So the delegate told the PR
seats that no spec review ran, which was false. The rounds were in the
ledger's `spec_reviews` rows all along.

## Done looks like

Every spec review prints one line naming its route, `run` included. A test
drives a stack batch through a `run` route and reads the line.

## Record

- 2026-10-09: filed from the spec loop's run 32.
