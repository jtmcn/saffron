---
id: SA-0437
title: "A queued spec that lists its wrong versions in prose prints no line, so REVIEW quietly runs none of them"
type: feature
priority: 3
estimated_lines: 44
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
      case the body writes it. The witness drives seven bodies, each in
      its own spec of three criteria where only the second declares
      `wrong_versions`. It compares the whole list for each.
    witness: tests/test_intake.py::test_prose_wrong_version_lines_names_each_criterion_that_declares_none
    positive_case: >-
      Each of the seven specs holds a lead and two undeclared criteria, and
      yields exactly two lines.
    covers:
      - set: lead spellings
        members:
          - member: "`These fail it:`"
            driven_by: tests/test_intake.py::test_prose_wrong_version_lines_names_each_criterion_that_declares_none
          - member: "`These fail them:`"
            driven_by: A lead pattern that matches `it` and never `them`.
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
      - set: leads in one body
        members:
          - member: the first of two leads
            driven_by: The last lead in the body quoted.
          - member: the second of two leads
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
      - A line for the first undeclared criterion only.
      - A line for every criterion, declared or not.
  - claim: >-
      `prose_wrong_version_lines` returns an empty list for a spec whose
      every criterion declares `wrong_versions`, for a body with no lead,
      and for a spec with no `acceptance:` whose body holds a lead. The
      bodies with no lead are `These pass it, and a fold fails it:`,
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
          - member: "`fails it` with no `these` before it"
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
  - claim: >-
      `discover_specs` on a queued directory issues each line of
      `prose_wrong_version_lines` as a `warnings` category
      `intake.WrongVersionsInProse`, one call per line, and still returns
      the spec as discovered. It issues no line for a spec the same scan
      refuses for an inline mutant. With `retired=True` the same directory
      issues none. A fresh interpreter whose module, not `__main__`, scans
      the directory from two lines of its source prints each line to
      stderr exactly once under Python's default filters.
    witness: tests/test_intake.py::test_a_queued_scan_prints_each_prose_line_and_still_discovers_the_spec
    positive_case: >-
      The queued scan of the same directory, through the same recorder,
      issues the flagged spec's two lines and refuses the inline-mutant
      spec.
    covers:
      - set: scan kinds
        members:
          - member: a queued scan
            driven_by: A scan that files the flagged spec as a failure.
          - member: a retired scan
            driven_by: A scan that issues the lines on a retired scan too.
      - set: specs in one queued scan
        members:
          - member: a flagged spec
            driven_by: A function computed and never issued.
          - member: a spec where every criterion declares
            driven_by: A scan that files the flagged spec as a failure.
          - member: a spec refused for an inline mutant
            driven_by: Lines issued before the queued-only check, so a refused spec issues its lines.
      - set: ways a line reaches the operator
        members:
          - member: one `warnings` call per line
            driven_by: One call carrying every line of the spec joined.
          - member: printed by default
            driven_by: A category subclassing `DeprecationWarning`.
          - member: once per process across callers
            driven_by: A call attributed to the caller's frame, so each calling line prints it again.
          - member: once per process within one module
            driven_by: A scan that sets the `always` filter before each call.
          - member: on stderr
            driven_by: A line printed to stdout.
    wrong_versions:
      - A scan that files the flagged spec as a failure.
      - A scan that issues the lines on a retired scan too.
      - Lines issued before the queued-only check, so a refused spec issues its lines.
      - One call carrying every line of the spec joined.
      - A category subclassing `DeprecationWarning`.
      - A call attributed to the caller's frame, so each calling line prints it again.
      - A scan that sets the `always` filter before each call.
      - A line printed to stdout.
      - A function computed and never issued.
---

## Context

Backlog item **b-ef8543**, filed 2026-09-29 from pass 22 of the spec loop.
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
operator chose intake, and a printed line that refuses nothing.

**Where it goes.** `discover_specs` already treats a queued scan apart
from a retired one. Its inline-mutant check runs only where `retired` is
false (`saffron/intake.py:693-694`). Every queued scan
reaches it, `saffron queue` and `saffron batch` included, through
`build_queue` (`saffron/scheduler.py:1432`). A retired scan keeps a
spec as it shipped. `saffron/` uses neither `warnings` nor `logging` at
base, and `saffron/cli.py` is in flight in `SA-0429`. So intake prints
through the standard `warnings` module, attributed to itself. Python's
default filter then prints each distinct line once per process, however
many callers scan.

