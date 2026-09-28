---
id: SA-0186
title: '`saffron cell` stacks a child on a merged parent''s branch, because it never asks GitHub whether the parent merged'
type: bug
priority: 1
depends_on: []
estimated_lines: 214
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
budget_usd: 21
max_attempts: 3
max_turns: 120
acceptance:
  - claim: >-
      Before it stacks, `saffron cell` asks GitHub about its parent's pull
      requests and no other spec's, even one whose id begins with the
      parent's. A merged pull request is recorded `MERGED`, from a parent
      task the ledger read as `READY_FOR_REVIEW` and from one it read as
      `APPROVED`. A pull request closed unmerged is recorded `REJECTED`. When
      the parent's newest task is `MERGED` or `REJECTED`, the cell is cut from
      the default branch, even with an older parent task still
      `READY_FOR_REVIEW`. That holds whether this reconcile moved the task or
      the ledger already held it. Each time, one `unstacked` `Preflight`
      naming the parent and the newest task's state reaches `events.jsonl`.
      A `MERGED` line names neither `REJECTED` nor `CHANGES_REQUESTED`, and a
      `REJECTED` line names neither `MERGED` nor `CHANGES_REQUESTED`.
    witness: tests/test_cli.py::test_saffron_cell_cuts_from_the_default_branch_once_its_parents_newest_task_merged_or_closed
    mutant:
      file: saffron/reconcile.py
      find: state not in PR_PENDING_STATES
      replace: state != "READY_FOR_REVIEW"
  - claim: >-
      When `gh` gives no answer about a parent whose task is
      `READY_FOR_REVIEW` or `CHANGES_REQUESTED`, `saffron cell` still stacks
      on the parent's branch. Exactly one `Preflight` saying GitHub could not
      be asked, naming the parent and not `unstacked`, reaches
      `events.jsonl`, though two of the parent's tasks went unasked. That
      holds for a `gh` that exits non-zero and for one that cannot start, and
      neither raises. A `gh` answering that the pull request is open and
      undecided stacks the cell with no `Preflight` naming the parent.
    witness: tests/test_cli.py::test_saffron_cell_stacks_on_a_parent_it_could_not_ask_about_and_says_so_once
    mutant:
      file: saffron/reconcile.py
      find: result.unasked.append(row["task_id"])
      replace: pass
  - claim: >-
      A parent whose task is `CHANGES_REQUESTED` keeps its child stacked on
      the parent's branch, where its review fixes land. That holds when this
      reconcile moved the task there and when the ledger already held it
      there. Each time, one `Preflight` naming the parent and
      `CHANGES_REQUESTED`, not `unstacked`, reaches `events.jsonl`.
    witness: tests/test_cli.py::test_saffron_cell_stacks_on_a_changes_requested_parent_and_names_the_state
    mutant:
      file: saffron/reconcile.py
      find: return "CHANGES_REQUESTED"
      replace: return None
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
  - claim: >-
      The resolver given no `GhRunner`, as `saffron batch`'s runners give
      none, still stacks only on a `READY_FOR_REVIEW`, `APPROVED` or
      `MERGE_TRAIN` task, never on a `CHANGES_REQUESTED` one.
    witness: tests/test_cli.py::test_which_of_a_parents_rows_supplies_the_sha_is_the_newest_waiting_one
    preserves: true
---

## Context

Backlog item **b-877e93**, found in the spec loop's run 19. It cites
`DESIGN.md` §4.2. `SA-0178`'s cell, and `SA-0147`'s first, ran stacked on
`saffron/SA-0159` at `fd6513a6`. That branch had merged in run 18. No
reconcile ran after the merge, so the ledger still read `SA-0159`'s task
as waiting. The cells missed #535 and the `tests` gate change from
b-76f08d, and their baselines ran the old `.saffron/gates`.

Every line number below was read at `8349d7b0`, and holds at `853d3012`.

