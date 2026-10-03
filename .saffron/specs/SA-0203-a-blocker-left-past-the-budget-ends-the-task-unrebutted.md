---
id: SA-0203
title: A blocker REVIEW leaves past the budget ends the task EXHAUSTED, unrebutted
type: feature
priority: 1
depends_on: [SA-0202]
estimated_lines: 257
estimate_measured: true
touches:
  - saffron/cell/session.py
  - saffron/events.py
  - tests/test_session.py
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
  - saffron/ledger.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/record/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/phases/**
  - saffron/report/**
  - saffron/cell/runtime.py
  - saffron/cell/worktree.py
  - saffron/cell/proxy.py
  - saffron/cell/runtimes/**
  - tests/test_batch.py
  - tests/test_rebut.py
  - tests/test_ledger.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 32
max_attempts: 3
max_turns: 150
acceptance:
  - claim: >-
      A task whose REVIEW leaves an anchored blocker with its spend at or past
      `budget_usd` runs REBUT once instead of ending `EXHAUSTED`. Its rebuttal
      turn, its extraction turn and its verdict each run once, and each lands
      as a `REBUTTING` attempt row. So REBUT's spend is counted in all three
      places that read a task's spend: the outcome's `spent_usd`,
      `ledger.task_spend`, and `ledger.batch_spend` for a batch holding the
      task's run. The witness drives a task past its budget and a task at
      exactly its budget.
    witness: tests/test_session.py::test_a_blocker_left_past_the_budget_is_rebutted_once_and_its_spend_recorded
    mutant:
      file: saffron/cell/session.py
      find: "spent += result.cost_usd"
      replace: "spent += 0.0"
    wrong_versions:
      - REBUT still refused once the spend reaches the budget, so the task ends `EXHAUSTED`.
      - REBUT runs and its cost is never added to the task's spend.
      - The REBUT sessions past the budget run through an agent that skips `record_attempts`, so no attempt row is written.
      - A second rebuttal turn runs past the budget.
  - claim: >-
      A REBUT that starts at or past the budget leaves exactly one `Budget`
      event, emitted after REBUT returns. Its `value` is the task's spend
      after REBUT, its `limit` is `budget_usd`, and it carries what REBUT's
      own sessions spent. It renders as the line the notes give, naming REBUT
      and that figure. REBUT's start emits no `Budget` line that says the
      task is stopping. The witness drives a task past its budget and a task
      at exactly its budget, neither of which asks for a notes turn.
    witness: tests/test_session.py::test_a_rebut_past_the_budget_leaves_one_budget_line_naming_its_spend
    wrong_versions:
      - The base's stopping line is still emitted when REBUT starts, beside the new line.
      - The trigger is `>` rather than `>=`, so a REBUT at exactly the budget emits no line.
      - The figure is the task's whole spend past the budget, not REBUT's own spend.
      - The event's `value` is the spend before REBUT ran.
      - No `Budget` event, only a REBUT phase line.
  - claim: >-
      Past the budget, REBUT's sessions share one cap of $7.00. Each
      session's `max_budget_usd` is $7.00 less what REBUT's earlier sessions
      cost, a failed session's cost included. That holds for the rebuttal
      turn, its extraction turn and a verdict session, at or past the
      budget. Once those sessions have cost $7.00 or more, no further session
      starts, and the fifth criterion says how the task ends. The witness
      drives a cap spent by a rebuttal turn that succeeds, by one
      that fails, and by the extraction turn. A REBUT that starts under the
      budget is unchanged: each session keeps `critic_budget`'s ceiling, and
      no `Budget` event is emitted.
    witness: tests/test_session.py::test_a_rebut_past_the_budget_shares_one_cap_and_stops_when_it_is_spent
    wrong_versions:
      - Every REBUT session gets the whole $7.00, so the cap bounds one session rather than the phase.
      - Past the budget, REBUT keeps `critic_budget`'s $2.00 floor per session and no shared cap.
      - The trigger is `>` rather than `>=`, so a REBUT at exactly the budget keeps the $2.00 floor.
      - A failed session's cost is not counted against the cap.
      - The cap also applies to a REBUT that starts under the budget.
      - A session still starts once the cap is spent, at a floor such as `REVIEW_FLOOR_USD`.
      - The cap is checked only before the extraction turn, so a verdict session starts after the extraction turn spent it.
      - A cap of $6.40, the measured maximum before rounding.
      - A `Budget` event after every REBUT, under the budget too.
  - claim: >-
      `describe` renders a `Budget` event that carries REBUT's figure as the
      line the notes give, and one that does not as the base's stopping line,
      unchanged. Both kinds survive `EventLog.append` and `read_log` equal to
      the event written.
    witness: tests/test_events.py::test_a_rebut_overrun_budget_line_names_rebut_and_survives_the_log
    mutant:
      file: saffron/events.py
      find: 'of ${event.limit:.2f} — stopping"'
      replace: 'of ${event.limit:.2f} — halting"'
    wrong_versions:
      - The stopping line rendered for every `Budget` event.
      - REBUT's figure typed so `read_log` drops the field or the line.
  - claim: >-
      A REBUT the cap cut short ends `EXHAUSTED`, a decided state, with its
      anchored blockers standing and no `rebut_result` on the outcome. That
      holds where `run_rebut` would have halted at `REBUTTING` because the cap
      refused a session. The ledger's task row reads `EXHAUSTED`,
      `rebuttal.json` is still written, and the budget line still carries
      REBUT's figure. The witness drives a cap spent by a rebuttal turn that
      succeeds, by one that fails, and by the extraction turn. Two shapes
      keep their base outcome. A fix claimed and never committed, with the
      cap not spent, halts at `REBUTTING` with its `rebut_result`. A refused
      extraction turn followed by a red gate re-run ends `EXHAUSTED` with its
      `rebut_result` kept.
    witness: tests/test_session.py::test_a_rebut_the_cap_cut_short_ends_exhausted_with_its_blockers_standing
    wrong_versions:
      - A cut-short REBUT left halted at `REBUTTING`.
      - A cut-short REBUT ends `EXHAUSTED` and keeps its `rebut_result`.
      - Every REBUT past the budget that would halt at `REBUTTING` ends `EXHAUSTED`, cap refusal or not.
      - A cap refusal also discards the `rebut_result` of a red gate re-run.
      - A cut-short REBUT ends `GATE_ERROR`, charged to nobody.
      - A cut-short REBUT emits no budget line.
---

## Context

Backlog item **b-4c5dc7**, found in the spec loop's run 24 on 2026-10-01. It
cites `DESIGN.md` §3 and §5.5. Every line number below was read at
`0fecec0c`.

**What happens past the budget today.** `_over_budget` returns `False`
while the task's spend is under `budget_usd`. At or past it, it emits a
`Budget` event and returns `True` (`saffron/cell/session.py:2194-2208`).
`describe` renders that event as the spend, the budget and the word
`stopping` (`saffron/events.py:799`). REVIEW is not gated on it. Each lens,
criterion probe and wrong-version session is capped at
`critic_budget(spec.budget_usd, spent)` (`saffron/cell/session.py:2705`).
That is the remainder, floored at `REVIEW_FLOOR_USD`, $2.00
(`saffron/cell/session.py:79`, `:141-143`). The host adds REVIEW's cost to
`spent` after every session has run (`saffron/cell/session.py:2887-2894`).
REBUT is gated. When REVIEW routes to `REBUTTING`, the host calls
`_over_budget` before the rebuttal turn. If it returns `True`, the outcome is
`EXHAUSTED` and no REBUT session runs (`saffron/cell/session.py:2917-2921`).

**The two cells.** Both event logs are under `~/.saffron/batches/v0/`.

- `SA-0162` declared $37.00. Its gates went green at $39.72. Its notes-turn
  check emitted the stopping line then (`saffron/cell/session.py:2564`), and
  REVIEW ran on. Four lenses, 11 criterion probes and the wrong-version sweep
  brought it to $57.36. One blocker. REBUT's check emitted a second stopping
  line at $57.36, and the task ended `EXHAUSTED`.
- `SA-0151` declared $25.00. It went green at $21.31 and REVIEW ran to
  $30.67. Two blockers. REBUT's check emitted the stopping line at $30.67,
  and the task ended `EXHAUSTED`.

Each blocker was a test fix of a few lines. The operator opened #626 and
#628 by hand.

**What REBUT's sessions are.** `run_rebut` runs the rebuttal turn and its
extraction turn in the implementer's session. Then it runs one verdict
session per lens that filed a blocker. Each gets its own
`max_budget_usd` from the one `budget_usd` it is handed
(`saffron/phases/rebut.py:678-681`, `:748-771`). The host hands it
`critic_budget(spec.budget_usd, spent)` (`saffron/cell/session.py:2982`).
`run_rebut` calls the `agent` it is given for every one of those sessions
(`saffron/cell/session.py:2996`). That `agent` is built once per task,
wrapped in `record_attempts` (`saffron/cell/session.py:2045-2055`).
`record_attempts` opens one attempt row per turn, under the task's current
state, and closes it with the turn's cost
(`saffron/cell/session.py:189-212`, `saffron/ledger.py:1314-1336`). The REBUT
branch sets the state to `REBUTTING` before any turn
(`saffron/cell/session.py:2918`). The host adds REBUT's cost to `spent` after
`run_rebut` returns (`saffron/cell/session.py:3003-3004`).

**How a batch sees a task's spend.** `ledger.task_spend` sums the task's
attempt rows (`saffron/ledger.py:1368-1378`). `ledger.batch_spend` sums every
attempt row of every run in the batch, with no filter on phase
(`saffron/ledger.py:1160-1185`). The batch checks it before each task, against
the budget less its reserve (`saffron/batch.py:239-243`).

**The cap, measured.** The ledger at `~/.saffron/ledger.db` held 53 tasks
with a `REBUTTING` attempt on 2026-10-03. Summed per task, the REBUT spend
was this.

| statistic | REBUT spend |
|---|---|
| minimum | $0.28 |
| median | $1.82 |
| mean | $2.11 |
| 75th percentile | $3.05 |
| 90th percentile | $3.43 |
| 95th percentile, nearest rank | $4.45 |
| maximum, `SA-0167` | $6.40 |

The next four were $4.82, $4.45, $3.88 and $3.61. The cap is the maximum,
rounded up to the next whole dollar: $7.00. One session in the sample hit
its own per-session ceiling (`SA-0087`, $3.09, `error_max_budget_usd`), so
that task's total is a floor. A cap below what a REBUT needs refuses its
last sessions, and the rebuttal is unjudged. That wastes everything REBUT
already spent past the budget. A cap at the 95th percentile would have cut
`SA-0167` and `SA-0126`, and met `SA-0027`'s spend exactly.

## Problem

Past the budget, the night pays for REVIEW and then refuses the REBUT that
would answer it. Let one REBUT run past the budget, under a fixed cap.

**This replaces the item's two arms.** b-4c5dc7's "Done looks like" offers
two: hold back REBUT's share before REVIEW, or skip REVIEW and package the
green patch. The operator chose neither on 2026-10-03, and chose a bounded
REBUT past the budget instead. REVIEW runs as it does today.

1. **The trigger.** REVIEW routes to `REBUTTING` with the task's spend at or
   past `budget_usd`. REBUT then runs, and the task no longer ends
   `EXHAUSTED` there. Decide it without calling `_over_budget`, because
   that emits the stopping line.
2. **The cap.** Declare $7.00 as a module constant in
   `saffron/cell/session.py`, beside `REVIEW_FLOOR_USD`. Its comment names
   the measurement above in one or two lines. Past the budget, REBUT's
   sessions share it. Each session's `max_budget_usd` is the cap less what
   REBUT's earlier sessions cost, the cost of a failed session included. A
   session that would get nothing or less is not started. Refuse it the way
   a failed turn reads to its caller, with `implement.AgentFailed`. Then
   `run_rebuttal` and `run_verdict` treat it as they treat any failed
   session, so the rebuttal is unjudged. `rebut_state` then gives
   `REBUTTING`, either because nothing was recorded
   (`saffron/phases/rebut.py:500-508`) or because a verdict errored
   (`saffron/phases/rebut.py:516-517`). The cell enforces `max_budget_usd`
   itself, so one session can still run a turn past its own ceiling
   (`DESIGN.md` §4.3). The cap bounds which sessions start, not REBUT's
   spend to the cent.
3. **One REBUT.** REBUT already runs at most once per task, and stays so.
4. **A cut-short REBUT is decided.** `REBUTTING` is an in-flight state. A
   task that stops there after its process exits is a halt, and a stack
   batch escalates a halt that nothing then decides. So the host records
   which sessions the cap refused. Suppose the cap refused one, and
   `run_rebut` returned `REBUTTING`. The task ends `EXHAUSTED`, and the
   outcome's `rebut_result` is `None`, as if REBUT had not run. The
   blockers stand unanswered. `rebuttal.json` and the ledger's rebuttal
   rows are still written, because the sessions ran and were paid for.
   The `why` line names the cap. Every other `run_rebut` result keeps its
   state and its `rebut_result`. That covers a red gate re-run after a
   refused extraction turn, which `run_rebut` already ends `EXHAUSTED`
   (`saffron/phases/rebut.py:716-724`).
5. **The record.** Every REBUT session still goes through `record_attempts`,
   so its cost lands on an attempt row. After `run_rebut` returns, the host
   adds its cost to the task's spend as it does today. It then emits one
   `Budget` event: `ceiling` `budget_usd`, `value` the spend after REBUT,
   `limit` `budget_usd`, and REBUT's own spend in a new optional field
   defaulting to `None`. REBUT's own spend is the sum of its sessions' costs,
   the figure `run_rebut` reports.
6. **The line.** `describe` renders a `Budget` event whose new field is set
   as the line in the notes. One whose field is `None` keeps the base's
   stopping line. Add one `FAMILIES` row for the new line, citing
   `cell/session.py:_drive_cell`.
7. **Under the budget, nothing changes.** A REBUT that starts under
   `budget_usd` keeps `critic_budget(spec.budget_usd, spent)` and emits no
   `Budget` event.

**A batch.** No change to `saffron/batch.py`. REBUT's sessions past the
budget are attempt rows like any other, so `batch_spend` counts them, and the
check before the next task sees them. A night can still end one task's
overshoot past its budget, as `DESIGN.md` §3.2 says. That overshoot now
includes at most one REBUT, held to the cap. The reserve is untouched.

## Out of scope

- **The notes turn's stopping line.** `SA-0162`'s first stopping line came
  from the notes-turn check (`saffron/cell/session.py:2564`), and REVIEW ran
  after it. It stays as it is.
- **A REBUT that starts under the budget and crosses it.** Its sessions keep
  `critic_budget`'s ceiling, one remainder each, as today.
- **`DESIGN.md`.** §4.3 and §5.6 said REBUT checks the ceiling before its
  turn. The operator edits both by hand in this spec's pull request.
- **An `EXHAUSTED` task with green gates opening a pull request.** That is
  b-038aef. Its spec routes on the shape step 4 leaves: `EXHAUSTED`, an
  anchored blocker and no `rebut_result`.

## Notes for the agent

**New or edit.** Criteria 1 and 4 declare a mutant on text the base already
determines, and the change keeps it. Criteria 2, 3 and 5 build new code.
This spec cannot know its spelling, so each declares a witness and no
mutant.
`witness` reports `skip` for them.

**The line** for a `Budget` event whose spend after REBUT is $63.10, whose
budget is $37.00, and whose REBUT spent $5.74 is exactly this.

```
budget: $63.10 of $37.00 — REBUT ran past it, spending $5.74
```

**One helper for the four session witnesses.** Put it in
`tests/test_session.py` beside `_through_rebut` (`:3508`). It takes the
three REBUT turn costs in order (rebuttal, extraction, verdict) and a
`budget_usd`. Three more keywords default to the common case. They are the
commits after the rebuttal (one), the extraction turn's output (the argued
answer) and the stub's `suites` (none). It builds the turns itself rather than through
`_through_rebut`. The plan turn, the implement turn and all four lens turns
each cost $0.125, so REBUT starts at exactly $0.75. The first lens files
`_BLOCKER`, and the other three file no findings. The rebuttal turn says
the blocker is intentional. The extraction turn argues finding 1, and the
verdict turn withdraws it.

- Build the cell with `_stub_the_runtime` (`tests/test_session.py:909`).
- Pass it `_ANCHORING_DIFF` as its patch (`tests/test_session.py:3479`).
- Call `_rebuttable` with the commits after the rebuttal
  (`tests/test_session.py:3490`).
- Drive it with `_drive` and a `capture` list (`tests/test_session.py:1229`).
- The double appends each turn's prompt to `cell.turns`
  (`tests/test_session.py:1306`).
- It appends each turn's options to `cell.turn_options`
  (`tests/test_session.py:1312`).

A REBUT session is a turn whose prompt is `rebut.EXTRACT_PROMPT`,
`rebut.VERDICT_TURN_PROMPT`, or starts with the rebuttal prompt's fixed
text.

**Criterion 1's witness** runs twice. With costs $1.50, $0.50 and $0.75
and a budget of $0.25, it asserts all of these.

- The state is `READY_FOR_REVIEW`.
- The task's `REBUTTING` attempt rows, in order, cost $1.50, $0.50 and
  $0.75.
- `outcome.spent_usd` and `ledger.task_spend` are both $3.50.
- A batch made with `ledger.create_batch`, holding the run through
  `attach_run_to_batch`, has a `batch_spend` of $3.50.

Then it runs once more with a budget of exactly $0.75. It asserts the
state `READY_FOR_REVIEW` and the same three `REBUTTING` rows.

**Criterion 2's witness** runs the helper with costs $1.50, $0.50 and
$0.75 and a budget of $0.25. It asserts exactly one `Budget` event in the
capture, with `value` $3.50, `limit` $0.25 and REBUT's figure $2.75. That
event's line is exactly this.

```
budget: $3.50 of $0.25 — REBUT ran past it, spending $2.75
```

No watched line contains `stopping`. Then it runs the same costs with a
budget of exactly $0.75, and asserts one `Budget` event whose line is
exactly this.

```
budget: $3.50 of $0.75 — REBUT ran past it, spending $2.75
```

**Criterion 3's witness** runs six times, each asserting the REBUT
sessions' `max_budget_usd` values in order, and the state.

- Costs $3.00, $2.50 and $1.00, budget $0.25: $7.00, $4.00 and $1.50, and
  `READY_FOR_REVIEW`.
- The same costs at a budget of exactly $0.75: the same three values, and
  `READY_FOR_REVIEW`.
- Costs $7.25, $0.50 and $0.75, budget $0.25: $7.00 alone, and `EXHAUSTED`.
  The extraction turn never starts.
- A rebuttal turn that raises `implement.AgentFailed` carrying a $7.25
  attempt, budget $0.25: $7.00 alone, and `EXHAUSTED`. `run_rebuttal` buys
  no extraction turn after a failed one, so the verdict is the session the
  cap refuses.
- Costs $3.00, $4.50 and $0.75, budget $0.25: $7.00 and $4.00, and
  `EXHAUSTED`.
- Costs $1.50, $0.50 and $0.75, budget $20.00: $19.25 three times. The
  capture holds no `Budget` event.

Give the helper an exception in place of the rebuttal cost for the fourth
run. The double records the turn's options first (`tests/test_session.py:1312`).
Then it raises a scripted `BaseException` as that turn
(`tests/test_session.py:1322-1323`). Compare dollar values with
`pytest.approx`. The witness drives one lens's verdict session. Blockers
from two or more lenses get one verdict session each, and no witness drives
the cap across them.

**Criterion 4's witness** builds both events by hand, with the figures in
**The line** above, and a stopping event at $9.00 of $9.00. It asserts each
line exactly, appends both to an `EventLog`, and asserts `read_log` returns
both, equal.

**Criterion 5's witness** runs the helper five times at a budget of $0.25.
The first three are criterion 3's three cut-short runs. Each asserts all of
these.

- The state is `EXHAUSTED`, and `outcome.rebut_result` is `None`.
- `review.anchored_blockers(outcome.reviews)` returns one finding.
- The ledger's one queue line reads `EXHAUSTED`.
- The capture holds one `Budget` event, and it carries REBUT's figure.
- `rebuttal.json` exists in the task's directory.

The fourth run costs $1.50, $0.50 and $0.75, with no commit after the
rebuttal. Its extraction turn returns `_CLAIMED_FIX`
(`tests/test_session.py:3487`). It asserts `REBUTTING` and a
`rebut_result` that is not `None`.

The fifth run costs $7.25, $0.50 and $0.75, with `suites` green, green,
then one failure. That is the shape
`test_gates_red_after_the_rebuttal_exhausts_and_keeps_the_diff` uses. It
asserts `EXHAUSTED` and a `rebut_result` that is not `None`.

**Keep what other tests read.** `tests/test_events.py:1215-1216` pins
`FAMILIES` at 69 rows. The new row makes it 70, and its docstring names this
spec beside the others that moved it.

**Wrong versions these witnesses must kill.** On 2026-10-03 every version
listed under the criteria was applied to a prototype, and its witness failed
it. So did both mutants. Criterion 1's first version is the base itself.
Each witness failed with the prototype's source reverted to the base.

**The `prose` gate** reads every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence over
25 words.

**Size.** `saffron/cell/**` is in `elevate_on`, so `size` blocks here. A
prototype with all five witnesses, counted by `size_gate`, came to 1025
tokens against the `feature` ceiling of 3000. Re-indenting the REBUT branch
counts no tokens. `estimated_lines` is those tokens over four.
