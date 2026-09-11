---
id: SA-0061
title: a cell run supplies no mutator and no criteria, so the gate still produces nothing
type: feature
priority: 1
depends_on:
  - SA-0060
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
  - saffron/gates/**
  - saffron/mutation.py
  - saffron/phases/**
  - saffron/cli.py
  - saffron/batch.py
  - saffron/intake.py
  - saffron/scheduler.py
  - saffron/preflight.py
  - saffron/reconcile.py
  - saffron/replay.py
  - saffron/cell/worktree.py
  - saffron/cell/runtime.py
  - saffron/cell/proxy.py
budget_usd: 8
max_attempts: 3
max_turns: 70
risk: elevated
acceptance:
  - claim: >-
      A cell run supplies the acceptance criteria and a mutator, so `witness`
      produces a result on a real attempt. This is the sentence three merged
      specs did not reach: before it, the gate ran on nothing.
    witness: tests/test_session.py::test_a_cell_run_produces_a_witness_result
  - claim: >-
      The mutator supplied is a stub that reports it cannot reach the tree, so
      the result is `skip` and no mutant is applied. Honest rather than
      convenient: the cell-side mutator is the next spec, and a gate that
      reported anything else here would be reporting a verdict it did not
      reach.
    witness: tests/test_session.py::test_the_stub_mutator_makes_the_result_an_honest_skip
  - claim: >-
      `witness` is advisory at `standard` and blocking at `elevated` in
      effect, agreeing with `contract.witness_blocking` rather than defaulting
      to blocking at every tier for want of an entry in the advisory set.
    witness: tests/test_session.py::test_a_witness_failure_is_advisory_at_standard_and_blocking_when_elevated
  - claim: >-
      A `skip` blocks nothing at any tier, so turning the gate on cannot fail
      a task while the mutator is a stub. This is what makes it safe to land
      the wiring before the mutator exists, and it is the property the whole
      sequence rests on.
    witness: tests/test_session.py::test_a_skipped_witness_blocks_nothing_at_either_tier
---

## Context

`docs/BACKLOG.md` item 71, second of three. `SA-0060` gave the gate an injected
mutator and no caller. This supplies one.

**Wiring before the mutator exists is the point, not an accident of
sequencing.** Item 69's chain built a mechanism across three specs and wired it
last, and the wiring is where anyone discovered the mechanism could not be
wired. Doing it in this order means the seam is exercised end to end while the
expensive part is still a stub, and if the shape is wrong this spec is where it
shows — at $8 rather than at the end of a chain.

## Problem

`session._suite` calls `run_suite(gates, cwd=repo, executor=executor)`. No
acceptance criteria, no mutator. `witness` is a core gate the runner knows how
to invoke and no attempt has ever invoked it.

And the blocking level is decided in prose only. `contract.witness_blocking`
returns `tier == "elevated"`; nothing reads it, and `_blocking` is
`failure.gate not in advisory_gates` over a set that gains only `size` at
non-elevated tiers — so a `witness` failure would block at `standard`, the
opposite of §5.4.1 and of the function written to say so.

## The stub, and what it must not do

It reports that it cannot reach the tree. It does not apply a mutant, does not
touch the worktree, and does not pretend a verdict. The gate's `skip` for an
unreachable tree is `SA-0060`'s, built and witnessed there precisely so this
spec can rely on it.

A `skip` blocks nothing, so this is safe to land: the gate becomes visible in
every suite, produces an honest row, and cannot fail a task until `SA-0062`
gives it a mutator that can actually reach the tree.

## Out of scope

**The cell mutator.** `saffron/cell/worktree.py` is `forbidden`. `SA-0062`
writes `source_mutated` and swaps the stub for it.

**Everything about the gate's own behaviour.** `saffron/gates/**` is
`forbidden`. If wiring reveals the gate needs a different shape, that is a
finding to file — and this time file it, in the pull request body and in
`docs/BACKLOG.md`'s language, because `SA-0058` was asked the same and a lens
withdrew the blocker on the correct observation that editing was out of scope,
which is not the same question as recording.

**PACKAGE's re-verification.** `saffron/phases/**` is `forbidden`; its
`run_suite` call would still omit both arguments, so the two suites differ in
shape. Real, and one seam at a time.
