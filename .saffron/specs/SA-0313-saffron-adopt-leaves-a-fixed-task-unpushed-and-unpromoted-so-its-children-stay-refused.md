---
id: SA-0313
title: "`saffron adopt` leaves a fixed task unpushed and out of `READY_FOR_REVIEW`, so its children stay refused"
type: feature
priority: 2
depends_on: [SA-0312]
estimated_lines: 370
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
      task's `pushed_sha`. It then re-gates that newest task, once. An empty
      `pr_url`, as PACKAGE writes it, counts as no url. When the re-gate
      records zero new failures on the adopted head, adopt moves the task to
      `READY_FOR_REVIEW` and exits 0. A child spec that `build_queue` refused
      before then becomes a candidate, both in a plain scan and in a
      `stack=True` scan, where its `stack_base` names the adopted task and
      its branch.
    witness: tests/test_cli.py::test_adopt_moves_a_task_whose_regate_is_green_on_the_adopted_head_to_ready_for_review
    wrong_versions:
      - "Adopt records the url but not the head, so the `stack=True` scan still refuses the child for no pushed sha."
      - "Adopt re-gates before it records the url, so the real `run_regate` would decline a task with no pull request."
      - "`MERGE_FAILED` stays out of the states adopt takes."
      - "Adopt moves the task to `READY_FOR_REVIEW` without re-gating at all."
      - "Adopt re-gates the spec's oldest task rather than its newest."
      - "Adopt treats an empty `pr_url` as a url, so it refuses a row PACKAGE wrote."
  - claim: >-
      For each of those three states, adopt keeps the task's state and exits
      0 in three cases. The re-gate records new failures on the adopted
      head and returns 1. Or it records zero new failures on another head
      and returns 0. Or it declines, records nothing and returns 1, for a
      task that holds no re-gate row. The url
      and the head are recorded all the same, and adopt prints a line that
      names the state it kept. Run again on the same pull request after a
      red re-gate, adopt records the new head, re-gates again, and on a
      green re-gate moves the task to `READY_FOR_REVIEW`.
    witness: tests/test_cli.py::test_adopt_keeps_the_state_of_a_task_whose_regate_is_red_declined_or_on_another_head
    wrong_versions:
      - "Adopt moves the task on `run_regate` returning 0 and never compares the recorded re-gate's head with the adopted head."
      - "Adopt moves the task whenever the newest re-gate row records zero new failures, whatever head it names."
      - "Adopt moves the task when `run_regate` declines, reading a missing re-gate row as no new failures."
      - "Adopt exits 1 when the re-gate is red."
      - "Adopt rolls back the url and the head when the re-gate is red."
      - "Adopt still refuses a task that carries a url, so the second run on the same pull request exits 1."
  - claim: >-
      For a newest task already in `READY_FOR_REVIEW`, adopt records the url,
      runs no re-gate and exits 0. A row with no resolved `pushed_sha` takes
      the head as its `pushed_sha`, and a `stack=True` scan then names that
      task as its child's `stack_base`. A row with a resolved `pushed_sha`
      keeps it.
    witness: tests/test_cli.py::test_adopt_of_a_ready_task_records_the_url_and_runs_no_regate
    wrong_versions:
      - "Adopt re-gates a `READY_FOR_REVIEW` task too."
      - "Adopt replaces a resolved `pushed_sha` with the head."
      - "Adopt records the head only for the three states it re-gates."
  - claim: >-
      Adopt exits 1 and writes nothing, and runs no re-gate, in seven cases.
      `gh` exits non-zero, or prints no JSON, or its JSON lacks the url, the
      head commit or the head branch. Or the head branch is not the task's
      `branch`. Or the task already carries a url other than the one `gh`
      names. The line it prints names the pull request number. For a branch
      mismatch it also names both branches, and for a url mismatch both urls.
    witness: tests/test_cli.py::test_adopt_refuses_a_pull_request_gh_cannot_describe_or_whose_head_is_another_branch
    wrong_versions:
      - "Adopt records the url before it reads the head branch, so a mismatch leaves a written row."
      - "A head branch other than the task's is accepted and written over the task's `branch`."
      - "A missing head commit is recorded as an empty `pushed_sha`."
      - "`gh` printing no JSON raises out of adopt, so the command exits 2."
      - "A task carrying another url is accepted, and the new url replaces the old one."
  - claim: >-
      For each of the three states adopt re-gates, a re-gate that raises
      makes `saffron adopt` exit 2. The task keeps its state, and the url
      and the head stay recorded.
    witness: tests/test_cli.py::test_adopt_whose_regate_raises_exits_two_with_the_pull_request_recorded
    wrong_versions:
      - "Adopt catches the raise and exits 0 as though the re-gate were red."
      - "Adopt writes nothing until the re-gate returns, so a raise leaves no url and no head."
  - claim: >-
      Folding the record rebuilds an adopted task's url and head. An
      `EXHAUSTED` task adopt moved to `READY_FOR_REVIEW` folds to
      `READY_FOR_REVIEW`, and a `NOT_IMPLEMENTED` task whose re-gate was red
      folds to `NOT_IMPLEMENTED`.
    witness: tests/test_cli.py::test_an_adopted_head_and_state_move_are_facts_the_fold_keeps
    wrong_versions:
      - "The head is written with a bare `UPDATE` rather than a fact, so the fold drops it."
      - "The state move is written with a bare `UPDATE`, so the fold rebuilds `EXHAUSTED`."
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
(`saffron/cli.py:2798-2803`), before any call to gh. So is a task whose
`pr_url` is set (`saffron/cli.py:2804-2806`). It asks
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
3. **Run again on the same pull request.** A task that already carries a
   `pr_url` is no longer refused before gh. When that url equals the one
   gh names, adopt runs the steps below again. Any other url refuses with
   exit 1, writing nothing. A re-gate that came back red, declined or
   raised can then be retried.
