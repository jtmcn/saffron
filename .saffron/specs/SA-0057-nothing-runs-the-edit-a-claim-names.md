---
id: SA-0057
title: a mutant can be declared and nothing applies it, so a claim guarded by nothing still passes
type: feature
priority: 1
depends_on:
  - SA-0056
touches:
  - saffron/gates/core/witness.py
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
  - saffron/cell/**
  - saffron/phases/**
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/preflight.py
  - saffron/reconcile.py
  - saffron/replay.py
budget_usd: 12
max_attempts: 3
max_turns: 90
risk: elevated
acceptance:
  - claim: >-
      A witness that dies under its claim's mutant passes. The gate applies
      the edit, invokes the repo's declared `tests` gate over exactly that one
      node id, and reads a `fail` as the answer it wanted — the only gate in
      the system for which a failing test is the passing result.
    witness: tests/test_witness_gate.py::test_a_witness_that_dies_under_its_mutant_passes
  - claim: >-
      A witness that survives its mutant fails, and the failure names the
      criterion, the witness and the edit. This is the whole gate: the claim
      says a property holds, the mutant removes it, and the witness noticed
      nothing.
    witness: tests/test_witness_gate.py::test_a_witness_that_survives_its_mutant_fails
  - claim: >-
      The tree is byte-identical once the gate is done, whether the witness
      died, survived, or the mutant never applied. It executes inside the
      worktree the task is packaged from, so a mutant left behind would ship
      in the diff.
    witness: tests/test_witness_gate.py::test_the_tree_is_unchanged_however_the_gate_ends
  - claim: >-
      A mutant that does not apply is `skip` for that criterion and is named
      in the summary — never `pass`, and never counted as a witness that did
      its job. A check that quietly buys nothing is the defect this gate
      exists to catch, one level up.
    witness: tests/test_witness_gate.py::test_a_mutant_that_did_not_apply_is_named_not_counted
  - claim: >-
      A `tests` gate that reports `error` under the mutant is `error` here
      too, not `fail`. A test runner that could not start says nothing about
      whether the witness guards its claim, and charging that to the task is
      the collapse `DESIGN.md` refuses everywhere else.
    witness: tests/test_witness_gate.py::test_a_runner_that_broke_under_the_mutant_is_an_error
  - claim: >-
      A spec whose criteria declare no mutants reports `skip` with a summary
      saying so. Every spec that exists today is in that state, and this gate
      must not fail a task for a field its own spec predates.
    witness: tests/test_witness_gate.py::test_a_spec_with_no_mutants_skips
  - claim: >-
      The gate restores the tree before invoking anything else, so two
      criteria cannot interact. Each mutant is applied to a clean tree and
      undone before the next, which is what makes a survivor attributable to
      one claim rather than to the pair.
    witness: tests/test_witness_gate.py::test_two_criteria_do_not_see_each_others_mutants
  - claim: >-
      The `tool` field is obtained by executing the `tests` gate, never
      written as a literal. This is the invariant that separates a gate that
      ran from one that never did, and it is the whole reason this gate
      re-invokes a declared gate rather than shelling out to a runner.
    witness: tests/test_witness_gate.py::test_the_tool_is_the_one_the_tests_gate_reported
---

## Context

`DESIGN.md` §5.4.1, and `docs/BACKLOG.md` item 69. `SA-0056` added the `mutant`
field and an applier that can put a file back exactly as it found it. Nothing
applies one.

## Problem

- **A claim, a witness, and now an edit that would falsify the claim — and no
  code that runs the three together.** The data is inert until something
  applies the mutant and asks the witness whether it noticed.
- **`criteria` (§5.4) checks the witness exists and passes**, which a witness
  guarding nothing satisfies exactly. That gap is what nine shipped tests went
  through in one session.

## The shape, and the invariant that decides it

**Core invokes declared gates, never tools** (§2.1). This gate applies a text
edit the *spec* supplied — data, not code — and then invokes the repo's own
`tests` gate through the same JSON contract every gate uses, with the subset
argument `revert` established. It runs no runner, knows no framework, and
parses no node id. `revert` (§5.4) is the precedent and the shape to copy.

**A failing test is the passing result**, and it is the only gate here for
which that is true. Say it in the module docstring: the next reader will
otherwise "fix" the comparison.

**`error` is not `fail`.** A `tests` gate that could not start under the mutant
has answered nothing. It aborts and is charged to nobody.

## Out of scope

**Declaring the gate, or wiring it into a policy.** `.saffron/**` is
`forbidden`. `SA-0058` decides where it runs and at which blocking level.

**Generating mutants.** No agent writes one; §5.4.1 gives the reason.

**Reaching sub-file granularity by any other route.** Hunk-level reversion was
priced and does not work: a diff that adds a function has one hunk, reverting
it kills every test trivially, and the token-level property inside goes
unmeasured. All nine defects that motivate this live below hunk granularity.

**This spec's own witnesses declaring mutants.** They could — `SA-0056` will
have landed at this spec's `base_sha` — and they deliberately do not, because a
gate whose own tests depend on the gate is a circle. The first spec to declare
mutants should be one that does not build this machinery.
