---
id: b-74e564
title: The stack batch restates the revise type, the budget-left sum and a phase name, and keeps a stale comment
status: partial
by_hand: true
tier: 3
filed: 2026-09-28
specs: []
prs: [1065]
commits: []
cites: [§4.4]
related: [b-792ab2]
---

## Problem

Found in the spec loop's run 20, 2026-09-28, by #566's seats (`SA-0164`). Line
numbers are at `82f0b1db`.

- The `revise` callable's type is written out in full at
  `saffron/batch.py:382-388`, `saffron/cli.py:763-765` and
  `saffron/cli.py:1222-1228`.
- `review` is typed `Callable[..., SpecReviewSession]` at `batch.py:376`,
  `cli.py:690` and `cli.py:1220`, so no argument is checked.
- The budget-left sum at `batch.py:570-574` restates `_drive`'s at `:232`.
  `SA-0173` adds a writer reserve and needs the sum in both places.
- Review attempts open with the literal `"SPEC_REVIEW"` (`batch.py:515`).
  Writer attempts use `spec_review.WRITING_PHASE` (`:594`).
- `batch.py:373-374` says `saffron batch` passes no `review`, and `_batch` now
  passes one.

## Done looks like

One alias names the `revise` type, and a `Protocol` types `review`. One helper
computes the budget left. A named constant holds the review phase. The stale
comment is gone.

## Record

- 2026-09-28: filed from the spec loop's run 20.
- 2026-11-08: partial by hand. The stale comment on `review` in
  `run_stack_batch` now names `_batch` and `_finish` as its callers. Left:
  the `revise` alias and the `review` `Protocol`, whose other sites are in
  `cli.py`. The review phase constant belongs beside `WRITING_PHASE` in
  `spec_review.py`, and `task.py` reads it. The budget-left helper needs its
  test in `test_batch.py`. Queued specs touch all four files.