**How a parent is chosen today.** `_resolve_stacked_on` takes
`depends_on[0]` and reads that spec's task rows from the ledger
(`saffron/task.py:211-214`). It keeps the rows in
`DEPENDENCY_WAITING_STATES` (`:215`), which are `READY_FOR_REVIEW`,
`APPROVED` and `MERGE_TRAIN` (`saffron/scheduler.py:97`). No waiting row
means an unstacked cell (`saffron/task.py:216-217`). Otherwise it fetches
the newest waiting row's branch and stacks on its head (`:218-247`). It
never asks whether that branch merged, and it takes the newest waiting row
whatever state the parent's newest task holds. The item's cells stacked on
`saffron/SA-0159` after it merged, so that branch still fetched. No
evidence file records the fetch itself. The `ParentGone` path at
`saffron/task.py:235-244` fires only for a branch the origin no longer has.

**Who reconciles.** `saffron queue` does. `_resolve_queue` calls
`reconcile` for it (`saffron/cli.py:867-869`). `saffron batch` does too.
Its opening scan calls `_resolve_queue` (`saffron/cli.py:1144-1151`). The
loop then calls `rescan()` after every task (`saffron/batch.py:318`), and
`_rescan` calls `_resolve_queue` (`saffron/cli.py:1189-1194`). `saffron
cell` does not. `_run_cell` builds the mirror, the protected-path and
retirement refusals and the ceilings, then calls `run_task`
(`saffron/cli.py:387-473`). Nothing in it calls `reconcile`.

**What `reconcile` already does.** It reads every task in the repo
through `tasks_by_repo` (`saffron/reconcile.py:147`). It asks `gh pr view`
about each one with a `pr_url` in `PR_PENDING_STATES` (`:48`,
`:149-153`), which are `READY_FOR_REVIEW`, `APPROVED` and
`CHANGES_REQUESTED`. So a parent already recorded `CHANGES_REQUESTED` is
asked again. `_next_state` maps a merged pull request to `MERGED`, a
closed one to `REJECTED`, and an open one with changes requested to
`CHANGES_REQUESTED` (`:118-131`). It never maps back to a waiting state.
An open, undecided one maps to `None`, and the row is left as it was
(`:161-163`). A mapped state is written at `:169-172`. A `gh` that exits
non-zero or prints no usable JSON leaves the row as it was and lists its
id in `unasked` (`:105-115`, `:154-156`). A `gh` that cannot start raises
from `run_gh` (`:41-42`). `_guarded_gh` turns that into a non-zero exit
(`saffron/cli.py:1426-1441`). `_resolve_queue` passes
`_guarded_gh(gh_failures)` to `reconcile` (`saffron/cli.py:868`).

## Problem

`saffron cell` stacks a child on a parent's branch after the parent's pull
request merged, whenever no `saffron queue` or `saffron batch` has run
since the merge.

Reconcile the parent's tasks at the point the parent is chosen, reusing
`reconcile`:

1. `reconcile` gains a keyword that narrows the rows it reads to one
   `spec_id`, matched exactly. With none given it reads every task in the
   repo, as today. `tasks_by_repo` already returns `spec_id`
   (`saffron/ledger.py:860`).
2. `_resolve_stacked_on` gains an optional `GhRunner` keyword, defaulting
   to `None`. Given one, it reconciles `depends_on[0]`'s tasks before it
   reads that parent's rows through `tasks_by_spec_id`
   (`saffron/task.py:214`). `None` reconciles nothing and changes nothing
   below, so `saffron batch`'s runners behave as today.
3. `run_task` gains the same keyword and passes it to `_resolve_stacked_on`
   at `saffron/task.py:343-351`.
4. `_run_cell` passes `_guarded_gh(...)` to `run_task` at
   `saffron/cli.py:458-468`, the way `_resolve_queue` passes one to
   `reconcile`.

Given a `GhRunner`, the resolver then decides as follows.

**Which rows it will stack on.** A `READY_FOR_REVIEW`, `APPROVED`,
`MERGE_TRAIN` or `CHANGES_REQUESTED` row. Keep that set in `task.py`,
built from `DEPENDENCY_WAITING_STATES`. Do not change the scheduler's set:
`saffron queue` still refuses a child of a `CHANGES_REQUESTED` parent,
because `_dependency_refusal` names any state that is not `MERGED`
(`saffron/scheduler.py:621`). A `CHANGES_REQUESTED` parent is stacked on
because its review fixes land on its branch (§4.2 gate 1, §4.2.1).

