---
id: SA-0044
title: nothing asks whether a new test would fail without the change it ships with
type: feature
priority: 2
depends_on:
  - SA-0043
touches:
  - saffron/gates/core/revert.py
  - saffron/cell/session.py
  - saffron/cell/worktree.py
  - tests/test_revert.py
  - tests/test_session.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/gates/contract.py
  - saffron/gates/runner.py
  - saffron/gates/baseline.py
  - saffron/gates/core/census.py
  - saffron/gates/core/criteria.py
  - saffron/gates/core/scope.py
  - saffron/gates/core/integrity.py
  - saffron/gates/core/size.py
  - saffron/gates/core/committed.py
  - saffron/cell/runtime.py
  - saffron/cell/proxy.py
  - saffron/phases/**
  - saffron/agents/**
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/report/**
  - images/**
acceptance:
  - claim: >-
      A test the diff adds, run with the diff's own source reverted, must not
      pass. One failure per test that did — named, so the operator reads which
      test is theatre rather than that some test is.
    witness: tests/test_revert.py::test_a_new_test_that_passes_without_the_source_is_a_failure
  - claim: >-
      The subset is arithmetic on lists the host already holds — the names
      collected at head minus the names collected at base — and never a second
      enumeration. A `preserves` witness is excluded: it is specified to be
      green on both sides, so requiring it to fail without the source would
      contradict its own declaration.
    witness: tests/test_revert.py::test_the_subset_is_the_new_names_and_excludes_a_preserved_witness
  - claim: >-
      A witness a criterion declares joins the subset, intersected with what
      head actually enumerated. Its own half of the arithmetic, because it is
      reached by the opposite route: a declared witness that already existed at
      base is on both sides, so the difference above never sees it, and a
      witness no runner enumerated at head is `criteria`'s failure to report
      rather than a name this gate may claim ran.
    witness: tests/test_revert.py::test_a_declared_witness_joins_the_subset_even_when_it_existed_at_base
  - claim: >-
      The worktree the other gates measure is the worktree they started with.
      `saffron/cell/worktree.py` restores every path this gate reverted, on the
      failing and erroring paths alike, and a tree it cannot restore is an
      `error` rather than a quietly dirty tree the `committed` gate blames on
      the task.
    witness: tests/test_revert.py::test_the_source_is_restored_when_the_run_raises
  - claim: >-
      Nothing to revert is `skip`, never `pass`. No names at base, a diff that
      adds no test, and a diff with no source side outside the repo's declared
      test paths are three different nothings and none of them is evidence.
    witness: tests/test_revert.py::test_each_kind_of_nothing_to_revert_is_a_skip
  - claim: >-
      `error` is not `fail`. A checkout that did not happen means the gate
      never ran and is charged to nobody; a test that passed without its source
      is the task's own defect.
    witness: tests/test_revert.py::test_a_checkout_that_failed_is_an_error_not_a_failure
  - claim: >-
      The `census` subtraction still runs in its own direction. This gate
      subtracts the same two lists the other way round, and the two must not be
      made to match.
    witness: tests/test_census.py::test_added_tests_alone_pass
    preserves: true
budget_usd: 16
max_attempts: 4
max_turns: 130
risk: elevated
---

## Context
§5.4 calls `revert` *"the anti-theater gate, and the best cost/value ratio in
the system"*: stash the source hunks of the diff, keep the test hunks, run only
the new and changed tests, and require them to fail. One extra test run.

It is specified and unbuilt. `saffron/gates/core/` holds `census`, `committed`,
`criteria`, `integrity`, `scope` and `size`, and no `revert`. Three places in
`DESIGN.md` already point at the hole it leaves:

- §5.4 on `census`: *"a test still collected but gutted belongs to `revert`,
  which is not built yet."*
- §5.4 on `criteria`: a **vacuous** witness — `def test_w(): assert True` —
  *"satisfies everything expressible here. `revert` closes that case; nothing
  here does."*
- §5.4's corollary, which is the cheapest thing in this spec to remember:
  *"if you cannot say what reverting it should break, your acceptance criteria
  are prose."*

**Most of the cost is already paid.** The contract obligation §5.4 calls "the
single most constraining line in the whole contract" is honoured: `run_gate` in
the gate runner takes a `subset` argument and passes it through as argv, and
this repository's own `tests` gate accepts a test subset — its own docstring
says it does so *"from day one"* because the gate that needs it does not exist
yet. Nothing in `saffron/` passes one today; two tests are the only callers.
This spec is the caller.

**What this gate is not.** It would not have caught the defects that motivated
the third critic lens, and the research record says so explicitly: `revert`
asks whether the new tests test *anything*, and that lens asks whether they test
*each thing*. Stashing the source of a spec that adds a module and its tests
together makes every one of those tests fail on the import, and the gate reports
green having learned nothing. It is a floor, not a ceiling — but it is a floor
no diff can walk under, it costs one test run, and it is mechanical where the
lens is a judgement.

## Problem
- **A test that passes on the parent commit ships freely.** Nothing on the host
  asks the question. `census` sees a name that exists, `criteria` sees a witness
  that ran and passed at head, `tests` sees green, `integrity` sees no
  suppression. Every gate agrees, and none of them has looked at whether the
  test is attached to the change.
- **The `criteria` gate's own documented hole has no other closer.** A witness
  absent at base gets *"did not pass at base"* for free, so an empty assertion
  satisfies the whole rule. That is not a defect in `criteria` — its docstring
  states the limit — it is a gate that was specified to close it and never
  built.
- **The one thing it must not break is the tree.** This gate is the first core
  gate that *changes* `/work` rather than reading it. `committed` runs in the
  same suite and fails one path per dirty file, and it would charge the task for
  this gate's leftovers.

## Out of scope
**Hunk-level surgery.** "Stash the source hunks" is achievable at file
granularity: check the changed files that match no declared test path back to
`tree_base`, leave the rest at head. A file that is half test and half source is
a real limit and belongs in a `ponytail:` comment naming it, not in a hunk
splitter written on the first attempt.

**Identifying *changed* tests.** §5.4 says "new and changed". New is a set
difference over names the host already holds. Changed-body-same-name needs a
mapping from diff hunks to test node ids, which is language knowledge §2.1
keeps out of core. Ship the half core can compute, and say in the pull request
body which half you shipped and why the other one is not core's to compute.

**Any change to the gate contract or the gate runner.** Both are `forbidden`.
The `subset` argument already exists and already works; a second path to the
same behaviour is the defect, not the feature.

**`census` and `criteria`.** Both `forbidden`. This gate reads the same
`collected` lists and must not alter how either of them subtracts. Their rules
are deliberately opposite and a spec that makes them match has broken one.

**A repo-side gate.** Core invokes declared gates, never tools. Invoke the
repo's own declared `tests` gate through the runner's existing entry point, and
learn nothing about pytest.

## Notes for the agent
**Do not declare the gate in `ontology/saffron.ttl`.** Adding
`saffron:revert a saffron:CoreGate` there fails
`tests/ontology/test_vocabulary_agrees_with_context.py`, which asserts that
`CONTEXT.md`'s *Core gates* bullet and `saffron:CoreGate` close the set the same
way — measured, one added line, one failure. `CONTEXT.md` is `forbidden` here,
so the two sides cannot be brought back into agreement from inside this task.
The ontology entry and the `CONTEXT.md` bullet are a follow-up the operator
makes together. Leave both alone; nothing fails while neither moves.

> Discharged: PR #112 made the three edits by hand, and Phase A of
> `2026-09-02-ontology-authoritative.md` reduces them to one command plus one —
> a core gate still needs its blocking level in `saffron:CoreGateBlockingShape`,
> which the vocabulary cannot imply and a test refuses to let you forget.

**Take the runner as an argument; do not discover gates.** The supervisor
already holds the discovered gate list and the executor. Hand this gate a
callable that runs the declared test gate over a subset and returns a
`GateResult`, the same shape the phases already take their agent as. Core then
holds no knowledge of which gate fills the role, and every test you write runs
without a container.

**"Passed" is the thing to detect, not "failed".** Reverting the source can make
a test fail, error, or vanish from collection, and all three are acceptable
answers. The defect is a test that *passed*. Compute it the way the `criteria`
gate computes the same predicate — a name that is in `collected` and is not
among the failure codes — so the two gates agree on what passing means. Naming
that symmetry in a comment is worth more than the code it describes.

**`preserves` witnesses must be excluded from the subset.** A criterion marked
`preserves` is specified to be green at base and at head. Requiring it to fail
without the source contradicts its own declaration, and a gate that fails a
correctly-written refactor spec on every attempt will be turned off. This is
the single most likely way to ship this gate broken.

**Restore in a `finally`, and verify.** The gate reverts files in the live
worktree that every later gate then measures. Restore on every path out —
success, failure, exception — and if the tree is not clean afterwards, that is
`error`: infrastructure, aborting the attempt, charged to nobody. A dirty tree
reported as `fail` sends the operator to read a diff that was never the cause.

**You have 600 changed lines, tests included**, and the `size` gate is blocking
at this tier. The gate logic is small; the tests are where the budget goes.
Parametrise the three kinds of nothing rather than writing three near-identical
functions, and drive the gate through its injected runner rather than building
worktrees in a fixture.

**Run the whole suite before you believe a red result.** The format check
rewrites files and then reports failure, so a second run passes.

**Cite code by file and symbol, never by line number**, and do not backtick a
path in an acceptance criterion that this spec's `touches` or `forbidden` does
not cover — gate 0 reads the criteria's own backticked path tokens, treats a
forbidden one as a citation, and refuses on the first token it can match to
neither, reporting only that one.

Commit after each coherent step. Uncommitted work dies with the cell.
