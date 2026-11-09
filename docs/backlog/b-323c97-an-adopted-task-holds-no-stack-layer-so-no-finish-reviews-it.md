---
id: b-323c97
title: An adopted task holds no stack layer, so its batch's finish refuses and no end review reads it
status: open
tier: 2
filed: 2026-10-29
specs: []
prs: []
commits: []
cites: [§5.7]
related: [b-8826cf]
---

## Problem

Found in the spec loop's run 50.

`SA-0325` ended `EXHAUSTED` in batch 59, so the batch recorded no layer for
it. The operator chose a hand fix, and `saffron adopt SA-0325 989` moved
the task to `READY_FOR_REVIEW`. Then `saffron finish 59` refused with
"batch 59 holds no layer". So #989 reached the stack with no end review.
Batch 60's finish read only its own layer, `SA-0326`.

## Done looks like

An adopted task that came from a stack batch is a layer of that batch, so
its finish reads it. Or `adopt` says the task will get no end review.

## Record

- 2026-10-29: filed from the spec loop's run 50.
- 2026-11-04: recurred in the spec loop's run 53. `SA-0330`'s cell ended
  `EXHAUSTED`, and `adopt` moved it to `READY_FOR_REVIEW` on #1016. Then
  `saffron finish 66` refused with "batch 66 holds no layer", and its $47.50
  reserve went unspent.
- 2026-11-09: recurred in the spec loop's run 56. `SA-0353` ended `EXHAUSTED` and was adopted on #1099. `saffron finish 73` did not refuse this time. It graded `SA-0354`'s layer against `SA-0355`, so `SA-0353`'s whole diff read as `SA-0354`'s. That raised eight false out-of-`touches` blockers. Six were pooled and two became follow-ups.
