---
id: SA-0062
title: the stub mutator cannot reach the volume a cell's worktree lives on
type: feature
priority: 1
depends_on:
  - SA-0061
touches:
  - saffron/cell/worktree.py
  - saffron/cell/session.py
  - tests/test_worktree.py
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
  - saffron/cell/proxy.py
budget_usd: 12
max_attempts: 3
max_turns: 90
risk: elevated
acceptance:
  - claim: >-
      A mutant is applied inside the cell and undone there, through the
      container — the shape `source_reverted` already uses for the one other
      piece of worktree mutation this module owns. The host never writes to
      the volume, because it cannot.
    witness: tests/test_worktree.py::test_a_mutant_is_applied_and_undone_inside_the_cell
  - claim: >-
      The undo is `git checkout` against `HEAD`, not a replay of displaced
      bytes. The agent's work is committed by the time gates run — `committed`
      is what guarantees it — so `HEAD` is exactly what a mutated file should
      return to, and `revert` restores the same way for the same reason.
    witness: tests/test_worktree.py::test_the_undo_restores_the_committed_file_not_a_byte_copy
  - claim: >-
      A find that does not match exactly once applies nothing and says so, the
      same rule the host mutator follows. A mutant that names two places names
      no property, and picking one silently is how a check comes to measure
      something other than what it claims.
    witness: tests/test_worktree.py::test_a_find_that_does_not_match_once_applies_nothing
  - claim: >-
      A failure to apply or to undo raises rather than reporting a verdict,
      and the gate turns that into `skip` or `error` — never `pass` or `fail`.
      A tree this could not restore is the one outcome that must not read as a
      witness doing its job.
    witness: tests/test_worktree.py::test_a_failed_undo_raises_rather_than_reporting_a_verdict
  - claim: >-
      The cell run supplies this mutator in place of the stub, so `witness`
      reaches a real verdict on a real attempt. Every spec in this repo
      declares no mutants, so that verdict is `skip` for want of anything to
      check — which is the intended landing, and the difference from the
      previous `skip` is that this one is a choice rather than a limitation.
    witness: tests/test_session.py::test_a_cell_run_supplies_the_real_mutator
---

## Context

`docs/BACKLOG.md` item 71, last of three. `SA-0060` gave the gate an injected
mutator; `SA-0061` wired a stub into a cell run and turned the gate on. This
replaces the stub.

## Problem

The stub reports it cannot reach the tree, so every `witness` result is `skip`
for the wrong reason. A cell's worktree is on a volume mounted at `/work`, and
nothing yet mutates a file there.

## The shape

`worktree.source_reverted(container, tree_base, paths)` is the precedent and
sits in the file this spec touches: a context manager that runs git inside the
container and restores from a `finally`. `source_mutated` is its sibling —
apply the find/replace inside the cell, and undo with `git checkout HEAD --`.

**The undo is git, and that is what makes this small.** `SA-0056`'s host
applier carries displaced bytes and a whole-file digest because a host path has
no better answer available. A cell does: `committed` guarantees the agent's
work is committed before gates run, so the file's committed state is exactly
what a mutated file should return to. None of the byte-level machinery needs to
cross into the container.

## Out of scope

**The host mutator.** `saffron/mutation.py` is `forbidden` and unchanged. Two
implementations of one callable is the design, not duplication to collapse.

**Any spec declaring mutants.** Every spec in this repo declares none, so the
gate lands reporting `skip` — now because there is nothing to check rather than
because it cannot look. The first spec to declare a mutant should be the one
after this, and it is the first real exercise of everything item 69 built.

**`saffron/gates/**`.** If the mutator cannot satisfy the callable's contract
as `SA-0060` wrote it, that is a finding to file rather than a signature to
edit from this side.
