---
id: SA-0331
title: A resumed row's own pull request does not stop an unpackaged push onto its branch, and no merge moves a `REBUTTAL_UNJUDGED` row to `MERGED`
type: bug
priority: 1
estimated_lines: 245
estimate_measured: true
touches:
  - saffron/phases/package.py
  - saffron/reconcile.py
  - saffron/cli.py
  - tests/test_package.py
  - tests/test_reconcile.py
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
  - saffron/task.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/regate.py
  - saffron/batch.py
  - saffron/report/**
  - saffron/record/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/cell/**
  - saffron/phases/rebut.py
  - saffron/phases/review.py
  - tests/test_cli.py
  - tests/test_task.py
  - tests/test_session.py
  - tests/test_ledger.py
  - tests/test_scheduler.py
budget_usd: 38
max_attempts: 3
max_turns: 210
acceptance:
  - claim: >-
      `push_unpackaged_work` refuses when the outcome's own row carries a
      non-empty `pr_url`, and the remote branch stays where it was. The
      witness drives every state in `TaskState` over a recorded head. It
      also drives a head an operator moved and an absent branch. The row
      keeps its `pushed_sha` and `pr_url`, and `gh` is never called. The note
      names the pull request, the branch and the task directory, and says
      `unmoved`. Outside that directory's path it never says `nothing`. The
      note reaches `emit`. With no patch the note stays the no-commits one.
    witness: tests/test_package.py::test_a_row_carrying_its_pull_request_keeps_that_branch_whatever_its_outcome
    wrong_versions:
      - The guard fires only when the outcome ended `REBUTTAL_UNJUDGED`.
      - The guard fires only when the outcome ended `REBUTTAL_UNJUDGED` or `EXHAUSTED`.
      - The guard fires only when the remote head equals the row's `pushed_sha`, so a moved head gets the branch check's note and an absent branch is pushed.
      - The guard fires only when the remote branch exists, so an absent branch is pushed.
      - The guard asks `gh` whether the pull request is open before it refuses.
      - The note says nothing was pushed.
      - The note leaves out the task directory.
      - The note leaves out the pull request's url.
      - The note leaves out the branch.
      - The note leaves out that the branch is unmoved.
      - The guard returns its refusal without emitting it.
      - The guard empties the row's `pr_url` as it refuses.
      - The guard runs before the patch check, so a run with no patch speaks of a patch it lacks.
  - claim: >-
      On a resumed row, `package()` in its `exhausted` mode followed by the
      push leaves the branch unmoved at each of three ends. A `PackageError`
      from re-verification leaves the old head, and the note names the pull
      request. A `PackageError` from `open_draft_pr` leaves PACKAGE's squash,
      with no `NOT PACKAGED` commit over it, and the note names the pull
      request. A refusal through `_finish` empties the row's `pr_url`, so the
      branch check refuses with its own note and names no pull request.
    witness: tests/test_package.py::test_an_exhausted_package_leaves_the_branch_of_a_carried_pull_request_unmoved
    wrong_versions:
      - The guard fires only when `package_refusal` is unset, so both raises push over the pull request.
      - The guard spares the row whose `pushed_sha` is the remote head when `package_refusal` is set, so the squash is replaced.
      - The guard tests `pr_url` against `None`, so the refused row's empty string reads as a pull request.
      - The branch check is removed as redundant, so the refused row is pushed.
      - '`_finish` is changed to keep a carried `pr_url`, which this spec leaves out of scope.'
  - claim: >-
      A remote head this spec never recorded still refuses through the branch
      check, on a row with no pull request, as it does today.
    witness: tests/test_package.py::test_unpackaged_work_does_not_replace_a_branch_someone_else_moved
    preserves: true
    mutant:
      file: saffron/phases/package.py
      find: 'if current and current not in recorded:'
      replace: 'if False:'
    wrong_versions:
      - The branch check is removed because the new guard reads as covering it.
  - claim: >-
      Another row of this spec follows today's rule. A `REJECTED` row with a
      pull request, an `EXHAUSTED` row with none and another spec's drafted
      row each let the push through. An `EXHAUSTED` row with a pull request
      refuses it.
    witness: tests/test_package.py::test_unpackaged_work_after_a_refused_package_says_so_and_spares_a_draft
    preserves: true
    mutant:
      file: saffron/phases/package.py
      find: 'or (row["state"] == "EXHAUSTED" and row["pr_url"])'
      replace: or False
    wrong_versions:
      - The guard reads every row of the spec for a `pr_url`, so an older `REJECTED` row refuses the push.
      - The guard replaces the `others` rule, so another row's open draft no longer refuses.
  - claim: >-
      A rerun whose own row carries no pull request still replaces that row's
      own earlier push, as it does today.
    witness: tests/test_package.py::test_a_rerun_on_one_task_replaces_that_tasks_own_unpackaged_push
    preserves: true
    mutant:
      file: saffron/phases/package.py
      find: 'recorded = {row["pushed_sha"] for row in task_rows if row["pushed_sha"]}'
      replace: 'recorded = {row["pushed_sha"] for row in others if row["pushed_sha"]}'
    wrong_versions:
      - The guard refuses on the row's own `pushed_sha` rather than its `pr_url`.
  - claim: >-
      A merged pull request on a `REBUTTAL_UNJUDGED` row moves it to `MERGED`.
      The witness drives a merged answer, which records the head and reports
      a moved one. It also drives a row a crash left with its merged head on
      the ledger, which completes with no `gh` call.
    witness: tests/test_reconcile.py::test_a_merged_pull_request_moves_its_rebuttal_unjudged_row_to_merged
    mutant:
      file: saffron/reconcile.py
      find: state not in PR_PENDING_STATES and state not in MERGE_ONLY_STATES
      replace: state not in PR_PENDING_STATES and state not in MERGE_ONLY_STATES - {"REBUTTAL_UNJUDGED"}
    wrong_versions:
      - The merged answer writes `MERGED` for this state and records no head.
      - The crash-recovered row is asked again rather than completed from its head.
  - claim: >-
      No other answer moves a `REBUTTAL_UNJUDGED` row, and each is asked for.
      The witness drives the six objects `_pr_status` returns other than a
      merge and the three answers it turns into `None`, which land in
      `unasked`. A null and an empty `pr_url` are never asked. Over two scans,
      a row answered with a moved head and a matching re-gate reports both
      each time.
    witness: tests/test_reconcile.py::test_a_rebuttal_unjudged_row_is_asked_and_moves_on_no_answer_but_a_merge
    mutant:
      file: saffron/reconcile.py
      find: if state not in MERGE_ONLY_STATES or candidate == "MERGED"
      replace: if state not in MERGE_ONLY_STATES - {"REBUTTAL_UNJUDGED"} or candidate == "MERGED"
    wrong_versions:
      - The state joins `PR_PENDING_STATES` rather than the merge-only set, so a closed pull request writes `REJECTED`.
      - A closed answer also moves the row, to `REJECTED`.
      - An empty `pr_url` is asked, because the skip tests it against `None`.
      - A `gh` failure on this state is dropped rather than recorded in `unasked`.
      - This state skips the `head_moved` report.
      - This state skips the `regated` report.
  - claim: >-
      `_ADOPTABLE_STATES` keeps exactly its four members, `EXHAUSTED`,
      `MERGE_FAILED`, `NOT_IMPLEMENTED` and `READY_FOR_REVIEW`. The witness
      drives every state in `TaskState`. Each of the 24 others refuses before
      any `gh` call, `REBUTTAL_UNJUDGED` among them. Each of the four reaches
      `gh`.
    witness: tests/test_cli.py::test_adopt_refuses_with_exit_one_and_writes_nothing
    preserves: true
    mutant:
      file: saffron/cli.py
      find: 'if state not in _ADOPTABLE_STATES:'
      replace: 'if state not in _ADOPTABLE_STATES | {"REBUTTAL_UNJUDGED"}:'
    wrong_versions:
      - The set stays built on the merge-only set, so `REBUTTAL_UNJUDGED` becomes adoptable.
      - The set is spelled out without `EXHAUSTED`.
      - The set is spelled out without `MERGE_FAILED`.
      - The set is spelled out without `NOT_IMPLEMENTED`.
      - The set is spelled out without `READY_FOR_REVIEW`.
---

## Context

Backlog item **b-af24d1**, found by the second spec review of `SA-0276`. It
cites `DESIGN.md` §4.2.1, §5.6 and §5.7. Every line number below was read at
`f596e814`. The item's own line numbers were read at `8272ac44` and do not
hold there.

`DESIGN.md` §5.7 and `CONTEXT.md`'s `REBUTTAL_UNJUDGED` entry read as amended
by this spec's pull request. §5.7 says the push does not replace the branch of
a row that carries its own pull request. The entry says only a merge of that
pull request moves the row to `MERGED`.

**A resumed row keeps its pull request.** `CHANGES_REQUESTED` re-queues on its
own task (`saffron/scheduler.py:136-145`). Only a `task_package` fact writes
`pr_url` (`saffron/ledger.py:882`), and `saffron/cell/session.py` never names
it. `tests/test_session.py:5279` seeds that row.

**Two paths reach the push with such a row.** A cell PACKAGE does not run
reaches it directly (`saffron/task.py:965`). A cell in the `exhausted` mode
reaches it after `package()` refuses or raises (`saffron/task.py:916-931`). A
raise there is caught (`saffron/task.py:893-905`), so no `task_package` fact
is written. REBUT's cut sets that mode up (`saffron/cell/session.py:3756-3758`).

**The guard skips the row's own pull request.** The open-pull-request guard
reads `others` (`saffron/phases/package.py:1145-1155`), which leaves the
outcome's own row out. The branch check reads every row's `pushed_sha`
(`saffron/phases/package.py:1157-1162`), so the row's own head passes it.

**`reconcile` never asks about the row.** A row outside `PR_PENDING_STATES` and
`MERGE_ONLY_STATES` is skipped (`saffron/reconcile.py:178-181`). The merge-only
set is two states (`saffron/reconcile.py:46`), and `saffron/cli.py:2860` builds
`_ADOPTABLE_STATES` from it.

## Problem

Measured on the host at `f596e814`, with the `packageable` fixture, a real
`package()`, a real push and a local bare remote. The row was seeded as a
resumed `CHANGES_REQUESTED` draft.

| End | Row after `package()` | The push at base |
|---|---|---|
| `reverify` raises `PackageError` | `pr_url` kept | a `NOT PACKAGED` commit lands on the branch |
| `open_draft_pr` raises after PACKAGE's push | `pr_url` kept | a `NOT PACKAGED` commit replaces the squash |
| a conflict refuses through `_finish` | `pr_url` and `pushed_sha` empty | the branch check refuses |

The first two replace what the operator's pull request shows with a commit
PACKAGE never packaged. A `REBUTTAL_UNJUDGED` end does the same by the direct
path.

When the operator merges that pull request, the row stays `REBUTTAL_UNJUDGED`.
So a child still reads the parent as open, and the accept rate never counts
the merge.

## Out of scope

- **The third row of the table.** `_finish` writes an empty `pr_url` and
  `pushed_sha` over a carried pull request
  (`saffron/phases/package.py:998-1005`). The guard then has nothing to read.
  This spec's claim covers rows that still carry `pr_url`. The branch check
  refuses in that measured case, and a witness pins it. That write path is its
  own item, b-8693ef, filed in this spec's pull request.
- Adopting a `REBUTTAL_UNJUDGED` row.
- A child of a `REBUTTAL_UNJUDGED` parent whose latest run pushed nothing.
  `SA-0330` owns it, and a refused push here leaves its column unset.
- A merged pull request on any other state outside the merge-only set.
- Whether the pull request is still open. The guard asks GitHub nothing.

## Notes for the agent

**Edit or new.** The guard is new code, so criteria 1 and 2 declare a witness
and no mutant. `witness` reports an honest `skip` on them. Criteria 3 to 8
pin text the code already determines. Write the two new `reconcile` tests and
the two new `package` tests. Criteria 3, 4, 5 and 8 name tests that exist, and
those tests need no edit.

**The guard.** Add it to `push_unpackaged_work` beside the `others` guard,
after the patch check and before the branch check. Refuse through `_refuse`.
Read the row from `task_rows`, and treat an empty `pr_url` as none. The note
must stay true when PACKAGE already pushed its squash. It says this push
leaves the branch unmoved, and it never says nothing was pushed. Update the
docstring sentence at `saffron/phases/package.py:1067-1070`.

A `repo_id` of `None` still reads no rows (`saffron/phases/package.py:1140-1144`),
so the guard has nothing to read there. That stays as it is.

**The merge-only set.** Add one member at `saffron/reconcile.py:46`, and leave
the two conditions that read the set as they stand. Reread the comments at
`saffron/reconcile.py:40`, `:44`, `:176-177`, `:194` and `:204`. The comment at
`:44` names who attached the pull request, and `:176-177` names the two states.
Both need the new case. The other three stay true.

**The other readers, as accepted behaviour.** These match what an `EXHAUSTED`
row with a draft does today.

- Each scan makes one `gh` call for each such row.
- `head_moved` and `regated` report on each scan until the row moves
  (`saffron/reconcile.py:195-202`). `saffron/cli.py:3182-3199` prints them.
- A `gh` failure lands in `unasked`, printed at `saffron/cli.py:3170`.
- `saffron/task.py:333` and `:502` then emit a `gh_unreachable` line and go on
  as they did.
- A parent that merged now reads `MERGED` at `saffron/task.py:491`, and its
  child unstacks. That is the point of this half.

**`_ADOPTABLE_STATES`.** Spell its four members out at `saffron/cli.py:2860`, and
drop the unused import at `saffron/cli.py:57`. `_adopt` reads the set at
`saffron/cli.py:2911`. `tests/test_cli.py:2773` pins `takes` and the count of
24, and it fails if the set stays built on the merge-only set. That run was
measured.

**Test shape.** A plain `def` over a loop, never a parametrised test. The
witness's state loop reads `typing.get_args(TaskState)` locally, as
`tests/test_cli.py:2773` does. Import the guard's names inside each test, as
`tests/test_package.py:3345-3349` explains. A `package` witness drives the three
ends on one `packageable` in the table's order. Its first two ends fail at base,
and the third passes there. `tests/test_reconcile.py:831` is the shape for the
nine answers, and `tests/test_reconcile.py:503` for the re-gate seed.

A `PackageResult` carrying no `pr_url` still reaches the same push, and the
existing `tests/test_task.py` test covers that handoff. This spec does not drive
`run_task` itself.

**Size.** A prototype measured 101 changed tokens outside the test paths and 980
with them. The estimate is the second figure over four.
