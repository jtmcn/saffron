---
id: b-e0cd57
title: Preflight's N1 refusal names ports and not the processes behind them, and a start that fails preflight leaves an `ORPHANED` task row
status: open
tier: 2
filed: 2026-09-25
specs: []
prs: []
commits: []
cites: [§5.1, §4.1]
related: []
---

## Problem

Found in the spec loop's run 16, 2026-09-23, starting `SA-0140`.

The N1 refusal lists the addresses that answered from the cell, and nothing
else (`saffron/preflight.py:205-214`). The host listeners were RAATServer on
port 9200 and limactl on port 53. Preflight already reads them from `lsof`
(`saffron/preflight.py:43`, `:67`). The operator found the names by hand.

`SAFFRON_ALLOW_HOST_PROCESS` matches lsof's COMMAND column, which truncates
RAATServer to `RAATServe`. The allowlist needed the truncated name, and no
message says so.

Two starts failed before a cell existed. One met a stopped container
apiserver (XPC), and one met the N1 refusal. Each left an `ORPHANED` task row
for a task that never started.

## Done looks like

- The N1 refusal names each listener's process as `lsof` prints it, which is
  the spelling `SAFFRON_ALLOW_HOST_PROCESS` takes.
- A start that fails preflight or the cell runtime writes no task row, or a
  row whose state says it never started.
- A test covers each.

## Record

- 2026-09-25: filed from the spec loop's run 16.
