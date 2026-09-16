---
id: 130
title: The spec review's accuracy has only an in-sample measurement, and step 1b keeps no report to score
status: open
tier: 3
by_hand: true
filed: 2026-09-15
specs: []
prs: []
commits: []
cites: []
related: [123, 124, 125]
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

four steps, in order.

1. Items 123 and 124 are fixed first. Measuring before then repeats the known
   FAIL.
2. An in-sample rerun, as a regression check. A new dated copy of the backtest
   script runs the shipped spec review on the same 29 versions, with controls at
   each cell's `tree_base` (item 125); the 2026-09-14 script stays as the record
   of what ran. The scoring rule, written down before the run, counts a blocker
   the outcome contradicted as false. The result is labelled in-sample and
   cannot promote. About $80.
3. An out-of-sample measurement, pre-registered in a new evidence file before
   its first report: the bar; what outcome confirms a defect (terminal state,
   rejections, review commits, the ceilings the cell used); how a blocker the
   operator acted on is judged (from the fix's reasoning, not the outcome); and a
   stopping rule (N specs or M recorded defects). Step 1b saves each report
   with its spec, base commit and cost under `docs/evidence/`, and each is scored
   once its pull request is reviewed. The reviews are ones the loop already
   pays for, about $2 each.
4. Promotion to a spec-review cell is decided on the out-of-sample result
   alone.

## Record

**Filed 2026-09-15.**
