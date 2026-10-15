---
id: b-4901d2
title: REBUT's verdict shares its cap with the fixes, so a task whose gates are green ends EXHAUSTED
status: open
tier: 1
filed: 2026-10-14
specs: [SA-0272]
prs: [875]
commits: []
cites: [§5.5]
related: [b-2750d5]
---

## Problem

Found in the spec loop's run 39, on `SA-0272`.

REBUT's sessions draw on one pool, `REBUT_CAP_USD`, set to $10. That figure
is the measured maximum of $9.29 on `SA-0223`. On `SA-0272` the implementer
fixed six of seven blockers in 41 turns for $6.41. Recording the fixes cost
$3.08. The gates re-ran with no new failures. The verdict lens then started
with $0.56 left, and ran out before it could answer.

The task ended `EXHAUSTED` at $41.29 of $36. Its code was sound, and PACKAGE
still opened draft #875. The operator had to decide what to do with it by hand.

## Done looks like

The verdict draws on money the fixes cannot spend, held back when REBUT starts.
A REBUT whose fixes use up their share still gets its verdict. A verdict that
runs out is reported apart from `EXHAUSTED`.

## Record

- 2026-10-14: filed from the spec loop's run 39.
