---
id: SA-0425
title: "A REBUT session that dies at or past its pool reads as a pool cut, so a runtime death ends the task `EXHAUSTED`"
type: bug
priority: 2
depends_on: [SA-0424]
estimated_lines: 25
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
  - saffron/phases/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/record/**
  - saffron/ledger.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/events.py
  - tests/test_rebut.py
  - tests/test_task.py
  - tests/test_implement.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
budget_usd: 30
max_attempts: 3
max_turns: 150
acceptance:
  - claim: >-
      A REBUT session that fails without the budget signal is never a pool
      cut, whatever it spent. That covers a death with no result event, an
      `api_error` result, a turn ceiling and a failure carrying no attempt.
      The task ends where `run_rebut` put it. The budget signal
      `cut_off_at_budget_cap` reads is a cut at any spend, even after a
      death in the same REBUT stage. A refusal of a call the stage's pool
      cannot cover is a cut too, unless a death without the signal brought
      that stage's spend to its limit. Each cut still ends `EXHAUSTED`
      with its stage's line. The witness drives one REBUT per row through
      `_rebut_capped` and reads the outcome's state, the `TaskOutcome`
      event, the queued state and the last REBUT line. In each of the three
      stages, a death with no result event at its pool, past it and under
      it ends `REBUTTAL_UNJUDGED`. So do an `api_error` result and a turn
      ceiling past the pool. The first two stages name the session's own
      error, and the verdict stage says a lens produced no verdict. No such
      line says REBUT ran out, and `rebut_result` stays. A rebuttal turn
      that raises with no attempt ends the same way. A session that
      succeeds and spends the extraction's pool to the cent, then claims a
      fix it did not commit, ends `REBUTTAL_UNJUDGED` too. In each stage the
      budget signal under the pool and at it ends `EXHAUSTED` with the
      stage's line. One rebuttal-stage row carries `terminal_reason` alone
      and the other `subtype` alone, and the extraction stage swaps them. The
      pool refusing the extraction's re-prompt, and refusing a second
      verdict, each ends `EXHAUSTED` with the stage's line. Each row with
      two blocker lenses refuses the second. After a first verdict that dies
      at the pool, it ends `REBUTTAL_UNJUDGED`. After one that ends on the
      budget signal, it ends `EXHAUSTED`. An extraction that dies at its
      pool, then a first verdict that spends the verdicts' pool, still
      ends `EXHAUSTED` on the refused second verdict. Two rows start the
      verdicts with a death under the verdicts' pool. In one a second
      lens spends the rest and a third is refused. In the other the second
      ends on the budget signal. Each ends `EXHAUSTED` with the verdict
      line. The witness checks every row before it asserts once, on the
      list of rows that disagreed.
    witness: tests/test_session.py::test_a_rebut_session_that_dies_is_never_read_as_a_pool_cut
    positive_case: >-
      In each stage the budget-signal and refusal rows read `EXHAUSTED` and
      the stage's "ran out of" line through the same `TaskOutcome` event and
      the same last REBUT line. So a death row's missing line is read where a
      cut's line does appear.
    wrong_versions:
      - "A failed session whose spend brings its pool to the limit is still a cut, as at your base."
      - "The budget signal is a cut only once the session's spend also reaches its pool."
      - "A failed session whose spend goes past its pool is still a cut, and one that lands exactly on it is not."
      - "Only a session with no result event is spared, so an `api_error` result or a turn ceiling at or past the pool is still a cut."
      - "The budget signal is read from `subtype` alone."
      - "The budget signal is read from `terminal_reason` alone."
      - "The budget signal is read from `failed.attempt` with no check that the attempt is present."
      - "The pool refusing a call it cannot cover no longer sets the cut."
      - "A death at or past the pool is still a cut in the rebuttal stage."
      - "A death at or past the pool is still a cut in the extraction stage."
      - "A death at or past the pool is still a cut in the verdict stage."
      - "Every failed session is a cut, whatever it spent."
      - "The budget signal is no longer a cut."
      - "A session that succeeds and spends its pool to the cent sets the cut."
      - "A refusal always sets the cut, even after a death in the same stage."
      - "A death keeps later stages' refusals from cutting, since `open` does not clear it."
      - "Any death marks its REBUT stage, at any spend, so a refusal after a death under the verdicts' pool is no cut."
      - "Any death marks its REBUT stage, and the mark keeps a later budget signal from cutting."
    covers:
      - set: the ending kind, in each stage
        members:
          - member: a death with no result event at its pool, in the rebuttal stage
            driven_by: "A death at or past the pool is still a cut in the rebuttal stage."
          - member: a death with no result event at its pool, in the extraction stage
            driven_by: "A death at or past the pool is still a cut in the extraction stage."
          - member: a death with no result event at its pool, in the verdict stage
            driven_by: "A death at or past the pool is still a cut in the verdict stage."
          - member: a death with no result event past its pool, in each stage
            driven_by: "A failed session whose spend goes past its pool is still a cut, and one that lands exactly on it is not."
          - member: a death under its pool, in each stage
            driven_by: "Every failed session is a cut, whatever it spent."
          - member: an `api_error` result or a turn ceiling past its pool, in each stage
            driven_by: "Only a session with no result event is spared, so an `api_error` result or a turn ceiling at or past the pool is still a cut."
          - member: a failure carrying no attempt
            driven_by: "The budget signal is read from `failed.attempt` with no check that the attempt is present."
          - member: the budget signal under its pool, in each stage
            driven_by: "The budget signal is a cut only once the session's spend also reaches its pool."
          - member: the budget signal at its pool, in each stage
            driven_by: "The budget signal is no longer a cut."
          - member: the pool refusing the extraction's re-prompt or a second verdict, with no death before it
            driven_by: "The pool refusing a call it cannot cover no longer sets the cut."
          - member: a refused second verdict after a first verdict that died at the pool
            driven_by: "A refusal always sets the cut, even after a death in the same stage."
          - member: a refused second verdict after a first verdict that ended on the budget signal
            driven_by: "The budget signal is no longer a cut."
          - member: a refused verdict after a death in the extraction stage
            driven_by: "A death keeps later stages' refusals from cutting, since `open` does not clear it."
          - member: a refused third verdict after a death under the verdicts' pool and a lens that spent the rest
            driven_by: "Any death marks its REBUT stage, at any spend, so a refusal after a death under the verdicts' pool is no cut."
          - member: the budget signal after a death under the verdicts' pool
            driven_by: "Any death marks its REBUT stage, and the mark keeps a later budget signal from cutting."
          - member: a success that spends its pool to the cent, then REBUT ends unjudged
            driven_by: "A session that succeeds and spends its pool to the cent sets the cut."
          - member: the old rule itself
            driven_by: "A failed session whose spend brings its pool to the limit is still a cut, as at your base."
      - set: the fields that spell the budget signal
        members:
          - member: "`terminal_reason` alone"
            driven_by: "The budget signal is read from `subtype` alone."
          - member: "`subtype` alone"
            driven_by: "The budget signal is read from `terminal_reason` alone."
  - claim: >-
      A REBUT a pool cut that `run_rebut` ends in a state other than
      `REBUTTAL_UNJUDGED` keeps that state, its own why and its
      `rebut_result`. The existing witness gains two REBUTs. In each the
      rebuttal turn carries the budget signal at $10.00 and moves HEAD,
      and the gate re-run after it ends `error` in one and red in the
      other. The first ends `GATE_ERROR`, naming the errored re-run. The
      second ends `EXHAUSTED`, naming the red gates. Each reads that state
      from the outcome, the `TaskOutcome` event and the queued state, and
      that why from `rebut_result` and the last REBUT line. Neither carries
      the cut's line, and each keeps its `rebut_result`.
    witness: tests/test_session.py::test_a_rebut_the_cap_cut_short_ends_exhausted_with_its_blockers_standing
    preserves: true
    positive_case: >-
      The same test's rows that end `REBUTTAL_UNJUDGED` under a cut read
      `EXHAUSTED`, the cut's line and no `rebut_result` through the same
      outcome, queue and last REBUT line. So a cut is seen to rewrite all
      three where the state allows it.
    wrong_versions:
      - "The cut check drops its state clause, so a REBUT a pool cut ends `EXHAUSTED` whatever state `run_rebut` gave it."
      - "The cut check spares `GATE_ERROR` alone, so a red re-run after a cut reads as a cut."
      - "The cut's line replaces the why of every REBUT a pool cut, whatever state it ends in."
      - "`rebut_result` is cleared for every REBUT a pool cut, whatever state it ends in."
    covers:
      - set: the states other than `REBUTTAL_UNJUDGED` a cut REBUT ends in
        members:
          - member: "`GATE_ERROR`, from an errored gate re-run"
            driven_by: "The cut check drops its state clause, so a REBUT a pool cut ends `EXHAUSTED` whatever state `run_rebut` gave it."
          - member: "`EXHAUSTED`, from a red gate re-run"
            driven_by: "The cut check spares `GATE_ERROR` alone, so a red re-run after a cut reads as a cut."
      - set: what such a REBUT keeps
        members:
          - member: its state
            driven_by: "The cut check drops its state clause, so a REBUT a pool cut ends `EXHAUSTED` whatever state `run_rebut` gave it."
          - member: its why
            driven_by: "The cut's line replaces the why of every REBUT a pool cut, whatever state it ends in."
          - member: "its `rebut_result`"
            driven_by: "`rebut_result` is cleared for every REBUT a pool cut, whatever state it ends in."
---

## Context

Backlog item **b-f582ee**, tier 1, its last open half: a runtime death read
as `EXHAUSTED`. It folds in **b-b8f0d9**, tier 3. Both cite `DESIGN.md`
§5.6. Every line below was read at `013c0083`. This spec depends on
`SA-0424`, and on `SA-0423`, `SA-0422` and `SA-0421` before it. `SA-0421`
and `SA-0424` edit `saffron/cell/session.py` and `tests/test_session.py`,
but none of the four edits `_RebutCap` or REBUT's cut check. So find each
cited line by the function named beside it.

**The pool.** `_RebutCap` holds one REBUT's pools
(`saffron/cell/session.py:186-243`). Its wrapper refuses a call once
nothing is left (`:220-227`), and sets `cut` to the refusal. A session that
raises `implement.AgentFailed` adds its estimated cost to `spent`
(`:235`). Then `cut` is set whenever `spent` reaches `limit` (`:237-238`),
whatever ended the session. The rebuttal stage runs one session, so its
pool never refuses (`:221-222`). The verdicts all draw on one wrapped
agent, one lens after another (`saffron/phases/rebut.py:1015-1023`). So a
first verdict that dies at the pool leaves the second to the refusal.

**The signal.** `cut_off_at_budget_cap` already reads the SDK's own
budget signal, `terminal_reason == "budget_exhausted"` or
`subtype == "error_max_budget_usd"` (`saffron/cell/session.py:522-534`).
`implement.run_agent` raises `AgentFailed` carrying that attempt
(`saffron/phases/implement.py:420`, `:457-460`). A death with no result
event raises with an attempt whose `subtype` is `"error"` and whose
`terminal_reason` is `None` (`saffron/phases/implement.py:385-401`).

**The outcome.** After `run_rebut`, the cut check reads `cap.cut` and the
state together (`saffron/cell/session.py:3991`). A cut REBUT that
`run_rebut` ended `REBUTTAL_UNJUDGED` gets the line naming its pool
(`:3992-3999`). Later its outcome becomes `EXHAUSTED` and `rebut_result`
is cleared (`:4078-4080`). Beside a lens with an `error`, the check is
reset (`:4010-4013`).

**What `run_rebut` does with a death.** A failed rebuttal turn returns its
error (`saffron/phases/rebut.py:283-289`), and so does a failed extraction
(`:304-308`). With HEAD unmoved and no argument, `rebut_state` ends
`REBUTTAL_UNJUDGED` with that error as the why (`saffron/phases/rebut.py:666-681`).
A verdict session that fails leaves its lens with an `error`. The
outcome is then `REBUTTAL_UNJUDGED` (`:688-692`), or `GATE_ERROR` when a
lens never started (`:682-687`).

**The live case.** In spec loop run 61, `SA-0368`'s rebuttal turn
spent $8.72 and committed nothing. Its extraction then died with
"ProcessError: Command failed with exit code -6" and no result event. The
task read `EXHAUSTED`, with the why "REBUT's extraction ran out of its
$4.00 reserve", followed by that error
(`~/.saffron/batches/v0/SA-0368/events.jsonl`, lines 3390-3397). In
`SA-0419`, REBUT's rebuttal turn ended on an `api_error` result after 7
turns and $0.77. It was under its pool, so it ended `REBUTTAL_UNJUDGED`
(`~/.saffron/batches/v0/SA-0419/events.jsonl`, lines 2375-2383).

**The rule's origin.** `5331b76a` added the spend rule for a session the
SDK cut at the cap, whose failure had never marked the cap refused. The
budget signal now names that case directly. The pools came with
`d9a6d490` (b-4901d2), which kept the rule per stage.

## Problem

A REBUT session that dies is read as a pool cut when its estimated spend
reaches its pool. The task then ends `EXHAUSTED`, a verdict on the spec,
for what was the runtime's failure. Its line says a pool ran out when no
pool cut anything. A death at a lower spend ends `REBUTTAL_UNJUDGED` with
its own error. So the same death reads two ways, decided by a cost estimate.

The fix moves such a task out of PACKAGE. `run_task` packages an
`EXHAUSTED` outcome with no `rebut_result` and a standing blocker
(`saffron/task.py:1008-1013`). That is how `SA-0368` opened #1145. A
`REBUTTAL_UNJUDGED` outcome takes the unpackaged branch instead and pushes
its work with no pull request (`saffron/task.py:1087-1101`). That is where
a death under the pool already ends.

The state clause of the cut check is also pinned by no test (b-b8f0d9).
Dropping it left 427 tests passing in spec loop run 44. A cut REBUT
that `run_rebut` ended `GATE_ERROR` would then read as `EXHAUSTED`.

## Out of scope

- **A retry of a REBUT turn after a provider error** (b-53354f). It stays
  its own item. REBUT's wrapper calls an agent already wrapped in
  `record_attempts` (`saffron/cell/session.py:289-313`). A retry inside the
  wrapper drops the first attempt's cost from the rebuttal's total.
- **`DESIGN.md` §5.6's text.** It already says a pool cuts on a refusal
  or on a session's own budget signal. It says a refusal is no cut where a
  session in that stage failed without the signal. The cell edits no
  protected file.
- **An extraction re-prompt after an extraction death.** A failed
  extraction returns at once (`saffron/phases/rebut.py:304-308`), so no
  re-prompt follows it.
- **REVIEW's pool.** `ReviewPool` cuts on a refusal alone
  (`saffron/phases/review.py:371-379`), and nothing here changes it.
- **The other states a cut can meet.** Criterion 2 drives two of them.
  A lens that never started beside a cut verdict is not driven. Nor are a
  refused or binary critic patch and a red repair turn.
  `REVIEW_INCOMPLETE` already resets the check.

## Notes for the agent

**Where the change goes.** `_RebutCap`'s wrapper decides whether a failed
session sets `cut`. That condition reads the budget signal alone. A
failure without it marks its REBUT stage when it brings that stage's spend
to its limit. Only then did the death empty that pool. `open`
clears the mark. The refusal branch sets `cut` only in a REBUT stage with
no mark. Keep `spent` counting every failed session's cost, since the
extraction's pool and the verdicts' pool read it. `cut_off_at_budget_cap` is defined below
the class in the same module, and Python resolves it when the wrapper is
called. Update the class docstring's last sentence to say what `cut` now
holds. In that docstring and in any comment, write "REBUT stage", never a
bare "stage", and name each pool, such as "the verdicts' pool". `CONTEXT.md`
lists both bare words under _Avoid_.

**Some deaths are deaths by design.** Take a budget and a turn ceiling
that trip together, with no budget signal on the attempt. Or take a
runner killed after a budget stop, with no result event. Each reads as a
death, not a cut, and that is intended.

**Three existing tests assert the old rule.** One is
`test_a_rebut_the_cap_cut_short_ends_exhausted_with_its_blockers_standing`.
Its rows `a`, `c`, `f` and `h` fail with `_cut_off_turn`, a turn
ceiling's attempt, spent at or past the pool. Each expects `EXHAUSTED`.
Under the new rule each ends `REBUTTAL_UNJUDGED`. Give each the attempt of
`_budget_cut_turn` at the same cost, with the message "budget spent".
Rows `c`, `f` and `h` already carry it, and row `h`'s line assertion reads
it. Row `a`'s "provider crashed" becomes "budget spent" too.
`test_a_rebut_carries_its_unread_and_unanswered_counts_past_a_pool_cut`
drives its cut the same way and takes the same change, its message
included. So does cell 5 of
`test_beside_a_lens_with_an_error_rebuts_own_stops_stand_and_a_cut_ends_incomplete`.
It drives its cap cut with `_cut_off_turn(cost=10.25)`. That stays green
under the new rule but no longer cuts, so it stops guarding the reset
beside an errored lens. Give it `_budget_cut_turn(cost=10.25)`. With
those edits the whole suite passed on the prototype, over all four
parents.

**Criterion 2's witness exists and carries `preserves: true`.** Its
behaviour holds at your base, and it stays green there. Add the two
REBUTs to its body and keep its node id. `_rebut_capped` takes `suites`,
whose third entry is the re-run's result. The same test's
`outcome6` case shows a red one, and
`test_a_rebuttal_the_cap_cut_reads_as_out_of_budget_not_as_silence` builds
an errored one.

**Criterion 1's witness is new.** Build each row with `_rebut_capped` at
`budget_usd=0.25`. A death with no result event needs a stub of its own,
an `AgentFailed` whose attempt has `session_id=None`, `subtype="error"`
and no `terminal_reason`. An `api_error` result is the attempt SA-0419's
result event carried: `subtype="success"`, `terminal_reason="api_error"`
and `is_error=True`. The pools are $10.00 for the rebuttal turn, $14.00 for
the extraction after a $6.00 fix, and $16.00 for the verdicts after $8.50.
A verdict row needs HEAD moved, so pass `rebut_commits=1` there. A
refused extraction re-prompt needs an extraction that is not the schema,
spent to the pool. A refused verdict needs two blockers, the first verdict
spending the verdicts' pool. `_rebut_capped` files one blocker per
verdict cost past the first two costs, so four costs give two blocker
lenses. Its third lens is adequacy, whose blocker needs a probe that
`_BLOCKER` lacks. So a row with three verdicts needs `_rebut_capped` to
take the lenses that file, such as correctness, contract and conventions.
A claimed fix is the test module's `_CLAIMED_FIX`.

**Two wrong versions match the right code.** "A later success clears the
mark" and "the mark keeps a later budget signal from cutting" change
nothing. A marked REBUT stage has no money left, so every later call is
refused before it starts.

**This change is an edit.** Each criterion has a mutant in
`saffron/cell/session.py`, kept on `refs/saffron/mutants`.
