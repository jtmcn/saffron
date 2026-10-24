---
id: b-e39286
title: "`saffron finish` seeds a resumed tail's exempt set with the base's own branch only, so a deferred night's follow-ups are refused on a pull request on the base's chain"
status: open
tier: 2
filed: 2026-10-23
specs: []
prs: []
commits: []
cites: [§4.2.1]
related: [b-1572e7, b-8a0c9a]
---

## Problem

Found in the spec review of `SA-0312`, round 2.

`SA-0312` gives `StackBase` the branches of the base's chain, and
`run_stack_batch` exempts them in the set it seeds. `saffron finish` builds
a resumed tail's `StackResume.layer_branches` itself
(`saffron/cli.py:2514-2524`). It adds each layer's branch and the base task's
own branch, and none on the base's chain. So a deferred night's follow-up
that overlaps a pull request on that chain is refused there. The same
follow-up passes in a night that runs its tail at once.

`SA-0312` forbids `cli.py`, so it leaves this seed alone.

## Done looks like

`saffron finish` seeds the resumed tail's exempt set with the base's chain
branches too. A test drives a deferred finish whose follow-up overlaps a
pull request on the base's chain, and the follow-up is not refused.

## Record

- 2026-10-23: filed from `SA-0312`'s second spec review.
