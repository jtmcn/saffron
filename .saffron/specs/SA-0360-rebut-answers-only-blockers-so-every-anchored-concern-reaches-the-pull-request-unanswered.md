---
id: SA-0360
title: REBUT answers only blockers, so every anchored concern reaches the pull request unanswered
type: bug
priority: 2
estimated_lines: 123
estimate_measured: true
touches:
  - saffron/phases/rebut.py
  - saffron/phases/review.py
  - saffron/cell/session.py
  - saffron/report/pr_body.py
  - saffron/agents/prompts/turns/rebut.md
  - saffron/agents/prompts/turns/rebut-extract.md
  - saffron/agents/prompts/turns/rebut-concerns.md
  - tests/test_rebut.py
  - tests/test_report.py
  - tests/test_session.py
  - tests/test_context.py
  - tests/test_agent_runner.py
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
  - hooks/**
  - saffron/ledger.py
  - saffron/task.py
  - saffron/end_review.py
  - saffron/scheduler.py
  - saffron/record/**
  - saffron/gates/**
  - saffron/phases/implement.py
  - saffron/phases/package.py
  - tests/test_task.py
  - tests/test_ledger.py
  - tests/test_scheduler.py
budget_usd: 60
max_attempts: 3
max_turns: 300
risk: standard
acceptance:
  - claim: >-
      `run_rebut` takes a required `concerns` list. The rebuttal turn's prompt
      lists every blocker numbered from 1, then a concerns paragraph, then
      every concern numbered on from the last blocker. The witness drives two
      blockers of two lenses and two concerns. One concern shares a blocker's
      lens and one has a lens no blocker has. No verdict session is shown a
      concern or a concern's answer, while each is shown its own blocker and
      that blocker's answer. `RebutResult.as_dict` lists each concern under
      `concerns` by its number. With no concern, the prompt carries no
      concerns paragraph.
    witness: tests/test_rebut.py::test_each_anchored_concern_reaches_the_rebuttal_turn_numbered_after_the_blockers
    wrong_versions:
      - Concerns are numbered from 1, so a concern shares a blocker's number.
      - The concerns are listed ahead of the blockers in the prompt.
      - A lens's verdict session is asked about the concerns that lens raised as well as its blockers.
      - The verdict prompt shows every rebuttal entry, a concern's answer included.
      - Only the first concern is handed to the rebuttal turn.
      - The concerns paragraph is sent with an empty list when there is no concern.
      - "`as_dict` numbers the concerns from 1 under `concerns`."
  - claim: >-
      A concern's rebuttal entry counts neither as an argument nor as a
      claimed fix toward the state `run_rebut` reaches or its line. HEAD
      stays one measurement for the whole rebuttal. The witness drives five
      shapes. The first three run twice, the second answer once a blocker's
      and once a concern's. The fourth and fifth run with a concern alone. A claimed blocker fix with no commit
      beside an argued concern ends `REBUTTAL_UNJUDGED`, claiming a fix for 1
      blocker, with no gate re-run and no critic cell. An argued blocker that
      is confirmed beside an argued concern counts 1 argued. An argued
      blocker beside a concern claimed fixed with no commit carries no
      claimed-fix clause. A concern fix that moves HEAD, with no blocker
      answered, is still re-gated, and a red re-run ends `EXHAUSTED`. A turn
      that argued only a concern and moved nothing ends `REBUTTAL_UNJUDGED`,
      and its line says the rebuttal answered no blocker. The same turn with
      no concern removed, an empty turn, still says it recorded nothing.
    witness: tests/test_rebut.py::test_a_concerns_answer_never_changes_the_state_rebut_reaches
    wrong_versions:
      - "`rebut_state` and the early return both count every rebuttal entry, a concern's included."
      - The early return counts blocker answers only, and the final `rebut_state` call is handed every entry.
      - The final `rebut_state` call counts blocker answers only, and the early return counts every entry.
      - A turn that answered no blocker returns early even when HEAD moved, so a concern's commit is never re-gated.
      - The early return's `rebut_state` call is handed every entry, so its line counts a concern's claimed fix.
      - A turn that answered only concerns keeps today's line, which says the rebuttal recorded nothing.
      - Every empty turn's line says it answered no blocker, though no concern entry was removed.
  - claim: >-
      The pull request body gains a `### Concern answers` table after
      `### Disagreements`, one row per anchored concern, numbered after the
      blockers, with no critic column. The witness drives a concern answered
      `fixed`, one answered `argued`, one left unanswered, and a duplicate
      answer, where the first answer stands. An unanchored concern and an
      anchored note get no row, and the disagreements table keeps the blocker
      alone. A turn nobody could read gives every row the fixed sentence and
      never its error. With no `RebutResult`, or no anchored concern, the
      table is absent.
    witness: tests/test_report.py::test_the_pull_request_body_shows_each_concerns_answer_under_its_number
    wrong_versions:
      - The rows are numbered from 1 rather than after the blockers.
      - The last answer to a duplicated number stands rather than the first.
      - An unanchored concern gets a row.
      - An anchored note gets a row.
      - A turn nobody could read quotes its error in each row.
      - The concerns are added to the disagreements table as well.
      - A turn nobody could read leaves each row with the mark for no answer.
      - The table renders from the reviews alone when no `RebutResult` exists.
      - A row shows the argument without its action.
  - claim: >-
      In a whole cell, REBUT hands the rebuttal turn each anchored concern
      REVIEW filed, numbered after the blockers. Neither a note nor an
      unanchored concern reaches it. The concern's answer lands on its own
      ledger row with no verdict, and `rebuttal.json` lists the concern under
      `concerns`. The witness drives the three answers item 42 names. A
      concern answered `fixed` reads `answered` and carries its argument.
      A readable turn that left it out reads `unanswered`. An unreadable turn
      gives it `unread` with that turn's error.
    witness: tests/test_session.py::test_rebut_hands_each_anchored_concern_to_the_rebuttal_and_records_its_answer
    wrong_versions:
      - "`session.py` passes `run_rebut` an empty `concerns` list."
      - The ledger loop records the blockers alone, so a concern's row keeps no answer.
      - The answer filter keeps numbers up to the blocker count, so a concern's argument is dropped.
      - "`blocker_answers` is asked about the blockers alone, so a concern's row records no answer."
      - "`rebuttal.json` is written from `as_dict(blockers)`, with no concerns."
      - An unanchored concern is handed to the rebuttal turn too.
      - An anchored note is handed to the rebuttal turn too.
---

## Context

Backlog item **b-31e3c8**. It cites `DESIGN.md` §5.6. Every line below was read
at `e537e5ca`.

`DESIGN.md` §5.6's first paragraph reads, as amended in this spec's own pull
request: "The implementer session resumes and gets the confirmed blockers, then
each anchored concern numbered after them. **One** attempt to either fix each
or argue the finding is wrong. Both outcomes recorded. Gates re-run. A
concern's answer is recorded, and the pull request shows it whenever REBUT's
result stands. No lens verdicts it." `CONTEXT.md`'s **Rebuttal** opens, as amended there: "The
implementer's single response to confirmed blockers, and to each anchored
concern beside them: either a fix or an argument that the finding is wrong."

**What REBUT is handed today.** `session.py` enters REBUT only on
`REBUTTING` (`saffron/cell/session.py:3432`). It selects
`review.anchored_blockers(reviews)` (`saffron/cell/session.py:3436`), which
keeps anchored blockers and host-filed survivors, in order
(`saffron/phases/review.py:956-972`). `review_state` routes to `REBUTTING`
only when that list is not empty (`saffron/phases/review.py:1064-1068`).
`review.anchored_concerns` counts anchored concerns and returns an int
(`saffron/phases/review.py:1032-1038`).

**How REBUT numbers and answers.** `run_rebut` numbers the blockers from 1
(`saffron/phases/rebut.py:823`). `run_rebuttal` fills the `{blockers}` slot of
`REBUT_PROMPT` with `blocker_lines` (`saffron/phases/rebut.py:251`). The prompt
is `saffron/agents/prompts/turns/rebut.md`. `rebut-extract.md` asks for one
`rebuttals` entry per blocker. `Rebuttal.finding` is an int
(`saffron/phases/rebut.py:47`).

**What reads those numbers.** `rebut_state` counts `argued` and `fixed` over
every rebuttal entry (`saffron/phases/rebut.py:587-588`). The early return in
`run_rebut` asks the same of every entry (`saffron/phases/rebut.py:860`).
`verdict_prompt` shows a lens only the arguments whose number is one of its own
blockers (`saffron/phases/rebut.py:365-370`). The verdict loop starts one agent
session per lens that raised a blocker (`saffron/phases/rebut.py:894-897`).
`blocker_answers` maps the numbers 1 to its count
(`saffron/phases/rebut.py:660-671`). `session.py` keeps answers numbered 1 to
`len(blockers)` (`saffron/cell/session.py:3738-3742`). It writes one ledger
rebuttal fact per blocker (`saffron/cell/session.py:3747-3755`), through
`Ledger.record_rebuttal` (`saffron/ledger.py:2181-2214`). It writes
`rebuttal.json` from `result.as_dict(blockers)`
(`saffron/cell/session.py:3725-3727`). `as_dict` lists `blockers` by number
(`saffron/phases/rebut.py:140-168`).

**The pull request body.** `render_pr_body` places `_disagreements` after the
new failures (`saffron/report/pr_body.py:122`). `_disagreements` numbers
`anchored_blockers(reviews)` from 1 and looks each answer up through
`first_answers` (`saffron/report/pr_body.py:311-384`). For a turn whose
`error` is set, every row carries one fixed sentence and never the error
(`saffron/report/pr_body.py:339-358`). `_NONE_MARK` is the
mark for no answer (`saffron/report/pr_body.py:51`).

## Problem

In spec loop iterations 55, 56 and 57, each batch left an in-cell concern
standing after REBUT. In iteration 57 they were `SA-0343`'s bare "pool" and
`SA-0356`'s "missed layer". Both pull request seats raised every one again. Each was a true
one-line fix inside `touches`, and the delegate made it by hand. REBUT never
saw them, because nothing hands it a concern.

1. **The selection.** Add `review.rebut_concerns(reviews)`. It returns every
   finding whose severity is `concern` and that is `anchored`, in review
   order. It is the one rule `session.py` and `pr_body.py` share, as
   `anchored_blockers` is for blockers.
2. **The prompt.** `run_rebut` takes a required `concerns` list and numbers it
   on from the last blocker. The rebuttal turn's prompt lists the blockers,
   then a concerns paragraph and the concern lines in `blocker_lines`' format.
   The paragraph lives in a new turn prompt,
   `saffron/agents/prompts/turns/rebut-concerns.md`, loaded with
   `context.turn_prompt` as `rebut.CONCERNS_PROMPT`. It carries a
   `{concerns}` slot. `rebut.md` gains a `{concerns}` slot after
   `{blockers}`, filled with the empty string when there is no concern. The
   paragraph says a concern is answered as a blocker is, that no critic
   judges the answer, and that the pull request shows it. `rebut-extract.md`
   asks for one entry per blocker and one per concern. Keep its sentence
   naming the pull request's disagreements table, and say a concern's argument
   appears in its concern answers table.
3. **The state.** The early return in `run_rebut` and both `rebut_state`
   calls count blocker answers only. Hand them the turn with every entry
   numbered as a concern removed. `rebut_state`'s signature stays as it is.
   The turn on `RebutResult.rebuttal` keeps every entry. `moved` stays one
   bit for the whole rebuttal (`saffron/phases/rebut.py:754-756`). So a
   concern's commit moves HEAD, and the gates judge it as they judge any
   commit. A red result ends `EXHAUSTED`. Today a turn with no commit and no
   argument ends `REBUTTAL_UNJUDGED` with a line ending "recorded nothing"
   (`saffron/phases/rebut.py:589-597`). When the filter removed a concern
   entry and left no blocker answer, that line is false. Say instead that the
   rebuttal moved no commit and answered no blocker. A turn that recorded no
   entry at all keeps today's line.
4. **The record.** `as_dict` takes the concerns as a second argument and lists
   them under a new `concerns` key, each with its number. In `session.py`,
   select the concerns beside the blockers and pass them to `run_rebut`. Keep
   answers numbered up to the blocker count plus the concern count. Ask
   `blocker_answers` about that total. Record a rebuttal fact for each concern
   after the blockers' facts, through the same `record_rebuttal` call, whose
   verdict is always `None`.
5. **The body.** Add `_concern_answers(reviews, rebut_result)` to
   `pr_body.py`, rendered right after `_disagreements`. Its heading is
   `### Concern answers`, and its columns are `#`, `lens`, `where`, `claim` and
   `implementer`. It numbers `rebut_concerns(reviews)` on from
   `len(anchored_blockers(reviews))`. Each row shows the first answer as
   `action: argument`, or `_NONE_MARK` when none stands. An errored turn gives
   every row the sentence `_disagreements` uses, without the HEAD clause, and
   never the error. It returns the empty string with no `RebutResult` or no
   anchored concern.

## Out of scope

- A task whose REVIEW raised concerns and no blocker. It does not enter REBUT,
  so its concerns reach the pull request unanswered, as today. The operator
  settled that concerns ride a REBUT that blockers start.
- A note. No note is handed to REBUT.
- A rebuttal that answers only a concern and commits its fix. HEAD moved, so
  it passes the early return and reaches the gates and the verdicts. `moved`
  cannot say which answer a commit was for.
- A verdict on a concern. No lens verdicts one, so the verdict sessions, the
  contradiction check, the withdrawal guard and the disagreements table see
  blockers alone.
- REBUT's cap and reserves (`DESIGN.md` §5.6). They stay as they are.
- The end review's known block. `_known_line` shows a rebuttal only beside a
  verdict (`saffron/end_review.py:83-89`), so a concern's answer stays out of
  it.
- `_not_covered`'s closing line, which says every finding reached the
  implementer (`saffron/report/pr_body.py:652-656`). A concern-only review
  makes it false, as it is false today.
- The queue's `unread` and `unanswered` counts. They stay per blocker
  (`saffron/cell/session.py:3721-3722`).
- Readers outside `touches` that need no change. `_left_by_critic` reads each
  finding row's verdict, which stays `None` for a concern
  (`saffron/finish.py:309-330`). The queue's concern count stays
  `anchored_concerns` (`saffron/phases/review.py:1032-1038`).

## Notes for the agent

**Edit or new.** Every criterion pins new code: a new parameter, a new
function, a new table and a widened range whose spelling is the cell's. So no
criterion declares a mutant, and `witness` reports an honest `skip` on each.

**Readers that need no edit.** `saffron package` rebuilds the turn from
`rebuttal.json`'s `rebuttal.rebuttals` (`saffron/task.py:1175-1199`), which
holds every entry. So its body renders the concern answers with no edit to
`task.py`. The ledger's fold writes any rebuttal fact onto its finding's row
by position (`saffron/ledger.py:1126-1134`).

**Existing tests this changes.** A full prototype of this change, with the
witnesses below, left these files green: `tests/test_rebut.py`,
`tests/test_report.py`, `tests/test_context.py`, `tests/test_session.py`,
`tests/test_task.py`, `tests/test_review.py`, `tests/test_package.py`,
`tests/test_agent_runner.py`, `tests/test_events.py` and
`tests/test_prose_gate.py`. It made these edits to existing tests.

- `_run` in `tests/test_rebut.py` (`tests/test_rebut.py:442-489`) takes a
  `concerns` argument, empty by default, and passes it on.
- The `run_rebut` calls at `tests/test_agent_runner.py:851` and
  `tests/test_events.py:2619` pass `concerns=[]`.
- `TURN_PROMPTS` in `tests/test_context.py:689-704` gains `rebut-concerns`.
  `test_a_loaded_turn_prompt_keeps_no_unfilled_slot`
  (`tests/test_context.py:722-728`) expects `{blockers}` and `{concerns}` in
  `rebut`, and `{concerns}` in `rebut-concerns`.
  `test_the_rebuttal_prompt_still_formats_its_blockers`
  (`tests/test_context.py:749-753`) passes `concerns=""` to `.format`.

**Comments that turn stale.** `blocker_answers`, `BlockerAnswer` and their
docstring speak of blockers alone (`saffron/phases/rebut.py:657-671`), and so
does `first_answers`' docstring (`saffron/phases/rebut.py:641-650`). The
comment at `saffron/cell/session.py:3728-3730` says each answer is keyed by
the blocker's number. Each now covers concerns too, so reword each. Renaming
the function is your choice.

`_rebuttal_fixed_prefix` in `tests/test_session.py:5151-5155` splits
`REBUT_PROMPT` on `{blockers}`, so the `{concerns}` slot goes after it.

**The witnesses.** Use plain `def`s, never a parametrised test.

- In `tests/test_rebut.py`, drive `_run` with a `record` list and read each
  call's `prompt` and its `options["system_prompt"]`. Give one concern the
  lens of a blocker, or a leak to that lens's verdict session goes unseen.
  For criterion 2, drive each shape twice. Once the second finding is a blocker
  and once a concern, so the witness sees the arrangement change the state.
- In `tests/test_report.py`, build the `RebutResult` by hand, as
  `test_disagreement_rows_attribute_the_right_rebuttal_to_the_right_blocker`
  does, and compare the table's rows whole.
- In `tests/test_session.py`, drive a cell through `_stub_the_runtime`,
  `_rebuttable` and `_drive`. One lens files a blocker, a concern and a note
  on `src/x.py` line 1, which `_ANCHORING_DIFF` changes. It also files a
  concern on a line the diff does not change. Read the rows from `ledger.findings(task_id)`.

**Every new test fails with the source reverted.** On the prototype, all four
witnesses failed with `saffron/` reverted. Each wrong version listed above
failed its own witness there.

**Size.** The prototype measured 491 changed tokens by `size_gate` outside the
test paths, against the `bug` ceiling of 1300. It measured 1457 more under
them. `estimated_lines` is the first figure over four. The diff touches
`saffron/cell/session.py`, which `elevate_on` names, so `size` blocks.
