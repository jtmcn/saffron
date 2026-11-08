---
id: b-d1c277
title: The queue's stack thresholds assume every earlier candidate ran, though a batch can pass one over
status: open
tier: 2
filed: 2026-11-08
specs: []
prs: []
commits: []
cites: [§4.2.1]
related: [b-f73cd0]
---

## Problem

Found writing `SA-0356`, in the spec loop's run 55.

`SA-0356` lets a batch pass over a candidate its budget cannot cover. The
`saffron queue --stack` admission lines are built by `_print_stack_admission`
(`saffron/cli.py:2121-2153`). They price each layer as if every earlier
candidate had spent its own `budget_usd`. Its docstring says so at
`saffron/cli.py:2124-2126`. Once a candidate can be passed over, a spec that
reaches no earlier one is admitted by a smaller budget than the line prints.
The printed figure stays sufficient, but it is no longer the least one.

## Done looks like

Each threshold line names the least budget that admits its layer, counting the
candidates a batch passes over. The docstring says what the code computes.

## Record

- 2026-11-08: filed from `SA-0356`'s spec writer and its first review.
