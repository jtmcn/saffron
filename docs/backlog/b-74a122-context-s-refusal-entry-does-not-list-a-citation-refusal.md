---
id: b-74a122
title: "`CONTEXT.md`'s Refusal entry does not list a stack batch's refusal for citations that do not resolve"
status: open
tier: 3
filed: 2026-10-17
specs: []
prs: []
commits: []
cites: [§4.2.1]
related: [b-d31930]
---

## Problem

Found by the Standards seat on #898, in the spec loop's run 43.

`SA-0294` gives `run_stack_batch` a `cite` callable. A spec whose citations
do not resolve is refused with no review. `CONTEXT.md`'s **Refusal** entry
lists the stack batch's other causes. This one is not among them.
`CONTEXT.md` was forbidden to `SA-0294`.

## Done looks like

The **Refusal** entry names the citation cause beside the stack batch's
others, rendered from `ontology/factory.ttl` if the set is closed there.
`SA-0295`, which supplies the production `cite`, is the natural place.

## Record

- 2026-10-17: filed from the spec loop's run 43.
