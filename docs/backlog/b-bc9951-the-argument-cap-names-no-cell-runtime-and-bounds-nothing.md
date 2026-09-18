---
id: b-bc9951
title: The argument cap `SA-0104` measured names no cell runtime, and the constant bounds nothing
status: open
tier: 3
filed: 2026-09-18
specs: []
prs: []
commits: []
cites: [§5.4]
related: [154]
---

## Problem

Found in the spec loop's run 7, 2026-09-18, reviewing #335 (`SA-0104`). Line
numbers below are at `origin/saffron/SA-0104`.

**The measurement names no runtime.** `saffron/cell/worktree.py:447-450` sets
`_MAX_ARG_BYTES = 131_000`, "Measured against `saffron/cell-base:python`". It
does not say which cell runtime ran the image, apple/container or podman. An
oversize exec on apple/container wedged a cell before (item 154). The review
commit's comment on `_CHUNK_BYTES` concedes the gap (`:452-454`).

**Nothing reads the constant.** No code under `saffron/` uses
`_MAX_ARG_BYTES`. `_CHUNK_BYTES = 65_536` is neither derived from it nor checked
against it. The witness in `tests/test_worktree.py:1342` spells `131_000` again
as a literal. A later edit to one number leaves the other two stale.

**A retired word in an error.** `_fail_write` raises "writing {path}'s mutant
failed" (`saffron/cell/worktree.py:473`). That calls the mutated file a mutant,
which `CONTEXT.md`'s _Avoid_ list for **Mutant** forbids. The text predates
#335, which moved it.

## Done looks like

- The cap's comment names the cell runtime it was measured on, or it is
  measured on both.
- `_CHUNK_BYTES` is derived from `_MAX_ARG_BYTES` or asserted below it, and the
  witness reads the constant.
- `_fail_write`'s message names the file and the edit without calling the file
  a mutant.

## Record

- 2026-09-18: filed from the spec loop's run 7 (stack #335 ← #338 ← #339 ←
  #342 ← #340). Surfaced by #335.
