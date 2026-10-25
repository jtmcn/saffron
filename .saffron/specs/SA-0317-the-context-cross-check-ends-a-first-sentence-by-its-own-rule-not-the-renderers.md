---
id: SA-0317
title: "The CONTEXT.md cross-check ends a first sentence by its own rule, not the renderer's, so it reads past a blank line"
type: bug
priority: 3
depends_on: []
estimated_lines: 44
estimate_measured: true
touches:
  - tests/ontology/test_vocabulary_agrees_with_context.py
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
  - saffron/**
  - docs/**
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - tests/conftest.py
  - tests/ontology/conftest.py
  - tests/ontology/ontology_paths.py
  - tests/ontology/test_spans.py
  - tests/ontology/test_render.py
budget_usd: 24
max_attempts: 3
max_turns: 140
acceptance:
  - claim: >-
      `context_enumeration` takes its span from `ontology.spans.definition_sentence`
      and keeps no first-sentence rule of its own. So each of three entries
      makes both raise `ValueError`. The first has no trailing period and ends
      the text. The second has no period before its blank line, and a later
      paragraph holds a backticked name and a period. The third defines its
      term twice, each with a period. With the test module's
      `definition_sentence` name replaced by a function that raises
      `LookupError`, the reader raises `LookupError`.
    witness: tests/ontology/test_vocabulary_agrees_with_context.py::test_the_reader_refuses_each_definition_the_renderer_refuses
    wrong_versions:
      - The base's reader kept, which splits at the first period anywhere after the marker, so the first entry returns its members.
      - A reader that raises only when no period follows the marker anywhere, so the second entry returns three tokens.
      - A reader with its own blank-line bound that takes the first occurrence of the marker, so the third entry returns one member.
      - A reader that counts the marker but splits with no blank-line bound, so the second entry returns three tokens.
      - A copy of `definition_sentence` under another name in the test module, so the replaced name is never called.
  - claim: >-
      Over the live `CONTEXT.md`, `Risk tier` still reads as exactly
      `standard` and `elevated`, and `elevate_on`, named later in the same
      entry, is still left out.
    witness: tests/ontology/test_vocabulary_agrees_with_context.py::test_the_parser_would_notice_a_changed_set
    preserves: true
    wrong_versions:
      - A reader that returns every backticked token up to the entry's blank line, so `elevate_on` joins the set.
  - claim: >-
      Over the live `CONTEXT.md`, `Status`, a term `ontology.spans.SETS` does
      not name, still reads as `pass`, `fail`, `skip` and `error`.
    witness: tests/ontology/test_vocabulary_agrees_with_context.py::test_the_gate_statuses_are_earl_outcomes_rather_than_saffron_terms
    preserves: true
    wrong_versions:
      - A reader that looks its term up in `SETS` first, so `Status` raises `KeyError`.
---

## Context

Backlog item **b-545741**, found in the third review of the parked
decision record that b-2227b0 tracks. Every line number below was read at `b2acd68f`.

**The renderer's rule.** `definition_sentence` in `ontology/spans.py:36`
returns the span of a term's first sentence. It raises `ValueError` unless
`**term**` occurs exactly once (`ontology/spans.py:38-40`). It bounds the search at
the entry's first blank line (`ontology/spans.py:44-46`). Its comment says why: unbounded,
a definition with no trailing period matched a period paragraphs away
(`ontology/spans.py:42-43`). It raises again when no period followed by
whitespace or the end falls before that bound (`ontology/spans.py:47-49`).
`render_context` rewrites within that span (`ontology/render.py:111`).

**The test's rule.** `context_enumeration` in
`tests/ontology/test_vocabulary_agrees_with_context.py:37` starts after the
first `**term**` it finds (`:52`). It splits the rest of the file at the
first period followed by whitespace or the end (`:53`). Nothing bounds it at a
blank line, and nothing checks the marker is unique. So the cross-check reads
each closed set by a different rule from the one the render writes it by. An
entry with no trailing period makes the renderer raise, while the reader takes
the whole rest of the file and passes.

**The readers.** Three tests call `context_enumeration`, all in the same
file. The parametrized cross-check reads the eleven terms in `CLOSED_SETS`
(`tests/ontology/test_vocabulary_agrees_with_context.py:71-72`).
`test_the_parser_would_notice_a_changed_set` reads `Risk tier` (`:85-86`).
`test_the_gate_statuses_are_earl_outcomes_rather_than_saffron_terms` reads
`Status`, which `ontology.spans.SETS` does not name (`:101`). Each of those
twelve terms occurs exactly once in `CONTEXT.md` at `b2acd68f`, and each entry
has a period before its blank line. A prototype of this change passed all
fifteen tests in the file.

## Problem

Make `context_enumeration` read its span from `definition_sentence`, so the
cross-check and the renderer share one rule. Change nothing outside the one
test file.

1. **The reader.** Import `definition_sentence` from `ontology.spans` under
   that name, and call it through the module's own global. Take the span it
   returns. Collect members from that span with
   `render.MEMBER_TOKEN`, as today. Keep reading the module's `CONTEXT` at
   call time, because the witness repoints it. Keep no split, search or
   bound of your own. Drop `import re` once nothing uses it.
2. **The docstring.** Say the span comes from the renderer's own function.
   Keep the paragraph on the token pattern.
3. **The witness.** One plain test, not parametrized. Its three entries and
   its replaced name are in criterion 1.

## Out of scope

- **`ontology/spans.py` and `ontology/render.py`.** Both are `gate_config`
  (`.saffron/policy.yaml:124`), and neither needs an edit.
- **Holding other `factory:` terms to `CONTEXT.md` entries.** That is
  b-c16c6c, and a sibling spec edits this file for it.
- **The comment in `ontology/render.py:89`** that names the span
  `context_enumeration` reads. It becomes true, so it stays.

## Notes for the agent

**New, not an edit.** The reader's body is replaced, and the spelling of its
replacement is yours. So every criterion declares a witness and no mutant,
and `witness` reports `skip`. The whole diff sits under `tests/**`, which is
`integrity.test_paths` (`.saffron/policy.yaml:70`). So `revert` skips with
"the diff has no source outside the repo's declared test paths"
(`saffron/gates/core/revert.py:175-180`). Criterion 1's witness is absent at
base, so `criteria` reads it red there. Criteria 2 and 3 name tests that exist.

**Criterion 1's witness.** For each of the three entries, write it to a file
under `tmp_path` and monkeypatch this module's `CONTEXT` to that file. Assert
that `context_enumeration("Risk tier")` raises `ValueError`. Then assert that
`definition_sentence` raises `ValueError` over the same text. Build each entry
from `**Risk tier**` and the backticked names `standard` and `elevated`. The
second entry's later paragraph also names `elevate_on`. Last, monkeypatch this
module's `definition_sentence` to a function that raises `LookupError`. Assert
that `context_enumeration("Risk tier")` raises `LookupError`.

**Measured on a prototype, 2026-10-24.** The reader and the witness above
were written against `b2acd68f`, and all fifteen tests in the file passed.
The new test failed under each of criterion 1's five wrong versions, and the
other fourteen passed under each. Criterion 2's wrong version failed its
witness and six of the parametrized cases. Criterion 3's failed its witness
alone. `ruff check`, `ruff format` and `ty check` passed on the file.

**The other readers stay green.** The parametrized cross-check drives the
eleven `CLOSED_SETS` terms. Criteria 2 and 3 drive `Risk tier` and `Status`.

**The `prose` gate** reads every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence over
25 words.

**Size.** The touched path is not in `elevate_on`, so `size` is advisory. The
prototype counted 175 changed tokens by `size_gate`, against the `bug`
ceiling of 1300. `estimated_lines` is those tokens over four.