**The newest task decides first.** Say the parent's newest task is
`MERGED` or `REJECTED`. The resolver then stacks on no row, even an older
one it would otherwise take. An older row still pending is a pull request the
newer one replaced. It carries the same branch name, so stacking on it
restacks on the merged or closed branch.

**One trigger for the `unstacked` line.** The parent has a task, and the
resolver finds no row it will stack on. Emit one `unstacked` `Preflight`
naming the parent and the newest task's state. It fires
whether this reconcile moved that task or the ledger already held it. The
cell is then cut from the default branch by the existing path at
`saffron/task.py:216-217`. A parent with no task at all emits nothing, as
today.

**A `CHANGES_REQUESTED` parent.** When the row it stacks on is
`CHANGES_REQUESTED`, emit one `Preflight` naming the parent and
`CHANGES_REQUESTED`, whose step is not `unstacked`. It fires whether this
reconcile moved the task there or the ledger held it there.

**When the pull request is open and undecided.** Nothing moves, the
parent's row stays waiting, and the cell stacks as today. Emit nothing
about the parent.

**When `gh` gives no answer.** Emit one `Preflight` naming the parent.
It says GitHub could not be asked whether its pull request merged. It is
one line however many of the parent's tasks went unasked. Its step is not `unstacked`. Only a task
in `PR_PENDING_STATES` is asked, so an unasked parent task holds one of
three states, and it keeps that state.

- `READY_FOR_REVIEW` or `APPROVED`: the cell stacks on its branch, and
  this is the only line about the parent.
- `CHANGES_REQUESTED`: the cell stacks on its branch, and the
  `CHANGES_REQUESTED` line follows this one.

A `MERGED` or `REJECTED` newest task is not asked, so a failed `gh` never
changes that outcome. Refusing the cell over a transient `gh` failure
would stop an attended run. Cutting from the default branch would build the
child without its parent's work.

**The new lines' families.** `describe` renders a `Preflight` whose step
is neither `cell_up` nor `unstacked` as `preflight: <detail>`
(`saffron/events.py:724-729`). `FAMILIES` lists each rendered shape with
the symbol that emits it (`saffron/events.py:895`). Its `unstacked:` row
already cites the resolver (`saffron/events.py:903`). Add one row for the
`gh` line and one for the `CHANGES_REQUESTED` line, each cited to
`task.py:_resolve_stacked_on`. `tests/test_events.py:1215-1216` pins the
table at 67 rows and 67 prefixes. Move both to 69, and add `SA-0186` to
that test's docstring beside `SA-0133`.

## Out of scope

- **`saffron batch`.** It reconciles at every scan, so its runners pass no
  `GhRunner` and keep today's resolver. A stack batch hands `run_task` a
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
- **Refusing a child in `saffron cell`.** `saffron cell` runs no
  dependency refusal. A child of a `MERGED` parent needs none. A child of a
  `REJECTED` parent is cut from the default branch, with a line naming the
  state. Refusing it is gate 0's work, which `saffron queue` already
  does.

## Notes for the agent

**All three new criteria edit existing code**, so each declares a mutant
on text `reconcile.py` already holds. Criteria 4 to 6 are `preserves` and
name tests that pass now. Criterion 6's test passes no `GhRunner`, so it
holds the batch path to today's set.

**Shared witness helpers.** Each witness builds `_local_origin`, pushes
`saffron/SY-9000` with `_push_parent_branch`, and gives `_ceiling_spec`
`depends_on: [SY-9000]`, as `test_a_resolvable_parent_reaches_the_cell_stacked`
does (`tests/test_cli.py:652-676`). It seeds parent tasks through
`_seed_task` (`tests/test_cli.py:1672-1688`), each with its own `pr_url`
and a recorded push. It patches `saffron.cli.run_gh` and runs
`_capture_cell_spec` (`tests/test_cli.py:549-563`). After each run it reads
the `Preflight` events that run added whose detail names `SY-9000`, from
`read_log(tmp_path / "out" / "SY-2")`. A `gh` double answers with JSON
carrying `state` and `reviewDecision`, as `_fake_gh_says_merged` does
(`tests/test_cli.py:1700-1703`).

