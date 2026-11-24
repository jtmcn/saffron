---
id: SA-0429
title: "`saffron adopt` refuses a `REBUTTAL_UNJUDGED` or `ORPHANED` task, so a by-hand pull request leaves its children refused"
type: feature
priority: 2
depends_on: [SA-0430]
estimated_lines: 362
estimate_measured: true
touches:
  - saffron/cli.py
  - saffron/ledger.py
  - tests/test_cli.py
  - tests/test_adopt_stack_layer.py
  - tests/test_ledger_fold_task.py
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
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/scheduler.py
  - saffron/regate.py
  - saffron/reconcile.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/phases/**
  - saffron/record/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/repos/**
  - tests/test_regate.py
  - tests/test_reconcile.py
  - tests/test_scheduler.py
  - tests/test_task.py
  - tests/test_session.py
  - tests/test_queued_specs.py
budget_usd: 42
max_attempts: 3
max_turns: 230
risk: elevated
acceptance:
  - claim: >-
      `saffron adopt` takes a newest task in `REBUTTAL_UNJUDGED` or
      `ORPHANED`. It records the pull request's url and its head as the
      task's `pushed_sha`, then re-gates the task once. Three re-gates keep
      the state: new failures on the adopted head, a decline, and zero new
      failures on another head. While a `REBUTTAL_UNJUDGED` state is kept,
      a `stack=True` `build_queue` scan refuses the child, and
      `task._resolve_stacked_on` with no `gh` raises `_StackingRefused`.
      The plain scan takes the child, as it does at base for a waiting
      parent. While an `ORPHANED` state is kept, the plain scan and the
      `stack=True` scan both take nothing. Each refuses the parent as
      `open_pr_on_spec` with a reason naming the adopted url, and the child
      as `depends_on` naming the parent. Adopted again with a fresh head that re-gates
      green, the task moves to `READY_FOR_REVIEW`. Both scans then take the
      child alone, the `stack=True` scan's `stack_base` names the adopted
      task and its branch, and the resolver fetches that branch. The
      witness drives four parent rows, none with a url. Three are
      `REBUTTAL_UNJUDGED`: one with a push recorded in that state, one whose
      only push came in an earlier state, and one with no push. The fourth
      is `ORPHANED` with no push. For the first row, a second red adopt of
      the same head on the same pull request finds the url already carried,
      and still leaves the child refused.
    witness: tests/test_cli.py::test_adopt_admits_a_rebuttal_unjudged_or_orphaned_tasks_child_only_after_a_green_regate
    wrong_versions:
      - "`ORPHANED` stays out of the states adopt takes."
      - "`REBUTTAL_UNJUDGED` stays out of the states adopt takes."
      - "The two states take the `READY_FOR_REVIEW` route: adopt records the url, keeps a resolved `pushed_sha`, and runs no re-gate."
      - "Adopt moves either state to `READY_FOR_REVIEW` without re-gating."
      - "Adopt re-gates either state but moves only `EXHAUSTED`, `NOT_IMPLEMENTED` and `MERGE_FAILED` on a green result."
      - "Adopt records a `REBUTTAL_UNJUDGED` task's head and url in the `EXHAUSTED` order, so the url's fact trusts the push."
      - "Adopt records the untrusted head before the url, so the url's fact trusts it again."
      - "The ledger writes the untrusted mark into the fact but its apply step still sets `pushed_in_state` to the row's state."
      - "An untrusted push leaves `pushed_in_state` as it stood, so the trust the url's fact gave the row stays."
      - "Adopt records the head untrusted only when the task carries no url yet, so a repeat adopt trusts it."
      - "Adopt records the head only when it differs from the row's `pushed_sha`, so a same-head repeat stays trusted through the url's fact."
      - "Adopt records a `REBUTTAL_UNJUDGED` head untrusted only when the row already holds a `pushed_sha`, and otherwise in the `EXHAUSTED` order."
    covers:
      - set: the parent rows adopt meets
        members:
          - member: "`REBUTTAL_UNJUDGED`, a push recorded in that state, no url (the `SA-0424` row)"
            driven_by: "An untrusted push leaves `pushed_in_state` as it stood, so the trust the url's fact gave the row stays."
          - member: "`REBUTTAL_UNJUDGED`, its only push recorded in an earlier state"
            driven_by: "Adopt records the untrusted head before the url, so the url's fact trusts it again."
          - member: "`REBUTTAL_UNJUDGED`, no push at all"
            driven_by: "Adopt records a `REBUTTAL_UNJUDGED` head untrusted only when the row already holds a `pushed_sha`, and otherwise in the `EXHAUSTED` order."
          - member: "`ORPHANED`, no push (the `SA-0423` row)"
            driven_by: "`ORPHANED` stays out of the states adopt takes."
      - set: the re-gates that keep the state
        members:
          - member: new failures on the adopted head
            driven_by: tests/test_cli.py::test_adopt_admits_a_rebuttal_unjudged_or_orphaned_tasks_child_only_after_a_green_regate
          - member: a decline that records nothing
            driven_by: tests/test_cli.py::test_adopt_admits_a_rebuttal_unjudged_or_orphaned_tasks_child_only_after_a_green_regate
          - member: zero new failures on another head
            driven_by: tests/test_cli.py::test_adopt_admits_a_rebuttal_unjudged_or_orphaned_tasks_child_only_after_a_green_regate
      - set: the adopts on one pull request
        members:
          - member: the first, with no url carried
            driven_by: tests/test_cli.py::test_adopt_admits_a_rebuttal_unjudged_or_orphaned_tasks_child_only_after_a_green_regate
          - member: a repeat red adopt of the same head, with the url carried
            driven_by: "Adopt records the head only when it differs from the row's `pushed_sha`, so a same-head repeat stays trusted through the url's fact."
          - member: a green re-adopt of a fresh head
            driven_by: tests/test_cli.py::test_adopt_admits_a_rebuttal_unjudged_or_orphaned_tasks_child_only_after_a_green_regate
      - set: the readers that refuse or admit the child
        members:
          - member: a plain `build_queue` scan
            driven_by: tests/test_cli.py::test_adopt_admits_a_rebuttal_unjudged_or_orphaned_tasks_child_only_after_a_green_regate
          - member: a `stack=True` `build_queue` scan, with its `stack_base`
            driven_by: "The ledger writes the untrusted mark into the fact but its apply step still sets `pushed_in_state` to the row's state."
          - member: "`task._resolve_stacked_on` with no `gh`"
            driven_by: tests/test_cli.py::test_adopt_admits_a_rebuttal_unjudged_or_orphaned_tasks_child_only_after_a_green_regate
    positive_case: >-
      The same witness adopts each task again on a green re-gate and reads
      the child from the same two scans and the same resolver call, so the
      refusals it reads first are readings that admit.
  - claim: >-
      For each of those two states, and for an `EXHAUSTED` control, adopt
      keeps the state and exits 0 after a red, a declined and an other-head
      re-gate. The url and the head are recorded all the same, and the line
      adopt prints names the state it kept. A `REBUTTAL_UNJUDGED` task's
      head is recorded in no state, so its `pushed_in_state` reads `None`.
      An `ORPHANED` task's head and the control's land in their own state,
      as at base. Adopted again with a fresh head that re-gates green, each
      red task moves to `READY_FOR_REVIEW`.
    witness: tests/test_cli.py::test_adopt_keeps_a_rebuttal_unjudged_or_orphaned_task_whose_regate_is_red_declined_or_on_another_head
    wrong_versions:
      - "Adopt moves either state to `READY_FOR_REVIEW` without re-gating."
      - "Adopt exits 1 when the re-gate of either state is red."
      - "Adopt clears the url again when the re-gate of either state is red."
      - "Adopt records the url but not the head for either state, so the row keeps its old `pushed_sha`, or none."
      - "Adopt records every state's head untrusted, `EXHAUSTED` and `ORPHANED` included."
    covers:
      - set: the states adopt re-gates here
        members:
          - member: "`REBUTTAL_UNJUDGED`, in the three shapes criterion 1 names"
            driven_by: tests/test_cli.py::test_adopt_keeps_a_rebuttal_unjudged_or_orphaned_task_whose_regate_is_red_declined_or_on_another_head
          - member: "`ORPHANED`"
            driven_by: "Adopt records every state's head untrusted, `EXHAUSTED` and `ORPHANED` included."
          - member: "`EXHAUSTED`, the control"
            driven_by: "Adopt records every state's head untrusted, `EXHAUSTED` and `ORPHANED` included."
      - set: the re-gates that keep the state
        members:
          - member: new failures on the adopted head
            driven_by: "Adopt exits 1 when the re-gate of either state is red."
          - member: a decline that records nothing
            driven_by: tests/test_cli.py::test_adopt_keeps_a_rebuttal_unjudged_or_orphaned_task_whose_regate_is_red_declined_or_on_another_head
          - member: zero new failures on another head
            driven_by: tests/test_cli.py::test_adopt_keeps_a_rebuttal_unjudged_or_orphaned_task_whose_regate_is_red_declined_or_on_another_head
    positive_case: >-
      The same witness then adopts each red task again on a green re-gate
      and reads `READY_FOR_REVIEW` from the same row, so the state it reads
      as kept is one that moves.
  - claim: >-
      In a stack batch, a green re-gate under adopt places a
      `REBUTTAL_UNJUDGED` task and an `ORPHANED` task that ran after every
      layer as the batch's top layer in turn. Each sits one position past
      the layer before it, with that layer as its predecessor.
    witness: tests/test_adopt_stack_layer.py::test_an_adopted_rebuttal_unjudged_or_orphaned_task_becomes_its_batchs_top_layer
    wrong_versions:
      - "Adopt places a layer only for `EXHAUSTED`, `NOT_IMPLEMENTED` and `MERGE_FAILED`."
      - "Adopt re-gates either state but moves only `EXHAUSTED`, `NOT_IMPLEMENTED` and `MERGE_FAILED` on a green result."
    covers:
      - set: the two states
        members:
          - member: "`REBUTTAL_UNJUDGED`"
            driven_by: tests/test_adopt_stack_layer.py::test_an_adopted_rebuttal_unjudged_or_orphaned_task_becomes_its_batchs_top_layer
          - member: "`ORPHANED`"
            driven_by: tests/test_adopt_stack_layer.py::test_an_adopted_rebuttal_unjudged_or_orphaned_task_becomes_its_batchs_top_layer
  - claim: >-
      `Ledger.record_push` can record a push untrusted. That push keeps its
      `pushed_sha` and sets `pushed_in_state` to `None`, over a push trusted
      in the same state before it. A default push after it lands in the
      row's state again. The row and a fold of the record agree on both.
    witness: tests/test_ledger_fold_task.py::test_an_untrusted_push_lands_in_no_state_and_a_fold_rebuilds_it
    wrong_versions:
      - "The ledger writes the untrusted mark into the fact but its apply step still sets `pushed_in_state` to the row's state."
    covers:
      - set: the pushes in order
        members:
          - member: an untrusted push over a trusted one
            driven_by: "The ledger writes the untrusted mark into the fact but its apply step still sets `pushed_in_state` to the row's state."
          - member: a default push over an untrusted one
            driven_by: tests/test_ledger_fold_task.py::test_an_untrusted_push_lands_in_no_state_and_a_fold_rebuilds_it
      - set: the readers
        members:
          - member: the ledger row
            driven_by: tests/test_ledger_fold_task.py::test_an_untrusted_push_lands_in_no_state_and_a_fold_rebuilds_it
          - member: a fold of the record
            driven_by: tests/test_ledger_fold_task.py::test_an_untrusted_push_lands_in_no_state_and_a_fold_rebuilds_it
    positive_case: >-
      The second row's default push reads `REBUTTAL_UNJUDGED` from the same
      row and the same fold, so the `None` read on the first row comes from
      reads that see a state.
  - claim: >-
      A push recorded without the new argument still lands in the row's
      own state, and a fold rebuilds it.
    witness: tests/test_ledger_fold_task.py::test_a_push_records_the_state_its_row_held_and_a_fold_rebuilds_it
    preserves: true
    positive_case: >-
      The same test reads a stale push as the earlier state and an
      unpushed row as `None`, so its reads tell each state apart.
  - claim: >-
      For `EXHAUSTED`, `NOT_IMPLEMENTED` and `MERGE_FAILED`, a green re-gate
      of the adopted head still moves the task to `READY_FOR_REVIEW`, and
      both scans then admit the child on it.
    witness: tests/test_cli.py::test_adopt_moves_a_task_whose_regate_is_green_on_the_adopted_head_to_ready_for_review
    preserves: true
  - claim: >-
      Folding the record still rebuilds an `EXHAUSTED` or `NOT_IMPLEMENTED`
      task's adopted url, head and state.
    witness: tests/test_cli.py::test_an_adopted_head_and_state_move_are_facts_the_fold_keeps
    preserves: true
---

## Context

Backlog item **b-619b7d**. It asks that a task finished by hand reach a state
its children read as a reviewable parent. `SA-0313` built that route for
`EXHAUSTED`, `NOT_IMPLEMENTED` and `MERGE_FAILED`, and `SA-0374` let its
re-gate read a recorded spec text. Two states still have no route.

**Spec loop sessions 82 and 84 met both.** `saffron adopt` refused
`SA-0419`'s and `SA-0424`'s `REBUTTAL_UNJUDGED` tasks and `SA-0423`'s
`ORPHANED` task. Each by-hand pull request merged with no adopted task.
`SA-0425` stayed refused behind `SA-0424`. The queue offered `SA-0423`
again until its spec was retired by hand.

**Adopt refuses both before any `gh` call.** `_ADOPTABLE_STATES` is
`EXHAUSTED`, `MERGE_FAILED`, `NOT_IMPLEMENTED` and `READY_FOR_REVIEW`
(`saffron/cli.py:3171-3173`). Its comment says `REBUTTAL_UNJUDGED` was
left out when it joined `MERGE_ONLY_STATES` (`saffron/cli.py:3169-3170`).
Any other state exits 1 at `saffron/cli.py:3255-3259`. For a taken state
other than `READY_FOR_REVIEW`, adopt records the head with
`ledger.record_push` and the url with `ledger.adopt_pull_request`
(`saffron/cli.py:3302-3303`). It then calls `regate.run_regate`
(`saffron/cli.py:3305-3313`). On a zero-failure re-gate of the adopted
head it sets `READY_FOR_REVIEW` (`saffron/cli.py:3315-3321`). It then places
the task as a stack layer through `_adopted_stack_layer`
(`saffron/cli.py:3204-3232`). Otherwise it prints `kept <state>` and exits 0
(`saffron/cli.py:3344-3347`).

**The re-gate has what it needs for both states.** The re-gate's query,
`_TASK_ROW`, selects the task's `branch`, `spec_sha`, `pr_url` and
`base_sha` (`saffron/regate.py:26-31`). `create_task` requires a `branch`
(`saffron/ledger.py:1635`), so an `ORPHANED` row has one. With no
`spec_texts` row the re-gate reads the spec file at `base_sha`
(`saffron/regate.py:201-203`). `SA-0423`'s and `SA-0424`'s rows in the home
ledger each carry `saffron/<spec id>` as `branch`.

**What the scheduler reads.** `REBUTTAL_UNJUDGED` is in
`DEPENDENCY_WAITING_STATES` (`saffron/scheduler.py:130-138`). So a plain
scan already admits its child (`saffron/scheduler.py:746-747`). A
`stack=True` scan also needs a trusted push and a url on that row
(`saffron/scheduler.py:1094-1110`). `_stale_push_state` distrusts a push not
recorded in the row's own state (`saffron/scheduler.py:151-158`), and so
does the batch's resolver, `task._resolve_stacked_on`
(`saffron/task.py:593-600`). `ORPHANED` is in `REQUEUE_STATES`
(`saffron/scheduler.py:164-173`), so the queue offers its spec again
(`saffron/scheduler.py:1346-1350`). `SA-0430` refuses that resume once the
row carries a url, as `open_pr_on_spec`. `ORPHANED` is not in
`DEPENDENCY_WAITING_STATES`, so the plain scan refuses the child
(`saffron/scheduler.py:756`).

**Both of adopt's writes trust the push today.** A `task_push` fact sets
`pushed_in_state` to the state the row held when it landed
(`saffron/ledger.py:1023-1030`). `adopt_pull_request` writes a
`task_package` fact that sets `pushed_in_state` to the row's own state
(`saffron/ledger.py:1889-1915`). So a `REBUTTAL_UNJUDGED` row adopt kept
would read as trusted, with a url. A `stack=True` scan would then stack
the child on the head the re-gate judged red. That was measured on the
prototype before this spec's ledger change, for both shapes.

## Problem

1. **Take both states.** Add `REBUTTAL_UNJUDGED` and `ORPHANED` to
   `_ADOPTABLE_STATES`. Both record the head and the url, re-gate, and move
   the task on a green re-gate of the adopted head, as `EXHAUSTED` does.
   Adopting is the operator's judgment of any blocker the cell left
   unjudged. The re-gate is the mechanical check. Every refusal that reads
   only the ledger stays before `gh`.
2. **Let `Ledger.record_push` record a push untrusted.** Add a keyword,
   defaulting to today's behaviour, that makes the push land in no state.
   Its fact carries the mark only when it is set, so every fact at base
   folds as before. The `task_push` apply step then sets `pushed_in_state`
   to `NULL` for a marked fact, and to the row's state otherwise.
3. **Record a `REBUTTAL_UNJUDGED` head untrusted, after the url.** For a
   state in `STALE_PUSH_STATES`, `_adopt` calls `adopt_pull_request` first,
   then records the head untrusted. The url is still on record before the
   re-gate, which reads `pr_url`. The url's fact trusts whatever push the
   row holds, so the untrusted head must come after it. A green re-gate
   then moves the row to `READY_FOR_REVIEW`, a state `_stale_push_state`
   never distrusts. Every other state keeps the order and the trusted push
   it has at base. The comment above the two writes
   (`saffron/cli.py:3300-3301`) names one order, so reword it to cover
   both branches.
4. **Rewrite the comment above `_ADOPTABLE_STATES`.** It must stop saying
   adopt refuses `REBUTTAL_UNJUDGED`. `_adopt`'s docstring sits at the
   ten-line limit the `prose` gate holds, so one added line there fails
   it. Put any new words in that comment.
5. **Update the `adopt` help string** (`saffron/cli.py:237-241`). It names
   the three re-gated states at base.
6. **Edit the refusal table** in
   `test_adopt_refuses_with_exit_one_and_writes_nothing`
   (`tests/test_cli.py:4920-4922`). Its `takes` set gains the two states,
   and its count of other states falls from 24 to 22.

## Out of scope

- **A fixed `MERGE_FAILED` task.** The item's other half, and the route the
  item names for it, stay with b-619b7d.
- **`saffron finish` and "holds no layer".** A deferred batch whose only
  task adopt placed is the item's later record. This spec places the
  layer and does not touch `finish`.
- **A kept `ORPHANED` task's next batch.** `SA-0430` owns it. Its scan
  refuses an `ORPHANED` resume whose row carries a url, so no green cell's
  PACKAGE pushes over the adopted head (`saffron/phases/package.py:970-975`).
  The adopted url also keeps `saffron package` away
  (`saffron/task.py:1382-1385`), and `push_unpackaged_work` as well
  (`saffron/phases/package.py:1244-1248`). Its spec stays refused until a
  green re-adopt moves the task, or the operator retires the spec.
- **Two refusal lines name the wrong cause after a kept adopt.** One is
  the `stack=True` scan's (`saffron/scheduler.py:1095-1098`). The other is
  the resolver's (`saffron/task.py:597-600`). Each says the parent pushed
  nothing in its state. For a `REBUTTAL_UNJUDGED` task adopt kept, the cause is
  an adopted head no green re-gate judged. Both files stay forbidden, and
  the lines stay as they are.
- **The window between adopt's two writes.** The url's fact trusts the
  push (`saffron/ledger.py:1889-1915`). The untrusted head follows it,
  where `saffron/cli.py:3300-3303` writes the two today. A refused append or a kill between them
  leaves the row trusted with a url, and adopting again on the same pull
  request closes it.
- **`DESIGN.md` and `CONTEXT.md`.** The `ORPHANED` and `REBUTTAL_UNJUDGED`
  rows of §3.3 and the **Adopt** entry in `CONTEXT.md` are amended by hand
  in this spec's own commit.

## Notes for the agent

**The route this spec chose, and why.** Neither existing write can leave a
push untrusted, so the fix sits in `saffron/ledger.py`. A keyword on
`record_push` is the smallest change there: one optional key in one fact
kind, read by one apply step. A keyword on `adopt_pull_request` would need
the same in `task_package`, a fact PACKAGE also writes. Recording the head
only after a green re-gate would leave a red adopt with no head on record,
and criterion 2 keeps it.

**`saffron/ledger.py` is `elevate_on`, so this task is `elevated`.** The
other callers of `record_push` are PACKAGE's two
(`saffron/phases/package.py:999`, `saffron/phases/package.py:1345`). They
pass no keyword, and criterion 5 holds them. `adopt_pull_request` is
unchanged, and criteria 6 and 7 hold the three older routes.

**The size estimate prices past 80%, and the operator accepts it.** The
real `size` gate sees only the 48 changed lines outside `tests/`.

**An edit to existing code, and still no criterion declares a mutant.** The
core change adds two members to a set literal. Six members pass the line
length, so `ruff format` reflows it, one member a line in the prototype.
Its spelling at head is the formatter's, not one the base code forces.
The ledger keyword is new code, so its spelling is yours. `witness` will
report `skip`.

**Never let a test reach the real `run_regate`.** Replace
`cli.regate.run_regate` with `_FakeRegate` (`tests/test_cli.py:4754-4782`)
in every test that reaches a re-gate. Its pair outcome records a re-gate
row, and its bare int is the decline shape.

**Seed the four parent rows the way the ledger writes them.** For the
first, set `REBUTTAL_UNJUDGED`, then call `ledger.record_push`. For the
second, call `record_push` in another state, then set `REBUTTAL_UNJUDGED`.
For the third, set `REBUTTAL_UNJUDGED` and record no push, the row a failed
`push_unpackaged_work` leaves. For the `ORPHANED` row, set the state and
record no push. Seed each
parent's task with the `spec_sha` `intake.load_spec` returns for its file,
as `tests/test_cli.py:5244` and `tests/test_cli.py:5261` do. A
`stack=True` scan reads a pushed sha only as forty or sixty-four lowercase
hex digits (`saffron/scheduler.py:1100`), so give each fake head that
shape.

**Drive the resolver without a mirror.** With `gh=None` and one parent,
`_resolve_stacked_on` reads the ledger alone and raises `_StackingRefused`
on a stale row (`saffron/task.py:593-600`). On a trusted one it calls
`_fetch_parent_head` (`saffron/task.py:288`). Replace that with a double
that records the branch it was asked for, so the green case reads as a
fetch.

**The witness reads each kept shape's own refusal.** For all three
`REBUTTAL_UNJUDGED` rows the plain scan takes the child while the state is
kept. The `stack=True` scan and the resolver refuse it. For the
`ORPHANED` row both scans take nothing. `SA-0430` refuses the parent on its
adopted url. The plain scan's reason reads "task 1 is ORPHANED beside pull
request https://github.com/owner/repo/pull/91, and resuming it would push
over that head". The child's reads "depends_on SA-95100 is ORPHANED, which
is not MERGED". The `stack=True` scan refuses the parent with the same
reason. Its child line ends "SA-95100 has no waiting task, so merge it, or
rerun it". These were measured on the prototype with `SA-0430`'s diff
beneath it. Read each reason's kind and the url or parent id it names.

**The stack-layer witness seeds its tasks with `_seed_stack_task`**
(`tests/test_adopt_stack_layer.py:21-43`), one batch holding one layer at
base. A batch places only a `READY_FOR_REVIEW` task as a layer
(`saffron/batch.py:445-455`), so neither state holds one before the adopt.
