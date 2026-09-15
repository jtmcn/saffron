---
id: 29
title: Nothing recorded that a task merged, measured against this repo's own ledger
status: done
tier: null
closed: 2026-08-30
specs: [SA-0019]
prs: [70]
commits: []
cites: [§3.3, §4.2.1, §4.5]
related: []
---

## Problem

`SA-0019`. `set_task_state` is the only writer of `tasks.state`, and PACKAGE's
last word is always `READY_FOR_REVIEW` — nothing asked GitHub what happened
after, though §3.3 draws arrows onward to `MERGED`/`REJECTED`/
`CHANGES_REQUESTED`/`APPROVED`, and a dead batch scan leaves `ORPHANED`.

**A corpse was never stamped either**, per §4.2.1's own premise: "in flight"
and "dead" are synonyms only inside a batch scan, which v0.5 has none of —
the only candidate caller is `saffron queue`, run at will, mid-phase
included. A first attempt (`EXHAUSTED` at $12.12) stamped every in-flight
row unconditionally and was correctly blocked: `ORPHANED` is in
`scheduler.REQUEUE_STATES`, so a live row stamped that way is handed back
out as resumable — a second cell on the same branch.

**One live-task path is left open deliberately, and `SA-0020` must close it
before a scan gets teeth.** The in-flight guard protects a first run for a
structural reason — `pr_url` is NULL until PACKAGE's last write, so there is
nothing to ask about. A *resumed* task escapes it. `_drive_cell` writes
`READY_FOR_REVIEW` and calls `finish_run` before `cli._run_cell` invokes
PACKAGE, so while PACKAGE runs the row reads `READY_FOR_REVIEW` and still
carries the **previous** attempt's `pr_url`, whose `reviewDecision` is the
`CHANGES_REQUESTED` that requeued it. Reconciling inside that window writes a
`REQUEUE_STATES` value onto a task whose cell is alive — the same double
-execution shape the first attempt was blocked for, arriving by the other
column. Harmless in v0.5: no scan starts a cell, and PACKAGE's
`set_task_package` overwrites the row moments later. **Done looks like** the
state being stamped out of `PR_PENDING_STATES` before PACKAGE is called
(`cli.py` owns that ordering), not a wider guard inside `reconcile` — the row
is genuinely `READY_FOR_REVIEW` in that window, so no state test can tell it
from a finished one. Note `runs.status = 'RUNNING'` is a liveness signal the
ledger already carries and no forbidden file owns; it does not close *this*
window, because `finish_run` precedes PACKAGE.

## Record

**Status:** **done**, 2026-08-30, driven from `SA-0019` (PR #70) — the
item's own closure paragraph is below.

**Measured, 2026-08-30:** `select task_id,spec_id,state,pr_url from tasks
where pr_url is not null` against this machine's ledger returned six rows,
every one `READY_FOR_REVIEW`. Cross-referenced against this repo's own
`git log --all --oneline --merges`:

| spec | pull request | ledger said | `gh` says |
|---|---|---|---|
| `SA-0013`..`SA-0017` | #51, #56, #59, #60, #64 | `READY_FOR_REVIEW` | `MERGED` |
| `SA-0018` | #65 | `READY_FOR_REVIEW` | still open |

Five of six were wrong, with no mechanism that could make them right.

**Done, 2026-08-30.** `saffron/reconcile.py`'s `reconcile()` — a writer
inverting `scheduler._open_prs`'s best-effort shape (an untrustworthy `gh`
answer counts as "could not be asked", never "not merged"; `MERGED` is never
asked again) — wired into a new `saffron reconcile --repo .` and into
`saffron queue` before it scans. Neither asserts §4.2.1's batch-scan premise,
so neither stamps `ORPHANED`; the supervisor still does, on the path it
already owned (`cell/session.py`, §4.5). **What has no writer is the scan's
half** — the corpse a hard kill or a power cut leaves behind, which is the
case §4.2.1 is actually about, and it waits for a caller that can assert the
premise. Tested against this repo's own six rows above, plus the CLI witness
that `IMPLEMENTING` survives `queue`/`reconcile`.