4. **Record the head, then the url.** Except as step 6 says, call
   `ledger.record_push` with the head commit, then `ledger.adopt_pull_request` with the url. The second
   carries the row's `pushed_sha`, so it now carries the head too. Both
   are facts, so a fold rebuilds them.
5. **Re-gate the three settled states.** For `EXHAUSTED`,
   `NOT_IMPLEMENTED` and `MERGE_FAILED`, call `regate.run_regate` on the
   task, the way `_regate` calls it (`saffron/cli.py:2766-2773`). Then read
   `ledger.regate(task_id)`. Call
   `ledger.set_task_state(task_id, "READY_FOR_REVIEW")` only when
   `run_regate` returned 0 and that row names the adopted head and zero new
   failures. Otherwise keep the state and print an `adopt:` line naming it
   and why.
6. **Leave `READY_FOR_REVIEW` alone.** Record the url and run no re-gate.
   Record the head only when the row's `pushed_sha` is not resolved, as
   `_RESOLVED_SHA` reads it (`saffron/scheduler.py:983`). A resolved one is
   PACKAGE's own commit, and it stays.
7. **Exit 0 once the url is recorded**, whether the state moved or not. A raise from the
   re-gate reaches `main`, which exits 2. Dispatch `adopt` through
   `_guarding_sigterm` with `out_dir`, as `regate` is, since adopt now
   starts cells.

Update `_ADOPTABLE_STATES`' comment, `_adopt`'s docstring and the `adopt`
help string (`saffron/cli.py:195-197`) to match.

## Out of scope

- **`saffron/ledger.py`.** It is `elevate_on`, so this spec writes through
  `record_push`, `adopt_pull_request` and `set_task_state` as they stand.
  `adopt_pull_request`'s docstring says an adoption changes nothing but
  `pr_url` (`saffron/ledger.py:1700-1705`). `set_task_package`'s says a
  `MERGE_FAILED` task reaches the operator with no pull request
  (`saffron/ledger.py:1679-1681`). Both go false here, and the delegate
  edits them in a review commit.
- **`reconcile` and a kept `MERGE_FAILED` task.** A row whose state is
  outside `PR_PENDING_STATES` and `MERGE_ONLY_STATES` is skipped
  (`saffron/reconcile.py:177-181`). `MERGE_FAILED` is in neither. So a
  `MERGE_FAILED` task whose re-gate was red carries a pull request that
  `reconcile` never asks about.
- **The revert exemption.** `run_regate` passes `reverify` no `exempt`
  set (b-6b06e1). A task whose PACKAGE exempted a test can come back red
  under adopt's re-gate, and then keeps its state.
- **A task whose spec text was recorded.** `run_regate` declines a task
  whose `ledger.spec_text` holds a row (`saffron/regate.py:55-58`). A stack
  batch records one for each spec revision (`saffron/batch.py:835-841`).
  Adopt's re-gate declines such a task, and it keeps its state. This is a
  known limit, and `saffron/regate.py` stays forbidden.
- **`ready_task` and a batch whose PACKAGE raised.** `SA-0315` takes the
  rest of b-066901.
- **`DESIGN.md` and `CONTEXT.md`.** The text this change makes true lands
  by hand in this spec's own pull request.

## Notes for the agent

