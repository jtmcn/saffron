---
id: b-7c88f8
title: A criterion-probe session or probe cell that errors files its claim unproven, and REVIEW reaches READY_FOR_REVIEW as if no probe failed
status: open
tier: 3
filed: 2026-09-22
specs: []
prs: []
commits: []
cites: [§5.4.1, §5.5]
related: [b-e40d09]
---

## Problem

Found reviewing ADR 4, 2026-09-22.

A lens that errors stops the task at `REVIEWING`. A criterion-probe session
that errors does not. `saffron/phases/review.py` returns its failure as an
entry with no edit. `_apply_criterion_probes` in `saffron/cell/session.py`
then files it `unproven`, the same as a session that named no edit.

- A probe cell that cannot be entered files every claim `unproven`.
- A runtime error part-way through the loop files every later claim
  `unproven`.
- `review_state` reads only the lenses' errors, so the task reaches
  `READY_FOR_REVIEW` on the partial set.
- The watch line counts a failed session as unnamed. Only the `error` field in
  `criterion-probes.json` tells the two apart, and nothing reads that file.

Principle 34 says absence renders as success in a schema that does not ask.
Principle 36 prefers one re-run to a consumer reading a truncated set.

## Done looks like

A criterion-probe error stops the task, as a lens error does. Or it reaches
the operator as an error distinct from `unproven`. A witness covers the chosen
behaviour.

## Record

- 2026-09-22: filed from ADR 4's review. ADR 4's principles 34 and 36 record
  it.
