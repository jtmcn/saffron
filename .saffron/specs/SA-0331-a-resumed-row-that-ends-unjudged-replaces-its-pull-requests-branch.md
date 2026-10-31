---
id: SA-0331
title: A row's standing pull request does not stop a rerun's unpackaged push onto its branch, and no merge moves a `REBUTTAL_UNJUDGED` row to `MERGED`
type: bug
priority: 1
depends_on: [SA-0329]
estimated_lines: 48
estimate_measured: true
touches:
  - saffron/phases/package.py
  - saffron/reconcile.py
  - saffron/cli.py
  - saffron/task.py
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
      witness sets the outcome's state and the row's state to every member
      of `TaskState`, over a recorded head. It also drives a head an operator moved and an absent branch. The row
      keeps its `pushed_sha` and `pr_url`, and `gh` is never called. The note
      names the pull request, the branch and the task directory, and says
      `unmoved`. Outside that directory's path it never says `nothing`. The
      note reaches `emit`. With no patch the note stays the no-commits one.
    witness: tests/test_package.py::test_a_row_carrying_its_pull_request_keeps_that_branch_whatever_its_outcome
    wrong_versions:
      - The guard fires only when the outcome ended `REBUTTAL_UNJUDGED`.
      - The guard fires only when the outcome ended `REBUTTAL_UNJUDGED` or `EXHAUSTED`.
      - The guard spares an outcome that ended `RATE_LIMITED`, so a rate-limited rerun replaces the branch.
      - The guard fires only while the row's own state is `CHANGES_REQUESTED`.
      - The guard spares a row whose own state is `MERGED`.
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
      On a row carrying a pull request, `package()` runs in its `exhausted`
      mode, and the push follows with `package()`'s refusal or raise text, as `run_task`
      hands it. At each of three ends the push leaves the branch where
      `package()` left it. A `PackageError` from re-verification leaves the
      old head, and the note names the pull request. A `PackageError` from `open_draft_pr` leaves PACKAGE's squash,
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
      Apart from the states criterion 9 adds, another row of this spec follows
      today's rule. A `REJECTED` row with a
      pull request, an `EXHAUSTED` row with none and another spec's drafted
      row each let the push through. An `EXHAUSTED` row with a pull request
      refuses it.
    witness: tests/test_package.py::test_unpackaged_work_after_a_refused_package_says_so_and_spares_a_draft
    preserves: true
    mutant:
      file: saffron/phases/package.py
      find: 'others = [row for row in task_rows if row["task_id"] != outcome.task_id]'
      replace: others = []
    wrong_versions:
      - The guard reads every row of the spec for a `pr_url`, so another `REJECTED` row refuses the push.
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
  - claim: >-
      Another row of this spec, carrying a pull request, refuses a rerun's push
      when it is `CHANGES_REQUESTED`, `APPROVED` or `REBUTTAL_UNJUDGED`, as it
      does at `READY_FOR_REVIEW` and `EXHAUSTED`. The branch stays where it was,
      and the note says `awaiting review or a merge` and `not ours to replace`.
      The witness sets that row to every member of `TaskState`, with the branch
      at a head this spec recorded. Every state but those five lets the push
      through. Each of the three new states also refuses at every member of
      `TaskState` on the outcome, and with the other row on either side of the
      outcome's task id. An empty `pr_url` on `EXHAUSTED` and on each new state
      lets the push through, and `READY_FOR_REVIEW` still refuses with one.
    witness: tests/test_package.py::test_another_row_with_a_standing_pull_request_keeps_that_branch
    mutant:
      file: saffron/phases/package.py
      find: 'others = [row for row in task_rows if row["task_id"] != outcome.task_id]'
      replace: others = []
    wrong_versions:
      - The `others` guard is left as it stands, so the rerun's push replaces the branch.
      - The guard leaves out `CHANGES_REQUESTED`, so a rerun beside a sent-back pull request replaces its branch.
      - The guard leaves out `APPROVED`, so a rerun beside an approved pull request replaces its branch.
      - The guard leaves out `REBUTTAL_UNJUDGED`.
      - The guard refuses on any state in the merge-only set, so a `NOT_IMPLEMENTED` row with a pull request refuses.
      - '`REVIEW_INCOMPLETE` joins the guard, though `Out of scope` leaves that state out.'
      - The guard refuses on any state with a `pr_url`.
      - The guard refuses on `CHANGES_REQUESTED` without reading its `pr_url`.
      - The guard refuses on `APPROVED` without reading its `pr_url`.
      - The guard refuses on `REBUTTAL_UNJUDGED` without reading its `pr_url`.
      - The guard reads `pr_url` on `READY_FOR_REVIEW` too, so a row with an empty one lets the push through.
      - The guard reads only rows with a lower task id than the outcome's.
      - The guard reads only rows with a higher task id than the outcome's.
      - The new states refuse only when the outcome ended `REBUTTAL_UNJUDGED`.
      - The note still says only `awaiting review`, which is false of an `APPROVED` row's pull request.
