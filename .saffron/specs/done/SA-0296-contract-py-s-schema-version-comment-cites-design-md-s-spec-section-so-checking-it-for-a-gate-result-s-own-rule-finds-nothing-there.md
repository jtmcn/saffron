---
id: SA-0296
title: contract.py's schema_version comment cites DESIGN.md's spec section, so checking it for a gate result's own rule finds nothing there
type: bug
priority: 3
estimated_lines: 18
estimate_measured: true
touches:
  - saffron/gates/contract.py
  - tests/test_contract.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/intake.py
  - saffron/repos/policy.py
  - saffron/gates/runner.py
  - saffron/gates/suite.py
  - saffron/gates/baseline.py
  - saffron/gates/core/**
  - saffron/cell/**
  - saffron/record/**
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/batch.py
  - saffron/reconcile.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/phases/**
  - saffron/agents/**
budget_usd: 10
max_attempts: 2
max_turns: 40
acceptance:
  - claim: >-
      `saffron/gates/contract.py`'s `SCHEMA_VERSIONS` comment cites DESIGN.md
      §5.4, the section stating a gate result's `schema_version` reads as 1
      when absent (DESIGN.md:910), and names no other section. The witness
      reads the comment line straight from the file on disk.
    witness: tests/test_contract.py::test_the_schema_version_comment_cites_the_gate_result_section
    wrong_versions:
      - The comment keeps citing §3.2, the section stating only the spec's own schema_version (DESIGN.md:248).
      - The comment cites both §3.2 and §5.4, so a reader still lands on the wrong section first.
      - The comment drops its section citation outright, so no reader is pointed anywhere.
      - The comment cites §5.4.1, the witness gate's own subsection, which never mentions schema_version.
---

## Context

Reviewer finding on `SA-0283` (saffron SA-0283, `9c27b82e`). Line numbers
below were read at this stack's head, `162e526a`.

`saffron/gates/contract.py:20` reads `# Versioned per module (DESIGN.md
§3.2). Only 1 exists today.`, directly above `SCHEMA_VERSIONS` on line 21.
That constant backs `GateResult`'s own `schema_version` field.

DESIGN.md's §3.2 heading sits at `DESIGN.md:188`, titled "Spec format". Its
only sentence naming `schema_version` is `DESIGN.md:248`: "A spec can
declare `schema_version`. One that declares none reads as version 1.
Intake refuses any other value... (`SA-0283`)." That sentence is about the
spec's own field. It names no gate result anywhere in its section.

DESIGN.md's §5.4 heading sits at `DESIGN.md:882`. `DESIGN.md:910` states
the rule the comment means to point at: "`schema_version` is optional too.
A gate result that declares none reads as version 1. The runner records
any other value as `error`, with a summary naming the versions it reads.
`policy.yaml` takes the same key under the same rule, refused at load
(`SA-0283`)."

`SA-0283` wrote the identical comment text into three files, verbatim:
`saffron/gates/contract.py:20`, `saffron/intake.py:50` and
`saffron/repos/policy.py:49`. `saffron/intake.py:50`'s citation is correct:
`Spec`'s own `schema_version` is exactly what `DESIGN.md:248` documents.
`saffron/repos/policy.py:49` carries the same wrong citation `GateResult`'s
does, since `policy.yaml`'s rule is also stated at `DESIGN.md:910`, in
§5.4, not in §3.2. That file sits outside this spec's `touches`, so its fix
is a separate matter (Out of scope).

## Problem

Change `saffron/gates/contract.py:20`'s comment to cite §5.4, the section
that actually states a gate result's `schema_version` rule, instead of
§3.2, which states only the spec's own rule. Add a witness that reads the
comment's own text from the file and fails on a build that still names
§3.2, names both sections, or names no section at all.

## Out of scope

- **`saffron/repos/policy.py:49`'s identical wrong citation.** It is not in
  this spec's `touches`, and `forbidden` names it so a cell does not drift
  there. A later spec can correct it the same way.
- **`saffron/intake.py:50`'s citation.** It already names the section that
  documents `Spec`'s own `schema_version`. Nothing about it changes here.
- **`DESIGN.md` itself.** Both §3.2 and §5.4 already state their own rules
  correctly. Only the code comment misreads which one applies to a gate
  result.
- **`SCHEMA_VERSIONS`'s value, the validator that reads it, or any test of
  `schema_version`'s runtime behaviour.** Nothing here changes what the
  code does. Only a comment's citation moves.

## Notes for the agent

**`saffron/gates/**` is in `elevate_on`,** so this task runs elevated
regardless of its declared `risk`, and `size` and `witness` both block. A
one-line comment edit plus one short test stays far under the ceiling.
Measured at 78 changed tokens with `size_gate`'s own counter, against the
`bug` ceiling of 1300.

**The fix is new text, not a changed behaviour**, so the one criterion
declares a witness and no mutant, and `witness` reports it `skip`. DESIGN.md §5.4.1's rule is that a
mutant pins text the existing code already determines, and the corrected
citation does not exist at base to pin against.

**Check the section number exactly, not by substring.** `"§5.4" in
comment` reads true for a comment citing §5.4.1 too, since one string
contains the other. Assert `"§5.4." not in comment` alongside it, so a
citation of the witness gate's own subsection still fails. Measured on a
prototype: a check asserting only `"§5.4" in comment` passed a build
citing §5.4.1.

**Read the comment from the file on disk, by its `"Versioned per
module"` text**, not by importing `SCHEMA_VERSIONS`. The constant's
value never changes, so a test reading it from the model would pass at
base too.

**At base the witness fails.** `saffron/gates/contract.py:20` cites §3.2
there, so `"§5.4" in comment` is false. Measured.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words.

