---
id: b-49329e
title: '`SA-0123` left its ledger write path short of its own rules, because the fixes would have crossed the `refactor` ceiling'
status: open
tier: 3
filed: 2026-09-22
specs: [SA-0123, SA-0124]
prs: [451, 459]
commits: []
cites: [§4.1]
related: [b-fd1468, b-89ec93, 171]
---

## Problem

Found in the spec loop's run 14, 2026-09-22.

`SA-0123` routed every task write through `_apply`. Its cell ended `EXHAUSTED`
at 1001 changed lines against the `refactor` ceiling of 1000. Review brought it
to 999, and every fix below would have cost lines the ceiling did not have.

- Three new witnesses read rows through `ledger._db`. The spec said to read
  them through `_raw_rows`. They are criterion 5's, criterion 13's and
  `_table_counts` in criterion 6's, in `tests/test_ledger_fold_task.py`.
- The new SQL in `saffron/ledger.py` is written as single-line strings. The
  spec asked for triple-quoted strings over several lines, as the file writes
  them elsewhere.
- `_apply`'s last line raises "fold cannot place fact kind". Live writers now
  reach it as well as the fold.
- `fold_task`'s docstring lost "All or nothing. Empty `facts` only drops the
  rows." Both are still true.
- A finding's position is computed two ways. `_finding_at` counts with
  `OFFSET`, and `record_rebuttal` counts with `COUNT` and `<=`.
- `tests/test_ledger.py`'s docstring for
  `test_an_attempt_against_no_task_raises_rather_than_naming_another` explains
  a `lastrowid` guard `open_attempt` no longer uses.
- `tests/test_fold.py` still reads `ledger._db` in `rows` and `_read`. Item
  b-fd1468 asked for that rewrite, and `SA-0123` deferred it. After `SA-0124`,
  the `rows()` docstring is false as well. It says every column `queue_lines`
  reads is in its `SELECT`, and `added` and `removed` are not.

## Done looks like

Each point above is fixed, in one change that is not near a ceiling.

## Record

- 2026-09-22: filed from the spec loop's run 14 (#451, #459).
