---
id: 176
title: '`mirror.diff_stat` reads without `DIFF_FLAGS`, so operator git config moves the queue line''s counts'
status: open
tier: 3
filed: 2026-09-17
specs: [SA-0105]
prs: []
commits: []
cites: []
related: [115, 171]
---

## Problem

Found reviewing `SA-0097` (PR #321), 2026-09-17, by both seats. #321 made
`mirror.changed_files` splice `saffron.cell.worktree.DIFF_FLAGS`. `diff_stat`
in the same file still runs a bare `git diff --shortstat`. An operator's
`diff.ignoreSubmodules` or `diff.renames` then changes the `+N/−M` that a queue
line and a pull request body show. Unverified by a run. The number is for display and
never reaches `scope`.

## Done looks like

Splice `DIFF_FLAGS` into `diff_stat` too, with a witness that sets
`GIT_CONFIG_GLOBAL` as #321's mirror witness does.
