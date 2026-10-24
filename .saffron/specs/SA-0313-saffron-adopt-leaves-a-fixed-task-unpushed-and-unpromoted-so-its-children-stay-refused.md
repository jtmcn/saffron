---
id: SA-0313
title: "`saffron adopt` leaves a fixed task unpushed and unpromoted, so its children stay refused"
type: feature
priority: 2
estimated_lines: 340
touches:
  - saffron/cli.py
  - tests/test_cli.py
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
  - saffron/regate.py
  - saffron/reconcile.py
  - saffron/scheduler.py
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
  - tests/test_queued_specs.py
budget_usd: 30
max_attempts: 3
max_turns: 150
acceptance:
  - claim: >-
      For a newest task in `EXHAUSTED`, `NOT_IMPLEMENTED` or `MERGE_FAILED`,
      `saffron adopt` records the pull request's url and its head as the
      task's `pushed_sha` before it re-gates. When that re-gate records zero
      new failures on that same head, the task moves to `READY_FOR_REVIEW`
      and adopt exits 0. A child spec that `build_queue` refused before then
      becomes a candidate, both in a plain scan and in a `stack=True` scan,
      where its `stack_base` names the adopted task and its branch.
    witness: tests/test_cli.py::test_adopt_promotes_a_task_whose_regate_is_green_on_the_adopted_head
    wrong_versions:
      - "Adopt promotes on `run_regate` returning 0 and never compares the recorded re-gate's head with the adopted head."
      - "Adopt records the url but not the head, so the `stack=True` scan still refuses the child for no pushed sha."
      - "Adopt re-gates before it records the url, so the real `run_regate` would decline a task with no pull request."
      - "`MERGE_FAILED` stays out of the states adopt takes."
      - "Adopt promotes without re-gating at all."
      - "Adopt re-gates the spec's oldest task rather than its newest."
  - claim: >-
      For each of those three states, adopt keeps the task's state and exits
      0 in three cases. The re-gate records new failures on the adopted
      head, or records zero on another head, or declines and records
      nothing. The url and the head are recorded all the same. Adopt prints
      a line that names the state it kept.
    witness: tests/test_cli.py::test_adopt_keeps_the_state_of_a_task_whose_regate_is_red_declined_or_on_another_head
    wrong_versions:
      - "Adopt promotes whenever the newest re-gate row records zero new failures, whatever head it names."
      - "Adopt promotes when `run_regate` declines, reading a missing re-gate row as no new failures."
      - "Adopt exits 1 when the re-gate is red."
      - "Adopt rolls back the url and the head when the re-gate is red."
  - claim: >-
      For a newest task already in `READY_FOR_REVIEW`, adopt records the url
      and the head as its `pushed_sha`, replacing any older one. It runs no
      re-gate and exits 0. A `stack=True` scan then names that task as its
      child's `stack_base`.
    witness: tests/test_cli.py::test_adopt_of_a_ready_task_records_the_head_and_runs_no_regate
    wrong_versions:
      - "Adopt re-gates a `READY_FOR_REVIEW` task too."
      - "Adopt records the head only when the row has no `pushed_sha` yet, so an older sha stays."
      - "Adopt records the head only for the three states it re-gates."
  - claim: >-
      Adopt exits 1 and writes nothing, and runs no re-gate, in six cases.
      `gh` exits non-zero, or prints no JSON, or its JSON lacks the url, the
      head commit or the head branch. Or the head branch is not the task's
      `branch`. The line it prints names the pull request number, and for a
      branch mismatch also both branch names.
    witness: tests/test_cli.py::test_adopt_refuses_a_pull_request_gh_cannot_describe_or_whose_head_is_another_branch
    wrong_versions:
      - "Adopt records the url before it reads the head branch, so a mismatch leaves a written row."
      - "A head branch other than the task's is accepted and written over the task's `branch`."
      - "A missing head commit is recorded as an empty `pushed_sha`."
      - "`gh` printing no JSON raises out of adopt, so the command exits 2."
  - claim: >-
      For each of the three states adopt re-gates, a re-gate that raises
      makes `saffron adopt` exit 2. The task keeps its state, and the url
      and the head stay recorded.
    witness: tests/test_cli.py::test_adopt_whose_regate_raises_exits_two_with_the_pull_request_recorded
    wrong_versions:
      - "Adopt catches the raise and exits 0 as though the re-gate were red."
      - "Adopt writes nothing until the re-gate returns, so a raise leaves no url and no head."
  - claim: >-
      Folding the record rebuilds an adopted task's url and head. A
      promoted `EXHAUSTED` task folds to `READY_FOR_REVIEW`, and a
      `NOT_IMPLEMENTED` task whose re-gate was red folds to
      `NOT_IMPLEMENTED`.
    witness: tests/test_cli.py::test_an_adopted_head_and_promotion_are_facts_the_fold_keeps
    wrong_versions:
      - "The head is written with a bare `UPDATE` rather than a fact, so the fold drops it."
      - "The promotion is written with a bare `UPDATE`, so the fold rebuilds `EXHAUSTED`."
  - claim: >-
      A `NOT_IMPLEMENTED` task carrying an adopted pull request still
      moves only on a merge when `reconcile` asks about it.
    witness: tests/test_reconcile.py::test_a_not_implemented_task_with_an_adopted_pull_request_moves_only_on_a_merge
    preserves: true
