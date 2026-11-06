---
id: b-25c0f5
title: "Test setup for the routed ledger and bare repos is restated across a dozen files"
status: open
tier: 3
filed: 2026-11-06
specs: [SA-0334, SA-0335]
prs: []
commits: []
cites: []
related: [b-4eaaa4]
---

## Problem

Found by the Standards seat on #1024 and #1025, in the spec loop's run 54.

- `_seeding_ledger` is the same function, docstring included, in
  `tests/test_regate.py` and `tests/test_commit_review.py`.
- About nine test helpers build
  `Ledger(..., record=RoutedRecord(lambda key: ledger.record_home(key)))`
  themselves. The `routed_ledger` fixture in `tests/conftest.py` fits only a
  helper with one fixed repo row. Run 54's review kept the copies.
- `_bare` is still defined in `tests/test_cli.py`, `tests/test_record_routed.py`,
  `tests/test_record_migrate.py` and `tests/test_task_record.py`, beside
  conftest's `bare_repo`.

## Done looks like

One factory in `tests/conftest.py` takes a mirror and an origin and returns
the routed ledger `main` builds. Every helper above imports it, and the four
`_bare` copies import `bare_repo`.

## Record

- 2026-11-06: filed from the spec loop's run 54.
