---
id: b-9eceda
title: '`EventLog` has no public path, and `failed` is one bit for two different faults'
status: open
tier: 3
filed: 2026-09-18
specs: []
prs: []
commits: []
cites: [§4.1]
related: [167, 46]
---

## Problem

Found in the spec loop's run 7, 2026-09-18, reviewing #342 (`SA-0103`). Line
numbers below are at `origin/saffron/SA-0103`.

**No public path.** `saffron/events.py:385` keeps the log's location in
`self._path`. To name the log in its warning, #342 re-derives
`out_dir / spec.id / "events.jsonl"` in `saffron/task.py:255-256`, under a
`ponytail:` that says so. A change to where `EventLog` writes would leave that
warning naming the wrong file.

**One bit, two faults.** `append` catches `OSError`, `RecursionError`,
`TypeError` and `ValueError` in one clause (`saffron/events.py:421`) and sets
`failed` for all four (`:426`). An `OSError` is a disk that stopped taking
writes. The other three are one event that could not be serialised, after
which the log keeps writing. No reader can word a warning that is true of both.

**Three log owners still never read it.** #342 reads `failed` in `run_task`
only. `_default_emit`'s log in `saffron/cell/session.py:802` and the two
fallbacks in `saffron/phases/package.py:624` and `:1046` never do. `SA-0103`'s
spec named these as left out.

**Two stale comments** name `cli.py` as a `run_one_cell` caller:
`saffron/cell/session.py:73-75` and `tests/test_session.py:984-985`.
`saffron/task.py` is the only caller. `SA-0103`'s spec named these too.

## Done looks like

- `EventLog` exposes its path, and `run_task`'s warning reads it. The
  `ponytail:` goes.
- A write that failed on the disk is told apart from an event that could not be
  serialised, and the warning says which.
- Every `EventLog` owner reads `failed`, or a comment at each says why not.
- Neither comment names `cli.py` as a caller of `run_one_cell`.

## Record

- 2026-09-18: filed from the spec loop's run 7 (stack #335 ← #338 ← #339 ←
  #342 ← #340). Surfaced by #342.
