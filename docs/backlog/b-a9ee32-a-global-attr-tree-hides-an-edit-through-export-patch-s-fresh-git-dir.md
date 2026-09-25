---
id: b-a9ee32
title: A global `attr.tree` hides an edit through `export_patch`'s fresh git dir on git 2.46 and later
status: done
tier: 2
filed: 2026-09-22
closed: 2026-09-25
specs: [SA-0118, SA-0137]
prs: [433, 505]
commits: []
cites: [§2]
related: [103, b-b5f379]
---

## Problem

Found reviewing `SA-0118` (#433), 2026-09-22, by probe.

`export_patch` now reads a fresh git dir, which no attribute file in the
worktree reaches. A global `attr.tree` still reaches it on git 2.46 and later.
Measured on host git 2.54, the patch prints `Binary files a/f.py and b/f.py
differ` with no hunks. The cell's git 2.39.5 does not read `attr.tree`, so the
gap opens when item b-b5f379 bumps the cell's git.

`-c attr.tree=` in `git_argv` restores the hunks on 2.54. It is unmeasured on
2.39.5.

## Done looks like

`git_argv` pins `attr.tree` empty, measured on the cell's git and the host's,
with a witness that sets it globally.

## Record

- 2026-09-22: filed from the spec loop's run 13.
- 2026-09-25: `SA-0137` reached `READY_FOR_REVIEW` as #505 at $2.51 of $16,
  in the spec loop's run 16. `git_argv` pins `attr.tree` empty. `SA-0137`
  retires to `done/`.
