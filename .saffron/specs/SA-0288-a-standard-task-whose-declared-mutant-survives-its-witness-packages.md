---
id: SA-0288
title: A `standard` task whose declared mutant survives its witness goes `READY_FOR_REVIEW`, because the gate suite holds `witness` advisory below `elevated`
type: bug
priority: 2
depends_on: [SA-0283, SA-0282, SA-0281, SA-0280]
estimated_lines: 210
estimate_measured: true
touches:
  - saffron/gates/suite.py
  - saffron/gates/contract.py
  - saffron/gates/core/witness.py
  - saffron/report/pr_body.py
  - saffron/agents/prompts/spec-writer.md
  - saffron/agents/prompts/spec-review.md
  - tests/test_session.py
  - tests/test_suite.py
  - tests/test_gates.py
  - tests/test_witness_gate.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - .github/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/gates/baseline.py
  - saffron/gates/runner.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/task.py
  - saffron/intake.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 24
max_attempts: 3
max_turns: 140
acceptance:
  - claim: >-
      A task whose declared mutant survives its witness never goes
      `READY_FOR_REVIEW`, at any risk tier. The witness drives three tiers
      through a whole cell: a declared `standard`, a declared `elevated`,
      and a `standard` spec that an `elevate_on` path elevates. Each runs
      the real `witness` gate under the real suite's advisory set. Each
      ends `EXHAUSTED` with the survivor among its new failures, and
      `witness` absent from its advisory gates.
    witness: tests/test_session.py::test_a_task_whose_declared_mutant_survives_its_witness_never_reaches_review
    mutant:
      file: saffron/gates/suite.py
      find: advisory.add("size")
      replace: advisory.add("size"); advisory.add("witness")
    wrong_versions:
      - The advisory set still adds `witness` at `standard`, so the standard leg ends `READY_FOR_REVIEW`.
      - The advisory set adds `witness` at `elevated` only, the inverse of the old rule, so the elevated legs end `READY_FOR_REVIEW`.
      - The repair decision treats a `witness` failure as blocking while the advisory set still lists `witness`, so the outcome's advisory gates name it.
      - The survivor ends the attempt as an `error` rather than a `fail`, so the outcome carries no `survived-mutant` new failure.
      - A canned `witness` result stands in for the gate, so no mutant is applied and the witness subset is never run.
---

## Context

Backlog item **b-02d328**, which cites `DESIGN.md` §5.4. Line numbers below
were read at `cf3db797`.

