---
id: b-cbb6e7
title: A finish mints its follow-up's id from the stack top's specs, so a spec merged to main since the batch took the same id
status: open
tier: 2
filed: 2026-11-08
specs: []
prs: []
commits: []
cites: [§3.4]
related: [b-589cf6]
---

## Problem

Found in finish 72, in the spec loop's run 55.

The end review pooled one concern into a follow-up, and the writer named it
`SA-0356`. `SA-0356` was already merged on `main` in #1085, a spec written by
hand after batch 72 started. `follow_up.next_spec_id` reads the spec files in
the end review's worktree, the stack top `06dad7af`, and the ledger. Neither
holds a spec merged to `main` by hand since the batch cut its base. The
finishing layer's re-verify went red with 3 new failures, and the finish
escalated and pushed nothing.

## Done looks like

`next_spec_id` also reads the specs at `origin/main`. A test merges a spec
to the origin's default branch after the batch base and asserts the finish
mints the next id.

## Record

- 2026-11-08: filed from the spec loop's run 55.
