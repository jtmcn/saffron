---
id: b-3e0dbe
title: A crash between `reconcile`'s two writes strands the row in `unasked` for good
status: open
tier: 2
filed: 2026-09-19
specs: []
prs: []
commits: []
cites: [§4.2.1, §6.1]
related: [97, b-1c7019]
---

## Problem

Found by the spec loop's Spec seat reviewing #381, 2026-09-19, and by the
in-cell correctness lens as a note on the same diff.

`SA-0111` has `reconcile` write the merged head before it moves the state, so a
crash between them loses the second write rather than the first. That is the
right order, and it leaves a row that nothing recovers.

The two writes are separate transactions, each with its own commit
(`saffron/ledger.py`). A crash between them leaves `merged_head_sha` set while
the state is still in `PR_PENDING_STATES`. The next scan asks GitHub again.
Once the merged branch is deleted `_pr_status` returns `None`, so the row lands
in `unasked` on that scan and on every scan after it. It never reaches
`MERGED`.

The evidence to close the case is now on the row. A pending row carrying a
non-NULL `merged_head_sha` is a row GitHub already answered "merged" for. No
reader looks, because `SA-0111` deliberately shipped the write alone.

## Done looks like

`reconcile` treats a pending row with a recorded merged head as merged without
asking GitHub again, or the two writes share one transaction. Whichever is
taken, a witness drives the crash: the head written, the state not, then a
second `reconcile` against a `gh` that errors on the deleted branch.

## Record

- 2026-09-19: filed from the spec loop's run 10 (#381). The correctness lens
  called the non-atomicity benign and was right about the order. The stranding
  is what the order does not fix.
