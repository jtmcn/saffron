---
id: b-542beb
title: An `integrity` comment, a `DESIGN.md` row and two test docstrings went stale after `SA-0118` and `SA-0121`
status: open
tier: 3
filed: 2026-09-22
by_hand: true
specs: [SA-0118, SA-0121]
prs: [433, 435]
commits: []
cites: [§5.4]
related: [103, 89]
---

## Problem

Found reviewing `SA-0118` (#433) and `SA-0121` (#435), 2026-09-22. Each
sentence sits outside its spec's `touches`.

- `saffron/gates/core/integrity.py:233-240` says a committed `.gitattributes` or
  a worktree setting renders every Python file as binary. After `SA-0118`
  neither reaches `export_patch`.
- `DESIGN.md` §5.4's gate-roles `size` row says a `-diff` attribute otherwise
  counts 0 and passes any ceiling. That overstates it now.
- `tests/test_scope.py:269-271` and `:298-301` cite `harness/recovery.py`'s
  `pinned_diff` as the home of the measured pins. After `SA-0121` they live
  only in `worktree.DIFF_FLAGS`.

## Done looks like

Each sentence says what the code does today. By hand, since `DESIGN.md` is
protected.

## Record

- 2026-09-22: filed from the spec loop's run 13.
