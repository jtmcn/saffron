---
id: SA-0002
title: The size core gate is specified but not implemented
type: feature
priority: 2
touches:
  - saffron/gates/core/size.py
  - tests/test_size.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
budget_usd: 8
max_attempts: 4
risk: standard
---

## Context
`DESIGN.md` §5.4 lists four core gates: `scope`, `size`, `secrets`, `integrity`.
v0 implemented `scope` only. `size` is the next one and the simplest — it reads
the diff as text and never executes repo code, which is why it can be core.

## Problem
There is no `size` gate. A diff of any length passes unremarked, and the
`elevated` risk tier has nothing to make blocking.

## Acceptance criteria
- [ ] A regression test exists that fails without `saffron/gates/core/size.py`
- [ ] `size` returns a `GateResult` satisfying the contract, including `tool`
- [ ] The ceiling is chosen by spec type: bug 300, feature 600, refactor 1000
- [ ] Lines are counted from the diff, added plus removed
- [ ] A diff at exactly the ceiling passes; one line over fails
- [ ] The result is `pass`/`fail` only — `size` never returns `error` for a
      diff it could read

## Out of scope
Making `size` blocking at `elevated`. The risk tier has no consumer until v1,
and wiring one is a separate spec. The `secrets` and `integrity` gates.

## Notes for the agent
`saffron/gates/core/scope.py` is the pattern to follow — same shape, same
contract, same test style. `tool` for a core gate is Saffron's own version;
there is no external tool to interrogate.
