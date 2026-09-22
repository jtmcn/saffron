---
id: 103
title: A cell can hide an edit's content from the critic with settings the diff never shows
status: partial
tier: 2
specs: [SA-0075, SA-0118]
prs: [231]
commits: []
cites: []
related: [89]
---

## Problem

**Tier 2.** Found reviewing `SA-0072` (PR #219), 2026-09-12, by probe. Four
repo-local settings make the pinned diff print `Binary files a/f.py and b/f.py
differ` with no hunks, while the name-only listing is unchanged: `* -diff` or
`* binary` in `.git/info/attributes`, `core.attributesFile`,
`diff.<driver>.binary=true`, and `core.bigFileThreshold=1`. None appears in the
diff, so the critic reviews nothing, and `integrity`'s binary ceiling
(`saffron/gates/core/integrity.py:234`), written against a *committed*
`.gitattributes`, never sees why. That ceiling's own upgrade path (`:238-240`)
says `--numstat` still counts added lines for a file rendered as binary; under
`* -diff` it printed `-	-	f.py`.

**Tier 2, not 1,** because — from reading `apply_patch`, not run — PACKAGE
refuses a binary change with no full index line, so the hidden content cannot
reach a pull request unreviewed. The task fails instead, and as infrastructure
rather than as its own failure, which is a second defect of the same shape.

**A fifth vector**, found reviewing `SA-0075` (PR #231), 2026-09-12, by probe.
An untracked `.gitattributes` marking every path `-diff`, hidden by a line in
`.git/info/exclude`, makes the pinned diff print `Binary files … differ` on both
the host's git (2.54) and the cell's (2.39.5). `dirty_paths`' `status
--untracked-files=all` does not list it and `commit_dirty`'s `add -A` never
commits it, so it is as invisible as `.git/info/attributes`. `--attr-source=HEAD`
restores the hunks on 2.54, since it reads attributes from the tree rather than
the worktree, but 2.39.5 rejects the flag: that answer needs the cell image's git
bumped first. Unmeasured: the `2g` threshold now also governs `commit_dirty`'s
`add -A`, which reads a file between git's `512m` default and `2g` into memory
rather than streaming it, inside a `4g` cell.

## Done looks like

each setting pinned on `_git`'s command line where one
exists — probed: `-c core.bigFileThreshold=2g` restores the hunks and
`-c core.attributesFile=/dev/null` neutralises the second — and an answer for
`.git/info/attributes`, which neither `--attr-source=<empty tree>` nor
`core.attributesFile` overrode. The integrity comment corrected either way.
Item **89** holds the settings that move the diff's shape rather than hide it.

## Record

**Status: the two `-c` pins are `READY_FOR_REVIEW`, 2026-09-12 — `SA-0075`,
PR #231 in stack #233, measured on the cell's own git (2.39.5) as well as the
host's.** Their threshold witness first edited an 8-byte file, so a pin lowered
to 32 bytes passed it; a review commit grew the file past 1 MiB. `.git/info/attributes` stays here, and now has a
probed answer: on git 2.54, `--text` restores its hunks, and a `diff.<driver>.binary`
driver's too. It is not taken, because it also renders every genuine binary as
text, which changes `integrity`'s binary check and PACKAGE's no-full-index
refusal. `integrity`'s comment claiming a `--numstat` cross-check would close
this was corrected by hand the same day, since `SA-0075` cannot reach
`saffron/gates/**`. On the comment's own example, a committed `*.py -diff`,
`--numstat` printed `-	-	f.py`, with `--text` as well.

Merged 2026-09-13, PR #231.