**Criterion 1's witness** seeds two parent tasks, an older one `ORPHANED`
and a newer one. It seeds a `READY_FOR_REVIEW` task of spec `SY-90001`
with its own `pr_url`. Its `gh` double records each URL and answers per
URL. Five passes follow.

1. The newer task is `READY_FOR_REVIEW`, and `gh` answers merged.
2. Nothing is reset, so the newer task is already `MERGED`.
3. The newer task is `APPROVED`, and `gh` answers merged.
4. The newer task is `READY_FOR_REVIEW`, and `gh` answers `CLOSED`.
5. Both tasks are `READY_FOR_REVIEW`. `gh` answers open for the older
   one and merged for the newer one.

Each pass asserts five things. `stacked_on` is `None`. The URLs asked are
exactly the parent tasks the pass left pending, in task order, which is
none in pass 2. The newer task reads `MERGED`, or `REJECTED` in pass 4.
The run added exactly one parent `Preflight`, with step `unstacked`, naming
that state. The line names neither of the other two states, from
`MERGED`, `REJECTED` and `CHANGES_REQUESTED`. After all five, the older
task reads `READY_FOR_REVIEW` and `SY-90001`'s task is unchanged.

**Criterion 2's witness** seeds two parent tasks, both
`READY_FOR_REVIEW`. It runs with `gh` returning exit 1, then `_no_gh`
(`tests/test_cli.py:1712-1713`), then answering `OPEN` with
`REVIEW_REQUIRED`. Each run stacks on the pushed head. The first two add
exactly one parent `Preflight` and the third adds none, and none is
`unstacked`. It then sets the newer task `CHANGES_REQUESTED` and runs with
exit 1 again. That run stacks on the head and adds two lines, neither
`unstacked`, and exactly one names `CHANGES_REQUESTED`.

**Criterion 3's witness** seeds one parent task, `READY_FOR_REVIEW`. It
runs twice with `gh` answering `OPEN` with `CHANGES_REQUESTED`. The first
run moves the task, and the second finds it already there. Each run
stacks on the pushed head, leaves the task `CHANGES_REQUESTED`, and adds
exactly one parent `Preflight`, not `unstacked`, naming
`CHANGES_REQUESTED`.

At the tree base each witness fails: the cell stacks after a merge, and no
new line is written.

**Wrong versions these witnesses must kill.** Each one below failed a
prototype's witnesses on 2026-09-27.

- A reconcile of the whole repo rather than the parent's tasks.
- A `spec_id` filter that matches by prefix.
- A resolver that reads the parent's rows before it reconciles.
- One `gh` line per unasked task.
- An `unstacked` line that says merged whatever the state.
- A `gh` line whenever the parent still waits.
- A resolver that falls back to an older waiting row.
- An `unstacked` line that fires for a moved parent and not for one the
  ledger already held.
- A resolver that will not stack on `CHANGES_REQUESTED`, or says nothing
  about it.
- The widened set applied without a `GhRunner` too.
- A `_run_cell` that passes no `GhRunner`, or passes `run_gh` unguarded.

**Two guards already hold the resolver.** It writes to no stream
(`tests/test_package.py:1405-1418`), so every new line goes through
`emit`. It keeps `(None, None)` or a pair together
(`saffron/task.py:159-163`).

**Queued `SA-0150` touches `saffron/task.py` too**, in `run_task`. It
depends on `SA-0182` and has not run. This spec does not depend on it.
Whichever merges second reads the other's lines. Queued `SA-0185` also
touches `saffron/task.py`, in `run_task`'s `CellSpec` build. The hunks are
separate, and the operator orders the two.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words.

**Size.** `size` is advisory here: no touched path is in `elevate_on`, and
the spec is `standard`. A prototype with all three witnesses, counted by
`size_gate`, came to 855 tokens against the `bug` ceiling of 1300.
`estimated_lines` is that count over four, with no overrun added.
