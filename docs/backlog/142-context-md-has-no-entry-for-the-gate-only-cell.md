---
id: 142
title: Nothing in `CONTEXT.md` defines the gate-only cell, and three sentences about the lenses go false
status: open
tier: 2
filed: 2026-09-16
by_hand: true
specs: [SA-0087, SA-0088, SA-0089]
prs: [274, 277, 282]
commits: []
cites: [§5.5]
related: [118, 133, 140]
---

## Problem

**Tier 2.** By hand, because every file involved is `forbidden` to the cells
that made the change.

`CONTEXT.md` §5 defines **Cell**, **Container** and **Critic cell**, and closes
the last with an `_Avoid_` list. `SA-0089` ships a *third* kind of cell with no
entry, so nothing constrains what the next spec calls it and
`tests/ontology/test_vocabulary_agrees_with_context.py` cannot reach a term that
is not there. The diff itself already drifts: `DESIGN.md`, `pr_body.py` and two
backlog titles say **gate-only cell**, while the new code's prose says "gate
cell".

Its entry needs the thing that distinguishes it from the critic cell: **its own
`--internal` network and `dict(policy.thread_env)` — no proxy, no credential**,
which is what Appendix N already learned the hard way.

Separately, three sentences are now false or half-false:

- `CONTEXT.md`: "Until `SA-0087` and `SA-0088` land, the lenses still run in the
  implementer's cell." Both have landed.
- `DESIGN.md` §5.5's equivalent, which also names `SA-0089`.
- `.claude/agents/spec-reviewer.md` check 4 — item 145.

Each is scoped to a range of specs, so no single spec's `scope` gate catches it
going false. Item 133 records the same shape.

## Done looks like

A **Gate-only cell** entry in `ontology/factory.ttl`, rendered into `CONTEXT.md`,
with its own `_Avoid_` line ("the gate cell", "the suite cell", "the third
cell"); the two stale sentences corrected; and the code's prose reading
"gate-only cell" throughout.
