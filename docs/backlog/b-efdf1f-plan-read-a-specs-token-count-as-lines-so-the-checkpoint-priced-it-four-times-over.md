---
id: b-efdf1f
title: PLAN read a spec's token count as lines, so the checkpoint priced `SA-0169` at four times its size
status: open
tier: 1
filed: 2026-09-27
closed:
specs: [SA-0185]
prs: []
commits: []
cites: [§5.3]
related: [b-408cf5, b-43a061]
---

## Problem

Found in the spec loop's run 19, 2026-09-27.

A plan's `estimated_lines` counts lines (`saffron/agents/artifacts.py:77`).
`judge_estimate` prices it at four changed tokens a line
(`saffron/agents/artifacts.py:299-336`). `SA-0169`'s spec said its change came
to about 2080 tokens. The plan wrote 2100 lines, and the checkpoint priced
8400 changed tokens against the `feature` ceiling of 3000 at `elevated`. The
cell ended `PLAN_REJECTED` at $1.44.

The writer's split then measured the whole change at 2094 tokens. So the
refusal came from a unit confusion, not from the spec's size. The two plans
refused this run ran 2.4 to 4 times the size later measured.

## Done looks like

The plan prompt names the unit of `estimated_lines`. A spec's size note states
lines, or its `estimated_lines` reaches the plan turn. A plan estimate far off
the spec's own `estimated_lines` is recorded beside it in the plan record.

## Record

- 2026-09-27: filed from the spec loop's run 19.
