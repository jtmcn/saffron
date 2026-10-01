---
id: b-f582ee
title: A transient seed failure after green records `ORPHANED`, and nothing resumes the green patch
status: open
tier: 1
filed: 2026-09-30
specs: [SA-0161]
prs: []
commits: []
cites: [§5.1]
related: [b-8170eb, 45]
---

## Problem

Found in the spec loop's run 23, 2026-09-30.

`SA-0161`'s first cell went green on attempt 2 at $14.63. The host then
seeded a fresh gate cell from the mirror (`saffron/cell/session.py:1279`,
`worktree.prepare_worktree`). The seed failed:

```
remote: error: unable to open loose object ccda5c08...: Permission denied
fatal: git upload-pack: aborting due to possible repository corruption on the remote side.
```

`saffron cell` raised `CellRuntimeError` and exited 2. The ledger recorded
`ORPHANED` with no pull request. The patch survived only as
`~/.saffron/batches/v0/SA-0161/patch.diff`, which no command resumes from.

Minutes later the same object read cleanly from a container over the same
read-only bind mount. The failure was transient, and its cause is unknown.
The re-run paid for the whole cell again, $20.30.

## Done looks like

A seed failure in a post-IMPLEMENT cell is retried once before it ends the
task. A task that still ends there keeps its green patch where a later
command can package it, and says which command does.

## Record

- 2026-09-30: filed from the spec loop's run 23.
