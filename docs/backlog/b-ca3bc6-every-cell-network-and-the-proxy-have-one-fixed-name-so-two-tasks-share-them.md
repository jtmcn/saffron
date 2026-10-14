---
id: b-ca3bc6
title: Every cell network and the proxy have one fixed name, so two tasks at once share them
status: done
closed: 2026-10-13
tier: 3
filed: 2026-10-01
specs: [SA-0269, SA-0270, SA-0271]
prs: [855, 856, 868]
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

## Record

- 2026-10-12: `SA-0269` ran in the spec loop's run 35 and ended
  `EXHAUSTED` at $41.03 of $36 after three gate attempts. Its branch is
  pushed with no pull request. `SA-0270` and `SA-0271` were refused for
  depending on it. The operator decides whether to rerun, split or drop it.
- 2026-10-12: the spec loop's run 36 stacked `SA-0269` as #855 and `SA-0270`
  as #856. Each task's networks and proxy are now named from the task, and its
  networks claim a /24 of a pool. `SA-0271` still owns the Gate-only cell and
  PACKAGE's re-verification, so the item stays partial.
- 2026-10-13: the spec loop's run 37 stacked `SA-0271` as #868 on `SA-0286`'s #867.
  The Gate-only cell, PACKAGE's re-verification and `saffron package`'s host
  probe now claim their networks from the subnet pool, and no cell sweeps
  another spec's network.
