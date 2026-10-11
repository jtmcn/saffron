---
id: SA-0267
title: "A stack order refuses a parent that is an earlier batch's open pull request, and names no remedy"
type: feature
priority: 2
depends_on: [SA-0265]
estimated_lines: 353
estimate_measured: true
touches:
  - saffron/scheduler.py
  - tests/test_scheduler.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - harness/**
  - records/**
  - hooks/**
  - images/**
  - saffron/record/**
  - saffron/view/**
  - saffron/report/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/ledger.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/finish.py
  - saffron/end_review.py
  - saffron/reconcile.py
  - saffron/phases/**
budget_usd: 30
max_attempts: 3
max_turns: 150
risk: standard
acceptance:
  - claim: >-
      Under `stack=True`, `build_queue` takes a spec whose `depends_on` names
      a parent outside the order and off the default branch, when that
      parent's newest task in a `DEPENDENCY_WAITING_STATES` state records a
      branch, a resolved pushed sha and a pull request URL. That parent is
      the stack base, and its `StackBase` names that newest waiting task.
      Every spec of the order carries the stack base. A parent whose push
      landed is on the default branch, and then no spec carries a stack
      base. The witness drives each of the three waiting states. It puts an
      older waiting task with no push and a newer `EXHAUSTED` task beside
      the stack base's own.
    witness: tests/test_scheduler.py::test_a_stack_order_stacks_on_an_earlier_batchs_pushed_pull_request
    mutant:
      file: saffron/scheduler.py
      find: DEPENDENCY_WAITING_STATES = frozenset({"READY_FOR_REVIEW", "APPROVED", "MERGE_TRAIN"})
      replace: DEPENDENCY_WAITING_STATES = frozenset({"APPROVED", "MERGE_TRAIN"})
    wrong_versions:
      - Only a `READY_FOR_REVIEW` task makes a stack base, so an `APPROVED` or `MERGE_TRAIN` parent is refused.
      - A parent whose push landed on the default branch is still taken as the stack base.
      - The stack base is set only on the specs whose `depends_on` names it.
      - The oldest waiting task is read, so the stack base names a task with no push.
      - The newest task of any state is read, so a newer `EXHAUSTED` task hides the waiting one.
  - claim: >-
      Under `stack=True`, a spec whose parent cannot be a stack base is
      refused. Its reason says the parent is outside the stack order, names
      the cause, and ends with that cause's remedy. With no task, no pushed
      sha or no branch, the remedy is to run it to a pull request first.
      With no pull request URL it is `saffron adopt <id> <pr>`. With no
      waiting task it is to merge it, or rerun it. The witness drives seven
      parents. One has no task. One has a waiting task with no push. One
      has a pushed task at `REJECTED`, and one at `EXHAUSTED`. One has a
      waiting, pushed task with no branch, and one has no pull request URL.
      The last has a newest waiting task with no push above an older one
      that qualified.
    witness: tests/test_scheduler.py::test_a_stack_order_refuses_a_parent_it_cannot_stack_on_and_names_the_remedy
    mutant:
      file: saffron/scheduler.py
      find: DEPENDENCY_WAITING_STATES = frozenset({"READY_FOR_REVIEW", "APPROVED", "MERGE_TRAIN"})
      replace: DEPENDENCY_WAITING_STATES = frozenset({"READY_FOR_REVIEW", "APPROVED", "MERGE_TRAIN", "EXHAUSTED"})
    wrong_versions:
      - The reason is the old one, with no cause and no remedy.
      - A waiting task with no recorded push is taken as the stack base.
      - A waiting task that records no branch is taken as the stack base.
      - A waiting task with no pull request URL is taken as the stack base.
      - A pushed task in any state is taken as the stack base.
      - A pushed task at `REJECTED` is taken as the stack base.
      - Waiting tasks that qualify are filtered first and the newest of those is taken.
      - Every cause gets one remedy, to run it to a pull request first.
      - A dead parent is told to run it to a pull request first.
      - A parent whose pull request exists is said to have no pushed pull request.
  - claim: >-
      A stack has at most one stack base. Parents are read only for kept
      specs, so a spec refused by gate 0 names none. When two parents
      qualify, the lower id as a string is the stack base. A spec naming the
      other is refused. Its reason names both parents and both halves of the
      remedy, to merge it first, or run the spec in a later stack batch. A
      stack base that no taken spec names is set on no spec. The witness
      drives three arrangements. Two parents qualify. The spec naming the
      lower id is refused by gate 0. The stack base's one dependent is
      refused on another parent.
    witness: tests/test_scheduler.py::test_a_stack_order_stacks_on_one_earlier_pull_request_and_refuses_a_spec_naming_another
    wrong_versions:
      - The higher id is the stack base.
      - Every qualifying parent counts as satisfied, so both specs are taken on one stack base.
      - The stack base is set on the order even when the one spec naming it was refused.
      - The second parent's refusal names only the first half of its remedy.
      - Parents are read for every candidate, kept or not.
---

## Context

Backlog item **b-e0e1cf**, under `DESIGN.md` §4.2 and §4.2.1, and ADR 7.
`SA-0265` adds `StackBase` and `Candidate.stack_base`, and builds
everything that reads them. This spec sets the field. Every line below was
read at `0a5e3e5c`, before `SA-0265` adds the type above `Candidate`, so
line numbers in `saffron/scheduler.py` can move. Find each function by
name.

**The stack order refuses an open parent.** `build_queue` orders a stack
by `_stack_order(kept, retired | merged_anywhere)`
(`saffron/scheduler.py:1014`). `_stack_order` takes a spec once every
`depends_on` entry is taken or in that set (`saffron/scheduler.py:802-842`).
`_stack_dependency_reason` names each entry that is neither
(`saffron/scheduler.py:783-799`). Its filter is
`saffron/scheduler.py:793`. Its text says the parent is outside the stack
order and not on the default branch, and names no remedy. After batch 13,
that refused `SA-0206` on `SA-0205`, whose layer #689 was
`READY_FOR_REVIEW` and pushed.

**A plain batch already stacks on such a parent.** Its dependency gate
admits a parent with a task in `DEPENDENCY_WAITING_STATES`
(`saffron/scheduler.py:99`, `:631-632`). `task._resolve_stacked_on` then
picks the parent's newest task in those states, across every `spec_sha`
(`saffron/task.py:244-251`). It stacks only when that task records a
branch and a resolved `pushed_sha` (`saffron/task.py:299-308`).
`saffron/task.py:78` imports from `saffron/scheduler.py`, so the scheduler
cannot import the task module back.

**A row with no pull request is never reconciled.** `reconcile` skips a
row whose `pr_url` is empty (`saffron/reconcile.py:162`). Such a parent
never becomes `MERGED` or `REJECTED`, and a layer cut on it targets a
branch with no pull request. `tasks_by_spec_id` returns `branch` and
`pushed_sha` but no `pr_url` (`saffron/ledger.py:1079-1112`).
`tasks_by_repo` returns `pr_url` but no `branch`
(`saffron/ledger.py:1060-1077`). `build_queue` already reads
`tasks_by_repo` for `SA-0131`'s admission (`saffron/scheduler.py:937`).
`SA-0264` adds `saffron adopt`, which writes a `pr_url` onto such a row,
and changes neither method's columns.

## Problem

1. **The stack base.** Under `stack=True`, `build_queue` reads each parent
   that a kept spec names, outside the kept specs and off the default
   branch. A spec gate 0 refused is not kept, so it names no parent. For
   each parent, it reads the tasks the way `_resolve_stacked_on` does
   without a `gh`. The newest waiting task decides. The parent qualifies
   when that task records a branch, a resolved `pushed_sha` and a
   `pr_url`. The lowest qualifying id is the stack base, and its
   `StackBase` names that task. `_stack_order` counts it satisfied. Every
   taken spec carries the stack base when one of them names it. Read the
   waiting states from `DEPENDENCY_WAITING_STATES`, never a copy.
2. **The refusals.** A parent that does not qualify keeps the refusal. The
   reason keeps "outside the stack order", adds the first cause that
   failed, and ends with that cause's remedy, as criterion 2 lists. A
   second qualifying parent refuses its dependents, naming the stack base
   and both halves of the remedy.

## Out of scope

- A second parent whose dependents lose to the stack base. The stack base
  is chosen before the order. If the spec naming the lower id is refused
  by the order, on another parent, the other parent's dependents are still
  refused.
- A parent below the stack base in the earlier stack. It refuses its
  dependents as a second parent does, though the stack base's branch
  holds its code.
- A spec of the order that reaches the stack base through no `depends_on`
  chain. Gate 0 still refuses it when its `touches` overlap the stack
  base's pull request, as `_refuse` checks before the order exists
  (`saffron/scheduler.py:995-1006`). `SA-0265` owns the gate 0 exemption
  inside the batch.
- A parent that is itself a spec of the order, never taken. Its reason
  stays the old one, with no cause and no remedy.
- A row `saffron adopt` named a pull request for, whose head is not
  `saffron/<id>`. The stack base stacks on the row's own recorded branch.
- `saffron queue --stack` naming the stack base, and a plain batch.
- `DESIGN.md`, `CONTEXT.md` and ADR 7. The operator edits them by hand.

## Notes for the agent

**Each mutant sits on a line the change keeps.** Both mutate the waiting
set the stack base must read, one way each. Leave that line unedited.
Criterion 3 judges only code this change writes, so it declares no
mutant, and `witness` will report `skip` for it. The wrong versions under
each criterion are what its witness must kill. Do not run them yourself.

**An existing test keeps its refusal.**
`test_a_stack_order_refuses_a_spec_with_any_dependency_outside_it_and_names_each`
records a push for its waiting `TE-41` and no pull request URL
(`tests/test_scheduler.py:2127`). It stays refused under the URL rule.
Leave the test unchanged, and keep "outside the stack order" in every
such reason, since it asserts that text.

**Shape, as the prototype measured it.** A resolved sha is 40 or 64 hex
digits, as `saffron/cell/session.py:311` spells it. Read the pull request
URLs once from `tasks_by_repo`, keyed by task id, and look the newest
waiting task up there. One helper returns the `StackBase` or the cause
with its remedy, and the reason function appends the cause. The
prototype's remedy texts are "run it to a pull request first", "merge it,
or rerun it" and "run `saffron adopt <id> <pr>` first". A witness asserts
each cause and ends with its remedy. `saffron/ledger.py` is forbidden,
since `.saffron/policy.yaml` elevates any diff that touches it.

**Fixtures.** `_write_spec`, `_task_at` and `set_task_package` in
`tests/test_scheduler.py`. `set_task_package` records the branch, the
pushed sha and the pull request URL together. Pass an empty string for
the one a member lacks. Build each waiting state's case in its own
directory and ledger. Criterion 3's gate 0 arrangement gives the spec
naming the lower id a protected path in `touches`, and passes `protected`.
`tests/test_batch.py:18` imports `tests/test_scheduler.py`, so import
nothing new at module scope there.

**Measured on a prototype at `0a5e3e5c`, with `SA-0265`'s prototype
applied.** It passed all three witnesses and `make check`. Each witness
failed with `saffron/scheduler.py` set back to `SA-0265`'s. Its own diff
measured 1412 changed tokens. Every wrong version above was applied as an
edit, and so was each declared mutant. Each failed its own criterion's
witness.