**What it would print.** Measured at `42107252` with the prototype's
pattern. No queued spec of 4 yields a line. In `done/`, 40 specs of the
377 that parse yield one, 176 lines in all. The item's own phrase,
`These fail it` with nothing between, alone reaches 33 of them. All 40 are `SA-0119` to
`SA-0190`. Only 2 of the 208 specs from `SA-0187` on yield a line, and
`SA-0187` and `SA-0190` are the two that added `wrong_versions`. So the
rule names the specs written before the field existed, not most specs.
A search of `done/` for `these`, up to three words, then `fail it` or
`fail them`, and for `each of these failed`, found six distinct leads,
counting case. Criterion 1 drives each, and none has three words between.

## Problem

Add to `saffron/intake.py`:

- `WRONG_VERSION_LEAD`, a module-level compiled pattern, matched without
  regard to case. It matches `these`, then zero to two words, then
  `fail it` or `fail them`, each gap any run of whitespace. It also
  matches `each of these failed`. Both forms match on word boundaries.
- `WrongVersionsInProse`, a subclass of `UserWarning`.
- `prose_wrong_version_lines(spec) -> list[str]`, as criteria 1 and 2
  say. It refuses nothing.

In `discover_specs`, after a spec loads and passes the queued-only
check, and only when `retired` is false, issue each of its lines with
`warnings.warn(line, WrongVersionsInProse, stacklevel=1)`. Write the
`stacklevel` out, since ruff's `B028` fails a call without it. At 1 the
warning is attributed to `saffron.intake`. The spec is still appended as
discovered.

## Out of scope

- **No refusal and no `retired_first`.** The line refuses no spec, and
  no queued spec yields one at `42107252`.
- **No ownership of a prose list.** The lead sits in the body, so the
  function cannot know which criterion a list belongs to. It names every
  undeclared criterion. `SA-0151` declares `wrong_versions` on some
  criteria and still yields lines for the rest.
- **A lead the author quotes.** A body that names `These fail it` as a
  phrase, as this one does, matches too. It yields no line where every
  criterion declares, as here.
- **A spec with no `acceptance:`.** Its checklist has no field to
  declare, so it yields no line.
- **`driver.py check` stays as it is.** Wiring the function into
  `check` is a hand edit, not this spec's.
- **Test noise.** `tests/test_scheduler.py`'s
  `test_no_real_spec_is_refused_on_its_own_acceptance_criteria` copies
  retired specs into a queued directory. It then shows 156 lines from 36
  specs in pytest's warnings summary, measured on the prototype. It still
  passes. Leave it.

## Notes for the agent

**Every criterion is new code**, so each declares a witness and no
mutant. None of the three names exists at base.

**At base each witness fails in its body.** `tests/test_intake.py`
imports from `saffron.intake` at module scope. Import the new names
inside each test body, so the module still collects at base.

**A fixture helper.** Write a helper that renders a spec from a body and
a tuple of flags, one per criterion. A true flag gives that criterion one
`wrong_versions` entry. Put the body under
`## Notes for the agent`.

**The first witness.** Loop over seven bodies, each with the text the
line must quote. Write the `each` form as `Each of these failed its
witness. These fail them:`, and expect `Each of these failed`. Wrap one
as `These fail` and `it, each measured:` on two lines, and expect `These
fail it`. Write one with a tab between `These` and `fail`. Use `Beyond
those, these fail it too:` for the lower-case one, and expect `these
fail it`. Compare the whole list for each body.

**The second witness.** Compare the flagged spec's whole list on two
separate calls, each against the literal list. Comparing one call with
the next passes a function that returns nothing the second time. Assert
the checklist spec's `acceptance_criteria` is non-empty, so the empty
list is about the lines and not a failed parse.

**The third witness.** Write a flagged spec, two criteria with neither
declaring, and a clean one beside it. Add a third whose one criterion
declares a `mutant:` inline, under a lead, with no `wrong_versions`.
Assert its own lines are not empty, so its silence in the scan is about
the refusal. Pin the flagged spec's two lines as literals. Record with
`warnings.catch_warnings(record=True)` and
`warnings.simplefilter("always")`. Keep only records whose category is
`WrongVersionsInProse`. Compare the discovered ids, the failure names
and the recorded messages as whole lists, for both scan kinds. Then
write a small module into a subdirectory of `tmp_path`. It calls
`discover_specs` on the spec directory on two separate lines. Run it as
`sys.executable -c "import scan"` with that subdirectory as `cwd`, and
assert each line appears exactly once in stderr. Two calling lines
catch a warning attributed to the caller, which prints once per calling
line. Python's default filters print a `UserWarning` and ignore a
`DeprecationWarning` raised outside `__main__`. Measured on host CPython
3.14.7.

**The `prose` gate** counts each new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words.

**Size.** A prototype measured 173 counted tokens outside `tests/` and
611 under it, against the 3000-token `feature` ceiling. That is 37
added lines outside `tests/` and 122 under it.
