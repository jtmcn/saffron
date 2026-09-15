---
id: 124
title: The spec review's "witness already green at base" check raises false blockers
status: open
tier: 3
filed: 2026-09-14
specs: []
prs: []
commits: []
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

## Done looks like

check 3 blocks only when it can name an existing test that already passes and
would serve as the witness; otherwise it is a concern.

## Record

**Filed 2026-09-14.**
