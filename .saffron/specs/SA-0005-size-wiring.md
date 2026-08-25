---
id: SA-0005
title: size is built and nothing calls it, because no risk tier reaches the loop
type: feature
priority: 1
touches:
  - saffron/cell/session.py
  - saffron/repos/policy.py
  - saffron/gates/core/size.py
  - saffron/report/pr_body.py
  - tests/test_session.py
  - tests/test_policy.py
  - tests/test_size.py
  - tests/test_report.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - docs/**
budget_usd: 12
max_attempts: 4
risk: elevated
---

## Context
`SA-0002` built the `size` gate and its spec put the consumer out of scope, so
`saffron/gates/core/size.py` is present, tested, reviewed — and unreachable.
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
- [ ] `size` returns `error` for a diff carrying a `Binary files ... differ`
      section for a file inside `touches`, matching what `integrity` already
      does with an unreadable section — a `-diff` gitattribute otherwise counts
      0 lines and zeroes the gate at the one tier where it blocks
- [ ] A test for each of: an `elevate_on` match elevating a `standard` spec, a
      `size` fail not repairing at `standard`, the same fail repairing at
      `elevated`, and a `blocking: false` declared gate not repairing

## Out of scope
The third lens (blast radius or coverage) — it needs the tier this task
delivers, and it is its own spec. The `--numstat` cross-check as a second
opinion on the line count: the `touches` rule above closes the escape this
gate can actually be gamed with, and numstat means a second git call in the
cell for a diff the host already holds.

## Notes for the agent
`scope.matches(path, pattern)` is this repo's glob matcher — `fnmatch` lets `*`
cross a `/` and `PurePath.full_match` needs 3.13, so do not reach for either.

**Do not declare `size` in `policy.yaml`.** It leaves `tool` unset, which is
right for a gate that executes nothing, and `runner.run_gate` converts a
declared gate's `pass`/`fail` with no `tool` into `error` — declaring it would
error every task. Core gates are prepended host-side; that is what `_suite` is.

`integrity` already carries the unreadable-section rule the last criterion
asks for. Read it before writing a second one, and make the two agree.

Advisory is a property of *this attempt's* gate, not of the failure: the same
`size` failure is advisory at `standard` and blocking at `elevated`, so it does
not belong in `Failure`. `subtract_baseline`'s counting is not yours to touch.
