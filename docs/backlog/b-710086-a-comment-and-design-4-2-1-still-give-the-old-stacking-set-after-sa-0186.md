---
id: b-710086
title: A scheduler comment and DESIGN §4.2.1 still give the stacking set SA-0186 changed
status: open
tier: 3
filed: 2026-09-28
closed:
specs: []
prs: []
commits: []
cites: [§4.2, §4.2.1]
related: [b-877e93]
---

## Problem

Found in the spec loop's run 20, 2026-09-28, by #562's seats (`SA-0186`).

After #562 the `saffron cell` path also stacks on `CHANGES_REQUESTED`
(`saffron/task.py:62` at `5479ddb6`). A newest task at `MERGED` or `REJECTED`
unstacks a child (`:237`). Two texts forbidden to `SA-0186` still say otherwise.

- `saffron/scheduler.py:605-610` says any row still waiting satisfies the
  dependency, and names `_resolve_stacked_on` as what stacks on it.
- `DESIGN.md` §4.2.1 (line 394) gives the stacking set as `READY_FOR_REVIEW`,
  `APPROVED` or `MERGE_TRAIN`.

## Done looks like

The comment and §4.2.1 name `CHANGES_REQUESTED` on the reconcile path. They say
that a `MERGED` or `REJECTED` newest task unstacks the child.

## Record

- 2026-09-28: filed from the spec loop's run 20.
