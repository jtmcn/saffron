---
id: b-206d2c
title: The `history` rule takes a runaway row as a spec's budget floor
status: open
tier: 3
filed: 2026-10-20
specs: []
prs: []
commits: []
cites: []
related: [b-41664e]
---

## Problem

Found writing `SA-0306` on 2026-10-20.

`driver.py check` compares a spec's `budget_usd` with the highest pre-review
total among past cells of its shape. For `SA-0306` that row was `SA-0162`, at
$39.72. That cell ran past its size ceiling at 5202 tokens and ended on
`error_max_turns`, so its spend measures a runaway, not the shape. The spec's
nearest true peer, `SA-0277`, spent $9.39 and $11.51 before REVIEW. A budget
of $32 drew a blocker and $42 a concern, so the spec carries $58.

The turn half already marks a peak cut off at its own ceiling as a floor
(`_cut_off_at_turn_ceiling`). The budget half has no such mark.

## Done looks like

The budget comparison skips or marks a runaway row, as the turn comparison
does. A runaway ended over its size ceiling or on a turn or budget ceiling.

## Record

- 2026-10-20: filed from the spec chain that wrote `SA-0300` to `SA-0306`.
