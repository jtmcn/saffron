---
id: b-0ac661
title: A fix to the plan checkpoint cannot pass the checkpoint it fixes
status: open
tier: 2
filed: 2026-11-04
specs: []
prs: []
commits: []
cites: [§5.3]
related: [b-15db6e]
---

## Problem

Found by the spec loop's run 53.

`SA-0333` fixed the plan checkpoint's pricing of test lines. Its own cell ran
under the unfixed checkpoint, which priced its 380-line plan at 1520 tokens
against `bug`'s 1300 at `elevated`. It ended `PLAN_REJECTED` at $1.57, and
the delegate built it by hand.

A cell always runs the host's checkpoint from the base, never the one its
diff writes. So a spec that loosens a checkpoint is judged by the rule it
replaces.

## Done looks like

A spec can say it changes a phase checkpoint, and the operator can then
run its cell with that checkpoint at `advisory`. Or the delegate's check
step names such a spec before its cell, so the by-hand path is chosen first.

## Record

- 2026-11-04: filed from the spec loop's run 53.
