---
id: b-708c8a
title: "`run_wrong_versions` restates `run_lens`'s re-prompt line for line"
status: open
tier: 2
filed: 2026-10-05
specs: [SA-0202]
prs: [675]
commits: []
cites: [§5.5]
related: [97, b-7251b5]
---

## Problem

Found reviewing #675, in the spec loop's run 28.

`SA-0202` gave `run_wrong_versions` one re-prompt on a malformed answer
(`saffron/phases/review.py:650-695`). It copies `run_lens`'s re-prompt
(`saffron/phases/review.py:272-318`). Both carry the rule that refuses a
retry with less budget than the failed turn spent. Both build the retry's
options, prompt with the error then `EXTRACTION_PROMPT`, and spell the same
two error prefixes. A change to one rule must be made twice, and nothing
fails when one copy is missed.

The fix was kept out of #675's review commit. It changes lens code that no
gate re-judges after the cell (item 97).

## Done looks like

One helper runs the re-prompt, and both callers use it. The existing
re-prompt tests for both callers pass unchanged.

## Record

- 2026-10-05: filed from the spec loop's run 28.
