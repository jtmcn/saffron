---
id: SA-0312
title: "A child stacks on its lowest open parent, and is refused for overlapping its own parent"
type: feature
priority: 2
estimated_lines: 354
estimate_measured: true
touches:
  - saffron/scheduler.py
  - saffron/task.py
  - saffron/batch.py
  - tests/test_scheduler.py
  - tests/test_cli.py
  - tests/test_batch.py
  - tests/test_refusal_count.py
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
  - saffron/cli.py
  - saffron/events.py
  - saffron/finish.py
  - saffron/end_review.py
  - saffron/reconcile.py
  - saffron/intake.py
  - saffron/phases/**
budget_usd: 52
max_attempts: 3
max_turns: 220
risk: standard
acceptance:
  - claim: >-
      `build_queue` stacks a child on its deepest open parent. That is the
      open parent whose own `depends_on` chain holds every other open
      parent. A parent merged, retired to `done/`, or whose push landed is
      not open, and needs no place on the chain. The order of `depends_on`
      changes nothing. Under `stack=True` the deepest parent is the order's
      stack base, counted across every spec of the order. The parents on its
      chain need no place in the order, and the base carries their branches.
      Without `stack=True`, each candidate counts only its own parents. The
      witness drives all 120 orders of five parents, in both modes, with a
      sixth whose push landed while its task waits. Three are open on one
      chain, and the deepest of them has neither the lowest id nor the
      highest. The fourth is merged, and the fifth retired. A second
      arrangement has two children, one naming the base and one naming a
      parent on its chain, in both modes. A third refuses the child naming
      the base, and the other child still carries the stack base.
    witness: tests/test_scheduler.py::test_a_stack_order_stacks_on_the_deepest_open_parent_whatever_the_depends_on_order
    mutant:
      file: saffron/scheduler.py
      find: if any(row["state"] == DEPENDENCY_MERGED for row in rows)
      replace: if any(row["state"] == "APPROVED" for row in rows)
    wrong_versions:
      - The lowest qualifying id is the stack base, as before.
      - The highest qualifying id is the stack base.
      - The stack base is the `depends_on[0]` entry, or the last entry.
      - A parent's chain is read one hop up, so a parent two links below the deepest is off its chain.
      - The deepest parent is the stack base, but the parents on its chain are still refused as outside the order.
      - A merged parent counts as open, so it is off the chain and refuses the child.
      - A retired parent counts as open, so it is off the chain and refuses the child.
      - A parent whose push landed counts as open, so it is off the chain and refuses the child.
      - The stack base is chosen from the first spec's parents alone, so a second spec naming the deeper parent is refused.
      - The stack base carries no branches from its chain.
      - The stack base is carried only when a taken spec names the base itself.
  - claim: >-
      The open pull request overlap refusal exempts the branch of every
      spec a `depends_on` walk reaches from the candidate, through every
      entry and every link. So every declared open parent is exempt, and so
      is every parent on the chosen parent's chain. A pull request from a
      branch off that walk still refuses. The witness drives both modes. Its
      child names a shallower parent first, and the deepest second. A
      grandparent it never names also opens a pull request.
    witness: tests/test_scheduler.py::test_the_overlap_refusal_exempts_every_branch_on_the_chosen_parents_chain
    mutant:
      file: saffron/scheduler.py
      find: "if branch == own_branch or branch in exempt_branches:"
      replace: "if branch == own_branch:"
    wrong_versions:
      - The walk follows `depends_on[0]` alone, as before.
      - Only the declared parents are exempt, so an undeclared grandparent's pull request refuses the child.
      - Every open pull request is exempt.
  - claim: >-
      `run_stack_batch` exempts the stack base's chain branches wherever it
      exempts the base's own branch. A revised spec of the order and a
      follow-up each overlap the pull request of a spec on the base's
      chain, and neither is refused. Another open pull request still
      refuses each. The witness drives one revised spec and one follow-up.
    witness: tests/test_batch.py::test_a_revised_spec_and_a_follow_up_are_not_refused_on_a_pull_request_on_the_stack_bases_chain
    mutant:
      file: saffron/batch.py
      find: candidate, follow_up_prs, frozenset(layer_branches)
      replace: candidate, follow_up_prs, frozenset()
    wrong_versions:
      - The batch seeds its exempt set with the base's own branch alone, as before.
      - Only the follow-up recheck reads the chain, so a revised spec is still refused.
  - claim: >-
      A spec whose open parents lie on no one chain is refused before any
      cell, under the `depends_on` kind, in both modes. The reason names
      each open parent off the deepest parent's chain, and no parent on
      it. The deepest is the open parent whose chain holds the most other
      open parents, with the lower id on a tie. The witness drives one
      child of four open parents. Two of them form a chain, and the other
      two lie on none.
    witness: tests/test_scheduler.py::test_a_spec_whose_open_parents_lie_on_no_one_chain_is_refused_naming_the_parents_off_it
    mutant:
      file: saffron/scheduler.py
      find: if dep not in taken_ids and dep not in on_default_branch
      replace: if dep not in taken_ids
    wrong_versions:
      - Only a stack batch refuses it, and a plain scan admits the child.
      - The reason names every open parent but the deepest.
      - The reason under `stack=True` names only the first parent off the chain.
      - The lowest id is taken as the deepest, so the reason names the wrong parents.
  - claim: >-
      `run_task` with no handoff stacks a cell on the deepest open parent,
      by the scan's rule. A parent is open when it has a task that is not
      merged and not retired, and whose push has not landed at `base_sha`.
      A waiting parent with no push is open. `cli._run_cell` reaches this
      with a `gh`, and `cli._batch_runner` without one. Chains and
      retirement come from the specs at `base_sha` in the mirror, never the
      working copy. When the cell stacks, no `unstacked` line is printed.
      When the deepest parent has no push, the cell starts unstacked rather
      than refused. The witness drives both orders of six parents, from the
      ledger alone and through a `gh`. Three are open on one chain. One is
      merged, one retired, and one waits with its push in the base. A
      second arrangement has a deepest parent with no push.
    witness: tests/test_cli.py::test_an_attended_cell_stacks_on_its_deepest_open_parent_read_at_base
    mutant:
      file: saffron/task.py
      find: "    return head, branch"
      replace: "    return None, None"
    wrong_versions:
      - The cell stacks on `depends_on[0]`, or on the first parent with a stackable row.
      - The cell stacks on the lowest or the highest id among its open parents.
      - Each parent's chain is read from the working copy's spec files.
      - No chain is read, so two open parents always tie and refuse the task.
      - Only `depends_on[0]` is reconciled through `gh`, so a merged second parent still counts as open.
      - A waiting parent whose push landed in the base counts as open, so the task is refused.
      - A retired parent counts as open, so the task is refused.
      - A waiting parent with no push is not open, so the cell stacks on a shallower parent.
      - Each parent the cell does not stack on prints its own `unstacked` line.
  - claim: >-
      `run_task` with no handoff returns `Refused` before any cell starts in
      two cases. Its open parents lie on no one chain, and the reason names
      each one off the deepest parent's chain and none on it. Or an open
      parent on that chain has a pushed head that the deepest parent's
      fetched head does not contain, and the reason names that parent. The
      witness drives both cases, from the ledger alone and through a `gh`.
      The parent off the chain waits with no push.
    witness: tests/test_cli.py::test_an_attended_cell_whose_open_parents_lie_on_no_one_chain_is_refused_before_any_cell
    wrong_versions:
      - The cell stacks on the deepest parent and starts anyway.
      - The off-chain case unstacks the cell and starts it on `base_sha`.
      - The reason names every open parent but the deepest.
      - No head is checked, so a parent declared on the chain but missing from the branch is stacked past.
      - Each parent's head is checked against `base_sha` rather than the deepest parent's head.
  - claim: >-
      A `depends_on` cycle above a candidate still ends the walk. The scan
      returns, and reads both members of the cycle as ancestors.
    witness: tests/test_scheduler.py::test_a_dependency_cycle_does_not_hang_the_ancestor_walk
    preserves: true
---

## Context

Backlog item **b-1572e7**, under `DESIGN.md` §4.2 and §4.2.1, and ADR 7.
Related: b-c94a2f, a second `depends_on` entry that carries no code into
the cell. Every line below was read at `af2831e8`.

**The stack base is the lowest id.** `_resolve_stack_base` reads every
parent a kept spec names outside the order and off the default branch
(`saffron/scheduler.py:999-1020`). It picks the lowest qualifying id
(`saffron/scheduler.py:1044`). Every other qualifying id comes back for
`_second_stack_base_reason` (`saffron/scheduler.py:1048-1057`). Its text
says the base won "by the lower id" and names one other parent.
The scan counts only the base itself satisfied
(`saffron/scheduler.py:1340-1342`). It sets the base on the order only when
a taken spec names it (`saffron/scheduler.py:1348-1351`). `StackBase`
carries a spec id, a task id and one branch (`saffron/scheduler.py:155-168`).

**The overlap exemption walks one slot.** `build_queue` maps each spec to
its `depends_on[0]` (`saffron/scheduler.py:1270-1274`).
`_ancestor_branches` walks that map one link at a time, and `visited`
stops a cycle (`saffron/scheduler.py:230-265`). The scan passes the
result into `_refuse` (`saffron/scheduler.py:1308-1317`), and on into
`open_pr_refusal` (`saffron/scheduler.py:913`). That function skips only
those branches (`saffron/scheduler.py:859`).
`_depends_on_path` already walks every entry with its own guard
(`saffron/scheduler.py:737-754`). `_removed_name_refusals` builds that
full map (`saffron/scheduler.py:757-779`).

**A stack batch rechecks against the base's branch alone.**
`run_stack_batch` seeds `layer_branches` with the stack base's branch
(`saffron/batch.py:549-555`). The follow-up recheck passes that set to
`open_pr_refusal` (`saffron/batch.py:642-643`). So does the revised spec's
recheck, through `_revised_spec_refusal` (`saffron/batch.py:759-764`).

**Run 46 met both.** `SA-0305` declared `[SA-0303, SA-0304, SA-0306]`, and
`SA-0306` sat on `SA-0303`. `SA-0304` had merged. Batch 49 refused
`SA-0305` at $0 for overlapping #941, `SA-0306`'s own pull request. #943
reordered `depends_on` by hand. The dry run in the notes reproduces it.

**The attended path stacks on slot zero, a separate choice.**
`run_task` calls `_resolve_stacked_on` when no handoff is given
(`saffron/task.py:528-540`). That function reads `depends_on[0]` alone
(`saffron/task.py:213`, `:261`). Without a `gh`, a parent stacks only from
a waiting row with a branch and a resolved push (`saffron/task.py:262-266`).
`cli._run_cell` calls `run_task` with no handoff and a `gh`
(`saffron/cli.py:648-659`). `cli._batch_runner` calls it with neither
(`saffron/cli.py:696-706`). `cli._stack_runner` passes a `Handoff` built
from the batch's order (`saffron/cli.py:795-800`), so a stack batch never
reaches `_resolve_stacked_on`. `run_task` promises that a base the mirror
lacks raises `GitError` (`saffron/task.py:479`).

**The scan's rule for landed.** A parent is landed when one of its tasks
is `MERGED` at any `spec_sha` (`saffron/scheduler.py:1229-1233`). It is
also landed when `pushed_landed` finds a recorded push in the pin
(`saffron/scheduler.py:1236-1251`). A spec retired to `done/` is landed too
(`saffron/scheduler.py:582-583`).

**What else chooses a base or walks parents, and stays.**
`cli._seed_branch` cuts a layer from its predecessor or the stack base
(`saffron/cli.py:711-722`). `batch.run_stack_batch`'s `blocking` reads
each entry of a candidate against the missed tasks
(`saffron/batch.py:579-584`). `_stack_order` takes a spec once every entry
is taken or satisfied (`saffron/scheduler.py:1095-1146`). None of them
picks among parents, so this spec leaves them alone.

## Problem

1. **One rule for the deepest open parent.** An open parent is one not
   merged and not retired, whose push is not in `base_sha`. Its chain is every
   spec a walk of `depends_on` reaches from it, through every entry and
   every link, with the cycle guard kept. The deepest open parent is the
   one whose chain holds the most other open parents. A tie goes to the
   lower id. Any open parent off its chain makes the spec unstackable.
2. **The stack base.** `_resolve_stack_base` picks the deepest among the
   qualifying parents outside the order, counted across every spec of the
   order. The external parents on its chain count as satisfied in
   `_stack_order`. `StackBase` carries the branches of its chain. The base
   is carried when a taken spec names it or a parent on its chain. A
   second qualifying parent off the chain refuses its dependents, as now.
   That reason names every parent off the chain.
3. **The overlap exemption.** It covers every branch the full walk
   reaches from the candidate. `run_stack_batch` adds the base's chain
   branches to the exempt set it seeds.
4. **The plain scan's refusal.** Without `stack=True`, a candidate whose
   open parents lie on no one chain is refused under `depends_on`. It
   counts only its own parents. The reason names the parents off the chain.
5. **The attended path.** With two or more entries, `_resolve_stacked_on`
   applies the scan's rule. A parent counts only when it has a task, since
   the scan refuses one with none before this point. With a `gh`, it
   reconciles every entry first. It stacks on the deepest open parent, or
   starts unstacked when that parent has no push. Each on-chain parent's
   newest pushed sha must be an ancestor of the deepest parent's fetched
   head. Off-chain parents, or a missing ancestor, make `run_task` return
   `Refused` before any cell starts.

## Out of scope

- A stack layer with no `depends_on` path to the stack base. Gate 0 still
  refuses it when it overlaps the base's pull request.
- Choosing the stack base again once the order refuses the spec naming it.
- `cli.py` and the `Handoff` a stack batch passes.
- The head check inside a stack batch or the scan. Only `run_task` fetches
  a parent's head.
- An on-chain parent with no recorded push. There is no head to check.
- The spec loop's driver. Its `_cite_base` and `_depends_on_chain` still
  read slot zero (`.claude/skills/run-saffron-spec-loop/driver.py:2352-2355`,
  `:638-645`). A cell cannot edit that directory.
- A parent's chain read through `specs/done/`. A retired spec is merged,
  so it ends the walk.
- `DESIGN.md`, `CONTEXT.md`, ADR 6 and ADR 7. This spec's pull request edits
  them by hand.

## Notes for the agent

**Mutants.** Criteria 1 to 5 each mutate a line the change keeps. Leave
each such line unedited. Criterion 6's refusals are new code, so it
declares no mutant, and `witness` will report `skip` for it. Criterion 7
holds a test that exists, with one edit named below. The wrong versions
under each criterion are what its witness must kill. Do not run them
yourself.

**Four tests assert the old rule.** The `census` gate fails a test that
is renamed or removed, so keep each name. Rewrite its assertions, and its
docstring to match them.

- `tests/test_scheduler.py:715`, the second dependency test. Its child's
  open parents lie on no one chain now, so assert the `depends_on`
  refusal naming its second parent and not the grandparent.
- `test_only_the_first_depends_on_entry_is_a_stacking_candidate`
  (`tests/test_cli.py:1130`) and
  `test_the_adapter_stacks_on_the_first_dependency_only`
  (`tests/test_cli.py:6158`). In each, the first entry has no task, so it
  is not open. Each now stacks on the second entry's pushed head.
- `test_a_third_partys_overlap_still_refuses_a_stacked_child`
  (`tests/test_scheduler.py:616`). Its assertions hold, and its docstring
  names `depends_on[0]` alone.
- `test_a_dependency_cycle_does_not_hang_the_ancestor_walk`
  (`tests/test_scheduler.py:788`), criterion 7. Only its last direct call
  of the walk changes, to the new map's shape.
- `tests/test_refusal_count.py:45` pins three `depends_on` sites. The plain
  scan's new refusal is a fourth.

**Shape, as the prototype measured it.** One pure helper in
`saffron/scheduler.py` returns the deepest open parent and the parents off
its chain. `_refuse`, `_resolve_stack_base` and `task.py` all call it.
`StackBase` takes a defaulted field for the chain's branches, so the tests
that build one keep working. The attended refusal travels as an exception
that `run_task` turns into `Refused`. A `Refused` return from
`_resolve_stacked_on` failed the `ty` hook, since tests in
`tests/test_cli.py` unpack its tuple. Keep every `Preflight` emit inside
`_resolve_stacked_on`, and emit only for the parent it settles on.
`tests/test_package.py:1596-1606` reads that function's body for stream
writes. `saffron/events.py` names it as the source of those lines.

**Reading the base.** Filter the parents by the ledger and the mirror
first. Export `.saffron` at `base_sha` only when two or more remain. A
`GitError` from that export propagates, as `run_task` promises.
`_recorded_spec_text` already exports it from the mirror
(`saffron/task.py:356-428`). `scheduler._retired_ids` reads `done/` the way
the scan does. A push is in `base_sha` when `git merge-base --is-ancestor`
finds it there, the check `cli._pushed_landed` makes. The adapter test at
`tests/test_cli.py:6173` passes a `base_sha` no repository holds. Its one
parent with a task needs no export.

**Prose.** An edited sentence in an old docstring or comment is a new
`prose` hit. Keep each one under 25 words, each comment to two lines and
each docstring to ten. The prototype's first `make check` failed on four
such edits.

**Fixtures.** `_write_spec`, `_task_at`, `set_task_package`, `_sha` and
`_fake_gh` in `tests/test_scheduler.py`. `_local_origin`, `_mirror_of`,
`_seed_repo` and `_seed_task` in `tests/test_cli.py`. Commit the parents'
spec files before cutting the mirror, and cut each parent's branch from
its own first parent's branch. Then drop every `depends_on` in the
working copy. Give each mode of the attended witnesses its own ledger
file. The batch witness can follow
`test_a_follow_up_and_a_revised_spec_on_an_earlier_pull_request_are_not_refused_on_it`
(`tests/test_batch.py:5840`). `tests/test_batch.py:18` imports
`tests/test_scheduler.py`, so add nothing at its module scope.

**Measured on a prototype at `af2831e8`.** It passed all seven witnesses
and `make check`. Each new witness failed at `af2831e8`. Its source diff
measured 1415 changed tokens. Every wrong version above was applied as an
edit, and so was each declared mutant. Each failed its own witness. A dry
run of batch 49's arrangement refused `SA-0305` for #941 at `af2831e8`.
With the prototype it took `SA-0305` on stack base `SA-0306`, in three
orders of `depends_on`.
