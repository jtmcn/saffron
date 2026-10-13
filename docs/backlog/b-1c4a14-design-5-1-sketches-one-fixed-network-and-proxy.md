---
id: b-1c4a14
title: DESIGN.md §5.1 still sketches one fixed cells network on 10.88.0.0/24 and one fixed proxy
status: open
tier: 3
filed: 2026-10-12
specs: []
prs: []
commits: []
cites: [§5.1]
related: [b-ca3bc6]
---

## Problem

Found by the in-cell REVIEW and both seats on #855 and #856, in the spec loop's
run 36.

`DESIGN.md` §5.1 creates `saffron-cells` once with `--subnet 10.88.0.0/24` and
starts `saffron-proxy` on it at `10.88.0.2`. After #855 and #856, each task
names its networks and proxy from its spec id. Each network claims one /24 of
`runtime.SUBNETS["pool"]`, the /16 at `10.200.0.0`. Both specs forbade
`DESIGN.md` and left it to be edited by hand.

`CONTEXT.md` also uses "pool" for a batch's concurrency pool. The subnet pool
is a second sense of the word.

## Done looks like

§5.1's sketch shows per-task names and a /24 claimed from the pool. `CONTEXT.md`
either names the subnet pool or the code calls it something else.

## Record

- 2026-10-12: filed from the spec loop's run 36.
