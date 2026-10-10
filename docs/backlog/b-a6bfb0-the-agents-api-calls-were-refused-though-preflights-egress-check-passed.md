---
id: b-a6bfb0
title: The agent's API calls were refused though preflight's egress check passed
status: done
tier: 1
filed: 2026-09-29
closed: 2026-10-10
specs: [SA-0193, SA-0195, SA-0235]
prs: [793]
commits: []
cites: [§5.1.1]
related: [b-8170eb]
---

## Problem

Found in the spec loop's run 22, 2026-09-29.

The agent's calls were refused on 2 of 5 agent starts this run. Each time
preflight printed `proxy reaches api.anthropic.com (401)` about five minutes
earlier (`saffron/cell/session.py:938`). Baseline gate cells ran in between.
Gate cells create and remove networks (`saffron/cell/session.py:1188-1265`).

The first time, Colima's `limactl hostagent` held `*:53`.
`SAFFRON_ALLOW_HOST_PROCESS` tolerated it. Stopping Colima let the next run
through. The second time nothing held port 53.

No proxy log is kept on this path (`saffron/cell/proxy.py`). So the cause is
unknown.

## Done looks like

When the agent's first call is refused, the host reads the proxy container's
state and log. It also reads the cell's resolver and route. It does so before
teardown and reports all of them.

Preflight's egress probe runs from a cell started the way the agent's is
(Appendix I).

## Record

- 2026-09-29: filed from the spec loop's run 22.
- 2026-10-10: done by `SA-0235` (#793), from the spec loop's run 33.
