---
id: SA-0011
title: Every acceptance criterion is prose, and the PR body renders it as an unticked box
type: feature
priority: 1
depends_on: []
touches:
  - saffron/gates/core/criteria.py
  - saffron/intake.py
  - saffron/cell/session.py
  - saffron/report/pr_body.py
  - tests/test_criteria.py
  - tests/test_intake.py
  - tests/test_report.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - saffron/gates/core/scope.py
  - saffron/gates/core/integrity.py
  - saffron/gates/core/census.py
budget_usd: 14
max_attempts: 4
max_turns: 100
risk: elevated
---

## Context

`DESIGN.md` §5.4's founding lesson is `tool`: `{"status":"pass","failures":[]}` is
bit-for-bit identical whether the linter found nothing or the linter was not on
`PATH`, so the contract requires an identifier **obtained by executing the tool**
(Appendix H). A gate that cannot run its tool cannot produce the field.

Acceptance criteria have no `tool`. They are parsed by `intake.py`, injected into
the implementer's and the critic's prompts, and rendered by `pr_body.py:128` as:

```python
lines += [f"- [ ] {criterion}" for criterion in spec.acceptance_criteria]
```

Unticked, always, for every criterion, with no host-side component anywhere that
asks whether one was met. The morning artifact shows a checklist that nothing can
tick, which reads as evidence and is not.

`agents/artifacts.py` already knows the principle — it rejects a plan naming no
test file with the reason *"acceptance criteria that cannot fail are prose"* — and
enforces it at the coarsest available grain: whether the plan mentions **any** test
file. Never per criterion, and never against what the change actually did.

## Problem

The gap this closes is not that criteria go unchecked. It is that **an unchecked
criterion is indistinguishable from a met one** in the artifact the operator reads
to decide. That is the `tool` defect, one layer up, in the layer that decides
whether a PR is merged.

Three consequences, all live today:

- A task can satisfy every gate, produce a diff that meets no acceptance criterion,
  and reach `READY_FOR_REVIEW` with a PR body that looks identical to one that met
  all of them.
- `SA-0001`'s Q1 — *"the operator rejected on this criterion; did any gate or lens
  assert on it?"* — returns an unbound assertor for every criterion, because the
  vocabulary models criteria as `earl:TestCriterion` and **nothing produces the
  assertions**. The reader exists; the writer does not.
- The flywheel's bucket-1 triage (§8) asks which failures were mechanically
  checkable. A criterion that was never mechanically checked cannot answer.

## The shape

A criterion declares a **witness**: an executable the host runs, not a claim the
model makes. The spec is an operator artifact under `.saffron/specs/`, which
`policy.yaml` lists as `protected` — so witnesses are declared by the operator and
**cannot be relaxed by the cell**. That property is what the whole design rests on;
without it the agent would simply mark every criterion `preserves`.

`criteria` is a core gate, invoked host-side like `scope` and `size`, taking the
spec directly (`session.py:682` is the shape). It **invokes the repo's declared
`tests` gate with the witness subset** — the sanctioned exception in `CLAUDE.md`:
*core invokes declared gates, never tools*. §5.4's role table already requires
`tests` to accept a test-subset argument for exactly this reason.

**The direction is the load-bearing part, and it is cheaper than `revert`.** The
baseline suite already runs against `base_sha` (§4.4), so a witness can be run on
both sides without stashing hunks. A criterion that claims the change *did*
something must have a witness that **failed or errored at base and passes at head**
— a witness that passed before the change proves nothing about it. A criterion
declaring `preserves: true` claims the opposite and is checked the opposite way.

## The format

A new optional frontmatter key. Absent, nothing changes:

```yaml
acceptance:
  - claim: "the size gate blocks a 700-line feature diff at elevated risk"
    witness: tests/test_size.py::test_a_feature_over_the_ceiling_blocks_at_elevated
  - claim: "a standard-risk task is unaffected"
    witness: tests/test_size.py::test_standard_risk_is_advisory
    preserves: true
```

