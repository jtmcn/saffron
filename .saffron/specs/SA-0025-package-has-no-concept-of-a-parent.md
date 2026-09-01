---
id: SA-0025
title: PACKAGE has no concept of a parent, so a stacked child's pull request opens against the wrong branch and re-applies its parent's hunks
type: feature
priority: 2
depends_on:
  - SA-0022
touches:
  - saffron/phases/package.py
  - saffron/scheduler.py
  - saffron/cli.py
  - tests/test_package.py
  - tests/test_scheduler.py
  - tests/test_cli.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/cell/**
  - saffron/reconcile.py
  - saffron/gates/**
  - saffron/report/**
budget_usd: 20
max_attempts: 4
max_turns: 140
risk: elevated
---

## Context
`SA-0022` gives a task two bases and one name for the second:
`CellSpec.tree_base` is `base_sha` unstacked and `stacked_on` otherwise, and
every consumer inside the cell — the worktree checkout, the patch export, the
commit subjects, the changed-file lists the `scope` gate and the critic read —
takes it from there. `base_sha` still pins what §5.4 says it pins: the gate
executables, the policy declaring them, `create_run`, and `patch.json`'s own
`base_sha` key, beside which `tree_base` is now recorded.

What `SA-0022` stops short of is a **resolver**: `saffron/cli.py` sets
`stacked_on=None` at the one place a `CellSpec` is built, so `tree_base` is
`base_sha` on every path an operator can reach and no real task stacks.

This spec turns it on. Three things have to become true in the same change or
the feature ships broken, which is why they are one spec and not three.

§4.2's rule is the target: **all `depends_on` tasks have reached
`READY_FOR_REVIEW`** — not `MERGED` — *"a dependent task branches off its
parent's branch rather than `base_sha`."* `SA-0020` shipped the merged-parent
half and its refusal reasons say so out loud, naming this spec's predecessor:
*"a dependent is cut from the default branch, so it waits for the parent to land
(stacking is SA-0022)."* Those reasons stop being true here and have to be
replaced rather than left contradicting the gate.

## Problem
- **PACKAGE resolves one base and applies one patch to it.** It fetches the
  remote's default-branch head (§5.7) and applies the task's patch there. A
  stacked child's pull request has to open against its parent's branch, or the
  diff GitHub renders is the parent's work plus the child's — and a reviewer
  approves a change nobody wrote.
- **Re-verification is where a noisy diff becomes a wrong merge.**
  `needs_reverification`/`reverify` re-fetch the default branch and re-apply.
  A parent that merged in between turns "apply the child's patch" into "apply
  the parent's diff a second time": a conflict at best, a silent double-land at
  worst. This is the one failure here that corrupts rather than annoys.
- **The gate still refuses the states stacking exists to admit.** Until it
  widens, the machinery has no producer: `READY_FOR_REVIEW`, `APPROVED` and
  `MERGE_TRAIN` are refused with a reason that names stacking as future work.
- **A parent that moves under a child is not a hypothetical.** The parent's
  branch head is read once; between that read and the child's push, the parent
  may merge, be force-updated, or be deleted. Each is a different outcome and
  none of them may silently produce a pull request against a branch that is gone.

## Acceptance criteria
- [ ] `saffron/cli.py` resolves a dependent's second base from the parent's
      recorded pushed branch head, at the one place `CellSpec` is constructed,
      and leaves it unset when the parent has no pushed branch
- [ ] A stacked task's pull request is opened against its parent's branch, so the
      diff GitHub renders is the child's alone, and a test asserts the base the
      pull request is opened with rather than the base the code was handed
- [ ] Re-verification of a stacked child whose parent merged in the meantime does
      not re-apply the parent's hunks, and a test drives that sequence — parent
      merges, child re-verifies — rather than asserting on a flag
- [ ] A parent branch that has disappeared or moved between the child's start and
      its push is reported as a task failure naming which, never a pull request
      opened against a branch that is not there
- [ ] The dependency gate admits a parent at `READY_FOR_REVIEW`, `APPROVED` or
      `MERGE_TRAIN`, and `SA-0020`'s refusal reasons for those states are
      replaced — a gate whose refusal text describes the opposite of what it does
      is the defect `SA-0020` was written to remove
- [ ] A merged parent and a retired parent still admit their dependents exactly
      as they do today, witnessed against this repo's own specs directory
- [ ] PACKAGE still reads its policy and gates at `fetch_head`, unchanged: a test
      asserts the second base did not move that
- [ ] Every new test runs with no network and no cell

## Out of scope
**The two bases themselves.** `SA-0022` owns `CellSpec`, `worktree.py` and the
patch export; `saffron/cell/**` is forbidden here. If the second base is wrong at
the seam, that is a bug against `SA-0022`, not a licence to edit it.

**What happens when a stacked parent is rejected.** §4.2 assigns it to the merge
train (§6.1) — *"one wasted task rather than three wasted nights"*. A child
stacked on a parent later rejected is a wasted task by design.

**Multi-node DAG ordering within one batch.** K=1; the scan only answers whether
one dependent is admissible now. A grandchild is not in reach and must not be
half-built.

**The merge train.** Nothing here merges anything (§6.1).

## Notes for the agent
**Three contracts `SA-0022` left you, and the first is a raise.**
`prepare_worktree` raises `ValueError` on a `stacked_on` that is present but
empty: a resolver that cannot find the parent must return `None`, never `""`,
because falling back to the pin would build the cell on the wrong tree while
everything downstream believed it was stacked. `stacked_on` is a sha resolved
host-side, never a ref name — it is interpolated into the seed script, and a
branch name is also a moving target between fetch and checkout. And
`patch.json` now carries both `base_sha` and `tree_base`; `package.py:526`
reads `base_sha` today, and **which of the two a stacked child's patch is
applied against is your decision to make explicitly**, not to inherit.

**Backlog item 33 names re-verification as your inheritance.** It is the second
`prepare_worktree` caller, and it builds its baseline and head worktrees from
the current default-branch head — the wrong baseline for a stacked child,
because the parent's commits are not in it. `SA-0022` could only record it;
`saffron/phases/package.py` is yours.

**Backlog item 16 is a trap with your name on it.** PACKAGE verifies under a
policy read at `fetch_head` and nothing says which; criterion 7 exists because
adding a base is exactly the change that would quietly move it.

**`spec.stacked_on` — or whatever `SA-0022` named it — is read, never
redefined.** `package()` already takes the `CellSpec`, so the parent's branch
reaches you without a new argument. If it genuinely does not, that is the
scope-proposal door at the plan checkpoint (§5.3.1), not an edit to
`saffron/cell/**`.

**Criterion 5 is a deletion as much as an addition.** `_dependency_refusal`'s
waiting branch names this work as pending. Search for the text, not just the
state list — the refusal reasons are the gate's contract with the operator.

**The documentation half is by hand, and here are the sentences.** Backlog item
30's rule. `DESIGN.md` is forbidden, so an operator corrects these afterwards:

- §4.2.1, the `depends_on` paragraph: *"Every other parent state is still
  refused, and the reason names the state it actually read."* Criterion 5
  falsifies it for three states.
- §3.1's frontmatter example: `depends_on: [TE-0139] # satisfied at
  READY_FOR_REVIEW, see §4.2` — the design's stated intent, true for the first
  time once this ships.
- §4.2's own stacking sentences, written in the present tense for a mechanism
  that did not exist. Check them against what this spec builds.

**A test that constructs the value it then asserts on proves nothing about the
caller.** Drive the pull request through `package()` and read the base it opened
with. `SA-0022` shipped a criterion witnessed by a test that handed
`export_patch` the base it then asserted on, so no mutation of Saffron could
fail it; the review caught it, and the fix was to make Saffron do the choosing
and assert on that. The same trap is one line away here: assert on the base the
pull request was *opened with*, never the one the code was handed.

Commit after each coherent step. Uncommitted work dies with the cell.
