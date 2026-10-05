---
id: SA-0204
title: An EXHAUSTED task whose gates went green opens no pull request
type: feature
priority: 2
depends_on: [SA-0203, SA-0198]
estimated_lines: 428
estimate_measured: true
touches:
  - saffron/task.py
  - saffron/phases/package.py
  - saffron/report/pr_body.py
  - tests/test_task.py
  - tests/test_package.py
  - tests/test_report.py
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
  - saffron/finish.py
  - saffron/ledger.py
  - saffron/reconcile.py
  - saffron/scheduler.py
  - saffron/cli.py
  - saffron/events.py
  - saffron/intake.py
  - saffron/replay.py
  - saffron/record/**
  - saffron/repos/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/cell/**
  - saffron/phases/implement.py
  - saffron/phases/review.py
  - saffron/phases/rebut.py
  - saffron/report/index.py
  - saffron/report/stack.py
  - tests/test_batch.py
  - tests/test_session.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_queued_specs.py
budget_usd: 33
max_attempts: 3
max_turns: 180
acceptance:
  - claim: >-
      `run_task` hands a cell to `package()` in the `EXHAUSTED` mode the
      second criterion names exactly when the cell ended `EXHAUSTED` with
      at least one finding `anchored_blockers` returns and no
      `rebut_result`. That call passes the same `parent_branch` a
      `READY_FOR_REVIEW` cell's call does, so in a stack batch it is the
      handoff's target branch. A `READY_FOR_REVIEW` cell is still packaged,
      outside that mode. Every other shape goes to `push_unpackaged_work`
      as it does today and never reaches `package()`. The witness drives
      eight cells, each with a stack handoff: that `EXHAUSTED` cell, a
      `READY_FOR_REVIEW` one, an `EXHAUSTED` one with no review, an
      `EXHAUSTED` one with an anchored blocker and a `rebut_result`, a
      `REVIEWING` and a `REBUTTING` one each with an anchored blocker and
      no `rebut_result`, and two `EXHAUSTED` ones whose only finding is an
      unanchored blocker or an anchored concern.
    witness: tests/test_task.py::test_an_exhausted_task_whose_rebuttal_was_never_paid_for_is_packaged
    mutant:
      file: saffron/task.py
      find: parent_branch=target_branch,
      replace: parent_branch=None,
    wrong_versions:
      - The routing ignores `rebut_result`, so a cell whose gates went red after the rebuttal is packaged.
      - The routing keys on a non-empty `reviews` rather than on an anchored blocker.
      - The routing keys on any state but `READY_FOR_REVIEW`, so a `REVIEWING` cell is packaged.
      - Every `package()` call sets the `EXHAUSTED` mode, so a `READY_FOR_REVIEW` cell is recorded `EXHAUSTED`.
      - The `EXHAUSTED` call passes no `parent_branch`, so a stacked task's pull request targets the default branch.
      - The routing counts every blocker, so an `EXHAUSTED` cell whose only blocker is unanchored is packaged.
  - claim: >-
      `package()` takes a keyword, off by default, that packages a task
      which ended `EXHAUSTED`. Set, every path that records a state records
      `EXHAUSTED` where the same path records `MERGE_FAILED` or
      `READY_FOR_REVIEW` with it unset. That holds for the returned
      `PackageResult`, the ledger's row and the queue line alike. The
      witness drives the pull request and all seven refusals: a parent
      that is gone, a conflict, a credential in the patch, in the agent's
      commit subjects and in the body, new failures on re-verification,
      and a branch that moved. The pull request path still pushes and
      opens a draft against the default branch, and records its `pr_url`
      and `pushed_sha`. Its `pr_body.md` carries the third criterion's
      line.
    witness: tests/test_package.py::test_an_exhausted_package_keeps_its_state_on_every_path
    mutant:
      file: saffron/phases/package.py
      find: pr_url=pr_url,
      replace: pr_url="",
    wrong_versions:
      - A gone parent still records `MERGE_FAILED`.
      - A credential refusal still records `MERGE_FAILED`.
      - A conflict still records `MERGE_FAILED`.
      - New failures on re-verification still record `MERGE_FAILED`.
      - A branch that moved still records `MERGE_FAILED`.
      - The pull request path still records `READY_FOR_REVIEW`.
      - The body is rendered without the third criterion's keyword, so it names no unanswered blocker.
  - claim: >-
      `render_pr_body` takes two keywords, both off by default. With the
      first set, `## Not covered` carries one line saying "the task ended
      `EXHAUSTED` before the critics finished judging its rebuttal" and
      that "its blockers stand". The line names the `file:line` of each
      finding `anchored_blockers` returns, and of no other finding. With
      the second set, `## Not covered` carries a line saying "HEAD moved
      after REVIEW" and that the patch carries commits "no lens judged".
      Unset, neither line renders, even beside anchored blockers and no
      `rebut_result`. Each `file` passes through `_cell`. The witness
      renders two anchored blockers from two lenses beside an unanchored
      blocker and an anchored concern, with the first keyword alone, with
      both, and with neither. One anchored blocker's file holds a `|`.
    witness: tests/test_report.py::test_an_unrebutted_body_names_every_blocker_it_left_standing
    wrong_versions:
      - The line names only the first anchored blocker.
      - The line renders whenever anchored blockers stand with no `rebut_result`, keyword or not.
      - The line names an unanchored blocker too.
      - The line names every anchored finding, a concern included.
      - The line says the blockers went unanswered, which is false where the cut-short rebuttal recorded answers and only a verdict is missing.
      - The HEAD line renders whenever the first keyword is set, whatever the second says.
      - The HEAD line never renders.
      - The line writes each file raw, skipping `_cell`.
  - claim: >-
      When `package()` in the `EXHAUSTED` mode returns no `pr_url`, or
      raises a `PackageError`, `run_task` then calls `push_unpackaged_work`
      as it does for any `EXHAUSTED` task. It hands that call PACKAGE's note
      or the error's text, as the seventh criterion's keyword. The task's
      one queue row stays `EXHAUSTED` with an empty link, and its note
      carries that text and the push's note both. `run_task` returns the
      outcome in `EXHAUSTED` and raises nothing. When `package()` returns a
      `pr_url`, no push runs and the row is the one PACKAGE wrote. A
      `PackageError` from a `READY_FOR_REVIEW` cell's `package()` still
      raises, and nothing is pushed. The witness drives a refusal, a
      `PackageError` and a pull request in the `EXHAUSTED` mode, and a
      `PackageError` from a `READY_FOR_REVIEW` cell.
    witness: tests/test_task.py::test_an_exhausted_package_that_opened_nothing_still_pushes_its_work
    wrong_versions:
      - A refused `EXHAUSTED` package pushes nothing and writes no row of its own.
      - The push runs after a pull request opened too.
      - The row's note carries the push's note alone, so it never says why no pull request opened.
      - The row's note carries PACKAGE's note alone, so it never says the branch was pushed.
      - A `PackageError` in the `EXHAUSTED` mode still raises, so the branch is not pushed and the task exits 2.
      - A `PackageError` is caught for a `READY_FOR_REVIEW` cell too.
      - The push is not told PACKAGE refused, so its commit says PACKAGE never ran.
  - claim: >-
      A stack batch adds a layer only for an outcome in
      `READY_FOR_REVIEW` (`saffron/batch.py:360-364`), so a task that
      stays `EXHAUSTED` adds none, whatever PACKAGE did with it.
      `link_stack` links only the layers' and the finishing layer's pull
      requests (`saffron/finish.py:40-60`), so this task's pull request is
      never linked into the stack.
    witness: tests/test_batch.py::test_a_stack_batch_records_one_layer_for_each_task_that_reached_review
    preserves: true
  - claim: >-
      In the `EXHAUSTED` mode, `package()` reads `head_moved` from
      `rebuttal.json` in the task's directory, and sets the third
      criterion's second keyword exactly when it is `true`. A missing file,
      one that is not JSON, and JSON that is not an object holding the key
      set nothing and raise nothing. Outside the mode, `package()` never
      sets it. The witness opens the pull request six times: with
      `head_moved` true and false, with no file, with a file that is not
      JSON, with a JSON list, and with `head_moved` true outside the mode.
    witness: tests/test_package.py::test_an_exhausted_body_says_when_the_rebuttal_moved_head
    wrong_versions:
      - The record is read outside the `EXHAUSTED` mode too.
      - A missing `rebuttal.json` raises.
      - A `rebuttal.json` that is not JSON raises.
      - A JSON list raises.
      - Any record present reads as moved, `head_moved` false included.
  - claim: >-
      `push_unpackaged_work` takes a keyword, off by default, naming why
      PACKAGE refused the task. Set, its commit says PACKAGE refused it and
      gives that text through `neutralize`, and never says PACKAGE never
      ran. A text in which `find_credentials_in_text` finds a credential is
      left out, and the commit says so. Unset, the commit reads as it does
      today. It refuses to push while another task of the same spec is
      `EXHAUSTED` with a `pr_url`, as it refuses beside a `READY_FOR_REVIEW`
      one. An `EXHAUSTED` row with an empty `pr_url`, a `REJECTED` row with
      a `pr_url`, and another spec's `EXHAUSTED` row with a `pr_url` do not
      stop it. Before any earlier row exists, the witness pushes with a
      keyword holding a mention and a closing keyword, and with one holding
      a credential. Both go through. It then pushes beside each of those
      four earlier rows, adding each row just before its push.
    witness: tests/test_package.py::test_unpackaged_work_after_a_refused_package_says_so_and_spares_a_draft
    wrong_versions:
      - The guard still checks `READY_FOR_REVIEW` alone, so a re-run pushes over an open draft.
      - The guard refuses beside any row with a `pr_url`, so a rejected pull request blocks every later push.
      - The guard refuses beside any `EXHAUSTED` row, a refused package's included.
      - The commit still says PACKAGE never ran when the keyword is set.
      - The commit says PACKAGE refused it without the text.
      - The guard reads every task in the repo, so another spec's open draft blocks this push.
      - The refusal text reaches the commit with its credential in it.
      - A refusal text holding a credential refuses the whole push.
      - The credential text is dropped and the commit does not say so.
      - The refusal text reaches the commit without `neutralize`.
---

## Context

Backlog item **b-038aef**, cited as `DESIGN.md` §5.7. Its sibling is
**b-4c5dc7**. Both came from the spec loop's run 24 on 2026-10-01.

`SA-0162` and `SA-0151` each went green, ran REVIEW and drew blockers.
`SA-0162`'s REVIEW ended "1 blocker(s) — the implementer rebuts", then a
`Budget` event at $57.36 of $37.00, then `EXHAUSTED`. `SA-0151`'s ended "2
blocker(s)", then $30.67 of $25.00, then `EXHAUSTED`. Neither task directory
under `~/.saffron/batches/v0/` holds a `rebuttal.json`, so REBUT never ran.
Each queue row reads `EXHAUSTED` with an empty link and the note `pushed
saffron/SA-0162 @ aa47d09f6381` or `pushed saffron/SA-0151 @ 5fc63c668953`.
The delegate opened #626 and #628 by hand and wrote both bodies without
`saffron/report/pr_body.py`.

After `SA-0203`, neither cell would end this way. Its REBUT runs once past
the budget under a $7.00 cap, and both cells' REBUTs would likely fit it.
A REBUT the cap cuts short still ends `EXHAUSTED` with its blockers
unanswered, and that is the task this spec packages.

The operator decided the scope. A task that ends `EXHAUSTED` in REVIEW or
REBUT with green gates opens a draft pull request whose body names the
unanswered blockers. Its state stays `EXHAUSTED`. Every other `EXHAUSTED`
task opens none, as today. In a stack batch the task still adds no layer
(ADR 7). Its pull request targets the branch it was cut from and is not
linked into the stack.

`DESIGN.md` §5.7 now says so. Its paragraph opens "A task REBUT could not
pay for is packaged too". It was written by hand in this spec's own pull
request.

**The base this spec's cell runs on carries its parents' code.** `SA-0198`
to `SA-0203` are built on `saffron/SA-0203`, which this cell is cut from.
Most line numbers below were read before they landed. So each citation names
its function or test beside its line, and the name is what to follow.

## Problem

**Which `EXHAUSTED` tasks went green?** `_drive_cell` starts REVIEW only on
`READY_FOR_REVIEW` (`saffron/cell/session.py:2613`). So a task that reached
REVIEW had a green gate suite in its cell. Once `SA-0203` lands, five paths
after that end `EXHAUSTED`.

| path | where | gates | review findings | REBUT result |
|---|---|---|---|---|
| the Gate-only cell refuses the patch | `saffron/cell/session.py:2661` | not measured | empty | none |
| the critic cell refuses the patch | `saffron/cell/session.py:2785` | read by no critic | empty | none |
| the cap cuts REBUT short | `saffron/cell/session.py:2917-2921` today | green | an anchored blocker | none |
| red after the rebuttal | `saffron/phases/rebut.py:715-723` | red | an anchored blocker | set |
| the critic cell refuses the post-rebuttal patch | `saffron/phases/rebut.py:731-738` | read by no critic | an anchored blocker | set |

The first three rows sit in `_drive_cell`, the third in its REBUT branch.
The last two sit in `run_rebut`.

The third row is `SA-0203`'s, in `_drive_cell`'s REBUT branch, where it
replaced the old budget refusal. `SA-0203` lets a REBUT that starts past the budget run
once, its sessions sharing a $7.00 cap. When the cap refuses a session and
`run_rebut` would halt at `REBUTTING`, the task ends `EXHAUSTED`. Its
anchored blockers stand, and the outcome carries no `rebut_result`
(`SA-0203`'s fifth criterion and its Problem step 4).

The gates in that row are green either way. Both cases below are in `run_rebut`. A rebuttal that moved no
commit and argued nothing returns before any re-run
(`saffron/phases/rebut.py:710-714`), so HEAD is the tree REVIEW
judged. Any other re-runs the gates first
(`saffron/phases/rebut.py:716-724`). A red re-run ends
`EXHAUSTED` and keeps its `rebut_result`, which `SA-0203` leaves alone, so
it is the fourth row. A green re-run goes on to the verdict, where the cap
can still cut it.

So the patch this spec packages can carry the rebuttal's commits. Teardown
exports it from the implementer's HEAD, whatever REBUT committed
(`saffron/cell/session.py:3126`). PACKAGE re-verifies
every packaged commit in a Gate-only cell of its own
(`saffron/phases/package.py:819-827`). That covers those commits, and a
new failure there opens no pull request. No lens read them, though. §5.5
says the critic reads the patch that ships, and here it read the patch
before the rebuttal. `rebuttal.json` records whether HEAD moved
(`saffron/phases/rebut.py:136-139`). So the body says so whenever it did,
and the operator knows which commits no lens judged.

`reviews` starts empty (`saffron/cell/session.py:2597`). It
is filled only once the critic cell is up
(`saffron/cell/session.py:2727`). `review_state` routes to
REBUT only on an anchored blocker (`saffron/phases/review.py:798-810`). So
the third row is the one shape with an anchored blocker and no
`rebut_result`. A patch no critic read is not packaged. §5.5 makes that
refusal the agent's, so a pull request from it would be a way past the
critic.

**`run_task` packages only `READY_FOR_REVIEW`.** Its one condition is
`saffron/task.py:575`. Every other state goes to `push_unpackaged_work`
(`saffron/task.py:598-608`). That pushes the branch and opens no pull
request (`saffron/phases/package.py:1043-1046`).

**`package()` records two states.** Its refusals record `MERGE_FAILED` at
`saffron/phases/package.py:706`, `saffron/phases/package.py:752`,
`saffron/phases/package.py:768`, `saffron/phases/package.py:856` and
`saffron/phases/package.py:917`. Its pull request records `READY_FOR_REVIEW`
(`saffron/phases/package.py:945`). Each goes through `_finish`
(`saffron/phases/package.py:964-995`), which writes the ledger row and the
queue line.

**The body cannot say why no rebuttal stands.** Take a body with no
`rebut_result`. `_disagreements` renders each anchored blocker with `—` in both the
implementer and critic columns (`saffron/report/pr_body.py:274-347`).
`_not_covered` starts at `saffron/report/pr_body.py:492`. Its one rebuttal
gap is a turn that recorded nothing (`saffron/report/pr_body.py:563-573`).

**The push after a refusal says PACKAGE never ran.** That sentence is
written for every unpackaged push (`saffron/phases/package.py:321-326`). After an `EXHAUSTED` package that
refused, that sentence is false.

**The push guards a pull request only by its state.** It refuses beside
another of the spec's tasks only when that task is `READY_FOR_REVIEW`
(`saffron/phases/package.py:1106-1112`). A task left
`EXHAUSTED` with a draft from this spec's mode would be pushed over by an
attended re-run that ends unpackaged. `tasks_by_repo` already reads each
task's `pr_url` (`saffron/ledger.py:955-971`).

**A stack batch keys its layer on the state alone.** `_is_layer` reads
`CellOutcome.state` (`saffron/batch.py:360-364`). `CellOutcome` carries no
pull request field (`saffron/cell/session.py:313-353`). So the task adds no
layer, and the next candidate's predecessor does not move
(`saffron/batch.py:732-735`).

## Out of scope

- **`reconcile` never reads an `EXHAUSTED` row.** `PR_PENDING_STATES`
  names `READY_FOR_REVIEW`, `APPROVED` and `CHANGES_REQUESTED`
  (`saffron/reconcile.py:49`). So merging this pull request never moves
  the task to `MERGED`. Its dependents stay refused on a dead parent
  (`DEPENDENCY_DEAD_STATES`, `saffron/scheduler.py:104`). The operator
  retires the spec by hand, as for #626 and #628. Two sentences go stale
  and stay, since both files are forbidden here. One is the module
  docstring's account of PACKAGE's last word (`saffron/reconcile.py:1-4`).
  The other is the list of states in `set_task_package`
  (`saffron/ledger.py:1423-1442`).
- **Whether REBUT runs past the budget.** That is **b-4c5dc7**, built by
  `SA-0203`. This spec packages whatever task still ends at the third row
  above.
- **The cut-short rebuttal's own text.** `SA-0203` still writes
  `rebuttal.json` and the ledger's rebuttal rows for it. The outcome
  carries no `rebut_result`, so the body's Disagreements table shows `—`
  for each blocker, and the operator reads `rebuttal.json` for the rest.
- **The pull request's title.** It stays the spec's id and title
  (`saffron/phases/package.py:933`).
- **Exit codes.** `CELL_EXIT` maps the state (`saffron/cli.py:488`), so
  the task still exits 1. A `PackageError` in the new mode is the fourth
  criterion's: the branch is pushed and the task stays `EXHAUSTED`. Only
  a `PackageError` is caught. A `PolicyError` or `GitError` from PACKAGE
  still raises, as it does for a `READY_FOR_REVIEW` cell.
- **The scheduler's view of the open pull request.** `open_pr_refusal`
  reads GitHub's open pull requests (`saffron/scheduler.py:635-705`). A
  spec overlapping this one's files is refused while it is open, as for
  every open pull request.

## Notes for the agent

**Mostly new code.** The keywords, the two lines and the guard's new half
do not exist at base.
Criteria 1 and 2 each pin one mutant on a line the change keeps. The first
is the `parent_branch` argument of the `package()` call in `run_task`
(`saffron/task.py:576-591`). The second is the `pr_url` argument of the
`PackageResult` the pull request path returns
(`saffron/phases/package.py:944-951`). Criteria 3, 4, 6 and 7 declare
none, and `witness` reports `skip` for them. Criterion 5 is `preserves`, and
`saffron/batch.py` is `forbidden`.

**Line numbers predate the parents.** `SA-0198` and `SA-0199` edit
`saffron/task.py`, `saffron/phases/package.py` and `tests/test_task.py`.
`SA-0201` to `SA-0203` edit `saffron/cell/session.py` and
`tests/test_session.py`. All five land before this cell, so find each site
by the function or test named beside it.

**The decision lives in `run_task`.** Make it once, after `run_one_cell`
returns (`saffron/task.py:567-574`). Read `outcome.state`,
`outcome.rebut_result` and `anchored_blockers(outcome.reviews)`. Import
`anchored_blockers` from `saffron.phases.review`, which defines it. Keep one
`package()` call for both shapes. When it returns no `pr_url` in the new
mode, run the existing `push_unpackaged_work` block, and join the two notes
in that row's `note`. Catch `PackageError` around that call only in the new
mode, and treat its text as PACKAGE's note. A `READY_FOR_REVIEW` cell's
error still propagates. Pass the note to `push_unpackaged_work` as the
seventh criterion's keyword, which hands it on to `commit_squash`.

**Reading `head_moved`.** A small helper beside `_finish` reads
`outcome.task_dir / "rebuttal.json"`. It returns `True` only for a JSON
object whose `head_moved` is `True`. It treats `OSError`, `ValueError`,
`KeyError` and `TypeError` as `False`. Call it only in the new mode.

**The guard's new half.** `tasks_by_spec_id` reads no `pr_url`
(`saffron/ledger.py:972-1006`), and `saffron/ledger.py` is forbidden. So
take the spec's rows from `tasks_by_repo` (`saffron/ledger.py:955-971`),
filtered by `spec_id`, and refuse beside one that is `EXHAUSTED` with a
non-empty `pr_url`. Keep the refusal's existing note.

**In `package()`, the keyword picks the two states** each `_finish` call
site records. Pass the third criterion's keyword to `render_pr_body`
(`saffron/phases/package.py:868-891`). Leave every other line of `package()`
as it is. Re-verification, the lease, the credential scans and the base
`open_draft_pr` is given already do what this task needs.

**What criterion 2 leaves to other tests.** Its witness opens an unstacked
pull request. A stacked one takes its base from the `open_draft_pr` call
every package shares (`saffron/phases/package.py:929-936`). For
`READY_FOR_REVIEW`,
`test_a_stacked_child_opens_against_its_parent_applies_onto_it_and_leaves_policy_at_default`
holds it (`tests/test_package.py:2644`). Criterion 1's witness holds that
`run_task` passes the parent in the new mode.

**In `_not_covered`, reuse `blockers`** (`saffron/report/pr_body.py:563`).
It is `anchored_blockers(reviews)`, the list `_disagreements` numbers
(`saffron/report/pr_body.py:290`). Route each `file` through `_cell`
(`saffron/report/pr_body.py:142-153`), as every cell-authored string in the
body is.

**Sentences this change makes false.** Update the module docstring's first
line (`saffron/phases/package.py:1`). Update `push_unpackaged_work`'s first
sentence (`saffron/phases/package.py:1011-1025`) and `run_task`'s first
sentence (`saffron/task.py:434-454`). Update the comment above the
`push_unpackaged_work` call (`saffron/task.py:595-598`). Update the
docstring sentence that says it never pushes beside a `READY_FOR_REVIEW`
row (`saffron/phases/package.py:1037-1038`). Name the new keyword in
`commit_squash`'s (`saffron/phases/package.py:294-319`). Three more go false.
`package()`'s docstring says every `PackageError` reaches `cli.main` and only
`MERGE_FAILED` is recorded. `commit_squash`'s refused-branch text says
"nothing here was re-verified or reviewed", though REVIEW ran and
re-verification ran on a new-failures refusal. `_resolve_stacked_on`'s
docstring says a push of unpackaged work writes `pushed_sha` only when
PACKAGE never ran. And the comment above the push block's row write says
`_finish` never ran, so the row is the task's only one. A refused-branch commit says
PACKAGE refused it and why, and that REVIEW ran.

**Every test you add must fail with this diff's source reverted.** At base
`package()`, `render_pr_body` and `push_unpackaged_work` refuse the new
keywords with a `TypeError`. And `run_task` sends the `EXHAUSTED` cell to the push. Pass
the new keyword at run time, never at module scope.

**Criterion 1's witness.** `_drive` (`tests/test_task.py:29-95`) passes no
handoff, so write a sibling helper. It replaces `run_one_cell`,
`package_phase.package` and `package_phase.push_unpackaged_work`. It calls
`run_task` with a `Handoff` whose `target_branch` is `saffron/TE-8`, as
`test_a_handoff_replaces_the_stacking_resolver` does
(`tests/test_task.py:520-600`). Give each cell its own `task_id` and
ledger file. Build the red `rebut_result` as a `RebutResult` in
`EXHAUSTED` around an empty `RebuttalTurn`. For each cell, assert whether
`package()` ran, with which keyword and `parent_branch`, and whether the
push ran. Bind loop values as default arguments in the fakes, or ruff's
B023 fails `lint`.

**Criterion 2's witness.** One `packageable` fixture
(`tests/test_package.py:904-1008`) can drive all eight paths in turn. First
set `outcome.state`, an anchored blocker in `outcome.reviews`, and the
ledger state, all to `EXHAUSTED`. After each call, assert the state in the
result, in `_state` and in `_queue_json_row` (`tests/test_package.py:1011-1030`).
The single-path tests in `tests/test_package.py` show each setup.

- Subjects: `outcome.agent_subjects` carrying `FAKE_KEY`, as `tests/test_package.py:1790-1812` does.
- Body: a blocker whose claim carries `FAKE_KEY`, as `tests/test_package.py:1814-1851` does.
- New failures: a `reverify` returning one `NewFailure`, as `tests/test_package.py:1654-1684` does, inside `monkeypatch.context()`.
- Moved branch: push `cell` to the task's branch and stub `remote_sha` to `""`, as `tests/test_package.py:1556-1584` does.
- Gone parent: point the `tree_base` in `patch.json` at the `cell` head, which `main` does not contain. Stub `fetch_parent_branch` to raise `ParentGone`, pass `parent_branch`, then restore `patch.json`.
- Pull request: a fake `gh` that prints a URL, as `tests/test_package.py:1221-1251` does. `_recording_gh` prints none, and `open_draft_pr` raises on that.
- Patch credential: commit a key on `cell` and rewrite `patch.diff`, as `tests/test_package.py:1745-1778` does, then restore it.
- Conflict, last: commit a different line 3 to `main` and push it.

**Criterion 3's witness.** `_finding` (`tests/test_report.py:711-722`)
builds each finding, and it defaults every one to `a.py:3`. Give the four
findings distinct places, none a prefix of another, such as `a.py:3`,
`b.py:17`, `c.py:29` and `d.py:41`. Shared or prefixed places let the wrong
versions that name a concern or only the first blocker pass. Give one anchored
blocker the file `a|b.py`, and expect the escaped form `_cell` writes. Split the body at `## Not covered` and assert on the
second half only. Check the two quoted phrases, and each anchored blocker's
`file:line`. Check that neither the unanchored blocker's nor the concern's
appears, nor the word `unanswered`. Render once more with both keywords and
check the HEAD line's two phrases. Check that neither line renders unset.

**Criterion 4's witness.** Reuse criterion 1's helper. A refusing fake
returns a `PackageResult` in `EXHAUSTED` whose note says it conflicts. An
opening fake writes its own row with `append_queue_line` and returns a
`pr_url`, as `tests/test_task.py:211-262` does. A raising fake raises
`PackageError`. Record each push's state and its new keyword. Assert the
pushes, the one row's state, link and note, and the returned state. Last,
run a `READY_FOR_REVIEW` cell through the raising fake inside
`pytest.raises`, and assert no push ran.

**Criterion 6's witness.** One `packageable` fixture opens the pull request
six times with a fake `gh` that prints a URL. Before each, write or remove
`rebuttal.json` in `outcome.task_dir`. After each, read `pr_body.md` and
look for "HEAD moved after REVIEW" in its `## Not covered` half.

**Criterion 7's witness.** One `packageable` fixture, and two phases.
First, with no earlier row, push with the keyword `"conflicts; Fixes #1
@someone"`. Read the commit with `git log -1 --format=%B` on the remote
branch, as `tests/test_package.py:3112-3131` does. It holds `neutralize`'s
form of that text and not the raw one. Push again with a keyword holding
`FAKE_KEY`. Assert `pushed` is true, the key is not in the commit, and the
commit says the text was left out. Second, build each earlier row with
`create_run`, `create_task` and `set_task_package`. Add it right before the
push beside it. Record the remote head as its `pushed_sha`, so only the
guard decides. `tasks_by_repo` returns every task in the repo, so one row
sits under another spec. In order: the `REJECTED` row, the empty-`pr_url`
`EXHAUSTED` row, the other spec's drafted row, then this spec's drafted one.
Assert `PushResult.pushed` is true for the first three and false for the
last. Compare `pushed`, never the remote head: two pushes of one tree inside
a second can make the same squash commit.
