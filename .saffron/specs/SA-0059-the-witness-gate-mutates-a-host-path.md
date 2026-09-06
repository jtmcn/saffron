---
id: SA-0059
title: the witness gate mutates a host path, and a cell's worktree has none
type: feature
priority: 1
touches:
  - saffron/gates/core/witness.py
  - saffron/mutation.py
  - saffron/gates/runner.py
  - saffron/cell/worktree.py
  - saffron/cell/session.py
  - tests/test_witness_gate.py
  - tests/test_mutation.py
  - tests/test_gates.py
  - tests/test_worktree.py
  - tests/test_session.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - saffron/cli.py
  - saffron/batch.py
  - saffron/intake.py
  - saffron/scheduler.py
  - saffron/preflight.py
  - saffron/reconcile.py
  - saffron/replay.py
  - saffron/phases/**
  - saffron/gates/contract.py
budget_usd: 16
max_attempts: 4
max_turns: 110
risk: elevated
acceptance:
  - claim: >-
      Applying a mutant is an injected context manager, not a path the gate
      writes to. `witness_gate` takes a callable from a mutant to a context
      manager that applies it on entry and undoes it on exit, and the gate
      itself holds no `Path` and performs no file I/O — which is what lets one
      gate serve a host tree and a cell's volume without knowing which it has.
    witness: tests/test_witness_gate.py::test_the_gate_mutates_through_an_injected_context_manager
  - claim: >-
      The context manager restores on exit however the block ends — a witness
      that died, one that survived, an inner `error`, or an exception in
      flight. Ownership moved on purpose: only the thing that knows how to
      reach the tree knows how to put it back, and the gate can no longer leak
      a mutated tree by forgetting.
    witness: tests/test_witness_gate.py::test_the_mutation_is_undone_however_the_block_ends
  - claim: >-
      An interrupt during a mutated run still propagates, and still restores.
      This is `SA-0057`'s worst defect and it must survive the seam moving:
      the restore now lives in the context manager's own exit path, which is
      the one place a `BaseException` cannot route around.
    witness: tests/test_witness_gate.py::test_an_interrupt_still_propagates_through_the_new_seam
  - claim: >-
      A host tree gets a mutator that reads and writes bytes — the behaviour
      `SA-0056` built, unchanged, including the whole-file digest that refuses
      a restore into a tree that moved. Tests and any host-side caller use it;
      it is one implementation of the callable, no longer the gate's own body.
    witness: tests/test_mutation.py::test_the_host_mutator_applies_and_restores_byte_identically
  - claim: >-
      A cell's worktree gets a mutator that goes through the container, the
      shape `revert` already uses for the one piece of tree mutation it owns.
      It applies inside the cell and restores with git, because the agent's
      work is committed by then and `HEAD` is what the file should return to.
    witness: tests/test_worktree.py::test_a_mutant_is_applied_and_undone_inside_the_cell
  - claim: >-
      A cell run supplies both the mutator and the acceptance criteria, so
      `witness` produces a result on a real attempt. This is the sentence the
      whole spec exists for: before it, `run_suite`'s `tree` parameter was one
      no production caller could supply, and the gate ran on nothing.
    witness: tests/test_session.py::test_a_cell_run_produces_a_witness_result
  - claim: >-
      `witness` is advisory at `standard` and blocking at `elevated`, in
      effect and not only in `contract.witness_blocking`. Whatever decides
      what an attempt does with a blocking failure agrees with that function,
      rather than defaulting it to blocking at every tier for want of an
      entry.
    witness: tests/test_session.py::test_a_witness_failure_is_advisory_at_standard_and_blocking_when_elevated
  - claim: >-
      A repo whose worktree the mutator cannot reach reports `skip`, never
      `error`. A gate that could not run says so; ending the attempt over it
      would charge a task for infrastructure, which is the collapse this
      system refuses everywhere else.
    witness: tests/test_witness_gate.py::test_a_mutator_that_cannot_reach_the_tree_skips
---

## Context

`docs/BACKLOG.md` item 71. `DESIGN.md` §5.4.1 specifies the gate; `SA-0056`,
`SA-0057` and `SA-0058` built and wired it, and it runs on nothing.

## Problem

**`witness_gate` takes `tree: Path` and mutates it with host file I/O.** During
a cell run there is no such path — `saffron/cell/worktree.py` says so in its
first paragraph: *"Work happens on the volume, not a bind mount."* So
`run_suite(..., tree=...)` is not a parameter no caller supplies yet; it is one
no production caller can ever supply. Three merged specs and the gate has never
produced a result on a real attempt.

**And the blocking level is decided in prose and contradicted in effect.**
`contract.witness_blocking` returns `tier == "elevated"`. Nothing reads it, and
`session._blocking` is `failure.gate not in advisory_gates`, a set that gains
only `size` at non-elevated tiers — so a `witness` failure blocks at
`standard`, the opposite of §5.4.1 and of the function written to say so.

## The shape, and why it is `revert`'s

`revert` owns the only other piece of worktree mutation in the system, and it
does not hold a path either. It takes `Reverted = Callable[[list[str]],
AbstractContextManager[None]]`, and a cell run hands it
`worktree.source_reverted(container, tree_base, paths)` — which reverts *inside*
the container and restores from a `finally`. Copy that, one noun over.

Two consequences worth stating because they are the point rather than side
effects:

**Restoration moves into the context manager.** `SA-0057` spent a `try/finally`,
two recorded-failure variables and a review round on restoring the tree on every
exit path, and still shipped a `return` inside a `finally` that swallowed a
Ctrl-C. A context manager's exit is the one place a `BaseException` cannot route
around, and the thing that knows how to reach the tree is the only thing that
knows how to put it back.

**The cell mutator restores with git, not with bytes.** `SA-0056`'s applier
carries the displaced bytes and a whole-file digest because a host path has no
better answer. A cell does: the agent's work is committed by the time gates run
— `committed` is what guarantees it — so `HEAD` is exactly what a mutated file
should return to, and `revert` already restores that way for the same reason.

## Out of scope

**Changing what the gate decides.** The four-way inversion, the unproven
accounting, the pre-flight probe and its `_argv_safe` filtering all stay as
`SA-0057` and `SA-0058` left them. This moves where the mutation happens, not
what a survivor means.

**`witness`'s absence from the vocabulary** (item 72). `ontology/` and
`CONTEXT.md` are `forbidden` here, and the gate's blocking level being wrong in
`session` is this spec's half of that item, not the entry itself.

**Declaring mutants on this spec's own criteria.** They would be the first, and
this is the spec that makes the gate able to judge them — a gate whose first
real subject is the change that turned it on is a circle, and an attempt that
cannot pass because the mechanism it is building is subtly wrong is unreadable.
The spec after this one is the first that should declare them, and the first
real exercise of the gate.

**`phases/package.py`'s re-verification.** It calls `run_suite` without `tree`
too, so PACKAGE's suite and the session's would differ in shape. `forbidden`
here to keep this spec to one seam; file it if this lands and it still matters.

## If the plan checkpoint refuses this

It might: five source files at `elevated`, where `size` is blocking. The split
is a *sequence*, not three independent specs, and its order is the point —
**wire first, build second**, which is the inverse of what item 69's chain did
and the reason item 71 exists:

1. `witness_gate` takes the injected callable; `mutation.host_mutator` supplies
   today's behaviour; `runner` passes it through. Nothing else moves, every
   existing test still passes.
2. `session` supplies a *stub* mutator and the acceptance criteria, and
   `advisory_gates` gains `witness`. The gate now produces a result on a real
   attempt, and the result is honest: `skip`, because the stub cannot reach the
   tree.
3. `worktree.source_mutated` replaces the stub.

Splitting the other way — build the cell mutator first, wire last — is what
produced item 71.
