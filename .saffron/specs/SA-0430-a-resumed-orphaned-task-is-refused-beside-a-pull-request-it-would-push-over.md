---
id: SA-0430
title: "The queue resumes an `ORPHANED` task beside a pull request a green cell would push over"
type: bug
priority: 2
estimated_lines: 198
estimate_measured: true
touches:
  - saffron/scheduler.py
  - tests/test_scheduler.py
  - tests/test_refusal_count.py
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
  - saffron/reconcile.py
  - saffron/regate.py
  - saffron/phases/**
  - saffron/record/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/repos/**
  - tests/test_cli.py
  - tests/test_adopt_stack_layer.py
  - tests/test_ledger_fold_task.py
  - tests/test_session.py
  - tests/test_batch.py
  - tests/test_task.py
  - tests/test_queued_specs.py
budget_usd: 32
max_attempts: 3
max_turns: 130
risk: standard
acceptance:
  - claim: >-
      When the newest re-queueing task at a spec's `spec_sha` is `ORPHANED`
      and its row carries a `pr_url`, `build_queue` does not resume it. It
      refuses the spec as `open_pr_on_spec`, and the reason names that url
      and does not say "another task". The same row resumes before the url
      is set. The witness sets the url two ways, through
      `adopt_pull_request` and through a `set_task_package` write followed
      by a return to `ORPHANED`. It reads the plain scan and the
      `stack=True` scan, each with no `repo_slug` and with a `gh` listing no
      pull request. A newer re-queueing row in another state above the
      url-carrying one still resumes, and a newest `ORPHANED` row with a url
      above it refuses again. A `CHANGES_REQUESTED` row carrying its own url
      still resumes.
    witness: tests/test_scheduler.py::test_an_orphaned_task_carrying_a_pull_request_url_is_refused_not_resumed
    wrong_versions:
      - "Any re-queueing row with a url refuses its spec, `CHANGES_REQUESTED` included."
      - "The check reads the oldest re-queueing row at the `spec_sha` rather than the one the scan resumes."
      - "Any `ORPHANED` row with a url at the `spec_sha` refuses the spec, even under a newer row in another re-queue state."
      - "The url check is made only when a `repo_slug` is passed."
      - "The refusal is added to the plain scan only, so a `stack=True` scan still resumes the task."
      - "The refusal is added to the `stack=True` scan only."
      - "The refusal reuses the same-spec check's reason, which says the pull request is from another task."
      - "The refusal is filed under `open_pr_overlap` rather than `open_pr_on_spec`."
      - "The url counts only on a row with no `pushed_sha`, so a row PACKAGE wrote is resumed."
      - "The url counts only on a row that holds a `pushed_sha`, so a row adopt wrote with no push is resumed."
    covers:
      - set: the writes that put a url on an `ORPHANED` row
        members:
          - member: "`Ledger.adopt_pull_request`"
            driven_by: "The url counts only on a row that holds a `pushed_sha`, so a row adopt wrote with no push is resumed."
          - member: "`Ledger.set_task_package`, then `set_task_state` back to `ORPHANED`"
            driven_by: "The url counts only on a row with no `pushed_sha`, so a row PACKAGE wrote is resumed."
      - set: the scans
        members:
          - member: the plain `build_queue` scan
            driven_by: "The refusal is added to the `stack=True` scan only."
          - member: a `stack=True` `build_queue` scan
            driven_by: "The refusal is added to the plain scan only, so a `stack=True` scan still resumes the task."
      - set: the `gh` arrangements
        members:
          - member: no `repo_slug`, so no `gh` call
            driven_by: "The url check is made only when a `repo_slug` is passed."
          - member: a `repo_slug` with a `gh` listing no pull request
            driven_by: tests/test_scheduler.py::test_an_orphaned_task_carrying_a_pull_request_url_is_refused_not_resumed
      - set: the row orders at one `spec_sha`
        members:
          - member: one `ORPHANED` row
            driven_by: tests/test_scheduler.py::test_an_orphaned_task_carrying_a_pull_request_url_is_refused_not_resumed
          - member: a newer `GATE_ERROR` row above the url-carrying `ORPHANED` row
            driven_by: "Any `ORPHANED` row with a url at the `spec_sha` refuses the spec, even under a newer row in another re-queue state."
          - member: a newest url-carrying `ORPHANED` row above both
            driven_by: "The check reads the oldest re-queueing row at the `spec_sha` rather than the one the scan resumes."
      - set: the re-queue states carrying a url
        members:
          - member: "`ORPHANED`"
            driven_by: tests/test_scheduler.py::test_an_orphaned_task_carrying_a_pull_request_url_is_refused_not_resumed
          - member: "`CHANGES_REQUESTED`, the control"
            driven_by: "Any re-queueing row with a url refuses its spec, `CHANGES_REQUESTED` included."
    positive_case: >-
      The same witness reads each `ORPHANED` row resumed on its own
      `task_id` by both scans before its url is set, and the
      `CHANGES_REQUESTED` control resumed by both scans after, so the
      refusals it reads come from scans that resume.
  - claim: >-
      When the newest re-queueing task is `ORPHANED` with no `pr_url`,
      `build_queue` refuses the spec as `open_pr_on_spec` if `gh` lists an
      open pull request on the task's own branch whose head is a non-empty
      sha other than the row's `pushed_sha`. The reason names that pull
      request's url and does not say "another task". The scan asks `gh` for
      each pull request's head. The witness drives a row with no push, the
      shape spec loop session 84 met, and the same row after a push. The task still resumes
      beside a pull request at its own pushed head, one on another branch,
      one with no head field, and one with an empty head. After the row
      moves to `CHANGES_REQUESTED`, a pull request at another head no longer
      refuses it. Both scans read each case.
    witness: tests/test_scheduler.py::test_an_orphaned_task_beside_another_head_on_its_branch_is_refused_not_resumed
    wrong_versions:
      - "The scan never asks `gh` for the head field, so no listed pull request carries one."
      - "Any open pull request on the task's branch refuses it, whatever its head."
      - "A pull request with no head field, or an empty one, refuses the task because it differs from the row's `pushed_sha`."
      - "An open pull request on any branch with another head refuses the task."
      - "Only a row with a `pushed_sha` is compared, so an unpushed row resumes."
      - "The head check covers every re-queue state, `CHANGES_REQUESTED` included."
      - "The head check is added to the plain scan only."
    covers:
      - set: the row's push
        members:
          - member: no push (the `SA-0423` row of spec loop session 84)
            driven_by: "Only a row with a `pushed_sha` is compared, so an unpushed row resumes."
          - member: a recorded push
            driven_by: tests/test_scheduler.py::test_an_orphaned_task_beside_another_head_on_its_branch_is_refused_not_resumed
      - set: the open pull requests `gh` lists
        members:
          - member: own branch, another head
            driven_by: "The scan never asks `gh` for the head field, so no listed pull request carries one."
          - member: own branch, the row's pushed head
            driven_by: "Any open pull request on the task's branch refuses it, whatever its head."
          - member: another branch, another head
            driven_by: "An open pull request on any branch with another head refuses the task."
          - member: own branch, no head field
            driven_by: "A pull request with no head field, or an empty one, refuses the task because it differs from the row's `pushed_sha`."
          - member: own branch, an empty head
            driven_by: "A pull request with no head field, or an empty one, refuses the task because it differs from the row's `pushed_sha`."
      - set: the re-queue states
        members:
          - member: "`ORPHANED`"
            driven_by: tests/test_scheduler.py::test_an_orphaned_task_beside_another_head_on_its_branch_is_refused_not_resumed
          - member: "`CHANGES_REQUESTED`, the control"
            driven_by: "The head check covers every re-queue state, `CHANGES_REQUESTED` included."
      - set: the scans
        members:
          - member: the plain `build_queue` scan
            driven_by: tests/test_scheduler.py::test_an_orphaned_task_beside_another_head_on_its_branch_is_refused_not_resumed
          - member: a `stack=True` `build_queue` scan
            driven_by: "The head check is added to the plain scan only."
    positive_case: >-
      The same witness reads the task resumed on its own `task_id` by both
      scans beside a pull request at its own pushed head, so the refusal it
      reads at another head comes from a scan that sees the pull request
      and resumes past one it owns.
  - claim: >-
      A `CHANGES_REQUESTED` task still resumes beside its own open pull
      request.
    witness: tests/test_scheduler.py::test_resuming_its_own_task_is_not_refused_by_its_own_open_pr
    preserves: true
  - claim: >-
      An open pull request on a spec's branch still refuses a candidate with
      no task to resume, naming another task.
    witness: tests/test_scheduler.py::test_an_open_pr_from_another_task_refuses
    preserves: true
    positive_case: >-
      The same test reads one refusal naming the pull request's url, so the
      empty candidate list comes from a scan that read the pull request.
  - claim: >-
      Of several re-queueing tasks with no url, the newest is still the one
      resumed.
    witness: tests/test_scheduler.py::test_the_newest_send_back_is_the_one_resumed
    preserves: true
    positive_case: >-
      The same test reads the newest task's id as the one candidate, so the
      scan it reads resumes a task.
---

## Context

Backlog item **b-f7db70**. `SA-0429`'s writer found it in spec loop
session 85. The item asks that the queue stop resuming an `ORPHANED` task that
carries a pull request.

**The queue resumes every `ORPHANED` task.** `ORPHANED` is in
`REQUEUE_STATES` (`saffron/scheduler.py:164-173`). `build_queue` takes the
newest re-queueing row at the spec's `spec_sha` as the task to resume
(`saffron/scheduler.py:1348-1350`). It reads rows from `tasks_by_spec`,
which selects `task_id`, `spec_id`, `spec_sha` and `state` alone
(`saffron/ledger.py:1282-1289`).

**Gate 0 exempts any resume from the pull request on its branch.**
`open_pr_refusal` refuses on it only for `candidate.task_id is None`
(`saffron/scheduler.py:910-927`). Its `ponytail:` names the ceiling: "is a
resume" stands in for "owns that PR", and the owner needs the ledger
(`saffron/scheduler.py:916-919`). `_open_prs` asks `gh` for
`number,headRefName,url,files` and no head
(`saffron/scheduler.py:343-357`).

**A green resumed cell then pushes over a by-hand head.** PACKAGE reads the
remote head as its lease and pushes (`saffron/phases/package.py:970-975`).
`open_draft_pr` finds the pull request already on the branch and returns it
to draft (`saffron/phases/package.py:459-470`). Spec loop session 84 opened `#1305` by hand
on `saffron/SA-0423` for an `ORPHANED` task that pushed nothing. The home
ledger's row for it, task 471, carries no `pr_url` and no `pushed_sha`.

**Two writes put a url on an `ORPHANED` row.** `adopt_pull_request` writes
the url and keeps the row's state (`saffron/ledger.py:1889-1915`). `SA-0429`
adds `ORPHANED` to the states adopt takes, and a red re-gate keeps it
`ORPHANED` with the url. A `task_package` fact sets `pr_url` beside the
state (`saffron/ledger.py:1004-1018`), and a later `task_state` fact leaves
it (`saffron/ledger.py:993-999`). So a `CHANGES_REQUESTED` task whose
resumed cell dies keeps its own url. The home ledger holds 60 `ORPHANED`
rows and none carries a url.

**The ledger already serves both fields.** `tasks_by_repo` selects `pr_url`
and `pushed_sha` for every task (`saffron/ledger.py:1295-1312`).
`build_queue` reads it already for `SA-0131`'s admission
(`saffron/scheduler.py:1376`).

## Problem

1. **Refuse a url-carrying `ORPHANED` resume.** Take the row
   `build_queue` would resume. An `ORPHANED` one with a `pr_url` refuses
   the spec as `open_pr_on_spec`, and the reason names the url. It is not another task's
   pull request, so the reason must not say so. This half reads the ledger
   alone and refuses with or without a `repo_slug`.
2. **Refuse one beside another head on its branch.** Refuse such a row
   with no `pr_url` too, for an open pull request on `_branch(spec.id)`.
   Its head must be a non-empty sha other than the row's `pushed_sha`. A row with no push differs from any such head. Add the
   head field to `_open_prs`'s `--json` list for this. A pull request that
   reports no head, or an empty one, refuses nothing. That keeps
   `_open_prs`'s best-effort reading (`saffron/scheduler.py:326-340`).
3. **Leave every other resume as it is.** A `CHANGES_REQUESTED` task keeps
   the exemption `open_pr_refusal` gives it. So does every other re-queue
   state, and an `ORPHANED` row beside a pull request at its own pushed
   head. Leave `open_pr_refusal`'s signature as it is, since
   `saffron/batch.py:477` and `saffron/batch.py:717` call it.
4. **Keep the site count honest.** `tests/test_refusal_count.py:39` pins one
   `open_pr_on_spec` site in `scheduler.py`. A new `return` of that kind is
   a second site. Raise the pin to what `_sites()` then counts, with a
   one-line comment naming both.

## Out of scope

- **`SA-0429`'s criterion 1 for a kept `ORPHANED` task.** It says the
  plain scan offers an adopted `ORPHANED` parent again. So does its note
  "The witness reads each kept shape's own refusal". Criterion 1 here refuses that
  parent. Measured with both prototypes applied, `SA-0429`'s witness fails at
  `('orphaned', 'red', False)`. The operator orders the two specs and
  amends `SA-0429`. `tests/test_cli.py` stays forbidden here.
- **An older url-carrying `ORPHANED` row under a newer re-queueing row.**
  The scan resumes the newer row, as at base. Its green cell pushes to the
  same branch. Gate 0's `ponytail:` keeps that ceiling.
- **A by-hand pull request at the row's own pushed head.** It resumes, as
  at base. Its head is the task's own work, and PACKAGE's lease still pushes
  over it.
- **A url on a row whose pull request has since closed or merged.**
  `reconcile` skips a url on a row outside two sets
  (`saffron/reconcile.py:180-183`). `ORPHANED` is in neither
  `PR_PENDING_STATES` nor `MERGE_ONLY_STATES`. Such a spec stays refused until it is retired.
- **A revision whose cell died.** A `CHANGES_REQUESTED` task resumed and
  then cut to `ORPHANED` keeps its own url, so criterion 1 refuses it. Only `task_package` writes `pr_url` (`saffron/ledger.py:1005`). At
  this base `saffron adopt` refuses `ORPHANED`
  (`saffron/cli.py:3171-3173`). `saffron package` refuses a task carrying
  a url (`saffron/task.py:1382-1385`). The home ledger holds no such row.
- **The child's refusal text.** A `stack=True` scan refuses a child of such
  a parent with "so merge it, or rerun it". That remedy no longer reaches
  the parent. The line is `_stack_order`'s and stays as it is.
- **`DESIGN.md`.** §4.2's note under the refusal gate says refusal is keyed
  on `task_id`. It gains this exception by hand in this spec's own commit.

## Notes for the agent

**No criterion declares a mutant.** The refusal is new code whose spelling
is yours. The one edit to existing code adds a field to `_open_prs`'s
`--json` list, and its place in that list is yours too. `witness` will
report `skip`.

**Seed rows the way the ledger writes them.** `_task_at`
(`tests/test_scheduler.py:49-55`) creates a task on `saffron/<id>` and sets
its state. Put a url on with `ledger.adopt_pull_request`, or with
`set_task_package` (`tests/test_scheduler.py:58-64`) and then
`set_task_state` back to `ORPHANED`. Record a push with
`ledger.record_push`. Two seeded specs that share a body share a
`spec_sha`, so give each its own id.

**A fake `gh` must answer only the fields it is asked for.** `_fake_gh`
(`tests/test_scheduler.py:228-238`) prints every key whatever the argv
asks. A witness built on it passes a scan that never asks for the head.
Read the `--json` argument and print only those keys.

**Read both scans.** `build_queue(..., stack=True)` refuses through the
same loop. A witness reading the plain scan alone passes a refusal placed
on one branch only.

**No `retired_first`.** Of the queued specs only `SA-0425` has a task in
the home ledger. Task 476 is `ORPHANED` with no url. `gh pr list` showed no
open pull request on a `saffron/` branch on 2026-11-23.

**The size estimate prices past 80%.** `check` multiplies the measured 198
lines by 1.77 and reads 1404 tokens against the `bug` ceiling of 1300. The
real `size` gate leaves out `tests/`, and the prototype changed 49 lines of
`saffron/scheduler.py`. `size` is advisory at `standard`.

**What the prototype measured.** Seven test files passed with the change
applied, the site pin aside. They were `tests/test_scheduler.py`,
`tests/test_refusal_count.py`, `tests/test_batch.py`,
`tests/test_reconcile.py`, `tests/test_spec_loop_driver.py`,
`tests/test_cli.py` and `tests/test_task.py`.
