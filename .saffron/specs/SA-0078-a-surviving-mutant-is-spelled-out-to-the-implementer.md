---
id: SA-0078
title: a mutant its witness survives is spelled out in the repair turn, so the implementer is shown the edit it will be judged by
type: bug
priority: 2
depends_on: []
touches:
  - saffron/gates/core/witness.py
  - tests/test_witness_gate.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/agents/**
  - saffron/report/**
  - saffron/phases/**
  - saffron/cell/**
  - saffron/repos/**
  - saffron/gates/suite.py
  - saffron/gates/contract.py
  - saffron/gates/runner.py
  - saffron/mutation.py
  - saffron/intake.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/replay.py
budget_usd: 5
max_attempts: 3
max_turns: 40
risk: elevated
acceptance:
  - claim: >-
      A mutant its witness survives fails `witness` with a result that names
      the criterion's claim and its witness, and carries neither the edit's
      `find` text nor its `replace` text anywhere in the result. Today the
      failure's message quotes both, and at `elevated`, where `witness` blocks,
      `repair_prompt` hands that message to the implementer verbatim.
    witness: tests/test_witness_gate.py::test_a_surviving_mutant_names_its_claim_and_not_its_edit
  - claim: >-
      A surviving mutant's failure still names its witness as its `file` and
      `survived-mutant` as its `code`, and still round-trips through the gate
      contract unchanged, as it does today.
    witness: tests/test_witness_gate.py::test_a_blocking_witness_failure_is_an_ordinary_blocking_failure
    preserves: true
---

## Context

`docs/BACKLOG.md` item **109**, found 2026-09-12 while deciding item 80.

A mutant is withheld from the implementer on purpose (`CONTEXT.md`, **Mutant**;
`DESIGN.md` §5.4.1, "The spec may not disclose its own mutant"). If the
implementer knows the edit it will be judged by, it can write a test that kills
that one edit and nothing else, and `witness` then reports `pass` on a test that
guards almost nothing.

`saffron/gates/core/witness.py` builds the `survived-mutant` failure with a
message that quotes the mutant's `find` and `replace` text and its file. At
`elevated`, `witness_blocking` makes that failure blocking (`_advisory` in
`saffron/gates/suite.py`). A blocking new failure goes to the implementer through
`repair_prompt` (`saffron/phases/implement.py`), which renders each failure's
`code` and `message` verbatim. So the first attempt whose witness survives hands
the next attempt the exact edit, and the next attempt can pass by writing a test
aimed at it.

That is the one place the edit's text appears in a gate result. No gate summary
reaches any prompt.

## Problem

The control that keeps a mutant secret is undone by the gate the mutant exists
for, on the one tier where that gate blocks. Whatever item 80 decides about where
mutants are stored, this path leaks them anyway.

## Out of scope

**Where mutants are stored.** Item 80 decided that mutants move out of the spec
file to a ref the cell never fetches. That needs `DESIGN.md` first and is done
by hand.

**How the pull request body renders this failure.** `saffron/report/pr_body.py`
prints the message in its new-failures table, so the operator will stop seeing
the edit there. That is intended: the operator has the spec.

**Special-casing `witness` in `repair_prompt`.** `saffron/phases/**` is
forbidden, and `test_a_blocking_witness_failure_is_an_ordinary_blocking_failure`
explains why a `witness` failure needs no special case downstream. Fix it where
the message is built.

## Notes for the agent

**The criteria carry witnesses and no mutants.** The fix is an edit, but its new
spelling is yours, so no text exists yet that a mutant could pin honestly.
`witness` will report `skip` on this spec, and that is expected.

**Keep the claim in the message.** A failure's `identity()` is built from
`(gate, file, code, message)`. Two survivors that share a witness would collide
without the claim, and baseline subtraction would cancel the wrong one. Naming
the target file is your call; the claim is only about `find` and `replace`.

**Pick `find` and `replace` strings the test can honestly look for.** Assert
over the whole `result.model_dump_json()`, not one field. Choose strings that
are not substrings of the claim, the witness id or the file name. Otherwise the
assertion either passes for the wrong reason or cannot pass at all.

**Correct the stale paragraph** in
`test_a_blocking_witness_failure_is_an_ordinary_blocking_failure`'s docstring.
It says `witness` is in no `advisory_gates` set and blocks at every tier. Item
71 fixed that: `_advisory` makes it advisory below `elevated`.

**The witness must fail with the source reverted, not merely be missing at
base.** Reverted, the message quotes both strings, so an honest test fails.
Import nothing new at module scope, because a module-scope import of a name you
add turns the reverted run into a collection error, which `revert` reads as
`skip`.

**Write any helper as a `def`, not a `lambda`.** A `lambda` assigned to a name
needs a `# noqa: E731` to pass `lint`, and that suppression fails `integrity`
even inside `touches`.

**The `size` gate counts tests.** A `bug` gets 300 changed lines, tests
included. This is well inside that.
