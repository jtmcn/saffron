---
id: b-1572e7
title: A stack batch stacks a child on its lowest open parent and exempts only `depends_on[0]` from the overlap refusal
status: open
tier: 2
filed: 2026-10-23
specs: []
prs: [943]
commits: []
cites: [§4.2.1]
related: [b-c94a2f]
---

## Problem

Found in the spec loop's run 46, on `SA-0305`.

`SA-0305` declared `depends_on: [SA-0303, SA-0304, SA-0306]`, and
`SA-0306` sits on `SA-0303`. `_resolve_stack_base` in `saffron/scheduler.py`
picks the lowest id among open parents, so it chose `saffron/SA-0303`.
`_ancestor_branches` exempts only the chain of `depends_on[0]`. So batch 49
refused `SA-0305` at $0, because its `touches` overlap open #941, its own
parent.

#943 reordered `depends_on` to `[SA-0306, SA-0304]` by hand. An earlier batch
also refused `SA-0302` for overlapping #928, its own stack ancestor.

## Done looks like

The stack base is the deepest open parent on the chain. The overlap refusal
exempts every branch any `depends_on` entry reaches. A scheduler test holds
a three-parent spec whose parents are a chain.

## Record

- 2026-10-23: filed from the spec loop's run 46.