---

## Context

Backlog item **b-af24d1**, found by the second spec review of `SA-0276`. It
cites `DESIGN.md` §4.2.1, §5.6 and §5.7. Every line number below was read at
`f596e814`. The item's own line numbers were read at `8272ac44` and do not
hold there.

`DESIGN.md` §5.7 and `CONTEXT.md`'s `REBUTTAL_UNJUDGED` entry read as amended
by this spec's pull request. §5.7 says the push does not replace the branch
when the task's own row carries a pull request. It says the same of another row
carrying one under a state criterion 9 names. The entry says only a merge of that
pull request moves the row to `MERGED`. §4.1's `REBUTTAL_UNJUDGED` entry reads
as amended too, with its exit to `MERGED`.

**A rerun runs on a fresh row.** `saffron/cli.py:679` and `:727` pass `run_task`
no `task_id`. `saffron/task.py:680` defaults it to `None`, and
`saffron/cell/session.py:2253` then creates a task. `_stack_mint` opens a fresh
task too (`saffron/cli.py:1431-1433`).
Backlog item b-223244 records this against the "resumes that task row" of
`DESIGN.md` §4.2.1. Only a `task_package` fact writes `pr_url`
(`saffron/ledger.py:882`), and `saffron/cell/session.py` never names it. So the
new row has no `pr_url`, and the row that carries one stays where it was.

**That other row is the reachable case.** `saffron/scheduler.py:1280` sets a
candidate's `task_id` from a re-queueing row at the same `spec_sha`, and
`CHANGES_REQUESTED` is one (`saffron/scheduler.py:136-145`). Gate 0 exempts a
candidate with a `task_id` from its open-pull-request refusal
(`saffron/scheduler.py:865`), and the runner then drops that id. So the older
row's open pull request passes gate 0, and the rerun runs on a fresh row. An
attended cell has no scan ahead of it (`saffron/cli.py:676`), so it reaches the
same push beside an `APPROVED` row too.

**The row's own pull request is not reachable on any path read at base.** Only
`_stack_runner` passes a `task_id` (`saffron/cli.py:842`), the one `wrapped` minted
(`saffron/batch.py:669-672`). A spec is offered again only after `RATE_LIMITED`,
`PROVIDER_UNREACHABLE`, `PREFLIGHT_FAILED` or an unmarked `CellRuntimeError`
(`saffron/batch.py:902`, `:908`). Only `_finish` (`saffron/phases/package.py:998`)
and `adopt_pull_request` (`saffron/ledger.py:1700`) write a `pr_url`. `_finish`
writes `READY_FOR_REVIEW`, `MERGE_FAILED` or `EXHAUSTED` (`saffron/phases/package.py:633-634`), and no raise
follows it that could be offered again. `saffron adopt` refuses all but four states
(`saffron/cli.py:2860`, `:2911`). Of those four, only an `EXHAUSTED` row can be
offered again, after its PACKAGE raised unmarked (`saffron/task.py:906-911`). So a
by-hand adoption in that instant is the one way left.

The same trace covers a `REBUTTAL_UNJUDGED` row with a `pr_url`. The cell writes
that state on its own row (`saffron/cell/session.py:3773-3774`), and that row has
none. Criteria 1, 2, 6 and 7 stay as the rule for such a row. No production row
reaches them today. They bind if a rerun ever resumes its row, as `DESIGN.md` §4.2.1 still
says it does. Backlog item b-223244 would instead amend that text.

**Two paths reach the push with a carried pull request.** A cell PACKAGE does not
run reaches it directly (`saffron/task.py:965`). A cell in the `exhausted` mode
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
`CHANGES_REQUESTED` draft carrying its pull request.

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

