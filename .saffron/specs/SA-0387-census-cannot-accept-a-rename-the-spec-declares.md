---
id: SA-0387
title: "`census` cannot accept a rename the spec declares, so a test keeps a name that states what it no longer tests"
type: feature
priority: 3
risk: elevated
estimated_lines: 211
estimate_measured: true
touches:
  - saffron/gates/core/census.py
  - saffron/gates/suite.py
  - saffron/intake.py
  - saffron/cell/session.py
  - saffron/task.py
  - tests/test_census.py
  - tests/test_suite.py
  - tests/test_constant_mutants.py
  - tests/test_intake.py
  - tests/test_cli.py
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
  - saffron/gates/core/revert.py
  - saffron/gates/core/criteria.py
  - saffron/gates/baseline.py
  - saffron/gates/contract.py
  - saffron/phases/**
  - saffron/regate.py
  - saffron/cli.py
  - saffron/scheduler.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
budget_usd: 48
max_attempts: 3
max_turns: 200
acceptance:
  - claim: >-
      A spec may declare `renames`, a mapping from an old collected test
      name to its new one. It loads as that mapping, every name whole and
      in declared order, and as an empty mapping when omitted. Load
      refuses seven shapes: an empty old name, a blank old name, an empty
      new name, a blank new name, one new name two entries share, a list
      in place of the mapping, and an integer in place of a new name. The
      witness drives the declared mapping, with names holding `::` and
      brackets out of sorted order, the omitted key, and each of the seven
      refused shapes.
    witness: tests/test_intake.py::test_renames_loads_as_a_mapping_and_refuses_a_blank_or_shared_new_name
    wrong_versions:
      - A field with no validator, so two old names sharing one new name load.
      - A blank check on the new name alone, so an empty or blank old name loads.
      - A blank check by emptiness, so an old name of one space loads.
      - A blank check by emptiness on the new name, so a new name of two spaces loads.
      - The mapping sorted at load, so the declared order is lost.
  - claim: >-
      `census_gate` takes the declared renames and accepts a pair only when
      the old name is absent at head, and the new name is collected at head
      and was not collected at base. An accepted pair's old name is no
      failure. Every other name collected at base and absent at head is a
      `removed-test` failure, as at base. A pair whose new name is not
      collected at head is one failure of its own, code
      `rename-not-collected`, whose `file` is the new name and whose
      message names the old one. That failure stands whether or not the
      old name is still collected. Names are compared whole. In one
      `census_gate` call the witness drives seven members: a pair carried
      out, a pair whose new name is absent and whose old name is gone, a
      pair whose new name is absent and whose old name stays, a pair whose
      old name is gone at head and whose new name was already collected at
      base and still is, a pair whose old name stays
      and whose new name is added, a pair whose new name only matches a
      collected name from another file after the last `::`, and one
      undeclared disappearance. It asserts the exact set of `file` and
      `code` pairs, and that each `rename-not-collected` message contains
      its pair's old name. A second call with only the carried-out pair is a
      `pass` with no failures. A third call holds only a pair whose old
      name stays and whose new name is absent, so nothing is removed. It
      is a `fail` with exactly one failure, the new name's
      `rename-not-collected`.
    witness: tests/test_census.py::test_census_accepts_exactly_the_declared_renames_the_head_carried_out
    wrong_versions:
      - Every declared old name accepted whatever head collected, so a deleted test with a declared rename passes.
      - A new name already collected at base accepted, so a deletion is laundered onto an existing test.
      - The missing new name reported under the `removed-test` code.
      - A `rename-not-collected` failure only where the old name is gone, so a pair whose old name stays reports nothing.
      - Names matched on the text after the last `::`, so a new name another file collects is accepted.
      - The renames read but never subtracted, so the carried-out pair still fails `removed-test`.
      - A message that does not name the old name.
      - No failure at all for a missing new name, only the old name's `removed-test`.
      - The `pass` return kept for an empty removed set ahead of the rename check, so a lone missing new name passes.
      - The status set to `fail` only when a name was removed, so a lone `rename-not-collected` failure reads as `pass`.
  - claim: >-
      The gate suite hands `census_gate` the renames of the spec it was
      built with. The witness builds a suite three times over one baseline
      collecting the old name and one head collecting the new name. A
      `CellSpec` declaring the pair and an `intake.Spec` declaring it each
      yield a `census` result of `pass`. A spec declaring no renames yields
      `fail`, with one `removed-test` failure naming the old name.
    witness: tests/test_suite.py::test_the_suite_hands_census_the_specs_own_renames
    wrong_versions:
      - The suite passing an empty mapping, so a declared pair still fails `removed-test`.
  - claim: >-
      `saffron cell` hands the cell the renames its spec declares. The
      witness drives a spec with two pairs, one name holding brackets,
      through `cli._run_cell` and reads them off the `CellSpec` that
      reaches `run_one_cell`.
    witness: tests/test_cli.py::test_a_specs_declared_renames_reach_the_cell
    wrong_versions:
      - The `CellSpec` field added but `run_task` never passing it, so the cell gets an empty mapping.
---

## Context

Backlog item **b-f30189**, filed from the spec loop's run 15. It cites
`DESIGN.md` §5.4. Every line number below was read at `2b093e64`.

**What happened**. `SA-0128` changed the ceilings a parametrised test
drives, and its node ids came from the ceilings. Attempt 1 failed
`census` on three vanished ids, and repair pinned `ids=` to the old
names. So `main-a-bug-300` now drives 1300 (#483). `SA-0126` changed a
test's expected state to `ORPHANED`, and its name still says
`is_not_implemented` (#478). The item's record adds three more cases:
#519 in the spec loop's run 17, #1099 in its run 56, and finish 82.

**What `census` does today**. `census_gate(base, head)`
(`saffron/gates/core/census.py:41`) unions every reported `collected`
list on each side. It subtracts head's set from base's
(`saffron/gates/core/census.py:72`), and reports each leftover name as a
`removed-test` failure (`saffron/gates/core/census.py:86`). Nothing a
spec declares reaches it. A `ponytail:` comment above it says so
(`saffron/gates/core/census.py:34-38`). It names a spec field as the
upgrade path, unbuilt because no task had needed one.

**How a spec reaches the gate**. `GateSuite._run` calls
`census_gate(prior, results)` last but one
(`saffron/gates/suite.py:231`). The suite reads its spec through the
`SuiteSpec` protocol (`saffron/gates/suite.py:40-52`). Two types fill it
in production. `_drive_cell` hands `GateSuite` the cell's own spec
(`saffron/cell/session.py:2478`), a `CellSpec`. `run_task` builds that
`CellSpec` field by field from the `intake.Spec`
(`saffron/task.py:862-881`).
`reverify` builds it from an `intake.Spec` directly
(`saffron/phases/package.py:533` and `:559`). `saffron package`, the
finishing layer and `saffron regate` all reach `reverify`
(`saffron/cli.py:1159`, `saffron/regate.py:180`). So a field on
`intake.Spec`, a field on `CellSpec`, one argument in `run_task` and one
protocol property reach every suite. No call site outside `touches`
changes.

**The test fakes**. `tests/test_suite.py:101` and
`tests/test_constant_mutants.py:90` each define a frozen `_Spec`
dataclass the suite reads. `tests/test_session.py:445` and `:510` import
the first. Each needs a `renames` field defaulting to an empty mapping,
or every suite those files build raises on the new read.

**Where the field sits**. `intake.Spec` refuses an unknown key
(`saffron/intake.py:234`). `removes` is the nearest sibling
(`saffron/intake.py:250`), with its validator at
`saffron/intake.py:305`. `CellSpec` keeps the spec's own fields beside
`history` (`saffron/cell/session.py:374`).

## Problem

Add `renames` to `intake.Spec`: a mapping from an old collected test
name to its new one, empty by default. Each name is an opaque string,
exactly as the runner reports it. Never split or parse one, which is
the rule census's module docstring states
(`saffron/gates/core/census.py:9-12`). Refuse a blank name and a new
name two entries share.

Add the same field to `CellSpec`, pass it in `run_task`, add it to
`SuiteSpec`, and pass `spec.renames` to `census_gate` as a keyword. That
keyword defaults to no renames.

In `census_gate`, accept a pair only when its old name is absent at
head. Its new name must also be collected at head and absent at base. An
accepted pair's old name leaves the removed set. Every other removed
name stays a `removed-test` failure. A pair whose new name is not
collected at head adds one failure with code `rename-not-collected`. Its
`file` is the new name, and its message names the old one. The two
asymmetric cases stay as they are: no names at base is `skip`, and
names at base with none at head is `error`.

Delete the `ponytail:` comment at `saffron/gates/core/census.py:34-38`,
which this change makes false. Update `census_gate`'s docstring to name
the renames.

## Out of scope

- **What this fixes, and what it leaves**. The item's record names five
  recurrences. `census` now accepts a declared rename in #478, #483 and
  #519. In #478 and #483 each renamed test asserts what the change made
  true, so it also fails without the diff's source. #519 ended with an
  id-only rename. `census` accepts it, and `revert` still refuses it
  wherever its test passes without the source.
  This change does not fix #1099. `revert` treats a name collected at
  head and not at base as a new test
  (`saffron/gates/core/revert.py:261`), and no `renames` reaches it. So
  a renamed test that passes without the diff's source is still refused
  there, as #1099's was. It does not fix finish 82 either. The finishing layer's suite runs under the synthetic
  `FINISH-0` spec (`saffron/finish.py:110-115`), which declares no
  renames.
- **A rename a spec does not declare**. It fails `census` as before. The
  host cannot tell a rename from a deletion and an addition.
- **A pair whose old name equals its new name**. It loads. It can never
  be accepted, since its old name cannot be absent where its new name is
  collected. It reports `rename-not-collected` only when the name is gone.
- **Two entries with one old name**. `yaml.safe_load` keeps the last of
  two duplicate mapping keys and drops the first without an error. So
  load never sees the first entry, and nothing refuses it.
- **Hand edits in the spec's own pull request**. `DESIGN.md` §5.4 says a
  rename the spec declares is accepted pair by pair, never as a
  deletion. Its definition of a removed test ends "unless the spec
  declares it renamed". `docs/agents/issue-tracker.md` holds a `renames`
  entry beside `removes`. `CONTEXT.md` gets its entry by hand under
  b-1b5747.

## Notes for the agent

**Every criterion is new code**, so each declares a witness and no
mutant, and `witness` will report `skip`. The change edits
`census_gate`, but the lines a mutant could pin there are the ones the
change rewrites, such as the subtraction at
`saffron/gates/core/census.py:72`. The new branch's spelling is yours.

**`saffron batch` shares the `saffron cell` path**. Both reach the one
`CellSpec(...)` call in `run_task` (`saffron/task.py:862`). The fourth
witness drives `saffron cell` alone.

**At base each witness fails in its body**. None imports a name the
change adds at module scope. Load refuses the unknown key, so a spec
declaring `renames` raises `SpecError` at base. `census_gate` takes no
`renames` keyword there, and `CellSpec` takes no `renames` field.
Import `CellSpec` and `parse_spec` inside the suite witness, as
`tests/test_session.py:445` imports from `tests.test_suite`.

**The census witness** uses `_tests` (`tests/test_census.py:7`). Compare
`sorted((f.file, f.code) for f in result.failures)` against a literal
list, so the order the gate reports in is not pinned. Give each pair its
own names, none a substring of another's, and put the sibling-suffix
pair's collected name in a second file, such as `other.py`. In the pair
whose new name was already collected at base, drop the old name from
head. With the old name still collected, that member tells no build
apart. The third call holds no removed name at all, so a build that
returns `pass` whenever nothing was removed fails it. Also assert that
each `rename-not-collected` failure's `message` contains its pair's old
name, in the first call and the third. One member keeps its old name and
adds its new one. It emits no failure under any build the spec names,
since an old name still collected was never removed. It pins that no
extra failure appears, and it tells no build apart.

**The suite witness** needs a tree whose `tests` gate collects one list
on its full suite and echoes the subset `revert` hands it. Subclass
`_Tree` (`tests/test_suite.py:21`), as `_RewriteTree` does at
`tests/test_suite.py:490`. Read the `census` result off
`comparison.run.results`, not `new_failures`, so `revert`'s own verdict
on the new name cannot mask it.

**The `saffron cell` witness** copies
`test_a_specs_declared_risk_reaches_the_cell`
(`tests/test_cli.py:695`). `_ceiling_spec` (`tests/test_cli.py:615`)
writes each keyword as one frontmatter line, so pass the mapping in YAML
flow style with every name quoted.

**The keyword defaults to no renames**. `tests/test_session.py:5169`
calls `census_gate(base=[], head=[])` with no third argument, and that
file lies outside `touches`. A default also leaves every existing call in
`tests/test_census.py` as it is.
`test_a_test_renamed_out_of_collection_is_a_removal` must keep failing a
rename the spec does not declare.

**The `prose` gate** counts each new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words.

**Size**. A prototype of this change measured 323 counted tokens outside
`tests/` and 521 under it, against the 3000-token `feature` ceiling.
That is 211 changed lines in all.
