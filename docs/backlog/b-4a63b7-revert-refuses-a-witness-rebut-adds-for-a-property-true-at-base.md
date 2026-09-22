---
id: b-4a63b7
title: '`revert` refuses a witness REBUT adds for a property already true at base, so a sound fix ends `EXHAUSTED`'
status: open
tier: 1
filed: 2026-09-22
specs: [SA-0118]
prs: [433]
commits: []
cites: [§5.4]
related: [103, b-2750d5, b-66e82d]
---

## Problem

Found in the spec loop's run 13, 2026-09-22.

The adequacy lens on `SA-0118` named a probe that hard-codes `fmt="sha1"`, and
the probe survived every witness. REBUT added
`test_export_patch_reads_a_worktree_whose_own_object_format_is_sha256`. That
witness kills the probe. It also passes with `saffron/cell/worktree.py`
reverted, measured on host git 2.54 and on the cell's 2.39.5.

`revert` exempts only a witness that a criterion declares `preserves`
(`saffron/gates/core/revert.py:109-112`). A test REBUT adds belongs to no
criterion, so `revert` failed it. REBUT does not re-enter the repair loop, and
the task ended `EXHAUSTED` at $10.45 of $20 with a correct diff. The operator
kept the branch and opened #433 by hand.

## Done looks like

A test that REBUT adds to kill a surviving probe is judged by what it kills.
`revert` does not require it to fail at base, or REBUT is told the rule before
it writes one. A witness drives both halves.

## Record

- 2026-09-22: filed from the spec loop's run 13.