**This spec does not use it, and that is a finding rather than an oversight.**
`Spec` sets `extra="forbid"`, so a spec declaring `acceptance:` today is refused at
intake as malformed — which means the first spec to declare witnesses cannot be the
one that builds them. The recursion has to be closed by a fixture instead: a
criterion below requires that this file, rewritten with the block above, parses and
passes its own gate. Worth carrying into `DESIGN.md` §3.2 separately: **a spec
cannot introduce the frontmatter it is written in.**

## Acceptance criteria

- [ ] A spec declaring `acceptance:` parses into structured criteria — `claim`,
      `witness`, optional `preserves` — and a spec declaring only the markdown
      section keeps today's behaviour byte for byte
- [ ] `criteria` reports `skip` when a spec declares no witnesses, and every spec
      from `SA-0001` to `SA-0010` still runs unchanged
- [ ] A criterion whose witness resolves to nothing the repo contains **fails**,
      rather than passing because nothing ran
- [ ] **A witness that passed at `base_sha` and passes at head fails the gate**,
      unless the criterion declares `preserves: true` — a witness that passed
      before the change proves nothing about it
- [ ] A criterion declaring `preserves: true` is checked the opposite way and
      fails if its witness did not pass at `base_sha`
- [ ] A witness that cannot run at `base_sha` because the diff adds it is the
      ordinary new-criterion shape, not an infrastructure abort
- [ ] The gate's `tool` is the one the `tests` gate reported, and a `tests` gate
      that errored yields `error` — never `pass` with the field absent
- [ ] `pr_body` ticks a criterion's box only from a `criteria` gate result, and an
      unticked box carries the reason it is unticked
- [ ] This spec, rewritten with the `acceptance:` block above as a test fixture,
      parses and passes `criteria` — the recursion the frontmatter cannot close

## Out of scope

The `revert` gate. It is designed (§5.4), unbuilt (`review.py:42`), and answers a
different question — whether *new tests* fail without the source hunks, over a
diff-derived set rather than a declared one. If it is built later it should call
this gate's runner rather than growing a second one; nothing here blocks it.

Migrating `SA-0001`–`SA-0010` to declared witnesses. They keep the markdown
section and the gate reports `skip`, which is what `skip` is for.

Any change to `ontology/`. The vocabulary already models a criterion as an
`earl:TestCriterion` and a gate result as an `earl:Assertion` over it; this spec
produces the assertions and stores them in the ledger. Emitting them as triples is
`v2.5` and conditional (Appendix O).

Checking prose anywhere other than a spec's criteria — commit messages, PR body
narrative, `DESIGN.md`. That is the same defect class and a much larger question.

## Notes for the agent

**`skip` is not a failure and is the common case.** Ten specs predate this one.
A spec with no `acceptance:` block must leave every existing behaviour byte-identical,
and there is a test for that. Reaching for a default witness would be worse than
skipping: a criterion checked against an invented test is the defect this spec
exists to close, wearing the fix's clothes.

**`error` is not `fail`, and this gate has two sources of it.** The `tests` gate it
invokes can error, and a witness can name a node id the runner cannot collect. Both
abort the attempt and are charged to nobody. A witness whose test *fails* is `fail`.
Collapsing them means an agent spending attempts on a broken runner.

**`tool` comes from the gate you invoked.** This gate executes no tool of its own, so
its `tool` is the one the `tests` gate reported. Do not synthesise one, and do not
report `pass` with the field absent — that is the exact shape Appendix H is about.

**The base side may not exist.** A witness naming a test the diff adds cannot run at
`base_sha` — that is an *error* at base, and error at base plus pass at head is the
ordinary successful shape for a new criterion. Treating it as an infrastructure
abort would make every new test fail its own criterion.

**Size.** `risk: elevated` makes `size` blocking at the 600-line feature ceiling.
The gate is perhaps 120 lines and the tests are most of the rest. If it will not
fit, stop and raise it — `pr_body` rendering is the separable half and is the
correct thing to split, not test coverage.