**Measured on `SA-0267`** (#846), from the item. Its criterion 1 declared a
mutant on `saffron/scheduler.py`
(`.saffron/specs/done/SA-0267-a-stack-order-refuses-a-parent-that-is-an-earlier-batchs-open-pull-request.md:58-61`).
The spec was `risk: standard` (same file, line 44), and its two touches match no
`elevate_on` path. The `witness` gate reported `fail`, "1 of 2 witness(es)
survived their own mutant", on attempt 1 and after the rebuttal. The task
still went `READY_FOR_REVIEW`. The Spec seat found the hole by running the
same mutant by hand.

**Where the level is decided.** `_advisory` builds each run's advisory set
(`saffron/gates/suite.py:226-234`). A gate declared `blocking: false` joins
it at every tier. `size` joins it unless `size_blocks` says the tier blocks
(`:230-231`). `witness` joins it when `witness_blocking` returns false
(`:232-233`). That function returns `tier == "elevated"`
(`saffron/gates/contract.py:112-136`). Nothing else calls it
(`git grep witness_blocking` finds `saffron/gates/suite.py:21` and
`saffron/gates/suite.py:232`, and `tests/test_gates.py:15` and
`tests/test_gates.py:81-82`). `_compare` keeps a failure in an
advisory gate out of `new_failures` (`saffron/gates/suite.py:237-253`), so
it never blocks.

**The survivor itself.** `witness_gate` files one `survived-mutant` failure
per surviving witness (`saffron/gates/core/witness.py:250-263`). The
baseline never cancels one (`saffron/gates/baseline.py:25-32`). So a
survivor present at base is still new at head.

**What this commit already landed by hand.** `DESIGN.md` §5.4.1's
*Blocking level* now says `witness` blocks at every tier.
`ontology/factory.ttl` declares `witness` at `alwaysBlocking`.
`ontology/shapes/factory-shapes.ttl` lists `witness` in
`CoreGateBlockingShape`, and `SizeTierShape` targets `size` alone.
`CONTEXT.md`'s *Risk tier* and *Gate* entries and ADR 3's *Consequences*
say the same. No test reads the code's level against the vocabulary, so
`make check` stays green with the code unchanged. The code is this task's.

## Problem

`witness` is advisory at `standard`. A spec's own declared mutant can
survive its witness, and the task packages as reviewable anyway. The
operator chose the first arm of the item's *Done looks like*. A survivor
blocks at every tier, as `scope` and `revert` do. REBUT routing is not this
spec.

1. **The level.** `_advisory` stops adding `witness`. Its docstring says
   a `blocking: false` gate is advisory at every tier, `size` is advisory
   below `elevated`, and `witness` is advisory at no tier.
2. **The dead function.** Delete `witness_blocking` from
   `saffron/gates/contract.py`, with the import in `suite.py` and each
   import the deletion leaves unused. A function returning true at both
   tiers would leave `_advisory` a branch that never runs. The notes say
   why its docstring's caveat needs no new home.
3. **The prose that turns false.** Two prompts, two docstrings and one
   comment say `witness` blocks only at `elevated`. The notes list each one.
4. **The existing assertions.** Seven tests pin the old level. The notes
   list each and what it asserts now. Every one keeps its name.

## Out of scope

- **REBUT routing.** A surviving criterion probe or wrong version already
  reaches REBUT at every tier (ADR 3). Nothing here changes `review.py`
  or `rebut.py`.
- **`size`.** Its level and `size_blocks` stay as they are.
- **Constant mutants.** `SA-0280` derives them in the same gate. Once both
  land, a constant-mutant survivor blocks at `standard` too, a false one
  included. This spec makes no exception for them.
- **Queued specs with declared mutants.** `SA-0270`, `SA-0271`, `SA-0276`,
  `SA-0277` and `SA-0282` are `standard` and declare mutants. Once this
  lands, each can end `EXHAUSTED` on a survivor. All but `SA-0277` touch
  `saffron/cell/**`, so a diff that edits those paths already blocked there.
- **The `witness` gate's own answers.** One comment in `witness.py`
  changes and nothing else does. Its inner-`error` trap stays as its
  `ponytail:` comment records (`saffron/gates/core/witness.py:224-233`).
- **The vocabulary and the design record.** This commit landed them.

## Notes for the agent

**An edit, so the criterion declares a mutant.** The change removes code
that exists. The mutant puts `witness` back into the advisory set beside
`size`, on a line the change keeps.

**Why deletion and not a constant `True`.** The `dead` gate's vulture scan
reads names, not branches. So a `witness_blocking` returning true at both
tiers would pass it, and `_advisory`'s `if not ...` would never run. The
docstring's caveat about an inner `error` already lives in the
`ponytail:` comment at `saffron/gates/core/witness.py:224-233`. So
deleting the function loses no record. An inner `error` already aborts the
attempt at every tier, since `_compare` checks `aborted_gates` before the
advisory split (`saffron/gates/suite.py:238-239`). `tests/test_artifacts.py:344` already calls `suite._advisory`
directly, which is the precedent for item 4's `test_gates.py` body.

**Criterion 1's witness.** Write it in `tests/test_session.py`, after
`test_a_skipped_witness_blocks_nothing_at_either_tier` (`:9696`). Take that
test's shape. Replace `saffron.gates.runner.run_suite` with a function
returning one real `witness_gate` result over the `acceptance` and
`mutate` it receives. Its `run_tests` records each subset and returns a
`tests` result at `pass`, so the witness survives. Declare one criterion
with a mutant on `src/x.py`. `_stub_the_runtime`'s own
`worktree.source_mutated` yields a reason, so the gate would `skip`
(`tests/test_session.py:1185-1195`). After `_stub_the_runtime`, patch
`saffron.cell.worktree.source_mutated` with a context manager that records
the mutant and yields `None`. Drive three legs, each with `max_attempts=1`
so the first suite decides:

- `risk="standard"`, policy `gates: {}`.
- `risk="elevated"`, policy `gates: {}`.
- `risk="standard"`, with `elevate_on` naming `src/**`.

Record per suite call. The replaced `run_suite` opens a new frame on each
call. `run_tests` appends its subset to the open frame, and the patched
`source_mutated` appends its mutant there. Each leg asserts `effective_risk`,
then `state == "EXHAUSTED"`. It asserts `witness` is not in
`advisory_gates`. The `(gate, file, code)` of the new failures is exactly
the witness's one `survived-mutant`. The last frame, the head suite's, is
exactly one subset holding the witness alone and one mutant equal to the
criterion's. An empty frame fails that, so a canned `witness` result fails
the witness. The standard leg fails at `cf3db797`, which is what `revert`
needs.

**Item 4, the seven tests.** A renamed test reads to `census` as a removed
one, and the gate has no override. Its `ponytail:` comment says so
(`saffron/gates/core/census.py:34-38`). So each test below keeps its name,
and its docstring or a comment says the name predates this change.

- `test_witness_is_advisory_at_standard_and_blocking_when_elevated`
  (`tests/test_gates.py:80`) asserts `witness` is absent from
  `suite._advisory` at both tiers, under `Policy(gates={})`. The module
  docstring stops naming the deleted function (`tests/test_gates.py:6-8`).
- `test_at_standard_size_and_witness_are_advisory`
  (`tests/test_suite.py:172`) expects the advisory set at `standard` to be
  `size` alone.
- `test_a_witness_left_unstrengthened_blocks_when_elevated_and_a_killed_mutant_reports_nothing`
  (`tests/test_suite.py:269`). Its declared-`standard` leg
  (`tests/test_suite.py:316-319`) expects the one blocking survivor the
  elevated legs expect.
- `test_a_new_failure_in_an_advisory_gate_is_carried_apart_and_blocks_nothing`
  (`tests/test_suite.py:326`). Its leg 4 (`tests/test_suite.py:404-427`)
  expects that survivor in `new_failures`, with `advisory_failures` empty.
  The docstring stops counting three ways a gate is held advisory.
- `test_a_size_failure_at_standard_does_not_enter_the_repair_loop`
  (`tests/test_session.py:3681`) expects `size` alone as its advisory gates
  (`tests/test_session.py:3709-3711`).
- `test_a_declared_gate_with_blocking_false_does_not_repair`
  (`tests/test_session.py:3859`) expects `lint` and `size`
  (`tests/test_session.py:3884-3887`).
- `test_a_witness_failure_is_advisory_at_standard_and_blocking_when_elevated`
  (`tests/test_session.py:9642`). Its standard leg expects `EXHAUSTED`. Its
  docstring and its comment (`tests/test_session.py:9658-9662`) stop naming
  the deleted function.

**Item 3, the prose.** `saffron/report/pr_body.py:280-282` names `witness`
among gates advisory at `standard`. `saffron/agents/prompts/spec-writer.md:27-29`
and `saffron/agents/prompts/spec-review.md:35-37` tie the witness gate to
`risk: elevated`. `tests/test_witness_gate.py:531-535` says item 71 made
`witness` advisory below `elevated`. The comment at
`saffron/gates/core/witness.py:251-252` says the survivor's message
reaches REPAIR at `elevated`. Each says instead that `witness`
blocks at every tier. The `prose` gate counts new hits per file, so a
rewritten sentence takes no em dash and stays under 25 words.

**Your own task is `elevated`.** `elevate_on` lists `saffron/gates/**`
(`.saffron/policy.yaml:34`), so `size` blocks on this diff.

**Measured on a prototype over `cf3db797`.** The whole change came to 837
changed tokens by the `size` gate's counter, against the `bug` ceiling of
1300. That is 64%. The count includes the three-leg witness with its
per-call frames. It also includes the seven edited tests, the prose edits
and the code. `make check` passed on an
earlier cut. The final cut passed ruff, the `prose` limit and every test
module it edits. The witness failed with the source reverted, on its
standard leg. The mutant and wrong versions 1, 2 and 5, applied as edits,
each failed it. Version 5 ran as a suite that hands the gate no criteria
and puts a canned survivor in its place.

Commit after the witness passes. Uncommitted work dies with the cell.
