---
id: b-bc54d1
title: '`SA-0100` left three things by operator decision: DESIGN''s one writer, a +0/−0 row, and an unshielded write'
status: open
tier: 2
filed: 2026-09-18
specs: [SA-0100]
prs: []
commits: []
cites: [§6, §5.7]
related: [165, b-990bd9, 171]
---

## Problem

Found in the spec loop's run 7, 2026-09-18, reviewing #339 (`SA-0100`). The
operator left each out of #339 on purpose. Line numbers below are at
`origin/saffron/SA-0100`.

- **`DESIGN.md` names one writer.** `DESIGN.md:1207` says PACKAGE appends a
  `QueueLine` per task. After #339, `run_task` appends one too, for a task that
  never reached PACKAGE (`saffron/task.py:357`).
- **A pushed unpackaged row reads `+0/−0`.** That write passes `added=0` and
  `removed=0`. A task whose work `push_unpackaged_work` pushed has a diff on
  its branch, and the row hides it.
- **The new write is not shielded.** `append_queue_line` in `run_task`'s
  `else:` can raise `OSError`. That turns a task's exit 1 into exit 2.
  `push_unpackaged_work` "Never raises" for this reason: its leftovers "must not
  become an infrastructure exit" (`saffron/phases/package.py:1037-1041`).
  `_finish` at `:955` has the same exposure.

## Done looks like

- `DESIGN.md` §6 names both writers of a `QueueLine`.
- An unpackaged row whose branch was pushed carries that branch's diff stat.
- A failed index write after a failed task is reported and leaves exit 1.
  `_finish` gets the same treatment, or a comment says why not.

## Record

- 2026-09-18: filed from the spec loop's run 7 (stack #335 ← #338 ← #339 ←
  #342 ← #340). Surfaced by #339.
