---
id: b-cc87b1
title: The end review's writer drafts a follow-up that a queued spec already owns, and leaves its origin item's `specs:` stale
status: open
tier: 2
filed: 2026-10-23
specs: []
prs: [939]
commits: []
cites: [§4.2.1]
related: [b-703e64, b-fe82d9, b-589cf6]
---

## Problem

Found in the spec loop's run 46, in batch 47.

Batch 47's end review filed the in-cell critic's concern at
`saffron/finish.py:259` as a follow-up. The finding's own claim said queued
`SA-0306` owned the fix. The writer still drafted `SA-0310` for $1.11, which
restates `SA-0306`'s criterion. The draft did not add `SA-0310` to
`b-8a0c9a`'s `specs:` list.

The finish committed the draft and escalated on "13 new failures". A local
run of that commit found one, the records test for that `specs:` list. Task
336 was then left `ORPHANED`.

## Done looks like

Qualification drops a finding whose claim names a queued spec as its owner.
A drafted follow-up updates its origin item's `specs:` list in the same
commit.

## Record

- 2026-10-23: filed from the spec loop's run 46.
