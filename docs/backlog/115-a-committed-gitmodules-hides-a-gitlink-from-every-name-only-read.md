---
id: 115
title: A committed `.gitmodules` hides a gitlink from every name-only read without the flag
status: open
tier: 1
filed: 2026-09-14
specs: [SA-0082, SA-0097]
prs: [244, 321]
commits: []
awaiting: [321]
cites: []
related: []
---

## Problem

**Tier 1.** Found reviewing `SA-0082` (PR #244), 2026-09-14. `SA-0082` pinned
`DIFF_FLAGS` with `--ignore-submodules=none` against a worktree's
`diff.ignoreSubmodules`. A committed `.gitmodules` with `ignore = all` hides the
gitlink the same way, and it is content the agent commits, not config: `-c
diff.ignoreSubmodules=none` does not override it, and only the flag does (plain
git 2.54: flag → `.gitmodules vendor/sub`; override and bare → `.gitmodules`).
`SA-0082`'s spec lists the override as an equivalent restorer; it is not. #244
added a witness that pins the flag in `worktree.changed_files`. Two more name-only
reads carry neither: PACKAGE's listing fed to `scope_gate`
(`saffron/phases/package.py:1141`) and `saffron/repos/mirror.py:125-140`'s
`changed_files`, whose docstring says it is matched against `touches`. Unverified
end to end through `apply_patch` and `commit_squash`.

## Done looks like

both reads taking `--ignore-submodules=none`, ideally by
importing `worktree.DIFF_FLAGS`, each with a witness that commits a gitlink under an
`ignore = all` `.gitmodules` and finds the path listed.

## Record

**2026-09-17, open as PR #321**, `SA-0097` in the spec loop's run 6: PACKAGE's
listing and `mirror.changed_files` splice `DIFF_FLAGS`. `mirror.diff_stat` still
does not, item 176.
