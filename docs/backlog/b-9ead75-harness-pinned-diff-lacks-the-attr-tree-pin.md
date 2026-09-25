---
id: b-9ead75
title: "`harness/recovery.py`'s `pinned_diff` lacks the `attr.tree` pin `git_argv` gained in SA-0137"
status: open
tier: 3
filed: 2026-09-25
specs: []
prs: []
commits: []
cites: [§2]
related: [b-a9ee32]
---

## Problem

Found in the review of #505 (`SA-0137`), 2026-09-24.

`SA-0137` pins `attr.tree` empty in `git_argv`
(`saffron/cell/worktree.py:206-207`). `pinned_diff` copies two of
`git_argv`'s overrides and not that one (`harness/recovery.py:70-90`). On
host git 2.54, a global `attr.tree` prints an edit there as binary.

## Done looks like

`pinned_diff` pins `attr.tree` empty, and a test sets it globally and reads
hunks.

## Record

- 2026-09-25: filed from the spec loop's run 16.
