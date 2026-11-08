---
id: b-879e72
title: '`package`, `finish` and `replay` take no home lock, so a batch beside one stamps its live row `ORPHANED`'
status: open
tier: 2
filed: 2026-11-08
specs: []
prs: []
commits: []
cites: [§4.2.1]
related: [b-a714d2, b-615466]
---

## Problem

Found reviewing `SA-0352` (#1090), in the spec loop's run 55.

`SA-0352` locks the home for `cell`, `batch` and `draft`
(`saffron/cli.py`, `_locked_dispatch`). `saffron package` reruns PACKAGE on a
row left `REVIEWING` or `REBUTTING`. `saffron finish` runs follow-up cells.
`saffron replay` creates an in-flight row. None of the three takes the lock,
so a batch started beside one can stamp its live row `ORPHANED`. The spec
deferred `replay` to v1. The Spec seat did not measure `package`'s row state
during a run, so that half is unverified.

## Done looks like

Every command that holds an in-flight row takes the home lock, or the
module docstring in `saffron/reconcile.py` names why one does not. A test
starts a batch beside `saffron finish` and asserts the follow-up's row keeps
its state.

## Record

- 2026-11-08: filed from the spec loop's run 55.
