---
id: SA-0022
title: a task has one word for two bases, so a patch exported from a stacked worktree carries its parent's diff
type: feature
priority: 2
depends_on:
  - SA-0020
touches:
  - saffron/cell/session.py
  - saffron/cell/worktree.py
  - saffron/cli.py
  - tests/test_session.py
  - tests/test_worktree.py
  - tests/test_cli.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/phases/**
  - saffron/scheduler.py
  - saffron/reconcile.py
  - saffron/gates/**
  - saffron/report/**
budget_usd: 16
max_attempts: 4
max_turns: 120
risk: elevated
---

## Context
§4.2 states the dependency rule as one sentence with two halves: **all `depends_on`
tasks have reached `READY_FOR_REVIEW`** — not `MERGED` — and *"a dependent task
branches off its parent's branch rather than `base_sha` — stacked branches."*
`SA-0020` shipped the half that needs no stacking: a dependent whose parent is
already in the default branch is admitted, because the child is cut from that
branch and the parent's commits are in it.

Stacking is the other half, and it was one spec until this one was split. The
seam is a single fact:

> For a stacked task, `worktree.prepare_worktree` checks out `spec.stacked_on`
> (the parent's own unmerged branch head, ahead of `base_sha`), but the exported
> patch — the task's sole durable product — is still computed as
> `worktree.export_patch(container, spec.base_sha)`, so it captures the parent's
> entire diff plus the child's own.

That is the `contract` lens on `SA-0020`'s first attempt: ledger task 20,
`EXHAUSTED` at $14.43 against a $16 budget, 2026-08-30, patch at
`~/.saffron/batches/v0/SA-0020/patch.diff`. It passed every gate on attempt 1
and could not fix the finding, because `saffron/phases/**` was forbidden to it
and the insufficiency only became visible after the plan checkpoint — §5.3.1's
stated ceiling on the scope-proposal door.

**This spec builds the two bases and nothing that uses them.** `SA-0025` resolves
a real parent, teaches PACKAGE to target its branch, and widens the gate. Split
because those are the criteria that killed the first attempt, and because a
mechanism with no production trigger can be witnessed exactly and reviewed
cheaply.

## Problem
- **The patch is computed against the wrong base the moment the worktree is not.**
  `export_patch(container, spec.base_sha)` is correct exactly while the worktree
  starts at `base_sha`. Anything that moves the checkout breaks that identity and
  nothing downstream notices, because every consumer reads the patch and not the
  tree.
- **One word for two bases is the defect, not a symptom of it.** A stacked task
  has a pin for the run (`base_sha`, which the gates and policy are exported
  from) and a starting point for the tree. Today those are the same field, so
  there is no way to be right about both.
- **`base_sha` is load-bearing in more places than the patch.** The gate
  executables and the policy declaring them are exported from `base_sha` (§5.4,
  backlog item 13). A stacked worktree tests a tree the parent has changed using
  gates the parent has not — a real disagreement this spec must record even
  though it does not resolve it.

## Acceptance criteria
- [ ] `CellSpec` carries a second base distinct from `base_sha`, defaulting to
      the shape every caller produces today, and `saffron/cli.py` sets it at the
      one place `CellSpec` is constructed
- [ ] A worktree created with that second base set contains the parent's commits,
      and the witness is a real branch with real commits rather than a sha handed
      to the assertion
- [ ] A patch exported from such a worktree contains **only the commits made on
      top of that base** — the parent's diff is not in it — witnessed by a real
      two-commit parent branch with a child committed on top
- [ ] With the second base unset, the worktree, the exported patch and the
      recorded `base_sha` are byte-identical to today's, and a test asserts it
- [ ] `saffron/cli.py` leaves the second base unset: **nothing in this spec
      stacks a real task.** A test drives `saffron cell` on a spec with a
      `depends_on` and asserts the cell is not stacked, so the half-built path
      cannot be reached by an attended run, which does not pass gate 0
- [ ] Where a stacked worktree and `base_sha`-exported gates disagree,
      `docs/BACKLOG.md` records which wins and why — a decision, not a silence
- [ ] Every new test runs with no network and no cell

## Out of scope
**Resolving a real parent, PACKAGE, and the dependency gate.** All three are
`SA-0025`, and `saffron/phases/**` and `saffron/scheduler.py` are forbidden here.
A pull request opened against the wrong base is the defect `SA-0025` exists to
prevent; this spec must not ship a path that reaches it, which is what criterion
5 is for.

**Changing what `base_sha` means.** It is the run's pin and four other things
depend on it (§5.4, items 13 and 15). This spec adds a second reference point; it
does not redefine the first.

**Multi-node DAG ordering within one batch.** K=1.

## Notes for the agent
**`saffron/cli.py` is in `touches` because `CellSpec` is built in exactly one
place, and it is there** (`cli.py`, the sole construction site). A field nothing
sets is a field that does not exist, and criterion 4's byte-identity claim is
about that call. The earlier draft of this spec omitted `cli.py` and would have
failed `scope` after the plan checkpoint — the ceiling `SA-0020`'s first attempt
died on.

**Read `SA-0020`'s first patch before starting.**
`~/.saffron/batches/v0/SA-0020/patch.diff` already contains a working
`spec.stacked_on` and a worktree that checks it out. Its `cli.py` hunks resolve a
real parent, which is `SA-0025`'s and not yours: take the shape, not the wiring.

**Name the second base once and make every consumer take it from the same
place.** The defect is that two things share one word. A fix that adds a second
word and then lets one caller keep guessing has not removed it.

**A test that constructs the value it then asserts on proves nothing about the
caller.** Build a real parent branch with real commits and a real child on top,
then read the exported patch — do not assert on the sha the code was handed.

**The documentation half is by hand, and this spec has none.** Backlog item 30's
rule: `DESIGN.md` and `CONTEXT.md` describe the dependency gate and the phases,
neither of which changes here. `SA-0025` carries the sentences.

Commit after each coherent step. Uncommitted work dies with the cell.
