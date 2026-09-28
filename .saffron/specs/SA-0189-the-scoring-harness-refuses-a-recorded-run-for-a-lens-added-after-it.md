---
id: SA-0189
title: The scoring harness would refuse every fixture's recorded run the moment REVIEW gains a lens
type: feature
priority: 1
depends_on: [SA-0188]
estimated_lines: 75
touches:
  - harness/lens_scoring.py
  - harness/corpus.py
  - tests/test_lens_scoring.py
  - tests/test_corpus.py
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
  - records/**
  - saffron/**
budget_usd: 24
max_attempts: 3
max_turns: 140
acceptance:
  - claim: >-
      `calibrate` scores a fixture's recorded run against the lenses that run
      carried, so a run recorded before a lens existed still reproduces its
      answer. A run with an errored lens is still refused, and a run whose
      findings no longer match the recorded answer still fails calibration.
      `graded_per_run` scores each run slice against the lens set its caller
      names, and against today's lenses when the caller names none.
    witness: tests/test_lens_scoring.py::test_calibrate_scores_a_recorded_run_against_the_lenses_it_ran
  - claim: >-
      The baseline, `CLAUDE.md` and spread passes each re-derive their
      published numbers from their own three-lens runs when every harness
      default names a fourth lens.
    witness: tests/test_corpus.py::test_the_published_passes_re_derive_under_a_fourth_lens
  - claim: >-
      Every shipped fixture still reproduces its own recorded answer.
    witness: tests/test_corpus.py::test_the_predicate_reproduces_every_fixture_s_recorded_answer
    preserves: true
  - claim: >-
      The published baseline pass still re-derives its headline from its own
      three-lens runs.
    witness: tests/test_corpus.py::test_the_baseline_pass_s_published_aggregate_is_re_derivable
    preserves: true
---

## Context

Backlog item **b-abeb74**, found in the spec loop's run 20 on 2026-09-28.
It cites `DESIGN.md` §5.5. This spec is the first of three. `SA-0191` then
declares a fourth REVIEW lens, `conventions`, and `SA-0192` gives it its
edges. ADR 8 records the decision. Every line number below was read at
`a4299786`, and the code is unchanged at `40dc7f8f`.

**What the harness reads.** `score_run` and `score_pass` default `expect`
to `tuple(LENSES)` (`harness/lens_scoring.py:359`, `:392`). A run missing
a lens in `expect` is refused with `LensErrored` (`:379-384`). `calibrate`
calls `score_run` with that default over a fixture's recorded run
(`:447`). Every shipped fixture recorded three lenses. So the moment
`LENSES` gains a fourth, every fixture refuses its own recorded answer.
The corpus driver calls `calibrate_corpus` before every pass
(`harness/corpus.py:44-51`), so no pass could start.

`graded_per_run` takes no `expect`. It scores each run slice through
`score_corpus` with the default (`harness/corpus.py:111-126`).
`score_corpus` already takes one (`:82-99`).

A pass recorded under an older lens set already names the set it ran, as
the docstring at `harness/lens_scoring.py:371-373` asks.
`PASS_2026_09_07_LENSES` does it for the first pass
(`tests/test_lens_scoring.py:520-524`). Four tests re-derive a published
number and name none.

- `test_the_calibration_case_reproduces_the_run_it_was_built_from`
  (`tests/test_lens_scoring.py:115-120`).
- `test_the_baseline_pass_s_published_aggregate_is_re_derivable`
  (`tests/test_corpus.py:979-991`).
- `test_the_claude_md_pass_s_per_run_totals_are_re_derivable`
  (`tests/test_corpus.py:1167-1183`).
- `test_the_spread_pass_s_per_run_totals_are_re_derivable`
  (`tests/test_corpus.py:1141-1160`).

The spread test fails silently once `LENSES` grows. Every slice then comes
back `None`, the totals string is empty, and its membership assert passes
on an empty string (`tests/test_corpus.py:1158-1159`).

A default argument is evaluated once, when its `def` runs. So patching
`review.LENSES` in a test moves none of these defaults. Patching a
function's own `__defaults__` does.

A stub fourth lens at `a4299786` failed 21 harness tests this way: 18 in
`tests/test_corpus.py` and 3 in `tests/test_lens_scoring.py`.

## Problem

Make the harness ready for a lens added after a run was recorded.

1. `calibrate` passes `score_run` the set of lens names its fixture's
   recorded run carries. The errored-lens refusal stays.
2. `graded_per_run` gains an `expect` keyword, defaulting to
   `tuple(LENSES)`, and passes it to `score_corpus`.
3. The four tests listed above name the three lenses their pass ran.
   Declare that tuple once in `tests/test_corpus.py`, and reuse
   `PASS_2026_09_07_LENSES` in `tests/test_lens_scoring.py`. The spread
   test also asserts its totals exactly, as `1/12 · 2/12 · 3/12`.

`score_run`, `score_pass` and `score_corpus` keep today's default, so a
live run still owes every lens `LENSES` names.

## Out of scope

- **The fourth lens.** `SA-0191` declares it. `LENSES` is unchanged here.
- **The corpus driver** under `docs/evidence/scripts/`. Its calls to
  `score_corpus` and `graded_per_run` take the default `expect`
  (`docs/evidence/scripts/2026-09-08-lens-corpus.py:526`, `:539`). So once
  `SA-0191` lands, re-scoring a three-lens pass with `--score-only` drops
  every fixture. A new pass runs four lenses and is unaffected. The file is
  under `docs/**`, which a cell cannot write, and nothing re-scores an old
  pass today.
- **New fixtures.** The fixture built from run 20's findings is built by
  hand once the lens exists.

## Notes for the agent

**Criteria 1 and 2 declare a witness and no mutant.** The spec does not
force the spelling of either edit. The `witness` gate reports `skip` for
both. Criteria 3 and 4 are `preserves`, and name tests that pass now.

Criterion 2 is what makes item 3 a gate. Its pinned tuple equals today's
`tuple(LENSES)`, so without it a skipped item 3 would pass every test here.
It would surface only in `SA-0191`, which cannot edit `tests/test_corpus.py`.

**The witness.** Build a fixture under `tmp_path` with `_one_defect`
(`tests/test_lens_scoring.py:60-86`). Its location is `PR_BODY` (`:90`).
Table its rows.

1. A recorded run holding `correctness` alone, no findings, no error.
   `calibrate` returns `None`.
2. The same run with `error` set to `"boom"`. `calibrate` raises
   `LensErrored`, and its message is exactly `"SA-9999: correctness: boom"`.
3. `harness.corpus.graded_per_run` over that one fixture and one run
   holding `correctness` alone, with `expect=("correctness",)`. The result
   is one slice. Assert its `declared` and `graded` exactly.
4. The same call with no `expect`. The result is exactly `[None]`.
5. A recorded run holding `correctness` alone, with one finding that sees
   the declared defect. Build it with `_finding`
   (`tests/test_lens_scoring.py:29-47`), anchored, at a
   line inside `PR_BODY`'s range, with a claim holding the phrase
   `neutraliz`. `calibrate` raises `CalibrationError`, since the fixture
   declares `recorded_seen = 0`.

At the tree base rows 1 and 5 raise `LensErrored`, and row 3 is a
`TypeError`. Row 5 kills a `calibrate` that returns early on an absent
lens.

**Criterion 2's witness.** Keep it small. Set `__defaults__` to a
four-lens tuple on `lens_scoring.score_run`, `lens_scoring.score_pass`,
`corpus.score_corpus` and `corpus.graded_per_run`, through `monkeypatch`.
Then call the three corpus tests from item 3 in turn, as plain functions.
At the tree base the baseline test raises `LensErrored`, since every
fixture drops.

**Wrong versions this witness must kill.**

- A `calibrate` that catches the refusal and returns.
- A `calibrate` that drops the errored-lens check along with the lens set.
- A `graded_per_run` that takes `expect` and never passes it on.
- A `graded_per_run` whose default is no lens at all.
- A `calibrate` that returns as soon as a lens is absent.
- An item 3 left undone, or done for two of the three corpus tests.

**Commit as each witness passes.** Criterion 2 turns green once item 3
lands.

**The prose gate** counts every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense, a hedge or a
sentence over 25 words.

**Size.** A prototype of the first witness and the edits measured about
180 tokens under `size_gate`'s counter. The second witness, row 5 and the
spread pin add about 120. `estimated_lines` is that over four, with no overrun
added. `harness/**` is in `elevate_on`, so `size` blocks here.
