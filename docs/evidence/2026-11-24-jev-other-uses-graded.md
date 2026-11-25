# Jev's other answers graded, after its noise test failed

Read-only, on 2026-11-24. No call was made. Script in
`scripts/2026-11-24-jev-other-uses-graded.py`. Backlog item b-ef334d.

## Why this was run

The noise pre-registration (`2026-10-02-jev-noise-preregistration.md`) was
scored on 2026-11-22. `driver.py noise` printed `noise 59, caught 25, acted on
647, flagged 14: fail`. Q2 caught 42% of the noise against a bar of half.

Before the loop stopped calling Jev, this record asked whether any other
answer it saved could help spec writing, spec review or a cell. Every figure
below is exploratory. It reads the same review rounds the noise test scored,
and nothing here was pre-registered.

AUC is the chance that a score ranks a positive case above a negative one.
A value of 0.5 is chance.

## Spec criteria: Q7, Q8 and Q9

Jev asked three questions of each criterion in a spec review round. Q7 asks
whether it is testable as written. Q8 asks whether it names its evidence. Q9
asks whether it conflicts with another criterion. The October grading never
looked at them.

**Against a blocker from the PR seats on that criterion.** This used the last
spec review round of each spec. It covered 211 criteria over 41 specs, and 33
of them drew a blocker.

| Score | AUC |
|---|---|
| 1 minus Q7 | 0.478 |
| 1 minus Q8 | 0.499 |
| Q9 | 0.467 |
| Spec review findings citing the criterion | 0.610 |
| Criterion length | 0.697 |

All three questions sit at chance. Most of those blockers name a missing
witness, which is a defect of the work and not of the criterion.

**Against a rewrite in the next spec review round.** Q7 and Q8 came from
round N, and the outcome is a criterion whose text changed by round N+1. It
covered 399 criteria over 31 specs, and 41 were rewritten.

| Score | AUC |
|---|---|
| 1 minus Q7 | 0.726 |
| 1 minus Q8 | 0.571 |
| The same round's citations, weighted by severity | 0.827 |
| Criterion length | 0.783 |

Q7 carries some signal, and the reviewer's own citations beat it. Jev reads
that round's findings as part of its input, so Q7 is not independent of the
reviewer. Only 5 of the 253 criteria the reviewer never cited were rewritten.
That is too few to show Jev adds anything beyond the reviewer.

## A revision addressing a finding: Q5

Q5 asks whether a round's diff addresses an earlier finding. It is asked again
at every later round, so only the answer at round N+1 grades a round-N finding.
The outcome is the finding's label. `fixed-pre-cell` counts as addressed.
`no-action`, `deferred-to-seat` and `filed-backlog` count as left.

| Fixed | Left | AUC | Mean P(addressed), fixed | Mean P(addressed), left |
|---|---|---|---|---|
| 242 | 174 | 0.767 | 0.48 | 0.21 |

This is the one signal outside Q2's notes. It gives a fixed finding a 48%
chance of being addressed, so it cannot gate a step. The next spec review round
already checks each earlier finding. No label marks a writer who claimed a fix
and made none, which is the case Q5 would serve.

## Q2's noise score, by kind and severity

This compares Q2's probability of severity 0 for `not-a-defect` findings
against `real` ones. It covers every schema-2 labelled finding.

| Kind | Severity | Noise | Real | AUC |
|---|---|---|---|---|
| cell | blocker | 41 | 157 | 0.563 |
| cell | concern | 5 | 43 | 0.491 |
| PR review | note | 53 | 771 | 0.812 |
| spec review | note | 8 | 59 | 0.894 |

Rows with no noise, or with one noise finding, are left out.

- **A cell's REVIEW.** About one cell blocker in five was `not-a-defect`.
  Those cost REBUT turns, and some are withdrawn. Q2 sits near chance on them.
- **Reviewer notes.** The ranking held out of sample. The fixed 0.5 cutoff
  failed on catch. A new cutoff needs a new pre-registration on new review
  rounds, not this data. The spec review row rests on 8 noise notes.

## Ranking real findings

Among real findings, this compares the ones acted on against the ones left
alone.

| Kind | Acted on | Left | Q2 expected severity | Reviewer severity |
|---|---|---|---|---|
| PR review | 1215 | 135 | 0.759 | 0.722 |
| spec review | 65 | 27 | 0.802 | 0.754 |

Q2 reads the reviewer's severity as input, and about nine real findings in
ten are acted on anyway. The edge of 0.04 is no use to the loop.

## Never asked, so not graded

No saved answer bears on these uses inside a cell.

- Scoring the plan checkpoint.
- Triaging repair turns.
- Refereeing REBUT.
- Predicting `EXHAUSTED` before a cell runs.

Each faces the same constraints. A vendor call inside `run_task` needs an ADR
(`docs/superpowers/specs/2026-09-21-jev-review-observer-design.md`). No key
reaches a cell, so it runs host-side only. The state is cut at 85,000
characters, so a large diff loses its end. Jev returns probabilities with no
reasons, so it cannot explain a verdict.

## Limits

- Every label was written by the delegate, by reading.
- Each table reuses review rounds the noise test already scored.
- Criteria match across review rounds by exact text, so a reworded criterion
  counts as rewritten.
- The criterion length result is clustered: 33 blocked criteria over 41 specs.
- Jev's cost per review round was never measured.

## What it says

No saved answer beats what the loop already has where money is spent. Q5 has
a real signal, and the next spec review round already does its job. The loop
stops calling Jev and keeps saving and labelling each review round.
