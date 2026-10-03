---
id: SA-0204
title: An EXHAUSTED task whose gates went green opens no pull request
type: feature
priority: 2
depends_on: [SA-0203, SA-0198]
estimated_lines: 287
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
      `render_pr_body` takes a keyword, off by default. Set, `## Not
      covered` carries one line that says, with `EXHAUSTED` in backticks,
      that the task ended `EXHAUSTED` before REBUT ran. The line names the
      `file:line` of each finding `anchored_blockers` returns, and of no
      other finding. Unset, no such line renders, even beside anchored
      blockers and no `rebut_result`. The witness renders two anchored
      blockers from two lenses beside an unanchored blocker and an
      anchored concern, once set and once unset.
    witness: tests/test_report.py::test_an_unrebutted_body_names_every_blocker_it_left_standing
    wrong_versions:
      - The line names only the first anchored blocker.
      - The line renders whenever anchored blockers stand with no `rebut_result`, keyword or not.
      - The line names an unanchored blocker too.
      - The line names every anchored finding, a concern included.
  - claim: >-
      When `package()` in the `EXHAUSTED` mode returns no `pr_url`,
      `run_task` then calls `push_unpackaged_work` as it does for any
      `EXHAUSTED` task. The task's one queue row stays `EXHAUSTED` with an
      empty link, and its note carries PACKAGE's note and the push's note
      both. When `package()` returns a `pr_url`, no push runs and the row
      is the one PACKAGE wrote. `run_task` returns the outcome in
      `EXHAUSTED` either way. The witness drives a refusal and a pull
      request.
    witness: tests/test_task.py::test_an_exhausted_package_that_opened_nothing_still_pushes_its_work
    wrong_versions:
      - A refused `EXHAUSTED` package pushes nothing and writes no row of its own.
      - The push runs after a pull request opened too.
      - The row's note carries the push's note alone, so it never says why no pull request opened.
      - The row's note carries PACKAGE's note alone, so it never says the branch was pushed.
  - claim: >-
      A stack batch adds a layer only for an outcome in
      `READY_FOR_REVIEW` (`saffron/batch.py:360-364`), so a task that
      stays `EXHAUSTED` adds none, whatever PACKAGE did with it.
      `link_stack` links only the layers' and the finishing layer's pull
      requests (`saffron/finish.py:40-60`), so this task's pull request is
      never linked into the stack.
    witness: tests/test_batch.py::test_a_stack_batch_records_one_layer_for_each_task_that_reached_review
    preserves: true
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

The operator decided the scope. A task that ends `EXHAUSTED` in REVIEW or
REBUT with green gates opens a draft pull request whose body names the
unanswered blockers. Its state stays `EXHAUSTED`. Every other `EXHAUSTED`
task opens none, as today. In a stack batch the task still adds no layer
(ADR 7). Its pull request targets the branch it was cut from and is not
linked into the stack.

`DESIGN.md` §5.7 now says so. Its paragraph opens "A task REBUT could not
pay for is packaged too". It was written by hand in this spec's own pull
request.

## Problem

**Which `EXHAUSTED` tasks went green?** `_drive_cell` starts REVIEW only on
`READY_FOR_REVIEW` (`saffron/cell/session.py:2613`). So a task that reached
REVIEW had a green gate suite in its cell. Five paths after that end
`EXHAUSTED`.

| path | where | gates | review findings | REBUT result |
|---|---|---|---|---|
| the Gate-only cell refuses the patch | `saffron/cell/session.py:2661` | not measured | empty | none |
| the critic cell refuses the patch | `saffron/cell/session.py:2785` | read by no critic | empty | none |
| REBUT refused on budget | `saffron/cell/session.py:2920-2921` | green | an anchored blocker | none |
| red after the rebuttal | `saffron/phases/rebut.py:715-723` | red | an anchored blocker | set |
| the critic cell refuses the post-rebuttal patch | `saffron/phases/rebut.py:731-738` | read by no critic | an anchored blocker | set |

`reviews` starts empty (`saffron/cell/session.py:2597`). It is filled only
once the critic cell is up (`saffron/cell/session.py:2727`). `review_state`
routes to REBUT only on an anchored blocker
(`saffron/phases/review.py:798-810`). So the third row is the one shape with
an anchored blocker and no `rebut_result`, and both measured cells took it.
A patch no critic read is not packaged. §5.5 makes that refusal the
agent's, so a pull request from it would be a way past the critic.

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
- **Whether REBUT runs past the budget.** That is **b-4c5dc7**. This spec
  packages whatever task still ends at the third row above.
- **The pull request's title.** It stays the spec's id and title
  (`saffron/phases/package.py:933`).
- **Exit codes.** `CELL_EXIT` maps the state (`saffron/cli.py:488`), so
  the task still exits 1. A `PackageError` raised in the new mode reaches
  `cli.main` as exit 2, as one from a `READY_FOR_REVIEW` cell does.
- **The scheduler's view of the open pull request.** `open_pr_refusal`
  reads GitHub's open pull requests (`saffron/scheduler.py:635-705`). A
  spec overlapping this one's files is refused while it is open, as for
  every open pull request.

## Notes for the agent

**Mostly new code.** The two keywords and the line do not exist at base.
Criteria 1 and 2 each pin one mutant on a line the change keeps. The first
is the `parent_branch` argument of the `package()` call in `run_task`
(`saffron/task.py:576-591`). The second is the `pr_url` argument of the
`PackageResult` the pull request path returns
(`saffron/phases/package.py:944-951`). Criteria 3 and 4 declare none, and
`witness` reports `skip` for them. Criterion 5 is `preserves`, and
`saffron/batch.py` is `forbidden`.

**Line numbers are at this spec's base.** `SA-0198` and `SA-0199` edit
`saffron/task.py`, `saffron/phases/package.py` and `tests/test_task.py`
first, so find each site by its function.

**The decision lives in `run_task`.** Make it once, after `run_one_cell`
returns (`saffron/task.py:567-574`). Read `outcome.state`,
`outcome.rebut_result` and `anchored_blockers(outcome.reviews)`. Import
`anchored_blockers` from `saffron.phases.review`, which defines it. Keep one
`package()` call for both shapes. When it returns no `pr_url` in the new
mode, run the existing `push_unpackaged_work` block, and join the two notes
in that row's `note`.

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
`push_unpackaged_work` call (`saffron/task.py:595-598`).

**Every test you add must fail with this diff's source reverted.** At base
`package()` and `render_pr_body` refuse the new keyword with a
`TypeError`. And `run_task` sends the `EXHAUSTED` cell to the push. Pass
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
builds each finding. Split the body at `## Not covered` and assert on the
second half only. Check `EXHAUSTED` in backticks and each anchored
blocker's `file:line`. Check that neither the unanchored blocker's nor the
concern's appears.

**Criterion 4's witness.** Reuse criterion 1's helper. A refusing fake
returns a `PackageResult` in `EXHAUSTED` whose note says it conflicts. An
opening fake writes its own row with `append_queue_line` and returns a
`pr_url`, as `tests/test_task.py:211-262` does. Assert the pushes, the one
row's state, link and note, and the returned state.
