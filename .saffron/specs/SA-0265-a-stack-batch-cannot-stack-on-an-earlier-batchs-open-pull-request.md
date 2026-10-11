---
id: SA-0265
title: "A stack batch refuses a spec whose parent is an earlier batch's open pull request, so the operator merges a stack before the next batch runs"
type: feature
priority: 2
depends_on: [SA-0254]
estimated_lines: 500
estimate_measured: true
touches:
  - saffron/scheduler.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/finish.py
  - tests/test_scheduler.py
  - tests/test_cli.py
  - tests/test_batch.py
  - tests/test_finish.py
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
  - saffron/end_review.py
  - saffron/follow_up.py
  - saffron/reconcile.py
  - saffron/phases/**
budget_usd: 48
max_attempts: 3
max_turns: 200
risk: standard
acceptance:
  - claim: >-
      Under `stack=True`, `build_queue` takes a spec whose `depends_on` names
      a parent outside the order and off the default branch, when that
      parent's newest task in a `DEPENDENCY_WAITING_STATES` state records a
      branch and a resolved pushed sha. That parent is the stack base, and
      every spec of the order carries it. A parent whose push landed is on
      the default branch, and then no spec carries a base. The witness drives
      each of the three waiting states. It puts an older waiting task with no
      push and a newer `EXHAUSTED` task beside the base's own.
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
      Under `stack=True`, a spec whose parent has no pushed branch to stack
      on is refused. Its reason names the parent, says it has no pushed
      branch, and names the remedy: merge it, or run it to a pull request
      first. The witness drives four such parents. One has no task. One has
      a waiting task with no push. One has a pushed task in a dead state.
      One has a waiting, pushed task that records no branch.
    witness: tests/test_scheduler.py::test_a_stack_order_refuses_a_parent_it_cannot_stack_on_and_names_the_remedy
    mutant:
      file: saffron/scheduler.py
      find: DEPENDENCY_WAITING_STATES = frozenset({"READY_FOR_REVIEW", "APPROVED", "MERGE_TRAIN"})
      replace: DEPENDENCY_WAITING_STATES = frozenset({"READY_FOR_REVIEW", "APPROVED", "MERGE_TRAIN", "EXHAUSTED"})
    wrong_versions:
      - The reason is the old one, with no remedy and no word of a pushed branch.
      - A waiting task with no recorded push is taken as the base.
      - A waiting task that records no branch is taken as the base.
      - A pushed task in any state is taken as the base.
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
  - claim: >-
      Given no predecessor, `_stack_runner`, `_stack_review` and
      `_stack_revise` each fetch the stack base's branch and seed there. The
      runner's `Handoff` names that branch and its fetched head. Each spec
      session's cell starts at that head. A predecessor still outranks the
      base, and a spec with neither seeds at `base_sha` as before. The
      witness drives all three callables in all three cases.
    witness: tests/test_cli.py::test_a_stack_batchs_spec_with_no_predecessor_is_seeded_on_the_pull_request_its_order_stacks_on
    wrong_versions:
      - The runner ignores the base and hands an empty `Handoff`.
      - The spec review seeds at `base_sha` despite the base.
      - The spec writer seeds at `base_sha` despite the base.
      - The base outranks a predecessor, so a later layer is cut from the base.
  - claim: >-
      `run_stack_batch` records the stack base's task as the first layer's
      predecessor, at that task's pushed sha. Every later layer's predecessor
      stays the layer below it. `end_review.layer_fields` then starts the
      first layer's range at the base's pushed sha, not at the run's
      `base_sha`.
    witness: tests/test_batch.py::test_a_stacks_first_layer_records_the_earlier_pull_request_it_stacks_on
    mutant:
      file: saffron/ledger.py
      find: predecessor_head = pred_row["pushed_sha"]
      replace: predecessor_head = None
    wrong_versions:
      - The first layer records no predecessor, so its range starts at `base_sha`.
      - Every layer records the base as its predecessor.
  - claim: >-
      Gate 0's open pull request check, as `run_stack_batch` runs it, exempts
      the stack base's branch for a revised spec of the order and for a
      follow-up. Another open pull request still refuses each. The witness
      drives a revised spec and a follow-up that overlap each pull request.
    witness: tests/test_batch.py::test_a_follow_up_and_a_revised_spec_on_an_earlier_pull_request_are_not_refused_on_it
    mutant:
      file: saffron/scheduler.py
      find: "if branch == own_branch or branch in exempt_branches:"
      replace: "if branch == own_branch:"
    wrong_versions:
      - The base's branch is exempt for neither.
      - A revised spec of the order is refused on the base's pull request.
      - A follow-up is refused on the base's pull request.
  - claim: >-
      When a stack's first layer stacks on a base, `publish_finish` expects
      that layer's pull request to target the base's branch. It pushes when
      the pull request does, and escalates naming that branch when it
      targets the default branch. `link_stack` then runs no `gh` and returns
      one line saying nothing is linked. The witness drives both targets and
      the link.
    witness: tests/test_finish.py::test_a_stack_on_an_earlier_pull_request_is_finished_against_its_branch_and_never_linked
    mutant:
      file: saffron/finish.py
      find: base = view.stdout.strip() if view.returncode == 0 else None
      replace: base = None
    wrong_versions:
      - The first layer's pull request is still expected to target the default branch.
      - "`link_stack` links the stack anyway, with the default branch as `--base`."
---

## Context

Backlog item **b-e0e1cf**, under `DESIGN.md` §4.2 and §4.2.1, and ADR 7.
Every line below was read at `0a5e3e5c`. `SA-0245`, `SA-0258`, `SA-0253`
and `SA-0254` edit `saffron/cli.py` before this spec runs, so its line
numbers can move. Find each function by name.

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
branch and a resolved `pushed_sha` (`saffron/task.py:299-308`). It
fetches the branch fresh for the head (`saffron/task.py:310`).
`saffron/task.py:78` imports from `saffron/scheduler.py`, so the scheduler
cannot import the task module back.

**The first layer starts at the default branch.** Its predecessor is
`None` until a layer exists (`saffron/batch.py:462`). `run_stack_batch`
hands that to the runner, the review and the revise (`:568`, `:696`,
`:738`).
Given `None`, `_stack_runner` hands `run_task` an empty `Handoff`
(`saffron/cli.py:610-611`). `_stack_review` and `_stack_revise` each seed
their cell at the pinned `base_sha` (`saffron/cli.py:925-926`,
`:1011-1012`). A `Candidate` carries a path, a spec, a `spec_sha` and a
`task_id`, and nothing about its stack (`saffron/scheduler.py:131-148`).

**The first layer records no predecessor.** `record_layer` passes
`predecessor_task_id`, which starts `None` (`saffron/batch.py:463`,
`:497-503`). `record_stack_layer` bakes in the predecessor's record key
and `pushed_sha` (`saffron/ledger.py:1607-1615`). `layer_fields` gives a
layer with no predecessor its run's `base_sha` as `base`, and any other
layer its `predecessor_head` (`saffron/end_review.py:116-124`). Each
end-review prompt states the range as `{base}..{head}`
(`saffron/agents/prompts/end-review-spec.md:69`,
`end-review-standards.md:65`, `end-review-join.md:48`).

**Gate 0 inside the batch exempts only this batch's layers.**
`layer_branches` starts empty (`saffron/batch.py:482`). A follow-up meets
`open_pr_refusal` against it (`saffron/batch.py:550-556`), and so does a
revised spec of the order (`saffron/batch.py:650-655`).

**The finish expects the first layer on the default branch.**
`publish_finish` reads each layer's pull request base back. It wants the
predecessor's branch when the predecessor is a layer of this batch, and
the default branch otherwise (`saffron/finish.py:383-397`). A
`stack_layers` row carries the predecessor's key and head, not its branch
(`saffron/ledger.py:1637-1644`). `link_stack` passes every layer's URL to
`gh stack link --base <default>` (`saffron/finish.py:64-67`). Run 4
read that a list without the pull request below would retarget the bottom
one onto `main`, and linked by hand instead
(`docs/evidence/2026-09-16-spec-loop-skill-feedback-run-4.md:57-61`).
`gh stack link --help` says `--base` names the bottom's base branch, and
defaults it to the default branch (gh-stack, read on the host 2026-10-10).

## Problem

The operator chose to stack on the earlier pull request. A stack batch
takes a parent that is an earlier batch's open pull request. The ledger
records it at a waiting state with a pushed branch. The stack's first
layer is seeded from that branch, and its pull requests are based on it.

1. **The stack base.** Under `stack=True`, `build_queue` finds each
   parent a kept spec names. It keeps those outside the kept specs and off
   the default branch. For each, it reads the parent's tasks the way
   `_resolve_stacked_on` does without a `gh`. A parent qualifies when its
   newest waiting task records a branch and a resolved `pushed_sha`. The
   lowest qualifying id is the stack base, and `_stack_order` counts it
   satisfied. Every taken spec carries the base when one of them names it.
   Read the waiting states from `DEPENDENCY_WAITING_STATES`, never a copy.
2. **The refusals.** A parent with no pushed branch keeps the refusal, and
   the reason names the remedy. A second qualifying parent refuses its
   dependents, naming the base and the remedy.
3. **Seeding.** With no predecessor, the runner, the spec review and the
   spec writer fetch the base's branch fresh and seed there.
4. **The layers.** The first layer's predecessor is the base's task. The
   base's branch joins the exempt set the batch's own gate 0 checks use.
5. **The finish.** The first layer's pull request must target the base's
   branch. `link_stack` links nothing for such a stack and says so.

**Decision: the end review and the finish leave the earlier pull
request's commits alone.** They are not graded and not finished.

- The end review reads each layer's own commit, `head^..head`
  (`saffron/end_review.py:249-254`). The join reads from the bottom
  layer's parent, `bottom^..top` (`saffron/end_review.py:450-459`).
  Neither range reaches below this batch's first layer. Criterion 5 makes
  the first layer's stated `base` the earlier head too. Those commits
  already passed their own in-cell lenses, and their own end review when
  a stack batch made them.
- The finishing commit writes this batch's layers' and unrun follow-ups'
  spec texts alone (`saffron/finish.py:139-175`). An earlier stack
  batch's finish wrote its own. `publish_finish` checks this batch's layers'
  heads and bases, and the first layer's base becomes the earlier branch.
- `link_stack` links nothing. A list without the earlier pull request
  would retarget the first layer onto the default branch, as run 4 read.
  Linking onto the earlier branch with `--base` was never tried. Each pull request already targets the branch below it, so
  the stack stays reviewable, and the operator links it by hand.

## Out of scope

- `saffron queue --stack` naming the base. `SA-0254` owns that output.
- A plain batch. Its gate and `_resolve_stacked_on` are unchanged.
- Checking the base branch's remote head at the finish. A hand push to
  the earlier pull request mid-batch leaves this stack on a stale head.
  ADR 7's principle 21 residual says the same of a layer.
- A spec of the order that reaches the base through no `depends_on`
  chain. Gate 0 still refuses it when its `touches` overlap the base's
  pull request, as `_refuse` checks before the order exists
  (`saffron/scheduler.py:995-1006`).
- A parent below the base in the earlier stack. It refuses its dependents
  as a second parent does, though the base's branch holds its code.
- The stack view. Its first layer's predecessor still shows the
  placeholder (`saffron/report/stack.py:115-118`, `:258-261`).
- `DESIGN.md`, `CONTEXT.md` and ADR 7. The operator edits them by hand.

## Notes for the agent

**Each mutant sits on a line the change keeps.** Every criterion edits
existing code. Criteria 1 and 2 mutate the waiting set the base
must read. Criterion 5 mutates the head the ledger bakes in. Criterion 6
mutates `open_pr_refusal`'s exemption. Criterion 7 mutates the base
`publish_finish` reads back. Leave those lines unedited. Criteria 3 and 4
judge only code this change writes, so they declare no mutant, and
`witness` will report `skip` for them. The wrong versions under each
criterion are what its witness must kill. Do not run them yourself.

**Import new names inside each test.** `tests/test_batch.py:18` imports
`tests/test_scheduler.py`. So a new name imported at module scope there
turns both reverted runs into collection errors. Import the new names inside each witness.

**An existing test asserts the refusal this spec lifts.**
`test_a_stack_order_refuses_a_spec_with_any_dependency_outside_it_and_names_each`
records a push for its waiting `TE-41` (`tests/test_scheduler.py:2127`).
That parent now qualifies. Drop the push, so `TE-41` stays a parent with
no pushed branch, and keep every assertion.

**Shape, as the prototype measured it.**

- `saffron/scheduler.py`: a frozen `StackBase` of `spec_id`, `task_id`
  and `branch`, and a `stack_base` field on `Candidate` defaulting to
  `None`. A resolved sha is 40 or 64 hex digits, as
  `saffron/cell/session.py:311` spells it.
- `saffron/cli.py`: one helper returns the branch a spec is seeded on.
  It is the predecessor's branch, else the base's, else `None`. All three
  callables use it.
- `saffron/batch.py`: read the base from the order once, before the
  loop. It seeds `predecessor_task_id` and `layer_branches`.
- `saffron/finish.py`: for a layer whose predecessor is not a layer of
  this batch, read that task's branch by its record key. `end_review.py`
  reads `ledger._db` the same way (`saffron/end_review.py:117`).
  `saffron/ledger.py` is forbidden, since `.saffron/policy.yaml` elevates
  any diff that touches it.

**Fixtures.**

- Criteria 1 to 3: `_write_spec`, `_task_at` and `record_push` in
  `tests/test_scheduler.py`. Build each waiting state's case in its own
  directory and ledger. A task with no branch needs `create_task` with
  `branch=""`.
- Criterion 4: `_spec_session_rig` in `tests/test_cli.py`. Its fake
  fetch returns `d` times 40 for any branch but `saffron/SY-8`. Replace
  `spec_review.run_spec_review`, `spec_review.run_spec_writer` and
  `cli.run_task`. Build the base's candidate with `dataclasses.replace`.
- Criteria 5 and 6: `ScriptedRunner` and `StackDoubles` in
  `tests/test_batch.py`. Record the base's task with `set_task_package`
  at `READY_FOR_REVIEW`.
- Criterion 7: `_stack(root, 2)` in `tests/test_finish.py`. Open a
  second batch whose one layer reuses the top branch, with the bottom
  task as its predecessor. Run it once with its pull request on the
  bottom branch and once on `trunk`.

**Measured on a prototype.** A prototype at `0a5e3e5c` passed all seven
witnesses and `make check`. Each witness failed with the four source files
reverted. Its diff measured 1999 changed tokens. Every wrong version above
was applied as an edit, and so was each declared mutant. Each failed its
own criterion's witness.