---

## Context

Backlog item **b-619b7d**, with the adopt half of **b-066901**. A task
finished by hand cannot become a parent its children can run on.

**`saffron adopt` names a pull request and leaves the rest.** `_adopt`
takes a newest task in `_ADOPTABLE_STATES`, which is `EXHAUSTED`,
`NOT_IMPLEMENTED` and `READY_FOR_REVIEW` (`saffron/cli.py:2778`). Any other
state is refused by `newest["state"] not in _ADOPTABLE_STATES`
(`saffron/cli.py:2798-2803`), before any call to gh. It asks
`gh pr view <n> --repo <slug> --json url --jq .url` (`saffron/cli.py:2808-2822`).
It then calls `ledger.adopt_pull_request` (`saffron/cli.py:2828`). That
method writes one `task_package` fact carrying the row's own `state`,
`branch`, `pushed_sha`, `added` and `removed`, with the new `pr_url`
(`saffron/ledger.py:1699-1724`). So the state and the `pushed_sha` never
change. `main` dispatches `adopt` with no `out_dir` and no SIGTERM guard
(`saffron/cli.py:366-367`). `regate` gets both (`saffron/cli.py:363-364`).

**Children read the state and the pushed sha.** A plain scan admits a
child whose parent has a task in `DEPENDENCY_WAITING_STATES`
(`saffron/scheduler.py:685-686`). That set holds `READY_FOR_REVIEW` but none
of the three states above (`saffron/scheduler.py:116-124`). A `stack=True`
scan takes an outside parent as its stack base under one condition. That
parent's newest waiting row needs a branch, a resolved `pushed_sha` and a
`pr_url` (`saffron/scheduler.py:974-996`). In run 46 the adopted `SA-0302` was
`READY_FOR_REVIEW` with no pushed sha. Batch 44 refused its child `SA-0303`
for that at `saffron/scheduler.py:983-987`.

**`run_regate` judges a task's pull request head and records it.** It
declines a task with no `pr_url`, or one whose `ledger.spec_text` holds a
row (`saffron/regate.py:53-58`). It also declines a pull request that is
not open (`saffron/regate.py:71-72`). A decline prints `regate:` and its
reason and returns 1. It fetches the task's own `branch` as the head
(`saffron/regate.py:147`). It writes a `task_regate` fact with that head
and the new failure count (`saffron/regate.py:175-177`), and returns 0 only
for zero (`saffron/regate.py:182`). Anything else it raises, and the caller
exits 2. `ledger.regate(task_id)` reads the newest one back
(`saffron/ledger.py:1846-1856`).

**`MERGE_FAILED` is where a fix by hand is most often needed.** `SA-0277`
ended `MERGE_FAILED` on one test line in run 44. `adopt` refused it, so
nine tasks below it stayed refused.

## Problem

Change `_adopt` in `saffron/cli.py` so that a pull request fixed by hand
makes its task a parent.

1. **Take `MERGE_FAILED` too.** The four states are `EXHAUSTED`,
   `NOT_IMPLEMENTED`, `MERGE_FAILED` and `READY_FOR_REVIEW`. Every refusal
   that reads only the ledger stays where it is, before `gh`.
2. **Ask gh for the head as well as the url.** One `gh pr view` call
   with `--json` reads the pull request's url, head commit and head
   branch. Refuse with exit 1, writing nothing, when `gh` fails,
   prints no JSON, or leaves one of the three out or empty. Refuse the same
   way when the head branch is not the task's `branch`. The re-gate fetches
   the task's own branch, and a stack base stacks on it.
3. **Record the head, then the url.** Call `ledger.record_push` with the
   head commit, then `ledger.adopt_pull_request` with the url. The second
   carries the row's `pushed_sha`, so it now carries the head too. Both
   are facts, so a fold rebuilds them.
