---
id: 7
title: "A stack batch runs the spec DAG into one stack and writes its own follow-ups"
status: accepted
date: 2026-09-23
supersedes: []
superseded_by: []
appendices: [A, D, E, F, H, I, J, K, L, N, P, U]
principles: [2, 4, 6, 15, 16, 17, 21, 23, 26, 27, 28, 29, 30, 34, 38, 40, 44, 45, 47, 49, 50, 54, 57, 62]
---

## Context

The spec loop skill runs each queued spec through an attended `saffron cell`.
A delegate reviews each pull request by hand, pushes review commits, and
chains the pull requests into one stack. Each step it does by hand is a gap in
Saffron's gates, lenses or phases.

`saffron batch` already walks a DAG. It rescans after every task (`SA-0106`),
admits a child once its parent is `READY_FOR_REVIEW`, and cuts the child from
the parent's branch (§4.2). A spec with no `depends_on` is cut from the
default branch, so a batch yields siblings, not one stack.

The review commits a delegate pushes reach a pull request that no gate or
critic reads (backlog items 40 and 97).

§1.4 refuses "agents writing their own specs from a roadmap", as the part most
likely to waste money. The operator asked for review findings to become specs
inside the same batch.

## Decision

**A stack batch hands each task's branch to the next.**

It plans its order once. A task's **predecessor** is the last task below it at
`READY_FOR_REVIEW`. The task is cut from the predecessor's head, and its pull
request targets the predecessor's branch. One stack batch yields one pull
request stack.

**Every task in a stack batch stacks.** Every `depends_on` entry of a spec
comes before it in the order, so its tree holds that code. A spec is refused
when any `depends_on` entry is outside the plan and not on the default branch.
A composite's members stay contiguous in the order, so the last member's tree
carries members only. Outside a stack batch, §4.2 and ADR 6 stack as before,
on `depends_on[0]`.

**A task that misses `READY_FOR_REVIEW` adds no layer.** Its `depends_on`
descendants are refused with a reason. The batch goes on.

**Spec review runs inside the batch.**

It runs before each spec's first cell. A blocker that asks for a better witness
or a buildable spec is revised by an agent, for a bounded number of rounds. A
blocker that asks to change what the spec is for skips the spec and its
descendants, and reaches the operator. Each round's fresh review reads the
revision beside the original, and a changed purpose it finds routes the same
way. The batch never pauses for the operator.

**A stack batch runs spec text that is not at `base_sha`.** The text is a spec
review's revision or a follow-up, and nothing else. Every spec the operator
queued is first read at `base_sha`. Outside a stack batch, §4.2.1's input rule
holds unchanged.

**One end review reads the whole stack once.** Two end-review lenses, Spec and
Standards, read each layer. One join lens reads the stack under ADR 6's rubric.
Each layer's unrebutted in-cell concerns join their findings as inputs. The
host decides which findings qualify. A qualified finding is anchored, and any
probe it carries survived.

**The end review takes four exceptions to ADR 4, and this ADR carries them.**
Its lenses are not ADR 4's declared lenses. They run once per batch, not on
every reviewed diff. A qualified `blocker` or `concern` feeds a follow-up spec,
not REBUT. A lens that errors has no task to stop, so its layer shows as
unreviewed. Every in-cell critic keeps ADR 4 whole, a follow-up's included.

**Qualified findings become follow-up specs, one generation deep.** An agent
writes each follow-up in a critic cell. It passes the same spec review and runs
on top of the stack. A follow-up's own unrebutted findings go to the backlog,
not to a second generation. A second generation needs an ADR that amends this
one.

**The host commits the batch's revised and follow-up specs.** They land in the
top layer. It is the one agent-written text a protected path takes, and the
host writes it, never a cell.

**Nothing merges.** The batch links the stack, and `--ready` marks it ready.
Merging stays the operator's, as §1.4 says of every version.

This ADR narrows §1.4's refusal, and §1.4's entry says so. An agent writes a
follow-up only from a qualified finding, inside a batch the operator started.
An agent revises a queued spec only for a witness or buildability blocker,
within the round bound. ADR 6's rule that the operator writes each new member
spec stands. A follow-up has no `depends_on`, so it is never a member spec. A
revised member spec is not a new one.

`docs/superpowers/specs/2026-09-23-stack-batch-design.md` holds the design
this decision rests on.

## Options considered

- **Keep the attended loop.** Each spec costs the operator a round of
  questions, and each review commit passes no gate.
- **Saffron runs the cells, and the delegate writes the follow-ups.** The
  delegate stays a required step in the middle of every batch.
- **Orchestrate from the skill's driver.** The control lives in a script that
  no gate reads, which is the reverse of the loop's goal.
- **A stack mode of `saffron batch` (chosen).** Every model call is a
  host-invoked session in a critic cell, and every fix passes a cell's gates.

## Principles

- **2** departs. A spec whose dependency sits in an unmerged stack outside the
  plan is refused. Cutting it from its predecessor would drop that code. The
  residual is a spec that waits for a merge, as §4.2 avoided.
