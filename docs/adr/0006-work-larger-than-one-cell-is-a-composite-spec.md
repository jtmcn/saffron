---
id: 6
title: "Work larger than one cell is a composite spec, reviewed once at the joins"
status: accepted
date: 2026-09-21
supersedes: []
superseded_by: []
appendices: [A, C, D, E, F, H, I, K, L]
principles: [2, 4, 12, 15, 17, 25, 26, 28, 29, 34, 38, 40, 45, 48, 49, 50]
---

## Context

A spec runs in one cell and ships as one pull request. The `size` gate bounds
its diff, blocking at `elevated` (§5.4). A feature needing several dependent
changes has no record in Saffron. `depends_on` links two specs and stacks the
child on its parent's branch (§4.2). Nothing holds the design the parts share,
their order, or the values every part must match.

So large work is sequenced outside the factory. `docs/superpowers/plans/`
holds 26 plans. 20 of them require the superpowers subagent executor, which
runs each task outside any cell. `2026-08-31-operator-visibility.md` and
`2026-09-04-batch-orchestration.md` did the other thing. Each of their tasks
was a spec run through `saffron cell`, sequenced by the operator. The second
put every task under one "Global Constraints" block. That plan is the pattern
this ADR records. Backlog item b-e1afbb records the gap.

Each critic reads one task's diff (§5.5). Appendix I found both Criticals of
the v0.5 build "in the wiring between tasks", and only "the whole-branch
pass" found them. It asked for at least one review scoped to the joins.

## Decision

A **composite spec** declares an ordered list of **member specs** and the
constraints every member inherits. It carries no criteria of its own. Its
members live in its repo, because dependencies do not cross repos (§4.2).

**The members stack.** Each member after the first names the member before it
as `depends_on[0]`, the only entry that stacks (§4.2). So they schedule as
§4.2 already describes. The composite's list is authoritative. A member whose `depends_on` disagrees with it is refused at
gate 0 (§4.2.1). Inside a stack batch, every task stacks, and ADR 7 narrows
the composite review's range to the members' own layers. ADR 7 also lets an
agent revise a member spec, within its bounds.

**One composite review reads the joins.** It runs once the last member reaches
`READY_FOR_REVIEW`, in a critic cell (§5.5). Its rubric has three parts:

- each name one member uses from another, against the member that produces it.
- each name a member produces that no later member uses.
- work a member redoes when an earlier member already provides it.

It also checks the composite's constraints across all members. A member's own
criteria stay with that member's critic. Its findings follow ADR 4 with one
exception. A `blocker` has no REBUT to route to, so Consequences leaves its
route to the spec.

**It reads the tree the last member's critic read.** That tree is the last
member's tree base with its patch applied. It already carries every member
before the last. The tree that merges can still differ. §6.1's merge train
re-runs the gates on it, and nothing re-reads its joins. A change to any
member voids the review until every member after it is rebuilt on the change.

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

- **2** departs. The composite review waits on `READY_FOR_REVIEW`, not
  `MERGED`, so its first review can happen inside a batch if the spec puts its
  owner there. A review after a void waits on the later members being rebuilt,
  and today only the operator re-queues them. That edge is satisfied outside
  the batch. The residual is a voided review that no batch repeats.
- **4** upholds. The review runs in a critic cell, never in a member's
  implementer cell.
- **12** upholds. The decision adds a spec kind and one review over its
  members. 26 plans show the need, so neither is built ahead of its use.
- **15** upholds. A composite finding counts only once the host anchors it.
  What it anchors against is left to the spec.
- **17** upholds. A member whose `depends_on` disagrees with the composite is
  refused at gate 0, before its cell spends.
- **25** upholds. "Composite spec", "member spec" and "composite review" enter
  through `ontology/factory.ttl`, so the vocabulary tests read them.
- **26** upholds. "Parent" keeps its one referent, a stacked task's
  `depends_on[0]`. The composite is never called a parent.
- **28** upholds. It holds once the spec settles anchoring. A name a member produces
  and no later member uses is absent from the last member's diff. An anchor
  tuned to that diff would drop the rubric's second part and leave no error.
- **29** upholds. The `size` ceiling guards the operator's review of one pull
  request. Each member still meets it. The composite review asks no person to
  read the combined diff, so it is no exception to the ceiling's reason. It is
  an exception to ADR 4's route for a `blocker`, named in the Decision.
- **34** upholds. It holds once the spec shows a composite whose review has
  not run, or was voided, as distinct from one whose review is clean.
- **38** upholds. The review reads the tree the last member's critic read, not
  a tree assembled for the review. The merged tree is the residual. The merge train gates it and reads no join.
- **40** upholds. It is the reason for the decision. The rubric reads the
  joins, which no member's critic can see. It names two seam shapes Appendix
  I found: a name produced and never called, and a second implementation of
  work another part already did. A right-typed value in the wrong slot and a
  file read from the wrong repo are left to the review's open reading.
- **45** upholds. It is one reason the superpowers executor is rejected. Its
  implementer writes the tests and reports them, which certifies agreement.
- **48** upholds. Each member's gates check what its spec named. The
  composite review exists for the joins no spec named.
- **49** upholds. It is the other reason. The executor's implementer runs its
  own checks before reporting, so they have already passed.
- **50** departs. At the joins the critic is the only full reader. The
  executor's whole-branch review read them, and this review replaces it. On
  the path where the operator runs cells by hand, nobody read the joins, so
  there it adds a critic and removes no reader. The residual is that nothing
  yet puts its findings in front of the operator. A join defect the critic
  misses has no second reader.

## Consequences

`CONTEXT.md` gains the three terms above. Its definitions of "critic cell" and
"queue line" widen to cover a review with no implementer of its own.

The spec schema gains the composite's fields. Per §3.2, the spec that adds
them cannot use them, so it ships with a fixture.

These are left to the spec that builds the composite review:

- what runs it: a task of its own, a phase of the last member's task, or the
  batch itself. The items below assume that owner.
- what counts as a change to a member, including a fixup the operator pushes
  by hand, and what rebuilds the members after it.
- its model, its budget, and how admission checks it, given that REVIEW spend
  is not checked while it runs (§5.5).
- where its findings are stored, what its queue line says, and what writes it.
- what its findings anchor against, since ADR 4 anchors to one diff.
- what a `blocker` becomes with no REBUT to route to, including any fix
  round.
- what the operator sees when the review errored, has not run, or was voided.
- how a patch that will not apply is charged.
- every site that reads the constraints. Principle 49 applies here. A member
  whose implementer sees the constraints has already checked itself against
  them, so the review catches less of that half.
- what editing a composite does to its members' tasks and open pull requests.

Gate 0 refuses a ninth thing. §4.2.1's count changes with it, and backlog
item 48 stands for the reader that notices.

Backlog item b-602d00 checks the first join, the names a member consumes,
before the member's cell starts.
