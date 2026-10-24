---
id: SA-0311
title: REBUT ends a task `EXHAUSTED` on a form gate its own fix turned red, with no repair turn
type: feature
priority: 2
estimated_lines: 309
estimate_measured: true
touches:
  - saffron/repos/policy.py
  - saffron/phases/rebut.py
  - saffron/cell/session.py
  - tests/test_policy.py
  - tests/test_rebut.py
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
  - saffron/agents/**
  - saffron/gates/**
  - saffron/record/**
  - saffron/phases/implement.py
  - saffron/phases/review.py
  - saffron/phases/package.py
  - saffron/report/**
  - saffron/task.py
  - saffron/ledger.py
  - saffron/events.py
  - saffron/cli.py
  - saffron/batch.py
  - tests/test_task.py
  - tests/test_events.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 52
max_attempts: 3
max_turns: 210
acceptance:
  - claim: >-
      A gate declaration in `.saffron/policy.yaml` takes a `form` key beside
      `blocking`. A gate declaring `form: true` loads as a form gate. A gate
      that omits the key is no form gate. The witness drives both values of
      `form` and both values of `blocking`, and neither key moves the other.
    witness: tests/test_policy.py::test_a_gate_declares_itself_a_form_gate_and_defaults_to_none
    wrong_versions:
      - "`form` defaults to true, so a gate that omits it is a form gate."
      - "`form` is derived from `blocking`, so an advisory gate reads as a form gate and a blocking one does not."
  - claim: >-
      `rebut.form_only(new_failures, gates)` says whether a red re-run after
      REBUT earns its one repair turn. It is true only when the new failures
      are not empty and each sits in a gate `gates` declares `form: true`. A
      core gate never earns it, even under a declaration that calls it a form
      gate. The witness drives one form gate, two form gates, no failure, a
      form gate beside a declared gate that is no form gate, and a form gate
      beside an undeclared gate. It drives every name in `CORE_GATE_NAMES`,
      alone and beside a form gate, each declared `form: true`.
    witness: tests/test_rebut.py::test_form_only_earns_the_repair_turn_for_declared_form_gates_alone
    wrong_versions:
      - The core gate check is left out, so a declaration calling `scope` a form gate earns the turn.
      - One form gate among the red ones is enough, so `lint` beside `tests` earns the turn.
      - An empty list earns the turn, as `all` over nothing would.
      - A gate missing from `gates` counts as a form gate.
  - claim: >-
      When REBUT's fix turns form gates alone red, the task gets one repair
      turn before the verdicts. The witness turns `format` and `lint` red
      together, both declared form gates. The repair turn's prompt is the
      repair loop's own, over both gates' new failures. Its `max_budget_usd`
      is what the task's budget has left after REBUT's own turns. Every gate
      then re-runs once, as a second REBUT attempt line, and is green. The
      verdict session runs after the repair turn, and the task ends
      `READY_FOR_REVIEW`. Its spend counts the repair turn.
    witness: tests/test_session.py::test_a_form_gate_red_after_rebut_earns_one_repair_turn_then_the_verdicts
    wrong_versions:
      - The repair prompt carries only the first red gate's failures.
      - The repair turn is capped at the whole `budget_usd`, not what is left of it.
      - The repair turn is capped at REBUT's own cap.
      - The repair turn's cost never reaches the task's spend.
      - The gates do not re-run after the repair turn, so the verdicts read a head no gate judged.
  - claim: >-
      The repair turn runs only while the task's spend is under its
      `budget_usd`, REBUT's own turns counted. The witness drives a form
      gate red at three budgets. Under the spend by one turn, the repair
      turn runs, capped at what is left. Level with the spend, and below it,
      no repair turn runs, no verdict runs, and the task ends `EXHAUSTED`
      with today's line saying REBUT does not re-enter the repair loop.
    witness: tests/test_session.py::test_a_rebut_red_on_a_form_gate_past_the_budget_runs_no_repair_turn
    wrong_versions:
      - The budget check reads the spend before REBUT, so a task REBUT took to its budget still repairs.
      - A task whose spend is level with its budget still repairs.
      - A task too poor to repair still gets the line naming a repair turn.
  - claim: >-
      A red re-run after REBUT that holds any gate other than a form gate
      ends the task `EXHAUSTED` as `DESIGN.md` §5.6 says, with no repair
      turn and no verdict. The witness drives `lint` beside `tests`, a
      declared gate that is no form gate. It drives `lint` beside `witness`,
      a core gate. Each ends with today's line. `lint` alone earns the turn.
    witness: tests/test_session.py::test_a_rebut_red_beyond_the_form_gates_runs_no_repair_turn
    mutant:
      file: saffron/cell/session.py
      find: return "EXHAUSTED" if comparison.new_failures else None
      replace: return None
    wrong_versions:
      - Any red form gate earns the turn, so `lint` beside `tests` is repaired.
      - A core gate counts as a form gate, so `lint` beside `witness` is repaired.
  - claim: >-
      The repair turn is the only one. When the gates re-run red after it,
      the task ends `EXHAUSTED` with no second repair turn and no verdict.
      Its line names the repair turn and is no longer today's line. The
      witness drives `lint` red again, and `tests` red anew.
    witness: tests/test_session.py::test_a_rebut_still_red_after_its_repair_turn_ends_exhausted
    wrong_versions:
      - A re-run still red on form gates alone earns a second repair turn.
      - The task keeps today's line, which says REBUT does not re-enter the repair loop.
---

## Context

Backlog item **b-0bd346**, which cites `DESIGN.md` §5.5. The change itself
is §5.6's. Line numbers below were read at `af2831e8`.

**Measured on `SA-0298`** in the spec loop's run 46. REBUT fixed all five
blockers, and the re-probe killed each one. The gates then re-ran on the
moved head, and `prose` failed on five hits in the test comments REBUT
wrote. The task ended `EXHAUSTED` with no pull request.
`~/.saffron/batches/v0/SA-0298/rebuttal.json` holds the state and its line.
The line says the gates are red after the rebuttal and REBUT does not
re-enter the repair loop. A person then fixed three comments by hand.

**What §5.6 says today.** A red re-run after REBUT ends the task
`EXHAUSTED`, and REBUT does not re-enter the repair loop
(`DESIGN.md:1257`). The reason it gives is that a fix for a confirmed
blocker that breaks something else is the most informative failure. A
comment that breaks the house style is not that failure. The operator
settled the arm. A red re-run whose every new failure sits in a gate the
repo calls a form gate earns one repair turn, inside the task's budget.
Anything else red ends the task as today.

**Where the re-run lives.** `run_rebut` calls `rerun_gates` after the
rebuttal turn, and a non-`None` answer ends the phase with the line above
(`saffron/phases/rebut.py:726-734`). The verdicts run only after a green
answer (`saffron/phases/rebut.py:736-753`). Production passes
`_rebut_gates` (`saffron/cell/session.py:3565`). That closure judges the
suite as attempt `attempts + 1`, labelled REBUT
(`saffron/cell/session.py:3488-3498`). An aborted or drifted suite is
`GATE_ERROR` (`saffron/cell/session.py:3499-3500`). Any new failure is
`EXHAUSTED` (`saffron/cell/session.py:3516`). The critic cell is seeded from
the implementer's head when `_rebut_critic_container` runs
(`saffron/cell/session.py:3524-3545`), so the verdicts see whatever that
head is then.

**The repair machinery.** The repair loop's turn is `_repair`
(`saffron/cell/session.py:2920-2965`). It resumes the implementer's
session with `implement.repair_prompt(new)`. It checkpoints work a failed
turn left uncommitted, and adds the turn's cost to `spent`.
`implement.repair_prompt` lists each new failure as gate, place, code and
message (`saffron/phases/implement.py:194-213`). `_repair` asks
`_over_budget`, which emits a budget line (`saffron/cell/session.py:2565-2580`).

**Spend at that point.** `spent` holds the spend before REBUT. REBUT's own
spend is added only after `run_rebut` returns
(`saffron/cell/session.py:3547-3594`). REBUT's sessions run under `_RebutCap`,
whose `spent` field counts them as they run
(`saffron/cell/session.py:189-245`, built at `:3519`). REBUT runs at any
spend (`saffron/cell/session.py:3395-3397`).

**What a gate declaration holds.** `GateDeclaration` holds `blocking`
alone, and refuses any other key (`saffron/repos/policy.py:57-60`).
Measured on `af2831e8`: `Policy.model_validate` on a gate declaring
`form: true` raises `extra_forbidden`. A policy cannot declare a core gate
at all. `_no_core_gate_names` refuses each name in `CORE_GATE_NAMES`
(`saffron/repos/policy.py:32-46`, `:187-196`). A gate declared
`blocking: false` is advisory, and its failures never reach
`new_failures` (`saffron/gates/suite.py:245-270`).

## Problem

1. **The key.** `GateDeclaration` gains `form`, a boolean that defaults to
   false. Its comment names §5.6.
2. **The rule.** `rebut.form_only(new_failures, gates)` takes the
   comparison's new failures and the policy's `gates` mapping. It returns
   true only when the list is not empty and every failure's gate is
   declared there with `form: true`. A name in `CORE_GATE_NAMES` is never
   a form gate, whatever the mapping says. The repo declares which gates
   are form gates, and core names none (§2.1).
3. **The turn.** In `_rebut_gates`, a red re-run that `form_only` accepts
   gets one repair turn. It runs only while the task's spend, `spent` plus
   what REBUT's cap has spent, is under `budget_usd`. It resumes the
   implementer's session with `implement.repair_prompt` over the new
   failures. Its `max_budget_usd` is what the budget has left. Its cost
   joins `spent`. A turn that fails still counts its cost, and the re-run
   judges whatever head it left. Then every gate re-runs once, as attempt `attempts + 2`,
   labelled REBUT. Green returns `None`, so the verdicts run on the
   repaired head. Aborted or drifted is `GATE_ERROR`, as today. Red is
   `EXHAUSTED`, with no second turn.
4. **The line.** A task the repair turn left red ends with a line naming
   that turn. Set it the way `probe_patch_why` overrides `run_rebut`'s line
   (`saffron/cell/session.py:3589-3592`). Every other `EXHAUSTED` from the
   re-run keeps today's line, a task too poor to repair included.
5. **The prose that turns false.** `_rebut_gates`'s docstring
   (`saffron/cell/session.py:3400-3403`) and `run_rebut`'s
   (`saffron/phases/rebut.py:634-678`) say a red re-run ends the task.
   Each gains the exception in one sentence.

## Out of scope

- **This repo's own form gates.** `.saffron/policy.yaml` marks `format`,
  `lint` and `prose` as form gates. The delegate adds that by hand as a
  review commit on the cell's pull request. The loader at base refuses the
  key, so the edit cannot land first.
- **The design record and the vocabulary.** This pull request edits
  `DESIGN.md` §5.4 and §5.6 and adds `CONTEXT.md`'s Form gate entry.
- **The task state during the turn.** The task stays `REBUTTING`. The
  turn sets no `REPAIRING` state.
- **A second repair loop.** One turn, never a loop. §5.6's reason against
  ping-pong between two phases still holds for anything past it.
- **`rebuttal.json`'s shape.** It gains no field. The line and the second
  REBUT attempt line say a repair turn ran.

## Notes for the agent

**Mostly new code, so one mutant.** Five criteria judge new code.
Criteria 1 to 4 and 6 judge a key, a function and a branch absent at
base. They declare a witness alone, and `witness` reports `skip` for them. Criterion 5's mutant names
the line at `saffron/cell/session.py:3516`, which the change keeps for a
red re-run `form_only` refuses. Keep that line as it is.

**Where the turn goes.** Inside `_rebut_gates`, after the `probe_infra`
check (`saffron/cell/session.py:3503-3515`). `_rebut_gates` is defined
before `cap`, but runs only after `cap` exists, so it can read `cap.spent`.
Do not call `_over_budget` for this check. Its budget line describes a
stopping task, and REBUT's own budget line already covers a REBUT past
budget (`saffron/cell/session.py:3625-3637`). Do not route the turn through
`_RebutCap`: the repair turn is the task's, not REBUT's.

**The witnesses.**

- Criterion 1: in `tests/test_policy.py`, after
  `test_reads_the_declared_gates` (`tests/test_policy.py:45`). Use
  `write_repo` with a policy of three gates: one `form: true` and
  blocking, one omitting `form`, and one `form: true` with
  `blocking: false`.
- Criterion 2: in `tests/test_rebut.py`, at the end. Build the failures as
  `NewFailure` values. Build each core-gate mapping from `GateDeclaration`
  values directly, since `Policy` refuses a core name. Loop over
  `sorted(CORE_GATE_NAMES)`, and say which name failed.
- Criteria 3 to 6: in `tests/test_session.py`, before
  `test_an_errored_or_drifted_rebuttal_re_run_logs_each_gate_with_no_count`
  (`tests/test_session.py:6752`). Share one helper. It stubs the runtime
  with `_stub_the_runtime(..., patch=_ANCHORING_DIFF)` and
  `_rebuttable(..., rebut_commits=1)`, then calls `_drive` with a policy
  declaring `format` and `lint` `form: true` and `tests` not, and
  `gates=("format", "lint", "tests")` (`tests/test_session.py:1381-1431`).
  Pass `use_default_emit=True` and read the event log and `rebuttal.json`,
  as `_rebuttal_log` does (`tests/test_session.py:6551-6571`). Script the
  turns as `_through_rebut` does (`tests/test_session.py:4870-4884`), with
  a `cost` argument, then the turns after the extraction.
- Each scripted suite names `format`, `lint` and `tests` with the same
  `tool` on every call, so no suite drifts. The stub serves `suites` in
  order, baseline first, and an empty suite past the end
  (`tests/test_session.py:1256-1279`).
- Criterion 3 compares the repair prompt with `implement.repair_prompt`
  over the expected `NewFailure` list. It finds that prompt by the text
  before its blank line. It finds the extraction and verdict turns by
  `rebut.EXTRACT_PROMPT` and `rebut.VERDICT_TURN_PROMPT` in `cell.turns`.
  It reads the cap from `cell.turn_options`. With eight $0.10 turns before
  it and a $12.00 budget, the cap is $11.20. Compare money with
  `pytest.approx`. Assert the REBUT `Attempt` events as
  `(attempt, new_failures)` pairs.
- Criterion 4 uses $0.125 turns, so eight come to exactly $1.00. Drive
  budgets of $1.125, $1.00 and $0.50. REBUT still runs past the budget,
  as `_rebut_capped` shows (`tests/test_session.py:4915-4935`).
- Criterion 5 scripts `witness` as a fourth result of the red suite only.
  `suite_drift` skips a gate the baseline lacks, so it reaches
  `new_failures` (`saffron/gates/baseline.py:67-100`).
- Criteria 4, 5 and 6 assert today's line by its clause "does not re-enter
  the repair loop", which `tests/test_rebut.py:334` also pins. Criterion 6
  asserts the clause is absent and "repair turn" is present.

**What no criterion drives.** Two shapes rest on item 3 alone. One is a
repair turn that fails. The other is a re-run after it that aborts or drifts.

**Existing tests stay green.** The harness's default policy declares no
gate (`tests/test_session.py:1388`), so no existing drive has a form gate.
`test_a_red_rebuttal_line_names_each_gate_that_failed_anew`
(`tests/test_session.py:6659`) still ends `EXHAUSTED` on `lint` alone.

**Measured on a prototype over `af2831e8`.** The prototype was measured
by the `size` gate's counter. It came to 1236 changed tokens with no test
path excluded, and 272 with `tests/**` excluded. The first count is 41%
of the `feature` ceiling of 3000. `tests/test_session.py` carried most of it. Each
witness failed with the source reverted. Each wrong version above,
applied as an edit, failed its criterion's witness. So did the mutant.
`prek` passed on the changed files, `ty` passed on the three source
files, and the `prose` gate found no hit the base lacks.

Commit after each witness passes. Uncommitted work dies with the cell.
