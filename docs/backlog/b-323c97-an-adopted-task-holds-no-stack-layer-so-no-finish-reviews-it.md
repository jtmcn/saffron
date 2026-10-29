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
