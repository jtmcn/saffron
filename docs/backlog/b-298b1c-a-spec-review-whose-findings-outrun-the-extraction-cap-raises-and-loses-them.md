---
id: b-298b1c
title: A batch spec review whose findings outrun the extraction cap raises, and its findings are lost
status: open
tier: 2
filed: 2026-10-29
specs: []
prs: []
commits: []
cites: [§4.2.1]
related: []
---

## Problem

Found in the spec loop's run 50, on `SA-0326` in batch 59.

The batch's spec review of `SA-0326` finished in 105 turns for $3.81, with
at least one blocker on criterion 1's charging. Its first structured output
passed the findings as a string, and the tool refused it. The retry ran past
`SPEC_REVIEW_EXTRACT_BUDGET_USD`, which is $1.00
(`saffron/spec_review.py:52`). The batch printed "spec review for SA-0326
could not be read", raised, and ran no cell for the layer.

Nothing kept the review's text. The batch log cuts each agent line short,
and the `spec_reviews` row stores only the error. The second batch's review
of the same spec passed, so the blocker it found was never read.

## Done looks like

An extraction that fails keeps the review's prose where an operator can
read it. The extraction cap is measured against long findings blocks, or a
failed extraction retries once within a cap that covers one.

## Record

- 2026-10-29: filed from the spec loop's run 50.
