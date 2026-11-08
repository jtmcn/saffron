---
id: b-d39d9a
title: "A cell spends past its own `budget_usd` during REVIEW and REBUT, and nothing stops it"
status: open
tier: 1
filed: 2026-11-06
specs: [SA-0335, SA-0343]
prs: []
commits: []
cites: [§5.2, §7.1]
related: [b-2f4746]
---

## Problem

Found in the spec loop's run 54.

`SA-0335` declared `budget_usd: 69`. IMPLEMENT and two GATE attempts spent
$40.81. REVIEW then ran for 63 minutes, with 40 criterion probes over 15
criteria and five adequacy blockers. REBUT moved the head. The cell reached
`READY_FOR_REVIEW` at $76.77, and `record` read $80.11 once PACKAGE ran.

Nothing compared the spend with the ceiling once IMPLEMENT ended. The overrun
came out of the batch's cell allowance and stopped the batch after two of
its four specs.

## Done looks like

A cell's spend is checked against its own `budget_usd` before each phase. A
phase that would cross it ends the task at a named state. A test drives a
REVIEW that crosses the ceiling.

## Record

- 2026-11-06: filed from the spec loop's run 54.
