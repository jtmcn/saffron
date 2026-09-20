---
id: b-bbf663
title: §4.1's `tasks` tuple names three columns that never existed and omits three that do
status: open
tier: 3
filed: 2026-09-19
specs: []
prs: []
commits: []
cites: [§4.1]
related: [b-1c7019]
---

## Problem

Found by the spec loop's Standards seat reviewing #381, 2026-09-19, and
verified by the delegate.

`DESIGN.md:305-307` declares the `tasks` row as `(task_id, run_id, spec_id,
spec_sha, state, risk, branch, policy_sha, prompt_sha, parent_task_id,
worktree, volume, budget_usd, spent_usd_est, updated_at)`.

Three of those names are in no schema: `parent_task_id`, `worktree` and
`volume`. `git grep` over `saffron/ledger.py` returns nothing for any of them.

Three columns the table declares are missing from the tuple: `pushed_sha` and
`pr_url` (`saffron/ledger.py:73-74`), and now `merged_head_sha` from #381.

`SA-0111` leaned on the second half, and rightly: a column missing from that
block is the existing shape rather than a contradiction. Nobody looked at the
first half. §4.1 promises columns the ledger never carried. A reader checking a
new column against it checks a list wrong in both directions.

§4.1 is `protected`, so this is reconciled deliberately or not at all.

## Done looks like

§4.1's `tasks` tuple matches `saffron/ledger.py`'s `SCHEMA`, in one pass rather
than one column at a time. The three absent names are either dropped or
recorded as still owed.

## Record

- 2026-09-19: filed from the spec loop's run 10 (#381). Surfaced while
  checking whether `merged_head_sha`'s absence from §4.1 was a contradiction.
