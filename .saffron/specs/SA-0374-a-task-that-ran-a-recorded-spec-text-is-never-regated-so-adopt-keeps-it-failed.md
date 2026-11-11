---
id: SA-0374
title: A task that ran a recorded spec text is never re-gated, so `saffron adopt` keeps it `EXHAUSTED` or `MERGE_FAILED`
type: bug
priority: 2
estimated_lines: 19
estimate_measured: true
touches:
  - saffron/regate.py
  - tests/test_regate.py
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
  - harness/**
  - images/**
  - records/**
  - hooks/**
  - saffron/cli.py
  - saffron/task.py
  - saffron/ledger.py
  - saffron/intake.py
  - saffron/mutants.py
  - saffron/batch.py
  - saffron/follow_up.py
  - saffron/draft.py
  - saffron/scheduler.py
  - saffron/events.py
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/record/**
  - saffron/repos/**
  - tests/test_cli.py
  - tests/test_adopt_stack_layer.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 30
max_attempts: 3
max_turns: 160
acceptance:
  - claim: >-
      `saffron regate` judges a task that holds `spec_texts` rows against
      the parse of its latest row, the row `ledger.spec_text` returns. It
      attaches the mutants the task's own row pins, exits 0 on a green
      head, and records the re-gate. The witness drives one task for each
      of `SPEC_TEXT_ORIGINS`, `revision`, `follow_up` and `draft`. Each
      task holds two rows whose titles differ. It checks the title and the
      attached mutant `reverify` receives, and the recorded head and count.
      A task with no row is still judged against its file at `base_sha`,
      and the same witness checks that file's title reaches `reverify`.
    witness: tests/test_regate.py::test_regate_judges_a_task_that_ran_a_recorded_spec_text_against_its_latest_row
    wrong_versions:
      - The decline kept, so every task with a row still exits 1.
      - The decline removed but the spec still read from the file at `base_sha`, so the mutants name a witness that file lacks and the task declines.
      - The first row read instead of the latest, so `reverify` receives the title `first revision`.
      - Mutants attached only on the file path, so the recorded text's criterion reaches `reverify` with no mutant.
      - A row read only for origin `revision`, so the `follow_up` task falls back to the file and declines on its hash.
      - The recorded-text path taken for every task, so the task with no row raises on a `None` row.
  - claim: >-
      A latest row that does not parse declines with exit 1 and a line
      holding `task <id>'s text <n> does not parse`, where `<n>` is the
      row's own number. No image is built, no probe or `reverify` runs,
      and no re-gate is recorded, though the task's file at `base_sha`
      hashes to its `spec_sha`. The witness drives a task whose only row
      does not parse, and a task whose row 1 parses and row 2 does not. It
      then records a parseable row 2 on the first task and sees that task
      re-gated green through the same spies.
    witness: tests/test_regate.py::test_regate_declines_a_latest_recorded_text_that_does_not_parse_and_names_its_row
    wrong_versions:
      - A fallback to the file at `base_sha` when the row does not parse, so the first task regates green.
      - The newest row that parses used instead, so the second task regates green on row 1.
      - The text parsed after the image build and probe, so the build spy holds a call.
      - A reason that names no row number, such as `task 1's recorded text does not parse`.
      - The `SpecError` left uncaught, so the command exits 2.
  - claim: >-
      `saffron adopt` moves an `EXHAUSTED` task and a `MERGE_FAILED` task
      that each hold a recorded spec text to `READY_FOR_REVIEW`. Its
      re-gate calls `regate.run_regate` with no fake and records a
      green re-gate on the adopted head. The text declares a witness whose
      pinned mutant lies outside the diff, so `revert` sets it aside. The
      file at `base_sha` declares no witness. The same witness adopts a
      task holding no text on a fixture of that shape and sees it stay
      `EXHAUSTED`.
    witness: tests/test_regate.py::test_adopt_moves_a_task_that_ran_a_recorded_spec_text_to_ready_for_review
    wrong_versions:
      - The decline kept, so adopt prints `its re-gate declined` and keeps each state.
      - The spec read from the file at `base_sha`, so the pinned mutants file names a witness it lacks and the re-gate declines.
      - Mutants attached only on the file path, so `revert` judges the text's witness and the re-gate records a new failure.
---

## Context

Backlog item **b-619b7d**, the open half its Record lines of 2026-11-09
and 2026-11-10 name. It cites `DESIGN.md` §4.2.1. Every line number below
was read at `65f65032`.

**The incident, twice.** In the spec loop's run 56, `saffron adopt SA-0353
1099` printed "regate: task 396 ran a recorded spec text, not a file at
base_sha" and kept the task `EXHAUSTED`. The batch had rewritten the
spec's moved citations, so the text the cell read is in no file. In the
spec loop's run 60, `saffron adopt SA-0364 1136` declined the same way, on
a `MERGE_FAILED` task.

**What regate does now.** `_task_and_run` declines any task that holds a
`spec_texts` row, before any `gh` call (`saffron/regate.py:55-58`).
Otherwise `run_regate` exports `.saffron/` at the task's `base_sha` and
reads the spec from the file whose bytes hash to the task's `spec_sha`
(`saffron/regate.py:152-155`, `saffron/regate.py:86-96`). It attaches the
mutants the task's row pins, and declines on a `SpecError` there
(`saffron/regate.py:156-161`). A `_Declined` prints `regate:` and its
reason and returns 1 before any image build or probe
(`saffron/regate.py:164-172`).

**Who records a text.** A stack batch records a `revision` row when it
rewrites moved citations, and one per spec-writer revision
(`saffron/batch.py:754-760`, `saffron/batch.py:928-934`). Both land before
the layer's cell runs (`saffron/batch.py:936-937`). A follow-up records a
`follow_up` row when it is minted, before its pass
(`saffron/follow_up.py:477-483`). `saffron draft` records a `draft` row,
and a `revision` row on a revised draft (`saffron/draft.py:238-240`,
`saffron/draft.py:272-278`). `Ledger.spec_text` returns the row with the
highest `n` (`saffron/ledger.py:2076-2087`). `SPEC_TEXT_ORIGINS` names
the three origins (`saffron/ledger.py:84`).

**Which text the cell ran.** `run_task` calls `_recorded_spec_text` for a
task it is handed (`saffron/task.py:764-771`). That reads the latest row
(`saffron/task.py:652`) and parses it with `parse_spec(row["text"])`
(`saffron/task.py:664`). It also checks the row's hash, the id,
`depends_on`, the ceilings, `touches` and the policy against a handed
spec. `run_task` then attaches the mutants the task's row pins
(`saffron/task.py:775-782`). `ready_task` reads a text the same way,
through `_spec_for_task` (`saffron/task.py:1133-1136`,
`saffron/task.py:1314`).

**What adopt does with the result.** `_adopt` re-gates any adoptable task
but a `READY_FOR_REVIEW` one, through `regate.run_regate`
(`saffron/cli.py:3227-3235`). It moves the task to `READY_FOR_REVIEW` only
when the re-gate returns 0 and records no new failure on the adopted head
(`saffron/cli.py:3236-3247`). A decline records nothing, so the task keeps
its state (`saffron/cli.py:3249-3250`).

## Problem

A task whose cell ran a recorded spec text cannot be re-gated, so no route
moves it to `READY_FOR_REVIEW`. Judge it against that text instead.

In `saffron/regate.py`, remove the decline at lines 55-58. Where
`run_regate` reads the spec at line 155, read `ledger.spec_text(task_id)`
first. With no row, keep `_spec_at_base`. With a row, parse its `text` with
`intake.parse_spec`. A `SpecError` there becomes a `_Declined` whose reason
holds `task <id>'s text <n> does not parse:` and the error's own words on
one line. That is the shape `_recorded_spec_text` gives its own refusal
(`saffron/task.py:657-658`, `saffron/task.py:668`). The mutants attachment
and everything after it stay as they are, so they apply to either spec.

`test_regate_refuses_each_task_it_cannot_judge_before_any_cell_and_exits_one`
asserts the old reason for its recorded-text case
(`tests/test_regate.py:943`). That case's text, "a revised spec", does not
parse. Change its expected reason to `task <id>'s text 1 does not parse`.
Write the three tests the criteria name in `tests/test_regate.py`.

## Out of scope

- **`saffron adopt` itself.** It reads the re-gate's result as it does now.
  `SA-0373` changes what adopt does after a green re-gate, and the two
  touch no file in common.
- **Gate 0's other checks.** Regate does not re-run the hash, id,
  `depends_on`, ceiling, `touches` or policy checks `_recorded_spec_text`
  makes. The cell passed them before it ran. Only a row that does not parse
  declines.
- **`saffron/task.py`.** `_recorded_spec_text` needs a handed spec, and a
  follow-up task has no file at `base_sha` to hand it. So regate parses the
  row itself and imports nothing from `saffron/task.py`.
- **Past tasks.** `SA-0353`'s and `SA-0364`'s tasks stay as they are until
  an operator adopts them again.

## Notes for the agent

**Every criterion is new code.** The read of the row and its decline do
not exist yet, so their spelling is not forced. None declares a mutant,
and `witness` will report `skip` for each. The wrong versions under each
criterion say what its witness must still catch.

**Why the latest row is the one the cell ran.** Every writer above records
its row before the cell runs on the task. A later batch that re-runs the
task records any new row before that cell too. So the latest row is the
text the newest cell read, which is the cell that produced the head.

**Seed each task so the wrong version reaches its branch.**

- For criterion 1, give the `revision` task the file's own `spec_sha`, so
  a version reading the file passes `_spec_at_base`. Pin a mutants commit
  naming only the text's witness, and give the file no witness. The
  `follow_up` and `draft` tasks carry the hash of their first text, as a
  minted follow-up does, so no file matches it. Use a path that
  `_FOLLOW_UP_PATH` accepts for those two (`saffron/ledger.py:88`).
- For criterion 2, give both tasks the file's own `spec_sha`, so a
  fallback to the file would regate green. The unparseable text
  "a revised spec" raises `SpecError` with no frontmatter.
- For criterion 3, build each task on its own fixture under its own
  subdirectory, since adopt reads the spec's newest task. Create the
  mirror before adopt, as
  `test_adopt_moves_a_task_whose_witness_its_cell_set_aside_to_ready_for_review`
  does. Use `_fake_reverify_through_revert_gate`, so a missing mutant shows
  as a new failure.

**Fixtures.** `_build_fixture`, `_seed_task`, `_seeding_ledger`,
`_mutants_commit`, `_mutants_yaml`, `_set_mutants_ref`, `_gh_pr_view`,
`_fake_reverify` and `_install_probe_fakes` already sit in
`tests/test_regate.py`. A mutants file that names a witness no criterion
declares makes `attach_mutants_at` raise, and regate then declines. So pin
one only on a task whose text declares its witness.

**At base each witness fails in its body.** Regate there declines every
task with a row. Import nothing the change adds at module scope.

**The `prose` gate** counts each new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words.

**Size.** A prototype measured 74 changed tokens with `size_gate`, against
the `bug` ceiling of 1300, with 871 more under the test paths. It held the
regate change, the one edited reason and the three witnesses. Every test in
`tests/test_regate.py` passed on it.
