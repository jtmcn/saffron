---
id: b-6b06e1
title: "A rebuilt outcome drops the `revert` exemption, so PACKAGE run alone ends `MERGE_FAILED`"
status: open
tier: 1
filed: 2026-10-11
specs: []
prs: []
commits: []
cites: [§5.6, §5.7]
related: [b-4a63b7, b-883f74]
---

## Problem

Found by the first review of `SA-0273`.

`SA-0273` exempts from `revert` a test REBUT added that killed a probe. The
cell carries that set on `CellOutcome.revert_exempt`, and PACKAGE hands it to
`reverify`. It also writes the set to `revert-exempt.json` in the task
directory.

Queued `SA-0266` rebuilds a `CellOutcome` for a task whose PACKAGE raised. A
rebuilt outcome that does not read `revert-exempt.json` carries an empty set.
Re-verification then runs `revert` over the same test, which passes with its
source reverted. The task ends `MERGE_FAILED` with a sound diff.

## Done looks like

A rebuilt outcome reads `revert-exempt.json` when the task directory holds one.
PACKAGE run alone then exempts the same tests the cell did. A witness drives
a task directory with the file and one without it.

## Record

- 2026-10-11: filed from `SA-0273`'s first spec review. `SA-0266` is not
  edited by that spec.
