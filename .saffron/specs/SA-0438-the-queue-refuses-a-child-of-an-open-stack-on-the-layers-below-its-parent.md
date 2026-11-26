---
id: SA-0438
title: "The queue refuses a child of an open stack on the pull requests of the layers below its parent"
type: bug
priority: 2
estimated_lines: 85
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
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/intake.py
  - saffron/events.py
  - saffron/finish.py
  - saffron/follow_up.py
  - saffron/qualify.py
  - saffron/spec_review.py
  - saffron/mutants.py
  - saffron/reconcile.py
  - saffron/regate.py
  - saffron/parent_versions.py
  - saffron/report/**
  - saffron/phases/**
  - saffron/record/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/repos/**
  - tests/test_refusal_count.py
  - tests/test_queued_specs.py
  - tests/test_cli.py
  - tests/test_adopt_stack_layer.py
  - tests/test_ledger_fold_task.py
  - tests/test_batch.py
  - tests/test_spec_review.py
  - tests/test_mutants.py
  - tests/test_qualify.py
  - tests/test_finish.py
  - tests/test_follow_up.py
  - tests/test_task.py
  - tests/test_intake.py
  - tests/test_events.py
  - tests/test_package.py
  - tests/test_package_cell.py
  - tests/test_stack_view.py
  - tests/test_spec_loop_driver.py
  - tests/test_witness_gate.py
  - tests/test_suite.py
  - tests/test_session.py
  - tests/test_parent_versions.py
  - tests/test_regate.py
  - tests/test_report.py
  - tests/test_record_refs.py
  - tests/test_record_routed.py
  - tests/test_record_migrate.py
budget_usd: 32
max_attempts: 3
max_turns: 130
risk: standard
acceptance:
  - claim: >-
      When an open `depends_on` ancestor's newest waiting task is a layer,
      `build_queue` exempts from the overlap refusal the open pull request
      of every task below that layer on its recorded predecessor chain. The
      witness records a three-layer stack batch whose layers declare no
      `depends_on`. A child of the top layer, and a grandchild that reaches
      it through a plain open parent, each overlap the layer one below the
      top and the layer two below it. Each is refused on each of those pull
      requests before the `stack_layers` rows exist. Each is admitted after,
      beside each one alone. The child is also admitted beside the top
      layer's own pull request, and beside all three. Both the plain scan
      and the `stack=True` scan read every case. Then the parent's spec is
      edited, so its layer sits at an older `spec_sha`. A `stack=True` scan
      lists the parent's own open pull request beside each lower layer. It
      refuses the parent as `open_pr_on_spec` and still admits the child.
      Without that pull request the edited parent would be kept and rerun
      from the default branch.
    witness: tests/test_scheduler.py::test_an_open_stacks_lower_layers_do_not_refuse_a_child_of_its_top
    wrong_versions:
      - "The walk stops at the predecessor of the parent's own layer, so the layer two below it still refuses."
      - "Only a candidate's direct `depends_on` entries are walked, so a grandchild through a plain open parent still refuses."
      - "The wider exemption is passed in the plain scan only, so a `stack=True` scan still refuses."
      - "The wider exemption is passed in the `stack=True` scan only."
      - "A chain read once in a scan is unioned only for the first candidate that reaches it, so the second candidate still refuses."
      - "The walk reads only the parent's tasks at its current `spec_sha`, so a layer at an older one is never walked."
    covers:
      - set: the layers below the parent's own layer
        members:
          - member: the predecessor of the parent's layer, one below
            driven_by: tests/test_scheduler.py::test_an_open_stacks_lower_layers_do_not_refuse_a_child_of_its_top
          - member: the layer two below
            driven_by: "The walk stops at the predecessor of the parent's own layer, so the layer two below it still refuses."
      - set: the candidates that reach the layer
        members:
          - member: a child naming the top layer's spec in `depends_on`
            driven_by: tests/test_scheduler.py::test_an_open_stacks_lower_layers_do_not_refuse_a_child_of_its_top
          - member: a grandchild through a plain open parent
            driven_by: "Only a candidate's direct `depends_on` entries are walked, so a grandchild through a plain open parent still refuses."
          - member: the second candidate in one scan to reach the same layer
            driven_by: "A chain read once in a scan is unioned only for the first candidate that reaches it, so the second candidate still refuses."
      - set: the scans
        members:
          - member: the plain `build_queue` scan
            driven_by: "The wider exemption is passed in the `stack=True` scan only."
          - member: a `stack=True` `build_queue` scan
            driven_by: "The wider exemption is passed in the plain scan only, so a `stack=True` scan still refuses."
      - set: the `spec_sha` of the parent's layer
        members:
          - member: the parent's current `spec_sha`
            driven_by: tests/test_scheduler.py::test_an_open_stacks_lower_layers_do_not_refuse_a_child_of_its_top
          - member: an older `spec_sha`, after an edit
            driven_by: "The walk reads only the parent's tasks at its current `spec_sha`, so a layer at an older one is never walked."
    positive_case: >-
      The same witness reads the child and the grandchild refused on each
      lower layer's pull request before the `stack_layers` rows exist. So
      each admission it reads comes from a scan that sees that pull request.
  - claim: >-
      The walk crosses from a stack batch's first layer into the batch its
      predecessor belongs to, as a stack base. The open pull request of
      that predecessor and of each layer below it in its own batch are
      exempt too. The witness records an earlier stack batch of two layers
      and cuts the three-layer batch's first layer from its top. A child of
      the later top is refused on each earlier layer's pull request before
      the later batch's `stack_layers` rows exist. It is admitted after,
      beside each one alone and beside both, in both scans. A third layer
      of the earlier batch sits above the stack base, and the child is
      still refused on its pull request, in both scans. Two more stack
      bases are no layer. One is a plain cell's task in no batch, with a
      branch, a push and a pull request. The other is a missed task of a
      stack batch whose one layer sits below no row of its own. Each is
      the first layer's predecessor. The child is refused on its pull
      request before the layers exist and admitted after, in both scans.
      Beside the missed one it is still refused on that batch's layer.
    witness: tests/test_scheduler.py::test_a_stack_base_in_an_earlier_batch_does_not_refuse_a_child_of_the_stack
    wrong_versions:
      - "The walk ends at the batch's first layer, so the stack base it was cut from still refuses."
      - "The walk exempts the stack base's own branch and stops there, so the layer below it in the earlier batch still refuses."
      - "On crossing into the stack base's batch, every layer of that batch is exempt, the ones above the stack base included."
      - "The walk checks `stack_batch_of` on the stack base and breaks before adding the stack base's own branch."
      - "A stack base in a stack batch with no `stack_layers` row of its own exempts that whole batch."
    covers:
      - set: the earlier batch's layers
        members:
          - member: the stack base, the first layer's predecessor
            driven_by: "The walk ends at the batch's first layer, so the stack base it was cut from still refuses."
          - member: the layer below the stack base
            driven_by: "The walk exempts the stack base's own branch and stops there, so the layer below it in the earlier batch still refuses."
          - member: the layer above the stack base, refused
            driven_by: "On crossing into the stack base's batch, every layer of that batch is exempt, the ones above the stack base included."
      - set: the stack bases that are no layer
        members:
          - member: a plain cell's task in no batch
            driven_by: "The walk checks `stack_batch_of` on the stack base and breaks before adding the stack base's own branch."
          - member: a missed task of a stack batch, beside that batch's layer
            driven_by: "A stack base in a stack batch with no `stack_layers` row of its own exempts that whole batch."
    positive_case: >-
      The same witness reads the child admitted beside both lower layers
      of the earlier batch, so the refusal on the layer above the stack
      base comes from a scan that crossed into that batch.
  - claim: >-
      Every other open pull request still refuses on overlap. The witness
      records a parent whose newest waiting task is the third of four
      layers. The parent's older waiting task is a layer of another batch,
      on a layer below it there. A newer `ORPHANED` task of the parent sits
      above both. A third batch holds an unrelated layer.
      The parent's child is refused, naming the pull request, on each of
      four: the layer above the parent's, the older task's lower layer, the
      unrelated batch's layer, and a pull request no task owns. A spec with
      no `depends_on` is refused on the bottom layer's pull request. So is
      a child whose parent's task ran in the same batch and missed. That
      task is `READY_FOR_REVIEW` with a branch, a push and a pull request
      url, a `spec_reviews` row and no `stack_layers` row. Both scans read every
      case.
    witness: tests/test_scheduler.py::test_an_open_stack_still_refuses_a_pull_request_off_its_childs_chain
    wrong_versions:
      - "Every layer of the parent's stack batch is exempt, the ones above its layer included."
      - "The walk starts from the parent's oldest waiting task rather than its newest."
      - "The walk starts from every waiting task of the parent and unions their chains."
      - "The walk starts from the parent's newest task in any state, so a newer `ORPHANED` task hides its layer."
      - "Every layer any stack batch in the repo recorded is exempt."
      - "Every chain the scan reads is exempt for every candidate, whatever its `depends_on`."
      - "A parent whose task sits in a stack batch with no `stack_layers` row of its own exempts every layer of that batch."
    covers:
      - set: the open pull requests that must still refuse
        members:
          - member: the layer above the parent's own layer
            driven_by: "Every layer of the parent's stack batch is exempt, the ones above its layer included."
          - member: a layer below the parent's older waiting task, in another batch
            driven_by: "The walk starts from every waiting task of the parent and unions their chains."
          - member: a layer of an unrelated stack batch
            driven_by: "Every layer any stack batch in the repo recorded is exempt."
          - member: a pull request no task owns
            driven_by: tests/test_scheduler.py::test_an_open_stack_still_refuses_a_pull_request_off_its_childs_chain
      - set: the candidates beside the bottom layer
        members:
          - member: the parent's child, admitted
            driven_by: "The walk starts from the parent's oldest waiting task rather than its newest."
          - member: a spec with no `depends_on`, refused
            driven_by: "Every chain the scan reads is exempt for every candidate, whatever its `depends_on`."
          - member: a child of a parent whose task missed in the batch, refused
            driven_by: "A parent whose task sits in a stack batch with no `stack_layers` row of its own exempts every layer of that batch."
      - set: the parent's tasks the walk could start from
        members:
          - member: its newest waiting task, the third layer
            driven_by: tests/test_scheduler.py::test_an_open_stack_still_refuses_a_pull_request_off_its_childs_chain
          - member: its older waiting task, a layer of another batch
            driven_by: "The walk starts from every waiting task of the parent and unions their chains."
          - member: its newer `ORPHANED` task
            driven_by: "The walk starts from the parent's newest task in any state, so a newer `ORPHANED` task hides its layer."
    positive_case: >-
      The same witness reads the parent's child admitted beside the bottom
      layer's pull request in both scans. So each refusal it reads comes
      from a scan that reads the recorded layers and exempts the ones on
      the child's chain.
  - claim: >-
      The overlap refusal keeps one site in `scheduler.py`, since the change
      widens the set it skips and adds no `return`.
    witness: tests/test_refusal_count.py::test_every_refusal_kind_but_preflight_has_its_pinned_sites_in_the_scan
    preserves: true
    positive_case: >-
      The same test parses `scheduler.py` and reads each kind's sites,
      `open_pr_overlap`'s one among them, so the count it compares is seen.
  - claim: >-
      An open pull request off a stacked child's `depends_on` chain, with no
      layer recorded, still refuses it.
    witness: tests/test_scheduler.py::test_a_third_partys_overlap_still_refuses_a_stacked_child
    preserves: true
    positive_case: >-
      The same test reads one refusal naming the third party's url, while
      the parent's own pull request over the same file is skipped.
  - claim: >-
      The `depends_on` exemption still reaches every branch on the chosen
      parent's chain, in both scans.
    witness: tests/test_scheduler.py::test_the_overlap_refusal_exempts_every_branch_on_the_chosen_parents_chain
    preserves: true
    positive_case: >-
      The same test reads the refusal naming the unreached grandparent's
      pull request, and none of the three reached ones.
---

## Context

Backlog item **b-910cef**. It recurred as b-0bd8c9, closed as a second
sighting of it. Over a failed stack batch's nine refused specs and one
more, a plain queue admitted two and a `--stack` queue none. Each later
spec's `touches` overlapped pull requests of layers it does not name in
`depends_on`.

**The overlap refusal skips only the branches its caller names**.
`open_pr_refusal` skips a pull request whose `headRefName` is the
candidate's own branch or sits in `exempt_branches`
(`saffron/scheduler.py:951-954`). Any other pull request whose files meet
`touches` refuses as `open_pr_overlap` (`saffron/scheduler.py:955-973`).

**The queue's exempt set is the `depends_on` walk alone**. `build_queue`
calls `_refuse` once per candidate in both modes, with
`ancestor_branches=_ancestor_branches(candidate.spec.id, edges)` and
`check_dependencies=not stack` (`saffron/scheduler.py:1536-1552`). `_refuse`
hands that set to `open_pr_refusal` (`saffron/scheduler.py:1092`).
`_ancestor_branches` turns each id `_reachable` finds into its branch
(`saffron/scheduler.py:294-305`), walking `edges`
(`saffron/scheduler.py:270-291`). `build_queue` builds `edges` from each
spec's `depends_on` list alone (`saffron/scheduler.py:1502-1504`). So the
scan that is wrong is `build_queue`'s gate 0 overlap check, plain and
`stack=True` alike. It lacks the recorded predecessors of the layer a
candidate is cut from.

**A layer's predecessors are in its tree, recorded or named**. A stack
batch cuts each task from its predecessor's head (ADR 7, "A task's
**predecessor** is the last task below it"). A batch's first layer is cut
from its stack base, and the base's task is its predecessor (ADR 7, the
2026-10-10 amendment). `run_stack_batch` records that: it seeds
`predecessor_task_id` with the stack base's task
(`saffron/batch.py:587-592`), and `record_layer` writes each layer with the
last one as predecessor (`saffron/batch.py:632-643`). The layers declare no
`depends_on` between them, so `_reachable` never finds them.

**The ledger already serves the chain**. Its layer table carries
`task_key`, `batch_key`, `position`, `spec_id` and `predecessor_key`
(`saffron/ledger.py:257-265`). `Ledger.stack_batch_of(task_id)` names a
task's stack batch (`saffron/ledger.py:1980-1997`).
`Ledger.stack_layers(batch_id)` lists that batch's rows with `task_id`
(`saffron/ledger.py:1960-1978`). `Ledger.record_key(task_id)`
gives a task's key (`saffron/ledger.py:631-635`). `tasks_by_repo` carries
`task_id` and `spec_id` but no key (`saffron/ledger.py:1295-1312`).
`_adopted_stack_layer` reads a task's batch the same way
(`saffron/cli.py:3204-3213`).

**A stack batch's own follow-up check already exempts its layers**.
`run_stack_batch` passes its recorded `layer_branches` to `open_pr_refusal`
(`saffron/batch.py:615-620`, `saffron/batch.py:717-719`). The queue has no
such set.

## Problem

1. **Exempt the recorded layers below each open ancestor's layer**. For
   each id `_reachable` finds from the candidate, take its newest task in
   `DEPENDENCY_WAITING_STATES`, the row `_stack_base_candidate` reads
   (`saffron/scheduler.py:1180-1185`). When that task is a layer, walk its
   `predecessor_key` chain and add each predecessor's branch to the set
   `build_queue` passes as `ancestor_branches`. A layer above it is no
   predecessor and still refuses. Read each id's chain once per scan.
2. **Cross into the stack base's batch**. A first layer's predecessor is a
   task in another batch. Add its branch. When it is a layer there, go on
   walking that batch's chain.
3. **Leave every other pull request refused**. A spec with no `depends_on`
   gets no chain. A repo with no ledger row gets none. An older waiting
   task of the parent is not walked.
4. **Correct the sentences the change makes false**. The comment in
   `open_pr_refusal` that names `_ancestor_branches` as `_refuse`'s exempt
   set (`saffron/scheduler.py:944-946`). The docstring of
   `test_a_third_partys_overlap_still_refuses_a_stacked_child`, which says
   the exemption is the `depends_on` chain "and nothing else"
   (`tests/test_scheduler.py:1124-1126`). Add a paragraph naming b-910cef
   to the module docstring, beside `SA-0430`'s.

## Out of scope

- **An edited parent whose pull request closed unreconciled**. Its spec
  text moved, so the scan keeps it as a fresh candidate and a batch runs
  it again from the default branch. The walk still exempts its old
  layer's chain for its children until `reconcile` records the close.
- **A layer above the parent's own layer**. b-0bd8c9's `SA-0327` met #990,
  `SA-0326`'s layer. The home ledger records batch 60's one layer as
  `SA-0326` at position 1, with `SA-0325`'s task as its predecessor.
  `SA-0327` names `SA-0325`, whose branch never held #990. So that refusal
  was real, and this change keeps it.
- **A parent whose task missed and recorded no layer**. The item's own
  sighting is this shape. In the home ledger `SA-0233`'s task 249 ran in
  batch 20 after layer 3. It holds no `stack_layers` row, no push and no
  pull request url. Its children stay refused on layers 1 to 3, and
  criterion 3 reads that shape refused. A missed
  task's branch is whatever was pushed by hand, so no record says what it
  holds. `saffron adopt` makes such a task a layer only when it ran after
  every layer (`saffron/cli.py:3214-3220`), and batch 20's layer 4 ran
  after task 249.
- **`StackBase.chain_branches`**. `_resolve_stack_base` builds it from the
  `depends_on` walk alone (`saffron/scheduler.py:1262-1266`). A stack batch
  seeds its exempt set from it (`saffron/batch.py:615-620`). Two checks read
  that set. One re-refuses a revised spec of the order
  (`saffron/batch.py:458-478`). The other refuses a follow-up
  (`saffron/batch.py:717-719`). Both keep the gap beside the stack base's
  lower layers, and `saffron/batch.py` is forbidden here.
- **The attended cell's resolver**. With a `gh`, `_resolve_stacked_on`
  stacks on the newest row in `DEPENDENCY_WAITING_STATES` or
  `CHANGES_REQUESTED` (`saffron/task.py:560-570`). `_run_cell`, behind
  `saffron cell`, passes `run_task` a `gh` (`saffron/cli.py:785-796`). `saffron batch` passes none
  (`saffron/cli.py:833-843`), so its resolver reads the waiting rows this
  walk reads. The queue scan serves `saffron batch`, and an attended cell
  of a parent sent back to `CHANGES_REQUESTED` can stack on a row this
  walk skips.
- **A by-hand pull request on a layer's branch**. The exemption matches
  `headRefName` against `_branch(spec_id)`, as `_ancestor_branches` already
  does. A pull request someone else opens on that branch is exempt too.
- **A candidate with no `depends_on` in a `--stack` order**. Once the order
  takes a stack base, every taken spec carries it
  (`saffron/scheduler.py:1591-1594`), but `_refuse` runs before that base
  is chosen. Such a spec still refuses on the base's lower layers.
- **The refusal's remedy text**. The overlap reason names no merge.
- **The site count**. `tests/test_refusal_count.py:42` pins one
  `open_pr_overlap` site. This change adds no `return` of that kind, so the
  pin stays and the file is forbidden.

## Notes for the agent

**No criterion declares a mutant**. The walk is new code whose spelling is
yours. The one edit to existing code is the argument `build_queue` passes
as `ancestor_branches`, and its new spelling is yours too. `witness` will
report `skip`.

**Leave `open_pr_refusal`'s signature alone**. `saffron/batch.py:477` and
`saffron/batch.py:717` call it.

**Leave `SA-0430`'s `ORPHANED` check and its call as they are**. `_refuse`
reads it before the overlap check (`saffron/scheduler.py:1084-1090`), and
it reads none of this.

**Seed a layer the way a stack batch leaves it**. `stack_batch_of` returns
a batch only for a task whose run is attached to it and that holds a
`spec_reviews` row (`saffron/ledger.py:1980-1997`).
`tests/test_adopt_stack_layer.py:21-43` builds such a task. Copy its shape
into `tests/test_scheduler.py` rather than importing it. Then call
`Ledger.record_stack_layer` with each layer's `position` and
`predecessor_task_id`. Spec ids must match `[A-Za-z0-9]+-[0-9]+`, so a
layer is `TE-1` and never `TE-L1`.

**Give the parent a stack base's shape, or `stack=True` refuses for the
wrong reason**. Its newest waiting row needs a branch, a 40-hex
`pushed_sha` and a `pr_url` (`saffron/scheduler.py:1186-1206`).
`set_task_package` (`tests/test_scheduler.py:58-64`) writes all three.
Seed that row at the spec's current `spec_sha`. Otherwise no task there
is done with the parent, and it becomes a fresh candidate itself
(`saffron/scheduler.py:1446-1450`).

**Read the refusal before the layers exist**. Each witness first reads the
candidate refused on the pull request it then sees exempted. The two reads
differ only in the `stack_layers` rows. `_fake_gh`
(`tests/test_scheduler.py:228-249`) prints the listed pull requests.

**No `retired_first`**. The change narrows a refusal and refuses nothing
new.

**What the prototype measured**. The change was 71 added and 2 removed
lines in `saffron/scheduler.py`, 339 changed tokens by the `size` gate's own
count. With it applied, `tests/test_scheduler.py`,
`tests/test_refusal_count.py`, `tests/test_batch.py` and
`tests/test_spec_loop_driver.py` passed. So did the `queue`, `stack` and
`batch` tests of `tests/test_cli.py` and `tests/test_task.py`.
