---
id: b-ca3bc6
title: Every cell network and the proxy have one fixed name, so two tasks at once share them
status: open
tier: 3
filed: 2026-10-01
specs: []
prs: []
commits: []
cites: [§4.2.1, §5.1, §5.5]
related: [135, 108]
---

## Problem

Found reviewing #633, which closed item 135. Item 135's record said the fix
would derive its network and proxy names from the task. It did not.

`saffron-cells`, `saffron-critic-net` and `PROXY_NAME` are constants. So is
each subnet in `runtime.SUBNETS`. `cell_up` removes a network and the proxy by
name before it starts. A second task started beside a first would tear down
the first one's proxy and network partway through.

Batches run one task at a time today (§4.2.1), so nothing breaks yet. Two
things press on it. A by-hand `pytest -m cell` run during a spec loop's cell
does the same teardown to the loop's task. A cloud host at K above one would
put two tasks' implementer cells on one network. That is item 135's defect
between tasks.

Names alone do not fix it. Each network also needs its own subnet, so the
allocation in `runtime.SUBNETS` has to become per task too.

## Done looks like

Each task's networks, subnets and proxy are named from the task. Two tasks
brought up at once share none of them, and a cell-marked test starts two and
probes that neither reaches the other.
