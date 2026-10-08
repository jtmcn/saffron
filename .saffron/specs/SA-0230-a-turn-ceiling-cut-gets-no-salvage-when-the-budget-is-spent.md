---
id: SA-0230
title: An IMPLEMENT turn cut with nothing committed gets no salvage turn once the budget is spent, so its work dies with the cell
type: bug
priority: 1
depends_on: []
estimated_lines: 230
estimate_measured: true
touches:
  - saffron/cell/session.py
  - saffron/events.py
  - saffron/phases/implement.py
  - tests/test_session.py
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
  - saffron/spec_review.py
  - saffron/end_review.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/reconcile.py
  - saffron/report/**
  - saffron/record/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/repos/**
  - saffron/cell/runtime.py
  - saffron/cell/worktree.py
  - saffron/phases/package.py
  - saffron/phases/review.py
  - saffron/phases/rebut.py
  - tests/test_implement.py
  - tests/test_events.py
  - tests/test_rebut.py
  - tests/test_review.py
  - tests/test_scheduler.py
budget_usd: 22
max_attempts: 3
max_turns: 130
acceptance:
  - claim: >-
      The IMPLEMENT turn runs under its own `max_budget_usd`, the budget less
      the plan turn's spend, less `SALVAGE_RESERVE_USD`, which is $1.00. Where
      that remainder is $1.00 or less, the turn gets the whole remainder. The
      plan turn and the REPAIR turn after it keep the task's `budget_usd`.
      The witness drives three cells, each with one REPAIR turn. An $8 budget
      after a $3.79 plan turn caps the IMPLEMENT turn at $3.21. A $2 budget
      after a $1.00 plan turn caps it at $1.00. A $1 budget after a $0.50
      plan turn caps it at $0.50. Today all three IMPLEMENT turns get the
      whole budget.
    witness: tests/test_session.py::test_the_implement_turn_keeps_the_salvage_reserve_out_of_its_cap
    wrong_versions:
      - The cap is the budget less the reserve, ignoring the plan turn, so the $8 cell gets $7.00.
      - The cap is the whole remainder with no reserve, so the $8 cell gets $4.21.
      - The reserve comes off every remainder, so the $2 cell gets $0.00 and the $1 cell a negative cap.
      - The reserve comes off a remainder equal to it, so the $2 cell gets $0.00.
      - The capped dict replaces the shared one, so the REPAIR turn after it is also capped at $3.21.
      - The reserve comes off the shared options dict, so the plan and REPAIR turns of the $8 cell get $7.00.
  - claim: >-
      An IMPLEMENT turn that its own budget cap cuts with nothing committed
      earns the salvage turn, as a turn-ceiling cut and a wall cut do. Its
      result reports the subtype `error_max_budget_usd`. The watch line that
      announces its salvage turn contains "budget", and neither "turn
      ceiling" nor "wall". Every salvage turn, whichever of the three bounds
      earned it, runs under a `max_budget_usd` of the reserve, $1.00. A
      budget-cap cut whose salvage turn recovers nothing ends `ORPHANED`, as
      the other two cuts do on their first time at a `spec_sha`. The witness
      drives SA-0087's shape, an $8 budget and a $3.79 plan turn, through
      four cells. The cap cuts one IMPLEMENT turn at $3.25. The turn ceiling
      cuts another and the wall clock a third, each at $3.00. All three
      salvage turns commit, and all three tasks reach `READY_FOR_REVIEW`. A
      fourth cell's cap cut is followed by a salvage turn that commits
      nothing. Today the cap cut ends `NOT_IMPLEMENTED` after two turns.
    witness: tests/test_session.py::test_an_implement_turn_its_budget_cap_cuts_is_salvaged_on_the_reserve
    wrong_versions:
      - A budget-cap cut is not a bound, so it ends `NOT_IMPLEMENTED` with no salvage turn.
      - The salvage turn keeps the whole budget as its cap, $8.00.
      - The salvage turn's cap is what the budget has left, $0.96 after the cap cut.
      - Only the budget-cap cut's salvage turn runs on the reserve, so the turn-ceiling and wall salvage turns keep $8.00.
      - A budget-cap cut salvages, but its failed salvage ends `NOT_IMPLEMENTED` rather than `ORPHANED`.
      - The announcing line names the wall clock for a budget-cap cut.
  - claim: >-
      An IMPLEMENT turn cut with nothing committed and no budget left for a
      salvage turn still gets the host checkpoint. This holds for each of
      the three bounds that earn a salvage turn. A dirty tree is committed by
      the host, the commits are measured again, and a commit carries the
      task on to GATE with no salvage turn. Its watch lines then say the host
      checkpointed the work and recovered 1 commit, and none says "no room
      left to salvage". On a turn-ceiling cut, a checkpoint the repo's hook
      refuses is reported, not raised, and the task ends `ORPHANED` as today.
      The witness drives a
      $12 budget whose IMPLEMENT turn spends $12.00 and is cut by the turn
      ceiling, the wall clock or its own cap, one cell each. With green gates
      each ends `READY_FOR_REVIEW`. A fourth cell, cut by the turn ceiling,
      has a checkpoint that raises `CellRuntimeError`. Today no cell takes a
      checkpoint. The turn-ceiling and wall cells end `ORPHANED`, and the cap
      cell ends `NOT_IMPLEMENTED`.
    witness: tests/test_session.py::test_a_cut_with_no_room_left_still_takes_the_host_checkpoint
    wrong_versions:
      - The no-room branch takes no checkpoint.
      - The checkpoint runs, but the commits are not measured again, so the task still ends `ORPHANED`.
      - The checkpoint runs only for a turn-ceiling cut.
      - A refused checkpoint's `CellRuntimeError` escapes the no-room branch.
  - claim: >-
      A turn-ceiling cut and a wall cut with no budget left and a clean tree
      still end `ORPHANED` after two turns, and the line refusing the
      salvage turn names the bound that cut each.
    witness: tests/test_session.py::test_every_cut_that_leaves_nothing_committed_halts_for_the_next_scan
    preserves: true
---

## Context

Backlog item **119**, tier 1, found running the spec loop on 2026-09-14. It
cites `DESIGN.md` §4.3, whose spend row and "A timeout must never discard
committed work" this change serves. §4.5's `ORPHANED` paragraph names the
salvage turn. Read at base `958db033`.

**What the budget does to the salvage turn today.** `_drive_cell` builds one
options dict for the task, with `budget_usd=spec.budget_usd`
(`saffron/cell/session.py:2089-2094`). `agent_options` writes that as
`max_budget_usd`, a per-turn cap enforced inside the cell
(`saffron/phases/implement.py:185-188`). Every turn of the task passes
that dict. That covers the plan turn
(`saffron/cell/session.py:2138-2140`), the IMPLEMENT turn
(`saffron/cell/session.py:2317`), each REPAIR turn
(`saffron/cell/session.py:2597`), the notes turn
(`saffron/cell/session.py:2667`) and REBUT
(`saffron/cell/session.py:3080`). `_over_budget` holds the host's running
sum against the budget (`saffron/cell/session.py:2280-2295`). The turn
ceiling or the wall clock can cut the IMPLEMENT turn with zero commits
(`saffron/cell/session.py:2352-2357`). The salvage turn is then refused if
`_over_budget()` is true (`saffron/cell/session.py:2364-2376`). That emits
`cut_off_no_salvage_room` and nothing else. The host checkpoint,
`worktree.commit_dirty` on a dirty tree, runs only on the salvage branch,
after the salvage turn (`saffron/cell/session.py:2436-2455`). So a no-room
cut never gets even the free checkpoint. The salvage turn's own options
pass `budget_usd=spec.budget_usd` again
(`saffron/cell/session.py:2388-2393`).

**What the ledger shows.** `SA-0087`'s task 85 spent $3.79 on its plan
turn. Its IMPLEMENT turn spent $4.59 before the turn ceiling cut it at 61
turns, $8.39 of $8. No commit ever ran, and the salvage turn was refused
for money. The plan turn spent 47% of the budget before a line was written.

**How a cap cut reads.** A turn the in-cell cap ends returns the subtype
`error_max_budget_usd` with `terminal_reason` `budget_exhausted`. The
ledger holds two such rows, task 87's REBUT and task 203's seventeenth
REVIEW session. `run_agent` raises `AgentFailed` for any subtype but
`success` (`saffron/phases/implement.py:444`,
`saffron/phases/implement.py:481`), and the attempt rides on it. Task 203's
session was capped at the $2.00 review floor and reported $2.04.

## Problem

A task whose plan turn and IMPLEMENT turn together reach the budget loses
its uncommitted work, though a salvage turn costs cents. Reserve the salvage
turn's cost out of the IMPLEMENT turn, and stop a no-room cut from skipping
the free checkpoint.

- **The reserve.** Add `SALVAGE_RESERVE_USD = 1.0` at module scope in
  `saffron/cell/session.py`, beside `REVIEW_FLOOR_USD`
  (`saffron/cell/session.py:83`). A comment of one or two lines cites the
  measurement in the notes, the way the comment on `REBUT_OVERRUN_CAP_USD`
  cites $6.40 (`saffron/cell/session.py:85-87`).
- **The IMPLEMENT turn's cap.** After the plan turn and the `_over_budget()`
  check before IMPLEMENT (`saffron/cell/session.py:2297`), take the
  remainder, `budget_usd` less `spent`. When it exceeds the reserve,
  subtract the reserve. Pass that as `max_budget_usd` to the IMPLEMENT turn
  alone. The shared options dict keeps the whole budget, so the plan,
  REPAIR, notes and REBUT turns are unchanged.
- **The budget-cap cut.** An IMPLEMENT turn whose result carries the
  subtype `error_max_budget_usd` joins the turn ceiling and the wall clock
  in `cut_by_bound` (`saffron/cell/session.py:2354`). So it earns the
  salvage turn, and a failed salvage ends `ORPHANED` through the existing
  re-queue rule (`saffron/cell/session.py:2502-2513`). Its `bound_word`
  names the budget cap.
- **The salvage turn's cap.** The salvage turn's options take the reserve
  as their budget, in place of `budget_usd=spec.budget_usd`
  (`saffron/cell/session.py:2388-2393`).
- **The no-room checkpoint.** On the `_over_budget()` branch
  (`saffron/cell/session.py:2364-2376`), take the same host checkpoint the
  salvage branch takes, then measure `commits_ahead` from `planned_sha`
  again. A commit emits the existing
  "recovered N commit(s)" `SALVAGE` line and no `Terminal`, and the task
  goes on to GATE. Zero commits emits `cut_off_no_salvage_room` as today.
  A refused checkpoint is caught as on the salvage branch (error is not
  fail). Share one checkpoint with the salvage branch rather than copying
  it.
- **The comments.** The `TerminalReason` comments
  (`saffron/events.py:91-100`) and the comment above `SALVAGE_MAX_TURNS`
  (`saffron/phases/implement.py:50-59`) name two bounds. Name the budget cap
  as the third.

## Out of scope

- **Whether the plan turn's spend belongs in IMPLEMENT's budget.** The item
  asks for a measured answer. The numbers are in the notes, and the
  decision is left out. The plan turn keeps the whole budget as its cap.
- **REBUT's budget.** `SA-0231` gives REBUT a fixed cap of its own and
  stacks on this spec. `saffron/phases/rebut.py` and REBUT's call in
  `session.py` stay as they are. The comment at
  `saffron/phases/rebut.py:678-681` says the IMPLEMENT session's cap is the
  whole task budget. It stays true of the shared dict REBUT receives.
- **The idle bound, a crash and a provider wall.** They still earn no
  salvage turn (`test_a_turn_that_crashed_is_not_reported_as_having_finished`).
- **`DESIGN.md` and `CONTEXT.md`.** Both are protected. The operator edits
  the sentences this makes incomplete in this spec's pull request.
- **The watch line catalogue.** The no-room checkpoint reuses three
  existing `SALVAGE` lines, so `events.FAMILIES` needs no new row.

## Notes for the agent

**The reserve, measured.** On 2026-10-07 `~/.saffron/ledger.db` held seven
salvage turns, each the IMPLEMENTING attempt after a cut. They spent
$0.17, $0.15, $0.34, $0.32, $0.24, $0.23 and $0.40, in two to four turns
(tasks 86, 90, 110, 148, 161, 175 and 223). The maximum, $0.40 on
`SA-0204`, rounds up to $1.00. The batch logs agree. Eight
`events.jsonl` files announce a salvage turn or refuse one, and the one
refusal is `SA-0087`'s. The in-cell cap held task 203's session to $0.04
past it, well inside the reserve's $0.60 margin.

**The plan turn's share, measured, for the decision left out.** Of 241
ledger tasks, 210 ran both a plan turn and an IMPLEMENT turn. The plan
turn took a median 13% of task spend, 27% at the 90th percentile and 50%
at most. It took a median 7% of the budget, 16% at the 90th percentile and
47% at most, on `SA-0087`. Four tasks spent 30% or more of their budget
planning: `SA-0031`, `SA-0085`, `SA-0086` and `SA-0087`. Only three of the
210 IMPLEMENT turns would have met the reserve's cap: `SA-0031`, `SA-0085`
and `SA-0087`. The turn ceiling cut all three.

**Why a budget-cap cut must salvage.** The cap is what makes room. In
`SA-0087`'s shape the cap now ends the IMPLEMENT turn before its turn
ceiling, so the cut arrives as `error_max_budget_usd`. A reserve whose cut
earns no salvage turn would spend $1.00 of IMPLEMENT's room for nothing.

**What a no-room checkpoint changes.** With the reserve, the branch is
reached only when the cut turn is charged past its cap. That is an
overshoot past the reserve, or a turn with no result charged the plan
turn's figure (`saffron/phases/implement.py:416`). A committed checkpoint
then takes the task to GATE rather than ending it `ORPHANED`. Red gates
end it `EXHAUSTED` at its first REPAIR, since `_repair` checks
`_over_budget()` first (`saffron/cell/session.py:2586-2589`). Its commits
are then pushed as unpackaged work (`saffron/task.py:706-711`). Green
gates go on to REVIEW, as a salvaged task over its budget does today.

**Which criteria have a mutant.** None. The cap, the bound and the
checkpoint call are new code, so no mutant can pin their spelling. Each
criterion lists its wrong versions instead. Criterion 4 passes today and
must keep passing.

**The witnesses.** Model them on the salvage tests beside
`test_a_cut_off_turn_over_budget_is_not_salvaged` in
`tests/test_session.py` (`tests/test_session.py:1906`).
`_stub_the_runtime` defaults `dirty_paths` to an empty list
(`tests/test_session.py:1159`). `_cut_off_turn`
(`tests/test_session.py:1253`) and `_wall_cut_turn`
(`tests/test_session.py:1267`) shape the other two cuts.

- *Criterion 1.* Script a failing suite for attempt 1, so each cell runs
  one REPAIR turn. Read `max_budget_usd` from `cell.turn_options` for the
  plan, IMPLEMENT and REPAIR turns. Write the expected caps as literals,
  with `pytest.approx` for $3.21. Derived from the constant, they would
  move with it.
- *Criterion 2.* Shape the cap cut as `run_agent` raises it, an
  `AgentFailed` carrying an attempt with `session_id="sess-1"`, the subtype
  and `terminal_reason` above, and the cost. The $3.25 cap cut models the
  measured overshoot. It also keeps the remainder, $0.96, apart from the
  reserve. Use `commits=[0, 1]` for the three salvage cells and `commits=0`
  for the fourth.
- *Criterion 3.* Use `commits=[0, 1]`. Make `dirty_paths` return one path
  only while two turns have run and nothing is checkpointed. A tree that
  stays dirty fails `committed` at GATE. Bind the cell as a lambda default
  inside a loop. For the refused cell, patch `worktree.commit_dirty` to
  raise `runtime.CellRuntimeError`, as
  `test_a_checkpoint_the_repo_refuses_is_not_an_infrastructure_abort`
  does.

**What criterion 3 leaves undriven.** A refused checkpoint after a wall
cut or a cap cut. The three bounds share one checkpoint call, so the
turn-ceiling cell reaches the code they would reach.

**How the lists were measured.** On 2026-10-07 a prototype of this change
and the three new witnesses ran on a plain copy of the base. With the
source reverted, all three witnesses failed. Each wrong version above was
applied to the prototype in turn, and each failed its criterion's witness.
Criterion 4's witness passed on the prototype. The whole suite failed
there only on the 38 tests that fail on a plain copy of the base, which
has no git repository.

**This cell runs under today's wall.** `tests/test_session.py` holds about
10,000 lines. Write the source change and commit it before any test. Run
each new test by its node id, and the touched test file whole once, at
the end.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. A docstring stays within ten lines.

**Size.** `saffron/cell/**` is in `elevate_on`, so `size` blocks at the
`bug` ceiling of 1300 tokens (`saffron/gates/core/size.py:26`). The
prototype counted 920 changed tokens by `size_gate`. That is 105 lines in
`session.py`, 16 in the two comment files and 132 in the test. The
prototype shares one checkpoint between both branches. A copy on the
no-room branch counted 715 instead. At 4 tokens a line, 920 is 230 lines.
