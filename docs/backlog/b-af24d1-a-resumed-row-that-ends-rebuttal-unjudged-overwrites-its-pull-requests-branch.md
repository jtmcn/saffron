---
id: b-af24d1
title: A rerun that ends `REBUTTAL_UNJUDGED` is pushed onto another row's open pull request branch, and no merge moves a row at that state to `MERGED`
status: open
tier: 1
filed: 2026-10-11
specs: [SA-0331]
prs: []
commits: []
cites: [§4.2.1, §5.6, §5.7]
related: [120, b-f603c9, b-223244]
---

## Problem

Found by the second spec review of `SA-0276`, 2026-10-11. Every line below
was read at `8272ac44`.

This paragraph and the next rest on a premise that did not hold. A rerun runs on a fresh row (b-223244).
The reachable case is that row beside an older `CHANGES_REQUESTED` or `APPROVED`
row with an open pull request (`SA-0331`). As filed: a `CHANGES_REQUESTED` task
re-queues on its own row and carries its open pull request into the next cell. `test_a_cell_bound_for_package_leaves_no_row_a_reconcile_can_requeue`
seeds exactly that row (`tests/test_session.py:4745-4838`).

Once `SA-0276` lands, such a cell can end `REBUTTAL_UNJUDGED`. PACKAGE does
not run, and `run_task` calls `push_unpackaged_work`. Its guard against an
open pull request reads only the spec's other rows, through its `others`
filter (`saffron/phases/package.py:1149-1158`). The row's own pull request
does not stop it. The row's own `pushed_sha` is a sha it recorded, so the
branch check passes too. The push then replaces the pull request's branch
with work no critic judged.

`reconcile` never asks GitHub about that row. It skips any row outside
`PR_PENDING_STATES` other than `EXHAUSTED` (`saffron/reconcile.py:162`). Only
`EXHAUSTED` takes a merged answer (`saffron/reconcile.py:182-184`), the rule
`SA-0251` set (`DESIGN.md` §5.7). So when the operator merges that pull
request, the row stays `REBUTTAL_UNJUDGED` and never reaches `MERGED`.

## Done looks like

A rerun's unjudged rebuttal does not overwrite a row's standing pull request. A merged pull request on a `REBUTTAL_UNJUDGED` row moves it to
`MERGED`, as one on an `EXHAUSTED` row does.
