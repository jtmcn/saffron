---
id: b-98a3be
title: The spec chain records no cost and no round per escaped defect, so no step can be cut on evidence
status: partial
filed: 2026-10-07
specs: [SA-0226, SA-0227, SA-0228, SA-0229]
prs: [745, 747, 781, 782]
commits: []
cites: []
related: [130, b-ef334d, b-8d5e55, b-0de0b3, b-43a061]
---

## Problem

The operator finds the spec chain too slow. The question is which step can go
without letting more defects reach a cell. The records answer half of it.

What is measured:

- The 2026-09-14 backtest caught 18 of 34 known defects, and 12 of 34 as
  blockers. It raised no false blocker on ten controls, with nine disputed.
  The checks were tuned on those cases, so recall is in sample.
- The delegate's labels read 15 of 15 blockers as real. They read 161 of 166
  concerns and 159 of 196 notes as real. The labels come from reading, not
  from outcomes.
- Over 41 specs in `~/.saffron/batches/spec-loop/`, the first review round
  found no real blocker or concern for only two of them.
- A real finding left alone came back in a cell review or a PR seat 22 to 26
  times in a hundred. The rate barely moved between rounds one, two and three.
- The chain records from 2026-09-21 to 2026-10-07 time each agent. A draft
  takes 9 to 36 minutes and a review takes 2 to 12. A revision takes 5 to 16.
- Second round findings mostly sit in text the revision added. The records for
  09-21, 09-22, 10-05 and 10-06 each say so.
- Escapes still happen. Two cells ended `PLAN_REJECTED` on size. The final
  whole-branch review of the run record view found four defects that every
  spec review and critic passed.

What is missing:

- No chain record states tokens after 2026-09-23. None states a dollar cost.
- No record says which review round raised a defect that a later stage
  confirmed. So nobody can tell what the second round buys.
- Item 130's out-of-sample bar is pre-registered and still unscored.

Every speedup on offer rests on those gaps. Scoping round two to the
revision's diff is one. Leaving notes alone is another, as is filtering them
by Jev's Q2 score. Replacing a third round with the wrong-version table is a
third.

## Done looks like

1. Each chain record states tokens and wall time for every writer, reviewer
   and delegate step. A script can produce it, as item b-0de0b3 asks.
2. Each defect confirmed under item 130's rule names the review round that
   raised it, or says no round did. It also says whether that finding was acted
   on.
3. Item 130's measurement is scored.
4. With 1 to 3 in hand, a dated entry here records the decision on three
   cuts. These are round two scoped to the revision's diff, notes left
   unrevised, and the two round stop rule. Each entry cites the counts behind
   it.

## Record

- 2026-10-07: filed from a read of the 2026-09-14 backtest, the 2026-10-02
  Jev grading, the chain records from 09-21 to 10-07, and the labelled rounds
  under `~/.saffron/batches/spec-loop/`.
- 2026-10-08: SA-0226 (#745) and SA-0228 (#747) landed in the spec loop's run
  31. A spec review's findings are rows, and the task page totals each
  phase. SA-0227 and SA-0229 wait on SA-0226 merging.
- 2026-10-09: `SA-0227` (#781) and `SA-0229` (#782) landed in the spec loop's
  run 32. `saffron draft` runs the spec chain as a task, and each session is a
  charged attempt. Points 1 to 4 still need the measurement, so the item stays
  partial.
