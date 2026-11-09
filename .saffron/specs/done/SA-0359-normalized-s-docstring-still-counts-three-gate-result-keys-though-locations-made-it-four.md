---
id: SA-0359
title: "`_normalized`'s docstring still counts three `gate_result` keys, though `locations` made it four"
type: bug
priority: 3
estimated_lines: 10
estimate_measured: true
touches:
  - saffron/record/migrate.py
  - tests/test_record_migrate.py
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
  - saffron/gates/**
  - saffron/cell/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/ledger.py
  - saffron/intake.py
  - saffron/scheduler.py
  - saffron/batch.py
  - saffron/reconcile.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/record/contract.py
  - saffron/record/refs.py
  - saffron/record/memory.py
  - saffron/mutants.py
  - tests/mutation.py
  - tests/test_batch.py
  - tests/test_cli.py
  - tests/test_constant_mutants.py
  - tests/test_context.py
  - tests/test_contract.py
  - tests/test_events.py
  - tests/test_follow_up.py
  - tests/test_gates.py
  - tests/test_mutants.py
  - tests/test_rebut.py
  - tests/test_revert.py
  - tests/test_session.py
  - tests/test_spec_review.py
  - tests/test_suite.py
  - tests/test_witness_gate.py
  - tests/test_worktree.py
budget_usd: 10
max_attempts: 2
max_turns: 40
acceptance:
  - claim: >-
      `_normalized`'s own docstring (`saffron/record/migrate.py:94-97`) names
      the exact count of `_GATE_RESULT_SET_ASIDE`'s own members, four, not
      the three it named before `locations` joined that set. The witness
      reads the docstring straight from the live import, and reads
      `_GATE_RESULT_SET_ASIDE`'s own length, never a hardcoded four.
    witness: tests/test_record_migrate.py::test_the_normalized_docstring_counts_every_set_aside_gate_result_key
    wrong_versions:
      - The docstring keeps saying "the three `gate_result` keys above", unaware `_GATE_RESULT_SET_ASIDE` now holds four.
      - The docstring says "the four `gate_result` keys above" and also keeps "the three `gate_result` keys above" elsewhere, so both counts are named at once.
      - The docstring drops its count word, reading "the `gate_result` keys above" with no number at all.
      - The docstring says "the five `gate_result` keys above", overcounting past `_GATE_RESULT_SET_ASIDE`'s own four members.
---

## Context

Reviewer finding on `SA-0342` (saffron SA-0342, `6266888ab43efbadbb68b8be96fbff00a01b4c79`).
Line numbers below were read at this stack's head, `13ddf0298406e705fc61f49c9c2c12ce00a575e8`.

`SA-0342` added `locations` to `_GATE_RESULT_SET_ASIDE`
(`saffron/record/migrate.py:85-87`), so the set now holds four members,
`schema_version`, `collected`, `uncollected` and `locations`, instead of
three. Its own notes asked the agent to "update the module docstring and
the comments that count the set-aside keys
(`saffron/record/migrate.py:20-24`, `:82-89`)".

Two of the three spots were updated. The module docstring now reads "It
also sets aside a `gate_result`'s `schema_version`, `collected`,
`uncollected` and `locations`" (`saffron/record/migrate.py:22-24`). The
comment above `_GATE_RESULT_SET_ASIDE` now reads "The four `gate_result`
keys the ledger's own fact never carries" (`saffron/record/migrate.py:83`).

The third spot was missed. `_normalized`'s own docstring still reads "its
`at`, the three `gate_result` keys above on a `gate_result`, and the two
`rebuttal` keys above on a `rebuttal`" (`saffron/record/migrate.py:95-97`).
A reader who trusts that count, not the frozenset two lines above it,
would read `_normalized` as setting aside only three `gate_result` keys.
That is one fewer than it sets aside.

## Problem

Change `saffron/record/migrate.py:96`'s `"the three"` to `"the four"`.
That brings `_normalized`'s own docstring in line with
`_GATE_RESULT_SET_ASIDE`'s own four members, the same count the module
docstring and the frozenset's comment already state. Add a witness that
reads the docstring from the live import and the frozenset's own length.
It fails on a build that still names three, names both three and four,
names no count, or overcounts past four.

## Out of scope

- **`saffron/record/migrate.py:20-24`'s module docstring and `:83`'s
  frozenset comment.** Both already name four, fixed by `SA-0342` itself.
  Nothing about either changes here.
- **`_GATE_RESULT_SET_ASIDE`'s own members or its frozenset literal.**
  Nothing here changes what the code does. Only a docstring's count moves.
- **The `rebuttal` count beside it on the same docstring line.**
  `_REBUTTAL_SET_ASIDE` still holds two members, `answer` and `error`
  (`saffron/record/migrate.py:90-91`). The docstring's own `"the two"`
  already agrees with that.

## Notes for the agent

**The fix is new text, not a changed behaviour**, so the one criterion
declares a witness and no mutant, and `witness` reports it `skip`.
`DESIGN.md` §5.4.1's rule is that a mutant pins text the existing code
already determines. The corrected count does not exist at base to pin
against.

**Read the docstring from the live import, and the count from
`_GATE_RESULT_SET_ASIDE`'s own length**, never a hardcoded four standing
alone. That way, a later change to the frozenset's own membership still
has something concrete to check the docstring against. The check is
never a number copied once and then stale again.

**At base the witness fails.** `saffron/record/migrate.py:96` reads "the
three `gate_result` keys above" there, so the `not in` assertion on that
exact text fails first. Measured.

**Size.** Measured at 55 changed tokens with `size_gate`'s own
`_token_counts`, against the `bug` ceiling of 1300. `saffron/record/**`
is not in `elevate_on`, so this task runs at standard risk. `size` blocks
only on the ceiling above, never a tier it does not reach.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense, or a
sentence over 25 words.
