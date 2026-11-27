---
id: SA-0437
title: "A queued spec that lists its wrong versions in prose prints no line about it, so REVIEW quietly runs none of them"
type: feature
priority: 3
estimated_lines: 31
estimate_measured: true
touches:
  - saffron/intake.py
  - tests/test_intake.py
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
  - tests/conftest.py
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/task.py
  - saffron/events.py
  - saffron/regate.py
  - saffron/parent_versions.py
  - saffron/follow_up.py
  - saffron/record/**
  - saffron/report/**
  - saffron/phases/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/agents/**
  - tests/test_cli.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
  - tests/test_spec_loop_driver.py
  - tests/test_adopt_stack_layer.py
  - tests/test_ledger_fold_task.py
  - tests/test_witness_gate.py
  - tests/test_suite.py
  - tests/test_session.py
  - tests/test_parent_versions.py
  - tests/test_regate.py
  - tests/test_report.py
  - tests/test_record_refs.py
  - tests/test_record_routed.py
  - tests/test_record_migrate.py
  - tests/test_stack_view.py
  - tests/test_events.py
  - tests/test_package.py
budget_usd: 40
max_attempts: 3
max_turns: 160
risk: standard
acceptance:
  - claim: >-
      `intake.prose_wrong_version_lines(spec)` returns one line for each
      criterion of `spec.acceptance` that declares no `wrong_versions`,
      where the spec's body holds a lead that
      `intake.WRONG_VERSION_LEAD` matches. Lines follow criterion order.
      Each is exactly `{spec.id} criterion {n}: its notes say {lead!r} and
      it declares no wrong_versions`, with `n` the criterion's place among
      all the spec's criteria counted from 1. `lead` is the first match in
      the body with each run of whitespace collapsed to one space, in the
      case the body writes it. The whole body is searched, every section.
      The witness drives nine bodies, each in its own spec of three
      criteria where only the second declares `wrong_versions`. One puts
      its lead under `## Context` and none under `## Notes for the agent`.
      It compares the whole list for each.
    witness: tests/test_intake.py::test_prose_wrong_version_lines_names_each_criterion_that_declares_none
    positive_case: >-
      Each of the nine specs holds a lead and two undeclared criteria, and
      yields exactly two lines.
    covers:
      - set: lead spellings
        members:
          - member: "`These fail it:`"
            driven_by: tests/test_intake.py::test_prose_wrong_version_lines_names_each_criterion_that_declares_none
          - member: "`These fail them:`"
            driven_by: A lead pattern that matches `it` and never `them`.
          - member: "`These builds fail it:`, one word between"
            driven_by: A lead pattern that allows no word between `these` and `fail`.
          - member: "`These wrong implementations fail it:`, two words between"
            driven_by: A lead pattern that allows at most one word between `these` and `fail`.
          - member: "`Each of these failed its witness.`"
            driven_by: A lead pattern that leaves out the `each of these failed` form.
          - member: a lower-case `these fail it` inside a sentence
            driven_by: A case-sensitive lead pattern.
          - member: a lead wrapped across a line break
            driven_by: A lead pattern that spells each gap as one literal space.
          - member: a lead with a tab in a gap
            driven_by: A lead pattern that spells each gap as one literal space.
      - set: sections of the body
        members:
          - member: a lead under `## Notes for the agent`
            driven_by: tests/test_intake.py::test_prose_wrong_version_lines_names_each_criterion_that_declares_none
          - member: a lead outside the notes section, under `## Context`
            driven_by: A search of the notes section only.
      - set: leads in one body
        members:
          - member: the first of two leads, quoted over the second
            driven_by: The last lead in the body quoted.
      - set: criteria of one spec
        members:
          - member: the first criterion, undeclared
            driven_by: A line for the first undeclared criterion only.
          - member: the second criterion, which declares
            driven_by: A line for every criterion, declared or not.
          - member: the last criterion, undeclared
            driven_by: A line for the first undeclared criterion only.
    wrong_versions:
      - A lead pattern that matches `it` and never `them`.
      - A lead pattern that leaves out the `each of these failed` form.
      - A case-sensitive lead pattern.
      - A lead pattern that spells each gap as one literal space.
      - A lead pattern that allows no word between `these` and `fail`.
      - A lead pattern that allows at most one word between `these` and `fail`.
      - The last lead in the body quoted.
      - A search of the notes section only.
      - A line for the first undeclared criterion only.
      - A line for every criterion, declared or not.
  - claim: >-
      `prose_wrong_version_lines` returns an empty list for a spec whose
      every criterion declares `wrong_versions`, for a body with no lead,
      and for a spec with no `acceptance:` whose body holds a lead. The
      bodies with no lead are `These pass it, and a fold fail it:`,
      `These three wrong builds fail it:`, `These fail its witness:` and
      `Synthese fail it:`. The spec with no `acceptance:` carries a
      `## Acceptance criteria` checklist. The witness calls the function
      twice on one flagged spec and compares the whole list each time.
    witness: tests/test_intake.py::test_prose_wrong_version_lines_is_empty_without_a_lead_or_an_undeclared_criterion
    positive_case: >-
      A spec of two criteria, where only the first declares
      `wrong_versions`, under the lead `These fail it:` yields exactly one
      line for criterion 2, on each of two calls.
    covers:
      - set: inputs that yield no line
        members:
          - member: every criterion declares
            driven_by: A line for every criterion, declared or not.
          - member: "`a fold fail it`, with no `these` before `fail`"
            driven_by: A lead pattern where `these` is optional.
          - member: three words between `these` and `fail`
            driven_by: A lead pattern that allows any number of words between `these` and `fail`.
          - member: "`its` in place of `it`"
            driven_by: A lead pattern with no word boundary after its last word.
          - member: "`these` ending a longer word"
            driven_by: A lead pattern with no word boundary before `these`.
          - member: a spec with no `acceptance:`
            driven_by: One line for a spec with no `acceptance:`, naming the spec.
      - set: calls on one input
        members:
          - member: the first call
            driven_by: tests/test_intake.py::test_prose_wrong_version_lines_is_empty_without_a_lead_or_an_undeclared_criterion
          - member: a repeat call
            driven_by: A function that remembers the last body it saw and returns nothing for it again.
    wrong_versions:
      - A line for every criterion, declared or not.
      - A lead pattern where `these` is optional.
      - A lead pattern that allows any number of words between `these` and `fail`.
      - A lead pattern with no word boundary after its last word.
      - A lead pattern with no word boundary before `these`.
      - One line for a spec with no `acceptance:`, naming the spec.
      - A function that remembers the last body it saw and returns nothing for it again.
---

## Context

Backlog item **b-ef8543**, filed 2026-09-29 from spec loop run 22.
It cites no `DESIGN.md` section. The change sits in intake (§3.2). Every
line number below was read at `42107252`.

**What happened.** `SA-0151`, `SA-0152` and `SA-0167` each listed about
35 wrong versions in their notes and declared no `wrong_versions:`.
REVIEW runs only the declared ones. It keeps the criteria that declare
any (`saffron/cell/session.py:3584`). So the host ran none. All three
were fixed by hand. The issue tracker's rule says a spec names its wrong
versions under `wrong_versions:` (`docs/agents/issue-tracker.md:199-207`).
Nothing checks it.

**The item's Done.** A line, from `driver.py check` or intake, when a
spec's notes list wrong versions and a criterion declares none. The
operator chose a pure judge in intake, read by `driver.py check` as a
concern that refuses nothing.

**Why not stderr from intake.** A first draft issued each line through
the `warnings` module from `discover_specs`. Under launchd a batch's
stderr goes to `batch.err.log` (`docs/host/dev.saffron.batch.plist:60-61`),
which no one reads. A dependency's `catch_warnings` also resets the
module registry, so "once per process" does not hold across a batch.
`coverage_problems` is the shape kept instead
(`saffron/intake.py:705-739`). It is a pure function, and only
`driver.py check` reads it.

**What it would name.** Measured at `42107252` with the prototype's
pattern. No queued spec of 4 yields a line. In `done/`, 40 specs of the
377 that parse yield one, 176 lines in all. The item's own phrase,
`These fail it` with nothing between, alone reaches 33 of them. All 40
are `SA-0119` to `SA-0190`. Only 2 of the 208 specs from `SA-0187` on
yield a line, and `SA-0187` and `SA-0190` are the two that added
`wrong_versions`. So the rule names the specs written before the field
existed, not most specs. A search of `done/` for `these`, up to three
words, then `fail it` or `fail them`, and for `each of these failed`,
found six distinct leads, counting case. Criterion 1 drives each, and
none has three words between.

## Problem

Add to `saffron/intake.py`:

- `WRONG_VERSION_LEAD`, a module-level compiled pattern, matched without
  regard to case. It matches `these`, then zero to two words, then
  `fail it` or `fail them`, each gap any run of whitespace. It also
  matches `each of these failed`. Both forms match on word boundaries.
- `prose_wrong_version_lines(spec) -> list[str]`, as criteria 1 and 2
  say. It searches the whole body and refuses nothing.

`parse_spec` and `discover_specs` stay as they are. Nothing in
`saffron/` calls the new function. `driver.py check` reads it, as the
next section says.

## Out of scope

- **No refusal and no `retired_first`.** The function refuses no spec,
  and no queued spec yields a line at `42107252`.
- **No ownership of a prose list.** The lead sits in the body, so the
  function cannot know which criterion a list belongs to. It names every
  undeclared criterion. `SA-0151` declares `wrong_versions` on some
  criteria and still yields lines for the rest.
- **A lead the author quotes.** A body that names `These fail it` as a
  phrase, as this one does, matches too. It yields no line where every
  criterion declares, as here.
- **A spec with no `acceptance:`.** Its checklist has no field to
  declare, so it yields no line.
- **Hand edits in this spec's own pull request, already made.** This
  copies `SA-0415`'s pattern.
  - `.claude/skills/run-saffron-spec-loop/driver.py` gains
    `_prose_wrong_version_lines` beside `_coverage_lines`. It reads
    `getattr(intake, "prose_wrong_version_lines", None)` and returns no
    line while the name is absent. `cmd_check` prints each line as
    `concern: <line>`, after the coverage concerns. Its exit code stays
    as it is.
  - `tests/test_spec_loop_driver.py` gains
    `test_check_notes_each_prose_wrong_version_line_and_still_exits_0`.
    It stubs the function, so it passes before and after this spec
    lands. It fails with the `cmd_check` loop removed.
  - `.saffron/deadcode-allow.py` gains `_.prose_wrong_version_lines`
    under "Called from outside the scanned roots". The `dead` gate scans
    no `.claude/` file, so the function reads as dead without it.
    Measured on the prototype, `dead` passes with that line.
- **Closing the item.** Once this spec's cell merges, backlog item
  b-ef8543 closes.

## Notes for the agent

**Every criterion is new code**, so each declares a witness and no
mutant. Neither new name exists at base.

**At base each witness fails in its body.** `tests/test_intake.py`
imports from `saffron.intake` at module scope. Import the new name
inside each test body, so the module still collects at base.

**A fixture helper.** Write a helper that renders a spec from a notes
text, a `## Context` text and a tuple of flags, one per criterion. A
true flag gives that criterion one `wrong_versions` entry. Put the
notes text under `## Notes for the agent`.

**The first witness.** Loop over nine bodies, each with the text the
line must quote. Write the `each` form as `Each of these failed its
witness. These fail them:`, and expect `Each of these failed`. Wrap one
as `These fail` and `it, each measured:` on two lines, and expect `These
fail it`. Write one with a tab between `These` and `fail`. Use `Beyond
those, these fail it too:` for the lower-case one, and expect `these
fail it`. Use `These builds fail it:` for one word between. Put one lead
under `## Context` alone, with notes that hold none. Compare the whole
list for each body.

**The second witness.** Compare the flagged spec's whole list on two
separate calls, each against the literal list. Comparing one call with
the next passes a function that returns nothing the second time. Assert
the checklist spec's `acceptance_criteria` is non-empty, so the empty
list is about the lines and not a failed parse.

**The `prose` gate** counts each new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words.

**Size.** A prototype measured 121 counted tokens outside `tests/` and
410 under it, against the 3000-token `feature` ceiling. That is 27
added lines outside `tests/` and 79 under it.
