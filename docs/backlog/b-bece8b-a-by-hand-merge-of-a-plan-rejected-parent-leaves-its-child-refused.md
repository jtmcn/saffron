---
id: b-bece8b
title: A by-hand merge of a `PLAN_REJECTED` parent leaves its child refused, and `adopt` cannot record it
status: open
tier: 2
filed: 2026-11-04
specs: []
prs: []
commits: []
cites: [§4.2.1]
related: [b-323c97]
---

## Problem

Found by the spec loop's run 53.

`SA-0333`'s cell ended `PLAN_REJECTED`, and the delegate built it by hand in
#1014. After #1014 merged, the queue still refused `SA-0330`: "depends_on
SA-0333 is PLAN_REJECTED, which is not MERGED".

- `saffron adopt SA-0333 1014` refused it, since `PLAN_REJECTED` is not in
  `_ADOPTABLE_STATES` (`saffron/cli.py:2860-2862`).
- `saffron reconcile` reads only rows with a pull request, and this row has
  none.

The only way past was a PR that retired `SA-0333` to `done/` (#1015). That
cost a merge round-trip before the batch could run.

## Done looks like

A parent whose by-hand pull request merged satisfies its child's
`depends_on`, whatever state its own cell ended in. Either `adopt` takes a
`PLAN_REJECTED` row, or the queue reads a merged pull request that names the
spec.

## Record

- 2026-11-04: filed from the spec loop's run 53.
