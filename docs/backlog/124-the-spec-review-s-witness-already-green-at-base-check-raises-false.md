---
id: 124
title: The spec review's "witness already green at base" check raises false blockers
status: done
tier: 3
by_hand: true
filed: 2026-09-14
closed: 2026-09-30
specs: []
prs: []
commits: ["bd2bee54"]
cites: []
related: [123, 125]
---

## Problem

**Tier 3.** Found running the spec review's 2026-09-14 backtest.

- It flagged SA-0061, SA-0054 and SA-0055 because the behaviour a criterion
  names already exists at base.
- Each cell passed with `criteria` and `revert` blocking, so the witnesses it
  wrote failed at base. The claim confuses behaviour that exists with a
  witness that passes.
- Two of these recur at the cells' real bases.
- **By hand.** The check is prose in `.claude/agents/spec-reviewer.md`. No test
  fails before a prompt is reworded and passes after, so a criterion here has
  no honest witness and a cell cannot land it.

## Done looks like

check 3 blocks only when it can name an existing test that already passes and
would serve as the witness; otherwise it is a concern.

## Record

**Filed 2026-09-14.**

- 2026-09-30: check 3 now blocks only on a named test that already passes at
  `base`. Behaviour that exists at base is a concern. The spec writer and the
  loop skill already treat the old shape as a forecast, and that stays true.
