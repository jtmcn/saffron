---
id: 123
title: The spec review is blind to ceilings defects and raises ceilings blockers the outcome contradicts
status: open
tier: 3
filed: 2026-09-14
specs: [SA-0092]
prs: []
commits: []
cites: []
related: [124, 125]
---

## Problem

**Tier 3.** Found running the spec review's 2026-09-14 backtest.

- It missed every recorded ceilings defect: SA-0031, SA-0087@24edb32 and
  SA-0059 were marked `checked` or blamed on the wrong cause.
- It raised two ceilings blockers that the cells contradicted: SA-0060 and
  SA-0027 finished inside the ceilings it called too low.
- Evidence: `docs/evidence/2026-09-14-spec-reviewer-backtest.md`.

## Done looks like

check 4 either reads `history`'s peak and endings correctly on the recorded
cases, or is dropped from the spec review in favour of a deterministic
comparison in `driver.py history`.

## Record

**Filed 2026-09-14.**
