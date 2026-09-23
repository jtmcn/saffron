---
id: b-66e82d
title: The gate results after REBUT are not in `events.jsonl`, so a red rebuttal names no gate
status: open
tier: 2
filed: 2026-09-22
specs: [SA-0118]
prs: [433]
commits: []
cites: [§5.5]
related: [b-4a63b7]
---

## Problem

Found in the spec loop's run 13, 2026-09-22.

`SA-0118`'s log said `gates: 1 new failures after the rebuttal` and then
`EXHAUSTED`. No `GateResult` event in `events.jsonl` names the gate that failed.
Finding it took reproducing every gate by hand, and the answer was `revert`
(item b-4a63b7).

## Done looks like

Each gate result after REBUT is an event in `events.jsonl`, and the
`new failures` line names each failing gate.

## Record

- 2026-09-22: filed from the spec loop's run 13.
- 2026-09-23: recurred in run 15. `SA-0128`'s attempt 1 failed `census` (3)
  and `dead` (1), and `events.jsonl` carried the counts with no identities.
  The ids came from the batch record only after the cell exited.
