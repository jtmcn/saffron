---
id: 16
title: No record says which policy PACKAGE verified under
status: done
tier: 0
closed: 2026-09-05
specs: [SA-0046]
prs: [116]
commits: [57b676c]
cites: [§4.1]
related: [13, 15, 58]
---

## Problem

Found reviewing item 15's fix, which created the gap by closing a worse one.
`policy_sha` on the `repos` row is written once, at cell start, from the export
at `base_sha`. When the default branch has moved, PACKAGE re-verifies under
`fetch_head`'s policy instead — a *different* declaration, correctly so — and
nothing records that: not the ledger, not the pull request body, not a watch
line. The body says the gates were re-run on the packaged commit "because the
base moved" without naming what they were re-run under.

This is item 13's own complaint one phase later — *the ledger's record of what
ran is not the record of what was declared* — and the sha is already in hand at
the call site, discarded as `policy, _`.

## Done looks like

a per-task record, which is the part that makes this an item rather than a one-line fix. `repos.policy_sha` is per repo and written before the task exists, so there is nowhere to put a second declaration without
deciding where a task's own policy lineage lives. §4.1's invalidation rule
(*change a repo's gate declarations mid-batch and its in-flight tasks are
invalidated*) is the same question from the other end and should be answered
with it.

## Record

**Decided 2026-09-04: a `policy_sha` column on `tasks`, built with item 58
rather than before it.** Written at cell start and rewritten at PACKAGE when it
differs, which gives the per-task lineage this item says is the part that makes
it an item.

The pairing this item asks for is now answerable: §4.1's invalidation rule has
no reader until batches exist, and a batch is precisely the window in which a
policy moves under an in-flight task. With the column, invalidation is a
comparison rather than a document's claim. **Tier 0**, folded into item 58.

**Status: done** — `SA-0046`, PR #116, merge `57b676c`. `tasks.policy_sha` is
written at cell start from the export at `base_sha` and rewritten at PACKAGE
only when re-verification ran under a different declaration. The record stands
across a gate that errors out of `reverify`, on purpose: the row says what
re-verification ran *under*, not what it concluded.

One thing the column does not do, worth knowing before a reader trusts it: it
holds the *last* declaration a task ran under, not both. After PACKAGE rewrites
it, the base-time value is gone, so "what did this task's cell gates run under"
is no longer answerable from it. §4.1's invalidation reader compares against
in-flight tasks, before PACKAGE, so that reader is unaffected.
