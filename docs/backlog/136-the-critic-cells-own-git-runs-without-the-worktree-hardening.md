---
id: 136
title: The critic cell's own git runs without the hardening every other in-cell git read carries
status: done
closed: 2026-09-19
tier: 1
filed: 2026-09-15
by_hand: true
specs: [SA-0087]
prs: [274]
commits: ["fe1a23a"]
cites: [§5.5]
related: [102, 103, 110, 118]
---

## Problem

**Tier 1.** Found reviewing `SA-0087` (PR #274), by reading the two call paths;
not measured.

`worktree._git` is the repo's single hardened in-cell git invocation, and every
pin in it was bought by an item: `core.useReplaceRefs=false` (102),
`core.bigFileThreshold` and `core.attributesFile=/dev/null` (103),
`GIT_GRAFT_FILE` and `GIT_SHALLOW_FILE` pointed at `/dev/null` (110), plus
`core.quotePath=false`. Each one closes a way the tree a reader sees can differ
from the tree that ships.

`_apply_and_commit_patch` (`saffron/cell/session.py`) calls `runtime.exec_stream`
and `runtime.exec_` directly instead, so the critic cell's `git apply --index`
and `git commit` carry none of them. The immediate exposure is narrow — the
critic cell's `.git/config` is fresh, and the patch is applied to a tree seeded
from the mirror — but the tree the lenses then read *through* the hardened
`export_patch` is no longer guaranteed to be a fixed point of the patch that was
applied. `core.attributesFile=/dev/null` is the pin that matters most here: the
review found an in-tree `.gitattributes` carried by the patch changing what
`git add` staged, which is the same class of influence.

`git apply` genuinely cannot go through `_git`, which carries no stdin
(`worktree.py`), and the patch must travel on stdin because a single argv is
capped. The commit could.

`saffron/cell/worktree.py` is in `SA-0087`'s `forbidden` list and `_git` is
private, so neither calling it nor widening it was available to that cell.

## Done looks like

`_git` — or a public sibling of it — carrying the critic cell's commit, and a
decision recorded about `git apply`: either a stdin-capable variant of `_git`,
or a comment at the call site naming which pins it forgoes and why that is
tolerable for an apply into a fresh tree.

## Record

- 2026-09-19: done by hand. `_git`'s argv is now the public `worktree.git_argv`.
  The critic cell's `git apply --index` and `git commit` both take it, so
  neither forgoes a pin. Measured applying and
  committing under git 2.54 on the host and git 2.39 in `saffron/cell:saffron`.
  One correction to the problem above: `core.attributesFile=/dev/null` nulls
  only the user-level attributes file, never an in-tree `.gitattributes`, so it
  was not the pin that answered the patch's own attributes. `--index` is.
