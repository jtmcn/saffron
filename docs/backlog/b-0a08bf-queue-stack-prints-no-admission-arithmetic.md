---
id: b-0a08bf
title: "`saffron queue --stack` prints no admission arithmetic, so nothing shows what `--budget` admits every layer"
status: open
tier: 2
filed: 2026-10-05
specs: []
prs: []
commits: []
cites: [§7.1]
related: []
---

## Problem

Measured in stage 2 of the delegate-loop plan, before batch 13.

`saffron queue --repo . --stack` prints candidates and refusals and nothing
else (`_queue` in `saffron/cli.py`). A `--stack` batch holds back two shares
of `--budget`. One is `end_review.RESERVE_SHARE`, 0.25
(`saffron/end_review.py:44`). The other is `follow_up.WRITER_SHARE`, 0.25
(`saffron/follow_up.py:32`). Each layer's spec review spends up to
`spec_review.SPEC_REVIEW_SESSION_USD` (`saffron/spec_review.py:56`) inside
the batch. That spend counts against the admission check at
`saffron/batch.py:243`.

The delegate's budget rule, total divided by 0.75, assumed one quarter held
back. At $138 it would admit about two of four specs. Nothing printed showed
it. Batch start does print "reserve $X, writer $Y" (`saffron/cli.py:1471`),
but only once the batch runs.

## Done looks like

`saffron queue --stack` prints, per candidate and in total, what `--budget`
must be for every layer to be admitted. The total counts both shares and each
layer's spec review.

## Record

- 2026-10-05: filed from stage 2 of the delegate-loop plan (the first live stack batches, batches 13 and 14).
- 2026-10-08: recurred in the spec loop's run 31. The delegate read
  `saffron/cli.py` to learn that `--stack` holds back half of `--budget`
  before choosing $320 for $157 of spec budgets.
