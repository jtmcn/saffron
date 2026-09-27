---
id: b-41664e
title: attach_run_to_batch's docstring names one call that mints a run, and there are three
status: open
tier: 3
filed: 2026-09-27
closed:
specs: []
prs: []
commits: []
cites: []
related: [b-792ab2]
---

## Problem

`Ledger.attach_run_to_batch` says the only call that mints a run is
`run_one_cell`, in `saffron/cell/**` (`saffron/ledger.py:990-991` at
`f492629e`). `replay` mints one as well (`saffron/replay.py:53`). Once
`SA-0156` lands, `cli._stack_mint` mints a third.

`SA-0156` asked for the reword. The operator took it out on 2026-09-27, so
that `SA-0156` touches no `saffron/ledger.py` and runs at `standard`.

## Done looks like

The docstring names every call that mints a run, or names none. The next
spec that already edits `saffron/ledger.py` can carry the reword.
