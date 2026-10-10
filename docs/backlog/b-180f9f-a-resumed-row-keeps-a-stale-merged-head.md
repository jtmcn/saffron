---
id: b-180f9f
title: "A row resumed after a crash before `SA-0246` keeps its `merged_head_sha`, and `reconcile` now trusts it"
status: open
tier: 2
filed: 2026-10-09
specs: []
prs: [788]
commits: []
cites: [§4.2.1]
related: [b-3e0dbe, b-1c7019]
---

## Problem

Found by #788's Spec seat in the spec loop's run 32, from the critic's
withdrawn contract blocker.

`SA-0246` lets `reconcile` complete a pending row as `MERGED` when
`merged_head_sha` is set, without asking `gh` (`saffron/reconcile.py:170`).
Nothing clears that column when a task is resumed, and `set_task_package`
leaves it (`saffron/ledger.py:1548`). A row that crashed between the two
writes before this change and was then requeued carries a stale head beside
a new `pr_url`. The seat's fixture showed `reconcile` marking it `MERGED`
without asking about the new pull request. The spec put such rows out of
scope. No one queried the real ledger for them.

## Done looks like

A one-time query counts requeued or pending rows with a non-null
`merged_head_sha` in the operator's ledger. The resume path clears the column,
and a test resumes such a row and reads it back pending.

## Record

- 2026-10-09: filed from the spec loop's run 32.
