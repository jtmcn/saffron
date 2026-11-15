---
id: SA-0399
title: "`SPEC_ID_DIRS` spells `done` by hand, because `RETIRED_DIRNAME` sits in `scheduler.py`, which `worktree.py` cannot import"
type: refactor
priority: 3
estimated_lines: 115
estimate_measured: true
touches:
  - saffron/intake.py
  - saffron/scheduler.py
  - saffron/draft.py
  - saffron/follow_up.py
  - saffron/cli.py
  - saffron/cell/worktree.py
  - tests/test_intake.py
  - tests/test_cli.py
removes:
  - saffron/scheduler.py:RETIRED_DIRNAME
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
  - saffron/gates/**
  - saffron/phases/**
  - saffron/record/**
  - saffron/view/**
  - saffron/cell/session.py
  - saffron/cell/runtime.py
  - saffron/cell/runtimes/**
  - saffron/task.py
  - saffron/finish.py
  - saffron/mutants.py
  - saffron/projection.py
  - tests/test_worktree.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 22
max_attempts: 3
max_turns: 150
acceptance:
  - claim: >-
      `saffron/intake.py` is the one module under `saffron/` that spells the
      retired-spec directory. A string literal spells it when `done` is one
      of its parts split on `/`. A string standing alone as a statement is a
      docstring and does not count. The witness proves its detector on a
      sample first. It flags `"done"`, `'done'`, the path ".saffron/specs/done",
      the path "done/x.md" and the literal part of f"{a}/done". It leaves
      alone a docstring naming specs/done/, the message "outside done/, found",
      `"undone"` and `"done_dir"`. It then scans every `.py` file under
      `saffron/`. `saffron/intake.py` yields exactly one hit, the value
      `done`, on the line of its module-scope `RETIRED_DIRNAME` assignment.
      No other file yields any. `worktree.SPEC_ID_DIRS` still holds
      `.saffron/specs` and then `.saffron/specs/done`, and nothing else.
    witness: tests/test_intake.py::test_only_intake_spells_the_retired_directory_in_saffron_source
    wrong_versions:
      - "`SPEC_ID_DIRS` keeps its `.saffron/specs/done` literal beside a new import of the name."
      - "`SPEC_ID_DIRS` joins `.saffron/specs` and a bare `done` literal."
      - "`SPEC_ID_DIRS` appends the text `RETIRED_DIRNAME` rather than the value, so it no longer lists the retired directory."
      - "`scheduler.py` keeps its own `RETIRED_DIRNAME = \"done\"` beside the new one in `intake.py`."
      - "The name is defined in a new module, not in `saffron/intake.py`."
      - "`intake.RETIRED_DIRNAME` takes a new value, so the directory it names moves."
  - claim: >-
      Every Python file under `saffron/` and `tests/` that reads
      `RETIRED_DIRNAME` reads it through `saffron.intake`, either as
      `from saffron.intake import RETIRED_DIRNAME` or as an attribute of the
      `intake` module. The witness collects each import naming the name, each
      attribute read of it and each assignment to it. It proves that walk on a
      sample first. The sample imports the name from `saffron.intake` and from
      `saffron.scheduler`. It reads it as an attribute of `intake`, of
      `saffron.intake` and of `scheduler`, and assigns it once. The witness
      asserts the exact routes and the one assignment. It then walks every
      file. Exactly one file assigns it, and that file is
      `saffron/intake.py`. No import of the name comes from another module,
      and no attribute read of it goes through another module. Each of
      `saffron/scheduler.py`, `saffron/draft.py`, `saffron/follow_up.py`,
      `saffron/cli.py`, `saffron/cell/worktree.py` and `tests/test_cli.py`
      reads it through `saffron.intake`.
    witness: tests/test_intake.py::test_every_reader_of_the_retired_directory_name_imports_it_from_intake
    wrong_versions:
      - "`scheduler.py` imports the name from `intake` and `draft.py` still imports it from `saffron.scheduler`."
      - "`follow_up.py` still imports the name from `saffron.scheduler`."
      - "`cli.py` still reads `scheduler.RETIRED_DIRNAME`."
      - "`tests/test_cli.py` still imports the name from `saffron.scheduler`."
      - "`scheduler.py` binds `RETIRED_DIRNAME = intake.RETIRED_DIRNAME` at module scope."
      - "`worktree.py` builds `SPEC_ID_DIRS` without reading the name."
  - claim: >-
      The suite still hands `integrity` the ids of the spec files in
      `.saffron/specs/` and in its retired directory at HEAD, read through
      `SPEC_ID_DIRS`.
    witness: tests/test_worktree.py::test_the_suite_judges_cited_ids_against_the_spec_files_at_head
    preserves: true
    wrong_versions:
      - "`SPEC_ID_DIRS` lists `.saffron/specs` alone."
      - "`SPEC_ID_DIRS` appends the text `RETIRED_DIRNAME` rather than the value."
---

## Context

Backlog item **b-e447ea**, filed while reviewing #1214 (`SA-0393`). It cites `DESIGN.md` §5.4, the gate whose
listing this touches. Every line number below was read at `7219608c`.

**Where the name lives today**. `RETIRED_DIRNAME = "done"` is defined at
`saffron/scheduler.py:628`. `scheduler.py` reads it at `saffron/scheduler.py:618`,
`saffron/scheduler.py:652`, `saffron/scheduler.py:681`,
`saffron/scheduler.py:724`, `saffron/scheduler.py:773` and
`saffron/scheduler.py:1410`. Three more modules read it from
`scheduler`. `saffron/draft.py:26` imports it and reads it at `:68`.
`saffron/follow_up.py:38` imports it beside `Candidate` and reads it at
`:112`. `saffron/cli.py:758` reads `scheduler.RETIRED_DIRNAME` as an
attribute. One test reads it too. `tests/test_cli.py:57` imports it from
`saffron.scheduler`, and `:14555` reads it.

**The reader that spells it by hand**. `SA-0393` added
`SPEC_ID_DIRS = (".saffron/specs", ".saffron/specs/done")`
(`saffron/cell/worktree.py:461`). `spec_ids` builds one pathspec pair from
each entry (`saffron/cell/worktree.py:475-482`). `worktree.py` cannot import
`scheduler`. `saffron/scheduler.py:70` imports `saffron.cell.session`, and
`saffron/cell/session.py:26` imports `saffron.cell.worktree`. A rename of the
directory would move every reader of the name and miss this one.

**Why `intake.py` holds it**. `saffron/intake.py:9-25` imports the standard
library, `yaml` and `pydantic`, and no `saffron` module. So any module can
import it without a cycle. Each reader already does. `saffron/cell/worktree.py:21`
imports `Mutant` from it. `saffron/scheduler.py:72` imports four names from it.
`saffron/cli.py:55` imports three. `saffron/draft.py:24` and `saffron/follow_up.py:30` import the
module whole. `intake.py` is also where `discover_specs` lives
(`saffron/intake.py:557`), and its `retired` flag names the scan of that
directory (`:561`).

**Other spellings of the directory**. With
`uv run ast-grep run -p '"done"' -l python saffron`, the definition at
`saffron/scheduler.py:628` is the one bare `"done"` literal in `saffron/`. The
`saffron/cell/worktree.py:461` path is the one other literal with `done` as a path
part. Docstrings and comments name `done/` in prose throughout, such as
`saffron/scheduler.py:632`. Messages build it from the name, such as
`saffron/scheduler.py:618`. `saffron/mutants.py:327` writes
`outside done/` inside a message, where `done` is not a whole path part.

## Problem

1. Define `RETIRED_DIRNAME = "done"` at module scope in
   `saffron/intake.py`, with a one-line comment naming it as the one name
   for that directory.
2. Delete the definition at `saffron/scheduler.py:628`, and import the name
   from `saffron.intake` in `scheduler.py`'s existing import from that
   module.
3. Import it from `saffron.intake` in `draft.py`, `follow_up.py`, `cli.py`
   and `tests/test_cli.py`, in place of each read through `scheduler`. In
   `saffron/cli.py:758`, read the imported name rather than the attribute.
4. Build `SPEC_ID_DIRS`'s second entry from `.saffron/specs/` and the
   imported name in `saffron/cell/worktree.py`. Its value does not change.
5. Add the two witnesses to `tests/test_intake.py`.

No re-export stays in `scheduler.py`. `CLAUDE.md`'s "Import a name from the
module that defines it" rules out `__all__` and `import x as x`, so every
reader moves.

## Out of scope

- **Spellings outside `saffron/`**. `.saffron/gates/prose.py:47` and
  `.claude/skills/run-saffron-spec-loop/driver.py` (`:326`, `:2356`,
  `:2376`, `:3046`, `:3662`) spell `done` too. Both trees are forbidden here.
  Test fixtures spell it on purpose, as the directory a test builds.
- **Prose that names `done/`**. Docstrings, comments and messages keep
  their wording. The first criterion skips docstrings, and the AST holds no
  comments.
- **A structure rule**. An ast-grep rule under `.saffron/rules/` would hold
  the first criterion as a gate. `.saffron/**` is `protected`
  (`.saffron/policy.yaml:66`), so a cell cannot write one. The witnesses
  hold the property as tests instead.

## Notes for the agent

**This is a refactor.** No value and no behaviour changes. Criteria 1 and
2 are new witnesses. They pin where the name lives, and nothing at base
holds it there, so they declare no mutant and `witness` reports `skip` for
them. Criterion 3 is `preserves`, and its test exists at
`tests/test_worktree.py:1213`. Leave that test as it is.

**At base each new witness fails in its body**. Criterion 1's scan finds
no definition in `intake.py` and finds the two literals in `scheduler.py`
and `worktree.py`. Criterion 2's walk finds the assignment in
`scheduler.py` and the reads through it. Import `worktree` inside the
first witness, not at module scope, and import no name the change adds at
module scope. A module-scope import of a name `intake` lacks at base is a
collection error, which `revert` reads as `skip`.

**Criterion 1's witness**. Find the repo root from `__file__`. Parse each
file with `ast`. A docstring is any `ast.Expr` statement whose value is a
`str` constant. Skip those constants, then test every other `str`
`ast.Constant`. An f-string's literal parts are such constants. Assert the
sample's flagged lines as an exact list, so a detector that flags too much
or too little fails. Read intake's hit through the same scan as the rest,
and check that its line is the line of the `RETIRED_DIRNAME` assignment.
That positive case is what makes "no other file yields any" mean something.

**Criterion 2's witness**. Walk `saffron/` and `tests/` with `ast`. Record
each `ast.ImportFrom` whose names include `RETIRED_DIRNAME`, with its
module. Record each `ast.Attribute` whose `attr` is the name, with its
value rendered as a dotted name. Record each `ast.Assign` to a plain name
`RETIRED_DIRNAME`. Use one function for the sample and for each file.
The sample then shows the walk sees an attribute read and an import from
another module. Accept `saffron.intake` and `intake` as routes. Assert
the six readers as a subset of the files read through them, so a later
reader does not break the test. The six named readers are the positive
case for "no read goes through another module".

**Size**. A prototype measured 457 changed tokens. 38 of them lie outside
the test paths, against the `refactor` ceiling of 4200. The two witnesses
are 134 added lines of `tests/test_intake.py`.

**The `prose` gate** counts each new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence
over 25 words. A docstring stays within ten lines.
