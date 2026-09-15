---
id: 120
title: REBUT gets whatever the task budget has left, and the halt it ends in reads as a corpse
status: open
tier: 1
filed: 2026-09-14
specs: [SA-0087, SA-0088, SA-0089]
prs: []
commits: []
cites: [§3.3, §4.2, §5.6]
related: []
---

## Problem

**Tier 1.** Found running the spec loop, 2026-09-14 (its second run).
`SA-0087`'s second cell went green on its first attempt at $8.64 of $14, and its
lenses spent $2.21 raising two anchored blockers. REBUT's cap is
`critic_budget(spec.budget_usd, spent)`: the remainder, floored at
`REVIEW_FLOOR_USD` (`saffron/cell/session.py:130`, passed at `:1767`). Here that was
$3.09, and the rebuttal session exhausted it with no output. `rebuttal.json` then
says "the rebuttal moved no commit and made no argument", the same words it would
use for an implementer that chose to say nothing. The task halts at `REBUTTING`,
as §5.6 intends (`DESIGN.md`, "earns nothing and halts at `REBUTTING`").
PACKAGE pushes the branch and opens no pull request. Three things read that halt
wrongly:

- `REBUTTING` is in `reconcile.IN_FLIGHT_STATES`, and §4.2's scan stamps any
  in-flight task `ORPHANED` before re-queueing it. The next queue therefore
  treats a deliberate halt as a crash.
- `DEPENDENCY_WAITING_STATES` (`saffron/scheduler.py:91`) excludes it, so a child
  cannot stack on a branch PACKAGE did push. This is why the operator dropped
  `SA-0088` and `SA-0089`.
- The spec loop's driver waits on it as a running cell
  (`docs/evidence/2026-09-14-spec-loop-skill-feedback-run-2.md`, observation 13).

## Done looks like

REBUT's budget decided on purpose, as a reserve or a ceiling
of its own, rather than inherited as a remainder. A rebuttal that ran out of
budget is reported as that. And `REBUTTING` after the cell exits is named as a
halt everywhere it is read, or gets the terminal state §5.6 says §3.3 lacks.