**The reachable row.** Measured at `fb9bee0e` on the same fixture. A new row ended
`REBUTTAL_UNJUDGED` beside another row carrying a `pr_url`, with the branch at that
row's head. Over every member of `TaskState` on that row, `READY_FOR_REVIEW`
and `EXHAUSTED` refused. The other 26 pushed, `CHANGES_REQUESTED`, `APPROVED`,
`REBUTTAL_UNJUDGED` and `REVIEW_INCOMPLETE` among them. So a rerun beside a
sent-back or approved pull request replaces its branch with work no critic judged.

## Out of scope

- **The third row of the table.** `_finish` writes an empty `pr_url` and
  `pushed_sha` over a carried pull request
  (`saffron/phases/package.py:998-1005`). The guard then has nothing to read.
  This spec's claim covers rows that still carry `pr_url`. The branch check
  refuses in that measured case, and a witness pins it. That write path is its
  own item, b-8693ef, filed in this spec's pull request.
- Adopting a `REBUTTAL_UNJUDGED` row.
- A rerun beside another row at `REVIEW_INCOMPLETE`. Its push still goes through,
  though the state carries the same gap. The operator left that state to the
  backlog item `SA-0330` files for it, one layer above this spec, so this spec
  leaves it out. `REJECTED` and every other state let the push through as well.
- Whether a rerun resumes its row. Backlog item b-223244 owns that, and this spec
  only guards a row in either case.
- A child of a `REBUTTAL_UNJUDGED` parent whose latest run pushed nothing.
  `SA-0330` owns it, and a refused push here leaves its column on an earlier
  state.
- PACKAGE's own lease push over a carried pull request
  (`saffron/phases/package.py:913-919`). The second end of the table lands
  through it.
- A merged pull request on any other state outside the merge-only set.
- Whether the pull request is still open. The guard asks GitHub nothing. So an
  attended cell, which reconciles nothing first, reads a row a closed pull request
  has not yet moved. Its push is refused, and the patch stays in the task directory.

## Notes for the agent

**`SA-0330`, above this spec.** It declares `depends_on: [SA-0331]`, so it builds
on this spec's work.

**`SA-0329`, the parent.** It edits `saffron/phases/package.py`,
`saffron/task.py` and `tests/test_package.py`, so this spec stacks on it. No
claim here turns on its code. Lines cited here were read before it, so find each
by its text.

**Existing tests.** No test at base seeds another row of its spec at
`CHANGES_REQUESTED` or `APPROVED` and then expects an unpackaged push. A logged run
of the whole suite over the prototype saw such a row reach the push in the new
witness alone. `tests/test_package.py:3609` is the one assertion on the note's old
words, and it still holds. So no existing test changes.

**Edit or new.** The guard is new code, so criteria 1 and 2 declare a witness
and no mutant. `witness` reports an honest `skip` on them. Criteria 3 to 9
pin text the code already determines. Write the two new `reconcile` tests and
the three new `package` tests. Criteria 3, 4, 5 and 8 name tests that exist, and
those tests need no edit.

**The guard.** Add it to `push_unpackaged_work` beside the `others` guard,
after the patch check and before the branch check. Refuse through `_refuse`.
Read the row from `task_rows`, and treat an empty `pr_url` as none. The note
must stay true when PACKAGE already pushed its squash. It says this push
leaves the branch unmoved, and it never says nothing was pushed.

Update the docstring sentence at `saffron/phases/package.py:1067-1070`. That
docstring runs 31 lines against `prose`'s limit of 10, and the gate counts each
line past the limit (`.saffron/gates/prose.py:310-323`). A 32nd line is a new
failure, so keep it at 31 or fewer. A prototype's rewording drew no new hit once
its closing sentence went. An added clause can also push that sentence past 25
words. That was measured too.

**Another row.** `others` is every row of this spec but the outcome's, whichever
side of it the row's task id falls. A row at one of criterion 9's new states sits
there, where the guard at `saffron/phases/package.py:1147-1151` refuses on neither
of its two shapes. Its recorded sha passes the branch check.

Measured on a prototype with the own-row guard and the `packageable` fixture.
Before the widening every new state's push landed. After it each was refused and
the branch stayed. Add `CHANGES_REQUESTED`, `APPROVED` and `REBUTTAL_UNJUDGED` to
that guard, and read `pr_url` on each as `EXHAUSTED` does. The refusal on
`READY_FOR_REVIEW` and on `EXHAUSTED` keeps its rule.
`saffron/reconcile.py:6-7` keeps this module from importing the merge-only set, and
that set also holds a state this guard must not refuse on.

