---
id: b-2f4746
title: "A stack batch at a layer's admission threshold drains with spend over its allowance"
status: open
tier: 2
filed: 2026-10-11
specs: []
prs: []
commits: []
cites: [§7.1]
related: [b-0a08bf]
---

## Problem

Measured by the Spec seat on #822 (`SA-0254`), in the spec loop's run 34.

`saffron queue --stack` now prints the `--budget` that admits each layer.
At `--budget 92` over the three-layer fixture, the batch spent $54 against
a $46 allowance. `_drive` checks admission before a candidate and runs no
comparison after its own spec review and cell (`saffron/batch.py:184`). So
the reserve and writer shares absorb the overrun.

The printed total is what keeps both shares whole. Nothing makes the shares
a hard floor.

## Done looks like

The operator decides whether the reserve and writer shares are a floor. If
they are, a layer whose spend would cross into them is not started, and a
test drives a batch at the threshold. If they are not, `CONTEXT.md` and the
printed block say a layer can spend into them.

## Record

- 2026-10-11: filed from the spec loop's run 34 (#822).
