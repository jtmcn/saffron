---
id: SA-0102
title: the GateResult kind renders and nothing constructs it, so a log carries one joined baseline line and a repair count with no gate names
type: bug
priority: 2
depends_on:
  - SA-0101
touches:
  - saffron/cell/session.py
  - tests/test_session.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/events.py
  - saffron/report/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/watch.py
  - saffron/replay.py
budget_usd: 14
max_turns: 90
acceptance:
  - claim: >-
      Every gate result the baseline suite produced reaches the log as its own
      event, each naming its gate, its status, and the baseline as what it was
      measured against. Today the log carries one joined line naming every gate
      and no event per gate.
    witness: tests/test_session.py::test_each_baseline_gate_result_reaches_the_log_as_its_own_event
  - claim: >-
      Every gate result an attempt's suite produced reaches the log as its own
      event, carrying that attempt's number. Two attempts produce two sets, and
      each set carries its own number rather than the latest one.
    witness: tests/test_session.py::test_each_attempts_gate_results_carry_their_own_attempt_number
  - claim: >-
      A gate that errored is emitted with the errored status and never the
      failed one, and the count of new failures it contributed is absent rather
      than zero, because a gate that broke computed no count.
    witness: tests/test_session.py::test_an_errored_gate_is_emitted_as_errored_and_counts_nothing
---

## Context

`saffron/events.py` defines ten kinds. Nine of them have a producer.

`GateResult` at `saffron/events.py:237-254` is the tenth. Its docstring calls it
"the host's own typed record of the fact a watch line already carried a hundred
times over". It carries `gate`, `status`, `against` with the three values
`baseline`, `attempt` and `rebuttal`, an optional `attempt` number, and an
optional `new_failures` count.

Nothing constructs one. The name appears in `saffron/events.py` at `:142`,
`:237`, `:241`, `:352`, `:367` and `:776`, all inside that module, and in
`tests/test_events.py`. The only mention elsewhere in `saffron/` is a comment at
`saffron/cell/session.py:612`. `describe` says so itself at
`saffron/events.py:777-781`: "No call site prints one alone today". It stays
rendered for a stated reason. A future consumer "reads one `GateResult` at a
time, and 'the ten kinds render' cannot mean 'eight of them'".

Measured 2026-09-17 across the 54 event logs under `~/.saffron/batches/v0/`:
`Agent` 56004, `PhaseStart` 475, `Preflight` 390, `Attempt` 154, `Teardown` 134,
`Baseline` 64, `Ceilings` 38, `Budget` 4, `Terminal` 2. `GateResult` appears
zero times.

What the log carries instead is two lossy summaries.

- One `Baseline` per run joins every gate and status into a single line, by
  design: its own docstring calls for "one event, one line per fact present".
  The statuses are there, and nothing ties a duration or a failure count to a
  gate.
- One `Attempt` per suite carries a count. On `SA-0095` the whole of GATE and
  REPAIR reads as `gates: attempt 1, 1 new failures -> repair` and then
  `gates: attempt 2, 0 new failures -> green`. Which gate failed is absent.

The ledger has all of it. `record_gate_result` is called at
`saffron/cell/session.py:1402` for the baseline, with `run_id`, and at
`saffron/cell/session.py:1836` for each attempt, with `attempt_id`. So a person
holding the event log alone cannot answer which gate sent a task back to REPAIR,
while a person holding the ledger can.

**The third `against` value has no site, and that is item 160.** Production
calls `record_gate_result` at those two places only. The Gate-only suite REVIEW
is shown lands in `lens-gates.json` and in no ledger row. §4.1 sets exactly one
of `attempt_id` and `run_id`, and that suite is neither. So `rebuttal` stays
unproduced until item 160 decides what the suite belongs to.

## Problem

- **The event log cannot name the gate that caused a repair turn.** That is the
  question a repair loop exists to answer.
- **A durable record is worse than the ledger beside it.** Both are written in
  the same function, from the same objects, three lines apart.
- **`saffron watch` inherits the gap.** It renders the log through `describe`
  and adds no second source, so it shows a count where a gate name belongs.
- **A kind that renders and never exists is a claim.** `events.py` was written
  so structure outlives the terminal scroll. This is the one kind whose
  structure never arrived.

## Out of scope

**The joined `Baseline` line and the `Attempt` count.** Both stay exactly as
they are. They are summaries an operator reads at a glance, and the per-gate
events sit beside them rather than replacing them. Removing either is a
regression this spec must not cause.

**`against: "rebuttal"`.** It has no producer because the Gate-only suite has no
owner, which is backlog item 160 and a schema decision. Do not invent a site for
it, and do not emit a borrowed attempt number.

**`saffron/events.py`.** It is forbidden. The kind, its fields and its renderer
all exist and need no change. A diff that touches them is a sign the events are
being reshaped rather than emitted.

**`saffron/watch.py` and its noise filter.** Forbidden. A per-gate event is a
host fact, not agent chatter, and `_is_noise` keys on payload shapes that this
spec does not add.

**The ledger writes.** `saffron/ledger.py` is forbidden. Both
`record_gate_result` calls stay where they are and keep their arguments.

## Notes for the agent

**This spec's change is new code.** All three criteria declare a witness and no
mutant. No call site exists, so nothing pins honestly. Expect `witness` to
report `skip` for all three.

**Emit beside the existing write, from the same object.** Both
`record_gate_result` calls already hold the `GateResult` the gate contract
produced. Read its gate, status and duration from there rather than recomputing
any of it. A second source for the same fact is how the two records come to
disagree.

**`error` is not `fail`.** `fail` means the repo's code is wrong, and `error`
means the gate broke and is charged to nobody. The kind's docstring says all
four statuses are representable and neither is inferred from the other. Carry
the contract's status through unchanged.

**`new_failures` is `None` and never `0` for a gate that did not compute one.**
The field's own comment says why: a skipped or errored gate had no count. Zero
is a measurement, and absent is the truth.

**Criterion 2's wrong implementation is the latest attempt number.** The suite
runs once per attempt, and the loop variable is easy to lose. Every event then
carries the last number. Drive two attempts, and assert the first set still
carries 1 after the second set is written.

**Criterion 1's wrong implementation is `against` inferred from the id.** That
couples the event to the ledger call. Deriving the value from whether `run_id`
or `attempt_id` was passed reproduces today's shape. The field's own comment
says it is required rather than defaulted, so a forgotten keyword cannot file a
baseline result as an attempt's. Pass it explicitly at each site.

**The two sites are in one function and one file.** Keep the diff to those two
places plus the tests. `census` compares test names, so rename nothing, and two
queued specs also name `tests/test_session.py`.

**Import anything new inside the test body.** Module scope does not work. A
module-scope import of a name this change adds turns `revert`'s reverted run
into a collection error. `revert` reads that error as `skip`, and the
anti-theater gate then checks nothing.

Commit after each coherent step. Uncommitted work dies with the cell.
