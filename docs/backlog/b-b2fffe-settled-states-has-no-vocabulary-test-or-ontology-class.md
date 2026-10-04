---
id: b-b2fffe
title: '`SETTLED_STATES` has no line in the vocabulary test and no class in the ontology'
status: open
tier: 3
filed: 2026-10-03
specs: [SA-0198]
prs: [662]
commits: []
cites: [§6]
related: [b-49a2f7]
---

## Problem

Found by #662's Standards seat in the spec loop's run 27.

`SA-0198` added `SETTLED_STATES` to `saffron/scheduler.py`, the seven states
`CONTEXT.md`'s **Settled task** names. `tests/ontology/test_vocabulary_agrees_with_code.py`
checks four other scheduler sets against `TaskState`, and has no line for this
one. `ontology/factory.ttl` has no settled class. So the set and the glossary
can drift apart with no test failing. Both files were forbidden to the spec.

## Done looks like

`ontology/factory.ttl` declares the settled states, `CONTEXT.md` renders from
it, and the vocabulary test holds `SETTLED_STATES` to it.

## Record

- 2026-10-03: filed from the spec loop's run 27.
