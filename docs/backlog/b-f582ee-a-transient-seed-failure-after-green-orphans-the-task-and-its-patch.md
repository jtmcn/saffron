---
id: b-f582ee
title: A transient seed failure after green records `ORPHANED`, and nothing resumes the green patch
status: partial
tier: 1
filed: 2026-09-30
specs: [SA-0161, SA-0232, SA-0369]
prs: [779]
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
- 2026-10-05: run 28 saw the same refusal while a cell seeded its
  worktree, on `f61da02f`. A retry worked (b-6ac0cd).
- 2026-10-09: `SA-0232` (#779) landed in the spec loop's run 32. A seed whose
  fetch fails is retried once on a cleared volume after a pause. Resuming an
  `ORPHANED` task's green patch is still open.
- 2026-10-09: recurred in run 32 on the mirror's loose object 6c8cc03b. It
  failed `SA-0233`'s PACKAGE seed and `SA-0251`'s first seed. `git repack -d`
  and moving the mirror aside cleared it again.
- 2026-11-10: a new shape in the spec loop's run 59. `SA-0362` went green and
  finished REBUT. Then the cell runtime failed to start any process in its
  container ("no PID data from sync pipe"). The patch export ran inside that
  container, so no `patch.diff` was written and the task ended `ORPHANED` at
  $31.46 of $32. `saffron adopt` refuses an `ORPHANED` task, so the hand
  rebuild (#1127) is no task's pull request.
- 2026-11-10: a second loss in the spec loop's run 60. `SA-0365`'s second
  repair chased the clock flake #1112 fixes and looped the suite. Then its
  agent died with exit -6, and the cell runtime failed with "no PID data from
  sync pipe". No patch was exported, and the task reads `ORPHANED` at $49.80
  of $60. #1137 is a hand rebuild.
- 2026-11-11: a third cell, in the spec loop's run 61. `SA-0368` went green
  on attempt 2. REBUT's agent then died with exit -6 before any result event,
  so no blocker was answered and the task reads `EXHAUSTED` at $39.92 of $52.
  The patch was exported, and PACKAGE opened #1145. A runtime death read as
  `EXHAUSTED` is an `error` charged to the task.
- 2026-11-11: `SA-0369` (#1150) landed in the spec loop's run 62. A cell
  the runtime cannot exec in now has its container removed, and its patch is
  read from the worktree volume by a read-only container. Resuming an
  `ORPHANED` task's patch is still open, and so is a runtime death read as
  `EXHAUSTED`.
