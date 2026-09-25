---
id: b-7eb5f5
title: A same-night rerun leaves two baselines on one run, and qualification reads both
status: open
tier: 3
filed: 2026-09-25
closed:
specs: []
prs: []
commits: []
cites: [§4.4]
related: [b-792ab2]
---

## Problem

A stack batch reruns a `RATE_LIMITED` task on the same task and run
(`SA-0148`). Each cell records its pre-turn baseline under the run
(`saffron/cell/session.py:1762-1763`), and `baseline_results(run_id)`
returns every row (`saffron/ledger.py:1248-1249`). `SA-0147` reads the
layer's run baseline, so a rerun's two baselines double-cancel failure
identities.

## Done looks like

A baseline read returns the latest cell's rows, or each cell's baseline is keyed apart.

## Record

- 2026-09-25: filed from the spec reviews of `b-792ab2`'s last build specs.
