---
id: SA-0191
title: No REVIEW lens reads a hunk against the repo's conventions, so the Standards seat finds a defect on every pull request
type: feature
priority: 1
depends_on: [SA-0189]
estimated_lines: 320
touches:
  - saffron/phases/review.py
  - saffron/agents/prompts/review-conventions.md
  - tests/test_review.py
  - tests/test_rebut.py
  - tests/test_lens_scoring.py
  - tests/test_context.py
  - tests/test_session.py
  - tests/test_events.py
  - tests/fixtures/watch-golden.txt
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
  - harness/**
  - saffron/phases/rebut.py
  - saffron/end_review.py
  - saffron/qualify.py
  - saffron/ledger.py
  - saffron/cell/**
  - saffron/report/**
  - saffron/agents/context.py
  - saffron/agents/prompts/review-correctness.md
  - saffron/agents/prompts/review-contract.md
  - saffron/agents/prompts/review-adequacy.md
  - saffron/agents/prompts/end-review-standards.md
  - saffron/agents/prompts/end-review-spec.md
  - saffron/agents/prompts/rebut-verdict.md
  - tests/test_end_review.py
  - tests/test_qualify.py
  - tests/test_corpus.py
budget_usd: 24
max_attempts: 3
max_turns: 180
acceptance:
  - claim: >-
      `review.LENSES` declares exactly four lenses, correctness, contract,
      adequacy and conventions, in that order, each mapped to its own prompt
      file. `run_review` starts one fresh session per lens in that order, and
      the fourth session's system prompt is the conventions prompt built with
      the spec, the diff, the gate results and the standing instructions.
    witness: tests/test_review.py::test_the_declared_lenses_are_the_four_that_run
    mutant:
      file: saffron/phases/review.py
      find: '"conventions": "review-conventions.md",'
      replace: ''
  - claim: >-
      No in-cell lens shares a name with an end-review lens. The in-cell set is
      exactly correctness, contract, adequacy and conventions, the end-review
      set is exactly spec and standards, and the two share no member.
    witness: tests/test_review.py::test_no_in_cell_lens_shares_a_name_with_an_end_review_lens
    mutant:
      file: saffron/phases/review.py
      find: '"conventions": "review-conventions.md",'
      replace: '"standards": "review-conventions.md",'
  - claim: >-
      The conventions prompt asks four questions of every hunk against the
      standing instructions the host read at the base commit, never a
      worktree file. It names a comment or docstring that contradicts its
      code, a constant restated rather than imported, and a citation that
      does not say what the text claims. It leaves format, lint, types,
      structure and sentence form to their gates.
    witness: tests/test_review.py::test_the_conventions_prompt_asks_its_four_questions_against_the_base_standards
  - claim: >-
      A blocker the conventions lens files gets a verdict at REBUT from a
      fresh session of its own, shown only its own blocker, after the
      correctness lens's verdict session. `saffron/phases/rebut.py` is
      unchanged.
    witness: tests/test_rebut.py::test_a_conventions_blocker_is_verdicted_by_a_session_of_its_own
    mutant:
      file: saffron/phases/review.py
      find: '"conventions": "review-conventions.md",'
      replace: ''
  - claim: >-
      A live scoring run with correctness, contract and adequacy and no
      conventions result is refused, and the refusal names conventions.
    witness: tests/test_lens_scoring.py::test_a_live_run_without_a_conventions_result_is_refused_by_name
    mutant:
      file: saffron/phases/review.py
      find: '"conventions": "review-conventions.md",'
      replace: ''
  - claim: >-
      An end review's Standards finding is still kept out of the in-cell
      findings a layer's end review is shown.
    witness: tests/test_end_review.py::test_a_layers_fields_come_from_its_own_row_and_its_own_task
    preserves: true
  - claim: >-
      The adequacy prompt is still the only one that claims the test-adequacy
      remit.
    witness: tests/test_review.py::test_exactly_one_prompt_claims_the_test_adequacy_remit
    preserves: true
---

## Context

Backlog item **b-abeb74**, found in the spec loop's run 20 on 2026-09-28.
It cites `DESIGN.md` §5.5. ADR 8 records the decision to add this lens, and
amends ADR 4's three-lens sentence. This is the second of three specs.
`SA-0189` readies the scoring harness. `SA-0192` gives the lens its edges and
its prompt for a repo with no `CLAUDE.md`. Every line number below was read
at `a4299786`, and the code is unchanged at `5438a23c`. `SA-0190` and
`SA-0188` edit `tests/test_session.py`, `tests/test_review.py`,
`tests/test_rebut.py` and `saffron/phases/review.py` before this spec runs.
Find a test by its name, not its line.

The Standards seat read every pull request of run 20 by hand, after REVIEW
passed it. It found three classes of defect no lens owns.

- A comment or docstring that contradicts its code. #565's comment on the
  spec writer's timeout called 3600 seconds twice the idle bound of 300
  seconds. #566's docstrings called a `witness` concern lone, three times,
  where the code revises on any.
- A constant or helper restated rather than imported. #559's `spec_text`
  and `spec_texts` repeated the query `Ledger.record_key` already runs.
  #560's `WALL_CAP_S = 3600.0` restated the library's hour.
- A citation to a section that does not say what the text claims. #562's
  two comments cited `DESIGN.md` §4.2.1 for resolver rules it does not state.

**How a lens runs today.** `LENSES` maps each lens to its prompt file
(`saffron/phases/review.py:39-43`). `lens_prompt` reads that file and fills
it through `context.build_system_prompt` (`:179-199`). `run_review` loops
over `LENSES` in order (`saffron/phases/review.py:330`). Each lens session
is capped at what is left of the budget, floored at `REVIEW_FLOOR_USD` of
2.0 and never decremented between lenses (`saffron/cell/session.py:70-79`,
`:141-143`).

**REBUT needs no change.** It runs one verdict session per lens in
`review.LENSES` that filed a blocker, in `LENSES` order
(`saffron/phases/rebut.py:603-606`). Every verdict session reads the same
lens-agnostic prompt file, `VERDICT_PROMPT_FILE` (`:30`, `:270`). A
conventions blocker therefore gets its verdict once the lens is declared.

**Why the key is not `standards`.** The end review declares `spec` and
`standards` (`saffron/end_review.py:35-38`). It writes its findings into
the same `findings` rows as REVIEW's, under the layer's own task
(`:355-356`). That table carries no column saying which review filed a row
(`saffron/ledger.py:175-187`). Two readers tell the two apart by whether
the row's lens is in `review.LENSES`: `end_review._known_block`
(`saffron/end_review.py:79`) and `qualify._in_cell_concerns`
(`saffron/qualify.py:102`). A shared name would feed every end-review
Standards concern back in as an in-cell one, qualified twice.

**The prose gate reads prompts.** `prose` scans `saffron/agents/prompts/`
(`.saffron/gates/prose.py:43-44`), and a new file starts at zero hits. Its
hedge rule refuses the word the other three prompts' framing sentence uses
(`:86`).

## Problem

REVIEW runs three lenses, and none reads a hunk against the repo's
conventions or checks a comment against the code beside it. The Standards
seat found such a defect on every pull request of run 20.

Declare a fourth in-cell lens, `conventions`.

1. **The table.** `LENSES` gains a fourth entry, `conventions`, whose
   prompt file is `review-conventions.md`, after `adequacy`.
2. **The prompt.** Write `saffron/agents/prompts/review-conventions.md` in
   the shape of `review-correctness.md`. It carries the same slots:
   `{vocabulary}`, `{standing_instructions}`, `{gates}`, `{diff}` and
   `{spec}`. Its framing sentence is under **The framing** in the notes.
   Its section headed `## Your remit` holds the text under **The remit**,
   word for word, and the next heading follows it. The rest follows
   `review-correctness.md`: severity in three levels, then the `<output>`
   block with `file`, `line`, `severity` and `claim`. It also carries the
   plain-language paragraph for the pull request's findings table.
3. **The tests that pin three lenses.** Update them, as the notes list.

## Out of scope

- **The edges.** `SA-0192` gives the conventions prompt its Not-yours
  list and the other three prompts their conventions bullet.
- **A repo with no `CLAUDE.md`.** `SA-0192` gives the conventions prompt
  its block for a repo that declares none.
- **REBUT, the end review and qualification.** Each reads `review.LENSES`
  already. The end review's own Standards lens stays as ADR 7 sets it.
- **The protected text.** It is edited by hand in this spec's own pull
  request: `DESIGN.md` §5.5 and §5.5.1, `CONTEXT.md`'s **Lens** and
  **Scoring run** entries, and ADR 4.
- **The measured pass.** It is built by hand once the lens exists, as the
  notes' measurement plan says.

## Notes for the agent

**Between this spec and `SA-0192`** the conventions lens runs for one cell
with no Not-yours list. A repo with no `CLAUDE.md` then gets an empty
standing-instructions section in it. Both are accepted, because the three
specs land in one stack.

**Which criteria edit code, and which are new.** Criteria 1, 2, 4 and 5
rest on the new `LENSES` entry. Each declares a mutant on it. Criterion 3
is a new file, so it declares a witness and no mutant, and the `witness`
gate reports `skip` for it. Criteria 6 and 7 are `preserves`, and name
tests that pass now. Criterion 6 holds the reason the key is
`conventions`.

**Commit as each witness passes.** Five new witnesses, then the test
updates below. One commit per green witness keeps a repair turn small.

### The framing

The conventions prompt's framing sentence:

```text
Find the reason this change must not be merged.
```

### The remit

Criterion 3's witness reads the prompt text between the heading line
`## Your remit` and the next line opening `## `. It joins that text on
whitespace and compares it for equality with this text joined the same
way. `SA-0192` inserts a heading after this section, so the witness holds
there too.

```text
Yours is each hunk read against the standing instructions below, and against
the code and text it describes. Judge against the standing instructions in
this prompt, never a file in the worktree. The host read them at this task's
base commit, before the implementer could touch them.

Ask four questions of every hunk:

- **Vocabulary.** Does each term carry the meaning the standing instructions
  give it, and avoid every term they rule against?
- **Invariants and conventions.** Does the hunk hold to each rule the
  standing instructions state?
- **One source.** Is a type, constant or helper the repository already
  defines imported, rather than restated? A constant restated is yours even
  when the two values agree today.
- **Said versus done.** Does each comment, docstring and citation say what
  the code or the cited text says? A comment or docstring that contradicts
  its code is yours. So is a citation to a section or line that does not say
  what the text claims.

The fourth question needs no standing instructions. Format, lint, types,
structure and sentence form each have a gate. Leave what they judge alone.
```

The witness also asserts the framing sentence over the whole prompt
joined on whitespace.

### The other witnesses

- **Criterion 1.** Assert `review.LENSES` equals the four-entry dict, and
  its key list equals the four names in order. Drive `run_review` through
  `_review(record=...)` in `tests/test_review.py`. Its `_agent` answers a
  clean review for every unscripted lens. Assert the four lens names in
  order, four recorded calls, and the fourth call's `system_prompt` equal
  to `review.lens_prompt("conventions", ...)` over the same inputs. It
  replaces `test_the_declared_lenses_are_the_three_that_run`. Move
  `test_the_blast_radius_lens_is_not_declared` to the four-name set.
- **Criterion 2.** Assert both sets exactly, then their intersection empty.
- **Criterion 4.** Drive `_run` in `tests/test_rebut.py` with two blockers
  from `_blocker`: a conventions one first, then a correctness one. Script
  `_rebuttals`, then `_verdicts` for finding 2, then for finding 1. Assert
  the verdict lenses equal `["correctness", "conventions"]` and each lens's
  finding numbers exactly. Assert the conventions session's `system_prompt`
  equals `rebut.verdict_prompt("conventions", ...)` given only finding 1,
  with the arguments `run_rebut` passes at this spec's base.
- **Criterion 5.** Call `lens_scoring.score_run` over the `sa0062` fixture
  with three clean `LensReview`s, one per lens but conventions. Assert it
  raises `LensErrored` with exactly this message.

```text
SA-0062: no result for conventions, so this run says nothing about the defects those lenses own
```

**Wrong versions these witnesses must kill.**

- A fourth lens keyed `standards`, or any end-review name.
- A conventions prompt with any of the four questions left out, or one
  telling the lens to read `CLAUDE.md` from the worktree.
- A fourth lens that runs before adequacy.
- A conventions blocker filed under another lens's name.

### The tests that pin three lenses

A stub fourth lens broke 54 tests at `a4299786`. `SA-0189` takes the 21
harness tests. Change each of the rest in its own terms, and copy no
helper.

- **`tests/test_session.py`, 25 tests.** Eleven route through
  `_through_rebut` (`:3503-3517`) and `_adequacy_turns` (`:3626-3637`). Add
  one clean conventions turn after adequacy in each. Give `_adequacy_turns`
  a `conventions=` keyword beside `correctness=` and `contract=`. The other
  fourteen script their turns inline. One is
  `test_what_the_task_spent_is_the_sum_of_the_turns_it_ran`, whose phase
  list gains one more REVIEW row. Five are criterion-probe tests,
  `test_each_claim_is_asked_of_its_own_session_that_is_never_shown_a_witness`
  among them. Name the `_EMPTY` constant (`:3623`) for each added turn.
- **`tests/test_events.py`, 3 tests, and `tests/fixtures/watch-golden.txt`.**
  The golden file gains one `REVIEW: conventions:` line after adequacy's.
  The spend moves from $0.50 to $0.60. The table of joined lines
  (`tests/test_events.py:1824`) reads the same lines.
- **`tests/test_rebut.py`.**
  `test_each_verdict_session_asks_for_the_schema_and_records_its_structured_output`
  takes four blockers, four fixes and four verdict sessions.
- **`tests/test_review.py`.** Table the framing sentence by lens in
  `test_each_lens_prompt_carries_the_framing_that_makes_it_a_critic`. The
  three existing lenses keep theirs, and conventions takes the one above.
- **`tests/test_context.py`.**
  `test_prose_bound_for_the_pr_body_is_asked_for_in_plain_language` gains
  a row for `review-conventions.md`, `claim` and `findings`.

**The prose gate** counts every new comment, docstring and prompt line.
Write none with an em dash, a semicolon, a contraction, the perfect tense, a
hedge or a sentence over 25 words. The prompt measured at zero hits in the
prototype.

**Size.** A prototype of this prompt measured 499 tokens under
`size_gate`'s counter, and its witnesses about 520. The test updates add
about 260. `estimated_lines` is about 1280 over four, with no overrun added.

**Queued neighbours.** `SA-0187` and `SA-0190` also edit
`saffron/phases/review.py`. Keep this spec's edit to `LENSES`.

### The measurement plan, for the operator

This is built by hand once the lens exists, outside every cell. Each defect
below is recovered from the review commit on its merged pull request. Line
numbers are at the cell's squashed head, and each line is one that diff
adds. Every `owner` is `conventions`. Every `min_severity` is `concern`,
and all five are unconfirmed against the seats' own grading.

| Spec, pull request | Range | Locations | `must_mention` |
|---|---|---|---|
| `SA-0182`, #559 | `145f087c..1a3796e8` | `saffron/ledger.py` [1492, 1496], [1506, 1510] | `record_key` |
| `SA-0184`, #560 | `2a20e23a..c4ac878e` | `saffron/cell/session.py` [68, 68] | `3600`, `hour` |
| `SA-0186`, #562 | `2a20e23a..dd7fd989` | `saffron/task.py` [86, 87], [259, 260] | `4.2.1` |
| `SA-0160`, #565 | `89a244a6..b9cbb5cc` | `saffron/spec_review.py` [539, 541] | `idle bound`, `twice` |
| `SA-0164`, #566 | `6fc23834..a67ec01b` | `saffron/spec_review.py` [256, 258], `tests/test_batch.py` [3588, 3589], `tests/test_spec_review.py` [395, 396] | ``lone `concern` ``, `lone concern` |

A bare `lone` phrase matches "alone", so the last row names the phrase
whole. Each fixture's recorded findings come from its cell's
`findings.json`, which ran three lenses. `SA-0189` makes `calibrate`
accept those.

The five fixtures collide with one pin. The baseline pass's test asserts
it scored 8 fixtures (`tests/test_corpus.py:1023`). The corpus loader reads
every directory under `docs/evidence/fixtures/`. Keep the five in a directory of
their own, or move that pin in the same commit.

The pull request body reports each defect's seen and graded counts over n
runs, before with three lenses and after with four. It also reports runs
dropped and the conventions session's cost per run.

**Cost, for the pull request body.** Run 20's eight cells ran 24 lens
sessions, each $0.35 to $2.73, a mean of $0.88. A fourth lens adds about
that to every reviewed diff, plus one verdict session when it files a
blocker. Its cap is a fourth remainder, never decremented, so REVIEW's
worst-case overrun grows from three remainders to four.
