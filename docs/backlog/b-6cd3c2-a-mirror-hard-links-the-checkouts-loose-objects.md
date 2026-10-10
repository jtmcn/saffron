---
id: b-6cd3c2
title: A mirror hard-links the checkout's loose objects, so one unreadable inode fails every seed and a fresh mirror inherits it
status: open
tier: 1
filed: 2026-10-08
specs: []
prs: []
commits: []
cites: [§5.1]
related: [b-6ac0cd, b-60a399, b-f582ee]
---

## Problem

Measured in the spec loop's run 31.

`saffron/repos/mirror.py` builds a mirror with `git clone --mirror` from the
operator's checkout. A local clone hard-links every object file, so the
mirror's loose objects are the checkout's own inodes. `958db033` had inode
206896207 in both `.git/objects` and the mirror.

Four seeds failed on those inodes in one night. Each seed's `git fetch` read
"unable to open loose object … Permission denied" (`saffron/cell/worktree.py`).

- Batch 16: SA-0226's PACKAGE re-verify seed, after the cell went green, and
  then SA-0225's cell seed.
- Batch 17: SA-0225's cell seed again, on ten objects.
- Batch 18: a mirror moved aside and rebuilt from scratch failed on the same
  two objects, because the clone linked the same inodes.

`cat` of the failing file in the same image, as the same root user, read
every byte, while git's own read of it failed. The failing objects were all
loose objects written between 19:25 and 19:30, by `git fetch` in the
delegate's sandboxed session. Packed objects never failed.

`git repack -d` in the checkout moved those objects into a pack. The mirror
was moved aside again, and batch 19's seeds and PACKAGE all succeeded.

## Done looks like

A mirror shares no inode with the operator's checkout, for example by
`git clone --mirror --no-local`. A test builds a mirror from a local
repository and asserts that no object file's inode appears in both.

## Record

- 2026-10-08: filed from the spec loop's run 31. It answers b-6ac0cd's open
  question in part: a retry does not clear it, a rebuilt mirror does not, and
  a repack does.
- 2026-10-09: recurred in the spec loop's run 32. The mirror's loose object
  6c8cc03b failed `SA-0233`'s PACKAGE seed and `SA-0251`'s first seed. `git
  repack -d` and moving the mirror aside cleared it again.
