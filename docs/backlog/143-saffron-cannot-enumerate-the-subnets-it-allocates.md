---
id: 143
title: Nothing enumerates the subnets Saffron allocates, and the pre-clean is by name while the collision is by value
status: open
tier: 1
filed: 2026-09-16
by_hand: false
specs: [SA-0089, SA-0094]
prs: [282]
commits: []
awaiting: [305]
cites: [§5.1]
related: [118, 140]
---

## Problem

**Tier 1.** Found reviewing `SA-0089` (PR #282); the first half was caught before
its cell ran and cost a spec amendment.

Three subnets are declared in three files: `runtime.DEFAULT_SUBNET`
(`10.88.0.0/24`), `proxy.EGRESS_SUBNET` (`10.89.0.0/24`), and now
`_GATE_CELL_SUBNET` (`10.90.0.0/24`) in `session.py`. Nothing lists them, and
`create_network` raises `CellRuntimeError` on overlap — **at REVIEW, after
IMPLEMENT is paid for**, landing in `_drive_cell`'s `except BaseException` as
`ABORTED`/`ORPHANED`, exit 2, charged to nobody.

The spec review caught this before the cell: `SA-0089`'s notes named only the
`saffron-cells` holder and told the agent to "choose a non-overlapping subnet",
and `10.89.0.0/24` — the obvious next pick after reading `10.88.0.0/24` — is the
proxy's. The suite cannot see the collision, because `_stub_the_runtime` stubs
`create_network` to a no-op. The spec was amended to name both holders and
dictate `10.90.0.0/24`; the next cell that adds one has to redo that audit by
hand, from prose.

The second half is unfixed. `_gate_cell_suite` pre-cleans by **name**
(`saffron-gate-net-<spec_id>`), but the collision is by **value**. A SIGKILLed
run of a different spec leaves `saffron-gate-net-SA-00XX` holding
`10.90.0.0/24`, and the next task's REVIEW aborts the same way — the failure the
pre-clean exists to prevent, one name over.

## Done looks like

A `SUBNETS` tuple in `runtime.py` that every allocation draws from, a test that
the declared subnets do not overlap, and a pre-clean that removes by value —
`networks_on_subnet` already exists and is what the overlap error uses to name
the holder.

## Record

**2026-09-17, open as PR #305**, `SA-0094` in the spec loop's run 5 (stack
#308): `runtime.SUBNETS` declares each distinct subnet once, and the Gate-only
cell's pre-clean removes a `saffron-` holder of its subnet by value.
