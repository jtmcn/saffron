---
id: 138
title: The loop's `size` measures a stacked branch against the default branch, so a child counts its parents' diff
status: open
tier: 2
filed: 2026-09-16
by_hand: false
specs: []
prs: [282]
commits: []
cites: [§5.4]
related: [40, 137]
---

## Problem

**Tier 2.** Measured on 2026-09-16 while reviewing `SA-0089` (PR #282).

`driver.py size SA-0089` reported:

```
SA-0089 since 51c2f3c3: 776 changed lines exceeds the feature ceiling of 600;
ask the operator (item 40)
```

`SA-0089` is stacked on `saffron/SA-0088`, and the count is taken from the merge
base with the default branch, so it included the parent's whole diff:

| measured from | changed lines |
|---|---|
| `main` (what `size` used) | 776 |
| `78dae0cd`, its real base | **477** |

477 + SA-0088's 299 = 776 exactly, and the in-cell `size` gate — which measures
from the tree the cell was actually cut from — recorded `477 changed lines within
the feature ceiling of 600`.

`SKILL.md` step 2c tells the operator to answer for a branch over its ceiling, so
the driver sends a false overrun for every stacked child, and the taller the
stack the worse it gets: `SA-0091` on `SA-0089` on `SA-0088` would triple-count.
The cost is not just noise — an operator who accepts one of these is accepting a
number that means nothing.

## Done looks like

`size` measuring from the base the cell used — the parent's branch head for a
spec with `depends_on`, which `task.py`'s `_stacked_on` already resolves and the
ledger records — rather than from the default branch.
