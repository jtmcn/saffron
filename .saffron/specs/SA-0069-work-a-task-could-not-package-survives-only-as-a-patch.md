---
id: SA-0069
title: a task that made commits and did not package pushes nothing, so its work survives only as a patch
type: bug
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
budget_usd: 10
max_attempts: 3
max_turns: 60
risk: elevated
acceptance:
  - claim: >-
      A task that ends in any state other than `READY_FOR_REVIEW`, having made
      commits, has its work pushed to its branch, and the ledger records the
      sha that was pushed. Measured on `SA-0031`: six commits and $19.17 of
      work, a ledger row reading `pushed_sha NULL`, and a `patch.diff` in the
      batch tree that nothing will ever read again. It applied cleanly and was
      roughly 85% finished.
    witness: tests/test_package.py::test_work_a_task_could_not_package_is_pushed_to_its_branch
  - claim: >-
      No pull request is opened for it. Red gates must not reach a reviewer as a
      draft, and a pull request is a separate decision from a branch. A branch
      nobody can reach, though, is not a decision. It is a leak.
    witness: tests/test_package.py::test_pushing_unpackaged_work_opens_no_pull_request
  - claim: >-
      The task's state is left exactly as the cell ended it. An `EXHAUSTED`
      task whose work was pushed is still `EXHAUSTED`. Recording
      `READY_FOR_REVIEW` or `MERGE_FAILED` would tell the morning queue that
      PACKAGE ran.
    witness: tests/test_package.py::test_pushing_unpackaged_work_leaves_the_tasks_state_alone
  - claim: >-
      Work carrying a credential is not pushed, and the refusal is said. The
      patch and the agent's commit subjects are both channels to the remote,
      and PACKAGE already refuses on either. The same scan applies here, since
      red work is no less able to carry a leak than green work.
    witness: tests/test_package.py::test_unpackaged_work_carrying_a_credential_is_not_pushed
  - claim: >-
      A push that fails for unpackaged work is reported and changes nothing
      about how the task ended. The task already failed on its own terms. A
      transport error while salvaging it must not become an infrastructure
      exit, or `saffron cell` would report exit 2 for a task that really ended
      exit 1.
    witness: tests/test_package.py::test_a_push_that_fails_for_unpackaged_work_is_said_and_not_raised
  - claim: >-
      A task with no commits pushes nothing. With no patch there is nothing to
      salvage, and an empty branch would read as work.
    witness: tests/test_package.py::test_a_task_with_no_commits_pushes_nothing
  - claim: >-
      The line the task ends on names the branch and the sha its work was
      pushed to. The operator's only route back to the work today is knowing
      the batch tree exists. After this, it is one line of output.
    witness: tests/test_cli.py::test_an_unpackaged_task_names_the_branch_its_work_was_pushed_to
  - claim: >-
      A green cell still becomes a branch, a draft pull request and a queue
      line, exactly as it does today.
    witness: tests/test_package.py::test_a_green_cell_becomes_a_branch_a_draft_pr_and_a_queue_line
    preserves: true
  - claim: >-
      `saffron cell`'s exit code still distinguishes the terminal states. A
      pushed `EXHAUSTED` is still exit 1.
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

Teardown already exports the work. `export_patch` writes `patch.diff` and
`patch.json` into the task directory on every path, the exception path
included, precisely because "an `EXHAUSTED` run with commits is worth reading
too". What is missing is the step from a file on the host to a branch on the
remote, and PACKAGE already contains every piece of it except the decision to
take it.

**Push the work onto the tree the cell built on, not onto the default branch.**
PACKAGE applies the patch onto the fetched head of the default branch (or of
the parent, when stacked) with a three-way apply, because it is producing
something to merge. This is salvage, not packaging: the patch is relative to
`tree_base` from `patch.json`, applies there by construction, and cannot
conflict. A salvage path that can hit `MERGE_FAILED` has recreated the loss it
exists to prevent.

**The branch is `saffron/<SPEC-ID>`, the name PACKAGE uses.** A later run of
the same spec that does package leases against whatever the remote holds
(`remote_sha` is read at push time), so it replaces the salvaged branch
cleanly. Do not invent a second naming scheme.

## Out of scope

**Opening a pull request, re-verifying, rendering a body, or appending a queue
line.** Those are PACKAGE's, for work that passed. `saffron/report/**` is
forbidden for that reason.

**Rebasing salvaged work onto a moved default branch.** Whoever picks it up
does that.

**The ledger.** `record_push` already exists and writes only `pushed_sha`,
which is what this needs. `saffron/ledger.py` is forbidden. The row's `branch`
column is set when the task is created. Check that, rather than writing it
again.

**The stacking resolver.** `_resolve_stacked_on` reads `pushed_sha` only for
rows in `DEPENDENCY_WAITING_STATES`, and `EXHAUSTED` is not one. A salvaged
branch therefore does not become a parent a child will stack on. That is
correct, so leave it.

## Notes for the agent

**This spec creates new code, so its criteria carry witnesses and no mutants.**
The salvage path does not exist yet, so there is no spelling to pin. The last
two criteria name tests that already exist.

**`task.py`'s docstring on `_resolve_stacked_on` says `pushed_sha` "is written
once, by PACKAGE".** After this it is not, so correct the sentence rather than
leaving a false claim beside the code that falsified it.

**Reuse, don't copy.** The credential scans (`find_credentials`,
`find_credentials_in_text`), the squash (`commit_squash`), the lease push
(`push_with_lease`) and the worktree lifecycle (`add_worktree` /
`remove_worktree` in a `finally`) are all in `package.py`. A second copy of any
of them is a scan that can drift out of step with the one that guards the
green path. If one of them needs a parameter to serve both callers, add the
parameter.

**This spec touches `package.py`, and the gate-suite stack (PRs #200 onward)
is rewriting PACKAGE.** If an open pull request changes `package.py` when this
spec is queued, the batch scan's overlap refusal will hold it back, and that
refusal is correct. Queue it after that stack lands.
