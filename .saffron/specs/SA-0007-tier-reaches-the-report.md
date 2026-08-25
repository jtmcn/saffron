---
id: SA-0007
title: the effective tier is computed, carried, and then dropped at both call sites
type: bug
priority: 1
depends_on:
  - SA-0005
touches:
  - saffron/cli.py
  - saffron/phases/package.py
  - tests/test_cli.py
  - tests/test_package.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - docs/**
  - saffron/cell/session.py
  - saffron/report/pr_body.py
budget_usd: 8
max_attempts: 4
max_turns: 80
risk: elevated
---

## Context
`SA-0005` (#21) computes the effective risk tier and the advisory-gate set per
attempt and carries both out on `CellOutcome` (`session.py:200-201`).
`render_pr_body` and `QueueLine` both accept them.

Nothing passes them. Both critic lenses filed it, the implementer conceded it,
and both lenses **confirmed** the blocker after the rebuttal — the first
recorded disagreement this pipeline has produced. The cause was that
`SA-0005`'s `touches` did not include the files where the wiring ends, so the
implementer could not have closed it without failing `scope`.

## Problem
Three call sites, one shape — a value that exists, is correct, and is not read.

- `cli.py` never passes `risk=spec.risk` into `CellSpec`, so a spec's declared
  tier never reaches the cell at all and `effective_risk`'s first clause (§5.6:
  *set explicitly in the spec*) can only ever see `"standard"`.
- `package.py:662` calls `render_pr_body` without `effective_risk` or
  `advisory_gates`, so every pull request reports the declared tier and renders
  an advisory failure as a bare `fail`.
- `package.py:775` builds `QueueLine(risk=spec.risk, ...)`, so an auto-elevated
  task sorts as ordinary in the queue an operator scans at 8am (`index.py:67`).

This is the fifth declaration in this repository that parses, validates, and is
never read (BACKLOG item 18). It is filed as a bug rather than a feature
because the capability is built and the wiring is missing.

## Acceptance criteria
- [ ] `cli.py` passes the spec's `risk` into `CellSpec`
- [ ] `package.py` passes `outcome.effective_risk` and `outcome.advisory_gates`
      to `render_pr_body`
- [ ] The queue line's `risk` is the effective tier, not `spec.risk`
- [ ] Each of the three is covered by a test that **exercises the production
      call path** — `cli._run_cell` and `package.package`, with the tier
      arriving from the spec or the outcome rather than being handed in
- [ ] A test that fails if any of the three call sites reverts to `spec.risk`

## Out of scope
`session.py` and `pr_body.py` are **forbidden**: both ends of this wiring are
already correct, and the failure mode of this task is changing the producer to
match a consumer that is not reading it.

## Notes for the agent
The last attempt at this shipped green with the defect intact, and the critic
named why:

> Every test exercising the new behaviour calls `render_pr_body`/`effective_risk`
> directly with hand-supplied values, so the gates pass while the acceptance
> criterion is unmet by the actual pipeline.

A test that constructs the arguments it then asserts on proves the renderer
works. It cannot prove anything about whether the pipeline calls it. That
distinction is the whole task: three call sites, and the assertion belongs at
the caller.

`tests/test_cli.py` already fakes `run_one_cell` and captures the `CellSpec` it
was handed — `_capture_cell_spec` is the shape to follow for the first one.

Commit after each coherent step. Uncommitted work dies with the cell.
