---
id: SA-0207
title: The turn wall leaves no room for one run of the suite, so it cuts an IMPLEMENT session in a check GATE repeats
type: bug
priority: 2
depends_on: [SA-0206]
estimated_lines: 87
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
  - saffron/cli.py
  - saffron/spec_review.py
  - saffron/end_review.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/events.py
  - saffron/ledger.py
  - saffron/report/**
  - saffron/record/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/repos/**
  - saffron/cell/runtime.py
  - saffron/cell/worktree.py
  - saffron/phases/**
  - tests/test_implement.py
  - tests/test_runtime.py
  - tests/test_cli.py
  - tests/test_runner.py
budget_usd: 21
max_attempts: 3
max_turns: 130
acceptance:
  - claim: >-
      Every turn's wall gains the summed `duration_ms` of the task's
      baseline results for the gates the repo's policy declares, advisory
      gates included, counted in seconds. A declared gate whose
      `duration_ms` is `None` adds nothing, and so does a result for a gate
      the policy does not declare. The sum goes on top of the wall the
      spec's `max_turns` sets, past its 900-second floor and its 3600-second
      cap alike. The witness drives one baseline under specs of 40, 130 and
      300 turns. It holds a blocking gate measured at 60.5 seconds, a
      blocking gate with no duration, an advisory gate at 27.5 seconds, and
      an undeclared `witness` result at 500 seconds. The three walls are 988,
      2038 and 3688 seconds. In each, five kinds of turn carry that wall:
      the plan turn, an implement turn the wall cuts with nothing committed,
      the salvage turn after it, one REPAIR turn, and every REVIEW lens turn.
    witness: tests/test_session.py::test_every_turn_carries_the_declared_gates_baseline_time_on_top_of_its_wall
    mutant:
      file: saffron/cell/session.py
      find: "timeout_s=turn_wall_s,"
      replace: "timeout_s=TURN_TIMEOUT_S,"
    wrong_versions:
      - No headroom at all, so the walls stay 900, 1950 and 3600.
      - The longest declared gate's duration instead of the sum, so the walls read 960.5, 2010.5 and 3660.5.
      - Each duration cut to whole seconds before the sum, so 60.5 and 27.5 give 87.
      - Only blocking gates counted, so the advisory gate's 27.5 seconds are dropped.
      - Every baseline result counted, so the undeclared `witness` result adds its 500 seconds.
      - A declared gate with no duration drops the whole headroom to zero.
      - The headroom added inside the cap, so the 300-turn spec still gets 3600.
      - The milliseconds added unconverted, so the 40-turn wall reads 88900.
      - The headroom passed to the implement turn alone, so the plan, salvage, REPAIR and lens turns keep the old wall.
  - claim: >-
      Under that baseline and a spec of 130 turns, an IMPLEMENT session of
      130 turns at 15.5 seconds a turn, 2015 seconds, ends at its turn
      ceiling, and its IMPLEMENT line names that ceiling and no wall. The
      same session at 16 seconds a turn is cut, and its IMPLEMENT line names
      the wall bound and the 2038 seconds it was given.
    witness: tests/test_session.py::test_a_session_inside_the_suites_headroom_ends_at_its_turn_ceiling
    mutant:
      file: saffron/cell/session.py
      find: "timeout_s=turn_wall_s,"
      replace: "timeout_s=TURN_TIMEOUT_S,"
    wrong_versions:
      - No headroom, so the 15.5-second session is cut at 1950 seconds.
      - The longest gate instead of the sum, so the 15.5-second session is cut at 2010.5 seconds.
      - Each duration cut to whole seconds, so the line names 2037 seconds.
      - Every baseline result counted, so the line names 2538 seconds.
      - The milliseconds added unconverted, so the 16-second session is never cut.
  - claim: >-
      A task whose policy declares no gate adds nothing to its wall. Specs
      of 40, 130 and 300 turns keep walls of 900, 1950 and 3600 seconds.
    witness: tests/test_session.py::test_every_turn_carries_a_wall_scaled_to_the_specs_max_turns
    preserves: true
---

## Context

Backlog item **b-23a149**, found in the spec loop's run 26 on `SA-0170`'s
cell. Tier 2. It cites `DESIGN.md` §4.3, whose wall-clock row is one of
the five bounds every phase runs under, and §5.3.

**The wall today.** `SA-0205` and `SA-0206` edit
`saffron/cell/session.py` first, so this spec names functions and
constants there, read at base `128e52b5`. `_drive_cell` computes one wall
per task, `turn_wall_s`, from the spec's `max_turns`. It is
`WALL_SECONDS_PER_TURN`, 15 seconds a turn, floored at `TURN_TIMEOUT_S`,
900, and capped at `WALL_CAP_S`, 3600. Those three are module-scope
constants near the top of the file. `_drive_cell` binds the wall once
into the `partial` over `implement.run_agent`, wrapped by
`record_attempts` and `stop_on_rejected`. Every turn goes through that
one `agent`. The plan turn receives it through `plan_checkpoint`. The
implement, salvage, REPAIR and notes turns call it in `_drive_cell`.
`review.run_review`, `review.run_criterion_probes` and
`review.run_wrong_versions` receive it as `agent=`. REBUT receives it as
`rebut_agent`, wrapped by its cap.

**What run 26 measured.** At `max_turns` 130 the wall is 1950 seconds.
The agent had three commits and every core gate green by its own run. Its
last action was a whole-suite run, and the wall cut the session there. The
host runs that suite next at GATE, outside the session. Attempt 1 then
failed `committed` and spent a repair turn.

**What the baseline already knows.** `_drive_cell` runs the task's
baseline suite in this same cell before any turn, as
`suite.baseline(tree)`. When `baseline.aborted` is non-empty it returns
`PREFLIGHT_FAILED` before the wall is computed. Each declared gate's result carries `duration_ms`
(`saffron/gates/contract.py:86`). `run_gate` sets it on every result it
returns. A parsed result gets it at `saffron/gates/runner.py:165`. A
result that is an `error` gets it from `_error` at `:355`.
The core gates that `GateSuite._run` builds host-side set none
(`saffron/gates/suite.py:182-206`). On this repo's last twelve recorded
baselines, run ids 210 to 223 in `~/.saffron/ledger.db`, every core gate
and `witness` row is null. The declared gates summed 86 to 105 seconds,
and the slowest one alone took 76 to 94.

## Problem

The wall bounds a turn's agent work, and leaves nothing for the one check
an agent is most likely to end on. So a session whose work is done can
still be cut while it confirms that work.

Give every turn's wall room for one agent run of the repo's suite:

- **The headroom.** Sum `duration_ms` over the baseline results whose gate
  the policy declares (`Policy.gates`, `saffron/repos/policy.py:69`),
  blocking and advisory alike. Count a `None` as nothing. Convert it to
  seconds and add it to the wall the spec's `max_turns` sets. Compute it
  where `_drive_cell` computes the wall today, after the baseline, so the
  one binding carries it to every turn.
- **The cap.** `WALL_CAP_S` still bounds the part scaled by `max_turns`.
  The headroom goes on top of it, and of the floor.
- **The comments.** Rewrite the comment above `WALL_SECONDS_PER_TURN`
  in `saffron/cell/session.py`. Its "Capped at the library's hour" is no
  longer the whole wall. The comment above the binding, that no turn can
  "quietly inherit the library's hour", stays true.

## Out of scope

- **Which gate is the suite.** Core names no test runner and picks no
  gate by name (§2.1). The rule reads every declared gate's measured time.
- **The implement prompt.** No turn is told the wall or the suite's time.
- **The wall-cut message.** `run_agent` already prints the `timeout_s` it
  was handed, in its `how` for a wall cut. So the new figure
  reaches the "the session failed" line with no edit there.
  `saffron/phases/implement.py` is `SA-0206`'s, and this spec leaves it
  alone.
- **The end review's and the spec review's walls.** Neither runs a task
  baseline. `saffron/cli.py:663` binds `TURN_TIMEOUT_S`, and
  `SPEC_REVIEW_TIMEOUT_S` lives in `saffron/spec_review.py`.
- **The salvage line's wording.** Its `bound_word` names "the wall clock"
  and no seconds, in `_drive_cell`. The IMPLEMENT line
  before it carries them.

## Notes for the agent

**Why the sum of the declared gates.** These are the operator's settled
calls, argued here so a reviewer can check them.

- *Declared, not every result.* An agent in its cell can run the repo's
  declared gates. It cannot run a core gate, which runs host-side. Core
  gates carry no duration today, so the restriction changes nothing now.
  It keeps a future core gate that re-runs the tests, as `revert` does,
  from counting that time twice.
- *Sum, not the longest.* Core cannot tell which declared gate an agent
  will re-run. The sum is one run of every declared gate, which covers any
  part of the suite the agent runs. On this repo it costs about 10 seconds
  more than the longest gate alone.
- *A `None` adds nothing.* `run_gate` always sets a duration, so a `None`
  comes from another producer of a `GateResult`. Dropping the measured
  gates' time because one is unmeasured would throw away what is known.
  Counting it as nothing keeps the wall at least what it is today.

**Why every turn.** The wall is bound once so that no call site drifts
from the others (`SA-0184`). REPAIR runs the suite as IMPLEMENT does. A
turn that never runs it pays nothing for the headroom unless it keeps
producing output. The idle bound, `runtime.IDLE_TIMEOUT_S`, still ends a
stall in 300 seconds, and the turn ceiling still ends a loop.

**Why the cap no longer bounds the whole wall.** Its comment calls 3600
the library's hour. Nothing in this tree outside `session.py` enforces an hour.
`run_agent` and `exec_stream` default `timeout_s` to 3600, in their
signatures (`saffron/cell/runtime.py:499` for the second), and
the binding always passes its own. `images/agent_runner.py` sets no
timeout. A spec of 240 turns or more runs the longest sessions. Those are
the likeliest to end in a suite run, and a capped sum would give them none.

**Which criteria have a mutant.** The headroom is new code, so no mutant
can pin its spelling. Criteria 1 and 2 share one mutant on the binding's
existing keyword, which the change keeps. It undoes the whole wall, and
each witness must see the walls change. Criterion 3 passes today and must
keep passing. Its policy declares no gate.

**Criterion 1's witness.** Model it on
`test_every_turn_carries_a_wall_scaled_to_the_specs_max_turns`, the same
turns and the same `commits=[0, 1]`. Pass `_drive` a `policy` declaring
three gates, two blocking and one with `blocking: false`, and the same
names as `gates=`. Give the baseline the four results the claim lists.
Give each declared result the `tool` the later suites report, `ruff 1.0`
from `_results`. A different tool makes `suite_drift` distrust the
subtraction, and no REPAIR turn runs. Name no declared gate `tests`. With
one declared, `GateSuite._run` runs `revert_gate`, whose `run_gate` call
the stub does not replace. Write the walls as the literals 988.0, 2038.0
and 3688.0. Worked out from the module's constants, they would move with
the mutant.

**What criterion 1 leaves undriven.** The notes turn, the criterion
probes, the wrong-version turns and REBUT take the same `agent` binding.
No witness drives them.

**Criterion 2's witness.** Model it on
`test_a_long_session_ends_at_its_turn_ceiling_not_the_wall`, with the
same baseline and policy as criterion 1. One suite is enough. Assert the
cut line holds the phrase "wall bound, given 2038s", which `run_agent`
already builds from what it was handed.

**How the lists were measured.** On 2026-10-05 a prototype of this change
and both witnesses ran on a plain copy of the base. Each wrong version
above was applied to it in turn, with bytecode writing off. Each failed
criterion 1's witness on an assertion. Criterion 2's witness killed the
five listed under it. With the source reverted both new witnesses failed,
and criterion 3's passed. The whole suite passed on the prototype.

**This cell runs under today's wall.** `tests/test_session.py` holds over
9500 lines. Write the source change and commit it before any test. Run
each new test by its node id, and the two test files whole once, at the
end.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. A docstring stays within ten lines.

**Size.** `saffron/cell/**` is in `elevate_on`, so `size` blocks at the
`bug` ceiling of 1300 tokens (`saffron/gates/core/size.py:26`). The
prototype counted 345 tokens over 97 changed lines by `size_gate`, 12 in
the source and 85 in the test. At 4 tokens a line that is 87 lines.
