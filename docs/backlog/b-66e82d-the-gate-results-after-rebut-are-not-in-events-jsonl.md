---
id: b-66e82d
title: The gate results after REBUT are not in `events.jsonl`, so a red rebuttal names no gate
status: done
tier: 2
filed: 2026-09-22
closed: 2026-10-10
specs: [SA-0118, SA-0242]
prs: [433, 794]
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
- 2026-09-26: recurred in the spec loop's run 18. A `GateResult` in
  `events.jsonl` carries a status and no summary. `revert` has nine skip paths,
  and nothing said which one `SA-0144`'s head took (b-76f08d). Repair turns
  read `prose.py` and `integrity.py` to learn what failed.
- 2026-09-27: recurred in the spec loop's run 19. `SA-0147`'s attempt 1 read
  `2 new failures -> repair`. The log named only `prose` and `terms` as
  failing, and both failed at base too. So the log never said which new hits
  the repair was sent to fix. The repair went green on attempt 2.
- 2026-10-10: done by `SA-0242` (#794), from the spec loop's run 33.
