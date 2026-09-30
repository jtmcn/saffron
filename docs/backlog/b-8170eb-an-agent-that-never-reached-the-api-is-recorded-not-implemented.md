---
id: b-8170eb
title: An agent that never reached the API is recorded `NOT_IMPLEMENTED`
status: open
tier: 1
filed: 2026-09-29
specs: [SA-0193, SA-0195]
prs: []
commits: []
cites: []
related: [173]
---

## Problem

Found in the spec loop's run 22, 2026-09-29.

Two IMPLEMENT sessions never reached the provider. They were `SA-0193`'s
second attempt (task 192) and `SA-0195`'s first (task 195). Each agent got
`API Error: Connection refused` on 10 of 10 `api_retry` events. The session
ended with `terminal_reason: api_error`, $0.00 spent and no commits.

`saffron cell` exited 1 and recorded `NOT_IMPLEMENTED`. That is a decided
state, so the loop's `next` passed the spec over. The delegate re-ran each
spec by path.

`error` is not `fail`. An agent that never reached the provider is an
infrastructure failure. Such a task exits 2 and is charged to nobody. The same
rule keeps `RATE_LIMITED` apart from `EXHAUSTED`.

Evidence: `~/.saffron/batches/v0/SA-0193/events.jsonl`, lines 48 to 50, from
the first run. The delegate kept `SA-0195`'s attempt 1 log.

## Done looks like

A session that ends `api_error` with no turn of work ends the task as an
infrastructure failure. `saffron cell` exits 2, and the ledger records no
`NOT_IMPLEMENTED`. A test drives such a session and reads both.

## Record

- 2026-09-29: filed from the spec loop's run 22.
