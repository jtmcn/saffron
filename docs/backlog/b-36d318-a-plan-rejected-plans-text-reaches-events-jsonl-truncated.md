---
id: b-36d318
title: A `PLAN_REJECTED` plan's text reaches `events.jsonl` truncated, so its per-part estimates are lost
status: open
tier: 3
filed: 2026-09-27
closed:
specs: []
prs: []
commits: []
cites: [§5.3]
related: [b-efdf1f]
---

## Problem

Found in the spec loop's run 19, 2026-09-27.

`SA-0147`'s first cell ended `PLAN_REJECTED` on 5800 estimated changed
tokens. The plan's text reached `events.jsonl` truncated, and no other record
kept it. The per-part estimates were lost, so sizing the split rested on the
delegate's own estimate.

## Done looks like

On `PLAN_REJECTED` the host records the whole plan as a control artifact,
hashed when it is extracted. The rejection event names where it lies.

## Record

- 2026-09-27: filed from the spec loop's run 19.
