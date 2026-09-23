---
id: b-111c56
title: A child waits on a parent that ended `EXHAUSTED` and then merged by hand, because the ledger never learns of the merge
status: done
tier: 3
filed: 2026-09-22
closed: 2026-09-23
specs: [SA-0123, SA-0124, SA-0131]
prs: [451, 459, 481]
commits: []
cites: [§5.7]
related: [b-4a63b7, b-e8027b]
---

## Problem

Found in the spec loop's run 14, 2026-09-22.

`SA-0123` ended `EXHAUSTED`, one line over its `size` ceiling. The operator
opened #451 by hand, the review brought it under, and #451 merged. The ledger
still read `EXHAUSTED` for the task. PACKAGE opened no pull request, so
`reconcile` had nothing to ask GitHub about.

Its child `SA-0124` then had a parent on `main` and could not start through
the loop's own tools.

- `driver.py next` printed "held back SA-0124: its parent SA-0123 is
  EXHAUSTED, so a cell would cut it from main".
- `saffron queue` refused it: "depends_on SA-0123 is EXHAUSTED, which will not
  merge as it stands".

Both read correctly before the merge and wrongly after it. The delegate
started `saffron cell` on the spec path, which does not check `depends_on`,
and the cell cut from `main`, which was correct.

## Done looks like

A parent whose work reached the default branch counts as merged, whatever
state its task ended in. A test covers a parent task that ended `EXHAUSTED`
and whose branch then merged.

## Record

- 2026-09-22: filed from the spec loop's run 14.
- 2026-09-23: `SA-0131` reached `READY_FOR_REVIEW` as #481 at $14.33 of $18,
  in the spec loop's run 15. `build_queue` now admits a child whose parent's
  recorded push reached the default branch. `SA-0131` retires to `done/`.
