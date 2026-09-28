---
id: SA-0184
title: The 900-second turn wall cuts sessions the spec's turn ceiling allows, and a cut does not say how long the wall was
type: bug
priority: 1
depends_on: []
touches:
  - saffron/cell/session.py
  - saffron/phases/implement.py
  - tests/test_session.py
  - tests/test_implement.py
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
  - saffron/cli.py
  - saffron/spec_review.py
  - saffron/end_review.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/events.py
  - saffron/ledger.py
  - saffron/cell/runtime.py
  - saffron/phases/review.py
  - saffron/phases/rebut.py
  - saffron/agents/**
  - saffron/gates/**
  - tests/test_runtime.py
  - tests/test_cli.py
  - tests/test_spec_review.py
budget_usd: 21
max_attempts: 3
max_turns: 130
estimated_lines: 112
acceptance:
  - claim: >-
      A cell's turns run under a wall of 15 seconds for each turn of the
      spec's `max_turns`, never below 900 seconds and never above 3600. The
      witness drives specs declaring 40, 130 and 300 turns, whose walls are
      900, 1950 and 3600 seconds. In each, five kinds of turn carry that wall:
      the plan turn, an implement turn the wall cuts with nothing committed,
      the salvage turn after it, one REPAIR turn, and every REVIEW lens turn.
    witness: tests/test_session.py::test_every_turn_carries_a_wall_scaled_to_the_specs_max_turns
    mutant:
      file: saffron/cell/session.py
      find: "TURN_TIMEOUT_S = 900.0"
      replace: "TURN_TIMEOUT_S = 600.0"
  - claim: >-
      Under a spec declaring 130 turns, an IMPLEMENT session of 130 turns at
      10.8 seconds a turn ends at its turn ceiling, and the IMPLEMENT line for
      it names that ceiling and no wall. The same session at 16 seconds a turn
      is cut, and its IMPLEMENT line names the wall bound and its 1950
      seconds.
    witness: tests/test_session.py::test_a_long_session_ends_at_its_turn_ceiling_not_the_wall
    mutant:
      file: saffron/phases/implement.py
      find: "timeout_s=timeout_s,"
      replace: "timeout_s=900.0,"
  - claim: >-
      A turn the wall bound cuts fails with a message naming the wall bound
      and the seconds that turn was given, ahead of the stderr it quotes. A
      turn the idle bound cuts, given
      the same seconds, names the idle bound and not those seconds.
    witness: tests/test_implement.py::test_a_wall_cut_names_the_seconds_it_was_given_and_an_idle_cut_does_not
  - claim: >-
      A spec that declares no `max_turns` still runs every turn under the
      900-second wall.
    witness: tests/test_session.py::test_every_turn_carries_the_drivers_wall_clock_not_the_librarys
    preserves: true
---

## Context

Backlog item **b-bf0c91**, found in the spec loop's run 19 on 2026-09-27.
Tier 1. It cites `DESIGN.md` §4.3, whose wall-clock row is one of the five
bounds every phase runs under.

**One wall today, for every turn.** `saffron/cell/session.py:58-63` sets
`TURN_TIMEOUT_S` to 900 seconds. `_drive_cell` binds it once, at
`saffron/cell/session.py:1959-1969`, into the `partial` over
`implement.run_agent`. Every turn goes through that one `agent`. The plan
turn takes it at `:1978`, IMPLEMENT at `:2142` and the salvage turn at
`:2224`. REPAIR takes it at `:2410` and the notes turn at `:2480`. REVIEW's
lenses and criterion probes take it at `:2669` and `:2684`, and REBUT at
`:2869`. `run_agent` passes the value on to
`exec_stream` (`saffron/phases/implement.py:301-308`). There the wall is one
of three time bounds, beside idle and completion
(`saffron/cell/runtime.py:545-561`).

**What runs 18 and 19 measured.** Read from `~/.saffron/ledger.db`'s
`attempts`, IMPLEMENT and REPAIR rows since 2026-09-25. Sessions that
finished ran up to 119 turns and 867 seconds. Of those with 45 turns or
more, the slowest ran 10.8 seconds a turn: `SA-0168`, 56 turns in 607
seconds. Eleven IMPLEMENT sessions and one REPAIR session were cut at 899
to 900 seconds. Each recorded subtype `error` and 0 turns, so a cut says
nothing of how far it got. Among them were `SA-0155`, `SA-0168`,
`SA-0169`, `SA-0175` and `SA-0181`. None was a hang. The queued specs
declare `max_turns` from 55 to 250.

**How a cut reads today.** A turn the wall ends has no result event.
So `run_agent` raises `AgentFailed` with "the agent produced no result
event, was cut by the wall bound" (`saffron/phases/implement.py:336-352`).
`_phase_start` prints it as the IMPLEMENT line "the session failed"
(`saffron/cell/session.py:2154`). The line names the bound and not its
seconds. That did not matter while every wall was 900 seconds.

## Problem

A spec that declares 130 turns gets 900 seconds to spend them. At the
slowest rate a finished session was measured at, 130 turns take about
1400 seconds. So the wall, not the turn ceiling, decides where a long
session ends.

Make the wall scale with the spec's `max_turns`:

- **The wall** is 15 seconds times `spec.max_turns`, floored at 900 and
  capped at 3600. Compute it once, where `_drive_cell` binds the `agent`
  today, so every turn that `agent` drives carries it. The floor is
  `TURN_TIMEOUT_S` itself, read by name, and it keeps its value.
  `saffron/cli.py:633` and `saffron/spec_review.py:51` read that name.
  Name the per-turn rate and the cap as module-scope constants beside it.
  Rewrite the comment above `TURN_TIMEOUT_S`
  (`saffron/cell/session.py:58-63`). Its "Fifteen minutes" is no longer
  the whole story.
- **The cut's message.** A turn the wall bound ends raises a message from
  `run_agent`. It names the wall bound and the `timeout_s` it was handed,
  in seconds. Put the seconds in `how` (`saffron/phases/implement.py:336`),
  ahead of `detail`. `detail` carries up to 800 characters of stderr
  (`:333`), and the IMPLEMENT line is cut at 500 (`_DETAIL_BOUND`,
  `saffron/events.py:666`). The idle and completion bounds keep their
  wording.

## Out of scope

- **The stack end review's binding** (`saffron/cli.py:629-635`). Its lenses
  run under `LENS_MAX_TURNS`, 50 (`saffron/end_review.py:43`), and not
  under a spec's `max_turns`. At 15 seconds a turn that is 750, under the
  floor, so it stays at `TURN_TIMEOUT_S`.
- **The spec review's wall.** `SPEC_REVIEW_TIMEOUT_S` is twice
  `TURN_TIMEOUT_S` (`saffron/spec_review.py:51`) and does not change.
- **A per-turn wall.** A salvage turn runs under a ceiling of
  `SALVAGE_MAX_TURNS` (`saffron/phases/implement.py:59`), but it takes the
  spec's wall like every other turn.
- **The salvage line's wording.** Its `bound_word`
  (`saffron/cell/session.py:2183`) stays. The IMPLEMENT line before it
  carries the seconds.
- **The idle bound's seconds.** `run_agent` never passes `idle_s`, so it
  does not know them.

## Notes for the agent

**Where the three numbers come from.** The operator set them.

- 15 seconds a turn is about 1.4 times the slowest rate a finished long
  session ran at. `SA-0168` took 607 seconds for 56 turns, 10.8 a turn, and
  `SA-0147` took 654 for 64, 10.2 a turn. Short plan and REPAIR sessions ran
  slower, up to 32 seconds a turn, but none of them past 739 seconds, so the
  floor holds them.
- 900 seconds is today's wall, kept as the floor. A spec of 60 turns or
  fewer runs as it does now.
- 3600 seconds is the library's hour, `run_agent`'s default `timeout_s`
  (`saffron/phases/implement.py:216`). A spec of 240 turns or more now gets
  that hour, set here by name rather than inherited. So the comment above
  the binding, "no turn … can quietly inherit the library's hour"
  (`saffron/cell/session.py:1954-1955`), stays true. Keep it true. The idle
  bound, `runtime.IDLE_TIMEOUT_S`, still ends a stalled turn in 300
  seconds, whatever the wall.

The run figures came from this query on the host's ledger, which is not in
the tree: `attempts` joined to `tasks`, phases `IMPLEMENTING` and
`REPAIRING`, started after 2026-09-25, with seconds taken as `ended_at`
less `started_at`.

**Which criteria have a mutant.** Criteria 1 and 2 edit code that exists,
and each mutant pins a line that stays. Criterion 3 is new message text, so
it declares a witness alone and `witness` reports `skip` for it. Criterion 4
passes today and must keep passing. `_spec()` declares no `max_turns`, so
`CellSpec`'s default of 60 applies (`saffron/cell/session.py:274`).

**Criterion 1's witness.** Drive `_drive` three times, one spec each. Stub
the runtime with `commits=[0, 1]` and `suites=([], _results(failing), [])`,
as `tests/test_session.py:1863-1866` does. The turns are a plan,
`_wall_cut_turn()` and two clean turns. So the salvage turn runs, one
REPAIR turn follows on the failing suite, and REVIEW runs on the green one.
Assert that the third turn is the salvage prompt, that the fourth carries
the failure, and that more than four turns ran. Then assert that
`cell.timeouts` is the one wall repeated for every turn. Write the expected
walls as the literals 900.0, 1950.0 and 3600.0. Worked out from
`session.TURN_TIMEOUT_S` the way `:4522` does, they would move with the
mutant, and it would survive. It must fail:

- a flat wall of 900, or of 3600
- a wall with no floor, or no cap
- a rate other than 15 seconds a turn
- a wall worked out per call from each turn's own `max_turns`, which gives
  the salvage turn 900
- the wall passed explicitly at every call site but REPAIR's, with the
  `partial` left at `TURN_TIMEOUT_S`

**What criterion 1 leaves undriven.** The notes turn
(`saffron/cell/session.py:2480`), REBUT (`:2869`) and the criterion probes
(`:2684`) take the same `agent` binding.
No witness drives them.

**Criterion 2's witness** runs each turn through the real `run_agent`.
`_drive` already does so when `real_run_agent` is a list
(`tests/test_session.py:1323-1356`). Give `_drive` an opt-in keyword
for the seconds each modelled turn takes. Multiply the turn's `num_turns`
by those seconds. Where that exceeds the `timeout_s` the `exec_stream`
double at `:1329` was handed, it returns a wall cut. That is exit 124 with
`bound="wall"`, and no lines. Without it, nothing changes for the tests that
use that path. A wall cut makes `run_agent` remove its prompt file with
`exec_`, so the `_REAL_RUN_AGENT` call at `:1348` needs an `exec_` double
beside `reap_cell=_no_reap`. `tests/conftest.py` refuses a real one. The
turns are a plan and `implement.AgentFailed` over `_cut_off_turn()`.
`_cut_off_turn()` fixes 60 turns (`tests/test_session.py:1162-1173`), so
override its `num_turns` to 130 with `replace`. Read the "the session
failed" line from `cell.watched`. It must fail a flat wall of 900 and a
flat wall of 3600. It must also fail a message that prints 900 whatever
the turn was given.

**Criterion 3's witness** calls `implement.run_agent` twice with
`timeout_s=1950.0`, using `_stream` and `_no_reap` from
`tests/test_implement.py`. One turn ends with `bound="wall"`, the other with
`bound="idle"`. Each `_stream` carries 800 characters of stderr, and the
witness asserts the seconds sit before the first of them. It must fail a
message that prints the floor instead of `timeout_s`, and one that prints
the seconds for the idle bound too. It must also fail seconds placed after
the detail.

**How the lists were measured.** On 2026-09-27 a prototype of this change
and these witnesses ran on a plain copy of the tree base. Each wrong version
above was applied to it in turn, with bytecode writing off, and each failed
its witness on an assertion. With the source reverted all three new
witnesses failed, and criterion 4's passed. Each declared mutant failed its
own witness.

**This cell runs under today's wall.** The host runs Saffron from `main`,
so each of your turns gets 900 seconds. `tests/test_session.py` holds over
8000 lines. So write the source change and commit it before any test.
Then write the tests, running each by its single node id. Run the two test
files whole only once, at the end.

**The `prose` gate** counts every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence over
25 words. A docstring stays within ten lines.

**Size.** `saffron/cell/**` is in `elevate_on`, so `size` blocks at the `bug`
ceiling of 1300 tokens (`saffron/gates/core/size.py:26`). A prototype counted
by `size_gate` came to 447 tokens over 103 changed lines, 22 in the source
and 81 in the tests. At the checkpoint's 4 tokens a line that is 112 lines,
the raw figure `estimated_lines` declares. `driver.py check` applies the
measured overrun to it.
