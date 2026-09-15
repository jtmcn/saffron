---
id: 102
title: '`refs/replace` lets a cell ship a tree its gates never ran on'
status: done
tier: 1
closed: 2026-09-13
specs: [SA-0074]
prs: [228]
commits: []
cites: [§5.7]
related: [110]
---

## Problem

**Tier 1.** Found reviewing `SA-0072` (PR #219), 2026-09-12, by probe; the
PACKAGE half is read from the code, not run in a cell. An agent that runs
`git replace <real> <benign>` in its worktree changes what every git read of
those objects returns, and `_git` (`saffron/cell/worktree.py:147`) pins config
with `-c` but not replacement. Measured: `--name-only` went from
`FORBIDDEN.md`, `src/a.py`, `tests/test_x.py` to `src/a.py` alone,
`git show HEAD:FORBIDDEN.md` returned the benign content, and `rev-parse HEAD`
still named the real commit.

The gates run on the real tree in `/work`, but `export_patch` and
`changed_files` read the replaced one. So `scope` judges one tree, `tests`
passes another, and `patch.diff` — what PACKAGE applies (§5.7) — describes
neither the commit `patch.json`'s `head_sha` names nor the tree the suite ran
on. `reverify`'s "the packaged tree is the tree the suite already ran on" is
the assumption it breaks. The mirror never receives `refs/replace`, so the
hidden edit itself does not reach the pull request; a `pass` certifying a tree
that does not ship does.

## Done looks like

`--no-replace-objects` as a global option in `_git` —
probed: it restores all three reads, as does `-c core.useReplaceRefs=false` —
with a witness that plants a replacement in `_hostile_repo` and asserts the
pinned read sees the real tree.

## Record

**Status: `READY_FOR_REVIEW`, 2026-09-12 — `SA-0074`, PR #228, the bottom of
stack #233.** The pin is `-c core.useReplaceRefs=false` in `_git`, so it covers
every read, not only the three the criteria name; a review commit added a
witness on `dirty_paths`, which a replacement made report a clean tree as
dirty. Grafts and `.git/shallow` are not replace refs and still move the
history reads: item **110**.

Merged 2026-09-13, PR #228.
