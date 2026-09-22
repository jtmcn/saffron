---
id: b-e1afbb
title: Work larger than one cell has no unit in Saffron, and no review reads its parts together
status: open
filed: 2026-09-21
specs: []
prs: []
commits: []
cites: [§3, §5.5]
related: [25, 56, b-602d00, b-3732ef]
---

## Problem

Filed 2026-09-21 from a comparison of Saffron with the superpowers
spec, plan and execute skills.

**A spec is the only unit.** One spec runs in one cell and ships as one pull
request under the `size` ceiling (§3, §5.4). A feature needing several
dependent changes has no record that holds all of them. `depends_on` links two
specs, and nothing states the design they share, their order, or the values
every part must match.

**So large work is sequenced outside Saffron.** `docs/superpowers/plans/`
holds 25 plans, and those with tasks carry 3 to 13 of them. 21 use the
superpowers subagent executor, which runs no task in a cell.
`2026-09-04-batch-orchestration.md` ran each task as a spec through
`saffron cell`, sequenced by the operator.

**No review sees the seam between parts.** Each critic reads one task's diff
(§5.5). Principle 40 states the gap: a reviewer scoped to one task cannot see
the seam between two. The superpowers executor closes it with one review of
the whole branch after the last task, on the strongest model, and one fix
wave.

## Done looks like

An ADR decides the shape. A spec then declares member specs, their order, and
constraints every member inherits. Once the last member reaches
`READY_FOR_REVIEW`, one review runs in a critic cell. It checks the joins
between members.

## Record

- 2026-09-21: filed. The ADR is `protected` and written by hand. The
  scheduler and review changes after it can go through cells.
