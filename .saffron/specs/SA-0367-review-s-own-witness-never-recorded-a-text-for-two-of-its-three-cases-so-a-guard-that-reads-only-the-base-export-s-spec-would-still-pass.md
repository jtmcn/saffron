---
id: SA-0367
title: 'Review''s own witness never recorded a text for two of its three cases, so a guard that reads only the base export''s spec would still pass'
type: bug
priority: 3
estimated_lines: 18
estimate_measured: true
touches:
  - tests/test_commit_review.py
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
  - saffron/**
  - tests/test_cli.py
  - tests/test_regate.py
  - tests/test_task.py
budget_usd: 12
max_attempts: 2
max_turns: 40
risk: standard
acceptance:
  - claim: >-
      `run_commit_review` attaches the task's row-pinned mutants
      (`saffron/commit_review.py:235-237`) to a spec `_spec_for_task`
      (`saffron/commit_review.py:231-233`) read as a recorded text. This
      holds for every one of the witness's three cases: a row pinning a
      commit, a row pinning none, and a recorded text that declares its
      own mutant inline. The row-pinning-a-commit and the
      row-pinning-none cases each record a plain spec text with no inline
      mutant. Each then makes `ledger.spec_text(task_id)` return a row
      (`saffron/commit_review.py:126-127`), so `_spec_for_task` parses
      that recorded text (`saffron/commit_review.py:128-129`) rather than
      falling back to `load_spec` on the base export's own file
      (`saffron/commit_review.py:134-143`).
    witness: tests/test_commit_review.py::test_review_hands_its_lenses_the_mutants_the_tasks_row_pins_reading_every_case_from_a_recorded_text
    wrong_versions:
      - Review attaches the mutants only to a spec loaded from the base export, so a recorded spec text reaches the lenses with none.
---

## Context

Backlog item `b-c5da95`'s own `SA-0363` spec declares one criterion for
`run_commit_review`, read at this stack's head
`80f41af06f318a54442c07aa978ce3419233310b`. Its claim ends "All three
read a recorded spec text"
(`.saffron/specs/SA-0363-regate-package-and-review-judge-a-spec-with-no-mutant-from-the-ref.md:119-120`).
That spec's own `wrong_versions` already names this exact wrong build,
word for word, as its second entry
(`.saffron/specs/SA-0363-regate-package-and-review-judge-a-spec-with-no-mutant-from-the-ref.md:124`).

The witness that claim names runs three cases inside one `_run` closure
(`tests/test_commit_review.py:1219-1273`). `_run` takes an optional
`record_text` argument. It calls `ledger.record_spec_text` only when the
caller supplies one (`tests/test_commit_review.py:1250-1257`). Case A, a
row pinning a commit whose mutant lies outside the diff, calls `_run`
with no `record_text` (`tests/test_commit_review.py:1294`). Case B, a
row pinning none, does the same (`tests/test_commit_review.py:1310`).
Only case C calls `_run` with `record_text=inline_text`
(`tests/test_commit_review.py:1329`). `inline_text` declares a mutant
inline (`tests/test_commit_review.py:1324-1328`).

So `ledger.spec_text(task_id)` returns `None` for cases A and B.
`_spec_for_task` then falls back to its file branch for both
(`saffron/commit_review.py:126-143`). It reads the spec at the base
export, never a recorded text, for either case
(`saffron/commit_review.py:134-143`). The witness's own docstring
already says this correctly, one sentence short of the spec's own
claim. It reads "Both read the base export's own spec file." at
`tests/test_commit_review.py:1225`.

That gap is not only textual. `attach_mutants_at` returns its `spec`
argument untouched whenever any criterion already declares a mutant
(`saffron/mutants.py:141-142`). It then reads nothing from the mirror.
Case C's recorded text always carries a mutant inline. So
`attach_mutants_at` never reaches its own `read_mutants`/`attach_mutants`
tail for a spec sourced from a recorded text
(`saffron/mutants.py:143-146`). `run_commit_review` calls
`_spec_for_task` and then `mutants.attach_mutants_at` unconditionally
(`saffron/commit_review.py:231-239`). Neither call branches on where the
spec came from.

A build could guard that second call behind "only for a spec read from
the base export's file". It would still pass all three cases as the
witness stood before this spec. Cases A and B never recorded a text.
Case C's recorded text never needed the guard, since it already carried
its own mutant. Applying exactly that guard to
`saffron/commit_review.py` and running the witness unmodified leaves it
green. The notes below give the measured check.

## Problem

In `tests/test_commit_review.py`:

1. Rename
   `test_review_hands_its_lenses_the_spec_with_the_mutants_the_tasks_row_pins`
   to
   `test_review_hands_its_lenses_the_mutants_the_tasks_row_pins_reading_every_case_from_a_recorded_text`
   (`tests/test_commit_review.py:1219`).
2. In its docstring, replace "Both read the base export's own spec
   file." with "All three read a recorded spec text."
   (`tests/test_commit_review.py:1225`).
3. Give case A's `_run` call a `record_text=_spec_text("recorded-a",
   witness)` argument (`tests/test_commit_review.py:1294`).
4. Give case B's `_run` call a `record_text=_spec_text("recorded-b",
   witness)` argument (`tests/test_commit_review.py:1310`).

Every existing assertion in the function stays as it is. Case A's
`handed.acceptance[0].mutant.file == "src/elsewhere.py"` assertion
stays, and so does case B's `handed.acceptance[0].mutant is None`.
Both now read the mutant `attach_mutants_at` attached to a spec
`parse_spec` built from a recorded text. Neither reads a spec
`load_spec` loaded from the base export's own file.

## Out of scope

- **Production code.** `saffron/commit_review.py` and
  `saffron/mutants.py` already attach the row's own pinned mutants to a
  spec however it was read. Neither branches on where the spec came
  from. Nothing there needs an edit.
- **`test_review_declines_a_mutants_commit_it_cannot_read_before_any_cell`.**
  Its own claim names no "recorded spec text" sentence. Nothing here
  touches it.
- **A fourth case, or a second criterion.** One criterion, one witness,
  already named by `SA-0363`.
- **`tests/test_regate.py` and `tests/test_task.py`.** Their own
  siblings of this witness pin or omit a mutants commit. Neither has a
  "recorded" case at all. This finding is specific to `review`'s own
  recorded-text branch.

## Notes for the agent

**No mutant.** The criterion above declares a witness and no `mutant`
key. Nothing in `saffron/` changes, so there is no edit at base to pin
one against. `witness` reports an honest `skip`.

**A rename, not a new witness.** `saffron queue`'s own
`test_no_witness_that_claims_a_change_exists_where_the_spec_was_written`
refuses a witness already defined before its own cell writes it
(`tests/test_queued_specs.py:310-321`). The function this edits already
exists in the working tree, so its witness is renamed rather than kept
as it stands. That check's `_authored_at` reads `SA-0363`'s own spec
file history (`tests/test_queued_specs.py:237-250`), never this tree's
current `tests/test_commit_review.py`. Renaming the function here
changes nothing that check reads for `SA-0363`'s own queued spec.

**Measured.** Guarding the existing `attach_mutants_at` call in
`saffron/commit_review.py` behind `if ledger.spec_text(task_id) is
None:` leaves the witness green as it stands at base. Adding this
spec's two `record_text` arguments, with that guard still in place,
fails case A on `handed.acceptance[0].mutant.file ==
"src/elsewhere.py"`. It raises `AttributeError` on a `None` mutant.
Reverting that guard, the renamed witness passes against the
unmodified source.

**Size.** Measured at 18 changed lines, 29 changed tokens by
`size_gate`'s own `_changed_lines`. Every changed path sits under this
repo's own declared test paths, so `size_gate` counts 0 of them
against the `bug` ceiling of 1300. No changed path sits in the risk
tier list, so this runs at standard risk.

**Format and lint.** `ruff format --check` and `ruff check` both pass
on the file as changed. Keep it that way.
