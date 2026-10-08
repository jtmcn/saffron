---
id: b-60a399
title: "An infrastructure error while seeding a layer's cell marks the layer missed, so the batch refuses its descendants"
status: open
tier: 1
filed: 2026-10-05
specs: [SA-0234]
prs: []
commits: []
cites: [§4.4, §7]
related: [b-6ac0cd]
---

## Problem

Measured in stage 2 of the delegate-loop plan, in batch 13.

`SA-0206`'s spec-review cell raised `CellRuntimeError: seeding the worktree
failed` (`saffron/cell/worktree.py:108`). Git reported "unable to open loose
object ... Permission denied". `run_stack_batch` in `saffron/batch.py`
catches a raise from `review` at `saffron/batch.py:563`. It sets the task
`GATE_ERROR` and records the spec in `missed` (`saffron/batch.py:573`).
`resolve_prefix` then refuses each descendant that reaches a missed spec
(`saffron/batch.py:514`). The log read "SA-0207 refused reaches SA-0206".

A raise from `runner` takes the same path (`saffron/batch.py:730`). Only a
`RATE_LIMITED` or `PROVIDER_UNREACHABLE` outcome stays out of `missed`.

The plan (`docs/superpowers/plans/2026-10-03-delegate-loop-onto-the-stack-batch.md`,
Review Focus 1) expects an infrastructure state here. It rules out a missed
layer that refuses its descendants.

## Done looks like

An infrastructure error on a layer leaves its descendants runnable, either
retried in the same batch or offered again in a later one. The batch reports
the layer as infrastructure, not as missed. A test raises `CellRuntimeError`
from `review` and reads the descendant back as a candidate.

## Record

- 2026-10-05: filed from stage 2 of the delegate-loop plan (the first live stack batches, batches 13 and 14).
