---
id: b-1ff5a3
title: "`render_context`'s docstring counts six closed sets, and `SETS` holds eleven"
status: open
tier: 3
filed: 2026-10-27
specs: []
prs: []
commits: []
cites: []
related: [b-c16c6c]
---

## Problem

Found in the spec loop's run 49, by the Standards seat on #979.

`ontology/render.py:93` says "Three of the six sets wrap across source lines".
`SETS` holds eleven sets at #982's head. The count of sets that wrap is
unchecked too.

## Done looks like

The docstring states no count, or one a test holds to `SETS`.

## Record

- 2026-10-27: filed from the spec loop's run 49.
