---
id: 138
title: The loop's `size` measures a stacked branch against the default branch, so a child counts its parents' diff
status: done
tier: 2
filed: 2026-09-16
closed: 2026-09-16
by_hand: false
specs: []
prs: [282, 287]
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

**Corrected after filing.** `cmd_size` does resolve a base below: `_own_base`
takes the branches `_bases_below` returns. The defect is that `_bases_below`
read the *order* and nothing else, and `SA-0088` had been held out of it by item
137 — so the list came back empty and the measurement fell through to the
trunk. The two items share a cause: the order is not a sound source for a
spec's parents, because a spec can be absent from it while its branch is real.
`depends_on` is on the spec itself and survives retirement to `done/`.

## Done looks like

`size` measuring from the base the cell used — the parent's branch head for a
spec with `depends_on`, which `task.py`'s `_stacked_on` already resolves and the
ledger records — rather than from the default branch.

## Record

**Filed 2026-09-16** from the spec loop's run of that day (stack #285).

**2026-09-16, a fix is open as PR #287.** `_bases_below` walks `depends_on` as well as the order, so a parent held out of it still supplies the base. It stays `open` until that merges.

**2026-09-16, done.** PR #287 merged (`1f64a99`). `_bases_below` walks
`_depends_on_chain` as well as the order (`driver.py:552-566`). Closed
2026-09-16 on review of the backlog: #287 wrote this record's "stays `open` until that merges" line itself, so the line could only land by the merge that should have closed it.
