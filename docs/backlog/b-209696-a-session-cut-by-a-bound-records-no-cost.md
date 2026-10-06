---
id: b-209696
title: 'A session a bound cuts records $0.00, though it spent tokens'
status: done
closed: 2026-10-05
tier: 2
filed: 2026-10-02
specs: [SA-0206]
prs: [696]
commits: []
cites: [§4.3, §5.3]
related: [b-d4e015]
---

## Problem

Found in the spec loop's run 25, and split from b-d4e015 in run 26.

A session ends with a cost only when its `result` event arrives. When the
idle or wall bound kills the runner first, no `result` event exists. The
ledger then reads $0.00 for the attempt. `SA-0167`'s first cell spent 18
minutes of PLAN tokens and recorded nothing.

b-d4e015 stopped the idle bound from cutting a session that is still
writing. A stalled session, or one that reaches the wall, still records
nothing for what it spent.

## Done looks like

A session cut without a `result` event records the cost it reached. One
source is the per-step `usage` the runner already carries on assistant
events. That source lacks output tokens (`SA-0090`), so the record must say
the figure is a floor.

## Record

- 2026-10-02: filed in the spec loop's run 26, split from b-d4e015.
- 2026-10-05: done by `SA-0206` (#696), from stage 2's second stack batch. A cut turn now records a floor priced from its per-step usage and charges the larger of the floor and its carry.
