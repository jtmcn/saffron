---
id: b-d1c277
title: The queue's stack thresholds assume every earlier candidate ran, though a batch can pass one over
status: done
closed: 2026-11-09
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
- 2026-11-09: #1107 (`SA-0356`) landed the pass-over. Both PR seats and the in-cell contract lens found `_print_stack_admission`'s docstring premise now false (`saffron/cli.py:2259-2263`).
- 2026-11-09: done by hand. A measured order of siblings priced $10, $50 and $5 starts `SY-3` from $60 to $120, not at $140, and again from $162. So no least budget admits a layer for every budget above a lower figure. The printed figures stay, and the docstring now says each is the least budget from which every larger one starts its layer. A sibling test pins both facts.
