---
id: b-ef334d
title: Jev's noise score sorts a reviewer's notes, and its stop signal adds nothing over a blocker count
status: partial
tier: 3
filed: 2026-10-02
specs: []
prs: []
commits: []
cites: []
related: [130, b-91ead2]
---

## Problem

`docs/evidence/2026-10-02-jev-scores-graded.md` graded Jev's saved answers
against the delegate's labels. It covered 1065 findings over 153 review rounds.

- Q2's probability of severity 0 separates a `real` note from a
  `not-a-defect` note at an AUC of 0.866. At a cutoff of 0.5 it flags 38 of 70
  `not-a-defect` findings and 28 of 952 `real` ones.
- Q6 loses to a constant answer on Brier score in three of five rows, and
  wins one by 0.012. Its answers span 0.27 to 0.73. For the next spec review
  round, the review round's own blocker count beats it.
- On a PR review round, `pr_seats` is true exactly when that round raised a
  blocker. Grading Q6 against it grades nothing.

The labels were written by reading and were not pre-registered. Nothing in the
loop reads `jev.ttl`, so the one useful score helps nobody yet.

## Done looks like

1. A pre-registration in `docs/evidence/` fixes the cutoff on Q2's noise
   probability, the findings it applies to and the bar it must pass. It
   follows the shape of `2026-09-30-spec-review-out-of-sample-preregistration.md`.
   Only review rounds scored after it merges count.
2. Q6 leaves `harness/jev_observe.py`'s questions, or the record says why it
   stays.
3. `labels.json` gives `pr_seats` a meaning a PR review round cannot answer
   from its own findings.
4. The pre-registered measurement is scored, and its result is recorded here.

## Record

- 2026-10-02: filed from the evidence record of the same date.
- 2026-10-02: Q6 dropped, schema-2 labels defined and the pre-registration
  proposed. Point 4 waits on the stopping rule.
