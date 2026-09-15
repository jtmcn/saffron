---
id: 110
title: Grafts and `.git/shallow` move a worktree's history reads with replace refs off
status: partial
tier: 3
filed: 2026-09-12
specs: [SA-0083]
prs: [246]
commits: []
cites: [§4.3, §5.7]
related: []
---

## Problem

**Tier 3.** Found reviewing `SA-0074` (PR #228), 2026-09-12, by probe on host
git 2.54. With base, then a commit touching a forbidden path, then an innocent
commit, and HEAD's parent grafted onto base, `rev-list --count base..HEAD`
dropped from 2 to 1 and `log` listed only the innocent commit — under
`-c core.useReplaceRefs=false` and `--no-replace-objects` alike, because a graft
is not a replace ref. A `.git/shallow` did the same. The diff was unaffected
(`--name-only` still listed the forbidden path), so `scope`, the gates and
PACKAGE judge the real tree.

What moves is what `commits_ahead` and `commit_subjects`
(`saffron/cell/worktree.py`) read: the commit count §4.3's doneness is measured
by — though an attempt with no commits still counts 0, since the range is empty
whatever a graft says — and the subjects recorded in the squash body (§5.7), the
only surviving trace of the agent's own commits.

## Done looks like

both reads pinned against both files — `GIT_GRAFT_FILE`
pointed at nothing is the reviewer's suggestion, unprobed, and `.git/shallow`
has no probed answer yet — with a witness that grafts a worktree the way
`SA-0074`'s fixture plants a replacement.

## Record

**Status: merged, 2026-09-14 — `SA-0083`, PR #246, stacked on
`SA-0082`, in stack #251.** The pin puts `env` at argv[0], and
`.saffron/Dockerfile` asserts `git --version` but not `env --version`. Probed that day on git 2.39.5 (the cell image) and 2.54, with identical
results (`docs/evidence/scripts/2026-09-13-history-and-diff-pins.sh`):
- `GIT_GRAFT_FILE=/dev/null` pins grafts and not shallow.
- `GIT_SHALLOW_FILE=/dev/null`, which git does not document, pins shallow.
- `--shallow-file` is not a command-line option on either version.
- Together the two variables restore both reads, and they change nothing on a
  clean repo.
- `GIT_GRAFT_FILE` makes every call print git's deprecation hint until
  `advice.graftFileDeprecated=false` is set.