The comment at `saffron/phases/package.py:1146` names `EXHAUSTED` alone, and
the docstring sentence at `:1068-1070` names two states. Both must name what the
guard now reads. The note at `:1153` says `awaiting review`, which is false of an
`APPROVED` row's pull request. Make it say `awaiting review or a merge`.
`tests/test_package.py:3609` asserts `awaiting review` in that note and still
passes, so that test needs no edit.

The new refusal reaches only a rerun whose PACKAGE did not run or opened no pull
request. A rerun that reaches `READY_FOR_REVIEW` still moves the
branch through PACKAGE's own lease push, as `Out of scope` says.

A `repo_id` of `None` still reads no rows (`saffron/phases/package.py:1140-1144`),
so the guard has nothing to read there. That stays as it is.

**The merge-only set.** Add one member at `saffron/reconcile.py:46`, and leave
the two conditions that read the set as they stand. Reread the comments at
`saffron/reconcile.py:40`, `:44`, `:176-177`, `:194` and `:204`. The comment at
`:44` names who attached the pull request, and `:176-177` names the two states.
Both need the new case. The other three stay true. A comment over two lines or
a sentence over 25 words is a new `prose` hit, and a prototype's first `:44`
edit drew both.

**The comments in `saffron/task.py`.** Correct `:917-918` and `:976-977`, which
say no pull request exists. That is false on a row that carries one. The file's
code does not change, and no criterion reads these comments. Write them with no
semicolon, and keep each at two lines.

**The other readers, as accepted behaviour.** These match what an `EXHAUSTED`
row with a draft does today.

- Each scan makes one `gh` call for each such row.
- `head_moved` and `regated` report on each scan until the row moves
  (`saffron/reconcile.py:195-202`). `saffron/cli.py:3182-3199` prints them.
- A `gh` failure lands in `unasked`, printed at `saffron/cli.py:3170`.
- `saffron/task.py:333` and `:502` then emit a `gh_unreachable` line and go on
  as they did. `SA-0330` is the spec that turns an unasked parent into a refusal.
- A parent that merged now reads `MERGED` at `saffron/task.py:491` and in the
  stacking loop at `saffron/task.py:367-369`, and its child unstacks. This note
  rests on that existing loop. No criterion here drives it.

**`_ADOPTABLE_STATES`.** Spell its four members out at `saffron/cli.py:2860`, and
drop the unused import at `saffron/cli.py:57`. `_adopt` reads the set at
`saffron/cli.py:2911`. `tests/test_cli.py:2773` pins `takes` and the count of
24, and it fails if the set stays built on the merge-only set. That run was
measured.

**Test shape.** A plain `def` over a loop, never a parametrised test. Each
witness's state loop reads `typing.get_args(TaskState)` locally, as
`tests/test_cli.py:2773` does. Criterion 1's witness writes each member to both
the outcome and the row. Criterion 9's writes each member to the other row alone,
and compares the remote head with `result.pushed_sha`. Two pushes of one patch in
one second can make one commit, so it never asserts that a push moved the head.
`adopt_pull_request(row, "")` empties a row's `pr_url`. Pointing
`packageable.outcome.task_id` at a new row puts the fixture's row below the outcome's.
The `package` witness hands the push the text `package()` raised or
returned, as `saffron/task.py:919` and `:929` do. Import the guard's names inside each test, as
`tests/test_package.py:3345-3349` explains. A `package` witness drives the three
ends on one `packageable` in the table's order. Its first two ends fail at base,
and the third passes there. `tests/test_reconcile.py:831` is the shape for the
nine answers, and `tests/test_reconcile.py:503` for the re-gate seed.

A `PackageResult` carrying no `pr_url` still reaches the same push, and the
existing `tests/test_task.py` test covers that handoff. This spec does not drive
`run_task` itself.

**Size.** A prototype measured 192 changed tokens by `size_gate`, against the `bug`
ceiling of 1300. It measured 952 more under the test paths, which that gate does
not count.
`estimated_lines` is the first figure over four. Its witnesses carry one-line
docstrings, so a cell's own test text can run higher, and no gate reads it.
