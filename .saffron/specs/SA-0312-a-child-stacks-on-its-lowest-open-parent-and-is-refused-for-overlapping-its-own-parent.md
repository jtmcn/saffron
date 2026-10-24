---
id: SA-0312
title: "A child stacks on its lowest open parent, and is refused for overlapping its own parent"
type: feature
priority: 2
estimated_lines: 320
estimate_measured: true
touches:
  - saffron/scheduler.py
  - saffron/task.py
  - tests/test_scheduler.py
  - tests/test_cli.py
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
  - saffron/batch.py
  - saffron/finish.py
  - saffron/end_review.py
  - saffron/reconcile.py
  - saffron/intake.py
  - saffron/phases/**
budget_usd: 34
max_attempts: 3
max_turns: 170
risk: standard
acceptance:
  - claim: >-
      `build_queue` stacks a child on its deepest open parent. That is the
      open parent whose own `depends_on` chain holds every other open
      parent. A parent merged or retired to `done/` is not open and needs
      no place on the chain. The order of `depends_on` changes nothing.
      Under `stack=True` the deepest parent is the order's stack base, and
      the parents on its chain need no place in the order. Without it, the
      child is a candidate. The witness drives all 120 orders of five
      parents, in both modes. Three are open on one chain, and the deepest
      of them has neither the lowest id nor the highest. The fourth is
      merged, and the fifth retired. A second arrangement has one child
      naming only a parent on the base's chain, beside a child naming the
      base that the order refuses. The first child still carries the stack
      base.
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
      the way the scan picks it. `cli._run_cell` reaches it with a `gh`,
      and `cli._batch_runner` without one. Each parent's chain comes from
      the specs at `base_sha` in the mirror, never from the working copy.
      A parent whose task has merged needs no place on the chain. The
      witness drives both orders of four parents, three open on one chain
      and one merged. It reads each parent from the ledger alone, and again
      through a `gh` that reports the fourth parent merged.
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
  - claim: >-
      `run_task` with no handoff returns `Refused` before any cell starts
      when the open parents lie on no one chain. The reason names each open
      parent off the deepest parent's chain, and no parent on it. The
      witness drives three open parents, two on one chain. It reads them
      from the ledger alone, and again through a `gh`.
    witness: tests/test_cli.py::test_an_attended_cell_whose_open_parents_lie_on_no_one_chain_is_refused_before_any_cell
    wrong_versions:
      - The cell stacks on the deepest parent and starts anyway.
      - The off-chain case unstacks the cell and starts it on `base_sha`.
      - The reason names every open parent but the deepest.
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
a taken spec names it (`saffron/scheduler.py:1348-1351`).

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

**Run 46 met both.** `SA-0305` declared `[SA-0303, SA-0304, SA-0306]`, and
`SA-0306` sat on `SA-0303`. `SA-0304` had merged. Batch 49 refused
`SA-0305` at $0 for overlapping #941, `SA-0306`'s own pull request. #943
reordered `depends_on` by hand. The dry run in the notes reproduces it.

**The attended path stacks on slot zero, a separate choice.**
`run_task` calls `_resolve_stacked_on` when no handoff is given
(`saffron/task.py:528-540`). That function reads `depends_on[0]` alone
(`saffron/task.py:213`, `:261`). `cli._run_cell` calls `run_task` with no
handoff and a `gh` (`saffron/cli.py:648-659`). `cli._batch_runner` calls
it with neither (`saffron/cli.py:696-706`). `cli._stack_runner` passes a
`Handoff` built from the batch's order (`saffron/cli.py:795-800`), so a
stack batch never reaches `_resolve_stacked_on`.

**What else chooses a base or walks parents, and stays.**
`cli._seed_branch` cuts a layer from its predecessor or the stack base
(`saffron/cli.py:711-722`). `batch.run_stack_batch`'s `blocking` reads
each entry of a candidate against the missed tasks
(`saffron/batch.py:579-584`). `_stack_order` takes a spec once every entry
is taken or satisfied (`saffron/scheduler.py:1095-1146`). None of them
picks among parents, so this spec leaves them alone.

## Problem

1. **One rule for the deepest open parent.** An open parent is a
   `depends_on` entry not merged and not retired. Its chain is every spec
   a walk of `depends_on` reaches from it, through every entry and every
   link, with the cycle guard kept. The deepest open parent is the one
   whose chain holds the most other open parents. A tie goes to the lower
   id. Any open parent off its chain makes the spec unstackable.
2. **The stack base.** `_resolve_stack_base` picks the deepest among the
   qualifying parents outside the order. The external parents on its
   chain count as satisfied in `_stack_order`. The base is carried when
   a taken spec names it or a parent on its chain. A second qualifying
   parent off the chain refuses its dependents, as now. That reason names
   every parent off the chain.
3. **The overlap exemption.** It covers every branch the full walk
   reaches from the candidate.
4. **The plain scan's refusal.** Without `stack=True`, a candidate whose
   open parents lie on no one chain is refused under `depends_on`. The
   reason names the parents off the chain.
5. **The attended path.** `_resolve_stacked_on` reads every entry the way
   it reads slot zero now, with `gh` or without. It stacks on the deepest
   parent with a stackable row. Each parent's chain comes from the spec
   files at `base_sha` in the mirror. Off-chain parents make `run_task`
   return `Refused` before any cell starts.

## Out of scope

- A stack layer with no `depends_on` path to the stack base. Gate 0 still
  refuses it when it overlaps the base's pull request.
- Choosing the stack base again once the order refuses the spec naming it.
- `cli.py`, `batch.py` and the `Handoff` a stack batch passes.
- The spec loop's driver. Its `_cite_base` and `_depends_on_chain` still
  read slot zero (`.claude/skills/run-saffron-spec-loop/driver.py:2352-2355`,
  `:638-645`). A cell cannot edit that directory.
- A parent's chain read through `specs/done/`. A retired spec is merged,
  so it ends the walk.
- `DESIGN.md`, `CONTEXT.md`, ADR 6 and ADR 7. This spec's pull request edits
  them by hand.

## Notes for the agent

**Mutants.** Criteria 1 to 4 each mutate a line the change keeps. Leave
each such line unedited. Criterion 5's refusal is new code, so it declares
no mutant, and `witness` will report `skip` for it. Criterion 6 holds a
test that exists, with one edit named below. The wrong versions under
each criterion are what its witness must kill. Do not run them yourself.

**Three tests assert the old rule.** The `census` gate fails a test that
is renamed or removed, so keep each name and rewrite its assertions.

- `tests/test_scheduler.py:715`, the second dependency test. Its child's
  open parents lie on no one chain now, so assert the `depends_on`
  refusal naming its second parent and not the grandparent.
- `test_only_the_first_depends_on_entry_is_a_stacking_candidate`
  (`tests/test_cli.py:1130`) and
  `test_the_adapter_stacks_on_the_first_dependency_only`
  (`tests/test_cli.py:6158`). In each, the first entry has no task, so it
  is not open. Each now stacks on the second entry's pushed head.
- `tests/test_scheduler.py:788`, criterion 6. Only its last direct call
  of the walk changes, to the new map's shape.
- `tests/test_refusal_count.py:45` pins three `depends_on` sites. The plain
  scan's new refusal is a fourth.

**Shape, as the prototype measured it.** One pure helper in
`saffron/scheduler.py` returns the deepest open parent and the parents off
its chain. `_refuse`, `_resolve_stack_base` and `task.py` all call it. The
attended refusal travels as an exception that `run_task` turns into
`Refused`. A `Refused` return from `_resolve_stacked_on` failed the `ty`
hook, since tests in `tests/test_cli.py` unpack its tuple. Read the spec
files only when `depends_on` has two or more entries. A base the mirror
cannot export reads as no edges. The adapter test at
`tests/test_cli.py:6173` passes a `base_sha` no repository holds.
`_recorded_spec_text` already exports it from the mirror
(`saffron/task.py:356-428`).

**Prose.** An edited sentence in an old docstring or comment is a new
`prose` hit. Keep each one under 25 words, each comment to two lines and
each docstring to ten. The prototype's first `make check` failed on four
such edits.

**Fixtures.** `_write_spec`, `_task_at`, `set_task_package`, `_sha` and
`_fake_gh` in `tests/test_scheduler.py`. `_local_origin`,
`_push_parent_branch`, `_mirror_of`, `_seed_repo` and `_seed_task` in
`tests/test_cli.py`. Commit the parents' spec files before cutting the
mirror, then drop their `depends_on` in the working copy. Give each mode
of the attended witnesses its own ledger file. `tests/test_batch.py:18`
imports `tests/test_scheduler.py`, so add nothing at its module scope.

**Measured on a prototype at `af2831e8`.** It passed all six witnesses and
`make check`. Each new witness failed at `af2831e8`. Its source diff
measured 1277 changed tokens. Every wrong version above was applied as an
edit, and so was each declared mutant. Each failed its own witness. A dry
run of batch 49's arrangement refused `SA-0305` for #941 at `af2831e8`.
With the prototype it took `SA-0305` on stack base `SA-0306`, in three
orders of `depends_on`.
