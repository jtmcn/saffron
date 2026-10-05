---
id: b-6ac0cd
title: Git in a cell was refused a loose object while seeding its worktree, and a retry worked
status: open
tier: 3
filed: 2026-10-05
specs: [SA-0203]
prs: []
commits: []
cites: [§5.1]
related: [b-f582ee]
---

## Problem

Found in the spec loop's run 28.

`SA-0203`'s first start exited 2 while it seeded its worktree. Git inside
the cell got "Permission denied" on a loose object, `f61da02f`, the merge
commit of #664. The ledger read `ORPHANED` at $0.00. A retry a minute later
worked. b-f582ee saw the same error on another object
in run 23, after green.

The cause is unknown. The one lead is the `com.apple.provenance` extended
attribute on the object. The mirror holds it as a hard link.

## Done looks like

The cause is measured, or ruled out. Either a test reproduces the refusal, or
this record says which lead failed and why.

## Record

- 2026-10-05: filed from the spec loop's run 28.
