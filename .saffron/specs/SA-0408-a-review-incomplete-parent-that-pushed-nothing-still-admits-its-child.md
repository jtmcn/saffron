---
id: SA-0408
title: "A REVIEW_INCOMPLETE parent that pushed nothing still admits its child, and no merge moves such a row to MERGED"
type: bug
priority: 2
estimated_lines: 43
estimate_measured: true
retired_first: []
touches:
  - saffron/scheduler.py
  - saffron/task.py
  - saffron/reconcile.py
  - saffron/phases/package.py
  - tests/test_cli.py
  - tests/test_scheduler.py
  - tests/test_reconcile.py
  - tests/test_package.py
  - tests/test_ledger.py
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
  - saffron/ledger.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/cell/**
  - saffron/phases/review.py
  - saffron/phases/rebut.py
  - saffron/record/**
  - saffron/report/**
  - saffron/view/**
  - saffron/gates/**
  - tests/test_session.py
  - tests/test_review.py
  - tests/test_rebut.py
  - tests/test_task.py
  - tests/test_batch.py
budget_usd: 64
max_attempts: 3
max_turns: 300
risk: standard
acceptance:
  - claim: >-
      With one `depends_on` entry, `_resolve_stacked_on` raises
      `_StackingRefused` when the parent's chosen row is `REVIEW_INCOMPLETE`
      and no push followed that state. The reason names the parent beside
      `REVIEW_INCOMPLETE`, says its latest run pushed nothing, and never
      names `REBUTTAL_UNJUDGED`. The witness drives three rows in both `gh`
      modes: no push, a stale push, and no push on a row newer than a pushed
      `READY_FOR_REVIEW` row. A row that pushed in the state stacks on the
      fetched head of a branch a review fix moved, in both `gh` modes. So
      does a newer `READY_FOR_REVIEW` row that pushed over an older stale
      `REVIEW_INCOMPLETE` row, in both `gh` modes. With
      no `gh`, a stale row beside a `MERGED` row, one whose older row pushed
      `base_sha` itself, and one retired at `base_sha` each stack on their
      branch. A stale row that carries a pull request refuses when a `gh`
      answers open and when it cannot answer. When it answers merged,
      `reconcile` moves the row to `MERGED` and the child starts unstacked.
      Through `cli._run_cell` with a `gh`, the no-push row returns 1
      before any cell starts. It prints the reason with no `unstacked` line,
      and writes no task row.
    witness: tests/test_cli.py::test_a_child_of_a_review_incomplete_parent_stacks_only_on_its_latest_runs_push
    wrong_versions:
      - The rule still reads `REBUTTAL_UNJUDGED` alone, so every `REVIEW_INCOMPLETE` row stacks or starts unstacked.
      - The rule compares `pushed_in_state` with the literal `REBUTTAL_UNJUDGED`, so a row that pushed in `REVIEW_INCOMPLETE` is refused.
      - The reason keeps the literal `REBUTTAL_UNJUDGED`, so a `REVIEW_INCOMPLETE` parent is named in the wrong state.
      - The `REVIEW_INCOMPLETE` refusal sits only on the path with no `gh`.
      - The `REVIEW_INCOMPLETE` refusal sits only on the path with a `gh`.
      - A `REVIEW_INCOMPLETE` row refuses even when its parent already landed, so a merged, retired or landed parent refuses its child.
      - Only an empty `pushed_sha` refuses, so a stale push still stacks.
      - The oldest waiting row decides, so an older pushed row rescues a newer row with none.
      - The check runs after `_fetch_parent_head`, so an `unstacked` line prints before the refusal.
      - A row GitHub could not be asked about is not refused.
      - Any stale waiting row refuses, so an older stale row refuses a child whose newest row pushed.
      - '`reconcile` still skips the state, so a merged pull request on the parent leaves its child refused.'
  - claim: >-
      With two or more `depends_on` entries, `_resolve_multi_parent` refuses
      for every open parent whose chosen row is `REVIEW_INCOMPLETE` with no
      push after that state, before it picks the deepest. The reason names
      each refused parent beside its own state and no other parent. The
      witness drives the deepest parent with no push, a shallower one on its
      chain with a stale push, and one off that chain with no push, in both
      `gh` modes. The off-chain reason names neither the chain nor the
      deepest parent. A `REBUTTAL_UNJUDGED` parent with a stale push beside a
      `REVIEW_INCOMPLETE` one with none names each in its own state, and says
      their latest run pushed nothing. A deepest parent that pushed in
      `REVIEW_INCOMPLETE` stacks on its head, in both `gh` modes.
    witness: tests/test_cli.py::test_a_multi_parent_child_is_refused_for_any_open_review_incomplete_parent_that_pushed_nothing
    wrong_versions:
      - The multi-parent path keeps reading `REBUTTAL_UNJUDGED` alone, and only the one-parent path changes.
      - The reason keeps the literal `REBUTTAL_UNJUDGED` for every refused parent.
      - The reason names every refused parent in the first one's state.
      - Only the deepest parent is read, so a shallower or off-chain parent passes.
      - The check runs after the chain check, so an off-chain parent is refused for the chain.
      - The rule compares `pushed_in_state` with the literal `REBUTTAL_UNJUDGED`, so the deepest parent that pushed in its state is refused.
  - claim: >-
      `_stack_base_candidate` does not qualify a newest waiting row that is
      `REVIEW_INCOMPLETE` with no push after that state, so `build_queue`
      with `stack=True` refuses the child under `depends_on`. The reason
      names the parent, `REVIEW_INCOMPLETE` and that its latest run pushed
      nothing, never names `REBUTTAL_UNJUDGED`, and ends on the remedy to
      merge it or rerun it. The witness drives three rows that carry a pull
      request: a stale push, no push, and a stale row newer than a pushed
      `READY_FOR_REVIEW` row. A row that pushed in the state is the one
      candidate, with that row as its stack base. A newer
      `READY_FOR_REVIEW` row that pushed over an older stale
      `REVIEW_INCOMPLETE` row qualifies as the stack base.
    witness: tests/test_scheduler.py::test_a_stack_order_refuses_a_child_whose_review_incomplete_stack_base_pushed_nothing
    wrong_versions:
      - The stack base path still reads `REBUTTAL_UNJUDGED` alone, so a stale `REVIEW_INCOMPLETE` row with a pull request becomes the base.
      - The reason keeps the literal `REBUTTAL_UNJUDGED`.
      - The oldest waiting row decides, so an older pushed row qualifies in place of a newer stale one.
      - Any stale waiting row refuses, so an older stale row disqualifies a newer row that pushed.
      - The check follows the pushed-sha check, so a row with no push gets a reason that never names its latest run.
      - The remedy tells the operator to run the parent to a pull request, which it already carries.
  - claim: >-
      `reconcile` asks about a `REVIEW_INCOMPLETE` row that carries a pull
      request, and a merge is the one answer that moves it. A merged answer
      moves it to `MERGED`, records the merged head, and reports a moved
      one. A row a crash left with its merged head on the ledger completes
      with no `gh` call. The witness drives six answers `_next_state` reads
      other than a merge: closed, changes requested, marked ready, an open
      draft, an open answer with no `isDraft`, and an unrecognised state. Each
      leaves the row at `REVIEW_INCOMPLETE` with nothing written to
      `rejected`, `changes_requested` or `approved`. It drives the three answers
      `_pr_status` turns into `None`, and each lands in `unasked`. A null and
      an empty `pr_url` are never asked.
    witness: tests/test_reconcile.py::test_a_review_incomplete_row_is_asked_and_moves_on_no_answer_but_a_merge
    wrong_versions:
      - The state stays out of `MERGE_ONLY_STATES`, so a merged pull request leaves the row `REVIEW_INCOMPLETE`.
      - The state joins `PR_PENDING_STATES` instead, so a closed pull request writes `REJECTED` and an approval writes `APPROVED`.
      - A `gh` failure on this state is dropped rather than recorded in `unasked`.
      - An empty `pr_url` is asked, because the skip tests it against `None`.
  - claim: >-
      Another row of this spec at `REVIEW_INCOMPLETE` that carries a pull
      request refuses a rerun's unpackaged push, and the remote branch stays
      where it was. The note says `awaiting review or a merge` and `not ours
      to replace`. The witness drives every member of `TaskState` on the
      outcome, with the other row on either side of the outcome's task id.
      An empty `pr_url` on that row lets the push through, and the branch
      moves.
    witness: tests/test_package.py::test_another_review_incomplete_row_with_a_pull_request_keeps_that_branch
    wrong_versions:
      - The guard leaves `REVIEW_INCOMPLETE` out, so the rerun's push replaces the branch.
      - The guard refuses on `REVIEW_INCOMPLETE` without reading its `pr_url`, so a row with an empty one still refuses.
      - The new state refuses only when the outcome ended `REBUTTAL_UNJUDGED`.
      - The guard reads only rows with a lower task id than the outcome's.
  - claim: >-
      Every other waiting state keeps its result on the one-parent path:
      `READY_FOR_REVIEW`, `APPROVED` and `MERGE_TRAIN` stack on an older push
      in both `gh` modes, and so does `CHANGES_REQUESTED` with a `gh`. A
      `REBUTTAL_UNJUDGED` parent refuses as it does today.
    witness: tests/test_cli.py::test_a_child_of_a_rebuttal_unjudged_parent_stacks_only_on_its_latest_runs_push
    preserves: true
    wrong_versions:
      - The rule reads every member of `DEPENDENCY_WAITING_STATES`, so a `READY_FOR_REVIEW` row with an older push is refused.
  - claim: >-
      Apart from `REVIEW_INCOMPLETE`, which criterion 5 adds, another row of
      this spec follows today's rule. With a pull request it refuses the push
      at `READY_FOR_REVIEW`, `EXHAUSTED`, `CHANGES_REQUESTED`, `APPROVED` and
      `REBUTTAL_UNJUDGED`. Every other member of `TaskState` lets it through.
    witness: tests/test_package.py::test_another_row_with_a_standing_pull_request_keeps_that_branch
    preserves: true
    wrong_versions:
      - The guard refuses on any state whose row carries a `pr_url`, so a `NOT_IMPLEMENTED` or `REJECTED` row refuses.
  - claim: >-
      `saffron adopt` still refuses a `REVIEW_INCOMPLETE` row before any `gh`
      call, so no adoption moves such a row and lets it push again in that
      state.
    witness: tests/test_cli.py::test_adopt_refuses_with_exit_one_and_writes_nothing
    preserves: true
    wrong_versions:
      - '`_ADOPTABLE_STATES` is rebuilt on `MERGE_ONLY_STATES`, so the widened set makes `REVIEW_INCOMPLETE` adoptable.'
---

## Context

Backlog item **b-e9dd4c**, found by the first review of `SA-0330`. It cites
`DESIGN.md` §4.2 and §5.5, and the change touches §3.3, §4.2.1 and §5.7.
Related: b-f603c9, which `SA-0330` closed for `REBUTTAL_UNJUDGED` alone.
Every line number below was read at `a5c1f2e9`.

**The protected text, as amended by hand in this spec's own pull request.**
No cell edits these.

- `DESIGN.md` §3.3's `REVIEW_INCOMPLETE` entry says its dependent stacks only
  on a push its latest run made, and that it leaves for `MERGED` on a merge.
- `DESIGN.md` §4.2's gate 0 names this refusal beside `SA-0330`'s.
- `DESIGN.md` §4.2.1 no longer hands this state's gaps to b-e9dd4c.
- `DESIGN.md` §5.7 names `REVIEW_INCOMPLETE` beside `REBUTTAL_UNJUDGED` in the
  push guard's list of other rows.
- `CONTEXT.md`'s **Stack base** and **`REVIEW_INCOMPLETE`** entries, and ADR 7,
  read the same way.

**How a `REVIEW_INCOMPLETE` row gets its state and its push.** The cell writes
every state but `READY_FOR_REVIEW` before it returns
(`saffron/cell/session.py:4061-4062`). `run_task` packages only
`READY_FOR_REVIEW` and an exhausted-mode `EXHAUSTED` cell
(`saffron/task.py:1009-1014`). Every other outcome reaches
`push_unpackaged_work` (`saffron/task.py:1093`). A push records
`pushed_in_state` as the state the row held at that moment
(`saffron/ledger.py:950`). So a push in this state reads `REVIEW_INCOMPLETE`,
and a refused one leaves the column on whatever an earlier run wrote.

**Nothing re-enters the state.** `REVIEW_INCOMPLETE` is not in
`REQUEUE_STATES` (`saffron/scheduler.py:162-172`). `saffron package` takes only
`READY_FOR_REVIEW` and `ORPHANED` (`saffron/task.py:1352`). `saffron adopt`
refuses every state outside `_ADOPTABLE_STATES`, which leaves it out
(`saffron/cli.py:3134-3136`, `:3218`). So no later writer records a push on
such a row in that state, the premise `SA-0330`'s rule states for
`REBUTTAL_UNJUDGED` (`saffron/scheduler.py:150-151`).

**The rule names one state.** `_stale_rebuttal_unjudged` tests
`REBUTTAL_UNJUDGED` alone (`saffron/scheduler.py:147-156`). Three places read
it. `_resolve_stacked_on`, the one-parent resolver, refuses through it ahead
of the fetch unless the parent landed (`saffron/task.py:588-595`). The multi-parent
resolver collects every open parent it holds for, before the chain check
(`saffron/task.py:435-448`). `_stack_base_candidate` returns `_MERGE_OR_RERUN`
under it, ahead of its pushed-sha check (`saffron/scheduler.py:1092-1097`).
All three reasons spell `REBUTTAL_UNJUDGED` as a literal
(`saffron/task.py:445`, `:594`, `saffron/scheduler.py:1094`). So a
`REVIEW_INCOMPLETE` parent with no push unstacks its child onto `base_sha`,
and one with a stale push stacks it on an older branch head. §4.2 calls that
child "a version that lies".

**`reconcile` never asks about the row.** A row outside `PR_PENDING_STATES`
and `MERGE_ONLY_STATES` is skipped (`saffron/reconcile.py:177-182`), and the
merge-only set leaves `REVIEW_INCOMPLETE` out (`saffron/reconcile.py:47`). A
merge is the one answer that moves a merge-only row
(`saffron/reconcile.py:205-209`). So a merged pull request on such a row
leaves it `REVIEW_INCOMPLETE`, and its child still reads the parent as open.

**The push guard leaves the state out.** `push_unpackaged_work` refuses beside
another row at `READY_FOR_REVIEW` (`saffron/phases/package.py:1233-1244`). It
also refuses beside one carrying a pull request at `EXHAUSTED`,
`CHANGES_REQUESTED`, `APPROVED` or `REBUTTAL_UNJUDGED`. A rerun beside a `REVIEW_INCOMPLETE`
row that carries one replaces that pull request's branch.

**Which path reads `gh`.** `cli._run_cell` passes a `gh`, and
`cli._batch_runner` passes none. With a `gh`, the one-parent resolver reads
`_STACKABLE_ON_RECONCILE`, and without one `DEPENDENCY_WAITING_STATES`
(`saffron/task.py:539-555`). The multi-parent resolver picks between the same
two (`saffron/task.py:414-416`).

**The live ledger.** `~/.saffron/ledger.db` holds no row at `REVIEW_INCOMPLETE`
or `REBUTTAL_UNJUDGED` (measured 2026-11-17). No queued spec sits on this
base, so `retired_first` is empty.

## Problem

1. **One set, spelled once.** Name the pair `REBUTTAL_UNJUDGED` and
   `REVIEW_INCOMPLETE` once, as one module-level `frozenset` in
   `saffron/scheduler.py`, beside `DEPENDENCY_WAITING_STATES`. The rule, the
   merge-only set and the push guard all read it.
2. **One rule.** Replace `_stale_rebuttal_unjudged` with one predicate: the
   row's state is in that set, and its `pushed_in_state` is anything other
   than that same state, `None` included. Rename it so its name says neither
   state alone. `tests/test_ledger.py:1160` names the old function as the
   reader of `pushed_in_state`, so point that entry at the new name.
3. **The reasons.** Each of the three reasons names the row's own state
   rather than a literal. The one-parent and stack base reasons keep their
   shape otherwise. The multi-parent reason keeps its `depends_on ` prefix,
   names each refused parent as `<id> is <state>`, the shape the one-parent
   reason has, then `its` or `their latest run pushed nothing` as today.
4. **`reconcile`.** `MERGE_ONLY_STATES` reads the set, beside `EXHAUSTED` and
   `NOT_IMPLEMENTED`. Nothing else in `reconcile`'s logic changes.
5. **The push guard.** The other-row guard in `push_unpackaged_work` refuses
   for a row in the set that carries a pull request, beside `EXHAUSTED`,
   `CHANGES_REQUESTED` and `APPROVED`. `READY_FOR_REVIEW` keeps its own rule.

## Out of scope

- **REBUT's own `EXHAUSTED` and `REVIEW_INCOMPLETE` after REBUT.** `SA-0406`
  and `SA-0407` take those for b-f7a591 in `saffron/cell/session.py`,
  `saffron/phases/review.py` and `saffron/phases/rebut.py`. This spec touches
  none of them, so the two stay independent.
- **`_dependency_refusal` and the plain scan.** `saffron queue` still lists
  such a child, and `run_task` refuses it, as `SA-0330` left
  `REBUTTAL_UNJUDGED`.
- **`saffron adopt`.** `_ADOPTABLE_STATES` keeps its four members, and its
  comment stays true (`saffron/cli.py:3132-3136`).
- **`saffron/record/migrate.py`'s docstring.** It names a row that pushed in
  `REBUTTAL_UNJUDGED` as reading refused after a migration
  (`saffron/record/migrate.py:4-5`). That stays true, and a migrated
  `REVIEW_INCOMPLETE` row reads the same way. The live ledger holds neither.
- **`push_unpackaged_work`'s docstring.** Its list of other rows sits past the
  docstring's tenth line (`saffron/phases/package.py:1148-1150`). The `prose`
  gate keys each line past the tenth by its text, so any edit there is a new
  hit. Leave that docstring as it stands. The comment above the guard names
  the set instead.
- **`DESIGN.md`, `CONTEXT.md` and ADR 7**, amended by hand as above.

## Notes for the agent

**Mutants and new code.** Criteria 1 to 5 each have a mutant on
`refs/saffron/mutants`, keyed by witness. Each sits on a line this change keeps, so leave the
lines around each new check as they are. A mutant applies only where its
line matches once in its file, so add no second copy of a line you keep.
Criteria 6 to 8 name tests that exist and must stay green. Criteria 6 and 7
name two of the four tests below, which change as listed. Do not run the
wrong versions yourself.

**Every new witness must fail with the source reverted.** So keep each
admission inside the five new witnesses. A row that pushed in the state is
one, and a landed parent is another. A separate test of them passes at base, and
`revert` then blocks it.

**Four existing tests pin the old behaviour, and each must change.**

- `tests/test_cli.py:2336-2360` drives `REVIEW_INCOMPLETE` among the states
  that still stack on an older push. Drop it from that tuple.
- `tests/test_cli.py:2823-2849` expects a deepest `REVIEW_INCOMPLETE` parent
  with no push to start unstacked. Remove that case. Criterion 2's witness
  drives it now.
- `tests/test_scheduler.py:3341-3362` qualifies a `REVIEW_INCOMPLETE` row
  with an older push as a stack base. Drop it from that tuple.
- `tests/test_package.py:3800-3875` lets every state outside five push beside
  a row with a pull request. Add `REVIEW_INCOMPLETE` to its `refusing` set and
  its docstring. Its loop over the three new states needs no change.

Each comment above those tuples says the rule reads only
`REBUTTAL_UNJUDGED`. So does the docstring of the stack base test
(`tests/test_scheduler.py:3179-3185`). Bring each into line.

**Imports.** `saffron/reconcile.py` imports only `saffron.ledger` from this
package today (`saffron/reconcile.py:32`), and its docstring says
`saffron/scheduler.py` and `saffron/phases/package.py` must not import from
it (`saffron/reconcile.py:6-7`). Importing the set from `saffron/scheduler.py`
into both is the other direction, and no module cycle results (measured on
the prototype).

**Docstrings at the ten-line limit.** The `prose` gate counts a docstring
line past the tenth as a hit keyed by its text. A line wider than 88
characters wraps into more lines. `_parent_landed`, `_resolve_multi_parent`,
`_resolve_stacked_on`, `Refused`, `run_task` and `_stack_base_candidate` sit
at ten or eleven lines. Edit their state lists in
place and keep each at its base length. `_StackingRefused` has room. The module docstring of
`saffron/task.py` has no such limit. Its **A stale parent** bullet names
`REBUTTAL_UNJUDGED` alone (`saffron/task.py:32-33`), so bring it into line.

**Other text the change makes false.** Three comments name
`REBUTTAL_UNJUDGED` alone. One sits above `DEPENDENCY_WAITING_STATES`
(`saffron/scheduler.py:128-129`). One sits in `reconcile`
(`saffron/reconcile.py:177-178`). One sits above the push guard
(`saffron/phases/package.py:1233-1234`). Bring each into line.

**Fixtures.** `_pushed_saffron_repo`, `_push_stacked_branch`,
`_chain_spec_text`, `_mirror_of`, `_seed_repo`, `_seed_task`, `_namespace`,
`_ceiling_spec` and `_gh_open` in `tests/test_cli.py`. `_pushed_saffron_repo`
takes `retired_specs` for a parent retired at `base_sha`. `_task_at`,
`set_task_package`, `_write_spec` and `_spec_dir` in `tests/test_scheduler.py`,
whose spec ids need digits, such as `TB-40`. `_task`, `_repo`, `_FakeGh`,
`_state`, `_merged_head`, `_PUSHED` and `_FIXED` in `tests/test_reconcile.py`.
The `packageable` fixture and `_another_row` in `tests/test_package.py`. Give
each case its own ledger file. A row seeded at `READY_FOR_REVIEW`, pushed,
then set to `REVIEW_INCOMPLETE` is a stale push. One set to the state first
and pushed after is a push in the state.

**Measured on a prototype.** Its source equalled `a5c1f2e9`. All five new
witnesses passed, and each failed with the source reverted, never at
collection. Every wrong version above was applied as an edit, and each
failed its own witness. The source diff measured 171 changed tokens against
the `bug` ceiling of 1300, and 1767 tokens under the test paths. The whole
suite passed on it, 5342 tests.
