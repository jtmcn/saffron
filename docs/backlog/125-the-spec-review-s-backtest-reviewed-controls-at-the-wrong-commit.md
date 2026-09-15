---
id: 125
title: The spec review's backtest reviewed controls at the wrong commit
status: open
tier: 3
filed: 2026-09-14
specs: []
prs: []
commits: []
cites: []
related: [123, 124]
---

## Problem

**Tier 3.** Found running the spec review's 2026-09-14 backtest.

- Controls were reviewed at the spec's last-touch commit, not at the base
  their cell ran on (`tree_base` in the batch tree's `patch.json`).
- Four dependency blockers were artifacts of that choice (SA-0062, SA-0061,
  SA-0054, SA-0040). None recurred when those controls were reviewed at their
  real bases; SA-0054, a stacked child, needed its parent's tree plus its own
  spec.

## Done looks like

a second backtest selects each control's version from its cell's recorded
base, and scores against outcomes as well as the literal rule (the operator
ruled outcome-contradicted blockers false).

## Record

**Filed 2026-09-14.**
