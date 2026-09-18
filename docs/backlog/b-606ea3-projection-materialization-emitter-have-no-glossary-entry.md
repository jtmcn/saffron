---
id: b-606ea3
title: '"Projection", "materialization" and "emitter" name SA-0107''s work and have no glossary entry'
status: open
by_hand: true
filed: 2026-09-18
specs: []
prs: []
commits: []
cites: [§4.6, §9]
related: [65, 72, b-946f03]
---

## Problem

Found 2026-09-18, writing `SA-0107`.

`SA-0107` creates `saffron/projection.py` and a batch-end materialization.
`DESIGN.md` §9 v2.5 and Appendix T call the whole the emitter. None of the three
words is in `CONTEXT.md`. `ontology/` is forbidden to the spec for the reason
`docs/agents/issue-tracker.md` gives, so the cell cannot add them.

## Done looks like

Each term the merged code uses has a `CONTEXT.md` entry rendered from
`ontology/factory.ttl`, or an `_Avoid_` line that points at the one it uses.
This is done by hand, because `CONTEXT.md` is `protected` and generated.

## Record

**Filed 2026-09-18** with `SA-0107`, as its vocabulary follow-up.
