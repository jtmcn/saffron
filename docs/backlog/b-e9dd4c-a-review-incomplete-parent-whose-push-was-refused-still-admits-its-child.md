---
id: b-e9dd4c
title: A `REVIEW_INCOMPLETE` parent whose push was refused still admits its child
status: open
tier: 2
filed: 2026-10-30
specs: []
prs: []
commits: []
cites: [§4.2, §5.5]
related: [b-f603c9]
---

## Problem

Found by the first review of `SA-0330`.

`SA-0287` gave `REVIEW_INCOMPLETE` the same push and the same stacking as
`REBUTTAL_UNJUDGED`, and it left both gaps to b-f603c9 and b-af24d1. `SA-0330`
closes b-f603c9 for `REBUTTAL_UNJUDGED` alone.

So a child of a `REVIEW_INCOMPLETE` parent whose latest run pushed nothing is
still admitted. It is cut from `base_sha` when the row records no push. It stacks
on an older branch when a resumed row carries an earlier push.

`SA-0331` leaves a second gap. A resumed row that ends `REVIEW_INCOMPLETE` has its
push refused, and `reconcile` does not ask about it, so no merge moves it to
`MERGED`.

It leaves a third. A rerun beside another `REVIEW_INCOMPLETE` row with a pull request
still pushes onto that branch. `SA-0331`'s guard names `CHANGES_REQUESTED`, `APPROVED`
and `REBUTTAL_UNJUDGED`, and leaves this state out.

## Done looks like

`SA-0330`'s refusal reads `REVIEW_INCOMPLETE` too, through `tasks.pushed_in_state`.
A merged pull request on such a row moves it to `MERGED`.

## Record

- 2026-10-30: filed from `SA-0330`'s first review. The merge gap comes from
  `SA-0331`'s second review.
