---
id: b-6a692d
title: A critic cell cannot run beside a task cell, because every cell shares one network and one proxy
status: open
tier: 3
filed: 2026-09-23
closed:
specs: [SA-0269, SA-0270, SA-0271]
prs: []
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
