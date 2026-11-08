---
id: b-8f6568
title: A spec review cut at its 90-turn ceiling refuses the whole chain below it, and the ceiling was never measured
status: done
tier: 1
filed: 2026-11-07
closed: 2026-11-07
by_hand: true
specs: []
prs: [1039]
commits: []
cites: [§4.2.1]
related: [b-d39d9a]
---

## Problem

Found in the spec loop's run 55.

Batch 69 ran `SA-0338` to `SA-0343` as one stack. Its spec review of
`SA-0338` stopped at 91 turns with no output, at $3.33 of $6. The route was
`error`, so the batch raised and refused all five children. No cell ran.

`SPEC_REVIEW_MAX_TURNS` was 90, marked as reasoned and unmeasured. The last
twelve reviews in the ledger ran 64 to 102 turns. 40 of 126 reached 80.

## Done looks like

The ceiling sits above the measured distribution, and the budget still binds.

## Record

- 2026-11-07: filed from the spec loop's run 55. Fixed by hand in #1039. The
  ceiling is now 150 and the writer's is 200.
