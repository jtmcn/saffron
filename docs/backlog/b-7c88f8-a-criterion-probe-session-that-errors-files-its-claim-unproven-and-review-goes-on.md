---
id: b-7c88f8
title: A criterion-probe session or probe cell that errors files its claim unproven, and REVIEW reaches READY_FOR_REVIEW as if no probe failed
status: partial
tier: 3
filed: 2026-09-22
specs: [SA-0371]
prs: [1158]
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
- 2026-11-11: hit in the spec loop's run 62. `SA-0369`'s gate-only cell
  stopped after its 26th criterion probe. The 9 probes after it, and all 37
  wrong versions, were filed `unproven`. No file names the error that
  stopped it. The task reached `READY_FOR_REVIEW`. The Spec seat then found 4
  witness blockers among those same wrong versions.
- 2026-11-11: `SA-0371` specs the probe cell's half. A stopped cell is
  entered once more, and an edit still unasked reads `error`. The REVIEW
  lines count it. A criterion-probe session that errors is left open.
- 2026-11-11: partial by `SA-0371` in #1158, from the spec loop's run 63. A
  probe cell that stops is entered once more, and every edit it still leaves
  unasked reads `error`. Both REVIEW lines count those edits. A
  criterion-probe session that errors still files its claim `unproven`.
