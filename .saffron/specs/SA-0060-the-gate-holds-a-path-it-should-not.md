---
id: SA-0060
title: the witness gate holds the path it mutates, so only a host tree can ever be given to it
type: refactor
priority: 1
touches:
  - saffron/gates/core/witness.py
  - saffron/mutation.py
  - saffron/gates/runner.py
  - tests/test_witness_gate.py
  - tests/test_mutation.py
  - tests/test_gates.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - saffron/cell/**
  - saffron/phases/**
  - saffron/cli.py
  - saffron/batch.py
  - saffron/intake.py
  - saffron/scheduler.py
  - saffron/preflight.py
  - saffron/reconcile.py
  - saffron/replay.py
  - saffron/gates/contract.py
budget_usd: 12
max_attempts: 3
max_turns: 90
risk: elevated
acceptance:
  - claim: >-
      The gate takes a callable from a mutant to a context manager, and holds
      no path of its own. It performs no file I/O — which is what lets one
      gate serve a host tree and a cell's volume without knowing which it has,
      and it is the only reason this refactor exists.
    witness: tests/test_witness_gate.py::test_the_gate_mutates_through_an_injected_context_manager
  - claim: >-
      The context manager restores on exit however the block ends — a witness
      that died, one that survived, an inner `error`, or an exception in
      flight. Ownership moves on purpose: a context manager's exit is the one
      place a `BaseException` cannot route around, and the gate spent a review
      round and a swallowed interrupt learning that by hand.
    witness: tests/test_witness_gate.py::test_the_mutation_is_undone_however_the_block_ends
  - claim: >-
      An interrupt during a mutated run still propagates and still restores.
      This is the defect this gate already shipped once; it must survive the
      seam moving, and it is the reason the restore lives in the exit path
      rather than in a `finally` the gate writes.
    witness: tests/test_witness_gate.py::test_an_interrupt_still_propagates_through_the_new_seam
  - claim: >-
      A host tree gets a mutator with exactly today's behaviour, whole-file
      digest included, refusing a restore into a tree that moved and a second
      restore that would double-insert. It becomes one implementation of the
      callable rather than the gate's own body; nothing about it changes.
    witness: tests/test_mutation.py::test_the_host_mutator_applies_and_restores_byte_identically
  - claim: >-
      A mutator that cannot reach the tree reports `skip`, never `error`. A
      gate that could not run says so; ending the attempt over it would charge
      a task for infrastructure. This is the branch the next spec's stub
      relies on, so it is built and witnessed here where nothing depends on it
      yet.
    witness: tests/test_witness_gate.py::test_a_mutator_that_cannot_reach_the_tree_skips
  - claim: >-
      `run_suite` and `run_witness` pass the callable through in place of a
      path, and every existing caller and test still gets the same answers.
      This is a refactor: the gate decides exactly what it decided before, and
      the pre-flight probe, the four-way inversion and the unproven accounting
      are untouched.
    witness: tests/test_gates.py::test_the_wiring_passes_a_mutator_through_and_changes_no_verdict
---

## Context

`docs/BACKLOG.md` item 71, and the first of three. `SA-0059` asked for the
whole seam in one spec and reached `EXHAUSTED`: nine files at `elevated`, two
attempts into the 110-turn ceiling, $26.75 and no pull request
(`docs/evidence/2026-09-06-an-attempt-is-the-overshoot-bound.md`). This is that
spec's own contingency, in the order it named.

## Problem

`witness_gate` takes `tree: Path` and mutates it with host file I/O. A cell's
worktree is on a volume — `saffron/cell/worktree.py` says so in its first
paragraph — so there is no host path to give it, and `run_suite(..., tree=...)`
is a parameter no production caller can supply. Three merged specs, and the
gate has never produced a result on a real attempt.

## The shape, and why it is `revert`'s

`revert` owns the only other piece of worktree mutation in the system and holds
no path either: it takes `Reverted = Callable[[list[str]],
AbstractContextManager[None]]`, and a cell hands it
`worktree.source_reverted(container, tree_base, paths)`. Copy that, one noun
over — a callable from a `Mutant` to a context manager that applies on entry
and undoes on exit.

**Restoration moves with it, and that is the point rather than a side effect.**
`SA-0057` spent a `try/finally`, two recorded-failure variables and two review
rounds restoring the tree on every exit path, and still shipped a `return`
inside a `finally` that swallowed a Ctrl-C, then an `OSError` raised from that
same `finally` which replaced the interrupt. Both are shapes a context
manager's exit does not have.

## Out of scope

**Any caller.** `saffron/cell/**` is `forbidden`. Nothing supplies a real
mutator when this lands, and `run_suite`'s parameter stays unsupplied — the
gate is exactly as inert as it is today, in a shape that can stop being.
`SA-0061` wires it.

**Changing what the gate decides.** The pre-flight probe, its `_argv_safe`
filtering, the four-way inversion and the unproven accounting stay as
`SA-0057` and `SA-0058` left them. A verdict that changes here is a defect.

**Declaring mutants on this spec's own criteria.** The gate cannot run yet.
The first spec that should declare them is the one after `SA-0062`.
