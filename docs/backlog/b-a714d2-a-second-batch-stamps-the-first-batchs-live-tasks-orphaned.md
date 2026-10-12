---
id: b-a714d2
title: A second batch stamps the first batch's live tasks ORPHANED, because nothing enforces one batch at a time
status: open
filed: 2026-10-11
specs: []
prs: []
commits: []
cites: [§4.2.1]
related: [b-ca3bc6, b-6a692d, b-d9ed45]
---

## Problem

Found 2026-10-11 while listing what blocks two cells on one host.

`_batch` resolves its queue with `stamp_orphaned=True` (`saffron/cli.py:1809`).
Its docstring states the premise: one batch runs at a time, so an in-flight
row is a corpse. `reconcile` then sets every row in `IN_FLIGHT_STATES` to
`ORPHANED` (`saffron/reconcile.py:195-198`).

Nothing enforces the premise. No lock, lease or process check guards it. So a
batch started while another batch or a by-hand `saffron cell` runs in the same
repo stamps that live task `ORPHANED`.

`ORPHANED` is in `REQUEUE_STATES` (`saffron/scheduler.py:111-119`). The second
batch can pick the same spec and start its cell. That cell's pre-clean removes
the first cell's container and volumes by name (item b-d9ed45).

## Done looks like

An in-flight task carries proof that its owner is alive, such as a pid and
host or a heartbeat. `reconcile` stamps `ORPHANED` only on a row whose owner
is gone. A test starts a second batch scan beside a live task and asserts the
task keeps its state.

## Record

- 2026-10-11: filed from the parallel-cells survey, beside b-ca3bc6.
