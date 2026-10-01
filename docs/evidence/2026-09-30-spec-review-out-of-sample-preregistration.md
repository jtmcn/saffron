# Spec review, out of sample: the pre-registration

**PROPOSED.** Every value below is a proposal. It takes effect when the
operator approves the pull request that adds this file. The cutoff is that
merge date. Backlog item 130, step 2.

## Why a second measurement

The 2026-09-14 backtest was in sample. Its six checks were tuned with the 34
cases in view (`2026-09-14-spec-reviewer-backtest.md`). Step 1b of the spec
loop now runs a blind spec review before every cell, and saves each round
under `~/.saffron/batches/spec-loop/SA-NNNN/spec-review/`. A round written
after the cutoff predicts an outcome nobody knew yet.

## The pilot, which counts for nothing

By 2026-09-30 the loop saved 73 labelled rounds over 38 specs. The delegate
labelled each finding by reading, not by outcome.

| severity | real | not a defect | unverified | real of those read |
|---|---|---|---|---|
| blocker | 15 | 0 | 0 | 1.00 |
| concern | 161 | 5 | 2 | 0.97 |
| note | 159 | 37 | 17 | 0.81 |

These labels grade the delegate's reading of each finding. They say nothing
about recall, since a defect the review missed carries no label. The bar below
reads outcomes for that reason.

## 1. The bar

The spec review passes on two counts, both required.

- **Recall.** It raises at least half of the confirmed defects, as a blocker
  or a concern. A note does not count as a catch.
- **False blockers.** At most one blocker in ten is judged no defect.

The recall figure matches the 2026-09-14 bar of 17 of 34.

## 2. The cutoff

Only a round whose report is written after the merge of this file counts. A
spec reviewed on both sides of the cutoff counts from its first round after it.

## 3. What confirms a defect

A defect is confirmed when the counted spec's own run shows it after the
spec review. Any one of these confirms it.

- The cell ends in a terminal state other than `READY_FOR_REVIEW`, and the
  cause traces to the spec.
- A line in `.saffron/rejections.md` names the spec.
- A review commit on the spec's pull request fixes something the spec caused.
- The cell used more than 90% of `max_turns` or `budget_usd`.
- A PR seat raises a finding the spec caused.

Each confirmed defect is matched against the report by file, or by criterion,
and by kind. The 2026-09-14 matching rule stands.

## 4. A blocker the operator acted on

A blocker the operator fixed before the cell cannot show its defect in the
outcome. It is judged from the fix's reasoning instead. The fix counts as a
confirmed defect when the change it made would have failed a criterion or a
gate. The fix counts as no defect when the operator records the change as
taste.

## 5. The stopping rule

Scoring ends at 20 counted specs or 30 confirmed defects, whichever comes
first. A hard stop falls on 2026-12-31 in case neither count arrives. Each
counted round is copied into `docs/evidence/` and scored once its pull
request is reviewed.

## What the result decides

Promotion of the spec review to a cell is decided on this result alone
(item 130, step 3). A fail keeps it in the loop as a pre-flight read.
