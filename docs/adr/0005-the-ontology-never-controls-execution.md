---
id: 5
title: "The ontology describes the run record and never controls execution"
status: accepted
date: 2026-09-22
supersedes: []
superseded_by: []
appendices: [B, D, E, O, P, T, U]
principles: [10, 11, 23, 24, 25, 29, 34, 36, 56, 57, 61, 62]
---

## Context

The decision is spread across §1.4, §4.6, §9's v2.5, §11, `ontology/RATIONALE.md`
and four appendices. Appendix U named it as the example of a decision no single
record held. Three questions were asked of the ontology, one at a time.

- **The analytical question.** `SA-0001` built a PROV-O and EARL vocabulary and
  challenged five queries against SQL (Appendix B). SQL won all five, so the
  RATIONALE said not to build the emitter. `CONTEXT.md` already met the
  glossary rival of §4.6.
- **The operational question.** Appendix O asked whether the ontology could
  control execution. A spike on 2026-09-04 built §4.2.1's refusal predicate
  twice, once as Python and once as shapes. The shape form stated no refusal
  the Python left implicit. The readable shape got `**/size.py` wrong, and the
  correct one was a nine-deep nested `REPLACE`. O's rule, named before the run,
  closed the question.
- **The N5 question.** Appendix T reopened the emitter on the RATIONALE's own
  clause. Q4, the query that encodes N5, had run only against hand-authored
  fixtures. T named a rule before the run. Build the projection from the whole
  ledger, and run Q4 over merged history against a checked SQL walk.

Appendix P called the emitter deferred. T then reopened it, and P still says
deferred.

## Decision

The factory ontology describes the run record. It never controls execution. No
scheduling decision reads a triple, and the shapes gate no state transition.
The `shacl` gate is blocking, and it validates an artifact, which is not a
state transition (Appendix O).

The graph is derived and one-way. SQLite is the system of record, and the
projection is rebuilt from the ledger and the batch tree with no write path
back. If the graph is stale, wrong or absent, the factory still runs.

For analytics nothing materializes the projection. No batch-end run exists, and
the five queries stay in `ontology/queries/`, as worked examples the tests run.

For N5 the emitter is built, as an instrument and not a control (`SA-0107`,
`SA-0108`). `saffron chains` materializes the projection over the real ledger
and compares Q4 with the checked walk. T's rule is not yet settled. The first
run compared 38 of 76 merged tasks and found no break. The one real overwrite in
history is among the tasks left out (backlog item b-952c34). A zero also cannot
see an overwritten diff of the same length as the one it replaced.

The vocabulary's readers are the shapes and the queries, Q4 included. The
dead-term test enforces them. A term no shape or query reads is deleted.
Coverage follows readers, never the reverse.

The operator's intent to revisit §1.4 is recorded in Appendix T, and it decides
nothing. §1.4 moves only on a measured result. Whoever reopens it starts with
§4.2.1. It omits the `forbidden` carve-out that explains O's no on question 1.

This ADR replaces Appendix P's paragraph on the emitter's status. P itself is
not edited.

## Principles

- **10** upholds. Five SQL wins was a pass, and no analytical run was ever
  built.
- **11** upholds. The modelling found defects in `DESIGN.md` before any triple
  was stored, and O records four.
- **23** upholds. §1.4 is a living refusal record. Its ontology entry moves only
  on a measured result, and T keeps the operator's intent from moving it.
- **24** upholds. `CONTEXT.md` is the glossary rival, with its `_Avoid_` lists.
  Its closed sets are rendered from the vocabulary.
- **25** upholds. The vocabulary found real defects in the design, which is why
  it keeps readers while no analytical run was built.
- **29** departs. §4.2.1 states the refusal predicate without the `forbidden`
  carve-out `_unmatched_criterion_path` carries.
- **34** upholds. T built the projection because a chain that never linked read
  the same as one that did. A stated edge is absent when the chain breaks.
- **36** upholds. A comparison over half the merged tasks is not taken as a
  result, and a zero with nothing compared reads as nothing comparable.
- **56** upholds. Each question got its own experiment. The analytical no did
  not answer the operational question, and neither answered N5.
- **57** upholds. This ADR condenses §1.4, §4.6, §9, §11 and three answers. It
  states each on its own evidence, and keeps §1.4's scope to execution.
- **61** departs. Q4 now runs over real history, but only over half of it. The
  case T named as decisive has not been an input yet, and backlog item b-952c34
  holds that open.
- **62** upholds. The RATIONALE's refusal reached the analytical case. T
  reopened the emitter on a reason the refusal never covered.

## Consequences

`saffron/projection.py` and `saffron/chain_walk.py` import `rdflib`, `pyshacl`
and `pyoxigraph` inside the functions that use them. T expected the operator to
move them to runtime dependencies at merge. They are still in the `dev` group.
Three files still say nothing under `saffron/` imports one: `pyproject.toml`,
`ontology/render.py` and `ontology/design_record.py`. So `saffron chains` runs
only where the dev group is installed (backlog item b-0adc85).

Item 170 makes the commits on `refs/saffron/*` the authoritative record and the
ledger an index folded from them. That reverses §4.6's first rule, and this
Decision's sentence on SQLite is restated when it lands. The projection is then
derived from a derivation. The overwrite T's rule looks for stops arising, so
the rule measures history recorded before item 170.

The roughly thirty `CONTEXT.md` terms O measured have no reader, and stay out
of the vocabulary.
