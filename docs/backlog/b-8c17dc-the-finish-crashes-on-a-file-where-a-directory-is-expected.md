---
id: b-8c17dc
title: "The finish raises an uncaught `NotADirectoryError` when a path component below the worktree is a file"
status: open
tier: 3
filed: 2026-10-09
specs: []
prs: [786]
commits: []
cites: []
related: [b-8d654b]
---

## Problem

Found by #786's Spec seat in the spec loop's run 32, not probed.

`_refuse_symlink` walks each path component with `lstat`
(`saffron/finish.py:118`). When a component below the worktree is a regular
file, `lstat` on the next one raises `NotADirectoryError`. `_stack_finish`
catches only `GitError` and `ValueError` (`saffron/cli.py:829`), so the batch
ends with a traceback. The base's `write_text` raised the same error, so
`SA-0239` added no new crash. Its spec put the `OSError` exit out of scope.

## Done looks like

The finish reports such a path as a refusal with one printed line, like a
symlink. A test commits a regular file named `.saffron/specs`.

## Record

- 2026-10-09: filed from the spec loop's run 32.
