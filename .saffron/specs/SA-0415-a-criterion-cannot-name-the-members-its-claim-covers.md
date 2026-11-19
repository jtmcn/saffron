---
id: SA-0415
title: "A criterion cannot name the members of the sets its claim covers, so no command sees a member no witness drives"
type: feature
priority: 3
estimated_lines: 370
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
  - saffron/agents/**
  - saffron/phases/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/scheduler.py
  - saffron/mutants.py
  - saffron/task.py
  - saffron/cli.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
  - tests/test_spec_loop_driver.py
  - tests/test_context.py
budget_usd: 48
max_attempts: 3
max_turns: 200
acceptance:
  - claim: >-
      A criterion may declare `covers`, a list of sets, and `positive_case`,
      one sentence. Each set has a `set` name and a list of `members`. Each
      member has a `member` text and an optional `driven_by`, which loads as
      `None` when omitted. Sets and members load in declared order. One
      member text may recur in two sets, and one set name in two criteria.
      A criterion declaring only `claim` and `witness` loads `covers` as an empty list and
      `positive_case` as `None`, and its `model_fields_set` holds only
      `claim` and `witness`. Load refuses nine shapes as a `SpecError`, each in
      its own spec. They are an empty `covers`, a blank set name, an empty
      `members`, a blank member, one member twice in a set, one set name
      twice in a criterion, a blank `positive_case`, an unknown key in a
      member, and an unknown key in a set. Each blank is whitespace alone.
      A repeated member shares only its text, with another `driven_by` and
      a member between the two. A repeated set name carries other members,
      with a set between the two.
    witness: tests/test_intake.py::test_a_criterion_declares_the_sets_its_claim_covers_and_its_positive_case
    wrong_versions:
      - A set with no duplicate check, so one member declared twice loads.
      - A duplicate check across every set of a criterion, so one member text in two sets is refused.
      - A set-name check across the whole spec, so one set name in two criteria is refused.
      - A member model that ignores unknown keys, so a misspelt `driver:` loads.
      - A set model that ignores unknown keys.
      - A blank check by emptiness, so a set name of two spaces loads.
      - A blank check by emptiness on the member, so a member of one space loads.
      - A `positive_case` with no blank check.
      - A blank check by emptiness on `positive_case`, so one of two spaces loads.
      - The sets sorted by name at load, so the declared order is lost.
      - The members sorted at load.
      - An explicit empty `covers` accepted.
      - An explicit empty `members` accepted.
      - A `driven_by` that defaults to an empty string in place of `None`.
      - A set name declared twice in one criterion accepted.
      - Duplicates compared as whole models, so a member or set repeated with other contents loads.
      - Only adjacent duplicates refused, so a repeat with an entry between loads.
  - claim: >-
      `intake.coverage_problems(spec)` returns one line per declared member
      whose `driven_by` is absent, or is not exactly its own criterion's
      witness or one of its own criterion's `wrong_versions`. A member
      driven by either yields no line. Each line starts `criterion {n}:`,
      with `n` the criterion's place among all the spec's criteria,
      counted from 1. Lines follow the criteria, their sets and their
      members in declared order. The witness's spec holds three criteria.
      The first is clean. It declares two wrong versions, and its two
      members are driven by its own witness and its first wrong version.
      The second declares three wrong versions and two sets, and the
      second set's name sorts before the first's. Four of its members are
      driven, by its witness twice, its middle wrong version and its last
      wrong version. Seven are flagged. One names no driver. The others
      name the first criterion's witness, its own wrong version with a
      changed first letter's case, the first criterion's wrong version, a
      prefix of its witness, its witness with a suffix, and its own wrong
      version with a trailing space. In each set the first and the last
      member are flagged, and a driven member sits between two flagged
      ones. The third criterion has one member, with no driver. The
      witness compares the whole list of lines.
    witness: tests/test_intake.py::test_coverage_problems_names_each_declared_member_no_driver_reaches
    wrong_versions:
      - Any criterion's witness accepted as a driver.
      - Any criterion's wrong version accepted as a driver.
      - Drivers compared case-insensitively.
      - A driver accepted when it is a prefix of the witness.
      - Drivers compared after stripping whitespace.
      - A member with no `driven_by` skipped.
      - The witness accepted and every wrong version refused.
      - Only the first wrong version accepted.
      - Only the last wrong version accepted.
      - Only the first two wrong versions accepted.
      - Only the first and the last wrong version accepted.
      - The lines sorted before they are returned.
      - Criteria numbered among those that yield lines, so the flagged criterion reads as criterion 1.
      - The last criterion skipped.
      - Only the first set of a criterion read.
      - The sets walked in reverse order.
      - The sets walked sorted by name.
      - The last member of each set skipped.
      - A set's walk stopped at its first driven member.
      - A driver accepted when it starts with the witness.
  - claim: >-
      `coverage_problems` also returns one line for a criterion whose claim
      holds a word of `intake.NEGATION_WORDS` and that declares no
      `positive_case`. The tuple holds exactly `no`, `not`, `never`,
      `nothing`, `none`, `neither`, `nor`, `without` and `cannot`. A word
      matches whole and in any case, inside backticks too. The criterion
      yields one such line however many words match. The line is exactly
      `criterion {n}: its claim says {word!r} and it declares no
      positive_case`, where `word` is the first match in the claim,
      lowercased. The witness drives each word in its own claim, and an
      upper case and a sentence-initial form, each the only listed word in
      its claim. One loud claim ends with its word and a full stop. Its
      quiet claims hold each word inside a longer word, and they yield no
      line. One quiet claim comes first, one sits among the loud ones, and
      one comes third from last. A criterion with an undriven member and a
      negative claim yields the member's line first. The last two criteria
      hold one negative claim. The first of them declares a
      `positive_case` and an undriven member, and yields only the member's
      line. The last declares no `positive_case` and yields the negation
      line. The witness compares the whole list of lines from the one
      call.
    witness: tests/test_intake.py::test_coverage_problems_names_each_negative_claim_that_declares_no_positive_case
    wrong_versions:
      - A list missing `nor`.
      - A list that adds `only`.
      - A match on substrings, so `another` and `nobody` are flagged.
      - A case-sensitive match, so `NOT` and `Never` go unflagged.
      - The word reported first in the tuple's order, not in the claim's order.
      - The word reported as the claim spells it, not lowercased.
      - A declared `positive_case` ignored.
      - Backticked text stripped before the match.
      - The negation line placed before the member lines.
      - A negation line worded other than the template.
      - One line per matched word.
      - Criteria numbered among those that yield lines.
      - The walk stops after the first criterion that yields a line.
      - A declared `positive_case` skips the criterion's member lines.
      - The final criterion skipped.
      - A `positive_case` flag carried across criteria.
      - A whitespace split that strips backticks, so a word before a full stop goes unflagged.
  - claim: >-
      `coverage_problems` refuses no spec. A spec it returns lines for parses
      with `parse_spec`, and `discover_specs` returns it as a candidate. In
      the same scan `discover_specs` refuses a spec beside it that declares
      an inline mutant, so the scan is seen refusing.
    witness: tests/test_intake.py::test_a_spec_coverage_problems_flags_still_parses_and_is_discovered
    wrong_versions:
      - "`parse_spec` raises `SpecError` for a spec the judge flags."
      - "`discover_specs` files a spec the judge flags as a failure."
  - claim: >-
      The docstring of `coverage_problems` says the judge cannot know
      whether a declared set is complete, and that `NEGATION_WORDS` is a
      heuristic.
    witness: tests/test_intake.py::test_coverage_problems_docstring_says_it_cannot_know_a_set_is_complete
    wrong_versions:
      - A docstring silent on whether a set is complete.
      - A docstring that calls the list a rule rather than a heuristic.
  - claim: >-
      Every spec queued at the change still parses.
    witness: tests/test_queued_specs.py::test_every_queued_spec_parses
    preserves: true
  - claim: >-
      Every spec in `done/` at the change still parses.
    witness: tests/test_queued_specs.py::test_every_retired_spec_still_parses
    preserves: true
---

## Context

Backlog item **b-c12d39**, filed 2026-11-09 from the spec chain speed
review. It cites `DESIGN.md` §5.4. Every line number below was read at
`f1068af4`.

**What keeps happening.** Spec reviews keep finding one class of defect.
A claim covers a set, and its witness drives one member. Or a claim has
a negative clause, and its witness never sees the positive case. The
item counts five of six blockers in this class on 2026-11-04, and seven
findings on 2026-11-07. The rule lives in prose, in
`docs/agents/issue-tracker.md`'s Conventions and the spec writer's step
6. The writer puts the table in its report, never in the spec.

**Why no command can read it.** `Criterion` sets `extra="forbid"`
(`saffron/intake.py:157`). Its fields are `claim`, `witness`,
`preserves`, `mutant`, `subject` and `wrong_versions`
(`saffron/intake.py:150-178`). So a spec that declares members fails to
parse.

**The precedent to copy.** `wrong_versions` is the newest optional
field (`saffron/intake.py:175`). Its validator runs only when the spec
sets the key, since pydantic skips a field validator on a default
(`saffron/intake.py:183-185`). It refuses an explicit empty list, a
blank entry and a repeated entry, and returns the list as declared
(`saffron/intake.py:180-198`).

**Who calls the judge.** `driver.py check` prints a `blocker:` line for
each problem a core function finds. `_disclosure_blocker` is the shape.
It calls `refuse_disclosed_mutants` and prints what it raises
(`.claude/skills/run-saffron-spec-loop/driver.py:2822`). This spec's
own pull request adds `_coverage_lines` beside it by hand. It calls
`intake.coverage_problems`. Each member line is a blocker. Each line that
ends `and it declares no positive_case` is a concern, by operator decision,
since the word list matches 78% of done claims. It tolerates the name's
absence until this spec lands. So the format of the third line is load
bearing for `check`.

**Where a dump could shift.** A deferred stack batch writes each spec
into `deferred.json` with `exclude_unset=True` (`saffron/cli.py:1113`).
A defaulted field is left out there, as `wrong_versions` is.

## Problem

Add two optional fields to `Criterion` in `saffron/intake.py`.

- `covers` is a list of sets, empty by default. Each set is a model
  with a `set` name and a `members` list. Each member is a model with a
  `member` text and a `driven_by`, which is `None` when omitted. Both
  models set `extra="forbid"`.
- `positive_case` is one sentence, `None` by default. It names the case
  the witness first observes where the claimed effect does happen,
  through the same instrument as the negative clause.

Validate only shape at load, and only when the spec declares the key.
Refuse the nine shapes criterion 1 names. A `driven_by` that names
nothing the criterion declares is no load error. The judge reports it.

Add `NEGATION_WORDS`, a module-level tuple of the nine words criterion
3 names, and `coverage_problems(spec) -> list[str]`. It walks the
criteria in order, numbering them from 1. For each one it emits a line
per undriven member, in set order and then member order. Then it emits
the negation line, if any. Write each line exactly as one of these,
with `!r` reprs.

```
criterion {n}: {set!r} member {member!r} names no driver
criterion {n}: {set!r} member {member!r} names {driven_by!r}, which is neither its witness nor one of its wrong versions
criterion {n}: its claim says {word!r} and it declares no positive_case
```

A member is driven when its `driven_by` equals its own criterion's
`witness` or one of its own `wrong_versions`, compared as whole strings.
A word matches as a whole word in any case, with no text stripped first.
The `word` printed is the first match in the claim, lowercased.

The function's docstring says two things. It judges only the members a
spec declares, and cannot know whether a set is complete. The word list
is a heuristic: a listed word can describe a precondition, and a
negation can be spelled without one.

`parse_spec` and `discover_specs` stay as they are. The judge refuses
nothing.

## Out of scope

- **The implementer never reads the new fields.**
  `context.witnesses_block` prints each claim and its wrong versions
  (`saffron/agents/context.py:186`). It stays as it is. So
  `refuse_disclosed_mutants` needs no new source text to search.
- **No core path calls the judge.** `saffron queue`, `saffron cell` and
  every gate ignore it. Only `driver.py check` reads it.
- **This spec declares neither field.** A spec cannot use the
  frontmatter its own task adds (`DESIGN.md` §3.2).
  Its own set table sits in the writer's report.
- **The word list's reach.** At `f1068af4` the 364 specs in `done/`
  that parse held 1580 claims. The nine words hit 1233 of them, in 333 of the 334 specs that declare
  `acceptance:`. A full reading of 25 sampled hits found 19 real
  negative clauses. The rest name a precondition, such as "a task that recorded
  nothing". `only` is left out. Most of its hits narrow a claim rather
  than negate it.
- **No `retired_first`.** The judge refuses no spec at load, and no spec
  is queued at `f1068af4`.
- **Hand edits in this spec's own pull request.**
  `.claude/skills/run-saffron-spec-loop/driver.py` gains
  `_coverage_lines` beside `_disclosure_blocker`, and its `SKILL.md`
  check paragraph names the new blocker and concern.
  `tests/test_spec_loop_driver.py` gains a witness for that wiring. It
  replaces `coverage_problems` with a stub, so it passes before and
  after this spec lands. `.saffron/deadcode-allow.py` gains
  `_.coverage_problems` under "Called from outside the scanned roots".
  The `dead` gate scans no `.claude/` file
  (`.saffron/gates/dead.py:21`), so the judge reads as dead without it.
  In `docs/agents/issue-tracker.md`'s Conventions, the bullet on a claim
  over a set gains two sentences. They name `covers:` and
  `positive_case:`, and say load refuses either key until `SA-0415`
  lands.
- **Hand edits once this spec merges.** `.claude/agents/spec-writer.md`
  step 6 and `.claude/agents/spec-reviewer.md` check 3 name the fields.
  Before the merge a spec declaring them fails to parse. `CONTEXT.md`
  gets its entries by hand under b-c7fd81.

## Notes for the agent

**Every criterion is new code**, so each declares a witness and no
mutant, and `witness` will report `skip`. The fields, the models, the
tuple and the function do not exist at base.

**At base each witness fails in its body.** `tests/test_intake.py`
imports from `saffron.intake` at module scope. Import
`coverage_problems` and `NEGATION_WORDS` inside each test body, so the
module still collects at base. At base load refuses the `covers` key,
so the first witness fails on its valid spec.

**The first witness.** Copy the shape of
`test_a_criterion_declares_its_wrong_versions_and_parse_refuses_an_empty_or_repeated_one`.
Write each refused shape into its own spec text. Read the omitted pair
through `model_fields_set`, which must equal `{"claim", "witness"}`.
Declare the sets and the members out of sorted order, so a sort is
caught.

**The second witness.** Give each flagged member its own text, and
write the driver with a trailing space as a double-quoted YAML scalar.
A plain scalar loses the space. Declare the flagged members out of
sorted order, so a sort is caught. Keep every claim in the fixture spec
free of the nine words, so no negation line joins the list. Put the
clean criterion with two wrong versions first, so the flagged one is
criterion 2. Give the third criterion one undriven member, so the last
criterion yields a line.

**The third witness.** Assert `sorted(NEGATION_WORDS)` against the nine
words, so a missing or an added word fails. One claim holds `not`
before `no`, so the claim's order and the tuple's order differ. One
claim holds a word only inside backticks. The quiet claims hold
`another`, `normal`, `note`, `nevertheless`, `notable`, `nobody`,
`knot`, `nothingness` and `nonempty`. Coin a word for each of
`neither`, `without` and `cannot` with the word inside it, such as
`neithermost`. Spread the quiet claims among the loud ones, so a numbering
that skips a quiet criterion is caught. Give the criterion that declares
a `positive_case` an undriven member too. Put it right before its twin,
which ends the spec, so a flag leaking into the next criterion is
caught.

**The fourth witness.** Write both specs into one `tmp_path` and call
`discover_specs` once. Assert the candidate ids and the failure file
names as whole lists.

**The `prose` gate** counts each new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words.

**Size.** A prototype of this change measured 461 counted tokens
outside `tests/` and 1018 under it, against the 3000-token `feature`
ceiling. That is 370 changed lines in all.
