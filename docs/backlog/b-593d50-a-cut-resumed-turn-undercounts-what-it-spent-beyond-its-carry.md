---
id: b-593d50
title: "A resumed turn cut mid-stream records the larger of its own floor and the session's carry, so it undercounts its own spend"
status: open
tier: 2
filed: 2026-10-05
specs: []
prs: []
commits: []
cites: [§4.1, §7.1]
related: [b-209696]
---

## Problem

Found by #696's Spec seat, on `SA-0206`.

`run_agent` in `saffron/phases/implement.py` charges a turn with no result
event `max(floor_usd_est, last_cost_usd)` (`saffron/phases/implement.py:416`).
The floor sums the cut turn's own step counts (`saffron/phases/implement.py:408`).
The carry is the cost of the turn before it. A resumed turn takes that carry
from the session's last figure. The repair turn passes `last_cost`
(`saffron/cell/session.py:2589`), which `saffron/cell/session.py:2619` sets
from the previous turn's `cost_usd_est`. That figure covers the whole session
so far.

So the floor and the carry price different things. A resumed turn cut
mid-stream records the larger of the two, not their sum. It undercounts by
up to the cut turn's own spend.

## Done looks like

A cut resumed turn records at least what it spent beyond the carry it started
from. A test cuts a resumed turn whose floor is below its carry and reads a
cost above the carry.

## Record

- 2026-10-05: filed from stage 2 of the delegate-loop plan (the first live stack batches, batches 13 and 14).
