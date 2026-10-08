---
id: SA-0231
title: REBUT inherits the task's remainder, and a rebuttal its budget cut reads as one that said nothing
type: bug
priority: 1
depends_on: [SA-0230]
estimated_lines: 184
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
  - saffron/ledger.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/scheduler.py
  - saffron/reconcile.py
  - saffron/intake.py
  - saffron/events.py
  - saffron/record/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/phases/**
  - saffron/report/**
  - saffron/cell/runtime.py
  - saffron/cell/worktree.py
  - saffron/cell/proxy.py
  - saffron/cell/runtimes/**
  - tests/test_rebut.py
  - tests/test_events.py
  - tests/test_reconcile.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 28
max_attempts: 3
max_turns: 130
acceptance:
  - claim: >-
      REBUT's sessions share one $10.00 cap whatever the task has left of
      `budget_usd`. Each session's `max_budget_usd` is $10.00 less what
      REBUT's earlier sessions cost, for the rebuttal turn, its extraction
      turn and the verdict. No session inherits the task's remainder or
      `REVIEW_FLOOR_USD`. A REBUT whose rebuttal turn spends the cap, and
      which `run_rebut` would halt at `REBUTTING`, ends `EXHAUSTED`. A
      re-run's own end stands, as criterion 2 says. The witness drives five
      budgets. Two leave a remainder
      larger than the cap ($20.00) or between the floor and the cap ($3.75).
      One leaves less than the floor ($1.00), one exactly none ($0.75), and
      one less than none ($0.25). A `Budget` event follows only a REBUT that
      started at or past the budget, as at base, so the two that cross it
      during REBUT emit none.
    witness: tests/test_session.py::test_rebut_draws_on_its_own_cap_whatever_the_task_has_left
    mutant:
      file: saffron/cell/session.py
      find: '{"max_budget_usd": remaining}'
      replace: "{}"
    wrong_versions:
      - The cap still applies only once the spend reaches the budget, so a REBUT under it keeps the remainder per session.
      - The pool is the smaller of the cap and the floored remainder, so a task with $1.00 left gives REBUT $2.00.
      - The pool is the larger of the cap and the remainder, so a task with $19.25 left gives REBUT $19.25.
      - Every REBUT session gets the whole $10.00, so the cap bounds one session rather than the phase.
      - The cap is wrapped under the budget, and the cut-short end to `EXHAUSTED` still fires only past it.
      - A `Budget` event after every REBUT, under the budget too.
      - A `Budget` event whenever the spend after REBUT is at or past the budget, so a REBUT that crosses it says REBUT ran past it.
      - A cap of $7.00, SA-0203's figure, which cuts the measured $9.29 REBUT.
      - A cap of $9.29, the measured maximum before rounding.
  - claim: >-
      A REBUT the cap cut short, where `run_rebut` would halt at
      `REBUTTING`, ends `EXHAUSTED`. Its blockers stand and it has no
      `rebut_result`, under the budget as well as past it. Its REBUT phase
      line and the `why` in `rebuttal.json` both say REBUT ran out of its
      $10.00 budget, a figure read from `REBUT_CAP_USD`. Neither says the
      rebuttal moved no commit or made no argument. A red re-run's
      `EXHAUSTED` and an errored re-run's `GATE_ERROR` stand, each with its
      `rebut_result`, after the cap refused the extraction turn. The witness
      drives each case in each of criterion 1's five budgets. The cuts are a
      rebuttal turn the cap ends with nothing committed, an extraction turn
      the cap refuses, and a verdict session the cap ends. A rebuttal turn
      that fails for another reason, before REBUT's sessions spend the cap,
      still halts at `REBUTTING` with the words it has at base. With the
      constant set to $8.00, the line says $8.00.
    witness: tests/test_session.py::test_a_rebuttal_the_cap_cut_reads_as_out_of_budget_not_as_silence
    mutant:
      file: saffron/cell/session.py
      find: "if self.spent >= self.cap:"
      replace: "if False:"
    wrong_versions:
      - The cap's words are prefixed to the old line, so it still says the rebuttal moved no commit and made no argument.
      - The phase line says REBUT ran out of its budget, and `rebuttal.json` keeps the old words.
      - Every REBUT that would halt at `REBUTTING` ends `EXHAUSTED`, a crashed rebuttal turn the cap never cut included.
      - The cut is read only from the rebuttal turn's error, so a verdict session the cap ends leaves the task at `REBUTTING`.
      - The cut is read from the session's `error_max_budget_usd` subtype, so an extraction turn the cap refuses before it starts leaves the task at `REBUTTING`.
      - The out-of-budget line is written only past the budget, and under it the task ends `EXHAUSTED` with the old words.
      - Any cap refusal turns the outcome into `EXHAUSTED`, so an errored re-run after a refused extraction turn ends `EXHAUSTED`, not `GATE_ERROR`.
      - Any cap refusal discards the `rebut_result`, so a red re-run after a refused extraction turn loses it.
      - The line spells $10.00 as a literal, so a cap set to $8.00 still reads $10.00.
      - The override keys on the pool's spend reaching the cap, not on a refusal, so a claimed fix with no commit after an extraction that spends the cap reads as out of budget.
---

## Context

Backlog item **120**, found running the spec loop on 2026-09-14. It cites
`DESIGN.md` §3.3, §4.2 and §5.6. Every line below was read at `958db033`.

**What REBUT is given under the budget.** REVIEW routes to `REBUTTING`, and
the host reads whether the task is at or past `budget_usd`
(`saffron/cell/session.py:3024`). Under it, no cap is built
(`saffron/cell/session.py:3048`). `run_rebut` gets
`critic_budget(spec.budget_usd, spent)` (`saffron/cell/session.py:3087`).
That is the remainder, floored at `REVIEW_FLOOR_USD`, $2.00
(`saffron/cell/session.py:83`, `:149-151`). That figure is the rebuttal and
extraction turns' `max_budget_usd` (`saffron/phases/rebut.py:681`). It is
each verdict session's `budget_usd` too (`saffron/phases/rebut.py:769`).
It is not decremented between them.

**What REBUT is given past the budget.** `SA-0203` built `_RebutCap`
(`saffron/cell/session.py:154-192`). Its pool is `REBUT_OVERRUN_CAP_USD`,
$7.00 (`saffron/cell/session.py:85-87`). Each wrapped call's own
`max_budget_usd` is the pool less what REBUT's earlier sessions cost. A call
with nothing left raises `implement.AgentFailed` and marks the pool
refused. So does a failed call that brings the spend to the pool
(`saffron/cell/session.py:172-191`). The wrapper's figure replaces the one
`run_rebut` passed in.

**A re-run's own end.** A rebuttal that committed reaches the gate re-run
even when the pool refused its extraction turn. An aborted or drifted
re-run is `GATE_ERROR` (`saffron/cell/session.py:3042-3043`), a red one
`EXHAUSTED`, and `run_rebut` returns either as it is
(`saffron/phases/rebut.py:716-724`). The host turns only a `REBUTTING`
result into `EXHAUSTED` (`saffron/cell/session.py:3147`).

**How a cut reads today.** A rebuttal turn that fails comes back as an
error with no rebuttals (`saffron/phases/rebut.py:210-215`). With HEAD
unmoved, `run_rebut` returns `rebut_state`'s halt without re-running the
gates (`saffron/phases/rebut.py:710-714`). That halt is `REBUTTING`, and
its line reads "the rebuttal moved no commit and made no argument", then
the error (`saffron/phases/rebut.py:500-509`). The host writes
`rebuttal.json` from that result (`saffron/cell/session.py:3107-3109`).
Only when the pool was built does it turn the halt into `EXHAUSTED`. The
line then becomes the cap's figure prefixed to the old words
(`saffron/cell/session.py:3136-3155`). So past the budget the old words
survive inside the new line. Under the budget the task halts at
`REBUTTING`, which item 120 measured on `SA-0087`. Its rebuttal session
had $3.09 left and spent it with no output.

**The cap, re-measured.** On 2026-10-07 the ledger at
`~/.saffron/ledger.db` held 67 tasks with a `REBUTTING` attempt. Their
REBUT spend, summed per task, had a median of $2.41. The two highest were
$9.29 (`SA-0223`) and $6.40 (`SA-0167`), and the next was $5.82.
`SA-0223`'s REBUT started with $7.87 of its $26.00 left. Its rebuttal turn
cost $6.68, its extraction $2.12 and its verdict $0.50. A $7.00 cap
leaves its extraction turn $0.32, so that turn is cut or refused. So the cap
follows `SA-0203`'s own rule on the new sample, the maximum rounded up to
the next whole dollar: $10.00.

## Problem

REBUT's budget is whatever the task has left, so a rebuttal can start with
$2.00 or with $19.00. When the budget does cut it, the task halts at
`REBUTTING` in words that also describe an implementer that chose silence.

The operator decided both parts on 2026-10-07.

1. **REBUT's budget is its own ceiling, always.** Build the pool for every
   REBUT, at any spend, and wrap every REBUT session in it. Set it to
   $10.00. Rename the constant `REBUT_CAP_USD`, since it no longer applies
   only past the budget. Its one-line comment cites the re-measurement: 67
   REBUTs, a maximum of $9.29 (`SA-0223`), 2026-10-07. Pass `run_rebut` the
   cap's figure, not `critic_budget(...)`. The wrapper replaces it on every
   call anyway. A REBUT the cap cuts short, where `run_rebut` would halt
   at `REBUTTING`, now ends `EXHAUSTED` where a large remainder used to
   carry it on. That is the cost of a ceiling of its own.
   REVIEW keeps `critic_budget` and its floor, unchanged
   (`saffron/cell/session.py:2805`).
2. **A cut reads as a cut.** Say the pool refused a session and
   `run_rebut` returned `REBUTTING`. The task then ends `EXHAUSTED` with no
   `rebut_result`, under the budget as past it. Any other result stands,
   a red re-run's `EXHAUSTED` and an errored re-run's `GATE_ERROR` included,
   with its `rebut_result`. Replace `run_rebut`'s line
   before `rebuttal.json` is written. The new line starts with "REBUT ran
   out of its $10.00 budget", the figure read from `REBUT_CAP_USD` when the
   line is written. The error
   of the session the cap ended can follow it. It never carries the old
   line. `rebuttal.json` keeps `run_rebut`'s own `state`.
3. **The `Budget` event is unchanged.** It still follows only a REBUT that
   started at or past the budget. Its line says REBUT ran past the budget,
   which a REBUT that started under it did not do.

## Out of scope

- **`REBUTTING` after the cell exits.** `REBUTTING` is in
  `reconcile.IN_FLIGHT_STATES` (`saffron/reconcile.py:56-67`), and
  `DEPENDENCY_WAITING_STATES` excludes it (`saffron/scheduler.py:99`).
  Whether such a halt gets a terminal state of its own is the operator's
  decision, so item 120 stays open on that part.
- **The words for a halt the budget did not cause.** `rebut_state` keeps
  its line for a rebuttal that moved nothing and argued nothing. It stays
  true there.
- **IMPLEMENT's salvage reserve.** That is `SA-0230`, which this spec
  depends on because both edit the budget constants at the top of
  `saffron/cell/session.py`.
- **`DESIGN.md`, ADR 4 and `CONTEXT.md`.** §3.3, §4.3, §5.6 and §5.7 said
  the cap applies past the budget only. ADR 4 and the `EXHAUSTED` entry in
  `CONTEXT.md` said so too. The operator edited each by hand in
  this spec's pull request.
- **One more witness run.** Add a `_rebut_capped` run costing $6.00 then
  $4.50, with `extracted=_CLAIMED_FIX` and `rebut_commits=0`. It is not cut,
  so it halts at `REBUTTING` with the words it has at base.

## Notes for the agent

**Edit, not new.** Both mutants pin text `_RebutCap.wrap` already holds,
and the change keeps that method's body as it is. Criterion 1's mutant
drops the per-call ceiling, and criterion 2's stops a failed session that
spends the pool from marking it refused.

**`SA-0230` lands first, in the same file.** It adds an IMPLEMENT
`max_budget_usd` near the top of `_drive_cell`. Re-grep each mutant's `find`
after that merge, and match on text, never on the line numbers below. On
2026-10-07 `SA-0230`'s prototype was applied under this spec's prototype.
Each `find` still matched exactly once. Both new witnesses failed with
only `SA-0230` applied, and every wrong version and both mutants still
failed them.

**Texts the change makes false.** The comment above the floor says REBUT's
sessions share `REBUT_OVERRUN_CAP_USD` once past the budget
(`saffron/cell/session.py:81-82`). The comment above the cap says the same
(`saffron/cell/session.py:85-86`). The pool class's docstring opens with
"once the task meets or passes budget_usd"
(`saffron/cell/session.py:155-156`). The comment above the pool's
construction opens with "At or past budget_usd"
(`saffron/cell/session.py:3046-3047`). Correct each one.

**Tests that assert the old behaviour.**
`test_a_rebut_past_the_budget_shares_one_cap_and_stops_when_it_is_spent`
(`tests/test_session.py:4107`) runs two REBUTs under the budget, `g` and
`h`, and asserts the remainder's ceilings, $2.00 and $19.25. Delete both
runs, and the docstring sentence that says a REBUT under the budget is
unchanged. Criterion 1's witness covers them now.
Every other figure there and in
`test_a_rebut_the_cap_cut_short_ends_exhausted_with_its_blockers_standing`
(`tests/test_session.py:4173`) assumes a $7.00 cap. Keep every run, and
let the same session spend the new cap. Add $3.00 to the cost of each
first REBUT session that is $2.00 or more, the verdict-cut run's included.
Read $10.00 wherever those tests read $7.00. Each later ceiling and each
state then stays as it is.
The helper below says it drives one cell to `REBUTTING` already past
`budget_usd` (`tests/test_session.py:3974`). It now drives either.

**One helper.** Both new witnesses drive `_rebut_capped`
(`tests/test_session.py:3965`). The plan, implement and four lens turns
each cost $0.125, so REBUT starts at $0.75. Read the REBUT sessions'
ceilings with `_rebut_turn_options` (`tests/test_session.py:3952`). The
five budgets are $20.00, $3.75, $1.00, $0.75 and $0.25. Compare dollar
values with `pytest.approx`. Give each run its own `tmp_path` subdirectory.

**A budget cut, as the cell reports it.** Build the session the cap ends as
`implement.AgentFailed` carrying an `implement.AttemptResult`. Give it
subtype `error_max_budget_usd`, terminal reason `budget_exhausted`, and a
cost. That is the shape `SA-0087`'s REBUT row carried in the ledger.

**Criterion 1's witness** runs two REBUTs per budget.

- Costs $3.00, $2.50 and $1.00. The ceilings are $10.00, $7.00 and $4.50,
  and the state `READY_FOR_REVIEW`. The capture holds one `Budget` event at
  $0.75 and $0.25, and none at the other three.
- Costs $10.25, $0.50 and $0.75. The ceilings are $10.00 alone, and the
  state `EXHAUSTED`.

**Criterion 2's witness** runs six REBUTs per budget. Three are cuts.

- The rebuttal turn raises the budget cut above at $10.00, with no commit
  after it, then $0.50 and $0.75.
- Costs $10.25, $0.50 and $0.75, with one commit after the rebuttal. The
  pool refuses the extraction turn, then the verdict.
- Costs $4.00 and $4.50, then a verdict that raises the budget cut at
  $1.50, with one commit after the rebuttal.

Each cut asserts all of these.

- The state is `EXHAUSTED`, and `outcome.rebut_result` is `None`.
- `review.anchored_blockers(outcome.reviews)` returns one finding.
- The ledger's one queue line reads `EXHAUSTED`.
- The last REBUT `PhaseStart`'s detail and `rebuttal.json`'s `why` each
  contain "REBUT ran out of its $10.00 budget".
- Neither contains "moved no commit" or "made no argument".

Two runs cost $10.25, $0.50 and $0.75, with one commit after the
rebuttal, so the pool refuses the extraction turn. Each passes the helper
`suites` of green, green, then the re-run.

- An errored re-run, one `tests` result with status `error`, asserts
  `GATE_ERROR`.
- A red re-run, one lint failure, asserts `EXHAUSTED`.
- Both assert a `rebut_result` that is not `None`, and a last REBUT line
  without "ran out of".

The sixth run's rebuttal turn raises `implement.AgentFailed`. It carries
what `_cut_off_turn` (`tests/test_session.py:1253`) returns at a cost of
$0.40, with no commit after it. It asserts the state `REBUTTING`. The last
REBUT line contains "moved no commit and made no argument" and not "ran
out of".

Last, outside the loop, set `session.REBUT_CAP_USD` to $8.00 with
`monkeypatch.setattr`. Run the rebuttal-turn cut at $8.00 with a $20.00
budget. Assert `EXHAUSTED` and a line containing "REBUT ran out of its
$8.00 budget". At base the attribute does not exist, so the call raises
inside the test rather than at collection.

**Wrong versions.** On 2026-10-07 a prototype of this change was built at
`958db033`, with the $10.00 cap and both re-figured SA-0203 tests. It was
run again over `SA-0230`'s prototype. Every
wrong version under criteria 1 and 2 was applied to it, and that
criterion's witness failed. So did both mutants. Both new witnesses and the
re-figured cut-short test failed with the source reverted to the base.

**The `prose` gate** reads every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words.

**Size.** `saffron/cell/**` is in `elevate_on`, so `size` blocks here. The
prototype, counted by `size_gate`, came to 735 changed tokens against the
`bug` ceiling of 1300. `estimated_lines` is those tokens over four.
