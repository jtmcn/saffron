---
id: b-979dbe
title: The stack batch charges a spec session's attempt in three copies, and diffs one layer two ways
status: open
tier: 3
filed: 2026-09-30
specs: []
prs: []
commits: []
cites: []
related: [b-792ab2]
---

## Problem

Found in the spec loop's run 23, 2026-09-30, by #610's Standards seat.

- `saffron/follow_up.py`'s `_charge` is the third inline copy of the
  `open_attempt`/`close_attempt` block with
  `subtype="error" if ... else "success"`. The other two are in
  `saffron/batch.py`, at the revision wrapper and the review charge.
  `SA-0161` could not share it, because `ledger.py` and `spec_review.py`
  were forbidden.
- `saffron/end_review.py:249-254` reads a layer's `head^..head` through
  `mirror._git` with no pins. `follow_up._diff` reads the same range under
  `DIFF_FLAGS` and `worktree.git_argv`. One layer commit can then show two
  different patches.

## Done looks like

One helper charges a spec session's attempt, and every caller imports it.
`end_review` reads a layer's diff under the same pins a cell's diff carries.

## Record

- 2026-09-30: filed from the spec loop's run 23.
- 2026-10-09: #781's Standards seat found a fourth copy. `_charge` in
  `saffron/draft.py:129` repeats the body of `saffron/follow_up.py:254`.
