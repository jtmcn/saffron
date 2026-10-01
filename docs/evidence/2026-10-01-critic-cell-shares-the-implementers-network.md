# The critic cell and the implementer reach each other

Taken 2026-09-30 by hand, on the operator's Mac, apple/container 1.3.0. Item 135
asked whether a process the implementer leaves running can reach the critic cell.
It can, and the critic cell can reach it back.

## How

`scripts/2026-10-01-critic-cell-peer-reach.py` starts the implementer cell
through `session.cell_up` on `saffron-cells`. It then starts the critic cell
through `session.critic_cell` on the same network, as `_drive_cell` does for
REVIEW. Each cell runs a TCP listener on port 8135. Every connect is a Python
socket with a four-second timeout.

Principle 34 asks that a negative result rest on a probe that can succeed. So
each probe has a control: the same client against an address it must reach.

## What it returned

| Connect | Result |
|---|---|
| control: implementer to its own address | connected |
| control: critic to the proxy on 3128 | connected |
| critic to the implementer's listener | **connected** |
| implementer to the critic's listener | **connected** |
| listeners in a fresh critic cell | none |

The rootfs guarantee `SA-0087` bought still holds. The network gives the two
cells no separation in either direction.

## Why production does not close it

`reap_cell` runs only after a turn hits its wall (`saffron/phases/implement.py`).
A process the agent backgrounds in a turn that ends normally survives into
REVIEW. Reaping before REVIEW would not settle it either. REBUT resumes
implementer turns in the same container while its verdict-lens cell is up.

The exposure today is narrow, because a fresh critic cell listens on nothing.
The claim that the lenses run apart from the implementer is still false of the
network.

## Two findings on the way

`runtime.container_ip` misreads a cell. A cell's `inspect` output carries
`HTTP_PROXY=http://10.88.0.2:3128` in its env. The regex takes the first address
in the subnet, so it returns the proxy's. Production calls it only on the proxy.
A test that calls it on a cell gets the wrong answer in silence. The script reads
each cell's address from inside instead.

A host listener on a non-loopback port blocks every cell start, as N1 intends.
Roon's `RAATServer` on `*:9200` did so twice, once on each day. It relaunches
on its own, so quitting it once does not clear the host.

## What it means for the fix

The critic cell moves to a network of its own (item 135, option A). The proxy
joins it as a third leg. `start_proxy` already creates the proxy on two networks
in one call, so a third adds no new runtime spelling. Item 108 measured a
dual-homed squid on podman, so the cloud host has the same mechanism.

Two properties stay unmeasured and belong in the test that lands the fix. The
proxy must refuse a `CONNECT` to the other internal network. `container_ip` must
return the proxy's address on the critic's subnet.

On a podman host no VM wraps each cell, so this separation carries more weight
there. Both options assume one task at a time, `saffron-cells` and `PROXY_NAME`
are fixed names, and K above one needs per-task names. Option A should derive
its names from the task now.
