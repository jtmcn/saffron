---
id: SA-0025
title: PACKAGE has no concept of a parent, so a stacked child's pull request opens against the wrong branch and re-applies its parent's hunks
type: feature
priority: 2
depends_on:
  - SA-0022
touches:
  - saffron/phases/package.py
  - tests/test_package.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/cell/**
  - saffron/cli.py
  - saffron/scheduler.py
  - saffron/reconcile.py
  - saffron/gates/**
  - saffron/report/**
budget_usd: 16
max_attempts: 4
max_turns: 140
risk: elevated
---

## Context
`SA-0022` gave a task two bases and one name for the second: `CellSpec.tree_base`
is `base_sha` unstacked and the parent's head otherwise, and every consumer
inside the cell takes it from there. `patch.json` records both. Nothing resolves
a real parent yet — `saffron/cli.py` sets `stacked_on=None`.

PACKAGE has never seen a second base. It fetches the remote's default-branch
head, applies the task's patch there, and opens the pull request against it
(§5.7). This spec teaches it a parent, and **turns nothing on**: no caller
passes one. `SA-0026` resolves a real parent and widens the dependency gate.

That order is not arbitrary. A cell that stacks while PACKAGE still targets the
default branch would open a pull request whose patch is relative to a tree the
base does not have — so the capability has to exist, inert, before anything can
produce it. `SA-0022` made the same argument for the same reason.

**The first attempt at this spec is why it is now two.** Ledger task 24,
2026-08-31, `NOT_IMPLEMENTED` at $14.61: the plan was accepted and was good —
it estimated **520 lines** against `size`'s 600-line ceiling — and the agent hit
the 140-turn ceiling at turn 141 while trimming the diff to fit. It had made
**zero commits**, so `teardown: no commits, nothing to export` and the entire
run was lost. Its plan survives at `~/.saffron/batches/v0/SA-0025/plan.json`
and is worth reading: the approach below is largely its own.

## Problem
- **The pull request opens against the wrong branch.** A stacked child's diff
  against the default branch is the parent's work plus the child's, and a
  reviewer approves a change nobody wrote.
- **The patch is applied against the wrong base.** `package.py` reads
  `patch.json["base_sha"]` — the run's pin. For a stacked child the patch is
  relative to `tree_base`, so applying it at `base_sha` puts parent-relative
  hunks on a tree without the parent's commits: `MERGE_FAILED` at best, an apply
  that looks right at worst. `SA-0022` recorded `tree_base` beside `base_sha`
  precisely so this read can be made correct (backlog item 33).
- **Re-verification turns a noisy diff into a wrong merge.**
  `needs_reverification`/`reverify` re-fetch the default branch and re-apply. A
  parent that merged in between turns "apply the child's patch" into "apply the
  parent's diff a second time".
- **A parent branch does not hold still.** Between the child's start and its
  push the parent may merge, be force-updated, or be deleted. Each is a
  different outcome and none may quietly open a pull request against a branch
  that is not there.

## Acceptance criteria
- [ ] `package()` takes an optional parent branch; omitted — which is every
      caller in this spec — every existing behaviour is unchanged, and a test
      asserts an ordinary unstacked package is byte-identical to today's
- [ ] With it set, the pull request is opened against that branch, and the test
      asserts the base the pull request was **opened with**, never the base the
      code was handed
- [ ] The patch is applied against `patch.json`'s `tree_base`, witnessed by a
      `patch.json` whose `tree_base` and `base_sha` differ — equal values would
      pass whichever key were read
- [ ] A parent whose commits are already in the fetched default branch falls
      back to the ordinary target rather than re-applying its hunks, and a test
      drives that sequence rather than asserting on a flag
- [ ] A parent branch that has disappeared, or moved to a commit the mirror
      cannot reach, is a task failure naming which of the two, never a pull
      request opened against a branch that is not there
- [ ] **Nothing in this spec passes a parent branch.** `saffron/cli.py` is
      forbidden here, and a test asserts the packaging path an operator can
      reach today is unstacked
- [ ] PACKAGE still reads its policy and gates at `fetch_head`: a test asserts
      the parent did not move that (backlog item 16)
- [ ] `docs/BACKLOG.md` records what re-verification should use as a stacked
      child's baseline — a decision, not a silence, and item 33 already names
      it as this spec's to make
- [ ] Every new test runs with no network and no cell

## Out of scope
**Resolving a real parent, and the dependency gate.** Both are `SA-0026`;
`saffron/cli.py` and `saffron/scheduler.py` are forbidden here. Criterion 6 is
what keeps this half from shipping a path it cannot serve.

**The two bases themselves.** `SA-0022` owns `CellSpec`, `worktree.py` and the
patch export; `saffron/cell/**` is forbidden. If the second base is wrong at the
seam that is a bug against `SA-0022`, not a licence to edit it.

**A squash-merged parent.** A mirror-local `git merge-base --is-ancestor` check
cannot recognise one: GitHub's squash creates new commit objects, so a
squash-merged parent whose branch was then deleted reads as "gone without
merging". The first attempt's plan named this and declined to solve it, which is
right — resolving it needs GitHub's own merge record. Name it in `BACKLOG.md`
under criterion 8 rather than building around it.

**Multi-node DAG ordering, and the merge train.** K=1; nothing here merges
anything (§6.1).

## Notes for the agent
**Commit after every coherent step, before you run anything by hand.** This is
not the usual closing line: the previous attempt at this spec made zero commits
across 141 turns and lost all of it at teardown, $14.61 for nothing. The gates
run against `/work`, but `export_patch` diffs commits — uncommitted work is
invisible to the record and dies with the cell. Commit first, verify second.

**Your budget is the turn ceiling, not the dollars.** The previous attempt
stopped at 141 turns with $5.39 unspent. Reading a file twice costs a turn as
surely as writing one.

**`package()` receives the intake `Spec`, not the `CellSpec`.** It reads
`spec.title`, which `CellSpec` has not got, and `CellOutcome` carries no base
either — so `stacked_on` is not reachable from here. The parent's branch arrives
as your new argument, and `SA-0026` is what will pass it.

**`tree_base` is in `patch.json` already.** `SA-0022` put it there for this
read. `package.py:526` currently takes `["base_sha"]`; both keys are present and
equal for every task that exists today, which is exactly why a test whose two
values differ is the only one that proves anything.

**Backlog item 16 is a trap with your name on it.** PACKAGE verifies under a
policy read at `fetch_head` and nothing says which; criterion 7 exists because
adding a base is the change that would quietly move it.

**The documentation half is by hand, and this spec has none.** `DESIGN.md` §5.7
describes PACKAGE resolving one base; it stays true until `SA-0026` turns
stacking on, and `SA-0026` carries the sentences.
