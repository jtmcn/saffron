---
id: 135
title: The critic cell shares a network with the implementer's container, which is still running
status: open
tier: 2
filed: 2026-09-15
by_hand: true
specs: [SA-0087]
prs: [274]
commits: []
cites: [§5.5, §2]
related: [118, 127]
---

## Problem

**Tier 2.** Found reviewing `SA-0087` (PR #274), by reading the lifetimes; not
measured, and it may cost nothing.

`SA-0087` puts the critic cell on the task's existing network on purpose — the
network and proxy are the implementer cell's, already running, and the critic
cell must not start, stop or remove either. But the implementer's *container* is
not torn down when REVIEW begins: `cell_down` runs in `_drive_cell`'s `finally`,
after REVIEW has finished. So for the whole of REVIEW, a process the implementer
backgrounded during IMPLEMENT is alive on the same internal network as the
container the lenses re-exec their runner in.

The rootfs guarantee `SA-0087` buys is untouched by this — a new container's
rootfs is the image's. What is not established is whether anything in the critic
cell listens, or whether the agent runner in it can be reached from a peer on
that network. Until that is probed, the claim "the lenses run in a container the
implementer never had root in" is true about the filesystem and unproven about
the network.

Item 127 already owns the missing production-shaped isolation test; this is the
specific property that test would settle.

## Done looks like

a `cell`-marked test that backgrounds a listener in the implementer's container,
starts the critic cell the way production does, and probes from inside it —
either showing nothing is reachable, or moving the critic cell to its own
network with the proxy reachable from both.