- **4** upholds. Every end-review lens and every spec session runs in a critic
  cell. The host decides what qualifies.
- **6** departs. A follow-up that carries a probe exists to kill it, and
  blocking teaches the cheapest satisfaction. ADR 3 measured this in
  `SA-0079`. The answer is the criterion probe a fresh session names in the
  follow-up's own critic.
- **15** departs. A finding feeds a follow-up only once the host anchors it
  and runs any probe it carries. A spec review's tag is a claim, and it decides
  whether an agent revises a spec. The next round's fresh review is its check.
- **16** upholds. One generation, bounded revision rounds and the batch budget
  bound the batch.
- **17** departs. Spec review runs before a spec's first cell. A descendant
  refused after its parent's review has paid for its own review and revisions.
  The round bound caps that spend, and no cell starts.
- **21** departs. A hand push to a lower layer mid-batch leaves the layers
  above on a stale head. The residual holds until the spec records each
  handoff's head and checks it at the finish.
- **23** upholds. §1.4's entry is narrowed in the same pull request, with its
  reason and the seam that covers the rest.
- **26** upholds. "Predecessor" names the task below in the stack. "Parent"
  keeps its one referent, `depends_on[0]`. The refusal names every
  `depends_on` entry, not the parent alone.
- **27** upholds. It holds once the spec keys a follow-up's anchors and named
  probe to the tree it runs on. A later layer can move both.
- **28** upholds. It holds once the spec checks qualification against each
  producer. A finding with no probe must still reach a follow-up.
- **29** upholds. This ADR carries its exceptions to §1.4, §4.2.1, ADR 4 and
  the protected path, each with its bound. §1.4 names its own.
- **30** departs. Stack mode widens definitions in `CONTEXT.md`, §4.2 and
  §4.2.1. The specs that build each piece edit them. Until then the old
  sentences stand.
- **34** upholds. It holds once the spec shows a layer the end review did not
  reach, or reached with an error, apart from a clean one.
- **38** upholds. The join lens reads the stack's pushed top head, not a tree
  assembled for the review.
- **40** upholds. The join lens reads the seams between layers. The residual
  is the seams around the follow-ups and the top layer, which it never sees.
- **44** departs. The follow-up path has never run. The criterion probe that
  answers principles 6 and 49 has not run live either (ADR 3). Its cost and
  its catch rate are both forecasts.
- **45** upholds. A finding with a probe qualifies by a run against the
  layer's tests, not by the author's report.
- **47** departs. A follow-up that names a surviving probe lets its cell kill
  that exact edit and no other. Principle 6's answer covers it.
- **49** departs. The implementer sees a named probe and can run it before it
  reports. The criterion probe its critic names stays hidden until REBUT.
- **50** departs. The end-review lenses replace a delegate's hand review. A
  qualified finding becomes code before any person reads it. The operator
  reads it only as a layer of the stack.
- **54** upholds. It holds once the spec re-runs gate 0 and `parse_spec`'s
  refusals on every revised and follow-up spec, not only on files at
  `base_sha`.
- **57** upholds. The Decision summarises the design record, and the record
  keeps the routes this ADR leaves out.
- **62** departs. §1.4's reason, money, still reaches follow-ups and
  revisions. One generation and the round bound answer it, and the
  measurement below tests the answer.

## Consequences

`CONTEXT.md` gains "predecessor", "stack batch", "follow-up spec", "end
review", "end-review lens" and "join lens" through `ontology/factory.ttl`.
"Spec review", "critic cell", "lens", "run", "stacked branch", "tree base" and
"spec chain" widen.

These are left to the specs that build it. The design record proposes an
answer to each.

- how blockers route by the spec review's tags, and the round bound.
- which refusals re-run on a revised or follow-up spec, and gate 0's
  "`spec_sha` moved" rule for a revised one.
- what qualifies a finding with no probe, which kill rule a probe meets, and
  whether a surviving probe promotes a `note`, as ADR 3 does.
- which tree a follow-up's anchors and named probe are keyed to.
- which follow-up spec fields the host enforces: `touches`, budget, risk.
- how the `scope` gate treats the host's commit to `.saffron/specs/`.
- where the ledger and the record keep the stack's layers.
- how gate 0's open pull request check treats the batch's own tasks (backlog
  item 59).
- what `RATE_LIMITED` does to the breaker in a stack batch (§4.2.1).
- what `--until` and the budget leave running, and the reserve for the end
  review, the spec work and the finish.
- what the operator sees for an escalation and for an unreviewed layer.
- how the delegate files the backlog from the batch's findings, until a
  declared program does it.

Whether follow-ups earn their cost is to be measured. The first measure is the
share of follow-ups that reach `READY_FOR_REVIEW` with a clean critic. The
second is the spend per follow-up, across its writing, spec review and cell. They
decide whether an amendment for a second generation is worth proposing.
