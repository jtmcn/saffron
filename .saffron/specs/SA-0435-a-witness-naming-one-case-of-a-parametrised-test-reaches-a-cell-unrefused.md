---
id: SA-0435
title: "A witness naming one case of a parametrised test reaches a cell, and no check on the queue refuses it"
type: test
priority: 3
estimated_lines: 52
estimate_measured: true
touches:
  - tests/test_queued_specs.py
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
  - tests/records/**
  - hooks/**
  - saffron/**
  - tests/conftest.py
  - tests/test_scheduler.py
budget_usd: 28
max_attempts: 3
max_turns: 130
risk: standard
acceptance:
  - claim: >-
      A queued spec with a witness that carries a `[` and has no
      `preserves: true` fails
      `test_no_witness_names_one_case_of_a_parametrised_test`, a new test in
      `tests/test_queued_specs.py` with one case per spec file. The failure
      prints that witness. It fails for the case spellings
      `[SA-0001-a.md]`, `[a-b]` and `[0]`. It fails for a bracketed witness
      in the first criterion ahead of a bare one, and in a later criterion
      behind a bare first one. It fails again when the same case is checked
      a second time. The same id without its bracket passes. A bracketed
      witness with `preserves: true` passes, since the test it names
      already exists. A spec in `done/` whose witness carries a bracket
      passes, since a retired spec reaches no cell. The witness also reads
      a collected node id of the new test for every queued spec and every
      `done/` file but `README.md`.
    witness: tests/test_queued_specs.py::test_a_witness_naming_one_case_is_refused_and_a_bare_one_is_not
    wrong_versions:
      - "Every witness holding a `[` is read, `preserves` included, so a bracketed `preserves` witness fails."
      - "Only a `preserves` witness is read, so a bracketed witness without it passes."
      - "The check matches a bracket holding word characters alone, so `[SA-0001-a.md]` passes."
      - "The check matches a bracket holding a character outside word characters, so `[0]` passes."
      - "Only the first criterion is read, so a bracketed witness behind a bare one passes."
      - "Only a later criterion is read, so a bracketed witness in the first criterion passes."
      - "A `done/` file is parsed and checked like a queued spec, so a retired bracketed witness fails."
      - "The check refuses any witness holding `::`, so a bare id fails too."
      - "The new test is parametrised over the queued specs alone, so a `done/` file gets no case."
      - "The check raises a message naming only the spec file, so its failure prints no witness."
    covers:
      - set: the kinds of witness a criterion declares
        members:
          - member: "a witness without `preserves`, refused"
            driven_by: "Only a `preserves` witness is read, so a bracketed witness without it passes."
          - member: "a witness with `preserves: true`, not refused"
            driven_by: "Every witness holding a `[` is read, `preserves` included, so a bracketed `preserves` witness fails."
      - set: the case spellings inside the bracket
        members:
          - member: "`[SA-0001-a.md]`"
            driven_by: "The check matches a bracket holding word characters alone, so `[SA-0001-a.md]` passes."
          - member: "`[a-b]`"
            driven_by: tests/test_queued_specs.py::test_a_witness_naming_one_case_is_refused_and_a_bare_one_is_not
          - member: "`[0]`"
            driven_by: "The check matches a bracket holding a character outside word characters, so `[0]` passes."
      - set: the criteria of one spec
        members:
          - member: the first criterion, ahead of a bare one
            driven_by: "Only a later criterion is read, so a bracketed witness in the first criterion passes."
          - member: a later criterion behind a bare first one
            driven_by: "Only the first criterion is read, so a bracketed witness behind a bare one passes."
      - set: where the spec file sits
        members:
          - member: the queue
            driven_by: tests/test_queued_specs.py::test_a_witness_naming_one_case_is_refused_and_a_bare_one_is_not
          - member: "`done/`"
            driven_by: "A `done/` file is parsed and checked like a queued spec, so a retired bracketed witness fails."
      - set: the files the new test takes a case for
        members:
          - member: each queued spec
            driven_by: tests/test_queued_specs.py::test_a_witness_naming_one_case_is_refused_and_a_bare_one_is_not
          - member: "each `done/` file"
            driven_by: "The new test is parametrised over the queued specs alone, so a `done/` file gets no case."
      - set: what the failure prints
        members:
          - member: the bracketed witness, case included
            driven_by: "The check raises a message naming only the spec file, so its failure prints no witness."
      - set: the checks of one case
        members:
          - member: the first check
            driven_by: tests/test_queued_specs.py::test_a_witness_naming_one_case_is_refused_and_a_bare_one_is_not
          - member: a second check of the same case
            driven_by: tests/test_queued_specs.py::test_a_witness_naming_one_case_is_refused_and_a_bare_one_is_not
    positive_case: >-
      The witness reads the bare id, the bracketed `preserves` witness and
      the retired file pass in the same fixture that reads the bracketed
      form without `preserves` fail. So the check it reads passing is one
      that refuses a bracket when it sees one.
  - claim: >-
      Retiring a spec still keeps a collected case id for every `done/` file
      under each test that `test_retiring_a_spec_keeps_every_case_id` names,
      as it does today.
    witness: tests/test_queued_specs.py::test_retiring_a_spec_keeps_every_case_id
    preserves: true
---

## Context

Backlog item **b-281f0a**, the half it still leaves open. Its last entry
says the tree-only check, the parametrised witness in
`tests/test_queued_specs.py`, needs a tests-only spec of its own. This is
that spec.

**What `criteria` does with a witness.** It looks the witness up in the
names the suite collected, by exact string, and parses no name
(`saffron/gates/core/criteria.py:87-91`). Intake keeps the witness opaque
too (`saffron/intake.py:193-194`). So nothing between the spec file and
the gate reads what a witness's text looks like.

**The convention this check holds.** `docs/agents/issue-tracker.md:253-263`
says a declared witness is a bare node id. A parametrised test collects as
`test_name[case]`, so a bare id names none of its cases. And a spec that
names one case pins itself to a parameter list the cell has not written
yet. `SA-0095` is background for the convention. Its cell parametrised a
witness its spec named bare, and lost an attempt to
`witness-not-collected` (backlog item 159). This check refuses the opposite
spelling, a witness that names the case.

**Why a `preserves` witness is left alone.** That reason holds only for a
test the cell will write. A `preserves` witness names a test that exists at
base, so its parameter list is already written. And `criteria` collects a
named case by exact string. Refusing it too would leave no way to declare a
parametrised test as a `preserves` target.

**What `tests/test_queued_specs.py` checks per spec today.** Four tests
take one case per spec file from `CASES` (`tests/test_queued_specs.py:94`,
`tests/test_queued_specs.py:214`, `tests/test_queued_specs.py:288` and
`tests/test_queued_specs.py:309`). `CASES` is every queued spec plus every
`done/` file but `README.md` (`tests/test_queued_specs.py:43-57`). Each of
the four returns at once for a `done/` file
(`tests/test_queued_specs.py:96-97`, `tests/test_queued_specs.py:216-217`,
`tests/test_queued_specs.py:292-293` and
`tests/test_queued_specs.py:311-312`).
`test_retiring_a_spec_keeps_every_case_id` names three of them in a tuple.
It leaves out `test_a_committed_queued_spec_has_a_commit_that_wrote_its_witnesses`.
It asserts a collected
node id under each for every `done/` file
(`tests/test_queued_specs.py:203-212`). The `collected` fixture collects the
suite once per module (`tests/test_queued_specs.py:170-181`).

**Measured at base.** No witness in the four queued specs carries a `[`, so
the new check refuses none of them and `retired_first` stays empty. A `grep`
over `.saffron/specs/` finds no `witness:` or `preserves:` line holding one,
so none of the 378 `done/` files carries one either.

## Problem

Add `test_no_witness_names_one_case_of_a_parametrised_test` to
`tests/test_queued_specs.py`. Parametrise it over `CASES` with the ids the
other per-spec tests use. A `done/` file returns at once, as in the other
four. For a queued spec it collects every criterion's witness that holds a
`[` and has no `preserves: true`, and asserts that list is empty.

Add its name to the tuple in `test_retiring_a_spec_keeps_every_case_id`.

`_RetiredCase`'s docstring says "the three per-spec tests"
(`tests/test_queued_specs.py:37-38`), and there are four at base. Reword it
so it gives no count.

Add the witness. It writes spec files under `tmp_path`, reads them back with
`_cases`, and calls the new test's function on the case it gets, as
`test_a_retired_case_checks_nothing_and_a_queued_one_is_still_checked`
does. Then it reads the `collected` fixture for the new test's node id under
each member of `CASES`.

## Out of scope

**The origin item's `specs:` entry.** The item's "Done looks like" asked for
it here, and its own second entry found it already held.
`check_specs_name_their_items` reports a spec whose `## Context` cites an item
that does not list it back (`records/check.py:413-436`).
`tests/records/test_records_integrity.py:20-30` through `check_all` (`records/check.py:571`) applies it to the live tree.
Measured at base: with `SA-0432` taken out of `b-65eb8f`'s `specs:`, that
test fails with "SA-0432 cites this item and is not listed". It skips a spec
whose `## Context` cites no item. 47 `done/` specs cite none, among them
follow-ups an end review filed from a parent spec, and
`saffron/follow_up.py:500` writes such a spec under `.saffron/specs/`.

**Whether `driver.py check` joins the commands a spec review calls.**
`.claude/agents/spec-reviewer.md` still names `driver.py history` alone. That
is a decision about the review, and `.claude/` is no cell's to edit.

**Checking `done/`.** A retired spec reaches no cell, and the four per-spec
tests beside this one read nothing from a `done/` file either.

## Notes for the agent

**This change is new, so its witness has no mutant.** `witness` will report
`skip`. `revert` will report `skip` as well, since the diff has no source
outside the test paths (`saffron/gates/core/revert.py:362-367`). The wrong
versions under the criterion are what judge the witness.

**Never name the witness as one case.** It is a plain `def` that drives every
member itself, by the convention this spec holds.

**Write a spec file the witness needs with only `id`, `title`, `type` and
`acceptance`.** Give it an id no live spec holds, such as `SA-8887`.
`test_a_retired_case_checks_nothing_and_a_queued_one_is_still_checked`
already writes `SA-8888`.

**The failure must print the whole witness.** The witness reads it with
`pytest.raises(..., match=...)` over the escaped id, case included.
