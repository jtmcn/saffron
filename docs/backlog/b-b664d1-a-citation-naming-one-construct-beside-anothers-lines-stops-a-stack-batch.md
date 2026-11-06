---
id: b-b664d1
title: "A citation that names one construct beside another's lines passes until a parent moves them, then stops the stack batch"
status: open
tier: 2
filed: 2026-11-02
specs: []
prs: []
commits: []
cites: [§4.2.1]
related: [b-d31930, b-61993a]
---

## Problem

Found in the spec loop's run 52.

`SA-0331` said "`_finish` writes `READY_FOR_REVIEW`, `MERGE_FAILED` or
`EXHAUSTED` (`saffron/phases/package.py:633-634`)". Those lines held `_state`,
not `_finish`. `cite` passed the spec at `main`, because the lines resolved
there.

`SA-0329` then added 45 lines above `_finish`. Batch 63 checked `SA-0331` at
that branch. It moved one citation and could not move this one, since the
held name matched nothing the sentence named. It refused `SA-0331`, and
`SA-0330` with it. A spec PR (#1009), the operator's merge and a second batch
followed.

The same spec carried about ten bare citations, such as `:1146`, with no
construct named beside them. The batch's spec review found each one about 49
lines stale after `SA-0329`. Nothing checks or moves a citation of that shape.

## Done looks like

`cite` flags a citation whose sentence names a construct the cited lines do
not hold, at the spec's own base. A bare citation into a file a parent layer
changes is flagged or moved before the spec review reads it.

## Record

- 2026-11-02: filed from the spec loop's run 52.
- 2026-11-06: recurred in the spec loop's run 54. `SA-0336` added 34 lines to `saffron/ledger.py`, and batch 68 refused `SA-0337` with `1 citation(s) do not resolve`. `driver.py check` ran `cite` at `origin/main` only, where every citation resolved. The operator ran `SA-0337` as a single cell from `main`.
