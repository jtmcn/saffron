---
id: SA-0005
title: size is built and nothing calls it, because no risk tier reaches the loop
type: feature
priority: 1
touches:
  - saffron/cell/session.py
  - saffron/repos/policy.py
  - saffron/report/pr_body.py
  - tests/test_session.py
  - tests/test_policy.py
  - tests/test_report.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - docs/**
  - saffron/gates/core/size.py
budget_usd: 12
max_attempts: 4
max_turns: 100
risk: elevated
---

## Context
`SA-0002` built the `size` gate and its spec put the consumer out of scope, on
the correct reasoning that the risk tier has none until v1. So
`saffron/gates/core/size.py` is present, tested, reviewed — and unreachable:
`session.py`'s `_suite` builds its core-gate list from `scope`, `integrity`,
`committed` and `census`.

Two declarations the wiring needs **already exist and have no reader**:
`Policy.elevate_on` (`saffron/repos/policy.py:51`, and this repo's
`.saffron/policy.yaml` already lists three patterns) and
`GateDeclaration.blocking` (`:29`). Both are parsed, validated and tested at the
policy layer, and nothing downstream looks at either. This task is mostly
*reading declarations that are already there*.

§5.6: `risk: elevated` is set explicitly in the spec **or** auto-elevated when
the diff touches any `elevate_on` path, and it makes `size` blocking. §5.4:
`size` is advisory at `standard`. There is no advisory result today — the repair
loop treats every `fail` as work to be done.

## Problem
A gate nothing calls is not a gate. And the loop cannot be handed one, because
`repair_loop` acts on every new failure `subtract_baseline` returns, which would
make `size` blocking at every tier — the exact contradiction Appendix B caught
in §5.4 and §5.6 disagreeing.

## Acceptance criteria
- [ ] An effective risk tier is computed once per attempt: `elevated` when the
      spec says so, or when any changed path matches a `policy.elevate_on`
      pattern. It is derived from the same changed-file list `_suite` already
      builds, never from a second read
- [ ] `size` runs in `_suite` beside `scope` and `integrity`, host-side, and its
      result appears in every gate result set and in the PR body's gate table
- [ ] A `size` failure at `standard` does **not** enter the repair loop's new
      failures; at `elevated` it does
- [ ] A declared gate with `blocking: false` behaves the same way at every tier
      — reported, never repaired
- [ ] An advisory failure is visibly marked as advisory wherever it is rendered,
      so a red row on a green pull request is not read as a contradiction
- [ ] The effective tier, not `spec.risk`, is what the PR body header and the
      queue line report
- [ ] A test for each of: an `elevate_on` match elevating a `standard` spec, a
      `size` fail not repairing at `standard`, the same fail repairing at
      `elevated`, and a `blocking: false` declared gate not repairing

## Out of scope
`saffron/gates/core/size.py` is **forbidden**, deliberately: the cheapest way to
make a blocking gate stop blocking is to weaken the gate, and this task is the
wiring. The gate's own `-diff` hole is `SA-0006`. The third lens (blast radius
or coverage) needs the tier this task delivers and is its own spec.

## Notes for the agent
`scope.matches(path, pattern)` is this repo's glob matcher — `fnmatch` lets `*`
cross a `/` and `PurePath.full_match` needs 3.13, so do not reach for either.

**Do not declare `size` in `policy.yaml`.** It leaves `tool` unset, which is
right for a gate that executes nothing, and `runner.run_gate` converts a
declared gate's `pass`/`fail` with no `tool` into `error` — declaring it would
error every task. Core gates are prepended host-side; that is what `_suite` is.

Advisory is a property of *this attempt's* gate, not of the failure: the same
`size` failure is advisory at `standard` and blocking at `elevated`, so it does
not belong in `Failure`. `subtract_baseline`'s counting is not yours to touch.

Commit after each coherent step. A previous run of this spec did 61 turns of
correct work and exported nothing, because it was holding all of it uncommitted
when its turn ceiling fired.
