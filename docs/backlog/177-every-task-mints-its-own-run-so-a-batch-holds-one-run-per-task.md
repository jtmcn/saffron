---
id: 177
title: Every task mints its own run, so a batch holds one run per task and not one per repo
status: done
tier: 2
closed: 2026-09-22
by_hand: true
filed: 2026-09-17
specs: []
prs: []
commits: [49c4095]
cites: [§4.1, §4.2.1]
related: [68, 164]
---

## Problem

Found 2026-09-17, checking `CONTEXT.md`'s **Run** against the code.

`CONTEXT.md` defines a run as one repo's slice of a batch. It owns the repo's
`base_sha`, preflight outcome and baseline, and a batch contains one per repo.
§4.2.1 does preflight once per run for the same reason.

The code makes one run per task. `run_one_cell` calls `ledger.create_run` for
every task it starts (`saffron/cell/session.py:1331`). `run_batch` then stamps
that run onto the batch after the task returns (`saffron/batch.py:198`). Nothing
reuses a run across tasks.

Measured against `~/.saffron/ledger.db` the same day: 102 runs and 102 tasks, no
run holding more than one task, and 10 of the 102 runs linked to any of the 12
batches. The other 92 come from `saffron cell` and `saffron replay`, which have
no batch.

So what a run owns is paid once per task. A night of five tasks on one repo
carries five `base_sha` pins, and item 164's preflight column would be written
five times.

## Done looks like

One of the two is made true, and the other says so:

- The batch mints one run per repo and every task in it reuses that run, as
  §4.2.1 and **Run** describe. `saffron cell` keeps a run of its own.
- Or **Run** and §4.2.1 are redefined as one task's pin. The per-repo slice of a
  batch then gets a name of its own, or is recorded as having none.

## Record

**Filed 2026-09-17** from the domain-modeling read of `CONTEXT.md` (PR #322).
Item 164 reads the same `create_run` call for a different defect.

**Closed 2026-09-22 by hand**, taking the second arm on the operator's call.
**Run** is now one task's pin in `CONTEXT.md` and `DESIGN.md` §4.1. §4.2.1 and
§4.4 now say what a batch does once per repo. The per-repo slice of a batch
has no name and no row. The code already matched, so `saffron/` is unchanged.
