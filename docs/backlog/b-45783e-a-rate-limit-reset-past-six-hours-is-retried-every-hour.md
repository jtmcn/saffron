---
id: b-45783e
title: A rate-limit reset past six hours is read as unknown, so a batch restarts the cell every hour until the window opens
status: open
tier: 3
filed: 2026-11-13
closed:
specs: []
prs: []
commits: []
cites: [§5.1]
related: []
---

## Problem

Found in the spec loop's run 66.

Batch 84 hit the weekly limit on `SA-0380` at $22.90. The provider said the
window reopens at 06:00 the next morning, about thirteen hours away.
`_wait_out_rate_limit` trusts a reset only when it is at most six hours off
(`saffron/batch.py:429`, SA-0148). Past that it waits one hour.

So the batch started `SA-0380` nine times overnight. Each start built the
cell image and booted the proxy, and each was rejected at $0. The log named
a new wrong reopen hour each time, such as 22:00, 23:04 and 00:08.

## Done looks like

A reset past six hours waits six hours, the cap, rather than one. The
emitted line names the provider's own reset beside the hour it will retry.

## Record

- 2026-11-13: filed from the spec loop's run 66.
