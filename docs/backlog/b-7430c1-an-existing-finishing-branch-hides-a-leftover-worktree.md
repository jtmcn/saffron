---
id: b-7430c1
title: 'An existing finishing branch hides a leftover worktree, because its escalation drops the removal error'
status: open
tier: 3
filed: 2026-10-02
specs: [SA-0167]
prs: [638]
commits: []
cites: []
related: [b-792ab2]
---

## Problem

Found in the spec loop's run 25, 2026-10-02.

When the lease push finds the finishing branch already there,
`publish_finish` returns its "already exists" escalation. A `GitError` from
removing the worktree is then caught and never reported
(`saffron/finish.py:357-358`, `:371-375`). The pushed path reports the same
error as a second line. Found by the Spec seat on #638 by reading, not
driven.

## Done looks like

Every path that leaves a worktree behind says so, the escalation paths
included.

## Record

- 2026-10-02: filed from the spec loop's run 25.
