---
id: SA-0230
title: An IMPLEMENT turn cut with nothing committed gets no salvage turn once the budget is spent, so its work dies with the cell
type: bug
priority: 1
depends_on: []
estimated_lines: 219
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
      The IMPLEMENT turn runs under its own `max_budget_usd`. That is the
      remainder, the budget less the plan checkpoint's spend, a re-prompted
      plan turn included, less the amount held for the salvage turn. The
      amount held is the smaller of `SALVAGE_RESERVE_USD`, which is $1.00,
      and half the remainder. The plan turn and the REPAIR turn after it keep
      the task's `budget_usd`. The witness drives six cells, each with one
      REPAIR turn. Remainders of $4.21, $2.00, $1.50, $1.00 and $0.50 cap the
      IMPLEMENT turn at $3.21, $1.00, $0.75, $0.50 and $0.25. A sixth cell's
      plan turn first replies off the schema for $2.00, then plans for $1.79.
      Its $4.21 remainder caps the IMPLEMENT turn at $3.21 too. Today all six
      IMPLEMENT turns get the whole budget.
    witness: tests/test_session.py::test_the_implement_turn_keeps_the_salvage_reserve_out_of_its_cap
    wrong_versions:
      - The reserve comes off only a remainder above $1.00, so the $1.50 cell gets $0.50 and the $1.00 cell $1.00.
      - The reserve comes off only a remainder of $2 or more, so the $1.50 cell gets $1.50.
      - The cap is the larger of the remainder less $1.00 and the smaller of the remainder and $1.00, so the $1.50 cell gets $1.00.
      - The cap is the budget less the amount held, ignoring the plan turn, so the $4.21 cell gets $7.00.
      - The remainder reads `last_cost`, the plan turn's last reply, instead of the checkpoint's total, so the re-prompted cell gets $5.21.
      - Nothing is held, so the $4.21 cell gets $4.21.
      - Half the remainder is always held, so the $4.21 cell gets $2.105.
      - The whole $1.00 is always held, so the $0.50 cell gets a negative cap.
      - The capped dict replaces the shared one, so the REPAIR turn after it is also capped at $3.21.
      - The reserve comes off the shared options dict, so the plan and REPAIR turns of the $4.21 cell get $7.00.
  - claim: >-
      An IMPLEMENT turn that its own budget cap cuts with nothing committed
      earns the salvage turn, as a turn-ceiling cut and a wall cut do. Its
      result reports the subtype `error_max_budget_usd`. The watch line that
      announces its salvage turn contains "budget", and neither "turn
      ceiling" nor "wall". Every salvage turn, whichever of the three bounds
      earned it, runs under a `max_budget_usd` of the amount held for it. A
      budget-cap cut whose salvage turn recovers nothing ends `ORPHANED`, as
      the other two cuts do on their first time at a `spec_sha`. The witness
      drives SA-0087's shape, an $8 budget and a $3.79 plan turn, so $1.00 is
      held. The cap cuts one IMPLEMENT turn at $3.25, and the turn ceiling
      cuts another at $3.00. Two cells have a $2 budget and a $0.50 plan
      turn, so $0.75 is held. The wall clock cuts one IMPLEMENT turn at $0.77,
      and the cap cuts the other at $0.77. All four salvage turns commit, and
      all four tasks reach `READY_FOR_REVIEW`. A fifth cell's cap cut, in SA-0087's
      shape, is followed by a salvage turn that commits nothing. Today the
      cap cut ends `NOT_IMPLEMENTED` after two turns.
    witness: tests/test_session.py::test_an_implement_turn_its_budget_cap_cuts_is_salvaged_on_the_reserve
    wrong_versions:
      - A budget-cap cut is not a bound, so it ends `NOT_IMPLEMENTED` with no salvage turn.
      - The salvage turn keeps the whole budget as its cap, $8.00.
      - The salvage turn's cap is what the budget has left, $0.96 after the $3.25 cap cut.
      - The salvage turn's cap is always `SALVAGE_RESERVE_USD`, so the $2 cell's salvage turn gets $1.00.
      - Only the budget-cap cut's salvage turn runs on the amount held, so the turn-ceiling and wall salvage turns keep the whole budget.
      - Only the budget-cap cut's salvage turn runs on the amount held, and the others on `SALVAGE_RESERVE_USD`, so the $2 wall cell's salvage turn gets $1.00.
      - A budget-cap cut salvages, but its failed salvage ends `NOT_IMPLEMENTED` rather than `ORPHANED`.
      - The announcing line names the wall clock for a budget-cap cut.
  - claim: >-
      An IMPLEMENT turn cut with nothing committed and no budget left for a
      salvage turn still gets the host checkpoint. This holds for each of
      the three bounds that earn a salvage turn. A dirty tree is committed by
      the host, the commits are measured again, and a commit carries the
      task on to GATE with no salvage turn. The host's commit message reads
      "checkpoint: host-committed" and then "no room left for a salvage
      turn", the note this branch names. Its watch lines then say the host
      checkpointed the work and recovered 1 commit, and none says "no room
      left to salvage". Green gates go on to `READY_FOR_REVIEW`. Red gates
      end the task `EXHAUSTED` with no REPAIR turn, not `ORPHANED`, so the
      spec is not re-queued. Its commits are then pushed as unpackaged
      work, as for any `EXHAUSTED` task. On a turn-ceiling cut, a
      checkpoint the repo's hook refuses is reported, not raised, and the
      task ends `ORPHANED` as today. The witness drives a $12 budget whose
      IMPLEMENT turn spends $12.00. Three cells are cut by the turn ceiling,
      the wall clock and the turn's own cap, with green gates. A fourth is
      cut by the turn ceiling, and its gates go red. A fifth, cut by the turn
      ceiling, has a checkpoint that raises `CellRuntimeError`. Today no cell
      takes a checkpoint. The turn-ceiling and wall cells end `ORPHANED`, and
      the cap cell ends `NOT_IMPLEMENTED`.
    witness: tests/test_session.py::test_a_cut_with_no_room_left_still_takes_the_host_checkpoint
    wrong_versions:
      - The no-room branch takes no checkpoint.
      - The checkpoint runs, but the commits are not measured again, so the task still ends `ORPHANED`.
      - The checkpoint runs only for a turn-ceiling cut.
      - The no-room checkpoint commits with the salvage branch's note, "the salvage turn committed nothing".
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
  remainder, `budget_usd` less `spent`. Hold the smaller of the reserve
  and half the remainder for the salvage turn. Pass the remainder less
  that amount as `max_budget_usd` to the IMPLEMENT turn alone. The shared
  options dict keeps the whole budget, so the plan, REPAIR, notes and REBUT
  turns are unchanged.
