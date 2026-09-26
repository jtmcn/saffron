---
id: b-830357
title: The budget gate's witness cannot tell `>` from `>=`, so an off-by-one at the boundary passes
status: open
tier: 3
filed: 2026-09-26
specs: []
prs: []
commits: []
cites: [§4.2.1]
related: []
---

## Problem

Found in the spec loop's run 18, 2026-09-26, reviewing #527 (`SA-0153`).

`test_the_budget_gate_is_one_comparison_before_each_task` drives a $20 spec
against a $5 budget. The mutant `>` to `>=` at the budget comparison in
`saffron/batch.py` survives it at base and at head.

## Done looks like

- The witness adds a spec whose budget equals what is left, and the mutant
  fails it.

## Record

- 2026-09-26: filed from the spec loop's run 18 (stack #531).
