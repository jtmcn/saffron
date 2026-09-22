---
id: 5
title: "The ontology describes the run record and controls nothing"
status: accepted
date: 2026-09-22
supersedes: []
superseded_by: []
appendices: [B, O, P, T]
principles: [10, 11, 24, 25, 56, 57, 61, 62]
---

## Context

The decision is spread across §1.4, §4.6, §9's v2.5, §11, `ontology/RATIONALE.md`
and four appendices. Three questions were asked of the ontology, one at a time.

- **The analytical question.** `SA-0001` built a PROV-O and EARL vocabulary and
  challenged five queries against SQL (Appendix B). SQL won all five, so the
  RATIONALE said not to build the emitter. `CONTEXT.md` already met the
  glossary rival of §4.6.
- **The operational question.** Appendix O asked whether the ontology could
  control execution. A spike on 2026-09-04 built §4.2.1's refusal predicate
  twice, once as Python and once as shapes. The shape form stated no refusal
  the Python left implicit, and was harder to read. O's rule, named before the
  run, closed the question.
- **The N5 question.** Appendix T reopened the emitter on the RATIONALE's own
  clause. Q4, the query that encodes N5, had run only against hand-authored
  fixtures. T named a rule before the run. Build the projection from the whole
  ledger, and run Q4 over merged history against a checked SQL walk.

Appendix P restated the emitter's status as deferred rather than refused.

## Decision

The factory ontology describes the run record. It never controls execution. No
scheduling decision reads a triple, and the shapes gate no state transition.

The graph is derived and one-way. SQLite is the system of record, and the
projection is rebuilt from the ledger with no write path back. If the graph is
stale, wrong or absent, the factory still runs.

For analytics the emitter is not built. The five queries stay in
`ontology/queries/`, as worked examples the tests run.

For N5 the projection is built, as an instrument and not a control
(`SA-0107`, `SA-0108`). `saffron chains` materializes it over the real ledger
and compares Q4 with the checked walk. T's rule is not yet settled. The first
run compared 38 of 76 merged tasks and found no break. The one real overwrite in
history is among the tasks left out (backlog item b-952c34).

The vocabulary keeps the readers it has: the `shacl` gate, the render of
`CONTEXT.md` from `ontology/factory.ttl`, and the dead-term test. A term with no
reader is deleted. Coverage follows readers, never the reverse.

The operator's intent to revisit §1.4 is recorded in Appendix T, and it decides
nothing. §1.4 moves only on a measured result. Whoever reopens it starts with
§4.2.1, which omits the `forbidden` carve-out that closed O's spike.

## Principles

- **10** upholds. Five SQL wins was a pass, and the analytical emitter was
  never built.
- **11** upholds. The modelling found defects in `DESIGN.md` before any triple
  was stored, and O records four.
- **24** upholds. `CONTEXT.md` is the glossary rival, and it is generated from
  the vocabulary rather than kept beside it.
- **25** upholds. The vocabulary found real defects in the design, which is why
  it keeps readers while the emitter did not.
- **56** upholds. Each question got its own experiment. The analytical no did
  not answer the operational question, and neither answered N5.
- **57** upholds. This ADR condenses §1.4, §4.6, §9 and three answers. It
  states each on its own evidence and merges none into a general verdict.
- **61** departs. Q4 now runs over real history, and half of it. The case T
  named as decisive has not been an input yet (item b-952c34).
- **62** upholds. The RATIONALE's refusal reached the analytical case. T
  reopened the emitter on a reason the refusal never covered.

## Consequences

`saffron/projection.py` and `saffron/chain_walk.py` import `rdflib`, `pyshacl`
and `pyoxigraph` inside the functions that use them. T expected the operator to
move them to runtime dependencies at merge. They are still in the `dev` group,
and `pyproject.toml` still says nothing under `saffron/` imports one. So
`saffron chains` runs only where the dev group is installed.

Item 170 makes the commits on `refs/saffron/*` the authoritative record and the
ledger an index folded from them. Once it lands, the projection is derived from
a derivation. The overwrite T's rule looks for stops arising, so the rule
measures history recorded before item 170.

The dead-term test holds the vocabulary to its readers. The roughly thirty
`CONTEXT.md` terms O measured have no reader, and stay out.
