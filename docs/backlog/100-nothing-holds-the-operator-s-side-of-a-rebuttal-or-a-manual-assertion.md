---
id: 100
title: Nothing holds the operator's side of a rebuttal, or a manual assertion, to the operator
status: open
tier: 3
specs: []
prs: []
commits: []
cites: []
related: []
---

## Problem

**Tier 3.** Found reviewing PR #189. `RebuttalShape` puts the implementer's
association on an `ImplementerSession` and the critic's on a `CriticLens`, and says
nothing of the third: a rebuttal whose `agrees` association names a
`factory:Delegate` conforms. An `earl:Assertion` in `earl:manual` mode — the
operator's rejection in `lifecycle.ttl` — may likewise be `earl:assertedBy` a
delegate. `CONTEXT.md`'s **Delegate** entry says a judgement a delegate types is
still the operator's; only ratification (`TouchesShape`) holds that in a shape.

## Done looks like

a third qualified association in `RebuttalShape` — at most one,
role in `( factory:agrees factory:disagrees )`, agent `sh:class factory:Operator` —
and a shape putting a manual assertion's `earl:assertedBy` on the operator, each
with a negative fixture naming a delegate.
