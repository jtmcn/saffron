---
id: b-a64578
title: "`saffron serve` will show a resumed batch's spend without its tail"
status: open
tier: 3
filed: 2026-10-20
specs: []
prs: []
commits: []
cites: [§4.2.1]
related: [b-8a0c9a]
---

## Problem

Found by `SA-0304`'s second spec review, on 2026-10-20.

Under `SA-0304`, a `saffron finish` resume writes nothing to the batch row.
The row keeps the night's window and its `spent_usd_est` snapshot.
`saffron serve` renders that snapshot as the batch's "spent" column
(`saffron/view/graph.py:178-179`, `ontology/queries/view/V1-batches.rq`). Its
task count reads `runs.batch_id`, which the follow-ups attach to. So after a
resume one row counts the tail's tasks and leaves out their spend. The stack
view reads the live `batch_spend` (`saffron/report/stack.py:93`), so the two
pages disagree for one batch.

The operator accepted this to keep the night's row as the night closed it.

## Done looks like

The batch page shows a resumed batch's spend with its tail, or says the
column is the night's alone. A test drives a batch with a resumed tail.

## Record

- 2026-10-20: filed from the spec chain that wrote `SA-0300` to `SA-0306`.
