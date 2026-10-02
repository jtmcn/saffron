---
id: b-d4e015
title: 'The idle bound kills a PLAN session that is still writing, and the ledger reads $0.00'
status: open
tier: 1
filed: 2026-10-02
specs: [SA-0167]
prs: [638]
commits: []
cites: [§5.1, §5.3]
related: [b-4c5dc7]
---

## Problem

Found in the spec loop's run 25, 2026-10-02.

`SA-0167`'s first cell ended `NOT_IMPLEMENTED` at PLAN. Its events show
the agent working for 1076 seconds. The gaps between events grew to 57, 75,
146 and 150 seconds. The last gap, after a `thinking` event at about 100k
tokens of context, reached exactly 300 seconds, and `IDLE_TIMEOUT_S` killed
the session (`saffron/cell/runtime.py:177`).

`images/agent_runner.py` emits whole messages only. A long assistant message,
such as a plan written in one tool call, reads as silence until it completes.
That is the likely cause, and it is inferred rather than measured.

The ledger then recorded $0.00, because no result event arrived, though
18 minutes of PLAN tokens were spent. `driver.py next` also treats
`NOT_IMPLEMENTED` as decided, so the re-run started by path. The re-run
went green and reached `READY_FOR_REVIEW` as #638.

## Done looks like

A session that is still producing tokens is never cut by the idle bound.
The runner streams partial messages, or emits a heartbeat while a message
is in flight. A session cut without a result event records the cost it
reached.

## Record

- 2026-10-02: filed from the spec loop's run 25.
