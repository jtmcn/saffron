---
id: SA-0249
title: A RATE_LIMITED outcome carries 0 attempts, so its index row reads as a task that never ran a suite
type: bug
priority: 2
depends_on: [SA-0248]
estimated_lines: 103
estimate_measured: true
touches:
  - saffron/cell/session.py
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
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/report/**
  - saffron/task.py
  - saffron/batch.py
  - saffron/events.py
  - saffron/record/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/phases/**
  - saffron/cell/runtime.py
  - saffron/cell/worktree.py
  - saffron/cell/proxy.py
  - saffron/cell/runtimes/**
  - tests/test_task.py
budget_usd: 16
max_attempts: 3
max_turns: 110
acceptance:
  - claim: >-
      A `RATE_LIMITED` outcome carries the number of gate suites
      `repair_loop` judged before the limit, the unit its `attempts` holds on
      every other path. The witness walls a turn at four points. A walled
      plan turn and a walled implement turn each report 0. A walled repair
      turn after attempt 1 reports 1, and one after attempt 3 reports 3. The
      same witness drives six returns that come before the first suite.
      Those are a baseline that aborts, a scope proposal, a rejected plan, a
      failed plan turn, the spend ceiling after the plan and an implement
      turn with no commits. Each still reports 0. Every count is an `int`.
    witness: tests/test_session.py::test_a_rate_limit_counts_the_suites_judged_and_no_return_before_a_suite_counts_any
    wrong_versions:
      - The count read from the ledger's attempt rows, one per agent turn, so a walled plan turn reports 1.
      - The count raised when a repair turn returns, so a limit in the repair turn after attempt 1 reports 0.
      - The count taken from what `repair_loop` returns, so a limit inside the loop reports 0.
      - An early return given the same ledger read-back, so the scope proposal reports 1.
      - The count stored as a float, so `1.0` stands where `1` belongs.
  - claim: >-
      A limit after the loop reports the count the loop reached, as the
      return after the loop does. The witness walls three turns after a loop.
      The notes turn and the first REVIEW lens each follow a loop that
      reached 2 and report 2. A REBUT verdict session follows a loop that
      reached 1 and the rebuttal's own suite, and reports 1. The same witness
      ends two cells with no limit. A loop that reached 2 ends
      `READY_FOR_REVIEW` with 2, and a REBUT after a loop that reached 1
      ends `READY_FOR_REVIEW` with 1.
    witness: tests/test_session.py::test_a_rate_limit_after_the_loop_counts_the_loops_suites_and_not_rebuts_rerun
    wrong_versions:
      - Every suite `_judge` judges counted, the rebuttal's suite included, so the walled REBUT verdict session reports 2.
      - The count set from the rebuttal suite's event number, the loop's count plus one.
      - The count reset to 0 once `repair_loop` returns, so a walled lens reports 0.
  - claim: >-
      `run_task` still writes an unpackaged task's index row with the
      outcome's own `attempts`. The witness drives an `EXHAUSTED` and a
      `NOT_IMPLEMENTED` outcome.
    witness: tests/test_task.py::test_a_task_that_never_packaged_still_reaches_the_index
    preserves: true
---

## Context

Backlog item **b-60732c**, filed from the spec loop's run 7. It cites
`DESIGN.md` §6. Every line number below was read at `958db033`.

**The defect.** `_drive_cell`'s `except RateLimited` handler
(`saffron/cell/session.py:3188-3217`) builds its `CellOutcome` with no
`attempts` (`saffron/cell/session.py:3208-3217`). So the field takes its
default of 0 (`saffron/cell/session.py:382`). `run_task` writes an
unpackaged task's index row with `attempts=outcome.attempts`
(`saffron/task.py:706-730`). The page renders it as `0 att`
(`saffron/report/index.py:237`). `sort_key` tiebreaks on `-line.attempts`
(`saffron/report/index.py:145`), so the row sorts after every row of its
rank that ties it on the keys before. A task walled after three red suites reads as one that never
ran a suite.

**The unit.** `CellOutcome.attempts` is the gate suite number
`repair_loop` reached. The loop numbers each suite it judges from 1
(`saffron/cell/session.py:761-762`). Each of its four exits returns that
number (`saffron/cell/session.py:769`, `:784`, `:789`, `:792`).
`_drive_cell` binds it to `attempts` (`saffron/cell/session.py:2633`) and
puts `attempts` on the outcome (`saffron/cell/session.py:3177`). A REBUT re-run suite is
numbered one past it for its event (`saffron/cell/session.py:3031-3040`).
That number never reaches the outcome. `CONTEXT.md`'s **Attempt** entry
names the suite count as the one exception to its phase rule.
`CellOutcome.attempts` leaves out the REBUT re-run's suite, unlike that count.

**Not the ledger's unit.** `record_attempts` opens one `attempts` row per
agent turn (`saffron/cell/session.py:242-262`). `ledger.attempts` returns
those rows (`saffron/ledger.py:1440-1446`). A plan turn, an implement turn
and a repair turn are three rows and one suite. The item's "read back from
the ledger" suggests that count. It is the wrong unit, and criterion 1's
first wrong version is that read.

**Where a limit lands.** Every turn goes through `stop_on_rejected`
(`saffron/cell/session.py:217-239`, wrapped at `:2125-2135`). It raises
`RateLimited`, which unwinds to the handler from any turn (§3.3). Before
the loop that is the plan turn (`saffron/cell/session.py:2138`) or the
implement turn (`:2314`). Inside it, a repair turn runs after the suite it
answers (`saffron/cell/session.py:2586-2600`). After it come the notes turn
(`:2662-2671`), REVIEW's sessions (`:2827`) and REBUT's (`:3076`).

**The other returns.** `_drive_cell` builds a `CellOutcome` at eight
places at `958db033`. Six come before the loop and pass no `attempts`. Those
`CellOutcome` returns are `PREFLIGHT_FAILED` (`saffron/cell/session.py:2061`),
`SCOPE_REVIEW` (`:2192`) and `PLAN_REJECTED` (`:2214`). The other three
`CellOutcome` returns are a failed plan turn (`:2246`), the spend ceiling
after the plan (`:2302`) and no commits (`:2519`). No suite
has run at any of them, so 0 is their true count. They keep it. The return
after the loop passes the loop's count (`:3171-3187`). The handler is the
only return that can follow a suite and still report 0.
`SA-0244` adds a ninth, a `PreflightFailed` handler for a refused
`cell_up` that returns `PREFLIGHT_FAILED`. That makes seven before the
loop. It runs before any suite, so it stays at 0, and no witness here
drives it.

**Spend is read back already.** The handler reads spend from the ledger,
since `spent` loses the walled turn (`saffron/cell/session.py:3189-3194`).
`spent` is bound before the `try` for the same reason
(`saffron/cell/session.py:1993-1998`).

## Problem

A `RATE_LIMITED` outcome must carry the suites `repair_loop` judged before
the limit.

1. Keep the latest suite number `repair_loop` judged where the handler can
   read it. Bind it to 0 before the `try`, beside `spent`. Set it in
   `_judge` only for a suite judged `against` `"attempt"`. `SA-0242`
   hands `repair_loop` `_judge` with that value bound. Its REBUT call
   passes `"rebuttal"` and the re-run's own number, and must not move it.
2. Pass it as `attempts` on the handler's `CellOutcome`.
3. Leave the early returns and the return after the loop as they are.

## Out of scope

- **The spend read-back.** Leave the handler's spend line
  (`saffron/cell/session.py:3194`) and `start_spend` alone. It is not this defect.
- **`task.py`, the index and the ledger.** They carry the count through
  unchanged. Criterion 3 holds the row's half of that.
- **Driving every unpackaged state through `run_task`.** Criterion 3's
  witness drives `EXHAUSTED` and `NOT_IMPLEMENTED`. `RATE_LIMITED` takes the
  same `else:` branch (`saffron/task.py:706`) and is not driven there.
  A new test for it would pass with the source reverted, which `revert`
  blocks.
- **Turns the witnesses do not wall.** Before the loop, the plan
  re-prompts and the `implement.SALVAGE_PROMPT` turn
  (`saffron/cell/session.py:2396-2398`) go undriven. No suite precedes them, as with the plan turn. After the loop,
  the three later lenses go undriven. So do REBUT's rebuttal and extraction
  turns, which come before its suite. `review.run_criterion_probes`
  (`saffron/cell/session.py:2856`) and `review.run_wrong_versions`
  (`:2871`) go undriven too. They share the lens's `critic_cell` block
  (`:2807`), so the count they would read is the lens's.
- **The `PROVIDER_UNREACHABLE` and `ORPHANED` states.** Each shares a return
  with a driven state (`saffron/cell/session.py:2229-2256`, `:2503-2527`).

## Notes for the agent

**Your base.** This spec stacks on `SA-0248`. Specs from `SA-0230` to
`SA-0248` edit `session.py` too, so read it at your base before you edit.
Line numbers above are from `958db033`, so expect them to differ there.

**Edit or new.** The binding that holds the count is new code, and its
name is yours to choose. So criteria 1 and 2 declare a witness and no
mutant, and `witness` reports `skip` for them. Criterion 3 is `preserves`.
Pick a name no other local in `_drive_cell` uses. REBUT binds `judged`
already (`saffron/cell/session.py:3125`).

**Both witnesses.** Use `_stub_the_runtime` and `_drive`. Wall a turn with
`implement.AgentFailed("api_error", attempt=_rejected())`. One small helper
can stub a cell under its own `tmp_path` subdirectory, drive it, and return
the state and count. Each case asserts the pair and that the count is an
`int`, with the case's name as the message.

**Criterion 1's cases.** Red suites come from `_results` with distinct
`Failure`s, so the loop sees progress. For attempt 3, script
`suites=([], red1, red2, red3)` and the plan, implement and two repair turns
before the walled one. The baseline that aborts scripts one `error`
`GateResult` as the baseline. The scope proposal scripts
`_turn(_block(_PROPOSAL))`. The rejected plan scripts two turns that are not
a plan. The failed plan turn raises `implement.AgentFailed` carrying a
plain `_turn()`. The spend ceiling uses `_spec(budget_usd=0.05)`. No
commits uses `commits=0`.

**Criterion 2's cases.** Script `suites=([], red1, [])` for a loop that
reaches 2. The notes turn needs `_spec(forbidden=["docs/**"])`. The REBUT
cases use `patch=_ANCHORING_DIFF`, `_rebuttable(..., rebut_commits=1)` and
`_through_rebut`. Script a rebuttal turn, an extraction turn arguing
finding 1, then the walled turn or a verdict withdrawing it.

**Measured on a prototype, 2026-10-07.** Both witnesses were written
against `958db033` with the fix above, and passed. Each failed with
`session.py` reverted. Each wrong version listed above failed its own
criterion's witness. `tests/test_session.py` and `tests/test_task.py` passed
whole, and `ruff` and `ty` passed. Both witnesses were then run again on
`SA-0242`'s prototype with this fix keyed on `against`, and passed. With
`SA-0242` alone, both failed. Criterion 2's first two wrong versions each
failed its witness there. `SA-0231`'s REBUT cap was not in that tree, so
that tree is not your full base.

**The `prose` gate** reads every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence over
25 words. Keep each docstring within ten lines.

**Size.** `saffron/cell/**` is in `elevate_on`, so `size` blocks. The
prototype counted 412 changed tokens by `size_gate`, against the `bug`
ceiling of 1300. `estimated_lines` is those tokens over four.
