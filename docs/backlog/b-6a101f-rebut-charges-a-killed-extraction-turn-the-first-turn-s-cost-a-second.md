---
id: b-6a101f
title: REBUT charges a killed extraction turn the first turn's cost a second time
status: open
tier: 3
filed: 2026-09-25
closed:
specs: []
prs: []
commits: []
cites: [§4.1]
related: [b-792ab2]
---

## Problem

`run_agent` reports `last_cost_usd` as the cost of a turn killed before
any result event (`saffron/phases/implement.py:319-334`). REBUT's extraction
turn is passed the first turn's cost there, then adds the failed attempt's
cost to the first turn's (`saffron/phases/rebut.py:192-197`). So a killed
extraction turn charges the first turn twice. `SA-0160` avoids it for the
spec writer.

## Done looks like

A killed turn with no result event adds nothing to REBUT's cost.

## Record

- 2026-09-25: filed from the spec reviews of `b-792ab2`'s last build specs.
