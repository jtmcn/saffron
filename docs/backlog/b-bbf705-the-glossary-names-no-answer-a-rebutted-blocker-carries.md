---
id: b-bbf705
title: "The glossary names no answer a rebutted blocker carries, once `SA-0340` records three"
status: open
tier: null
filed: 2026-11-07
by_hand: true
specs: []
prs: []
commits: []
cites: [§5.6]
related: [42]
---

## Problem

Filed writing `SA-0340`.

`SA-0340` records each blocker's answer in the `rebuttal` fact as
`answered`, `unanswered` or `unread`. The morning queue then counts unread
and unanswered blockers apart from a sustained one. `CONTEXT.md`'s
**Rebuttal** entry names a fix and an argument, and no answer a blocker can
carry. The operator kept the three values a `Literal` in code, not an
ontology closed set.

By hand because `CONTEXT.md` is protected and is rendered from
`ontology/factory.ttl`, so a cell cannot move the two together.

## Done looks like

The **Rebuttal** entry, or one beside it, says what `unread` and
`unanswered` mean for a blocker, and that neither is an argument. The edit
lands in `ontology/factory.ttl` and is rendered into `CONTEXT.md`.

## Record

- 2026-11-07: filed writing `SA-0340`, for backlog item 42.
