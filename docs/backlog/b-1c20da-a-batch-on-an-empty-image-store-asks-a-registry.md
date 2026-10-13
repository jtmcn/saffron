---
id: b-1c20da
title: "A batch on a host whose cell runtime holds no images asks a registry for the proxy, and writes a task row for the failure"
status: open
tier: 1
filed: 2026-10-12
specs: []
prs: []
commits: []
cites: [§5.1.2]
related: []
---

## Problem

Measured in the spec loop's run 35, batch 23.

The cell runtime's image store was empty, so `saffron/proxy` was missing
too. Preflight passed. `container run` then asked Docker Hub for
`saffron/proxy` and got a 401. The batch exited 2 at $0. It left a
`GATE_ERROR` task row for `SA-0260`, which never started a cell.

The delegate built both images by hand and started batch 24.

## Done looks like

- Preflight reads the proxy image and the base image from the local store.
  A missing one refuses the batch and names the build command.
- No task row is minted for a batch that preflight refuses.

## Record

- 2026-10-12: filed from the spec loop's run 35, batch 23.
- 2026-10-12: the spec loop's run 36 hit the same class. Batch 25 started with
  the cell runtime's service stopped. `container network create` failed with an
  XPC connection error, the batch exited 2 at $0, and `SA-0269` got a
  `GATE_ERROR` row. Preflight never asked whether the service was up.
