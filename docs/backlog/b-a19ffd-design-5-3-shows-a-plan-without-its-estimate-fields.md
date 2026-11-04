---
id: b-a19ffd
title: '`DESIGN.md` §5.3 shows a `plan.json` without its estimate fields'
status: open
tier: 3
filed: 2026-11-04
specs: []
prs: []
commits: []
cites: [§5.3]
related: [b-15db6e]
---

## Problem

Found by the Standards seat on #1014, in the spec loop's run 53.

The `plan.json` example in `DESIGN.md` §5.3 (`DESIGN.md:863`) lacks
`estimated_lines` and `estimated_test_lines`. The `Plan` model requires both,
so the example no longer validates.

## Done looks like

§5.3's example carries both fields, with values that pass the model's
validator.

## Record

- 2026-11-04: filed from the spec loop's run 53.
