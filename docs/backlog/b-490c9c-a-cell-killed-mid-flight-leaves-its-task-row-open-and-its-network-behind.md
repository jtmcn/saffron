---
id: b-490c9c
title: A cell killed mid-flight leaves its task row open and its network behind, so its spend reads zero and the next cell cannot start
status: open
tier: 2
filed: 2026-09-21
specs: []
prs: []
commits: []
cites: []
related: []
---

## Problem

Found in the spec loop's run 11, 2026-09-20.

The delegate stopped `SA-0113`'s first cell mid-IMPLEMENT on the operator's
instruction. The process died before it could record its own end.

- **The task row stayed open.** Task 119 reads `IMPLEMENTING` for good, and its
  `tasks.spent_usd_est` reads 0.00. Its two attempts carry $1.67 over 42 turns.
  Finished tasks 115 to 118 match their attempts exactly. Task 120, which failed
  on infrastructure, went `ORPHANED` correctly. So core closes a failure it
  observes, and not the death of its own process.
- **The network stayed behind.** Killing the cell skipped `cell_down`. The next
  cell failed with exit 2 on "network saffron-cells already exists", yet
  `container network inspect` answered "network not found" and delete failed too.
  Only a restart of the cell runtime cleared it. The guard in `cell_up` that
  removes a leftover network first (`saffron/cell/session.py:860-865`) could not
  remove this one either.

The open row does not block a re-queue. `build_queue` skips a spec only on a row
in `DONE_STATES` (`saffron/scheduler.py:777`). The cost is in the accounting:
anything that sums `tasks.spent_usd_est` under-counts a killed cell.

## Done looks like

A task row a dead process left in flight is closed, with its spend summed from
its attempts, at the next cell or at reconcile. A killed cell's network does not
stop the next cell from starting.

## Record

- 2026-09-21: filed from the spec loop's run 11 (task 119, task 120).
