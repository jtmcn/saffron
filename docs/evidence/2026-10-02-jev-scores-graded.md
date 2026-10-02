# Jev's scores graded against the loop's labels

Read-only, on 2026-10-02. No call was made. Script in
`scripts/2026-10-02-jev-scores-graded.py`.

## What was graded

Jev scored each review round of the spec loop from 2026-09-21. Nothing read
those scores (`docs/superpowers/specs/2026-09-21-jev-review-observer-design.md`).
The delegate labelled the same review rounds by hand in `labels.json`. This
record joins the two for the first time.

`~/.saffron/batches/` held 229 `jev.ttl` files on this date. A review round
counts when it also holds `labels.json` and `findings.json`. That gives 153
review rounds, 88 of spec review and 65 of pull request review. Those rounds
hold 1065 labelled findings. The delegate read 952 as `real`, 70 as
`not-a-defect` and 43 as `unverified`. The 43 are left out.

AUC is the chance that a score ranks a positive case above a negative one.
A value of 0.5 is chance.

## Per finding

Each row tests whether a score separates `real` from `not-a-defect`.

| Score | Spec review | PR review | Both |
|---|---|---|---|
| Q2, probability of severity 0 (noise), inverted | 0.837 | 0.857 | **0.860** |
| Q2, expected severity | 0.813 | 0.841 | 0.826 |
| The reviewer's own severity | 0.697 | 0.682 | 0.687 |
| Q3, fixing it changes the outcome | 0.687 | 0.622 | 0.672 |
| Q1, probability of `noMatch`, inverted | 0.636 | 0.449 | 0.582 |

Q3 also reads 0.655 for a finding acted on against one left alone.

Q2 beats the reviewer's own severity. Its signal sits in the reviewer's notes.

| Reviewer severity | real | not-a-defect | Q2 noise AUC |
|---|---|---|---|
| blocker | 114 | 0 | n/a |
| concern | 325 | 7 | 0.565 |
| note | 513 | 63 | **0.866** |

Three cutoffs on Q2's noise probability:

| Cutoff | not-a-defect flagged | real flagged | real flagged and left alone |
|---|---|---|---|
| 0.3 | 47 of 70 | 99 of 952 | 45 |
| 0.5 | 38 of 70 | 28 of 952 | 17 |
| 0.7 | 12 of 70 | 5 of 952 | 2 |

At 0.5 the cutoff drops more than half the noise. It drops 11 real findings
that someone then acted on.

## Per review round

Q6 asks whether another review round would surface a blocker. Each label in
`blocker_followed` says whether a later stage did. The baseline counts the
blockers the review round itself raised.

| Review round | Label | n | Rate | Q6 AUC | Blockers AUC | Q6 Brier | Constant Brier |
|---|---|---|---|---|---|---|---|
| spec review | `next_spec_round` | 40 | 0.15 | 0.600 | **0.740** | 0.278 | 0.128 |
| spec review | `cell_review` | 61 | 0.41 | 0.697 | 0.556 | 0.230 | 0.242 |
| spec review | `pr_seats` | 65 | 0.75 | 0.721 | 0.622 | 0.239 | 0.186 |
| PR review | `cell_review` | 31 | 0.35 | 0.559 | 0.557 | 0.273 | 0.229 |
| PR review | `pr_seats` | 31 | 0.71 | 0.975 | **1.000** | 0.155 | 0.206 |

The constant Brier is the score of always answering the base rate. Q6 loses to
it in three of five rows. It wins one row by 0.012, and the last row is the
one below. Its answers span only 0.27 to 0.73.

The 0.975 is no forecast. On all 31 PR review rounds, `pr_seats` is true
exactly when that review round raised a blocker. The label reads the review
round itself.

For the next spec review round, the blocker count beats Q6.

## What could not be graded

- Q4 and Q5 have no label to grade against.
- No PR review round carries a Q4 answer, against 235 in spec review.
- No PR review round carries a boolean `next_spec_round`.

## Limits

- The delegate wrote every label by reading, not by outcome, and none was
  pre-registered. Item 130 already calls this set a pilot.
- 70 of 1022 graded findings are `not-a-defect`. One label moved changes an
  AUC in the second decimal place.
- The review round counts for Q6 are 31 to 65.

## What it says

Q2's noise probability is the one score worth keeping. It sorts the reviewer's
notes, and nothing else in the loop does that. Q6 adds nothing over a count
the loop already has. Q1 and Q3 are weak. Backlog item b-ef334d takes the
first half to a pre-registered test.
