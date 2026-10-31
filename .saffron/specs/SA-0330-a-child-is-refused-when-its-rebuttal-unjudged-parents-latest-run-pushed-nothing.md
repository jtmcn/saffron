---
id: SA-0330
title: "A child is refused when its REBUTTAL_UNJUDGED parent's latest run pushed nothing, rather than cut without that parent's code"
type: bug
priority: 1
estimated_lines: 85
estimate_measured: true
depends_on: [SA-0331]
touches:
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/task.py
  - tests/test_ledger.py
  - tests/test_ledger_fold_task.py
  - tests/test_cli.py
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
  - saffron/phases/**
  - saffron/cli.py
  - saffron/batch.py
  - saffron/reconcile.py
  - saffron/regate.py
  - saffron/events.py
  - saffron/intake.py
  - saffron/finish.py
  - saffron/end_review.py
  - tests/test_batch.py
  - tests/test_task.py
  - tests/test_package.py
budget_usd: 40
max_attempts: 3
max_turns: 200
risk: standard
acceptance:
  - claim: >-
      `tasks` gains `pushed_in_state`, its last column. A `task_push` fact sets
      it to the state its row holds at that fact. A `task_package` fact sets it
      to the state that fact carries. A later state write leaves it, so a push
      from before that write reads as stale. `tasks_by_spec_id` carries it. The
      witness drives five rows through the write methods: a push in the state,
      a stale push, a push resumed and pushed again, a packaged row later sent
      back, and a row with no push. It reads all five from the live ledger and
      from a fold of the same facts into a new ledger. A ledger that predates
      the column gains it on open and keeps its rows, and such a row reads
      `None`.
    witness: tests/test_ledger_fold_task.py::test_a_push_records_the_state_its_row_held_and_a_fold_rebuilds_it
    wrong_versions:
      - A `task_package` fact leaves the column as it was, so a packaged row carries the state of its earlier push.
      - A `task_push` fact writes `REBUTTAL_UNJUDGED` or the sha, whatever state the row holds.
      - A `task_state` fact moves the column along with the state on any row that has a push, so a stale push reads as current.
      - The column is in the schema with no additive migration, so an older ledger raises on the first read.
      - The column is written by `record_push` after its fact, so a fold of the same facts leaves it empty.
      - The column is written but `tasks_by_spec_id` does not select it.
  - claim: >-
      With one `depends_on` entry, `run_task` returns `Refused` before any cell
      starts when the parent's chosen row is `REBUTTAL_UNJUDGED` and no push
      followed that state. The reason names the parent, `REBUTTAL_UNJUDGED` and
      the push. No `unstacked` line prints, and no queue row is written. The
      witness drives three rows through `cli._run_cell` with a `gh` and through
      `cli._batch_runner` with none. They are no push, a stale push whose branch
      still points at it, and no push on a row newer than a pushed
      `READY_FOR_REVIEW` row. `run_batch` over that runner ends `DRAINED` and
      attaches no run. A stale push whose branch a review fix moved is refused
      too, in both `gh` modes. A push made in the state still stacks on the
      fetched head, as does a resumed row pushed again, on a branch a review fix
      moved past the recorded push. A row carrying a pull request is refused
      when a `gh` answers open and when it cannot answer. When it answers merged,
      the row refuses nothing. In both `gh` modes `READY_FOR_REVIEW`, `APPROVED`,
      `MERGE_TRAIN` and `REVIEW_INCOMPLETE` keep their old result, with a stale
      push and with none. With a `gh`, so does a stale `CHANGES_REQUESTED` row.
      A parent with a `MERGED` row, one retired at `base_sha`, and one with a
      push in `base_sha` each refuse nothing, in both `gh` modes. A row a
      reconcile moves to `MERGED` counts, so the rule reads the rows after it.
    witness: tests/test_cli.py::test_a_child_of_a_rebuttal_unjudged_parent_stacks_only_on_its_latest_runs_push
    mutant:
      file: saffron/task.py
      find: newest = waiting[-1]
      replace: newest = waiting[0]
    wrong_versions:
      - Only an empty `pushed_sha` refuses, so a stale push still stacks.
      - Every waiting state is read by the new rule, so a `READY_FOR_REVIEW` row with an older push is refused.
      - The rule also covers `REVIEW_INCOMPLETE`.
      - The refusal sits only on the path with no `gh`.
      - The refusal sits only on the path with a `gh`.
      - The cell unstacks and starts on `base_sha` instead of being refused.
      - A stale push is read from the fetched head differing from `pushed_sha`, so a stale row whose branch never moved stacks.
      - A stale push counts as current once its branch moves, so a stale row whose branch moved stacks.
      - A row GitHub could not be asked about is not refused.
      - The refusal writes a queue row.
      - An older row with a push rescues a newer row with none.
      - The check runs after `_fetch_parent_head`, so an `unstacked` line prints before the refusal.
      - A different exception carries the refusal, so it escapes `run_task`.
      - The reason omits the parent's id.
      - The reason omits `REBUTTAL_UNJUDGED` or the push.
      - The rule reads the rows before the reconcile, so a parent whose older row just merged is refused.
      - A `MERGED` row does not count as landed, so a merged parent refuses its child.
      - Retirement at `base_sha` does not count as landed.
      - A push in `base_sha` does not count as landed.
  - claim: >-
      With two or more `depends_on` entries, `_resolve_multi_parent` reads every
      open parent's chosen row before it picks the deepest. A parent refuses as
      in the one-parent rule, whatever its place. The witness drives the deepest
      parent, a shallower one on its chain, a parent off that chain, and two at
      once, each with no push and with a stale push, in both `gh` modes. The
      reason names each refused parent and no other, and an off-chain parent's
      reason names its push rather than the chain. Two parents pushed in the
      state, or resumed and pushed again, still stack on the deepest head. A
      parent with a `MERGED` row, one retired at `base_sha` and one with a push
      in `base_sha` are not open, so each carries a refused row and refuses
      nothing. A deepest `REVIEW_INCOMPLETE` parent with no push still starts
      unstacked. `run_task` returns `Refused` with no cell on one case through
      `cli._run_cell` with a `gh`, and one through `cli._batch_runner` with
      none.
    witness: tests/test_cli.py::test_a_multi_parent_child_is_refused_for_any_open_parent_whose_latest_run_pushed_nothing
    mutant:
      file: saffron/task.py
      find: "if dep in retired_ids:"
      replace: "if False:"
    wrong_versions:
      - Only the chosen parent is read, so a shallower parent or an off-chain parent passes.
      - The check runs after the chain check, so an off-chain parent is refused for its chain and its push goes unnamed.
      - The reason names the first refused parent alone.
      - The check reads every entry before the open filter, so a merged, retired or landed parent refuses.
      - The multi-parent path has no check, and only the one-parent path refuses.
      - Every waiting state is read by the new rule.
      - The refusal sits only on the path with no `gh`.
      - The refusal sits only on the path with a `gh`.
      - The cell unstacks and starts on `base_sha` instead of being refused.
  - claim: >-
      `_stack_base_candidate` does not qualify a newest waiting row that is
      `REBUTTAL_UNJUDGED` with no push after that state, so `build_queue` with
      `stack=True` refuses the child under `depends_on`. The reason names the
      parent, `REBUTTAL_UNJUDGED`, the push and the remedy to merge it or rerun
      it. The witness drives three rows that carry a pull request: a stale push, no push, and a stale row newer
      than a pushed `READY_FOR_REVIEW` row. A row resumed and pushed in the
      state qualifies. So do `READY_FOR_REVIEW`, `APPROVED`, `MERGE_TRAIN` and
      `REVIEW_INCOMPLETE` rows that carry an older push.
    witness: tests/test_scheduler.py::test_a_stack_order_refuses_a_child_whose_stack_base_pushed_nothing_in_its_latest_run
    mutant:
      file: saffron/scheduler.py
      find: newest = waiting[-1]
      replace: newest = waiting[0]
    wrong_versions:
      - The stack base path is left as it was, so a stale row with a pull request becomes the base.
      - The check follows the existing pushed-sha check, so a row with no push gets a reason that never names its refused push.
      - Refused rows are filtered out of the waiting list, so an older row qualifies in their place.
      - Every waiting state is read by the new rule.
      - Only an empty `pushed_sha` refuses, so a stale push still qualifies.
      - The remedy tells the operator to run the parent to a pull request, which it already carries.
  - claim: >-
      A stack batch counts a `Refused` result a miss, and refuses each spec
      whose `depends_on` reaches that miss before the runner sees it.
    witness: tests/test_batch.py::test_a_stack_batch_refuses_every_descendant_of_a_task_that_missed_review
    preserves: true
  - claim: >-
      Given a `Handoff`, `run_task` never calls `_resolve_stacked_on`. So a
      layer of a stack batch does not reach this spec's resolver refusal.
    witness: tests/test_task.py::test_a_handoff_replaces_the_stacking_resolver
    preserves: true
---

## Context

Backlog item **b-f603c9**, under `DESIGN.md` §3.3, §4.2 and §5.6, and ADR 7.
Related: 120, b-af24d1. Every line below was read at `f596e814`. This spec stacks
on `SA-0331`, whose changes are named where they matter.

**The protected sentences, as landed by hand.** `CONTEXT.md`'s `REBUTTAL_UNJUDGED`
entry says the dependent of a row with a refused push is refused, naming that
push. `DESIGN.md` §4.2 gate 0 counts this among the refusals that come later.
§4.2.1 says a child of a row whose latest run pushed nothing is refused. That
holds even when the row carries an earlier run's `pushed_sha`. §3.3 already says a
dependent stacks only when the latest run's push succeeded.

**How the row gets its state and its push.** The cell writes the state
(`saffron/cell/session.py:3774`), and `run_task` then calls
`push_unpackaged_work` (`saffron/task.py:965`). That function records a push
only at its end (`saffron/phases/package.py:1236`). Each refusal returns before
that line (`saffron/phases/package.py:1118-1235`). `REBUTTAL_UNJUDGED` is not in
`REQUEUE_STATES` (`saffron/scheduler.py:136-145`). `SA-0331` adds it to
`MERGE_ONLY_STATES` and keeps `_ADOPTABLE_STATES`'s members exact, so `saffron
adopt` still refuses it (`saffron/cli.py:2860`). So a row cannot re-enter that
state, and no later writer records a push on it. `reconcile` now asks such a row
that carries a `pr_url`, and a merge moves it to `MERGED`.

**Nothing on the row tells the two runs apart.** `task_push` writes `pushed_sha`
and `updated_at` alone (`saffron/ledger.py:899-901`). Clearing `pushed_sha` on
resume is not open to us: `push_unpackaged_work` needs it to replace its own
earlier push (`saffron/phases/package.py:1157`). The operator chose a column
`_apply` derives from the order of the facts, with no new fact kind.

**Which path reads `gh`.** `cli._run_cell`, the attended path, passes a `gh`
(`saffron/cli.py:689`). `cli._batch_runner`, a plain batch, passes none
(`saffron/cli.py:727-738`). So an attended cell reads `_STACKABLE_ON_RECONCILE`
(`saffron/task.py:490`), and a plain batch reads `DEPENDENCY_WAITING_STATES`
(`saffron/task.py:476`). The backlog item states this the other way round.
`cli._stack_runner` passes a `Handoff` (`saffron/cli.py:831-845`), and `run_task`
then skips the resolver (`saffron/task.py:742-743`).

**What happens to the child today.** The one-parent path takes the newest
stackable row (`saffron/task.py:479`, `:501`) and passes it to
`_fetch_parent_head`. A row with no push prints `unstacked`, and the cell starts
on `base_sha` (`saffron/task.py:281-290`). A stale row stacks on the older
branch head. The multi-parent path picks the deepest of its open rows
(`saffron/task.py:366-387`) and treats it the same way. For any other open parent
with no push it moves on with no check (`saffron/task.py:418-422`).

**The stack base.** A stack batch never reaches the resolver.
`_stack_base_candidate` qualifies the newest waiting row with a branch, a
resolved `pushed_sha` and a `pr_url` (`saffron/scheduler.py:1021-1041`). A
`CHANGES_REQUESTED` row keeps its `pr_url` when it resumes, since only a
`task_package` fact writes that column (`saffron/ledger.py:882-893`). So a stale
`REBUTTAL_UNJUDGED` row qualifies today. `SA-0331`'s guard refuses a push on a row
that carries a `pr_url`, in any outcome state, so every such row ends stale. A row with no push is refused there
already, with a reason that names no refused push (`saffron/scheduler.py:1030`).

**What a batch does with a refusal.** `run_batch` attaches no run for a `Refused`
result and leaves the breaker's count alone (`saffron/batch.py:332-335`).
`_is_layer` counts it a miss in a stack batch (`saffron/batch.py:413-423`), and
the batch refuses that miss's descendants. This spec changes neither.

**What the one-parent path does not read.** The scan admits a child whose parent
merged, retired or landed. Its dependency check reads the first two
(`saffron/scheduler.py:673-678`), and the scan's own landed read follows
(`saffron/scheduler.py:1292-1300`). The one-parent resolver reads neither a
retirement nor a landed push, and without a `gh` it reads no `MERGED` row. The multi-parent path skips all three
(`saffron/task.py:367-375`). So a new refusal on the one-parent path must read
them first, or a child of a parent landed by hand is refused for good.

## Problem

1. **The fact.** `tasks.pushed_in_state` is set where the two facts apply
   (`saffron/ledger.py:882-901`). The column goes last in `tasks`, with the
   additive migration the other columns take (`saffron/ledger.py:415-428`).
   `tasks_by_spec_id` selects it (`saffron/ledger.py:1184`).
2. **One rule.** A `REBUTTAL_UNJUDGED` row refuses on any other
   `pushed_in_state`, `None` included. The rule lives in `saffron/scheduler.py`,
   which `saffron/task.py` already imports from.
3. **The one-parent path.** After both `gh` branches pick the row, and before
   `_fetch_parent_head`, raise `_StackingRefused` under the rule. A landed parent
   is the exception. Landed means a `MERGED` row, a retirement at `base_sha`, or
   a row's push in `base_sha`. That parent keeps the path it takes today.
4. **The multi-parent path.** Check each `stack_rows` entry after the loop fills
   it and before the deepest is picked. Raise `_StackingRefused` naming every
   such parent together.
5. **The stack base.** `_stack_base_candidate` returns a cause under the rule,
   ahead of its pushed-sha check, so a row with no push names its refused push.
   The remedy is `_MERGE_OR_RERUN`. A carried pull request can merge, and an
   attended cell mints a new row (`saffron/cli.py:679`), so both halves hold.
   `_RUN_TO_PR_FIRST` is false of a row that already carries one.
   `_stack_dependency_reason` carries that into the `depends_on` refusal.

The refusal costs no cell and no token. A plain batch prints the one line
`run_task` prints, and writes no queue row, as §4.2 says of the later refusals.

## Out of scope

- `_dependency_refusal` and the plain scan. `saffron queue` still lists such a
  child as a candidate, and `run_task` refuses it. The operator chose this. An
  unresolved `consumes` entry already behaves the same way.
- `REVIEW_INCOMPLETE` and every other waiting state. Their rows take the path
  they take today, including a start on `base_sha` with no push. Backlog item
  b-e9dd4c owns the `REVIEW_INCOMPLETE` gap.
- `SA-0331`, the parent, which adds an own-row guard to `push_unpackaged_work`. A
  push that guard refuses leaves this column on an earlier state, so the rule
  here reads that row as refused with no further change.
- A `REBUTTAL_UNJUDGED` row whose own stale push lies in `base_sha`. It reads as
  landed, as the multi-parent path already reads it.
- A stack batch's own `REBUTTAL_UNJUDGED` predecessor. It misses through
  `_is_layer`, whatever its push. Criterion 5 drives that predicate with a
  `Refused` result and with `MERGE_FAILED`, not with this state.
- `saffron/record/**` and `saffron/record/migrate.py`'s order, below.
- `DESIGN.md` and `CONTEXT.md`. The caller lands their sentences by hand.

## Notes for the agent

**Mutants and new code.** Criteria 2 to 4 each mutate a line the change keeps,
so leave those lines as they are. Criterion 1's column is new code. It declares
no mutant, and `witness` will report `skip` for it. Criteria 5 and 6 hold tests
that exist. Do not run the wrong versions yourself.

**A declared `find` stays unique.** A mutant applies only where its `find` matches
once in its file. Add no second line matching any criterion's declared `find`, in
new code or in a helper you extract.

**Every new test must fail with the source reverted.** So the admissions and the
unchanged waiting states live inside the refusal witnesses. A separate test of
them passes at base, and `revert` then blocks it.

**The migration limit.** `saffron/record/migrate.py:469-471` writes `task_push`
before the final `task_state`. A migrated row that pushed in
`REBUTTAL_UNJUDGED` therefore reads as refused. That is the direction that cannot
admit a child without its parent's code. The live ledger holds no such row
(measured 2026-10-30). An older ledger's rows read `None` until a fold, with the
same result. No backfill is wanted.

**An adopted row.** `adopt_pull_request` writes a `task_package` fact with the
row's own state (`saffron/ledger.py:1700`), so it sets the column too. `saffron
adopt` still refuses a `REBUTTAL_UNJUDGED` row over `SA-0331`, and no other state
reads the column.

**The schema block.** Write the two lines about `merged_head_sha` above
`merged_head_sha`, which is no longer the last column. They cannot stay below the
new last column, since that block then grows past the `prose` gate's limit. They
cannot sit above the last column either, because `saffron/ledger.py:155-157`
measures a comment there breaking `DROP COLUMN` on SQLite 3.51.0. The block under
the new last column counts as new, so keep it to two lines with the measured fact
in them.

**One docstring to correct.** `_touch_task` says it takes one of four literals
(`saffron/ledger.py:706`). If `task_push` stops calling it, that count is three.

**Tests that name the new column.** `tests/test_ledger.py:1048` starts
`_TASKS_COLUMN_READERS`, and `test_the_schema_adds_no_column_that_nothing_reads`
fails until it has an entry for this column. Name the function holding the rule.
`test_a_ledger_that_predates_the_package_columns_keeps_its_rows` removes a pair
of adjacent schema lines (`tests/test_ledger.py:329`), so do not split that pair.

**Other text the change makes false.** `_StackingRefused`'s docstring
(`saffron/task.py:201-205`), `run_task`'s (`saffron/task.py:693-695`) and
`Refused`'s (`saffron/task.py:540`) list what refuses. `_resolve_multi_parent`'s (`saffron/task.py:320-328`) and
`_stack_base_candidate`'s (`saffron/scheduler.py:1011-1020`) say what each reads.
Bring each into line, within ten lines.

**`base_sha` on the one-parent path.** It is optional there
(`saffron/task.py:446`), and `run_task` always passes it. Read it only once a row
would refuse, so the one-parent tests with no base keep working. Read retirement
as `_resolve_multi_parent` does (`saffron/task.py:352-360`).

**Fixtures.** `_pushed_saffron_repo`, `_push_stacked_branch`, `_chain_spec_text`,
`_ceiling_spec`, `_seed_repo`, `_seed_task`, `_fake_gh_unreachable_for` and
`_fake_gh_says_merged` in `tests/test_cli.py`. `_task_at` and `_write_spec` in
`tests/test_scheduler.py`, whose ids need digits, such as `SY-1000`. Give each
case its own ledger file. `_seed_task`'s `pr_url` writes that column alone.
`adopt_pull_request` also writes the pushed state, so it sets the new column.
`reconcile` asks a `REBUTTAL_UNJUDGED` row only when it carries a `pr_url`
(`saffron/reconcile.py:178-181`, over `SA-0331`). `_fake_gh_says_merged` answers
`MERGED` for every url, and `_fake_gh_unreachable_for` leaves a named url unasked.
So give a carried row its own url, and let the older-row `MERGED` case carry its
`pr_url` on the older row alone. The stack base's row pushed in the state and
carrying a `pr_url` cannot arise over `SA-0331`'s guard. It stays as the other
side of the rule. Import `run_batch`, `Readiness` and `PinnedBase` inside the test, since
`tests/test_batch.py:18` imports `tests/test_scheduler.py`.

**Measured on a prototype.** It sat at `f596e814`, with `SA-0331`'s
`MERGE_ONLY_STATES` line and `_ADOPTABLE_STATES` change applied. The host's SQLite is 3.53.1, and the
schema block's `DROP COLUMN` tests passed there. All four new witnesses passed.
Each failed with this spec's source reverted, by a runtime assertion or a missing
key, never at collection. Every wrong version above was applied as an edit, and
each declared mutant too. Each failed its own witness. An earlier copy at
`f596e814` alone passed every hook in `make check`, and its suite ran 4718 passed
and 7 failed. All seven read git history that one-commit copy lacks, in
`tests/records/test_records_integrity.py` and `tests/test_corpus.py`. Over
`SA-0331`'s lines, the seven test modules this spec touches or relies on ran 496
passed and no failures. The source diff measured 337 changed tokens against the
`bug` ceiling of 1300.
