---
id: b-54c8b4
title: The multi-parent stacking path ignores the rule that a merged or rejected newest row unstacks a parent
status: open
tier: 3
filed: 2026-10-24
specs: []
prs: []
commits: []
cites: [§4.2.1]
related: [b-1572e7]
---

## Problem

Found in the spec loop's run 47, while fixing `SA-0312` (#957) in review.

The single-entry path in `saffron/task.py` returns no stack base when a parent's newest
row is `MERGED` or `REJECTED`. The multi-parent path shares the row choice since review.
It does not apply that rule, so a merged parent can still count as open there. Nobody
probed it yet.

## Done looks like

Both paths apply one rule for a merged or rejected newest row, and a test drives the
multi-parent arrangement.

## Record

- 2026-10-24: filed from the spec loop's run 47.
