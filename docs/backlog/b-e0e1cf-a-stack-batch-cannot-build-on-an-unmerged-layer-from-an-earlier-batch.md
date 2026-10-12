---
id: b-e0e1cf
title: "A stack batch cannot build on an unmerged layer from an earlier batch, so the operator merges a stack before the next batch runs"
status: done
tier: 2
filed: 2026-10-05
closed: 2026-10-12
specs: [SA-0265, SA-0267]
prs: [844, 846]
commits: []
cites: [§4.2]
related: []
---

## Problem

Measured in stage 2 of the delegate-loop plan, between batches 13 and 14.

After batch 13, `saffron queue --repo . --stack` refused `SA-0206` with
"depends_on SA-0205 is outside the stack order and not on the default
branch". `SA-0205`'s layer, #689, was `READY_FOR_REVIEW` and pushed. The
refusal comes from `_stack_dependency_reason` in `saffron/scheduler.py`
(`saffron/scheduler.py:793`). It accepts a parent only when the parent sits
in this batch's order or on the default branch.

The operator reviewed and merged the earlier stack before batch 14 could
run. The refusal named no such remedy.

## Done looks like

A stack batch can take a parent whose layer is a reviewable pull request from
an earlier batch, and stacks the new layer on it. Or the refusal names the
remedy: merge the parent's pull request first.

## Record

- 2026-10-05: filed from stage 2 of the delegate-loop plan (the first live stack batches, batches 13 and 14).
- 2026-10-12: `SA-0265` and `SA-0267` ran in the spec loop's run 35 as
  #844 and #846. A stack order takes an earlier batch's open pull request
  as its stack base, and a stack batch seeds, exempts and finishes on it.
  What review left is b-7ee599.
