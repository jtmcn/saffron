---
id: b-edcab7
title: Three sentences in files run 28's cells could not edit lag what the stack built
status: open
tier: 3
filed: 2026-10-05
specs: [SA-0203, SA-0204]
prs: [676, 678]
commits: []
cites: [§5.7, §6.1]
related: [b-990bd9, b-8e30bd]
---

## Problem

Found reviewing #676 and #678 in the spec loop's run 28. Each file was forbidden to the
cell whose change made its sentence false.

- `saffron/reconcile.py:1-4` says PACKAGE's last word is `READY_FOR_REVIEW`
  or `MERGE_FAILED`. `SA-0204` packages an `EXHAUSTED` task too.
- `saffron/ledger.py`'s `set_task_package` docstring names the same two
  states.
- `saffron/cell/session.py:1297` says "only READY_FOR_REVIEW is packaged".

`saffron/task.py` now builds an `EXHAUSTED` row and an unpackaged row from two
13-field `QueueLine` copies that differ in `state` and `note`. That is
b-990bd9's shape, grown by one more site.

## Done looks like

Each sentence says what the code does. b-990bd9's builder covers the two
`task.py` sites.

## Record

- 2026-10-05: filed from the spec loop's run 28.
