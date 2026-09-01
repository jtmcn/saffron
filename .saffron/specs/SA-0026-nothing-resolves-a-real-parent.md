---
id: SA-0026
title: nothing resolves a real parent, so the dependency gate still refuses the states stacking was built to admit
type: feature
priority: 2
depends_on:
  - SA-0025
touches:
  - saffron/cli.py
  - saffron/scheduler.py
  - tests/test_cli.py
  - tests/test_scheduler.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/cell/**
  - saffron/phases/**
  - saffron/reconcile.py
  - saffron/gates/**
  - saffron/report/**
budget_usd: 14
max_attempts: 4
max_turns: 120
risk: elevated
---

## Context
Two specs built a mechanism nothing produces. `SA-0022` gave a task two bases
and `CellSpec.tree_base` to name the second; `SA-0025` taught PACKAGE to open a
pull request against a parent branch and to apply the patch against
`patch.json`'s `tree_base`. Both are deliberately inert: `saffron/cli.py` sets
`stacked_on=None` and passes no parent branch, so `tree_base is base_sha` on
every path an operator can reach.

This spec is the producer, and it is the last piece. §4.2's rule is the target:
**all `depends_on` tasks have reached `READY_FOR_REVIEW`** — not `MERGED` —
*"a dependent task branches off its parent's branch rather than `base_sha`."*
`SA-0020` shipped the merged-parent half, and `SA-0024`'s follow-up added a
parent retired to `specs/done/`. Both admit a parent whose work is **already in
the default branch**, which is the half that needs no stacking. The states
stacking exists for are still refused.

## Problem
- **The gate refuses exactly what the machinery was built to serve.**
  `READY_FOR_REVIEW`, `APPROVED` and `MERGE_TRAIN` are refused, with a reason
  that names the work as pending: *"a dependent is cut from the default branch,
  so it waits for the parent to land (stacking is SA-0022)."* Once stacking
  exists that sentence describes the opposite of what the gate does, and a gate
  whose refusal text contradicts its behaviour is the defect `SA-0020` was
  written to remove.
- **The parent's head is in the ledger and nothing reads it.** A task's
  `pushed_sha` is recorded at PACKAGE. That is the sha a dependent's worktree
  must be built on, and `CellSpec.stacked_on` has been waiting for it since
  `SA-0022`.
- **Two different facts, two different kinds.** The tree base is a **sha**
  (`CellSpec.stacked_on`, which `CellSpec` validates at construction); the pull
  request base is a **branch name** (`SA-0025`'s argument to `package()`).
  Resolving one and not the other ships a cell stacked on a parent whose pull
  request targets `main`.

## Acceptance criteria
- [ ] `saffron/cli.py` resolves a dependent's `stacked_on` from its parent's
      recorded `pushed_sha`, at the one place `CellSpec` is built, and leaves it
      `None` when the parent has no pushed branch — a spec whose parent never
      ran still gets an ordinary unstacked cell
- [ ] The same path passes the parent's branch to `package()`, so a task whose
      worktree was stacked cannot reach a pull request that is not
- [ ] The dependency gate admits a parent at `READY_FOR_REVIEW`, `APPROVED` or
      `MERGE_TRAIN`
- [ ] `SA-0020`'s refusal reasons for those three states are **replaced**, not
      left beside a gate that no longer refuses them — search the text, not just
      the state list
- [ ] A merged parent and a parent retired to `specs/done/` still admit their
      dependents exactly as they do today, witnessed against this repository's
      own specs directory
- [ ] Only the first `depends_on` entry is a stacking candidate (K=1), stated
      where the code is and covered by a test — a spec with two unmerged parents
      must not appear to stack on both
- [ ] A parent whose `pushed_sha` is absent, empty, or not a resolved sha yields
      an unstacked cell rather than a `CellSpec` that raises: `SA-0022` made
      that a construction-time error, and an operator's `saffron cell` must not
      die on it
- [ ] Every new test runs with no network and no cell

## Out of scope
**PACKAGE's own behaviour.** `SA-0025` owns `saffron/phases/**`, which is
forbidden here. This spec passes a parent branch; it does not decide what
PACKAGE does with it.

**The two bases.** `saffron/cell/**` is forbidden; `SA-0022` owns them.

**Multi-node DAG ordering within one batch.** K=1, and criterion 6 makes that
explicit rather than incidental. A grandchild is not in reach and must not be
half-built.

**The merge train, and what happens when a stacked parent is rejected.** §4.2
assigns the latter to §6.1 — *"one wasted task rather than three wasted
nights"*. A child stacked on a parent later rejected is a wasted task by design.

## Notes for the agent
**Commit after every coherent step, before you run anything by hand.** The first
attempt at this work's predecessor made zero commits across 141 turns and lost
all of it at teardown — $14.61 for nothing. `export_patch` diffs commits, so
uncommitted work is invisible to the record and dies with the cell.

**The gate's refusal text is its contract with the operator.** Criterion 4 is a
deletion as much as an addition. `_dependency_refusal` names this work as
pending in prose; leaving that while widening the state list is the exact defect
`SA-0020` removed.

**`_retired_ids` and `merged_anywhere` are not yours to rewrite.** They admit a
parent whose work is in the default branch and they are correct; this spec adds
a third route for parents whose work is not, and criterion 5 is what proves the
first two still work.

**The documentation half is by hand, and here are the sentences.** Backlog item
30's rule. `DESIGN.md` is forbidden, so an operator corrects these afterwards:

- §4.2.1's `depends_on` paragraph: *"Every other parent state is still refused,
  and the reason names the state it actually read."* Criterion 3 falsifies it
  for three states.
- §3.1's frontmatter example: `depends_on: [TE-0139] # satisfied at
  READY_FOR_REVIEW, see §4.2` — the design's stated intent, true for the first
  time once this ships.
- §5.7's description of PACKAGE resolving one base.
- `CONTEXT.md` owes an entry for the second base (`tree_base`), which item 33
  names and no spec has been able to reach.

**A test that constructs the value it then asserts on proves nothing about the
caller.** Build a real ledger row with a real `pushed_sha` and read what reaches
`CellSpec`; do not hand the resolver its own answer.
