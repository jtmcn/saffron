---
id: b-2dea1c
title: A spec that asks the cell to run its wrong versions spends the fifteen-minute turn bound on them
status: open
tier: 3
filed: 2026-09-22
specs: [SA-0123, SA-0130]
prs: [451]
commits: []
cites: [§4.3]
related: [b-2750d5, b-36b551]
---

## Problem

Found in the spec loop's run 14, 2026-09-22.

`SA-0123`'s notes listed about twenty wrong versions and asked the cell to
run each against the witnesses. It also asked for four more that the review
added. Each run is a pytest call on the ledger's test files.

The cell's IMPLEMENT turn was cut by the wall bound. That bound is
`TURN_TIMEOUT_S = 900` at `saffron/cell/session.py:63`. The kill came while the
agent was applying the spec's wrong versions, with criteria 4 to 6 still to
go. The first
REPAIR turn was cut by the same bound. IMPLEMENT had spent $4.17. The task
ended `EXHAUSTED` at $38.20, one line over its `size` ceiling.

Running the wrong versions is the host's job now. REVIEW's criterion probes
and the Spec seat's `driver.py probe` both do it outside the agent's turn.

## Done looks like

A spec says which wrong versions its witnesses must kill, and the cell is not
asked to run them. The host runs them, or the spec-writer's guidance says not
to ask.

## Record

- 2026-09-22: filed from the spec loop's run 14.