- **The budget-cap cut.** An IMPLEMENT turn whose result carries the
  subtype `error_max_budget_usd` joins the turn ceiling and the wall clock
  in `cut_by_bound` (`saffron/cell/session.py:2354`). So it earns the
  salvage turn, and a failed salvage ends `ORPHANED` through the existing
  re-queue rule (`saffron/cell/session.py:2502-2513`). Its `bound_word`
  names the budget cap.
- **The salvage turn's cap.** The salvage turn's options take the amount
  held as their budget, in place of `budget_usd=spec.budget_usd`
  (`saffron/cell/session.py:2388-2393`).
- **The no-room checkpoint.** On the `_over_budget()` branch
  (`saffron/cell/session.py:2364-2376`), take the same host checkpoint the
  salvage branch takes, then measure `commits_ahead` from `planned_sha`
  again. A commit emits the existing "recovered N commit(s)" `SALVAGE` line
  and no `Terminal`, and the task goes on to GATE. Zero commits emits `cut_off_no_salvage_room` as today.
  A refused checkpoint is caught as on the salvage branch (error is not
  fail). Give this branch its own checkpoint call, whose note is "no room
  left for a salvage turn". It reaches the pull request body through
  `commit_subjects` (`saffron/cell/session.py:2418-2419`). The salvage
  branch's checkpoint and its note stay as they are.
- **The comments.** The `TerminalReason` comments
  (`saffron/events.py:91-100`) and the comment above `SALVAGE_MAX_TURNS`
  (`saffron/phases/implement.py:50-59`) name two bounds. Name the budget cap
  as the third. The comment on `max_budget_usd` says one options dict
  drives every turn (`saffron/phases/implement.py:185-188`). Say the
  IMPLEMENT and salvage turns get caps of their own.

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
past it. That leaves the full reserve a $0.60 margin over the largest
salvage turn, for remainders of $2 or more. The $0.04 overshoot was
measured on a REVIEW session, not on an IMPLEMENT turn.

**Why half the remainder below $2.** A fixed $1.00 taken only from a
remainder above $1.00 leaves a cliff. A $1.01 remainder would cap the
IMPLEMENT turn at $0.01, so it is cut at its first call on a clean tree.
Its salvage turn recovers nothing, and the task ends `ORPHANED`, spending
the spec's one re-queue. Holding half the remainder below $2 splits it
evenly instead, and the two rules meet at $2.

**The plan turn's share, measured, for the decision left out.** Of 241
ledger tasks, 210 ran both a plan turn and an IMPLEMENT turn. The plan
turn took a median 13% of task spend, 27% at the 90th percentile and 50%
at most. It took a median 7% of the budget, 16% at the 90th percentile and
47% at most, on `SA-0087`. Four tasks spent 30% or more of their budget
planning: `SA-0031`, `SA-0085`, `SA-0086` and `SA-0087`. Only three of the
210 IMPLEMENT turns would have met the new cap: `SA-0031`, `SA-0085` and
`SA-0087`. The turn ceiling cut all three.

