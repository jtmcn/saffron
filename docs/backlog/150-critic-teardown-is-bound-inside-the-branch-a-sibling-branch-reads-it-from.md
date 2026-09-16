---
id: 150
title: The critic teardown closure is bound inside the REVIEW branch and read from the REBUT branch beside it
status: open
tier: 3
filed: 2026-09-16
by_hand: false
specs: [SA-0088]
prs: [277]
commits: []
cites: [§5.6]
related: [118]
---

## Problem

**Tier 3.** Found reviewing `SA-0088` (PR #277). Not a defect today — it cannot
fail — but it takes a dependency the file warns against two lines above.

`_critic_teardown` is defined inside `if outcome == "READY_FOR_REVIEW":` and used
from the sibling `if outcome == "REBUTTING":` branch. It is safe because
`"REBUTTING"` is produced nowhere but `review.review_state`, inside that same
block, so the `def` has always executed by then — Python has function scope, not
block scope.

The file sets the opposite convention immediately above, and says why:

> Pre-bound, not left to the branch below: `repair_loop` can hand back
> `EXHAUSTED` or `GATE_ERROR` directly, skipping REVIEW entirely, and the outcome
> at the bottom of this function must still be constructible.

`reviews` and `recorded` are pre-bound for exactly this hazard. The new code takes
it instead. `SA-0091` later added `reviewed_diff` and pre-bound it correctly, so
the file now does both.

Deferred at review time because the move is +9/−9 against one line of `size`
headroom on a `bug` ceiling — see item 40.

## Done looks like

The nine-line `def` moved above `if outcome == "READY_FOR_REVIEW":`, beside
`reviews` and `recorded`.
