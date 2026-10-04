---
id: b-3b8eb2
title: The host never sees which criterion the `criteria` gate failed, and the log's count of new failures disagrees with the event's
status: open
tier: 3
filed: 2026-10-03
specs: [SA-0197]
prs: [659]
commits: []
cites: [§5.4]
related: [47]
---

## Problem

Found in the spec loop's run 27, watching `SA-0197`'s first attempt.

The cell log printed `gates: attempt 1, 3 new failures -> repair`, with
`criteria=fail`. The `GateResult` event for `criteria` in `events.jsonl` held
only `"new_failures": 1`. Neither the log, the event log nor the task's batch
directory named the criterion. Its failures went only to the repair turn's
prompt, inside the cell.

So an attended operator cannot tell what the repair turn is fixing until it
ends. The delegate inferred the cause from the repair turn's edits: a
parametrised witness whose node id no longer matched its declared name.

## Done looks like

The `criteria` gate's failures, each naming its witness, reach a host-side
record the operator can read during the cell. The log's failure count and the
event's agree, or each says what it counts.

## Record

- 2026-10-03: filed from the spec loop's run 27.
