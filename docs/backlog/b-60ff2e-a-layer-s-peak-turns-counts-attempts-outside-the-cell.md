---
id: b-60ff2e
title: A layer's peak turns counts spec review and writing attempts, so the page can read 150 of 90 turns
status: open
tier: 2
filed: 2026-10-03
specs: [SA-0152, SA-0208]
prs: [650]
commits: []
cites: [§6]
related: [b-792ab2]
---

## Problem

Found by `SA-0152`'s correctness lens and #650's Spec seat in the spec
loop's run 26.

The stack view's `peak_turns` is the highest `num_turns` over every
attempt of the layer's task (`saffron/report/stack.py`, `_peak_turns`). A
stack batch also records `SPEC_REVIEW` and writing-phase attempts on that
task (`saffron/batch.py`). The page prints the peak against the spec's
`max_turns`, which bounds only the cell. The seat measured a 150-turn
`SPEC_REVIEW` attempt reading "150 of 90 turns".

The spec asked for every attempt, so the cell built it as written.

## Done looks like

A layer's peak reads only the attempts `max_turns` bounds, or the page
names each phase's peak beside its own bound.

## Record

- 2026-10-03: filed from the spec loop's run 26.
