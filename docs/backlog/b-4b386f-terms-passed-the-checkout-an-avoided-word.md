---
id: b-4b386f
title: "The `terms` gate passed \"the checkout\", a phrase on Worktree's _Avoid_ line"
status: open
tier: 3
filed: 2026-10-09
specs: []
prs: [786]
commits: []
cites: []
related: [174, b-d5d290]
---

## Problem

Found by #786's Standards seat in the spec loop's run 32.

`SA-0239`'s cell wrote "the checkout" in `commit_finish`'s docstring
(`saffron/finish.py:151` at the packaged head). `CONTEXT.md:85` lists that
phrase under **Worktree** as one to avoid. The `terms` gate passed it,
because `AVOIDED` holds seven phrases and that one is absent
(`.saffron/gates/prose.py:151-159`). The review commit 78c55207 fixed the
line by hand.

The tree holds the phrase elsewhere, in `saffron/preflight.py:385`,
`saffron/cell/worktree.py:553`, `saffron/cell/session.py:351` and
`saffron/phases/package.py:726`. Some of those name the operator's checkout
and not a worktree, so adding the phrase needs a read of each.

## Done looks like

`AVOIDED` lists "the checkout" under Worktree, or a recorded decision says why
not. Each hit in the tree is fixed or exempted, and a test drives a docstring
holding the phrase through `terms`.

## Record

- 2026-10-09: filed from the spec loop's run 32.
