---
id: b-ac97c0
title: Seven sentences still call the lenses disjoint by construction, after Appendix L measured two lenses filing one finding
status: open
tier: 3
filed: 2026-09-22
by_hand: true
specs: []
prs: []
commits: []
cites: [§4.6, §5.5, §7]
related: [6, 79]
---

## Problem

Found reviewing ADR 4, 2026-09-22.

Appendix L measured two lenses filing one finding, and principle 51 says that
agreement is a fact about the prompts. These sentences still state
disjointness as a property the design holds:

- `DESIGN.md` §4.6, "lens disjointness".
- `DESIGN.md` §5.5, "the lenses are disjoint by construction".
- `DESIGN.md` §7, the plausible-but-wrong row, "disjoint lenses".
- `CONTEXT.md`'s entry for a lens.
- The lens comment in `ontology/factory.ttl`, which `CONTEXT.md` is rendered
  from.
- The lens comment in `ontology/shapes/factory-shapes.ttl`.
- Backlog item 79.

## Done looks like

Each sentence says the remits are meant to be disjoint, and that L measured an
overlap. The no-vote rule rests on principle 51 as well as 9.
`CONTEXT.md` is edited through `factory.ttl` and the render.

## Record

- 2026-09-22: filed from ADR 4's review. ADR 4's principle 30 records it.
  By hand, because `DESIGN.md` and `CONTEXT.md` are `protected`.
