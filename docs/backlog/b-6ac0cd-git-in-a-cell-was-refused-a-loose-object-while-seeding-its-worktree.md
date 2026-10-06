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
- 2026-10-05: a second live case in batch 13, in stage 2 of the
  delegate-loop plan. `SA-0206`'s spec-review cell failed its seed with
  "unable to open loose object e31fc36de48460dda1ee180348d21be876fa938e:
  Permission denied", then "bad pack header". The object is a tree in
  `SA-0205`'s commit `c051799e`. In the batch mirror
  (`~/.saffron/mirrors/shiny-chasing-hippo-855a6e42f11a.git`) it was mode
  0444 and owned by the user. It carried a `com.apple.provenance` xattr. It
  was hard-linked, link count 2, to the main checkout's `.git/objects` copy.
  Six of the mirror's 33 loose objects were hard-linked, and all six carried
  the xattr. An earlier seed read the hard-linked `96afa54b` without error.
  Nine minutes later, a read of the same file through the same read-only bind
  mount succeeded. The seed is a throwaway container that runs `git fetch`
  from the mirror, bind-mounted read-only (`saffron/cell/worktree.py`).
  Batch 14's seeds all succeeded. Proposed direction: retry a failed seed
  once before failing the layer. b-60a399 keeps that failure from refusing
  the layer's descendants.
