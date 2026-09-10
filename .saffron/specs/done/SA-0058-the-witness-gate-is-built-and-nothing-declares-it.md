---
id: SA-0058
title: the witness gate is built and no repo declares it, so it runs on nothing
type: feature
priority: 1
depends_on:
  - SA-0057
touches:
  - saffron/gates/runner.py
  - saffron/gates/contract.py
  - tests/test_gates.py
  - tests/test_witness_gate.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - saffron/cli.py
  - saffron/batch.py
  - saffron/intake.py
  - saffron/mutation.py
  - saffron/gates/core/witness.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/preflight.py
  - saffron/reconcile.py
  - saffron/replay.py
budget_usd: 10
max_attempts: 3
max_turns: 80
risk: elevated
acceptance:
  - claim: >-
      `witness` is a core gate the runner invokes like the others, and it runs
      after `tests` rather than beside it. It re-invokes the `tests` gate, so
      a `tests` result that does not exist yet is one it cannot read.
    witness: tests/test_gates.py::test_the_witness_gate_runs_after_the_tests_it_re_invokes
  - claim: >-
      It is advisory at `standard` and blocking at `elevated` — `size`'s own
      levels, for `size`'s own reason. An elevated diff is where a
      plausible-looking wrong change hurts most, and a claim guarded by
      nothing is exactly that.
    witness: tests/test_gates.py::test_witness_is_advisory_at_standard_and_blocking_when_elevated
  - claim: >-
      A repo whose `tests` gate refuses a subset argument gets `skip`, not
      `error`. The subset is `revert`'s contract obligation and a repo may not
      have met it; a gate that cannot run says so and does not take the task
      down.
    witness: tests/test_gates.py::test_a_tests_gate_that_takes_no_subset_skips_the_witness_gate
  - claim: >-
      Its result carries, per criterion, the witness and whether the mutant
      applied — not a bare count. `census` and `criteria` both learned this:
      an operator tracing why a night stopped needs the row, and a count is
      the shape that cannot be traced.
    witness: tests/test_gates.py::test_the_result_names_each_criterion_not_a_count
  - claim: >-
      A blocking `witness` failure reaches the phase that reads gate results
      the same way every other blocking failure does, with no special case.
      It is an ordinary blocking gate that happens to invert one comparison
      internally.
    witness: tests/test_witness_gate.py::test_a_blocking_witness_failure_is_an_ordinary_blocking_failure
---

## Context

`DESIGN.md` §5.4.1, `docs/BACKLOG.md` item 69. `SA-0056` built the data,
`SA-0057` built the gate, and nothing invokes it.

## Problem

- **A gate no runner calls is item 18's pattern wearing a gate** — code written
  and read by nobody. `witness` exists and no attempt runs it.
- **Its blocking level is undecided in code.** §5.4.1 fixes it as advisory at
  `standard` and blocking at `elevated`; nothing implements that, and
  `factory:CoreGateBlockingShape` is one of the two shape lists `CLAUDE.md`
  says stays hand-maintained precisely because the vocabulary cannot imply it.

## Two things this spec decides by choosing a blocking level

Both came out of `SA-0057`'s review rounds, and neither is visible from inside
`saffron/gates/core/witness.py` — they are consequences of *turning the gate
on*, which is what this spec does.

**A survivor finding is discarded if a later criterion errors.** The gate
returns on the first inner `error`, so a night where criterion 1's witness
survived its mutant — a real blocking finding — and criterion 2's `tests` gate
then reported `error` returns `error` with `failures: 0`. The finding is lost
and the attempt aborts charged to nobody. That follows from
`session.aborted_gates` and is the same trade `revert` makes; it matters here
because a blocking level is what decides whether the lost finding would have
stopped anything.

**`witness` and `revert` disagree about the same trap, deliberately.** An inner
`error` ends the attempt, and a mutant that kills its witness by making a
fixture raise produces exactly that — `.saffron/gates/tests.py` reports `error`
when pytest exits non-zero with no `FAILED ` line to parse. `revert` met this
and chose `skip`, calling that choice "the whole gate's usability"; `SA-0057`
asked for `error` and the `ponytail:` at that line names the disagreement.
Choosing a blocking level without deciding this is choosing it by accident.

Neither is this spec's to *fix* — `witness.py` is `forbidden` here. What this
spec owes them is a blocking level chosen in full knowledge of both, and a note
in the backlog if the answer is that the gate should not block until they are
resolved.

## Out of scope

**Declaring it in this repo's `.saffron/policy.yaml`.** `.saffron/**` is
`forbidden` to every cell. Turning it on here is an operator's edit, and it
should be made only after the gate has run advisory for a while and its
survivor rate is known — which is `docs/BACKLOG.md` item 69's remaining half.

**Backfilling mutants onto retired specs.** Every spec in this repo declares
none, so this gate reports `skip` on all of them until new specs are written
with mutants. That is the intended landing: the mechanism arrives inert and
earns its blocking level on evidence.

**`saffron/gates/core/witness.py`.** `SA-0057` owns it and it is `forbidden`
here. This spec wires what that spec built; if wiring reveals the gate needs a
different shape, that is a finding to file rather than an edit to make.
