---
id: SA-0389
title: "`revert` reads no declared rename, so a renamed test that passes without the source is refused as new"
type: bug
priority: 3
risk: elevated
estimated_lines: 138
estimate_measured: true
touches:
  - saffron/gates/core/revert.py
  - saffron/gates/suite.py
  - tests/test_revert.py
  - tests/test_suite.py
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
  - saffron/gates/core/census.py
  - saffron/gates/core/criteria.py
  - saffron/gates/contract.py
  - saffron/gates/runner.py
  - saffron/intake.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/report/**
  - saffron/finish.py
  - saffron/task.py
  - saffron/regate.py
  - saffron/cli.py
  - tests/test_census.py
  - tests/test_session.py
  - tests/test_regate.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
budget_usd: 48
max_attempts: 3
max_turns: 200
acceptance:
  - claim: >-
      `revert_gate` takes a spec's declared `renames` as a keyword that
      defaults to none. It accepts a pair by `census`'s own rule: the old
      name is collected at base and absent at head, and the new name is
      collected at head and absent at base. Names are compared whole. An
      accepted pair's new name leaves the set of tests the diff adds, so
      `run_tests` is never handed it, unless a criterion names it as its
      witness. A renamed criterion witness is judged as before, and a
      renamed `preserves` witness stays out as before. The summary names
      each new name the rule left out, and no other pair's new name. In
      one call the witness drives eight pairs: one accepted, one whose old
      name stays at head, one whose old name was never collected, one whose
      new name was already collected at base, one whose new name head does
      not collect, one accepted whose new name a criterion names, one
      accepted whose new name a `preserves` criterion names, and one whose
      old name matches a base name only after the last `::`. One undeclared
      new test sits beside them. It asserts the exact subset handed to
      `run_tests`, and which new names the summary holds. Over two
      accepted renames, one a criterion's witness, both passing with the
      source reverted, it asserts a `fail` naming the witness alone. With
      no renames, the same input fails both names. With the non-witness
      pair alone, the gate skips as a diff that adds no new test, and its
      summary names that pair's new name.
    witness: tests/test_revert.py::test_revert_leaves_out_exactly_the_declared_renames_census_accepts
    wrong_versions:
      - Every declared new name left out, whatever base and head collected.
      - A pair accepted when its old name was collected at base, without asking whether head still collects it.
      - The renamed names subtracted after the criteria union, so a renamed criterion witness is never judged.
      - The renames read for the summary but never subtracted, so an accepted pair still fails `passed-without-source`.
      - Names matched on the text after the last `::`, so a pair whose old name only shares a test's short name is accepted.
      - A summary that names every accepted new name, a criterion's witness and a `preserves` witness included.
      - A summary built without the new-name checks, so it names a pair whose new name was already collected at base, or one head does not collect.
      - A summary that names no left-out pair.
      - A skip that reports every new test as exempt when only renames remained.
  - claim: >-
      The gate suite hands `revert_gate` the renames of the spec it was
      built with. The witness builds a suite three times over one baseline
      whose `tests` gate collects an old name, and one head that collects
      the new name and passes it with the source reverted. A `CellSpec`
      declaring the pair and an `intake.Spec` declaring it each yield a
      `revert` result of `skip`. A spec declaring no renames yields `fail`,
      with one `passed-without-source` failure naming the new name.
    witness: tests/test_suite.py::test_the_suite_hands_revert_the_specs_own_renames
    wrong_versions:
      - The suite never passing the spec's renames to `revert_gate`, so a declared pair still fails `passed-without-source`.
      - The suite passing an empty mapping in place of the spec's renames.
---

## Context

Backlog item **b-d2b6b3**, filed from spec loop run 69 while `SA-0387`
(#1196) was in its cell. It cites `DESIGN.md` §5.4. Every line number below was read
at `3495ef85`.

**What `census` does with a rename**. `SA-0387` added a spec's
`renames` map (`saffron/intake.py:253`) and carried it on `CellSpec`
(`saffron/cell/session.py:377`). The suite reads it through the
`SuiteSpec` protocol (`saffron/gates/suite.py:54`), and hands it to
`census_gate` (`saffron/gates/suite.py:233`). `census_gate` accepts a
pair when its old name is in the removed set. Its new name must be
collected at head and absent at base
(`saffron/gates/core/census.py:78-82`). An accepted pair's old name is no
`removed-test` failure.

**What `revert` does with one**. `revert_gate`
(`saffron/gates/core/revert.py:210`) takes no renames. The suite calls it
with ten keywords, none of them a rename
(`saffron/gates/suite.py:185-200`). Its new-test set is
`((set(after) - set(before)) | (declared & set(after))) - preserved`
(`saffron/gates/core/revert.py:262`). `declared` is every criterion's
witness (`saffron/gates/core/revert.py:261`), and `preserved` every
`preserves` witness (`saffron/gates/core/revert.py:246`). So a renamed
test's new name, collected at head and not at base, is a new test there.
If it passes with the diff's source reverted, `revert` fails it
`passed-without-source` (`saffron/gates/core/revert.py:585-605`). That
is the case the item names. A test kept under a new name tests what it
tested before, and it passes without the source when the diff only
renamed it. #1099 was refused that way in spec loop run 56.

**Who reaches the suite**. `revert_gate` has one production caller,
`GateSuite._run` (`saffron/gates/suite.py:185`). Every path that builds a
suite reaches it: a cell through `CellSpec`, and `reverify` through an
`intake.Spec` (`saffron/phases/package.py:559`). `saffron package`,
`saffron regate` and the finishing layer all reach `reverify`
(`saffron/cli.py:1159`, `saffron/regate.py:180`). So one
keyword in the suite's call carries the renames to every path.

**The second subset**. `_second_subset` reads only names collected at
both base and head (`saffron/gates/core/revert.py:147`). A renamed test's
new name is absent at base, so it never reaches that advisory subset, at
base or after this change.

## Problem

Give `revert_gate` a keyword `renames`, a mapping from an old collected
name to its new one, that defaults to no renames. Pass `spec.renames` to
it from `GateSuite._run`.

In `revert_gate`, accept a pair by `census`'s rule. Its old name is
collected at base and absent at head. Its new name is collected at head
and absent at base. Compare names whole, and never split one, as
`census`'s module docstring says (`saffron/gates/core/census.py:9-12`).

An accepted pair's new name leaves the `set(after) - set(before)` half
of the new-test set. The criteria union is untouched: a criterion's
witness is a name this change claims to make pass, so a renamed witness
still joins the set. `- preserved` stays last, so a renamed `preserves`
witness stays out.

**Why the rule is `census`'s**. A pair `revert` leaves out is then
exactly a pair `census` accepts. One whose old name head still collects
added a test beside the old one, and `revert` judges it. One whose old
name base never collected renamed nothing `census` can see, and `revert`
judges it too.

Add one clause to the gate's summary naming each new name the rule left
out, and no other name. It is the channel the exempt names already ride
(`saffron/gates/core/revert.py:280-281`). Leave out a new name a
criterion names, since that name is judged. Leave out one the set
would not hold without the rule. A skip whose subset holds
only left-out renames keeps the message "the diff adds no new test"
(`saffron/gates/core/revert.py:308`).

Update the module docstring's sentence that defines "new"
(`saffron/gates/core/revert.py:5-7`), and the list of skips in
`revert_gate`'s docstring (`saffron/gates/core/revert.py:228-229`), to
name the declared renames.

## Out of scope

- **The finishing layer's half of the item**. Its suite runs under the
  synthetic `FINISH-0` spec (`saffron/finish.py:110-115`), which
  declares no renames. So finish 82's revised parametrize ids still read
  as a removed test to `census`, and as new tests to `revert`. b-d2b6b3
  stays open for it.
- **A renamed test no criterion names, whose body the diff changed**.
  The rule leaves it out whatever its body says. It never reaches the
  advisory second subset either (`saffron/gates/core/revert.py:147`). So
  a rename that also rewrote the test is not judged against the reverted
  source. Routing such a name into the second subset is a later change.
- **A rename a spec does not declare**. `revert` judges its new name as a
  new test, as at base.
- **Hand edits in the spec's own pull request**. `DESIGN.md` §5.4's
  rename paragraph, under the integrity section, says `census` accepts a
  declared pair. It gains that `revert` reads the same pair. Its
  `revert` paragraph defines the first subset as the new tests. It gains
  that an accepted rename's new name is not one, unless a criterion
  names it. In `docs/agents/issue-tracker.md`'s Conventions, the
  `renames` entry names `revert` beside `census`. One entry says a
  witness must fail with the source reverted. Its bold subset gains
  "minus every accepted rename's new name that no criterion names". `CONTEXT.md`'s **Declared rename** entry stays true as
  written, so it needs no edit.

## Notes for the agent

**Both criteria are new code**, so each declares a witness and no
mutant, and `witness` will report `skip`. The lines a mutant could pin
are the ones this change rewrites, such as the set arithmetic at
`saffron/gates/core/revert.py:262`. The new branch's spelling is yours.

**Copy the rule, do not import it**. `census_gate` computes acceptance
inline (`saffron/gates/core/census.py:78-82`), and `revert.py` already
copies `census`'s `_collected` rather than importing it
(`saffron/gates/core/revert.py:46-52`). `census.py` is `forbidden` here.

**At base each witness fails in its body**. `revert_gate` takes no
`renames` keyword there, so the first witness raises `TypeError`. At
base the suite's `revert` result is `fail` for both declaring specs, so
the second witness fails its first assertion. Neither imports a name the
change adds at module scope. Import `CellSpec` and `parse_spec` inside
the suite witness, as
`test_the_suite_hands_census_the_specs_own_renames` does
(`tests/test_suite.py:576-578`).

**The `revert` witness** uses `_tests` and `_reverted`
(`tests/test_revert.py:12`, `:48`). Give each pair its own names, none a
substring of another's. A check that the summary lacks a name then
means what it says. Hand `run_tests` a recorder that fails every name it
receives, and compare the recorded subset against a literal list. Put the
suffix pair's old name in a second file, such as `u.py::test_india`, with
`t.py::test_india` collected at base and absent at head. For the three
theater calls, hand `run_tests` a fake that passes every name. Assert the
`fail` call's failures as `(file, code)` pairs. In the summary checks,
assert that each left-out name is in the summary, and that each judged
or never-new pair's new name is not.

**The suite witness** needs a tree whose `tests` gate collects one name
on its full suite and passes whatever subset `revert` hands it. Subclass
`_Tree` (`tests/test_suite.py:21`), as `_RewriteTree` does at
`tests/test_suite.py:491`. Declare `tests/**` as the policy's
`test_paths`. Give the head tree a changed source file outside them,
such as `src/a.py`. Without one, `revert` skips before it reads any name. Read the
`revert` result off `comparison.run.results`.

**The keyword defaults to no renames**. Every existing call in
`tests/test_revert.py` and `tests/test_regate.py:366` passes none, and
must keep its verdict.

**The `prose` gate** counts each new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. A docstring line over 88 characters counts as
two toward its ten-line limit, and `revert_gate`'s docstring sits at
nine.

**Size**. A prototype of this change measured 110 counted tokens outside
`tests/` and 439 under it, against the 1300-token `bug` ceiling. That is
138 changed lines in all.
