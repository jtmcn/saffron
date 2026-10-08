---
id: b-fbd181
title: "A measured estimate priced two specs at half their landed size, and `size` only advised at `standard`, so both layers shipped over the ceiling"
status: open
tier: 2
filed: 2026-10-07
specs: []
prs: []
commits: []
cites: [§5.4]
related: [b-1e106d]
---

## Problem

Measured in the spec loop's run 30. `SA-0223` and `SA-0224` each set
`estimate_measured: true` from a prototype. `driver.py check` priced them at
1.0, so 415 and 434 lines read as 1660 and 1736 tokens. That is under 80% of
the feature ceiling of 3000, and `check` passed both.

The cells landed 3345 and 3309 changed tokens. The ledger's `size` results
failed every attempt of both. Both specs are `standard`, so `size` only
advised, and both packaged as `READY_FOR_REVIEW`. After review commits the
layers stood at 3616 (#733) and 3341 (#735). The operator kept them.

Most of the excess was test fixture code. The prototypes measured the code a
cell writes, not the witnesses a spec asks for.

## Done looks like

`check` prices a measured estimate against what landed for measured specs, as
it already does for unmeasured ones. Or the prototype counts its witnesses.
Either way, a spec that lands at twice its estimate shows in the check's ratio.

## Record

- 2026-10-07: filed from the spec loop's run 30 (#733, #735).
- 2026-10-08: recurred in the spec loop's run 31. All three specs set
  `estimate_measured: true`, so `check` priced each at 1.0. They landed at
  1.6x to 1.7x: SA-0226 at 1506 tokens against 924, SA-0225 at 2881 against
  1740, and SA-0228 at 943 against 564. SA-0225 ended 119 tokens under its
  ceiling.
