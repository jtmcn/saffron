---
id: b-115f9b
title: The stack batch reads its batch id three ways, and two helpers restate the layer query and the git runner
status: partial
tier: 3
filed: 2026-10-01
specs: [SA-0162, SA-0151]
prs: [626, 628, 934]
commits: []
cites: []
related: [b-792ab2]
---

## Problem

Found by the review seats of #626 and #628, 2026-10-01.

- `run_stack_batch` holds `batch_id` and still calls `ledger.latest_batch_id()`
  three times. `Ledger.latest_batch_id`'s docstring says `run_stack_batch`
  reads it once `run_batch` returns, which is no longer true.
- `saffron/end_review.py`'s `_BATCH_LAYERS` repeats the join
  `Ledger.stack_layers` now exposes.
- `saffron/cli.py`'s `_run_git` calls the private `git_mirror._run`. A public
  runner in `saffron/repos/mirror.py` would serve it and `finish.py`.

## Done looks like

One source for each: the held `batch_id`, `Ledger.stack_layers`, and a
public git runner.

## Record

- 2026-10-01: filed from the review seats of #626 and #628.
- 2026-11-07: partial in grooming. `run_stack_batch` holds its own batch id
  and calls `latest_batch_id` nowhere. Only `saffron/report/stack.py:277`
  reads it. `SA-0304`'s review (#934) corrected the docstring at
  `saffron/ledger.py:1375`. Two parts stay open. `end_review.py`'s
  `_BATCH_LAYERS` still repeats the join in `Ledger.stack_layers`.
  `cli.py`'s `_run_git` and `finish.py:220` still call the private
  `git_mirror._run`.
