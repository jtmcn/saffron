---
id: SA-0293
title: REBUT's verdict shares its cap with the fixes, so a task whose gates are green ends `EXHAUSTED`
type: bug
priority: 1
depends_on: [SA-0288, SA-0287]
estimated_lines: 160
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
  - saffron/reconcile.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/events.py
  - saffron/report/**
  - saffron/record/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/phases/**
  - tests/test_rebut.py
  - tests/test_agent_runner.py
  - tests/test_events.py
  - tests/test_scheduler.py
  - tests/test_task.py
  - tests/test_spec_loop_driver.py
budget_usd: 25
max_attempts: 3
max_turns: 140
acceptance:
  - claim: >-
      The rebuttal turn and its extraction draw on the $10.00 cap alone. Each
      verdict draws on a $2.00 reserve plus what those two left of the cap,
      less what earlier verdicts spent. The witness drives six ways the
      rebuttal turns end: under the cap, two calls summing past it, a turn
      landing on it, a turn running past it, a turn failing at it, and two
      lenses. Each case asserts every REBUT session's own budget and a
      verdict that is answered.
    witness: tests/test_session.py::test_a_rebuttal_that_spends_the_cap_still_gets_its_verdict_from_the_reserve
    mutant:
      file: saffron/cell/session.py
      find: REBUT_CAP_USD = 10.0
      replace: REBUT_CAP_USD = 12.0
    wrong_versions:
      - The reserve added to the cap the rebuttal turns draw on, so the rebuttal turn starts with $12.00.
      - The verdicts given the cap plus the reserve less everything REBUT spent, so a rebuttal turn that ran past the cap eats into the reserve.
      - The verdicts given the reserve alone, so what the rebuttal turns left of the cap is dropped.
      - Each verdict given the whole verdict pool, so a second lens gets what the first already spent.
      - The reserve opened only when the cap refused a rebuttal call, so a REBUT under the cap gets none.
  - claim: >-
      A verdict the reserve cuts short ends the task `EXHAUSTED` with its
      blocker standing. Its line names the verdict and the $2.00 reserve,
      in `rebuttal.json` and in the REBUT phase event alike. A cut during
      the rebuttal turns keeps today's line, which names neither. The
      witness drives a verdict that spends the pool and a verdict the pool
      refuses, then a rebuttal turn and an extraction the cap cut.
    witness: tests/test_session.py::test_a_verdict_the_reserve_cut_short_says_so_apart_from_a_rebuttal_cut
    mutant:
      file: saffron/cell/session.py
      find: f"REBUT ran out of its ${REBUT_CAP_USD:.2f} budget"
      replace: f"REBUT's verdict ran out of its ${REBUT_CAP_USD:.2f} budget"
    wrong_versions:
      - The cut line left as it is today for both kinds of cut, so a verdict cut reads as a rebuttal cut.
      - The verdict's line chosen only when the pool refuses a call, so a verdict session that spends the pool reads as a rebuttal cut.
      - The verdict's line chosen for every cut, so a cut during the rebuttal turns names the verdict too.
      - The verdict's line written to `rebuttal.json` after the REBUT phase event was emitted, so the event keeps the rebuttal's line.
  - claim: >-
      A verdict session that starts and fails with money left in its pool is
      no cut, even after the cap refused the extraction. The task ends
      `REBUTTAL_UNJUDGED` with its own line and keeps its rebut result. The
      witness drives a verdict outside the schema and a verdict session that
      crashes.
    witness: tests/test_session.py::test_a_verdict_that_fails_on_its_own_after_the_cap_is_spent_is_no_cut
    mutant:
      file: saffron/cell/session.py
      find: cut = cap.refused and
      replace: cut = (cap.refused or cap.spent >= REBUT_CAP_USD) and
    wrong_versions:
      - The cap's refusal during the rebuttal turns left standing once the verdicts start, so any verdict that fails afterwards reads as a cut.
      - A REBUT cut decided by whether REBUT's total spend reached the cap, so a verdict paid from the reserve always reads as a cut.
---

## Context

Backlog item **b-4901d2**, found in the spec loop's run 39 on `SA-0272`. It
cites `DESIGN.md` §5.6, where REBUT's cap is written down. Every line number
below was read at `841a62e1`. That commit holds `SA-0272` and this spec's
own commit. `SA-0276` lands before this spec and edits two of the lines
named here, and the notes say how.

**REBUT's sessions draw on one pool.** `REBUT_CAP_USD` is $10.00
(`saffron/cell/session.py:95-97`). The cell builds one `_RebutCap` from it
(`:3367`) and wraps the agent with it (`:3368`). Every call through the
wrapper gets the cap less what earlier calls spent (`:197`, `:203-207`). A
call with nothing left is refused, and a failed call that spends the rest
sets `refused` (`:196-201`, `:211-213`). `run_rebut` passes that one agent
to the rebuttal turn and its extraction (`saffron/phases/rebut.py:676-686`).
It then passes the same agent to each lens verdict (`:744-768`).

**The verdict comes last, so it gets what the fixes left.** On `SA-0272` the
rebuttal turn spent $6.41 and its extraction $3.08. The gates re-ran green.
The verdict then started with $0.56 and ran out
(`~/.saffron/batches/v0/<task>/rebuttal.json`, `why` says
`error_max_budget_usd`). The cell read the halt as a cut
(`saffron/cell/session.py:3427`). It rewrote the line to say REBUT ran out
of its budget (`:3428-3435`) and ended the task `EXHAUSTED` (`:3480-3482`).
The code was sound, and the operator had to settle draft #875 by hand.

**One place knows the verdicts are about to start.** That place is
`critic_container`. `run_rebut` calls it at most once, after a green re-run
and before the first verdict (`saffron/phases/rebut.py:645-648`, `:717-728`, `:744`). The cell's
`_rebut_critic_container` is that callback
(`saffron/cell/session.py:3372-3393`). An early exit and a red or errored
re-run never call it (`saffron/phases/rebut.py:711-726`).

**The line reaches two records.** The cell writes `result.why` to
`rebuttal.json` (`saffron/cell/session.py:3438-3440`). It then emits the
REBUT phase event with the same text (`:3465`, `:3484`).

**Measured on 2026-10-14** from the 90 `rebuttal.json` files under
`~/.saffron/batches/v0/`, 86 with a verdict. The verdict sessions of one
REBUT summed to $1.16 at most (`SA-0266`, three lenses). The median was
$0.34. The most one verdict session spent was $0.70 (`SA-0271`).
`SA-0272`'s $0.56 was cut, so it is a floor and not counted.

## Problem

Hold a verdict reserve of $2.00 on top of `REBUT_CAP_USD`. That is the
measured $1.16, rounded up to the dollar, as `SALVAGE_RESERVE_USD` was
(`saffron/cell/session.py:91-93`). Say in its comment that the figure is
measured, and from which REBUT.

Leave the rebuttal turn and its extraction exactly as they are. They draw on
`REBUT_CAP_USD` alone, and the reserve never reaches them. When the verdicts
start, open their pool. It holds the reserve plus whatever the rebuttal turns
left of the cap, never less than the reserve. A rebuttal turn that ran past
the cap leaves nothing, and the reserve stays whole. Each verdict session
gets what that pool has left, as each rebuttal session does today.

Keep `SA-0276`'s contract: a REBUT the cap cut short ends `EXHAUSTED`. Say
which half cut it. A cut while the verdicts ran gets a line naming the
verdict and the reserve's dollars, and still saying it ran out. A cut during
the rebuttal turns keeps today's line unchanged. Either line still carries
the error of the session that was cut, as today.

A refusal by the cap during the rebuttal turns no longer decides the
outcome once a verdict has its own money. A verdict that then fails with
money left is not a cut. It ends `REBUTTAL_UNJUDGED`, as any unjudged
rebuttal does.

Update the two comments the change makes false. One above
`REVIEW_FLOOR_USD` names REBUT's ceiling (`saffron/cell/session.py:87-88`).
The other is `_RebutCap`'s docstring, which says each lens verdict draws on
the same pool (`:176-181`).

Then update four tests that pin the old pool. Keep each test's name and its
own intent. Each case below names the edit the prototype measured.

- `test_a_rebut_past_the_budget_shares_one_cap_and_stops_when_it_is_spent`
  (`tests/test_session.py:4859-4912`). Its verdict budgets now include the
  reserve. A case whose extraction the cap refused now runs its verdict on
  the next scripted turn, so it ends unjudged, not `EXHAUSTED`. A case whose
  extraction succeeded past the cap now ends `READY_FOR_REVIEW`.
- `test_a_rebut_the_cap_cut_short_ends_exhausted_with_its_blockers_standing`
  (`:4915-5012`). Its cut cases must still be cuts. Give each rebuttal-turn
  cut no commit, so it ends at the early exit. Replace the extraction that
  succeeds past the cap with one the cap cuts. Raise the cut verdict's cost
  to the verdict pool. Its line check accepts either cut's line.
- `test_rebut_draws_on_its_own_cap_whatever_the_task_has_left`
  (`:5120-5163`). Its verdict budget now includes the reserve. Its cut case
  gets no commit, so it still ends `EXHAUSTED`.
- `test_a_rebuttal_the_cap_cut_reads_as_out_of_budget_not_as_silence`
  (`:5166-5283`). Its extraction cut gets no commit. Its verdict cut costs
  the whole verdict pool, and its line is the verdict's. The rebuttal and
  extraction lines are unchanged.

## Out of scope

- **A new state.** No state is added, and §3.3's states, `CONTEXT.md` and
  the ontology stay as they are. The line is what tells the two cuts apart.
- **`run_rebut` and the verdict prompt.** `saffron/phases/**` is forbidden.
  The cell's own callback marks the switch, so `run_rebut` needs no edit.
- **The size of `REBUT_CAP_USD`.** It stays $10.00.
- **The task budget and the batch.** The reserve is REBUT's own. Its spend
  is counted as any REBUT spend is today.
- **The protected text.** This spec's own commit updates `DESIGN.md` §5.6
  and §5.7 and amends ADR 4.

## Notes for the agent

**Each criterion pins text the change keeps.** The cap's constant stays at
$10.00, so criterion 1 mutates it. The rebuttal cut's line stays as it is,
so criterion 2 mutates that literal. `SA-0276` leaves the cut check
comparing the cap's flag with `REBUTTAL_UNJUDGED`, and criterion 3 widens
that flag. The reserve's own constant and the pool are new code, so no
mutant names them. If you restructure a line a mutant names, the mutant
does not apply and `witness` reports it as such.

**After `SA-0276`**, `rebut_state` returns `REBUTTAL_UNJUDGED` where it
returns `REBUTTING` at base (`saffron/phases/rebut.py:501-518`). The cell's
cut check compares against that state (`saffron/cell/session.py:3427` at
base). Read both at your own base before you edit.

**A prototype at `841a62e1`** kept every change inside
`saffron/cell/session.py`. It gave `_RebutCap` the reserve, opened the
verdict pool from `_rebut_critic_container` before the critic cell is built,
and cleared the rebuttal half's refusal there. It chose the line from which
half the pool was in when the cut came.

**The witnesses drive `_rebut_capped`** (`tests/test_session.py:4717-4791`),
and read each REBUT session's budget with `_rebut_turn_options` (`:4696`).
Write each expected budget as a dollar literal. A witness that reads the
reserve's constant back passes whatever value the constant holds.

**A refused call consumes no scripted turn.** The cap raises before the fake
agent runs, so the next scripted turn goes to the next call. A failed
rebuttal turn buys no extraction either (`saffron/phases/rebut.py:211-216`).
So where the extraction never runs, the verdict takes the turn scripted for
the extraction. Give that turn the verdict's own answer. `_rebut_capped`'s
`extracted` argument sets it. Criterion 3's two failures ride on the same
slot: plain text with no structured output, and a scripted
`implement.AgentFailed` costing less than the pool.

**Criterion 1's cases**, each with one commit unless named. The verdict pool
is the reserve plus the cap less the rebuttal turns' spend, floored at the
reserve.

| case | rebuttal | extraction | verdicts | budgets asserted |
|---|---|---|---|---|
| under the cap | $6.00 | $2.50 | $1.00 | $10.00, $4.00, $3.50 |
| summing past it | $6.00 | $4.50 | $0.75 | $10.00, $4.00, $2.00 |
| landing on it | $10.00 | refused | answered | $10.00, $2.00 |
| running past it | $10.25 | refused | answered | $10.00, $2.00 |
| failing at it | cut at $10.00 | not run | answered | $10.00, $2.00 |
| two lenses | $5.00 | $1.00 | $1.50, $0.50 | $10.00, $5.00, $6.00, $4.50 |

Each ends `READY_FOR_REVIEW`, since each verdict withdraws its blocker.

**Criterion 2's cases.** The verdict that spends its pool runs $6.00, $2.50,
then a budget cut costing $3.50. The verdict the pool refuses follows a
first lens that spent it: $6.00, $4.50, $2.25, then a second lens. The two
rebuttal-half cuts have no commit. One is a rebuttal turn cut at $10.00. The
other is a $10.25 turn whose extraction is refused. For each, read the line
from `rebuttal.json` and from the last REBUT `PhaseStart`. Assert each case
ends `EXHAUSTED` with no rebut result and its blocker standing. Assert the
verdict's line does not begin with the rebuttal cut's text. Assert the
rebuttal cut's line begins with it and names no verdict and no $2.00.

**Criterion 3's cases** run $10.25 with one commit, so the extraction is
refused and the verdict starts with $2.00. A verdict that never started
ends `GATE_ERROR` first and is not one of them. Assert the state, a rebut result
that is not `None`, and a line that does not say it ran out.

**At base each new witness fails in its body.** None imports a name this
change adds. The prototype ran all three red against the unchanged source.

**`saffron/cell/**` is in `elevate_on`**, so this task runs `elevated` and
`size` blocks.

**The `prose` gate** counts every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence over
25 words.

**Size.** The prototype measured 576 changed tokens with `size_gate`'s
counter, against the `bug` ceiling of 1300. It held the source change, the
four test updates and the three witnesses. It lacked the two comment
updates. `estimated_lines` is that count over four, plus a margin for them.