**New code, so no criterion declares a mutant.** None of the re-gate, the
head or the state move exists at base. Their spelling is yours. `witness`
will report `skip` for criteria 1 to 6. Criterion 7 is `preserves` over
`reconcile`, which this spec does not edit.

**Never let a test reach the real `run_regate`.** It builds the repo's
image and starts cells. Replace `regate.run_regate` in every test that
reaches a successful adopt. A fake that writes `ledger.record_regate` on
the ledger it is handed drives every case above. Return what the real one
would (`saffron/regate.py:182`): 0 for zero new failures, else 1, and 1
for a decline that records nothing. Criterion 2's other-head fake records
zero new failures on another head and returns 0. Give each decline case
a fresh task that holds no re-gate row.

**Criterion 1's fake records each call.** The witness asserts one call,
with the newest task's id. It also asserts that `ledger.regate` names the
adopted head. The fake also asserts that the row
already carries the url, which the real one needs (`saffron/regate.py:53-54`).
Give each parent an older task of the same spec and `spec_sha`, in
`REJECTED` with no url. It keeps both scans refusing before the adopt
(`saffron/scheduler.py:688-693`). PACKAGE's result defaults to
`pr_url: str = ""` (`saffron/phases/package.py:591`). So seed the two
parents PACKAGE writes through `ledger.set_task_package` with that empty
url, as `tests/test_cli.py:2238-2246` does.

**Why a resolved `pushed_sha` stays on a `READY_FOR_REVIEW` task.** The end
review reads a layer's `pushed_sha` as PACKAGE's one squashed commit
(`saffron/end_review.py:147`, `saffron/end_review.py:212`). The finish
labels the critic's findings with it (`saffron/finish.py:276-280`). Review
commits on top would cut that diff to its last commit. Criterion 3 seeds a
`READY_FOR_REVIEW` task with a resolved sha and asserts it is kept. A
second task has none and takes the head.

**A stored url can differ in form from what `gh pr view` prints.** PACKAGE
stores `gh pr create`'s last line (`saffron/phases/package.py:440-441`).
Such a difference makes adopt refuse with exit 1, which is safe.

**Move the state on both signals.** `ledger.regate` returns the task's
newest re-gate row, whoever wrote it (`saffron/ledger.py:1846-1856`). So
move the task only when `run_regate` returned 0 and that row names the
adopted head with zero new failures.

**Read the branch from the right method.** `ledger.tasks_by_repo` selects
`state`, `pr_url` and `pushed_sha` but no branch
(`saffron/ledger.py:1147-1148`). `ledger.tasks_by_spec_id`
does (`saffron/ledger.py:1183-1184`).

**A fork's pull request can name a branch of the same name.** The re-gate
fetches that branch from origin (`saffron/regate.py:147`). It then judges
or fails on origin's branch, and a failed fetch raises, so adopt exits 2.

**Four tests at base assert the old behaviour, and you edit each.**

- `test_adopt_writes_the_url_gh_names_onto_the_specs_newest_task`
  (`tests/test_cli.py:2622`) asserts `state`, `branch` and `pushed_sha`
  unchanged. Its `gh` fake answers `--jq .url` only (`tests/test_cli.py:2608-2619`).
- `test_adopt_refuses_with_exit_one_and_writes_nothing`
  (`tests/test_cli.py:2716`) holds the taken set and `len(others) == 25`.
  With `MERGE_FAILED` taken that count is 24. Its tasks that carry a url
  are refused before gh at base, and it asserts no gh call. Now gh is
  asked, and a different url refuses.
- `test_an_adopted_pull_request_is_a_fact_the_fold_keeps`
  (`tests/test_cli.py:2836`) asserts `pushed_sha` unchanged.
- `test_a_merged_adopted_pull_request_admits_the_child_of_a_not_implemented_parent`
  (`tests/test_cli.py:2900`) says adopt alone changes nothing. It asserts
  no `pushed_sha` after the merge, which becomes the adopted head. Give it
  a red re-gate, so the child stays refused until the merge.

**The scans in criterion 1 need the parent's spec file.** A plain scan
reads the parent's tasks at its current `spec_sha`. Seed the parent's task
with the sha `intake.load_spec` returns for that file, as the test at
`tests/test_cli.py:2919` does. `build_queue(..., stack=True)` returns the
`StackBase` on the child's candidate (`saffron/scheduler.py:156-170`).
Before the adopt, both scans must refuse the child for each state. The
stack scan reads a pushed sha only as forty or sixty-four lowercase hex digits
(`saffron/scheduler.py:983`), so give the fake head that shape.
