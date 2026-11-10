---
id: b-d39d9a
title: "A cell spends past its own `budget_usd` during REVIEW and REBUT, and nothing stops it"
status: done
closed: 2026-11-09
tier: 1
filed: 2026-11-06
specs: [SA-0335, SA-0343]
prs: [1106]
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
- 2026-11-09: partial in #1106 (`SA-0343`), from the spec loop's run 57. REVIEW now draws from one pool and caps each session at what is left. REBUT's half stays open.
- 2026-11-09: #1106 deletes `critic_budget`. `tests/test_rebut.py:1083` still names it in a test name, and item 120 still cites it. That file was `forbidden` to `SA-0343`, so both seats kept it here.
- 2026-11-09: done by hand. REBUT's half is §5.6's deliberate rule: REBUT runs once past the budget under a fixed cap and two reserves (`SA-0203`, b-4c5dc7). Its overrun is bounded by that cap, so no phase spends an unbounded remainder. The test name that still named `critic_budget` now names REBUT's own cap.
