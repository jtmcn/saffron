---
id: SA-0200
title: Retiring a spec turns this repo's gate suite red, so no stack batch finish can push here
type: bug
priority: 2
depends_on: []
estimated_lines: 121
estimate_measured: true
touches:
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
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
  - tests/conftest.py
  - docs/**
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/**
budget_usd: 14
max_attempts: 3
max_turns: 60
acceptance:
  - claim: >-
      Each of the three per-spec tests in `tests/test_queued_specs.py` has a
      case for every queued spec and for every file in `done/` other than
      `README.md`, each named by its bare filename. Over a scratch spec
      directory, moving a queued spec into `done/` keeps every case name, and
      a file in `done/` that does not parse still has its case. In the live
      tree, each of the three tests collects a case for every `SA-*.md` file
      in `.saffron/specs/done/`.
    witness: tests/test_queued_specs.py::test_retiring_a_spec_keeps_every_case_id
    wrong_versions:
      - A case list built from the top level alone, as the base builds it, so a moved spec loses its case.
      - A case list that reads `done/` through `discover_specs`, so a retired file that does not parse, such as `SA-0063`, has no case.
      - A new case list that one of the three decorators does not use, so that test still parametrizes over the queued specs only.
      - A retired case named `done/<filename>`, so the move still renames the case.
  - claim: >-
      A case for a file in `done/` passes in each of the three per-spec tests
      without checking anything, even when its text breaks every rule those
      tests check. A case for a queued spec with the same text still fails
      each of the three.
    witness: tests/test_queued_specs.py::test_a_retired_case_checks_nothing_and_a_queued_one_is_still_checked
    wrong_versions:
      - A retired case that runs the checks, so a retired spec that breaks a rule fails its case.
      - An early return taken for every case, so a queued spec that breaks a rule passes.
      - An early return in two of the three tests, so the third fails or crashes on a retired case.
  - claim: >-
      The queue smoke test reads its specs from the module's `REAL_SPECS`
      when it runs. It builds its scratch directory with only the measured
      ids' files at the top level, each taken from the top level or from
      `done/`, and the rest of `done/` beneath. It leaves its source
      directory unchanged. Over a copy of the live specs
      in which every top-level spec is moved into `done/` and a new spec with
      no parent is written at the top, the smoke test still passes. Over a
      specs directory holding none of the measured ids, it fails with an
      `AssertionError`.
    witness: tests/test_scheduler.py::test_the_measured_queue_holds_when_its_specs_retire_and_a_new_one_lands
    wrong_versions:
      - The base's whole-directory copy kept, so the new top-level spec joins the candidates.
      - A measured file taken from the top level only, so a retired one is missing.
      - A measured file copied out of `done/` but left there too, so it reads as retired and its children become candidates.
      - Every top-level file copied as well as the measured ones, so the new spec joins the candidates.
      - The smoke test reading the live directory through its own path rather than `REAL_SPECS`, so the second half never fails.
      - A helper that moves a measured file out of the source's `done/`, so the source loses it.
      - A helper that moves a measured file out of the source's top level, so the source loses it.
---

## Context

Backlog item **b-b0cd68**, filed from the spec reviews of `b-792ab2`'s last
build specs. It cites `DESIGN.md` §5.4. Every line number below was read at
`04222f69`.

**What a finishing commit does.** `commit_finish` writes the latest text of
every layer and every unrun task (`saffron/finish.py:114-145`). It
then moves each layer's file into the retired directory under the same filename
(`saffron/finish.py:156-159`). A follow-up spec it writes lands at the top
of `.saffron/specs/`.

**Why that turns this repo red.** `tests/test_queued_specs.py:28` builds
`QUEUED` with `discover_specs`, which globs the top level alone
(`saffron/intake.py:388-417`). Three tests parametrize over it, each case named
by the spec's filename (`tests/test_queued_specs.py:66`, `:102`, `:178`).
A retirement drops three collected names, and `census` fails a removed name
(`saffron/gates/core/census.py:72-80`). Its own comment says no override
exists (`saffron/gates/core/census.py:35-39`).

The queue smoke test copies the whole live directory
(`tests/test_scheduler.py:2818-2820`) and pins both lists
(`tests/test_scheduler.py:2829-2830`). A retirement turns a refused child
into a candidate. A new top-level spec adds an id. Either way it fails.

**What stays as it is.** The non-recursive glob check holds because
`done/` stays one directory down (`tests/test_scheduler.py:2831-2833`).
`REAL_SPECS` already names the live directory
(`tests/test_scheduler.py:62`), and `_write` already writes a minimal valid
spec (`tests/test_scheduler.py:39`).

## Problem

A stack batch's finishing commit cannot pass this repo's gate suite, so it
pushes nothing. Make the two tests read the spec directory in a way a
retirement and a new spec leave alone. Change nothing outside the two test
files.

1. **The per-spec cases.** Build one case list from every queued spec, as
   today, and every file in `done/` except `README.md`. A retired file is
   not parsed. Parametrize all three tests over it with the same
   `ids=lambda d: d.path.name`, so each case keeps the bare filename.
2. **A retired case.** Each of the three tests returns at once on a case
   from `done/`, before it reads the spec. A queued case runs exactly as
   today.
3. **The smoke test.** Factor the scratch arrangement into a helper that
   takes a source directory, a destination and the measured ids. It copies
   the source's `done/` first. Then each measured id's one file goes to the
   top level, moved out of the destination's `done/` or copied from the top.
   A measured id with no file fails an `assert` naming it. The smoke test passes
   `REAL_SPECS` to it, read at call time.
4. **The measured ids.** Name them in one set literal in the smoke test,
   above the helper call, as `measured = {"SA-0197", ...}` with the ids
   sorted. The spec loop's driver finds the set by that name. It holds
   exactly the ids its two assert lines name at your base. Keep those two lines byte for byte, so the spec
   loop's driver still drafts them.
5. **The docstring.** Replace the docstring's topmost `Re-measured`
   paragraph with one of no more lines. It names this change and both
   lists. Leave every other paragraph alone.

## Out of scope

- **A finishing commit that edits a measured spec's `depends_on`.** That
  still moves the split. The smoke test then fails, and a person re-measures it.
- **The spec loop's driver and `docs/agents/issue-tracker.md`.** Both
  change by hand in the pull request stacked on this spec's. `.claude/**`
  is out of a cell's reach (b-e471bd). Once the smoke test binds
  `measured`, `bookkeeping` drafts that line too. For a retirement it
  drafts no change to either list.
- **`census`, `integrity` and `finish.py`.** The fix is test-side only.

## Notes for the agent

**New, not an edit.** The case list, the helper and the three witnesses are
new code, so every criterion declares a witness and no mutant. `witness`
reports `skip`. The whole diff sits under `tests/**`, which is
`integrity.test_paths` (`.saffron/policy.yaml:71`). So `revert` skips with
"the diff has no source outside the repo's declared test paths"
(`saffron/gates/core/revert.py:166-174`). Each witness is absent at base,
so `criteria` reads it red there.

**Why a retired case returns and does not skip.** `integrity` scans every
added line for the skip call's text (`.saffron/policy.yaml:70-88`). Its
`touches` exemption binds the gate-config check alone
(`saffron/gates/core/integrity.py:14-18`, `:245-248`). The gate is never
advisory (`saffron/gates/suite.py:190`, `:220-228`). Any alias of the skip
fails `structure` (`.saffron/rules/skip-is-spelled-in-full.yml`). So write
no skip and no skip marker anywhere in the diff. A one-line comment on the
first early return says the spec is no longer queued.

**Census on your own cell.** Every name the base collects from both files
must still be collected at head. Keep all three test names, the smoke
test's name and the filename ids. The prototype's collection at head was a
superset of the base's.

**Criterion 1's witness.** Write two minimal specs at a scratch top level,
a file reading `no frontmatter here` in its `done/`, and a `done/README.md`. Take the case
names, move one spec into `done/`, and take them again. Assert both lists
hold the same three names, and neither names `README.md`. Then request the module's `collected` fixture.
For each of the three tests and every `SA-*.md` in `SPECS / "done"`, assert
`tests/test_queued_specs.py::<test>[<filename>]` is in it.

**Criterion 2's witness.** One scratch spec breaks all three rules. It
declares `depends_on: [SA-9999]`, a `preserves` witness naming
`tests/nowhere.py::test_absent`, and a second witness naming
`tests/test_queued_specs.py::test_every_queued_spec_parses`. Monkeypatch
the module's `_authored_at` to return `None`, so the third test reads the
working tree. Call each test function directly with that spec's queued
case, and an empty `frozenset` for `collected`. Each raises
`AssertionError`. Move the file into `done/`, rebuild the cases, and call
each again with the retired case. Each returns `None`.

**Criterion 3's witness.** Copy `REAL_SPECS` to a scratch source. Move each
top-level `SA-*.md` there into its `done/`, and `_write` a new spec
`SA-9999` at the top. Monkeypatch the module's `REAL_SPECS` to that source.
Call the smoke test function with a fresh scratch directory and the
`ledger` fixture, and it returns. The source's sorted file list, recursive,
is the same before and after the call. Then point `REAL_SPECS` at a directory
holding only an empty `done/`. Call it again with another fresh directory,
inside `pytest.raises(AssertionError)`. Last, point `REAL_SPECS` at an
unmodified copy of the live specs, where the measured ids sit at the top.
Call it with a third fresh directory, and compare that source's recursive
file list before and after.

**Measured on a prototype, 2026-10-03.** All of this was written against
`04222f69`, and both files passed. Each wrong version listed above was
applied to the prototype and failed its own criterion's witness. The two
that move a file out of the source came after it, and are driven by
reading alone. No
existing test needed an edit. `ruff`, `ty` and the `structure` gate passed.

**The `prose` gate** reads every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence over
25 words. A docstring over ten lines draws one hit per extra line
(`.saffron/gates/prose.py:303-316`). The smoke test's docstring is past that
already, so it must not grow by a line.

**Size.** Neither touched path is in `elevate_on`, so `size` is advisory.
The prototype counted 483 changed tokens by `size_gate`, against the `bug`
ceiling of 1300. `estimated_lines` is those tokens over four.
