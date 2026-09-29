---
id: b-66d1c3
title: A stack's new lens or REVIEW phase runs in none of its own cells, since REVIEW runs from the host's `main`
status: open
tier: 2
filed: 2026-09-29
closed:
specs: []
prs: []
commits: []
cites: [§5.5, §5.6]
related: [b-abeb74, b-ab4b33, b-cd5fd2, b-78ccc7]
---

## Problem

Found in the spec loop's run 21, 2026-09-29.

Lenses, REBUT and the probe sessions run from the host's checkout of `main`.
A stacked child's REVIEW therefore runs the phases its parents replaced.

- `SA-0191` (#580) added the conventions lens. `SA-0191` and `SA-0192` each
  ran three lenses. The new lens ran live in no cell.
- `SA-0192`'s REBUT ran without `SA-0188`'s `contradicted` verdict. It
  withdrew a real `preserves` blocker (item b-cd5fd2).
- The handoff raised `SA-0192`'s budget to $26 for a four-lens REVIEW that
  never happened. It cost $7.16.

ADR 8 needs a live run of the conventions lens as evidence. A spec loop that
budgets a child for its parent's phases prices the wrong REVIEW.

## Done looks like

The loop says which REVIEW a stacked child gets. Either the host runs REVIEW
from the child's parent, or `check` prices a child for `main`'s phases and
says so. The loop's report names the lens set each REVIEW ran.

## Record

- 2026-09-29: filed from the spec loop's run 21.
