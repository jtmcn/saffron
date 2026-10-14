---
id: b-573746
title: DESIGN.md §5.1 says `/gates` is a cell's one bind mount, which SA-0272's snapshot mount makes false
status: open
tier: 3
filed: 2026-10-14
specs: [SA-0285, SA-0272]
prs: [872]
commits: []
cites: [§5.1]
related: [b-a8270f]
---

## Problem

Found by the Standards seat on #872 in the spec loop's run 38.

`SA-0285` let `prepare_worktree` take `extra_mounts`. No caller passes one
yet. `SA-0272` will mount a read-only ledger snapshot and the mirrors there.
§5.1 says `/gates` "is the one bind mount in the block", and its argument
against bind mounts leans on that. Both specs forbid `DESIGN.md`.

## Done looks like

§5.1 names the History run's read-only mounts beside `/gates`, edited by hand
in the pull request that lands `SA-0272`.

## Record

- 2026-10-14: filed from the spec loop's run 38.
