---
id: SA-0186
title: '`saffron cell` stacks a child on a merged parent''s branch, because it never asks GitHub whether the parent merged'
type: bug
priority: 1
depends_on: []
estimated_lines: 140
touches:
  - saffron/task.py
  - saffron/reconcile.py
  - saffron/cli.py
  - saffron/events.py
  - tests/test_cli.py
  - tests/test_events.py
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
  - saffron/batch.py
  - saffron/scheduler.py
  - saffron/ledger.py
  - saffron/intake.py
  - saffron/record/**
  - saffron/report/**
  - saffron/repos/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - tests/test_task.py
  - tests/test_reconcile.py
  - tests/test_scheduler.py
  - tests/test_package.py
budget_usd: 18
max_attempts: 3
max_turns: 120
acceptance:
  - claim: >-
      Before it stacks, `saffron cell` asks GitHub about its parent's pull
      requests. A parent task the ledger reads as `READY_FOR_REVIEW`, and one
      it reads as `APPROVED`, whose pull request merged is recorded `MERGED`.
      One read as `READY_FOR_REVIEW` whose pull request closed unmerged is
      recorded `REJECTED`, and one whose pull request drew changes is
      recorded `CHANGES_REQUESTED`. In each case the cell is cut from the
      default branch. An `unstacked` `Preflight` naming the parent and the
      state its task now holds reaches the task's `events.jsonl`. Only the
      parent's pull requests are asked about, so another spec's waiting task
      is left as it was.
    witness: tests/test_cli.py::test_saffron_cell_cuts_from_the_default_branch_once_its_parents_pull_request_stops_waiting
    mutant:
      file: saffron/reconcile.py
      find: state not in PR_PENDING_STATES
      replace: state != "READY_FOR_REVIEW"
  - claim: >-
      When `gh` gives no answer about the parent's pull request, `saffron cell`
      still stacks on the parent's branch as it does today, and one
      `Preflight` naming the parent, not `unstacked`, reaches `events.jsonl`.
      That holds for a `gh` that exits non-zero and for one that cannot
      start, and neither raises. A `gh` answering that the pull request is
      open and undecided stacks the cell with no `Preflight` naming the
      parent.
    witness: tests/test_cli.py::test_saffron_cell_stacks_on_an_open_parent_and_says_so_only_when_gh_cannot_answer
    mutant:
      file: saffron/reconcile.py
      find: result.unasked.append(row["task_id"])
      replace: pass
  - claim: >-
      A waiting parent with no pull request recorded still stacks its child
      on the parent's branch.
    witness: tests/test_cli.py::test_a_resolvable_parent_reaches_the_cell_stacked
    preserves: true
  - claim: >-
      `saffron queue` still reconciles, before it scans, a waiting task
      whose pull request merged, with no spec named to narrow it.
    witness: tests/test_cli.py::test_queue_reconciles_before_it_scans_so_the_refusal_gate_sees_current_state
    preserves: true
---

## Context

Backlog item **b-877e93**, found in the spec loop's run 19. It cites
`DESIGN.md` §4.2. `SA-0178`'s cell, and `SA-0147`'s first, ran stacked on
`saffron/SA-0159` at `fd6513a6`. That branch had merged in run 18. No
reconcile ran after the merge, so the ledger still read `SA-0159`'s task
as waiting. The cells missed #535 and the `tests` gate change from
b-76f08d, and their baselines ran the old `.saffron/gates`.

Every line number below was read at `8349d7b0`, and holds at `63d53946`.

**How a parent is chosen today.** `_resolve_stacked_on` takes
`depends_on[0]` and reads that spec's task rows from the ledger
(`saffron/task.py:211-214`). It keeps the rows in
`DEPENDENCY_WAITING_STATES` (`:215`), which are `READY_FOR_REVIEW`,
`APPROVED` and `MERGE_TRAIN` (`saffron/scheduler.py:97`). No waiting row
means an unstacked cell (`saffron/task.py:216-217`). Otherwise it fetches
the newest waiting row's branch and stacks on its head (`:218-247`). It
never asks whether that branch merged. The item's cells stacked on
`saffron/SA-0159` after it merged, so that branch still fetched. No
evidence file records the fetch itself. The `ParentGone` path at
`saffron/task.py:235-244` fires only for a branch the origin no longer has.

**Who reconciles.** `saffron queue` does. `_resolve_queue` calls
`reconcile` for it (`saffron/cli.py:867-869`). `saffron batch` does too.
Its opening scan calls `_resolve_queue` (`saffron/cli.py:1144-1151`). The
loop then calls `rescan()` after every task (`saffron/batch.py:318`), and
`_rescan` calls `_resolve_queue` (`saffron/cli.py:1189-1194`). `saffron
cell` does not. `_run_cell` builds the mirror, the protected-path and retirement
refusals and the ceilings, then calls `run_task` (`saffron/cli.py:387-473`).
Nothing in it calls `reconcile`.

**What `reconcile` already does.** It reads every task in the repo
through `tasks_by_repo` (`saffron/reconcile.py:147`). It asks `gh pr view` about each one with a
`pr_url` in `PR_PENDING_STATES` (`:48`, `:149-153`), which are
`READY_FOR_REVIEW`, `APPROVED` and `CHANGES_REQUESTED`. `_next_state`
maps a merged pull request to `MERGED`, a closed one to `REJECTED`, and an
open one with changes requested to `CHANGES_REQUESTED` (`:118-131`). An
open, undecided one maps to `None`, and the row is left as it was
(`:161-163`). A mapped state is written at `:169-172`. A `gh` that exits non-zero
or prints no usable JSON leaves the row as it was and lists its id in
`unasked` (`:105-115`, `:154-156`). A `gh` that cannot start raises from
`run_gh` (`:41-42`). `_guarded_gh` turns that into a non-zero exit
(`saffron/cli.py:1426-1441`). `_resolve_queue` passes
`_guarded_gh(gh_failures)` to `reconcile` (`saffron/cli.py:868`).

## Problem

`saffron cell` stacks a child on a parent's branch after the parent's pull
request merged, whenever no `saffron queue` or `saffron batch` has run
since the merge.

Reconcile the parent's tasks at the point the parent is chosen, reusing
`reconcile`:

1. `reconcile` gains a keyword that narrows the rows it reads to one
   `spec_id`. With none given it reads every task in the repo, as today.
   `tasks_by_repo` already returns `spec_id` (`saffron/ledger.py:860`).
2. `_resolve_stacked_on` gains an optional `GhRunner` keyword, defaulting
   to `None`. Given one, it reconciles `depends_on[0]`'s tasks before it
   reads that parent's rows through `tasks_by_spec_id`
   (`saffron/task.py:214`). `None` reconciles
   nothing, as today.
3. `run_task` gains the same keyword and passes it to `_resolve_stacked_on`
   at `saffron/task.py:343-351`.
4. `_run_cell` passes `_guarded_gh(...)` to `run_task` at
   `saffron/cli.py:458-468`, the way `_resolve_queue` passes one to
   `reconcile`.

**When the parent stops waiting.** A reconcile that writes `MERGED`,
`REJECTED` or `CHANGES_REQUESTED` onto the parent's task leaves it no
waiting row. The resolver's existing path at `saffron/task.py:216-217` then
cuts the cell from the default branch, as it does today for any parent
with no waiting row. Before it returns, emit an `unstacked` `Preflight`
whose detail names the parent and the state its task now holds. The state
read back from the ledger goes in the detail, so a changes-requested
parent reads as one and never as a merge.

**When the pull request is open and undecided.** Nothing moves, the
parent's row stays waiting, and the cell stacks as today. Emit nothing
about the parent.

**When `gh` gives no answer.** The parent's row stays waiting, so the
cell stacks on its branch as it does today. Emit a `Preflight` whose
detail names the parent and says GitHub could not be asked whether its
pull request merged. Its step is not `unstacked`, because the cell still
stacks. That keeps the operator's `saffron cell` running, and the stacking
decision is readable in `events.jsonl` the morning after. Refusing the
cell would stop a stacked run over a transient `gh` failure. Cutting from
the default branch would build the child without its parent's work.

**The new line's family.** `describe` renders a `Preflight` whose step is
neither `cell_up` nor `unstacked` as `preflight: <detail>`
(`saffron/events.py:724-729`). `FAMILIES` lists each rendered shape with
the symbol that emits it (`saffron/events.py:895`). Its `unstacked:` row
already cites the resolver (`saffron/events.py:903`). Add a row for the new line,
cited to `task.py:_resolve_stacked_on`. `tests/test_events.py:1215-1216`
pins the table at 67 rows and 67 prefixes. Move both to 68, and add
`SA-0186` to that test's docstring beside `SA-0133`.

## Out of scope

- **`saffron batch`.** It reconciles at every scan, so its runners pass no
  `GhRunner` and are left alone. A stack batch hands `run_task` a
  `Handoff`, and `run_task` reads `handoff` instead of calling the
  resolver (`saffron/task.py:340-341`).
- **A parent at `MERGE_TRAIN`.** It is waiting but not in
  `PR_PENDING_STATES`, so `reconcile` never asks about it. No code writes
  that state today.
- **The resumed-task window** (`saffron/reconcile.py:15-25`, backlog
  item 29). A parent whose own cell is in PACKAGE while its child
  starts could be asked about mid-write. `saffron queue` carries the same
  risk. Narrowing to the parent's rows keeps every other task out of it.
- **Printing `head_moved` or the reconcile summary** from `saffron cell`.
- **Refusing the child of a parent that stopped waiting.** A parent can
  now read `REJECTED` or `CHANGES_REQUESTED` here. §4.2's gate 1 branches a
  dependent off its parent's branch. `saffron queue` refuses such a child,
  since its parent is not `MERGED` (`saffron/scheduler.py:621`). `saffron cell` runs no dependency refusal,
  and cuts from the default branch for any parent with no waiting row
  already. So a child of a changes-requested parent is still built without
  its parent's work. This spec makes that visible through the `unstacked`
  line, and changes nothing else about it.

## Notes for the agent

**Both criteria edit existing code**, so each declares a mutant on text
`reconcile.py` already holds. Criteria 3 and 4 are `preserves` and name
tests that pass now.

**Criterion 1's witness** follows
`test_a_resolvable_parent_reaches_the_cell_stacked`
(`tests/test_cli.py:652-676`). It builds `_local_origin`, pushes
`saffron/SY-9000` with `_push_parent_branch`, and gives `_ceiling_spec`
`depends_on: [SY-9000]`. It seeds the parent `READY_FOR_REVIEW` with a
`pr_url` and a recorded push, through `_seed_task`
(`tests/test_cli.py:1672-1688`). It seeds a second spec's task,
`READY_FOR_REVIEW` with its own `pr_url`. It patches `saffron.cli.run_gh`
with a double that records each URL it is asked about and answers as
`_fake_gh_says_merged` does (`:1700-1703`). Then, for `READY_FOR_REVIEW` and
then `APPROVED` as the parent's state, it runs `_capture_cell_spec`
(`:549-563`) and asserts four things. The captured `stacked_on` is `None`.
The only URL asked about is the parent's. The parent's row reads `MERGED`.
The newest `Preflight` in `read_log(tmp_path / "out" / "SY-2")` whose
detail names `SY-9000` has step `unstacked`. Its detail names the state the
row now reads, and none of the other three. Two more passes set the parent
back to `READY_FOR_REVIEW` and answer as a closed pull request and as
`_fake_gh_says_changes_requested` (`tests/test_cli.py:1706-1709`). Each asserts the same
four things, with `REJECTED` and `CHANGES_REQUESTED` as the state. After
all four, the second spec's row still reads `READY_FOR_REVIEW`. At the tree base the branch is pushed, the cell stacks, and the witness
fails.

**Criterion 2's witness** seeds the same parent with one `pr_url`. It runs
`_capture_cell_spec` three times, with `saffron.cli.run_gh` patched to
return exit 1, then to `_no_gh` (`tests/test_cli.py:1712-1713`), then to
answer `OPEN` with `reviewDecision` `REVIEW_REQUIRED`. Each time it asserts
that `stacked_on` is the pushed branch's head. It counts the `Preflight`
events naming `SY-9000` that the call added. The first two passes add
exactly one, the open pass adds none, and none is `unstacked`. It fails at
the tree base, where no such `Preflight` is written.

**Wrong versions these witnesses must kill.** Each one below failed a
prototype's witnesses on 2026-09-27.

- A resolver that says the parent merged whenever no waiting row is left.
- A resolver that says GitHub could not be asked whenever the parent still
  waits.
- An `unstacked` line emitted only for a merge.

- A resolver that reconciles the whole repo rather than the parent's tasks.
- A resolver that reads the parent's rows before it reconciles.
- A `_run_cell` that passes no `GhRunner`, or passes `run_gh` unguarded.
- A resolver that treats a `gh` with no answer as a merge.
- A merge or a `gh` failure said through `print` rather than `emit`.
- A merge found by asking `gh` directly, with no `MERGED` written.
- Asking only about a `READY_FOR_REVIEW` row.

**Two guards already hold the resolver.** It writes to no stream
(`tests/test_package.py:1405-1418`), so both new lines go through `emit`.
It keeps `(None, None)` or a pair together (`saffron/task.py:159-163`).

**Queued `SA-0150` touches `saffron/task.py` too**, in `run_task`. It
depends on `SA-0182` and has not run. This spec does not depend on it.
Whichever merges second reads the other's lines. Queued `SA-0185` also
touches `saffron/task.py`, in `run_task`'s `CellSpec` build. The hunks are
separate, and the operator orders the two.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words.

**Size.** `size` is advisory here: no touched path is in `elevate_on`, and
the spec is `standard`. A prototype with all six witness passes, counted by
`size_gate`, came to 558 tokens against the `bug` ceiling of 1300.
`estimated_lines` is that count over four, with no overrun added.
