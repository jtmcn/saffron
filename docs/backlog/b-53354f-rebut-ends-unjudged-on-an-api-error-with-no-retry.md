---
id: b-53354f
title: REBUT ends a task unjudged on one API error, with no retry
status: open
tier: 2
filed: 2026-11-22
specs: []
prs: []
commits: []
cites: [§5.6]
related: [b-0bd346]
---

## Problem

Found in the spec loop's run 82, batch 102.

`SA-0419`'s REVIEW filed three blockers. REBUT's agent then exited 1 with
`api_error` and no output. The cell printed "the rebuttal moved no commit
and made no argument" and ended at `REBUTTAL_UNJUDGED` after $13.87. One
transient provider error decided the task. A person then judged all three
blockers by hand.

## Done looks like

A REBUT turn that exits on a provider error with no output is run again
once, while budget allows, before the task ends `REBUTTAL_UNJUDGED`. A
second failure ends it as today. A test stubs one failed turn and then a
rebuttal, and asserts the rebuttal is judged.

## Record

- 2026-11-22: filed from the spec loop's run 82.
- 2026-11-23: recurred in the spec loop's run 84. Batch 105's REBUT for `SA-0424` exited with code -6 and no result event. The task ended `REBUTTAL_UNJUDGED`, and the operator took it by hand as #1310.
