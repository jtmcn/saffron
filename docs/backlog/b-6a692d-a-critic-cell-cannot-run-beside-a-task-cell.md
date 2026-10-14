---
id: b-6a692d
title: A critic cell cannot run beside a task cell, because every cell shares one network and one proxy
status: done
tier: 3
filed: 2026-09-23
closed: 2026-10-13
specs: [SA-0269, SA-0270, SA-0271]
prs: [855, 856, 868]
commits: []
cites: [§4.2, §5.1]
related: [b-792ab2]
---

## Problem

Found 2026-09-23 in `SA-0149`'s spec review. A stack batch wanted its spec
reviews to run beside the task cells, up to K at once.

The cell runtime cannot host that. Every task cell joins the fixed network
`saffron-cells` (`saffron/cell/session.py:1632`). `cell_up` removes that
network before it creates it (`:909`). `start_proxy` removes the singleton
proxy `saffron-proxy` (`saffron/cell/proxy.py:15`, `:54`), and `cell_down`
stops the proxy and removes the network (`session.py:1012-1013`). So a critic
cell started beside a task cell loses its route to the model when the task
cell starts or ends. `DESIGN.md` §4.2 already lists K > 1 as deferred.

So `SA-0149` reviews one spec at a time, right before its cell.

## Done looks like

Each cell gets its own network and proxy names, so a critic cell and a task
cell can run at once. A stack batch can then review the next spec while the
current cell runs.

## Record

- 2026-09-23: filed from `SA-0149`'s round-1 review.
- 2026-09-27: the spec loop's run 19 ran twelve cells one after another. The
  one shared proxy (`PROXY_NAME`, `saffron/cell/proxy.py:15`, removed first at
  `:54`) is also what blocks two independent layers of the spec DAG from
  running at once. `DESIGN.md` §4 holds K at 1, and N4 wants 3.
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
