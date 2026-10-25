---
id: b-066901
title: "`saffron package` refuses a stack layer cut from its parent's review commit, since only PACKAGE's push counts as a parent"
status: done
tier: 2
filed: 2026-10-23
closed: 2026-10-25
specs: [SA-0313, SA-0315, SA-0316]
prs: [937, 961, 964, 966]
commits: []
cites: [§5.7]
related: [b-619b7d, b-4eaaa4]
---

## Problem

Found in the spec loop's run 46, on `SA-0302`.

A stack batch cuts each layer from its parent's live branch head. The loop
pushes review commits early, so that head is a review commit. `SA-0302`'s
PACKAGE raised during re-verify when the container service failed. The batch
still exited 0.

`saffron package SA-0302` then refused: "076bf182097f was pushed by no task
in this repo". `ready_task` at `saffron/task.py:997` matches the tree base
only against each task's `pushed_sha`. A review commit is no task's
`pushed_sha`, so such a layer can never be packaged again. The delegate
pushed it by hand and ran `saffron adopt`.

The same gap stopped `SA-0303`'s first batch. The adopted `SA-0302` recorded
no pushed sha, so `_resolve_stack_base` refused the child.

## Done looks like

`ready_task` accepts a tree base that some task's branch carries above its
`pushed_sha`. `saffron adopt` records the adopted head as the task's pushed
sha. A batch whose PACKAGE raised exits 2.

## Record

- 2026-10-23: filed from the spec loop's run 46.
- 2026-10-25: done in #961 (`SA-0313`), #964 (`SA-0315`) and #966 (`SA-0316`), from the
  spec loop's run 48. `adopt` records the adopted head, `ready_task` stacks on a
  branch at origin that carries the tree base, and a batch whose PACKAGE raised exits 2.
