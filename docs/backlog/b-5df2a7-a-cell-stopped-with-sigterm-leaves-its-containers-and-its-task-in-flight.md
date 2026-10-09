---
id: b-5df2a7
title: "A cell stopped with SIGTERM leaves its containers and its task in flight"
status: open
tier: 2
filed: 2026-10-06
specs: [SA-0245]
prs: []
commits: []
cites: [§4.5]
related: [b-a1d649]
---

## Problem

Measured 2026-10-06. The operator stopped `SA-0218`'s first cell mid-REVIEW
with SIGTERM, because the parent it was stacked on had merged with new
commits. The process exited 143 and printed no teardown line.

- `saffron-cell-SA-0218`, `saffron-critic-SA-0218` and `saffron-proxy` kept
  running until they were removed by hand.
- Task 232 stayed `REVIEWING` in the ledger, and its run was never closed.
- The patch the cell had made was never exported.

`run_one_cell` closes the run `ABORTED` and stamps the task `ORPHANED` in an
`except BaseException`. It exports the patch and calls `cell_down` in a
`finally` (`saffron/cell/session.py:3205-3248`). Ctrl-C raises
`KeyboardInterrupt`, so both run. SIGTERM's default action ends the process
without raising, so neither does. No module under `saffron/` installs a
handler for it.

A stopped cell then holds the shared proxy and network. The next cell's
`start_proxy` removes them, but a task left in flight reads as live until a
batch's own scan stamps it `ORPHANED`. `CLAUDE.md` already warns that SIGTERM
discards a batch's log under launchd, which is the same signal reaching the
same unhandled default.

## Done looks like

SIGTERM to `saffron cell` or `saffron batch` raises inside the process. The
run then closes `ABORTED` and the task is stamped `ORPHANED`. The patch is
exported, and every container the cell created is removed. A test sends the
signal to a running cell and asserts all four.
