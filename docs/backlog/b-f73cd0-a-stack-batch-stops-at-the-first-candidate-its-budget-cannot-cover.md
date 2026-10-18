---
id: b-f73cd0
title: A batch stops at the first candidate its budget cannot cover, though a later one fits
status: open
tier: 2
filed: 2026-10-16
specs: []
prs: []
commits: []
cites: [§4.2.1]
related: [b-b24cf7]
---

## Problem

Found in the spec loop's run 42.

The loop's order named `SA-0275` and `SA-0294`. A `--stack` batch takes
every candidate a chain reaches, so batch 35 listed 16, with `SA-0284`
second. After `SA-0275`, $90 less the reserve, the writer's share and
$18.53 spent left $26.47. `SA-0284` needs $42, so the batch stopped with
`BUDGET` (`saffron/batch.py:256-263`). `SA-0294` needs $25 and never ran.

§4.2.1 says a batch ends when "the budget is gone". Here $26.47 was left
and a queued spec fit inside it. The stop reads the next candidate alone.

## Done looks like

The operator chooses one of two arms. A batch passes over a candidate its
budget cannot cover and offers the next one that fits. Or the stop names
the candidate it could not pay for, and what remained. In a stack, a skipped
layer's dependents are refused, as a missed layer's are.

## Record

- 2026-10-16: filed from the spec loop's run 42.
- 2026-10-17: recurred in the spec loop's run 43. A plain batch rescans into `SA-0276` after `SA-0284`. A `--stack` batch orders `SA-0294` behind 13 chained specs. The operator ran `SA-0294` as an attended cell first.
