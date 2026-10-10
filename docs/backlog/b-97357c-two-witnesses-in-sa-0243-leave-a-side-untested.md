---
id: b-97357c
title: "Two of SA-0243's witnesses leave a side untested: the raise path's state, and whether reconcile reached the row"
status: open
tier: 3
filed: 2026-10-10
specs: []
prs: [795]
commits: []
cites: []
related: []
---

## Problem

Found by the seats on #795 in the spec loop's run 33. Both were cut from
the review commit to keep `SA-0243` within its `size` ceiling, at
1296 of 1300.

- **The re-seeded rows (`tests/test_task.py:377`):** the two
  broken-then-fixed tests start their rows at `READY_FOR_REVIEW`. Neither
  can tell whether the raise path wrote the state.
- **Criterion 1's witness (`tests/test_session.py:4551`):** it never
  asserts that reconcile reached the row. A repo-id miss would leave its
  reconcile step vacuous.

## Done looks like

- The re-seeded rows start at `REVIEWING`, and each test asserts the state
  the raise path wrote.
- Criterion 1's witness asserts that reconcile read the row.

## Record

- 2026-10-10: filed from the spec loop's run 33.
