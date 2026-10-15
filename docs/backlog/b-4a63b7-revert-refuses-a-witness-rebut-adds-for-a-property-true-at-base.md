---
id: b-4a63b7
title: '`revert` refuses a witness REBUT adds for a property already true at base, so a sound fix ends `EXHAUSTED`'
status: done
closed: 2026-10-15
tier: 1
filed: 2026-09-22
specs: [SA-0118, SA-0273]
prs: [433, 881]
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
- 2026-10-10: deferred by the operator. The operator chose the arm where `revert`
  exempts a test REBUT added to kill a probe. A spec writer stopped at step 1.
  REBUT records no kill, because no probe runs after REBUT (ADR 3). `revert` also
  judges before any verdict session reads the rebuttal (`rebut.py:717`). So that
  arm needs a probe run after REBUT and before `rerun_gates`, which amends ADR 3.
- 2026-10-11: specced as `SA-0273`. A probe runs again after a rebuttal that
  moved HEAD. `revert` exempts a test REBUT added that kills a probe there, at
  the re-run and at PACKAGE. ADR 3 and `DESIGN.md` §5.4 and §5.6
  are amended by hand in the same branch.
- 2026-10-15: the spec loop's run 40 packaged `SA-0273` as #881. A probe runs
  again after a rebuttal that moved HEAD, and `revert` exempts each test the
  rebuttal added that killed one. The task itself ended `EXHAUSTED` at $50.91
  of $45, because REBUT ran out of its $10 (b-4901d2).