**Why a budget-cap cut must salvage.** The cap is what makes room. In
`SA-0087`'s shape the cap now ends the IMPLEMENT turn before its turn
ceiling, so the cut arrives as `error_max_budget_usd`. A reserve whose cut
earns no salvage turn would spend $1.00 of IMPLEMENT's room for nothing.

**When the no-room branch is reached.** The cut turn must be charged at
least what was held for the salvage turn past its own cap. A cap overshoot
can do it, most easily on a small remainder, where little is held. So can
a turn with no result, charged the plan turn's figure
(`saffron/phases/implement.py:416`).

**What a no-room checkpoint changes.** The operator chose this trade, so
that work is never lost. A committed checkpoint takes the task to GATE
rather than ending it `ORPHANED`. Red gates end it `EXHAUSTED` at its
first REPAIR, since `_repair` checks `_over_budget()` first
(`saffron/cell/session.py:2586-2589`). `EXHAUSTED` is in
`DEPENDENCY_DEAD_STATES` (`saffron/scheduler.py:105`) and not in
`REQUEUE_STATES` (`saffron/scheduler.py:111-118`), so the spec is not
re-queued. `push_unpackaged_work` then pushes its commits
(`saffron/task.py:706-711`). Criterion 3's witness drives the state, not
the push. Green gates go on to REVIEW, as a salvaged task over its budget
does today.

**The re-queue cap and a resumed row.** A batch already resumes the
newest row in `REQUEUE_STATES` when it re-queues the spec
(`saffron/scheduler.py:907-910`). `previous_cut_orphan` then excludes that
row as the task itself (`saffron/cell/session.py:456-477`), so a second
cut re-queues again. This is
true at base. This spec widens what feeds the cap to the budget-cap cut.
§4.5 already names the re-key, and it is out of scope here.

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
  plan, IMPLEMENT and REPAIR turns. Use six cells: an $8 budget after a
  $3.79 plan turn, $3 after $1.00, $2 after $0.50, $1.50 after $0.50 and $1
  after $0.50. The sixth has an $8 budget, a plan turn replying "not the
  schema" for $2.00 and then a plan for $1.79. Tests near
  `test_a_turn_that_fails_after_a_completed_turn_keeps_not_implemented`
  script that reply. Its turns shift by one, so read its options from the
  re-prompt on. Write the expected caps as literals, with `pytest.approx`.
  Derived from the constant, they would move with it.
- *Criterion 2.* Shape the cap cut as `run_agent` raises it, an
  `AgentFailed` carrying an attempt with `session_id="sess-1"`, the subtype
  and `terminal_reason` above, and the cost. The $3.25 cap cut models the
  measured overshoot. It also keeps the remainder, $0.96, apart from the
  amount held. The $2 cell's cut at $0.77 keeps $0.73 apart from its $0.75.
  Use `commits=[0, 1]` for the four salvage cells and `commits=0` for the
  fifth.
- *Criterion 3.* Use `commits=[0, 1]`. Make `dirty_paths` return one path
  only while two turns have run and nothing is checkpointed. A tree that
  stays dirty fails `committed` at GATE. Bind the cell as a lambda default
  inside a loop. Assert `cell.checkpointed` holds the one message. For the
  red cell, script a green baseline and a failing first attempt. Give the
  refused cell `commits=0`, as
  `test_a_checkpoint_the_repo_refuses_is_not_an_infrastructure_abort`
  does. With `[0, 1]` the stub reports a commit the refused checkpoint never
  made. Patch `worktree.commit_dirty` to raise `runtime.CellRuntimeError`
  as that test does.

**What criterion 3 leaves undriven.** A refused checkpoint after a wall
cut or a cap cut. The three bounds share one checkpoint call, so the
turn-ceiling cell reaches the code they would reach.

**How the lists were measured.** On 2026-10-07 a prototype of this change
and the three new witnesses ran on a plain copy of the base. With the
source reverted, all three witnesses failed. Each wrong version above was
applied to the prototype in turn, and each failed its criterion's witness.
That held for the prototype with its own no-room checkpoint call and for
one sharing a helper.
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
prototype counted 875 changed tokens by `size_gate`. That is 70 lines in
`session.py`, 20 in the two comment files and 166 in the test. At 4 tokens
a line, 875 is 219 lines, 67% of the ceiling. A prototype sharing one
checkpoint helper between the two branches counted 1077, 83%, past the
80% margin. So the no-room branch carries its own checkpoint call.
