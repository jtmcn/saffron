---
id: b-4c5dc7
title: A budget stop after green does not stop REVIEW, so REBUT is refused and a one-line fix ends the task EXHAUSTED
status: open
tier: 1
filed: 2026-10-01
specs: [SA-0162, SA-0151]
prs: [626, 628]
commits: []
cites: [§3, §5.5]
related: [b-038aef]
---

## Problem

Found in the spec loop's run 24, 2026-10-01.

`SA-0162`'s cell printed `budget: $39.72 of $37.00 — stopping` once its gates
went green. REVIEW then ran four lenses and the wrong-version sweep, to
$57.36. The sweep found one witness blocker, and REBUT was refused on budget.
The task ended `EXHAUSTED`.

`SA-0151` went the same way: green at $21.31 of $25, REVIEW to $30.67, two
witness blockers, REBUT refused. Each blocker was a test fix of a few lines.

So the budget neither stops REVIEW nor leaves REBUT a share. The night pays for
the review and then cannot act on it.

## Done looks like

A green cell holds back REBUT's share before REVIEW starts. Or, out of
budget, it skips REVIEW and packages the green patch. A night never pays
for lenses it cannot answer.

## Record

- 2026-10-01: filed from the spec loop's run 24. Both cells were adopted by hand as #626 and #628.
