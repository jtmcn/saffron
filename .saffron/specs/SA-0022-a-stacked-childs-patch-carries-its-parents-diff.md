---
id: SA-0022
title: a stacked child's exported patch carries its parent's diff, and PACKAGE re-applies it
type: feature
priority: 2
depends_on:
  - SA-0020
touches:
  - saffron/cell/session.py
  - saffron/cell/worktree.py
  - saffron/phases/package.py
  - saffron/scheduler.py
  - tests/test_session.py
  - tests/test_worktree.py
  - tests/test_package.py
  - tests/test_scheduler.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/reconcile.py
  - saffron/gates/**
  - saffron/report/**
budget_usd: 20
max_attempts: 4
max_turns: 140
risk: elevated
---

## Context
§4.2 states the dependency rule as one sentence with two halves: **all `depends_on`
tasks have reached `READY_FOR_REVIEW`** — not `MERGED` — and *"a dependent task
branches off its parent's branch rather than `base_sha` — stacked branches."*
`SA-0020` ships the half that needs no stacking: it admits a dependent whose
parent is already `MERGED`, so the parent's commits are in the default branch the
child is cut from. This spec is the other half — admitting at `READY_FOR_REVIEW`,
which requires stacking, and the reason the two were separated.

`SA-0020`'s first attempt built both together and was blocked on the seam.
Measured 2026-08-30, ledger task 20, `EXHAUSTED` at $14.43 with its patch at
`~/.saffron/batches/v0/SA-0020/patch.diff`. It passed every gate on attempt 1;
the `contract` lens then found this:

> For a stacked task, `worktree.prepare_worktree` checks out `spec.stacked_on`
> (the parent's own unmerged branch head, ahead of `base_sha`), but the exported
> patch — the task's sole durable product — is still computed as
> `worktree.export_patch(container, spec.base_sha)`, so it captures the parent's
> entire diff plus the child's own.

`saffron/phases/package.py` applies that combined patch onto a fresh checkout of
the **current** remote default branch to build the child's pull request. Once the
parent's own pull request merges separately, re-verification re-fetches a default
branch that already contains the parent's changes and applies the same hunks
again. The implementer could not fix it: `saffron/phases/**` was forbidden to
`SA-0020`, and the insufficiency only became visible after the plan checkpoint had
passed — §5.3.1's stated ceiling on the scope-proposal door.

## Problem
- **The patch is computed against the wrong base the moment the worktree is not.**
  `export_patch(container, spec.base_sha)` is correct exactly while the worktree
  starts at `base_sha`. Stacking breaks that identity and nothing else in the
  pipeline notices, because every consumer downstream reads the patch and not the
  tree.
- **PACKAGE has no concept of a parent.** It resolves one base — the remote's
  default-branch head (§5.7) — and applies one patch to it. A stacked child's
  pull request has to open against its parent's branch, not against `main`, or
  the diff GitHub renders is the parent's work plus the child's.
- **Re-verification is where it becomes a wrong merge rather than a noisy diff.**
  `needs_reverification`/`reverify` re-fetch the default branch and re-apply. A
  parent that merged in between turns "apply the child's patch" into "apply the
  parent's diff a second time" — a conflict at best, a silent double-land at
  worst.
- **`base_sha` is load-bearing in more places than the patch.** The gate
  executables and the policy that declares them are exported from `base_sha`
  (§5.4, backlog item 13). A stacked worktree tests a tree the parent has changed
  using gates the parent has not.

## Acceptance criteria
- [ ] A dependent task's worktree is created from its parent's pushed branch head,
      and a test asserts the parent's commits are present in the dependent's tree
- [ ] A stacked task's exported patch contains **only its own commits** — the
      parent's diff is not in it — and the witness is a real two-commit parent
      branch with a child committed on top, not a patch handed to the assertion
- [ ] A stacked task's pull request is opened against its parent's branch, so the
      diff GitHub renders is the child's alone
- [ ] Re-verification of a stacked child whose parent merged in the meantime does
      not re-apply the parent's hunks, and a test drives that sequence rather than
      asserting on a flag
- [ ] `SA-0020`'s gate admits a parent at `READY_FOR_REVIEW`, `APPROVED` or
      `MERGE_TRAIN` once stacking exists, and the refusal reasons `SA-0020`
      shipped for those states are replaced rather than left contradicting the
      gate
- [ ] Where a stacked worktree and `base_sha`-exported gates disagree, the spec
      records which wins and why in `docs/BACKLOG.md` — a decision, not a silence
- [ ] Every new test runs with no network and no cell

## Out of scope
**The dependency gate's admitting states for a merged parent.** `SA-0020` owns
that and shipped it; this spec widens the list, it does not rewrite the lookup.

**What happens when a stacked parent is rejected.** §4.2 assigns it to the merge
train (§6.1) — *"one wasted task rather than three wasted nights"*. A child
stacked on a parent that is later rejected is a wasted task by design.

**Multi-node DAG ordering within one batch.** K=1; the scan only answers whether
one dependent is admissible now.

**Changing what `base_sha` means.** It is the run's pin and four other things
depend on it (§5.4, items 13 and 15). This spec adds a second reference point for
a stacked task; it does not redefine the first.

## Notes for the agent
**Read `SA-0020`'s first patch before starting.**
`~/.saffron/batches/v0/SA-0020/patch.diff` already contains a working
`spec.stacked_on` and a worktree that checks it out. The half that was wrong is
downstream of it, and the finding above names the line.

**`export_patch`'s second argument is the whole defect.** A stacked task has two
bases and the code has one word for them. Whatever names the second, name it once
and make every consumer take it from the same place — `package.py` included, which
is why it is in `touches` here and was not in `SA-0020`.

**PACKAGE is forbidden to change what it reads at `fetch_head`.** Backlog item 16
records that PACKAGE verifies under a policy read at `fetch_head` and that nothing
says which; do not quietly move that while adding a base.

**A test that constructs the value it then asserts on proves nothing about the
caller.** Build a real parent branch with real commits and a real child on top,
then read the exported patch — do not assert on the sha the code was handed.

Commit after each coherent step. Uncommitted work dies with the cell.
