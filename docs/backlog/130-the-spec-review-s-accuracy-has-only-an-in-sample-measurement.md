---
id: 130
title: The spec review's accuracy has only an in-sample measurement, and the reports step 1b now keeps were never pre-registered
status: partial
tier: 3
by_hand: true
filed: 2026-09-15
specs: []
prs: []
commits: [6855198e]
cites: []
related: [123, 124, 125, b-250dc7]
---

## Problem

**Tier 3.** Found planning how to re-measure the spec review after its
2026-09-14 backtest failed (PR #265).

- The only measurement is in-sample. The six checks were written and then
  tuned with the 34 cases and 10 controls in view
  (`docs/evidence/2026-09-14-spec-reviewer-backtest.md`, *Correction* and
  *Disclosures*). Scoring the same set again after items 123 and 124 are fixed
  shows whether the fixes worked, not whether the spec review is accurate.
- Step 1b of the spec loop already runs a spec review on every spec before its
  cell, so each report is blind and written before its outcome. But the report
  lives only in the loop's conversation, so nothing is left to score.
- A blocker the operator acts on changes the spec, and its cell then never
  shows the defect. A score that reads outcomes alone counts it as unconfirmed.
- **By hand.** Step 2 spends money on headless sessions, step 3's saving of
  reports is prose in the loop skill, and the pre-registration and the scoring
  are the operator's. A cell carries no credentials beyond its own agent token,
  so none of it can go through one. Item 123's other half can: `SA-0092`.

## Done looks like

three steps, in order.

1. Items 123 and 124 are fixed first. Both are done (124 on 2026-09-30).
2. An out-of-sample measurement, pre-registered in a new evidence file before
   the first round it counts. The file names these five things.
   - The bar.
   - A cutoff date. Only rounds after it count.
   - What outcome confirms a defect: terminal state, rejections, review
     commits, the ceilings the cell used.
   - How a blocker the operator acted on is judged: from the fix's reasoning,
     not the outcome.
   - A stopping rule: N specs or M recorded defects. Each counted round is copied
   into `docs/evidence/` and scored once its pull request is reviewed. The
   reviews are ones the loop already pays for.
3. Promotion to a spec-review cell is decided on the out-of-sample result
   alone.

The in-sample rerun this list once carried as step 2 is dropped with item 125.
It showed only whether the fixes worked, for about $80.

## Record

**Filed 2026-09-15.**

- 2026-09-30: step 1b keeps its reports now. Since 2026-09-21 the loop saves
  each spec-review round under `~/.saffron/batches/spec-loop/SA-NNNN/spec-review/`.
  Each round holds the spec, the report, its findings, the commit it read, and
  Jev's scores. By 2026-09-30 that is 77 rounds over 38 specs, and 73 carry the
  delegate's labels. Of 396 labelled findings, 335 read `real`, 42
  `not-a-defect` and 19 `unverified`. None of it was pre-registered, so it is a
  pilot for step 2 and not its measurement. The in-sample rerun is dropped
  with item 125, and steps renumber.
- 2026-09-30: step 2 is set up, not measured.
  `docs/evidence/2026-09-30-spec-review-out-of-sample-preregistration.md`
  proposes the five values. They take effect when its pull request merges.
