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
  - tests/test_events.py
  - tests/fixtures/watch-golden.txt
  - saffron/events.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
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
      Every gate result the repair loop's suite produced reaches the log as its
      own event, carrying that attempt's number. Two attempts produce two sets,
      and each set carries its own number rather than the latest one. In a
      suite where no gate errored and nothing drifted, a blocking gate carries
      the count of new failures it contributed, so a passing gate carries zero,
      which is a measurement. An advisory gate and a skipped gate carry no
      count. The suite the post-rebuttal re-run judges emits none of these,
      because it belongs to neither an attempt nor a run.
    witness: tests/test_session.py::test_each_attempts_gate_results_carry_their_own_attempt_number
  - claim: >-
      In an attempt's suite where a gate errored, that gate is emitted with the
      errored status and never the failed one, and no gate in that suite
      carries a count, because the suite aborted before any subtraction ran.
      A suite that drifted carries no count on any gate either, since its
      subtraction is not to be trusted.
    witness: tests/test_session.py::test_an_aborted_or_drifted_suite_counts_nothing_on_any_gate
---

## Context

`saffron/events.py` defines ten kinds. Nine of them have a producer.

(`SA-0101`, the parent, adds an eleventh. Every count of kinds below is
at `origin/main`, and each is one higher on the parent's branch.)

`GateResult` at `saffron/events.py:237-254` is the tenth. Its docstring calls it
"the host's own typed record of the fact a watch line already carried a hundred
times over". It carries `gate`, `status`, `against` with the three values
`baseline`, `attempt` and `rebuttal`, an optional `attempt` number, and an
optional `new_failures` count.

Nothing constructs one. The name appears in `saffron/events.py` at `:142`,
`:237`, `:241`, `:352`, `:367` and `:777`, all inside that module, and in
`tests/test_events.py`. The only mention elsewhere in `saffron/` is a comment at
`saffron/cell/session.py:616`. `describe` says so itself at
`saffron/events.py:778-782`: "No call site prints one alone today". It stays
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
`saffron/cell/session.py:1409` for the baseline, with `run_id`, and at
`saffron/cell/session.py:1848` for each attempt, with `attempt_id`. So a person
holding the event log alone cannot answer which gate sent a task back to REPAIR,
while a person holding the ledger can.

**The third `against` value has no site: item 160.** Production calls
`record_gate_result` at those two places. `saffron/replay.py` also
calls it, and it is v0-only and forbidden. The Gate-only suite REVIEW
is shown lands in `lens-gates.json` and in no ledger row. §4.1 sets exactly one
of `attempt_id` and `run_id`, and that suite is neither. So `rebuttal` stays
unproduced until item 160 decides what the suite belongs to.

**The attempt site serves two different suites, and one of them is not this
spec's.** `_judge` is defined at `saffron/cell/session.py:1833` and called twice.
`repair_loop` takes it as `judge=_judge` at `:1897`, and `_rebut_gates` calls it
directly at `:2169` for the §5.6 post-rebuttal re-run. The ledger write at `:1848`
books that second suite under the rebuttal's extraction turn, which its comment at
`:1840-1845` explains. An unguarded emit at `:1848` therefore files a rebuttal
suite as an attempt's, with a borrowed number. That is the conflation `against`
exists to prevent.

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

**`saffron/events.py`, except two lines of prose.** The kind, its fields and
its renderer all exist and need no change. The change does make two things there
false, and those two change with it. `describe`'s comment at `:778-782` says no
call site prints a `GateResult` alone. `FAMILIES` (`:867`) is the proof its kinds
cover every call site. It gains one row for the new `gates: {gate}={status}`
line, with a prefix distinct from the four `gates:` rows at `:898-901`.
`test_the_table_did_not_quietly_lose_a_row` in `tests/test_events.py` moves its
count by one, from whatever `SA-0101`'s branch left it at. A diff touching
anything else in `events.py` is a sign the events are being reshaped rather than
emitted.

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
produced. Read its gate and status from there rather than recomputing either. A
second source for the same fact is how the two records come to disagree. The event
kind carries no duration field, and `saffron/events.py` is forbidden, so duration
stays ledger-only after this spec.

**Emit nothing from the post-rebuttal call.** `_judge` needs to know which caller
it serves. Give it a parameter, and pass the emitting value only from
`repair_loop`. Do not reach for the rebuttal value instead. That suite has no
owner until item 160 decides one, and a borrowed attempt number is worse than
silence. Criterion 2's last sentence is what pins this, and only a whole cell
driven through REBUT can see it: a unit test over `repair_loop` never reaches
`_rebut_gates`, and a parameter defaulted to emitting passes it. Drive the
witness through `_drive` and REBUT, the way
`test_the_gate_check_after_the_rebuttal_continues_the_gate_count` does, and
assert no `GateResult` follows the `Attempt` whose phase is `REBUT`.

**The attempt number is not in scope at the emit site.**
`saffron/cell/session.py:637` holds the loop `for attempt in range(1, max_attempts
+ 1)`, and that loop belongs to `repair_loop`, which invokes the callback as
`comparison = judge()` at `:638`. Inside `_judge` the only number at hand is the
ledger's `attempt_id` at `:1846`. That is a row id counting every turn, plan,
notes and rebut extraction included, rather than the gate attempt. Thread the real
number in from `repair_loop`. Both `attempt_id` and the length of
`ledger.attempts(...)` are wrong, and criterion 2's witness catches both.

**`error` is not `fail`.** `fail` means the repo's code is wrong, and `error`
means the gate broke and is charged to nobody. The kind's docstring says all
four statuses are representable and neither is inferred from the other. Carry
the contract's status through unchanged.

**A count exists only where a subtraction ran.** `_compare` in
`saffron/gates/suite.py:223-236` returns before `subtract_baseline` when any gate
errored, and again when the suites drifted. `comparison.new_failures` is then
`()`, which reads as zero for every gate. It is not: CONTEXT.md's suite
comparison says the subtraction "is not even attempted" in either case, and the
`Attempt` beside it already says "not computed" (`new_failures=None`). The
subtraction also drops advisory gates (`:233-235`), so an advisory `size` failure
counts nothing there either. A gate's count is the number of
`comparison.new_failures` naming it. It is taken only when the suite neither
aborted nor drifted, and only for a blocking gate that did not skip. Everywhere
else it is `None`.

**Criterion 3's wrong implementation counts whatever `new_failures` holds.**
`None if status == "error" else count(...)` passes an errored-gate check. It
also writes zero on every other gate of an aborted suite, a failing one
included. Drive an attempt's suite with one errored gate, one failing gate and
one passing gate, and assert all three carry no count. Drive it through an
attempt, never the baseline: at the baseline no gate has a count whatever the
implementation does. Criterion 2 carries the converse. A count written to fall
back to absent whenever it is zero collapses a passing gate's measured zero. So
criterion 2's witness asserts that zero in a suite with no errored gate.

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

**The golden fixture changes, and that is why it is in `touches`.**
`test_watch_output_matches_the_golden_fixture` (`tests/test_events.py:1762`)
drives two whole cells. It compares the captured lines byte for byte against
`tests/fixtures/watch-golden.txt`. Its green run carries one joined baseline line
at `:8` and one `gates: attempt 1` line, so a per-gate block lands in both runs.
`test_the_join_covers_every_captured_line_a_kind_renders` (`:1977`) needs every
distinct captured line joined, so `_JOINED` (`:1810`) gains one `GateResult` row
per distinct `gates: {gate}={status}` line, about seven. The header comment at
`:1744-1745` says `GateResult` is never captured, and changes with them.
Append the new rows at the end of `_JOINED`. Its cases have no ids, so an
insertion renumbers the cases after it, and `census` reads that as tests
removed (`:1948-1953`).

**`size` blocks at 300 lines here.** This diff touches `saffron/cell/**`,
which `.saffron/policy.yaml`'s `elevate_on` elevates. At elevated, `size` is not
advisory (`_advisory` in `saffron/gates/suite.py`). The
spec review estimated 255 to 300 lines. Write one shared helper that drives a
cell and collects its `GateResult` events, and use it in all three witnesses.

**`census` compares test names, so rename nothing.**

**`events.GateResult` needs an aliased import.** `saffron/cell/session.py:39`
already binds that name from `saffron.gates.contract`, which is the gate contract
rather than the host's own record. Import the event kind under another name, and
do not shadow the contract.

**Import anything new inside the test body.** Module scope does not work. A
module-scope import of a name this change adds turns `revert`'s reverted run
into a collection error. `revert` reads that error as `skip`, and the
anti-theater gate then checks nothing.

Commit after each coherent step. Uncommitted work dies with the cell.
