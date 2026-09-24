---
id: b-6a692d
title: A critic cell cannot run beside a task cell, because every cell shares one network and one proxy
status: open
tier: 3
filed: 2026-09-23
closed:
specs: []
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
