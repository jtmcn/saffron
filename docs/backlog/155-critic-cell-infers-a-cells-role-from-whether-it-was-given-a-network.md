---
id: 155
title: "`critic_cell` infers which cell it is building from whether it was handed a network"
status: open
tier: 3
filed: 2026-09-16
by_hand: false
specs: [SA-0093]
prs: [303]
commits: []
cites: [§5.1, §5.5]
related: [140, 142]
---

## Problem

**Tier 3.** Found by both review seats on `SA-0093` (#303), 2026-09-16.

`SA-0093` folded `_gate_cell_suite`'s lifecycle into `critic_cell`, which now
takes `network: str | None` and `env`. `network is None` decides three things
at once: that the cell makes and removes its own network, that it uses the
Gate-only cell's subnet, and that its container and volumes are named
`saffron-gate-*` rather than `saffron-critic-*`.

`CONTEXT.md` says a Gate-only cell "is not the critic cell, and the distinction
is the point", and half of that distinction is the environment, which is now a
separate argument. So `network=None, env=<proxied>` builds a container named
`saffron-gate-*` that routes through the proxy. And a future caller wanting a
critic cell on its own network would get Gate-only names, whose by-name
pre-clean could remove a live container of the other role.

Both callers are consistent today, and the preserved tests catch a caller
passing the wrong branch. The operator kept the shape for #303 (the spec named
`critic_cell` and asked for exactly `network: str | None`).

## Done looks like

The role is an explicit, keyword-only, default-free argument, and the names,
the subnet and network ownership derive from it rather than from `network`
being absent. Or the function is renamed so a Gate-only cell is not built by
something called `critic_cell`.

## Record

**Filed 2026-09-16** from the spec loop's run 5 (stack #308), kept rather than
fixed on #303 by operator decision.
