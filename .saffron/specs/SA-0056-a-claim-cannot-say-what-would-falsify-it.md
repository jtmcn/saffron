---
id: SA-0056
title: an acceptance claim cannot say what would falsify it, so nothing can check that it is guarded
type: feature
priority: 1
touches:
  - saffron/intake.py
  - saffron/mutation.py
  - tests/test_intake.py
  - tests/test_mutation.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - saffron/cli.py
  - saffron/batch.py
  - saffron/gates/**
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
risk: standard
acceptance:
  - claim: >-
      An acceptance criterion may declare a `mutant` beside its claim and
      witness — a file, the text to find, and what to put in its place. A
      criterion without one parses exactly as it does today, because every
      spec in this repo has none and none may be rewritten to gain one.
    witness: tests/test_intake.py::test_a_criterion_may_declare_the_edit_that_falsifies_it
  - claim: >-
      A mutant naming no file, or an empty `find`, is refused at parse rather
      than discovered at gate time. An empty `find` matches at every
      position in the file, so it is not a weak mutant but an unrunnable one.
    witness: tests/test_intake.py::test_a_mutant_with_nothing_to_find_is_refused_at_parse
  - claim: >-
      Applying a mutant to a tree replaces the found text and returns the
      exact bytes it displaced, so the caller can put them back. Restoring is
      the caller's obligation and the applier's promise, because a gate that
      leaves a mutated worktree behind has corrupted the attempt it was
      checking.
    witness: tests/test_mutation.py::test_applying_a_mutant_returns_what_it_displaced
  - claim: >-
      A `find` that appears more than once does not apply, and says so rather
      than editing the first occurrence. Two matches mean the mutant does not
      name one property, and picking one of them silently is how a check comes
      to measure something other than what it claims.
    witness: tests/test_mutation.py::test_a_find_that_matches_twice_does_not_apply
  - claim: >-
      A `find` that appears nowhere does not apply, and the reason names the
      file and the text. This is the ordinary case when an implementation is
      written differently from what the spec anticipated, and it must read as
      "this mutant did not apply" and never as "the witness survived".
    witness: tests/test_mutation.py::test_a_find_that_matches_nothing_does_not_apply
  - claim: >-
      Applying and restoring leaves the file byte-identical, including its
      trailing newline and line endings. The gate executes inside the worktree a
      task is being packaged from, so anything it does must be undone exactly.
    witness: tests/test_mutation.py::test_apply_then_restore_is_byte_identical
  - claim: >-
      A mutant may not name a path outside the tree it is applied to. A spec
      is data the host reads and the operator writes, but `..` in a declared
      path is the shape that turns a check into an arbitrary write, and the
      applier refuses it rather than resolving it.
    witness: tests/test_mutation.py::test_a_mutant_cannot_escape_the_tree_it_is_applied_to
---

## Context

`docs/BACKLOG.md` item 69, and `DESIGN.md` §5.4.1 specifies the gate this is
the first half of. This spec builds the *data* — how a spec says what would
falsify a claim, and how that edit is applied and undone. It builds no gate.

Nine tests shipped in one session naming a behaviour they did not guard, each
past every gate and all three lenses. Vacuity is not visible in a test's text,
because a vacuous test and a sound one are textually identical; it is visible
only in how the pair responds to being perturbed.

## Problem

- **A claim asserts a property and names a witness, and nothing connects the
  two.** `criteria` (§5.4) checks that the witness *exists and passes*. A
  witness that passes while guarding nothing satisfies it exactly.
- **The information needed to check this is not written down anywhere.** §5.5.1
  already asks the adequacy lens to name "the smallest edit that would keep the
  suite green while the behaviour breaks" — in prose, in a finding, after the
  fact, unexecutable. The spec is where that edit belongs, beside the claim it
  falsifies.

## A note on this spec's own witnesses

They are plain claim-and-witness pairs, with no `mutant:` of their own. They
cannot have one: the field is what this spec adds, and a spec is parsed against
the export at its own `base_sha`, where `Criterion` still forbids it. The first
spec that can declare a mutant is the one after this.

That is worth saying rather than leaving as an apparent omission — a reader who
finds the mechanism unused in the spec that builds it should find the reason
here and not have to work it out.

## The shape

A `Mutant` is three fields — `file`, `find`, `replace` — and `find` must match
exactly once. Not a unified diff: a diff carries line numbers, and a mutant
that names line 51 stops meaning anything the moment the implementation shifts
by a line. Exact text is stable under everything except a rewrite of the
construct itself, and a rewrite of the construct is a change the claim should
notice.

`apply` returns what it displaced. Restoring is the caller's obligation, and
this spec's tests are what make it possible rather than merely intended.

## Out of scope

**The gate.** `saffron/gates/**` is `forbidden`. `SA-0057` builds the gate that
applies these and invokes the repo's `tests` gate over one witness.

**Generating a mutant.** No agent writes one. §5.4.1 gives the reason and it is
not cost: a cell is untrusted, and a mutant it authored is a mutant chosen to
be killed.

**Backfilling mutants onto existing specs.** `.saffron/**` is `forbidden` and
every spec in this repo is retired. A criterion without a `mutant` must parse
and behave exactly as it does today, which is what the first witness pins.

**Deciding what an unapplied mutant means.** The applier reports `ok=False` and
a reason. Whether that is a `skip`, a `fail`, or a refusal is §5.4.1's answer
and `SA-0057`'s code.
