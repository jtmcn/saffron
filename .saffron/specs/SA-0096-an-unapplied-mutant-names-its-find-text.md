---
id: SA-0096
title: a mutant that does not apply spells its find text into the reason, and the witness gate carries that reason to the lenses
type: bug
priority: 2
depends_on: []
touches:
  - saffron/mutation.py
  - saffron/cell/worktree.py
  - tests/test_mutation.py
  - tests/test_worktree.py
  - tests/test_witness_gate.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/cell/session.py
  - saffron/cell/runtime.py
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/report/**
  - saffron/task.py
  - saffron/cli.py
  - saffron/batch.py
budget_usd: 14
max_turns: 90
acceptance:
  - claim: >-
      When the host applier cannot apply a mutant because its find text
      matches nowhere, or matches more than once, the reason it returns names
      the mutant's file and which of the two cases it hit. The reason carries
      no part of the mutant's find text or its replace text. Today both
      reasons end with the find text in full.
    witness: tests/test_mutation.py::test_a_mutant_that_does_not_apply_names_neither_half_of_its_edit
  - claim: >-
      The same holds for the cell's applier: the reason it yields for a find
      text that matches nowhere, or more than once, names the file and the
      case and carries no part of either half of the edit. Today it spells the
      find text the same way the host applier does.
    witness: tests/test_worktree.py::test_a_mutant_that_does_not_apply_in_a_cell_names_neither_half_of_its_edit
  - claim: >-
      With one criterion whose mutant its witness survives and one whose
      mutant does not apply, neither the whole serialized `witness` result
      nor the gate table REVIEW's lenses are shown contains any part of
      either mutant's find or replace text. Today the unapplied mutant's find
      text reaches the result's summary, and the lens table repeats every
      summary.
    witness: tests/test_witness_gate.py::test_an_unapplied_mutant_reaches_neither_the_result_nor_the_lens_table
    mutant:
      file: saffron/gates/core/witness.py
      find: _named(criterion, reason))
      replace: _named(criterion, reason + mutant.find))
  - claim: >-
      A find text that matches twice still applies nothing on the host, leaves
      the file untouched, and names the file in its reason, as it does today.
    witness: tests/test_mutation.py::test_a_find_that_matches_twice_does_not_apply
    preserves: true
  - claim: >-
      The cell's applier still applies nothing for a find text that matches
      nowhere or twice, and still says which of the two it was, as it does
      today.
    witness: tests/test_worktree.py::test_a_find_that_does_not_match_once_applies_nothing
    preserves: true
  - claim: >-
      A mutant its witness survives still fails `witness` with a result that
      names the claim and carries neither half of the edit, as `SA-0078` made
      it.
    witness: tests/test_witness_gate.py::test_a_surviving_mutant_names_its_claim_and_not_its_edit
    preserves: true
---

## Context

Backlog item **114**, found reviewing `SA-0078` (PR #243) on 2026-09-14.

A mutant is withheld from the implementer on purpose (`CONTEXT.md`, **Mutant**;
`DESIGN.md` §5.4.1). An implementer that knows the edit it will be judged by can
write a test that kills that one edit and nothing else. `SA-0078` took the edit
out of a *surviving* mutant's failure message. It left the other path alone: a
mutant that does not apply at all.

Both appliers put the find text into their refusal:

- `saffron/mutation.py:148` returns `f"{mutant.file}: find text not found: {mutant.find!r}"`,
  and the matches-more-than-once reason at `:150-157` ends with the same
  `{mutant.find!r}` (`:155`).
- `saffron/cell/worktree.py:562` yields the not-found reason with `{mutant.find!r}`,
  and the matches-more-than-once reason at `:564-568` ends with it (`:567`).

`saffron/gates/core/witness.py:165` records that reason as unproven, and
`:266-270` joins every unproven reason into the result's `summary`.
`review.gate_summary` (`saffron/phases/review.py:150-157`) writes each gate's
`summary` into the table REVIEW's lenses are shown, and a lens may quote that
table back in REBUT. Item 114 reproduced it against #243's head:

```
- witness: fail (pytest 8.3.2) — 1 of 2 witness(es) survived their own mutant — 1 mutant(s) not proven: t.py::test_b (a.py: find text not found: 'min(d, CAP_SECRET)')
```

A mutant that does not apply is usually one aimed at code the implementer has
not written yet, which makes it the one most worth withholding.

## Problem

The reason a mutant could not apply discloses the mutant's edit. From there it
reaches the gate table REVIEW's lenses read, and in REBUT a lens can hand it
back to the implementer.

## Out of scope

**Where the operator reads the find text.** The operator has the spec, which
holds it, so the reason does not need to carry it anywhere.

**The other refusals.** A path outside the tree, a path not tracked at `HEAD`,
a file that is not a regular file, a file with uncommitted work, and a file
that could not be read all name the file and never the edit. Leave them as
they are.

**`gate_summary` and the lens prompt.** `saffron/phases/**` is forbidden.
Fix it where the reason is built, in the two appliers.

**`saffron/gates/core/witness.py`.** The third criterion's mutant is
applied there, which needs no `touches` entry, and `saffron/gates/**` is
forbidden, so `scope` refuses an edit to it.

## Notes for the agent

**Criteria 1 and 2 carry witnesses and no mutants.** The fix is an edit, but
the new wording of each reason is yours, so no text exists yet that a mutant
could pin honestly. Criterion 3's mutant targets text this change does not
touch. `witness` will report `skip` for the first two, and that is expected.

**Cover both cases in each applier.** A fix that removes the text from the
not-found reason and leaves it in the matches-more-than-once reason is the
likeliest wrong answer. Each witness should drive both cases and check both
reasons.

**"No part of" means no fragment either.** A reason that keeps the first ten
characters of the find text still discloses the edit, so the witness must fail
on that, and so must one that keeps the last ten. Start *and* end the find
and replace text with a distinctive fragment, such as
`find="QRVT_FIND = QRVT_"` and `replace="QRVT_REPLACE = QRVT_"`, and assert
that `QRVT_` is absent as well as each whole string. A token only in the
middle does not work: a prefix or suffix that stops short of it passes. Make sure the fragment is not also part of
the file name, the witness id or a claim, or the assertion cannot pass at all.

**Two existing assertions state the old behaviour, and you must invert them.**
`tests/test_mutation.py:94` asserts the find text is in the host reason, under a
comment saying the reason names "the file and the text", and `:252` asserts the
same through `host_mutator`. Keep both tests and their names, since `census`
compares test names. Keep the file-name assertion, and assert that the find
text is absent. Correct the `apply_mutant` docstring too: `saffron/mutation.py:118-121`
says a refusal names "the file and the text".

**The reason must still say which case it was.** The two preserves witnesses
check for "matches 2 times" and "not found" in the cell's reasons. Keep both
categories distinct, name the file, and keep the match count in the
matches-more-than-once case. A reason that says only "could not apply" loses
the operator's one clue about what to fix in the spec.

**Criterion 3 drives the gate end to end.** Use `host_mutator` on a real tree,
as `test_a_surviving_mutant_names_its_claim_and_not_its_edit` does, with two
criteria: one whose witness passes with its mutant applied, and one whose find
text is absent from the file. Assert over `result.model_dump_json()` and over
`gate_summary([result])` (import it from `saffron.phases.review` inside the
test body), for both halves of both mutants.

**Import anything new inside the test body**, not at module scope. A
module-scope import of a name the change adds turns `revert`'s reverted run
into a collection error, which it reads as `skip`.

**The cell applier's tests run on the host.** `tests/test_worktree.py` drives
`source_mutated` through `_repo_with_a_file` and a monkeypatched `_git`. The
preserves witness at `tests/test_worktree.py:1088` shows the shape.
