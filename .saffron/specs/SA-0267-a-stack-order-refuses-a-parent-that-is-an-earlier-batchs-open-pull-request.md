---
id: SA-0267
title: "A stack order refuses a parent that is an earlier batch's open pull request, and names no remedy"
type: feature
priority: 2
depends_on: [SA-0265]
estimated_lines: 289
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
      the stack base, and every spec of the order carries it. A parent whose
      push landed is on the default branch, and then no spec carries a base.
      The witness drives each of the three waiting states. It puts an older
      waiting task with no push and a newer `EXHAUSTED` task beside the
      base's own.
    witness: tests/test_scheduler.py::test_a_stack_order_stacks_on_an_earlier_batchs_pushed_pull_request
    mutant:
      file: saffron/scheduler.py
      find: DEPENDENCY_WAITING_STATES = frozenset({"READY_FOR_REVIEW", "APPROVED", "MERGE_TRAIN"})
      replace: DEPENDENCY_WAITING_STATES = frozenset({"APPROVED", "MERGE_TRAIN"})
    wrong_versions:
      - Only a `READY_FOR_REVIEW` task makes a base, so an `APPROVED` or `MERGE_TRAIN` parent is refused.
      - A parent whose push landed on the default branch is still taken as the base.
      - The base is set only on the specs whose `depends_on` names it.
      - The oldest waiting task is read, so the base names a task with no push.
      - The newest task of any state is read, so a newer `EXHAUSTED` task hides the waiting one.
  - claim: >-
      Under `stack=True`, a spec whose parent has no pushed pull request to
      stack on is refused. Its reason names the parent, says it has no pushed
      pull request, and names the remedy: merge it, or run it to a pull
      request first. The witness drives six such parents. One has no task.
      One has a waiting task with a branch and a pull request but no push.
      One has a pushed task at `REJECTED`, and one at `EXHAUSTED`. One has a
      waiting, pushed task with no branch. One has a waiting, pushed,
      branched task with no pull request URL.
    witness: tests/test_scheduler.py::test_a_stack_order_refuses_a_parent_it_cannot_stack_on_and_names_the_remedy
    mutant:
      file: saffron/scheduler.py
      find: DEPENDENCY_WAITING_STATES = frozenset({"READY_FOR_REVIEW", "APPROVED", "MERGE_TRAIN"})
      replace: DEPENDENCY_WAITING_STATES = frozenset({"READY_FOR_REVIEW", "APPROVED", "MERGE_TRAIN", "EXHAUSTED"})
    wrong_versions:
      - The reason is the old one, with no remedy and no word of a pull request.
      - A waiting task with no recorded push is taken as the base.
      - A waiting task that records no branch is taken as the base.
      - A waiting task with no pull request URL is taken as the base.
      - A pushed task in any state is taken as the base.
      - A pushed task at `REJECTED` is taken as the base.
  - claim: >-
      A stack has at most one base. When two parents qualify, the lower id
      as a string is the base. A spec naming the other is refused, and its
      reason names both parents and the remedy: merge it first, or run the
      spec in a later stack batch. A base that no taken spec names is set on
      no spec. The witness drives both arrangements.
    witness: tests/test_scheduler.py::test_a_stack_order_stacks_on_one_earlier_pull_request_and_refuses_a_spec_naming_another
    wrong_versions:
      - The higher id is the base.
      - Every qualifying parent counts as satisfied, so both specs are taken on one base.
      - The base is set on the order even when the one spec naming it was refused.
      - The second parent's refusal names no remedy.
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

1. **The stack base.** Under `stack=True`, `build_queue` finds each
   parent a kept spec names. It keeps those outside the kept specs and off
   the default branch. For each, it reads the parent's tasks the way
   `_resolve_stacked_on` does without a `gh`. A parent qualifies when its
   newest waiting task records a branch, a resolved `pushed_sha` and a
   `pr_url`. The lowest qualifying id is the stack base, and
   `_stack_order` counts it satisfied. Every taken spec carries the base
   when one of them names it. Read the waiting states from
   `DEPENDENCY_WAITING_STATES`, never a copy.
2. **The refusals.** A parent with no pushed pull request keeps the
   refusal, and the reason names the remedy. A second qualifying parent
   refuses its dependents, naming the base and the remedy.

## Out of scope

- A second parent whose dependents lose to the base. The base is chosen
  before the order. If the spec naming the lower id is refused for another
  reason, the other parent's dependents are still refused.
- A parent below the base in the earlier stack. It refuses its dependents
  as a second parent does, though the base's branch holds its code.
- A spec of the order that reaches the base through no `depends_on`
  chain. Gate 0 still refuses it when its `touches` overlap the base's
  pull request, as `_refuse` checks before the order exists
  (`saffron/scheduler.py:995-1006`).
- `saffron queue --stack` naming the base, and a plain batch.
- `DESIGN.md`, `CONTEXT.md` and ADR 7. The operator edits them by hand.

## Notes for the agent

**Each mutant sits on a line the change keeps.** Both mutate the waiting
set the base must read, one way each. Leave that line unedited. Criterion
3 judges only code this change writes, so it declares no mutant, and
`witness` will report `skip` for it. The wrong versions under each
criterion are what its witness must kill. Do not run them yourself.

**An existing test asserts the refusal this spec lifts.**
`test_a_stack_order_refuses_a_spec_with_any_dependency_outside_it_and_names_each`
records a push for its waiting `TE-41` (`tests/test_scheduler.py:2127`).
Drop the push, so `TE-41` stays a parent with no pushed pull request, and
keep every assertion.

**Shape, as the prototype measured it.** A resolved sha is 40 or 64 hex
digits, as `saffron/cell/session.py:311` spells it. Read the pull request
URLs once from `tasks_by_repo`, keyed by task id, and look the newest
waiting task up there. `saffron/ledger.py` is forbidden, since
`.saffron/policy.yaml` elevates any diff that touches it.

**Fixtures.** `_write_spec`, `_task_at` and `set_task_package` in
`tests/test_scheduler.py`. `set_task_package` records the branch, the
pushed sha and the pull request URL together. Pass an empty string for
the one a member lacks. Build each waiting state's case in its own
directory and ledger. `tests/test_batch.py:18` imports
`tests/test_scheduler.py`, so import nothing new at module scope there.

**Measured on a prototype at `0a5e3e5c`, with `SA-0265`'s prototype
applied.** It passed all three witnesses and `make check`. Each witness
failed with `saffron/scheduler.py` set back to `SA-0265`'s. Its own diff
measured 1154 changed tokens. Every wrong version above was applied as an
edit, and so was each declared mutant. Each failed its own criterion's
witness.
