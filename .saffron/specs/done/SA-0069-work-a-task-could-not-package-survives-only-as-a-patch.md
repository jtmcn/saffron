---
id: SA-0069
title: a task that made commits and did not package pushes nothing, so its work survives only as a patch
type: feature
priority: 1
depends_on: []
touches:
  - saffron/task.py
  - saffron/phases/package.py
  - tests/test_package.py
  - tests/test_cli.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/agents/**
  - saffron/phases/implement.py
  - saffron/phases/review.py
  - saffron/phases/rebut.py
  - saffron/report/**
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/reconcile.py
  - saffron/batch.py
  - saffron/cli.py
  - saffron/replay.py
budget_usd: 12
max_attempts: 3
max_turns: 80
risk: elevated
acceptance:
  - claim: >-
      A task whose cell ended in a state other than `READY_FOR_REVIEW`, so that
      PACKAGE never ran, and which made commits, has its work pushed to its
      branch, and the ledger records the sha that was pushed. Measured on
      `SA-0031`: six commits and $19.17 of work, a ledger row reading
      `pushed_sha NULL`, and a `patch.diff` in the batch tree that nothing will
      ever read again. It applied cleanly and was roughly 85% finished.
    witness: tests/test_package.py::test_work_a_task_could_not_package_is_pushed_to_its_branch
  - claim: >-
      Its work is pushed to its branch, and no pull request is opened for it.
      Red gates must not reach a reviewer as a draft, and a pull request is a
      separate decision from a branch. A branch nobody can reach, though, is
      not a decision. It is a leak. The witness asserts both the branch on the
      remote and that `gh` was never called.
    witness: tests/test_package.py::test_pushing_unpackaged_work_opens_no_pull_request
  - claim: >-
      An `EXHAUSTED` task whose work was pushed is still `EXHAUSTED`. Recording
      `READY_FOR_REVIEW` or `MERGE_FAILED` would tell the morning queue that
      PACKAGE ran. The witness asserts both the push and the state.
    witness: tests/test_package.py::test_pushing_unpackaged_work_leaves_the_tasks_state_alone
  - claim: >-
      Unpackaged work never replaces a branch someone else moved. It is pushed
      only where the remote branch is absent, or holds a sha that one of this
      spec's own ledger rows recorded as pushed. Otherwise nothing is pushed and
      the line says why. Without this, a spec whose pull request is open with
      the operator's review fixes on it, edited and re-run through `saffron
      cell`, would replace that reviewed branch with red, unreviewed work.
    witness: tests/test_package.py::test_unpackaged_work_does_not_replace_a_branch_someone_else_moved
  - claim: >-
      Work carrying a credential is not pushed, and the refusal is said. The
      patch and the agent's commit subjects are both channels to the remote,
      and PACKAGE already refuses on either. The same scan applies here, since
      red work is no less able to carry a leak than green work.
    witness: tests/test_package.py::test_unpackaged_work_carrying_a_credential_is_not_pushed
  - claim: >-
      Any failure while pushing unpackaged work is reported and changes nothing
      about how the task ended: reading the remote, applying the patch,
      committing or pushing. The task already failed on its own terms, and a
      failure while pushing its work must not become an infrastructure exit. The
      witness makes applying fail, not only the push.
    witness: tests/test_package.py::test_a_failure_pushing_unpackaged_work_is_said_and_not_raised
  - claim: >-
      A task with no commits pushes nothing, and the line it ends on says there
      was nothing to push. With no patch there is nothing to push, and an empty
      branch would read as work.
    witness: tests/test_package.py::test_a_task_with_no_commits_pushes_nothing
  - claim: >-
      The line the task ends on names the branch and the sha its work was
      pushed to, and `saffron cell` still exits 1 for it, as it does for a push
      that failed. The operator's only route back to the work today is knowing
      the batch tree exists. After this, it is one line of output.
    witness: tests/test_cli.py::test_an_unpackaged_task_names_the_branch_its_work_was_pushed_to
  - claim: >-
      A green cell still becomes a branch, a draft pull request and a queue
      line, exactly as it does today.
    witness: tests/test_package.py::test_a_green_cell_becomes_a_branch_a_draft_pr_and_a_queue_line
    preserves: true
  - claim: >-
      `saffron cell`'s exit code still distinguishes the terminal states.
    witness: tests/test_cli.py::test_the_exit_code_distinguishes_the_terminal_states
    preserves: true
---

## Context

`docs/BACKLOG.md` item **45**. `SA-0028` closed the door where an implement
turn dies on its ceiling with *nothing* committed. This is the door beside it:
commits exist, the gates are red or the run stopped, and PACKAGE never runs,
because `task.run_task` calls `package()` only on `READY_FOR_REVIEW`. So
nothing is pushed and there is no pull request. The spec loop's own gotchas
record the same thing from the other side. A rate limit that landed during
REBUT, after four commits and green gates, left "no branch and no pull
request, and the re-run starts over."

The split design (`docs/superpowers/specs/2026-09-01-splitting-a-too-wide-spec-design.md`)
needs this independently. Its mid-flight split hands child 1 the parent's
branch, and today there is no branch to hand.

## Problem

Teardown already exports the work. Whenever the cell was created and the diff
is not empty, `export_patch` writes `patch.diff`, and `patch.json` with
`tree_base`, into the task directory, precisely because "an `EXHAUSTED` run with
commits is worth reading too". `run_one_cell` then carries `cell_head_sha` and
`agent_subjects` on the outcome. What is missing is the step from a file on the
host to a branch on the remote, and PACKAGE already contains every piece of it
except the decision to take it.

**Push the work onto the tree the cell built on, not onto the default branch.**
PACKAGE applies the patch onto the fetched head of the default branch (or of
the parent, when stacked) with a three-way apply, because it is producing
something to merge. Pushing unpackaged work is not packaging: the patch is
relative to `tree_base` from `patch.json`, applies there by construction, and
cannot conflict. A path that can hit `MERGE_FAILED` has recreated the loss it
exists to prevent.

**The branch is `saffron/<SPEC-ID>`, the name PACKAGE uses.** Do not invent a
second naming scheme. `push_with_lease`'s lease reads whatever the remote holds
at push time, so on its own it would replace anything there. That is why the
fourth criterion checks the remote head against this spec's own recorded
pushes (`Ledger.tasks_by_spec_id`) first.

## Out of scope

**Opening a pull request, re-verifying, rendering a body, or appending a queue
line.** Those are PACKAGE's, for work that passed. `saffron/report/**` is
forbidden for that reason.

**A task PACKAGE already handled.** `run_task` overwrites `outcome.state` with
the packaging result, so a `MERGE_FAILED` from PACKAGE is not a state the cell
ended in. Decide from the cell's own state, before packaging, or you will push
over the very branch PACKAGE refused to overwrite.

**A cell that raised.** Ctrl-C, SIGTERM and a `CellSessionError` all leave the
task `ORPHANED` and re-raise out of `run_one_cell`, so `run_task` never sees an
outcome. Their patch stays in the batch tree. Do not catch `BaseException` in
`run_task` to reach it: that would push to a remote in the middle of a SIGTERM.

**Rebasing pushed work onto a moved default branch.** Whoever picks it up does
that.

**The ledger.** `record_push` already exists and writes only `pushed_sha`,
which is what this needs. `saffron/ledger.py` is forbidden. The row's `branch`
column is set when the task is created. Check that, rather than writing it
again.

**The stacking resolver.** `_resolve_stacked_on` reads `pushed_sha` only for
rows in `DEPENDENCY_WAITING_STATES`, and `EXHAUSTED` is not one. So a branch
pushed this way does not become a parent a child will stack on. That is
correct, so leave it.

## Notes for the agent

**This spec creates new code, so its criteria carry witnesses and no mutants.**
The path that pushes unpackaged work does not exist yet, so there is no spelling
to pin. The last two criteria name tests that already exist.

**Every new witness must fail with `task.py` and `package.py` reverted, not
merely be missing at base.** The `revert` gate re-runs each new witness against
the reverted source and blocks any that still pass. Base code pushes nothing,
opens no pull request and leaves the state alone, so a test asserting only one
of those passes reverted. That is why criteria 2, 3 and 7 each pair the absence
with something only the new path produces. Import new names inside tests, not
at module scope. A module-scope import of a name you add makes the reverted run
a collection error, which `revert` reads as `skip`, and then it checks nothing.

**Do not call it salvage.** "Salvage" already names `SA-0028`'s IMPLEMENT turn:
the `SALVAGE:` line, `cut_off_salvage_failed` and `SALVAGE_MAX_TURNS`. Say
"push unpackaged work".

**Check that `patch.diff` exists before reading the remote.** Several
`tests/test_cli.py` tests drive `run_task` to `EXHAUSTED` with no patch and a
fake remote URL. Reading the remote first would reach the network from a unit
test.

**Catch what can actually fail.** `real_remote`, `apply_patch`, `commit_squash`,
`remote_sha` and `push_with_lease` raise `PackageError`. `add_worktree` raises
`mirror_ops.GitError`, which is not a `PackageError`. `apply_patch` raises on
any binary file, because `DIFF_FLAGS` carries no `--binary`. Anything that
escapes `run_task` reaches `cli.main`'s catch-all and exits 2.

**Say what the commit is.** `commit_squash` renders the same message a packaged
commit gets. Give it a way to say the task's state and that the gates were not
green, so nobody reading the branch mistakes it for packaged work. Adding a
parameter is fine; a second copy of the function is not.

**Reuse, don't copy.** The credential scans (`find_credentials`,
`find_credentials_in_text`), the squash (`commit_squash`), the lease push
(`push_with_lease`) and the worktree lifecycle (`add_worktree` /
`remove_worktree` in a `finally`) are all in `package.py`. A second copy of any
of them is a scan that can drift out of step with the one that guards the
green path.

**Keep the state word in the ending line.** It stays `f"{spec.id:<10} {state}"`
followed by what was pushed. The spec loop's watch pattern matches the state
word on that line. The line is a `print`, so it does not reach `events.jsonl`.
`events.py` is outside `touches`, and that is accepted.

**Stale sentences in `touches`.** `task.py`'s docstring on `_resolve_stacked_on`
and a docstring in `tests/test_cli.py` both say `pushed_sha` is "written once,
by PACKAGE". Correct both. `DESIGN.md` §5.7 says the same, and that one is
filed by hand on backlog item 45.

**Queue it after the gate-suite stack lands.** That stack (PRs #200 onward)
rewrites PACKAGE and will likely touch `tests/test_package.py`. `SA-0066` and
`SA-0067` also edit `tests/test_cli.py`. If any of their pull requests is open
when a night is scanned, the overlap refusal holds this spec back, and that is
correct.
