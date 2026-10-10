---
id: b-8a0c9a
title: "A stack batch's end review grades the packaged heads, before the loop's review commits"
status: open
tier: 2
filed: 2026-10-09
specs: []
prs: [789]
commits: []
cites: []
related: [b-792ab2, b-d96f14, b-f71105]
---

## Problem

Found in the spec loop's run 32, reading
`~/.saffron/batches/v0/finish/20/findings.json`.

The end review reads each layer's `pushed_sha` as the batch recorded it
(`saffron/end_review.py:84-131`). The delegate's review commits land after
PACKAGE, so the end review graded heads from before them. Of the twelve
findings it kept, most were already fixed on the branches by then. Examples
are the print-order blocker on `SA-0232`, the `_qualify_range` docstring on
`SA-0238` and the `_SNAPSHOT_SENTENCE` restatement on `SA-0229`.

Its two follow-ups cost $6.06 between them. `SA-0256` (#789) answered a point
the loop's review had made harder to change, and the operator closed it.
`SA-0257` ended `EXHAUSTED`. Two findings stayed real at the top head: the
test name `test_a_seed_whose_fetch_fails_twice_raises_after_two_attempts`
uses "attempts" (`tests/test_worktree.py:672`), and `_draft` hashes the spec
text by hand (`saffron/cli.py:1122` and `:1234`).

## Done looks like

The end review reads each layer's current branch head, or it runs only after
the loop's review commits land. A finding fixed on the branch is not pooled. A
test drives an end review over a layer whose branch moved after PACKAGE.

## Record

- 2026-10-09: filed from the spec loop's run 32.
- 2026-10-10: recurred in the spec loop's run 33. Batch 21's end review graded
  the packaged heads again. Seven of its eight findings were already fixed
  on the branches. The eighth became b-55186d.
