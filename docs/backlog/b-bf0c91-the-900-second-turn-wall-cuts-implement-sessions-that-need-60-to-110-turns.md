---
id: b-bf0c91
title: The 900-second turn wall cuts IMPLEMENT sessions that need 60 to 110 turns
status: open
tier: 1
filed: 2026-09-27
closed:
specs: []
prs: []
commits: []
cites: [§4.3]
related: [4, 34, b-36b551, b-149df3]
---

## Problem

Found in the spec loop's run 19, 2026-09-27.

Every turn runs under `TURN_TIMEOUT_S = 900.0` (`saffron/cell/session.py:63`,
bound at `:1963`). In run 19 the wall cut 6 of 14 IMPLEMENT sessions and one
REPAIR session. The six were `SA-0155`, `SA-0168`, `SA-0181`, `SA-0169`,
`SA-0175` and `SA-0156`, and `SA-0175`'s repair was cut too.

No cut was a hang. Each landed mid-thought, right after a tool call.
`SA-0175`'s IMPLEMENT session ended with 0 commits after an `Edit`. The
salvage turn from b-36b551 recovered every cell. But `SA-0169`'s cut session
never wrote the cell test its notes asked for (b-20043f).

The specs in this chain need 60 to 110 turns. The cells the wall let finish
took 55 to 109 IMPLEMENT turns (`SA-0180` 103, `SA-0148` 109). A bound of 15
minutes per session sits below that work at the pace the model runs.

## Done looks like

The wall scales with the spec's `max_turns`, or a spec declares it beside its
other ceilings. The log line for a cut names which bound fired. A test holds a
long session that the turn ceiling bounds and the wall does not cut.

## Record

- 2026-09-27: filed from the spec loop's run 19.
