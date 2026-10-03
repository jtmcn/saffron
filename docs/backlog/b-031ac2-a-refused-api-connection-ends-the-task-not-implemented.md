---
id: b-031ac2
title: A refused API connection ends the task `NOT_IMPLEMENTED`, exit 1, as if the task failed
status: open
tier: 1
filed: 2026-10-03
specs: [SA-0152]
prs: [650]
commits: []
cites: [§4.3, §5.1]
related: [b-d4e015, b-209696]
---

## Problem

Found in the spec loop's run 26, on `SA-0152`'s first cell.

Preflight reached `api.anthropic.com` through the proxy twice, from both
networks. The PLAN session then logged ten `api_retry` events and "API Error:
Connection refused". It ended `success/api_error` at $0.00. The cell recorded
`NOT_IMPLEMENTED` with no commits and exited 1.

Exit 1 means the task did not make it. A connection the network refused
says nothing about the task, so exit 2, infrastructure, is the honest code.
`driver.py next` treats `NOT_IMPLEMENTED` as decided, so the delegate
re-ran the spec by path. The re-run went green and reached #650.

An unattended night reads the same state as a task that failed on its
merits, and moves on.

## Done looks like

A session that ends `api_error` with no turn the agent completed is
infrastructure. The cell exits 2, and the task's state says the provider
was unreachable, never that the task was not implemented.

## Record

- 2026-10-03: filed from the spec loop's run 26.
