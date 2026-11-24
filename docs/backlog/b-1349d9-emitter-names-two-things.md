---
id: b-1349d9
title: "\"Emitter\" names the projection's writer in `CONTEXT.md` and an `emit` callable in `DESIGN.md`, and §4.7 says `append` sets `failed`"
status: open
tier: 3
filed: 2026-11-23
outside_cell: true
specs: []
prs: []
commits: []
cites: [§4.7, §5.7]
related: [b-606ea3, b-9eceda]
---

## Problem

Found by the Standards seat on `SA-0424` (#1310), in the spec loop's run 84.

- `CONTEXT.md` defines **Emitter** as `materialize` in
  `saffron/projection.py`. `DESIGN.md` §4.7 and §5.7 use "emitter" for an
  `emit` callable that holds a log. So do three test names, among them
  `test_the_default_emitter_warns_once_for_each_fault_its_log_raised`.
- §4.7 still says `append` "sets `failed` instead". Since `SA-0424`, `failed`
  is a property read from `write_refused` and `unserializable`, and `append`
  sets those two flags.

Both files are `protected`, so a cell cannot fix either.

## Done looks like

One sense keeps the word, and the other is renamed or gets an _Avoid_ line,
rendered from `ontology/factory.ttl`. §4.7 names the two flags.

## Record

- 2026-11-23: filed from the spec loop's run 84.
