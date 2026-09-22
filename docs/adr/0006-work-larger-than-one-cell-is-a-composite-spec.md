---
id: 6
title: "Work larger than one cell is a composite spec, reviewed once at the joins"
status: accepted
date: 2026-09-21
supersedes: []
superseded_by: []
appendices: [A, C, D, E, F, I, K, L]
principles: [2, 4, 12, 17, 25, 26, 29, 38, 40, 45, 49, 50]
---

## Context

A spec runs in one cell and ships as one pull request. The `size` gate bounds
its diff, blocking at `elevated` (§5.4). A feature needing several dependent
changes has no record in Saffron. `depends_on` links two specs and stacks the
child on its parent's branch (§4.2). Nothing holds the design the parts share,
their order, or the values every part must match.

So large work is sequenced outside the factory. `docs/superpowers/plans/`
holds 25 plans. 21 of them use the superpowers subagent executor, which runs
each task outside any cell. `2026-09-04-batch-orchestration.md` did the other
thing. Each of its tasks was a spec run through `saffron cell`, sequenced by
the operator under one "Global Constraints" block. That plan is the pattern
this ADR records. Backlog item b-e1afbb records the gap.

Each critic reads one task's diff (§5.5). Appendix I found both Criticals of
the v0.5 build "in the wiring between tasks", and only the whole-branch pass
found them. It asked for at least one review scoped to the joins.

## Decision

A **composite spec** declares an ordered list of **member specs** and the
constraints every member inherits. It carries no criteria of its own. Its
members live in its repo, because dependencies do not cross repos (§4.2).

**The members stack.** Each member after the first names the member before it
in `depends_on`, so they schedule as §4.2 already describes. The composite's
list is authoritative. A member whose `depends_on` disagrees with it is
refused at gate 0 (§4.2.1).

**One composite review reads the joins.** It runs once the last member reaches
`READY_FOR_REVIEW`, in a critic cell (§5.5). Its rubric has three parts:

- each name one member uses from another, against the member that produces it.
- each name a member produces that no later member uses.
- work a member redoes when an earlier member already provides it.

It also checks the composite's constraints across all members. A member's own
criteria stay with that member's critic.

**It reads the tree the last member's critic read.** That tree is the last
member's tree base with its patch applied. It already carries every member
before the last. The tree that merges can still differ, and §6.1's merge
train covers that. A change to any member voids the review until every member
after it is rebuilt on the change.

**The operator writes any new member spec**, because an agent writing its own
specs is a non-goal (§1.4).

## Options considered

- **Keep sequencing large work outside Saffron.** Under the subagent
  executor, the implementer reports its own tests, and no host gate executes
  them. Sequenced through `saffron cell` by hand, each part is gated, and
  nothing reads the joins or holds the constraints.
- **Raise the `size` ceiling.** One cell would carry the whole feature. The
  ceiling keeps each pull request small enough for the operator to review, and
  this removes it.
- **A composite spec (chosen).** The operator still reviews each member's pull
  request, each under its own ceiling. The composite review reads the joins
  across them.

## Principles

- **2** upholds. It holds for the first run only. The composite review runs
  at `READY_FOR_REVIEW`, not `MERGED`. It holds once something inside the batch
  runs the review, which the spec decides. A re-run after a void waits on the
  later members being rebuilt, and today only the operator re-queues them.
- **4** upholds. The review runs in a critic cell, never in a member's
  implementer cell.
- **12** upholds. The decision adds a spec kind and one review over its
  members. 25 plans show the need, so neither is built ahead of its use.
- **17** upholds. A member whose `depends_on` disagrees with the composite is
  refused at gate 0, before its cell spends.
- **25** upholds. "Composite spec", "member spec" and "composite review" enter
  through `ontology/factory.ttl`, so the vocabulary tests read them.
- **26** upholds. "Parent" keeps its one referent, a stacked task's
  `depends_on[0]`. The composite is never called a parent.
- **29** upholds. The `size` ceiling guards the operator's review of one pull
  request. Each member still meets it. The composite review asks no person to
  read the combined diff, so it is no exception to the ceiling's reason.
- **38** upholds. The review reads the tree the last member's critic read, not
  a tree assembled for the review.
- **40** upholds. It is the reason for the decision. The rubric reads the
  joins, which no member's critic can see. It covers both shapes Appendix I
  found: a name produced and never called, and a second implementation of
  work another part already did.
- **45** upholds. It is one reason the superpowers executor is rejected. Its
  implementer writes the tests and reports them, which certifies agreement.
- **49** upholds. It is the other reason. The executor's implementer runs its
  own checks before reporting, so they have already passed.
- **50** departs. At the joins the critic is the only full reader. Before this
  decision nobody read the joins together, so it adds a critic and removes no
  reader. The residual is that nothing asks the operator to read a join. A
  join defect the critic misses has no second reader.

## Consequences

`CONTEXT.md` gains the three terms above. Its definitions of "critic cell" and
"queue line" widen to cover a review with no implementer of its own.

The spec schema gains the composite's fields. Per §3.2, the spec that adds
them cannot use them, so it ships with a fixture.

These are left to the spec that builds the composite review:

- what runs it: a task of its own, a phase of the last member's task, or a
  batch step. The items below assume that owner.
- what counts as a change to a member, including a fixup the operator pushes
  by hand, and what rebuilds the members after it.
- its budget, and how admission checks it, given that REVIEW spend is not
  checked while it runs (§5.5).
- where its findings are stored, what its queue line says, and what writes it.
- what a `blocker` becomes with no REBUT to route to.
- how a patch that will not apply is charged.
- every site that reads the constraints. Principle 49 applies here. A member
  whose implementer sees the constraints has already checked itself against
  them, so the review catches less of that half.
- what editing a composite does to its members' tasks and open pull requests.

Backlog item b-602d00 checks the first join, the names a member consumes,
before the member's cell starts.
