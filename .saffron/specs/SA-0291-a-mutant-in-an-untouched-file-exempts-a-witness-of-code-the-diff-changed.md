---
id: SA-0291
title: "`revert` reads a mutant's file as its claim's subject, so a mutant in an untouched file exempts a witness of code the diff changed"
type: feature
priority: 1
depends_on: [SA-0290, SA-0273]
estimated_lines: 240
estimate_measured: true
touches:
  - saffron/intake.py
  - saffron/gates/core/revert.py
  - tests/test_intake.py
  - tests/test_revert.py
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
  - saffron/cli.py
  - saffron/task.py
  - saffron/scheduler.py
  - saffron/follow_up.py
  - saffron/agents/**
  - saffron/phases/**
  - saffron/cell/**
  - saffron/record/**
  - saffron/report/**
  - saffron/gates/suite.py
  - saffron/gates/runner.py
  - saffron/gates/contract.py
  - saffron/gates/core/witness.py
  - saffron/gates/core/criteria.py
  - saffron/gates/core/scope.py
  - tests/test_consumes.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
  - tests/test_witness_gate.py
budget_usd: 45
max_attempts: 3
max_turns: 165
acceptance:
  - claim: >-
      `revert` judges a witness whose mutant sits in a file the diff left
      alone when its criterion declares a `subject` the diff changed. Such
      a witness that passes with the source reverted fails the gate as
      theater. A `subject` in the repo's test paths keeps the witness
      judged too. The gate's summary names each witness its `subject` kept
      judged, with that subject, on a `fail` verdict and on a `pass`
      verdict. The summary names no other witness that way. That covers a
      witness its mutant's file already kept judged, one with no `subject`,
      one set aside with a `subject` outside the source, and one the head
      run never collected. The note naming a set-aside witness never calls
      its mutant's file a subject.
    witness: tests/test_revert.py::test_a_witness_whose_declared_subject_the_diff_changed_is_judged_and_named
    mutant:
      file: saffron/gates/core/revert.py
      find: 'without their source{note}"'
      replace: 'without their source"'
    wrong_versions:
      - "`subject` parsed and never read by `revert`, so the item's motivating witness is still set aside."
      - The witness judged and the summary left as it reads at base, so nothing shows the field mattered.
      - The summary naming the kept witness with its mutant's file rather than its subject.
      - The summary naming every judged witness that declares a subject in the source, a witness its mutant's file already kept included.
      - The summary naming a criterion whose witness the head run never collected.
      - A subject compared with the source alone, so a subject in the test paths exempts the witness.
      - The new text added to the `fail` summary alone, so a `pass` verdict names nothing.
      - The kept set taken as every witness whose mutant lies outside with any `subject`, before the set-aside ones leave it, so a set-aside witness's subject is named.
      - The set-aside note left worded as at base, so it still calls the mutant's file a subject.
  - claim: >-
      `revert` sets a witness aside only when its mutant's file and its
      declared `subject` both lie outside the diff's source and outside the
      repo's test paths. A criterion with no `subject` is set aside exactly
      as at base. The witness drives all twelve pairs of a mutant's file and
      a `subject`. The mutant's file lies in the source, outside it, or in
      the test paths. The `subject` is absent, in the source, outside it, or
      in the test paths. Only a mutant outside with no `subject`, and a
      mutant outside with a `subject` outside, are set aside.
    witness: tests/test_revert.py::test_a_witness_is_set_aside_only_when_its_mutant_and_its_subject_lie_outside_the_source
    mutant:
      file: saffron/gates/core/revert.py
      find: 'matches(c.mutant.file, pat)'
      replace: 'matches(c.mutant.file, pat) and False'
    wrong_versions:
      - "`subject` never read, so a mutant outside the source with a subject inside it is still set aside."
      - "`subject` replacing the mutant's file when declared, so a mutant in the source with a subject outside it is set aside."
      - Either path lying outside enough to set the witness aside.
      - A subject compared with the source alone, so a mutant outside with a subject in the test paths is set aside.
      - A subject outside the source setting aside a witness whose mutant's file is in the test paths.
  - claim: >-
      A criterion may declare `subject`, a repo-relative path. It is `None`
      when omitted. Load refuses a `subject` on a criterion with no
      `mutant`, with a message naming that criterion's witness. Load refuses
      a `subject` that is not canonical, with a message naming the path. The
      witness drives six such paths. They are an empty path, an absolute
      path, a `.` segment, a `..` segment, a trailing `/` and a `//`.
    witness: tests/test_intake.py::test_a_subject_needs_a_mutant_and_a_canonical_path
    mutant:
      file: saffron/intake.py
      find: 'segment == ""'
      replace: 'segment is None'
    wrong_versions:
      - A `subject` accepted on a criterion with no `mutant`.
      - A refusal message that names no criterion, so the author cannot tell which entry to fix.
      - A canonical check that refuses only an absolute path.
      - An empty `subject` accepted.
      - A `.` segment accepted.
      - A refusal message that leaves out the refused path.
      - An omitted `subject` read as an empty string, so every criterion without a mutant is refused.
---

## Context

Backlog item **b-000d04**, filed 2026-10-13 from `SA-0286`'s second review.
It cites `DESIGN.md` §5.4 and §5.4.1. Item **84** built the rule this spec
narrows. Every line number below was read at `9466b17b`.

**What `revert` sets aside today.** `revert` reverts the diff's source and
re-runs the new tests and the declared witnesses. A witness that still
passes is theater (`saffron/gates/core/revert.py:376-399`). `source` is
every changed file outside the repo's test paths (`:166-168`). A criterion
whose `mutant.file` is not in `source`, and not in the test paths, has its
witness taken out of the run (`:195-207`). The summary note names each one
with its mutant's file (`:208-211`). When no witness is left, the gate
reports `skip` (`:212-217`). The comment above the rule reads the mutant's
file as "the subject its claim is about (§5.4.1)" (`:176`).

**Where that reading breaks.** Item 84's case was `SA-0064`. Its witness
checked a predicate in a file the spec forbade, so reverting the source
could not make it fail. `SA-0286` broke the reading the other way. Its
witnesses read two prompts the diff changed. Its mutants edited a
`LENSES` entry in `saffron/phases/review.py`, a file the spec forbade.
`revert` dropped both witnesses, and only the `witness` gate checked them.
A witness asserting only the five base bullets killed the first mutant and
passed with the prompts reverted. `revert` exists to catch that witness.

**Where the author is told to do this.** `docs/agents/issue-tracker.md:137-141`
tells a writer to put a mutant's file under `forbidden`. It said nothing of
what that costs. That paragraph is edited by hand with this spec.

**The criterion model.** `Criterion` sets `extra="forbid"`
(`saffron/intake.py:117`), so a `subject` key is refused at base. Its
`mutant` is optional and `None` by default (`:127`). The `consumes`
validator refuses a path that is not canonical by testing each of its
segments (`saffron/intake.py:239-243`). `SA-0290` shares that validator with a new `removes` field.

**Who reads the rule.** `revert_gate` is called once, from
`saffron/gates/suite.py:168`, with the spec's whole `acceptance`. That
call needs no change. `SA-0273` adds a required keyword to `revert_gate`
naming tests to exempt. It removes them from the candidates as the
`preserves` witnesses are removed, and it leaves this rule alone.

**The decision.** The operator chose a declared field over running every
exempt witness or a rule alone. A `subject` can only remove an exemption,
never add one.

## Problem

Add `subject` to a criterion, and make `revert` judge a witness whose
`subject` the diff changed.

**The field.** `Criterion` gains `subject`, an optional string that is
`None` by default. It names the path a claim is about when the mutant's
file is not that code.

- Refuse a `subject` on a criterion whose `mutant` is `None`. The message
  names the criterion's witness and the word `subject`.
- Refuse a `subject` that is not canonical, with a message naming it.
  Use the same test the `consumes` validator applies to a path. Move that
  test into one function, and call it from both validators. Keep its text
  as it reads at base when you move it.

**The rule.** In `revert_gate`, a witness stays set aside only when both
of these hold.

- Its mutant's file lies outside `source` and outside the test paths, as
  at base.
- Its criterion declares no `subject`, or the `subject` also lies outside
  `source` and outside the test paths.

Compute the mutant-file condition once, with its existing conditions as
they read at base. Derive both the set-aside witnesses and the witnesses a
`subject` keeps judged from that one result. Do not repeat the condition
for the second set. A criterion with no `subject` is judged exactly as at
base. Keep the mutant file's test-path check inline, written as at base.
Test the `subject` in an expression of its own. Never route the mutant's
file through a helper it shares with the `subject`.

**The summary.** A witness its `subject` kept judged is one the mutant's
file alone would set aside. Its `subject` lies in `source` or in the test
paths. Only a witness in the run's subset counts. A witness that any
criterion sets aside is never named as kept, though another of its criteria
declares a `subject` in `source`. Add each such
witness and its `subject` to the summary note, as the set-aside witnesses
are added at `saffron/gates/core/revert.py:208-211`. The note already
reaches the `fail` and `pass` verdicts.

**The set-aside note.** At base it calls each set-aside witness one "whose
subject this diff never touched" (`saffron/gates/core/revert.py:208-211`).
Once `subject` is a declared field, that wording misleads. Reword it to name
the mutant's file, with no "subject" in it. Keep the witness and its
mutant's file in the note.

**The comment.** Rewrite the comment above the rule
(`saffron/gates/core/revert.py:176-194`) so it no longer says the mutant's
file is always the subject. Keep it to the reasons. Item 84 is the case for
the exemption, and the test paths stay judged for the reason at `:188-194`.
The docstring at `tests/test_revert.py:605` says the same thing, so rewrite
it too. In the leg that asserts no "subject" in the note, name no witness
or path with that word in it.

## Out of scope

- **The `driver.py check` warning.** A criterion whose mutant's file lies
  outside `touches` with no `subject` is named by `check`. It lives under
  `.claude/` and lands by hand after this cell.
- **`SA-0191`, `SA-0195` and `SA-0247`.** Each merged with mutants in
  `review.py` while its witnesses read changed files. Nobody re-checks them
  here.
- **Declaring `subject` on any queued spec.** `.saffron/**` is protected.
- **The `witness` gate.** It applies the mutant where it sits, and reads
  no `subject`.
- **The skip summaries that carry no note.** Uncommitted source is one,
  and a run with no readable verdict is another. Each leaves the note out
  at base, and still does.
- **`DESIGN.md`, `docs/agents/issue-tracker.md` and `CONTEXT.md`.** The
  first two are edited by hand with this spec. The glossary entry lands by
  hand under backlog item b-cd1566.

## Notes for the agent

**Every criterion edits code**, so each declares a mutant. Each mutant sits
in a file this diff changes, so `revert` judges its witness.

**`SA-0273` lands first.** After it, `revert_gate` takes a required keyword
naming tests to exempt. Pass it empty in every call your tests add, as
`tests/test_revert.py` does after `SA-0273`.

**At base every witness fails in its body.** Each one builds a criterion
or parses frontmatter that declares `subject`, and `Criterion` refuses the
key. Build each criterion inside the test, never at module scope. A
module-scope build would make the reverted run a collection error, which
`revert` reads as `skip`.

**Fixtures for the two `revert` witnesses.** Use `_tests` and `_reverted`
from `tests/test_revert.py`. Prior collects `t.py::test_a`. Head collects
that and the witnesses. The changed files are one source file and one file
under `tests/`, with `test_paths` of `tests/**`. Name three paths: the
changed source file, an untouched source file, and a file under `tests/`.
The reverted run passes every handed name unless a leg says otherwise. A
judged witness then fails the gate, and a set-aside one leaves nothing to
run, so the gate reports `skip`.

**Criterion 1** drives these legs.

- A mutant in the untouched file and a `subject` the diff changed. Assert
  `fail`, the witness as the one failure, and the witness and the subject
  in the summary.
- The same with the `subject` under `tests/`. Assert `fail`, and that path
  in the summary.
- The first leg with the reverted run failing the witness. Assert `pass`,
  and the witness and the subject in the summary.
- One run with six criteria. The first five follow, each but the fourth
  with a `subject` the diff changed. Their mutants sit in the untouched
  file, the changed file, the file under `tests/`, the changed file with no
  `subject`, and the untouched file. The sixth has its mutant in the
  untouched file and its `subject` at a second untouched path. Head
  collects every witness but the fifth. Assert the first four fail, and the
  first is named. Assert none of the second to fifth witnesses appears, and
  the sixth's `subject` path does not appear.
- A lone criterion with its mutant in the untouched file and no `subject`.
  Assert `skip`, the witness and the mutant's file in the summary, and no
  "subject" anywhere in it.

**Keep criterion 2's mutant text unique.** The rule's mutant-file condition is
computed once, and both sets derive from it (see Problem). A prototype built
that way holds that condition's text once at its head.

**Criterion 2** loops over the three mutant paths and the four `subject`
values, absent included, in one plain test. Each pair runs alone. The two
set-aside pairs report `skip` with the witness in the summary. The other
ten report `fail` with the witness as the one failure.

**Criterion 3** parses two criteria in one spec. The first declares a
`mutant` and a `subject`, and the second neither. Assert the first's
`subject` and the second's `None`. Parse the first with its `mutant`
removed, and read the validator's own message from the `ValidationError`
that `parse_spec` chains as the cause, as `tests/test_consumes.py:90-95`
does. Assert it names the witness and `subject`. Then parse each of the
six paths as a quoted `subject`, and assert each message holds the path's
`repr`.

**`saffron/gates/**` is in `elevate_on`,** so this task runs `elevated` and
`size` blocks.

**The `prose` gate** counts each new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence over
25 words. Keep each to two lines naming the reason.

**Size.** A prototype at `9466b17b` measured 839 changed tokens with
`size_gate`, against the `feature` ceiling of 3000. It held the field, both
validators, the rule, the note, the comment rewrite and the three
witnesses. Every test in `tests/test_revert.py`, `tests/test_intake.py`
and `tests/test_consumes.py` passed on it. `estimated_lines` is that count
over four, plus a margin for docstrings and the `SA-0273` keyword.