4. **Re-gate the three settled states.** For `EXHAUSTED`,
   `NOT_IMPLEMENTED` and `MERGE_FAILED`, call `regate.run_regate` on the
   task, the way `_regate` calls it (`saffron/cli.py:2766-2773`). Then read
   `ledger.regate(task_id)`. Promote with
   `ledger.set_task_state(task_id, "READY_FOR_REVIEW")` only when that row
   names the adopted head and zero new failures. Otherwise keep the state
   and print an `adopt:` line naming it and why.
5. **Leave `READY_FOR_REVIEW` alone.** Record the head and the url, and run
   no re-gate.
6. **Exit 0 once the url is recorded**, promoted or not. A raise from the
   re-gate reaches `main`, which exits 2. Dispatch `adopt` through
   `_guarding_sigterm` with `out_dir`, as `regate` is, since adopt now
   starts cells.

Update `_ADOPTABLE_STATES`' comment and `_adopt`'s docstring to match.

## Out of scope

- **`saffron/ledger.py`.** It is `elevate_on`, so this spec writes through
  `record_push`, `adopt_pull_request` and `set_task_state` as they stand.
  `adopt_pull_request`'s docstring says an adoption changes nothing but
  `pr_url` (`saffron/ledger.py:1700-1705`). That goes false here, and the
  delegate edits it in a review commit.
- **`reconcile` and a kept `MERGE_FAILED` task.** A row whose state is
  outside `PR_PENDING_STATES` and `MERGE_ONLY_STATES` is skipped
  (`saffron/reconcile.py:177-181`). `MERGE_FAILED` is in neither. So a
  `MERGE_FAILED` task whose re-gate was red carries a pull request that
  `reconcile` never asks about.
- **The revert exemption.** `run_regate` passes `reverify` no `exempt`
  set (b-6b06e1). A task whose PACKAGE exempted a test can come back red
  under adopt's re-gate, and then keeps its state.
- **`ready_task` and a batch whose PACKAGE raised.** `SA-0315` takes the
  rest of b-066901.
- **`DESIGN.md` and `CONTEXT.md`.** The text this change makes true lands
  by hand in this spec's own pull request.

## Notes for the agent

**New code, so no criterion declares a mutant.** The re-gate, the head and
the promotion do not exist at base, and their spelling is yours. `witness`
will report `skip` for criteria 1 to 6. Criterion 7 is `preserves` over
`reconcile`, which this spec does not edit.

**Never let a test reach the real `run_regate`.** It builds the repo's
image and starts cells. Replace `regate.run_regate` in every test that
reaches a successful adopt. A fake that writes `ledger.record_regate` on
the ledger it is handed, then returns 0 or 1, drives every case above. For
criterion 1 the fake also asserts that the row already carries the url and
the head, as the real one needs. A task that ran a recorded spec text is
declined by the real one, which criterion 2's decline case stands for.

**Four tests at base assert the old behaviour, and you edit each.**

- `test_adopt_writes_the_url_gh_names_onto_the_specs_newest_task`
  (`tests/test_cli.py:2197`) asserts `state`, `branch` and `pushed_sha`
  unchanged. Its `gh` fake answers `--jq .url` only (`tests/test_cli.py:2183-2194`).
- `test_adopt_refuses_with_exit_one_and_writes_nothing`
  (`tests/test_cli.py:2291`) holds the taken set and `len(others) == 25`.
  With `MERGE_FAILED` taken that count is 24.
- `test_an_adopted_pull_request_is_a_fact_the_fold_keeps`
  (`tests/test_cli.py:2411`) asserts `pushed_sha` unchanged.
- `test_a_merged_adopted_pull_request_admits_the_child_of_a_not_implemented_parent`
  (`tests/test_cli.py:2475`) says adopt alone changes nothing. It asserts
  no `pushed_sha` after the merge, which becomes the adopted head. Give it
  a red re-gate, so the child stays refused until the merge.

**The scans in criterion 1 need the parent's spec file.** A plain scan
reads the parent's tasks at its current `spec_sha`. Seed the parent's task
with the sha `intake.load_spec` returns for that file, as the test at
`tests/test_cli.py:2494` does. `build_queue(..., stack=True)` returns the
`StackBase` on the child's candidate (`saffron/scheduler.py:155-168`).
Before the adopt, both scans must refuse the child for each state. The
stack scan reads a pushed sha only as forty or sixty-four lowercase hex digits
(`saffron/scheduler.py:983`), so give the fake head that shape.
