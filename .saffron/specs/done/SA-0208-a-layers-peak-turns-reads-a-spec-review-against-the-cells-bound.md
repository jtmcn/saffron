---
id: SA-0208
title: A layer's peak turns reads a spec review's attempt against the cell's turn bound
type: bug
priority: 2
estimated_lines: 151
estimate_measured: true
touches:
  - saffron/report/stack.py
  - tests/test_stack_view.py
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
  - saffron/spec_review.py
  - saffron/batch.py
  - saffron/follow_up.py
  - saffron/ledger.py
  - saffron/cli.py
  - saffron/end_review.py
  - saffron/replay.py
  - saffron/report/index.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/record/**
  - saffron/gates/**
  - tests/test_cli.py
  - tests/test_accept_rate.py
  - tests/test_ledger.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 14
max_attempts: 3
max_turns: 90
acceptance:
  - claim: >-
      Each layer's section on the stack page carries six turn lines, one per
      phase, in the order SPEC_REVIEW, SPEC_WRITING, IMPLEMENT, GATE ⇄
      REPAIR, REVIEW, REBUT. The peak is the highest `num_turns` among the
      layer task's attempts in that phase alone. A cell phase's attempt is
      one turn, so its line reads `<label> <peak> of <bound> turns`, the
      bound being the spec's `max_turns`. A SPEC_REVIEW or SPEC_WRITING
      attempt sums a session's turns, extraction turns included, and each
      turn has its own bound. So those two lines read `<label> <peak> turns,
      extraction turns included, <bound> each`. SPEC_REVIEW's bound is
      `spec_review.SPEC_REVIEW_MAX_TURNS` and SPEC_WRITING's is
      `spec_review.SPEC_WRITER_MAX_TURNS`. The witness drives a 150-turn
      SPEC_REVIEW attempt on a layer whose spec declares 90 turns, which is
      the backlog item's own case. It drives all six phases on a second
      layer with a distinct peak each, and patches both constants to values
      no other bound holds.
    witness: tests/test_stack_view.py::test_each_phase_reads_its_own_peak_beside_its_own_bound
    wrong_versions:
      - SPEC_REVIEW and SPEC_WRITING printed as `<peak> of <bound> turns`, which reads `150 of 77 turns` as an overrun no turn made.
      - SPEC_WRITING alone printed as `<peak> of <bound> turns`.
      - Every phase printed in the per-turn shape, which reads `IMPLEMENT 44 turns, extraction turns included, 90 each`.
      - SPEC_REVIEW's bound read from the spec's `max_turns`, which reads `140 each` on the second layer.
      - SPEC_WRITING's bound read from the spec's `max_turns`.
      - The two constants swapped between SPEC_REVIEW and SPEC_WRITING.
      - SPEC_REVIEW's bound typed as the literal 90, which the patched constant exposes.
      - SPEC_WRITING's bound typed as the literal 120.
      - SPEC_REVIEW's bound taken from `end_review.LENS_MAX_TURNS`.
      - Each of the four cell phases reading the highest attempt over all four of them.
      - The last attempt in a phase taken for its peak, which reads SPEC_REVIEW as 7.
      - The first attempt in a phase taken for its peak, which reads SPEC_REVIEW as 12.
      - A phase's attempts summed, which reads IMPLEMENT as 47 on the first layer.
      - REPAIRING attempts labelled REPAIR rather than GATE ⇄ REPAIR.
      - The four cell phases listed before SPEC_REVIEW and SPEC_WRITING.
      - The old whole-task line kept beside the six.
      - SPEC_WRITING attempts matched on a phase string other than `spec_review.WRITING_PHASE`.
  - claim: >-
      A phase whose layer task has no closed attempt in it reads
      `PLACEHOLDER` for its peak and keeps its line. Its peak is never 0. An
      attempt left open, whose `num_turns` is NULL, counts as no attempt. A
      closed attempt of 0 turns reads 0. An attempt in a phase outside the
      six counts toward no line. A layer whose spec the page was not handed
      reads `PLACEHOLDER` for the four bounds the spec gives, and still reads
      both constants. The witness drives one layer per case. Between them
      each of the six phases reads absent on at least one layer.
    witness: tests/test_stack_view.py::test_a_phase_with_no_closed_attempt_reads_absent_never_zero
    wrong_versions:
      - A phase with no attempt read as 0.
      - A closed attempt of 0 turns read as absent, as `max(turns) or None` does.
      - An open attempt counted as 0, which reads REBUT as `0 of 70 turns`.
      - A phase with no attempt left off the page.
      - An attempt in any phase outside the six counted toward IMPLEMENT, which reads `200 of 90 turns`.
      - Both constant bounds read as `PLACEHOLDER` on a layer with no spec, so TE-4's SPEC_WRITING line loses its 133.
---

## Context

Backlog item **b-60ff2e**. It cites `DESIGN.md` §6.

**What the page prints today.** `_build_layer` sets a layer's `peak_turns`
from every attempt of its task (`saffron/report/stack.py:109`).
`_peak_turns` takes the highest `num_turns` among them, phase unread
(`saffron/report/stack.py:132-134`). The layer's `max_turns` is the spec's
own (`saffron/report/stack.py:122`). `_layer_section` joins the two into
one `turns` string (`saffron/report/stack.py:193-196`). It prints that as one
`<p>{turns}</p>` line (`saffron/report/stack.py:205`). `peak_turns` and
`max_turns` are two fields of `StackLayer` (`saffron/report/stack.py:40-41`).

**What a layer's task records.** Every attempt row carries a `phase`
(`saffron/ledger.py:148-164`). `open_attempt` takes the task's state when
no phase is passed (`saffron/ledger.py:1333-1357`). A cell records each
agent turn through `record_attempts`, which passes no phase
(`saffron/cell/session.py:242-266`). So a cell's attempts carry the state
the task held at the turn. That is `IMPLEMENTING` (`:2099`), `REPAIRING`
(`:2569`), `REVIEWING` (`:2691`) or `REBUTTING` (`:2997`). A stack batch
records the spec review on the same task as `SPEC_REVIEW`
(`saffron/batch.py:588-595`). It records a revision's spec writer session as
`spec_review.WRITING_PHASE` (`saffron/batch.py:694-703`), which is
`SPEC_WRITING` (`saffron/spec_review.py:38`). A follow-up's spec writer
session records the same phase (`saffron/follow_up.py:254-263`). The only
other phase written anywhere is `REPLAY` (`saffron/replay.py:88`). A
replay task never gets a layer, since only `run_stack_batch` calls
`record_stack_layer` (`saffron/batch.py:491`).

**What caps each phase's turns.**

| attempt phase | page label | bound | read at |
| --- | --- | --- | --- |
| `SPEC_REVIEW` | SPEC_REVIEW | `SPEC_REVIEW_MAX_TURNS` in `spec_review`, 90 | `saffron/spec_review.py:45`, `:313` |
| `SPEC_WRITING` | SPEC_WRITING | `SPEC_WRITER_MAX_TURNS` in `spec_review`, 120 | `saffron/spec_review.py:555`, `:617` |
| `IMPLEMENTING` | IMPLEMENT | `max_turns=spec.max_turns` | `saffron/cell/session.py:2093` |
| `REPAIRING` | GATE ⇄ REPAIR | the IMPLEMENT turn's `options=options` | `saffron/cell/session.py:2576` |
| `REVIEWING` | REVIEW | `max_turns=spec.max_turns` | `saffron/cell/session.py:2827`, `:2842`, `:2857` |
| `REBUTTING` | REBUT | `options=options` and `max_turns=spec.max_turns` | `saffron/cell/session.py:3059`, `:3065` |

The IMPLEMENT row's salvage turn runs at `min(SALVAGE_MAX_TURNS,
spec.max_turns)` (`saffron/cell/session.py:2376`), which never exceeds the
spec's own. The GATE ⇄ REPAIR row reuses the IMPLEMENT turn's `options`. The REBUT
row's rebuttal turn reuses them too (`:3059`). Its verdict sessions take
`max_turns=spec.max_turns` (`:3065`, `saffron/phases/rebut.py:323-325`).
`end_review.LENS_MAX_TURNS` caps the end review's lenses
(`saffron/cli.py:684`). Their `agent` records no attempt
(`saffron/cli.py:660-666`), so no layer line reads them.

**What one attempt holds, phase by phase.** In `CONTEXT.md`'s words, an
extraction turn resumes a session (`CONTEXT.md:241-244`). The planner and the
implementer are one session (`CONTEXT.md:236-238`). So a session can span
several turns, and `max_turns` bounds each turn.

- **The four cell phases hold one turn per attempt.** `record_attempts`
  opens and closes one row around each `agent` call
  (`saffron/cell/session.py:255-264`). One call runs one
  `async for message in query(` loop (`images/agent_runner.py:196`). Every cell turn calls that wrapped
  `agent`. IMPLEMENTING's plan turn goes through `plan_checkpoint` with
  `agent=agent` (`saffron/cell/session.py:2127-2133`). Its salvage turn is
  its own `salvaged = agent(` call (`saffron/cell/session.py:2385`).
  REPAIRING's turn is `repaired = agent(` (`saffron/cell/session.py:2573`).
  REVIEWING's lens sessions take `agent=agent`
  (`saffron/cell/session.py:2829`, `:2844`, `:2859`). A lens retry is a
  second `agent(` call (`saffron/phases/review.py:262`, `:294`). REBUTTING
  takes `agent=rebut_agent`, the same `agent` or a wrap of it
  (`saffron/cell/session.py:3028`, `:3076`). Its rebuttal turn and its
  extraction turn are two `agent(` calls (`saffron/phases/rebut.py:202`,
  `:219`).
- **SPEC_REVIEW and SPEC_WRITING hold a whole session per attempt.**
  `run_spec_review` makes a `first = agent(` call
  (`saffron/spec_review.py:340`). It then runs an extraction turn resumed on
  that session (`saffron/spec_review.py:408-410`) and at most one re-ask
  (`saffron/spec_review.py:428-430`). `_measure` adds each turn's count with
  `turns += attempt.num_turns` (`saffron/spec_review.py:326`). Each
  extraction turn's `extract_options` keeps the review's `max_turns`
  (`saffron/spec_review.py:370-373`). `run_stack_batch` closes one
  `SPEC_REVIEW` attempt with that sum (`saffron/batch.py:588-595`). The
  review's `agent` is a bare `partial` of `implement.run_agent`, with no
  row per turn (`saffron/cli.py:922-926`). The writer has the same shape:
  a `first = agent(` call (`saffron/spec_review.py:644`), then
  `_extraction_turn(` twice at most (`saffron/spec_review.py:718`, `:738`). It sums with
  `turns += attempt.num_turns` too (`saffron/spec_review.py:630`). Its
  `extract_options` keeps its own `max_turns` (`saffron/spec_review.py:674`).
  So a `SPEC_REVIEW` attempt of 150 turns can sit under a bound of 90 with
  no turn over it.
- **A resumed turn counts its own turns only.** Measured read-only on the
  host ledger, 2026-10-05. Task 223's `IMPLEMENTING` attempt 2 ran 181 turns
  and ended `error_max_turns`. Attempt 3 resumed the same session and
  recorded 4. Its `REPAIRING` attempt 1 ran 105, and attempt 2 on the same
  session recorded 1. Task 221's two `REBUTTING` attempts on one session
  recorded 15 and 2. A count that carried the resumed session's turns would
  read at least the earlier figure. So a summed `SPEC_REVIEW` attempt counts
  no turn twice.

**The page's vocabulary.** `CONTEXT.md`'s **Phase** entry names the cell's
phases IMPLEMENT, GATE ⇄ REPAIR, REVIEW and REBUT (`CONTEXT.md:221-226`).
GATE ⇄ REPAIR is one phase everywhere but the event log. The entry names
SPEC_REVIEW and SPEC_WRITING as the labels a stack batch puts on attempts.
`PLACEHOLDER` is the page's mark for a value it does not have
(`saffron/report/index.py:185`).

## Problem

A stack batch's spec review records its whole session as one `SPEC_REVIEW`
attempt on the layer's task. The page takes the highest attempt of any
phase and prints it against the spec's `max_turns`. Run 26's Spec seat read
a 150-turn `SPEC_REVIEW` attempt as `150 of 90 turns`. Nothing on the page
said whose 150 it was. Printing it beside its own constant would still read
as an overrun, since that attempt sums several turns and 90 bounds each.

## Out of scope

- **`driver.py history`'s `peak_turns`.** It takes the highest attempt of
  any phase as well (`.claude/skills/run-saffron-spec-loop/driver.py:1967`).
  Its `ceilings:` line compares that to a spec's `max_turns` (`:2016-2017`).
  `.claude/**` is forbidden here.
- **Splitting a spec review attempt by turn.** `saffron/spec_review.py`
  and `saffron/batch.py` are `SA-0205`'s, and both are forbidden here. The
  page says the attempt is a sum and gives the bound each turn has.
- **Where `max_turns` comes from.** After a stack batch, `write_stack_view`
  gets the order's specs at `base_sha` (`saffron/cli.py:1728-1730`). A follow-up
  layer's spec is not among them, so its four cell bounds read
  `PLACEHOLDER`. This spec keeps that source.
- **The queue rows, `queue.json` and `saffron watch`.** None reads a peak.
  `QueueLine` carries no turns field (`saffron/report/index.py:85-111`).
  `saffron watch` prints the `Ceilings`
  event's declared `max_turns` (`saffron/events.py:742`) and no attempt's
  turns.

## Notes for the agent

**Both criteria are new code.** The per-phase read and the six lines do not
exist. No text pins honestly, so each criterion declares a witness and no
mutant. Expect `witness` to report `skip` for both.

**The read.** Replace `StackLayer`'s `peak_turns` and `max_turns` with one
field, `turns: tuple[tuple[str, int | None, int | None, bool], ...]`. It
holds the six phases in page order, each as label, peak, bound, and whether
one attempt sums a session's turns. That flag is true for SPEC_REVIEW and
SPEC_WRITING alone. Build it in `_build_layer` from one list of six rows:
label, attempt phase, bound and flag, in the table's order. Spell each phase string once in that list. Use
`spec_review.WRITING_PHASE` for the writing phase rather than retyping it.
The peak counts only attempts whose `phase` matches and whose `num_turns`
is not NULL.

**The two constants.** Add `from saffron import spec_review` to
`saffron/report/stack.py`. Read `spec_review.SPEC_REVIEW_MAX_TURNS` and
`spec_review.SPEC_WRITER_MAX_TURNS` when a layer is built. The witnesses
patch both on the module with `monkeypatch.setattr`, so a name bound at
import time reads the unpatched value and fails them. Importing the module
from `saffron/report/stack.py` makes no cycle in either import order
(measured 2026-10-05).

**The page.** Replace the one `<p>{turns}</p>` line with six, one per
phase. A cell phase's reads `<p><label> <peak> of <bound> turns</p>`. A
flagged phase's reads `<p><label> <peak> turns, extraction turns included,
<bound> each</p>`. Print `PLACEHOLDER` for a peak or bound that is `None`.

**The fixture.** `_attempt` in `tests/test_stack_view.py` opens every
attempt in the task's state today, which is `QUEUED` for every fixture
task. Give it a `phase` argument that defaults to `IMPLEMENTING`, and pass
it to `open_attempt`. Open `TE-4`'s one batch B attempt, 10 turns, in
`REPAIRING`. Then add these to `_build_batches` after `record_push`, each
closed at $0.00 so no spend the other witnesses assert moves.

| task | phase | turns |
| --- | --- | --- |
| `te7` | `SPEC_REVIEW` | 150 |
| `te7` | `REPLAY` | 200 |
| `te9` | `SPEC_REVIEW` | 12, then 31, then 7 |
| `te9` | `SPEC_WRITING` | 0 |
| `te9` | `REPAIRING` | 27 |
| `te9` | `REVIEWING` | 38 |
| `te9` | `REBUTTING` | 45 |
| `te4_1` | `SPEC_WRITING` | 9 |
| `te6_2` | `REBUTTING` | opened and never closed |

**Both witnesses** patch `SPEC_REVIEW_MAX_TURNS` to 77 and
`SPEC_WRITER_MAX_TURNS` to 133. They render `stack_view(ledger, batch_b,
specs)`. They collect the text of each layer section's `<p>` lines that
hold ` turns`, in order. Write `P` for `PLACEHOLDER`, and `X` for `turns,
extraction turns included,`. Criterion 1 asserts two layers whole.

- `TE-7`: `SPEC_REVIEW 150 X 77 each`, `SPEC_WRITING P X 133 each`,
  `IMPLEMENT 44 of 90 turns`, `GATE ⇄ REPAIR P of 90 turns`,
  `REVIEW P of 90 turns`, `REBUT P of 90 turns`.
- `TE-9`: `SPEC_REVIEW 31 X 77 each`, `SPEC_WRITING 0 X 133 each`,
  `IMPLEMENT 50 of 140 turns`, `GATE ⇄ REPAIR 27 of 140 turns`,
  `REVIEW 38 of 140 turns`, `REBUT 45 of 140 turns`.

Criterion 2 asserts two more whole, then TE-9's zero line and that no
TE-7 line holds 200.

- `TE-6`: `SPEC_REVIEW P X 77 each`, `SPEC_WRITING P X 133 each`,
  `IMPLEMENT 61 of 70 turns`, `GATE ⇄ REPAIR P of 70 turns`,
  `REVIEW P of 70 turns`, `REBUT P of 70 turns`.
- `TE-4`: `SPEC_REVIEW P X 77 each`, `SPEC_WRITING 9 X 133 each`,
  `IMPLEMENT P of P turns`, `GATE ⇄ REPAIR 10 of P turns`,
  `REVIEW P of P turns`, `REBUT P of P turns`.

**The three tests already in the file.** In
`test_the_stack_view_reads_each_layer_of_one_batch_in_position_order`, drop
`peak_turns` and `max_turns` from `_assert_layer` and from each expected
layer. The two witnesses assert the turns. In
`test_the_stack_view_renders_a_section_for_the_batch_and_each_layer`, build
each `StackLayer` with a one-row `turns` whose flag is false. Assert `IMPLEMENT 44 of 140 turns`
where it asserts `44 of 140 turns`, and `IMPLEMENT P of P turns` likewise.
Change nothing else in either test.

**Import inside each test body.** Import `stack_view`, `render_stack` and
`spec_review` inside the witnesses, as the file's other tests do.

Commit after each witness passes. Uncommitted work dies with the cell.
