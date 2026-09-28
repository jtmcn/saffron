---
id: b-877e93
title: '`saffron cell` stacks a child on a merged parent''s stale branch, because it never reconciles'
status: open
tier: 1
filed: 2026-09-27
closed:
specs: []
prs: []
commits: []
cites: [§4.2]
related: [b-111c56, b-fab381]
---

## Problem

Found in the spec loop's run 19, 2026-09-27.

`SA-0178`'s cell, and `SA-0147`'s first, ran stacked on `saffron/SA-0159` at
`fd6513a6`. That branch had merged in run 18. No `reconcile` ran after the
merge, so the ledger still held `SA-0159`'s task in a waiting state.

`saffron/task.py:211-235` takes `depends_on[0]`'s newest task in
`DEPENDENCY_WAITING_STATES` and fetches its branch. It never asks whether that
branch merged. `saffron queue` reconciles first, and `saffron cell` does not.

The cell missed #535 and the `tests` gate fix from b-76f08d. Its baseline and
gates ran the old `.saffron/gates`. The `saffron/` code matched `main`, so the
diff still applied there.

## Done looks like

`saffron cell` reconciles the parent's pull request before it stacks. A parent
whose pull request merged is read from the default branch. A test covers a
parent the ledger reads as `READY_FOR_REVIEW` whose pull request merged.

## Record

- 2026-09-27: filed from the spec loop's run 19.
- 2026-09-27: worked around by hand. The loop driver's `snapshot` and `next` reconcile first (acd2f1f6). `SA-0186` is the fix in `saffron cell`.
