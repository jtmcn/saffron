---
id: 5
title: "The ontology describes the run record and never controls execution"
status: accepted
date: 2026-09-22
supersedes: []
superseded_by: []
appendices: [B, D, E, F, H, O, P, T, U]
principles: [10, 11, 23, 24, 25, 29, 30, 34, 36, 56, 57, 61, 62]
---

## Context

The decision is spread across §1.4, §4.6, §9's v2.5, §11, `ontology/RATIONALE.md`
and Appendices B, O, P and T. Appendix U named the emitter as its example of a
decision no single record held. Three questions were asked of the ontology, one
at a time.

- **The analytical question.** `SA-0001` built a PROV-O and EARL vocabulary and
  challenged five queries against SQL (Appendix B). SQL won all five, so the
  RATIONALE said not to build the emitter. `CONTEXT.md` already met the
  glossary rival of §4.6.
- **The operational question.** Appendix O asked whether the ontology could
  control execution. Its rule, named before the spike, reopened §1.4 only on a
  yes to two questions. Does the shape form state a refusal the Python leaves
  implicit (question 1)? Can someone who has not read the Python read it
  (question 4)? A spike on 2026-09-04 built §4.2.1's refusal predicate twice,
  once as Python and once as shapes. It answered no to both. The readable shape
  got `**/size.py` wrong, and the correct one was a nine-deep nested `REPLACE`.
- **The N5 question.** Appendix T reopened the emitter on the RATIONALE's own
  clause. Q4, the query that encodes N5, had run only against hand-authored
  fixtures. T named a rule before the comparison. Build the projection from the
  whole ledger, and run Q4 over merged history against a checked SQL walk.

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

For analytics nothing materializes the projection, at batch end or anywhere
else. The five queries stay in `ontology/queries/`, as worked examples the
tests run.

For N5 the emitter is built, as an instrument and not a control (`SA-0107`,
`SA-0108`). `saffron chains` materializes the projection over the real ledger
and compares Q4 with the checked walk. T's rule is not yet settled. Its first
invocation compared 38 of 76 merged tasks and found no break. The one real
overwrite in history is among the tasks left out (backlog item b-952c34). A
zero also cannot see an overwritten diff of the same length as the one it
replaced, and `saffron chains` prints that caveat (backlog item b-0281e4).

T's rule decides the emitter both ways. A zero across every merged pull request
returns it to the drawer. A break keeps it only while Q4 over the projection
stays cheaper to hold than the SQL walk with the same check added.

The dead-term test counts the shapes and the queries, Q4 included, as the
vocabulary's readers. A term neither reads is deleted. Coverage follows
readers, never the reverse.

The operator's intent to revisit §1.4 is recorded in Appendix T, and it decides
nothing. §1.4 moves only on a measured result. Whoever reopens it starts with
§4.2.1, which now states the `forbidden` carve-out behind O's no on question 1.

This ADR replaces Appendix P's paragraph on the emitter's status and rev 20's
entry in `DESIGN.md`'s status line. Neither is edited.

## Principles

- **10** upholds. Five SQL wins was the successful outcome §4.6 names, and no
  analytical materialization was built. The N5 emitter holds its place only
  under T's rule, and a zero sends it back.
- **11** upholds. The modelling found defects in `DESIGN.md` before any triple
  was stored, and O records four.
- **23** upholds. §1.4 is a living refusal record. Its ontology entry moves only
  on a measured result, and T keeps the operator's intent from moving it.
- **24** upholds. `CONTEXT.md` is the glossary rival, with its `_Avoid_` lists.
  Its closed sets are rendered from the vocabulary.
- **25** upholds. The vocabulary stays a test suite for the design. A term
  keeps its place only while a shape or a query reads it.
- **29** upholds. §4.2.1 now states the `forbidden` carve-out that
  `_unmatched_criterion_path` carries, so the predicate's exception is written
  into the rule.
- **30** upholds. §4.6's third rule and §10's tree line stated the emitter as
  unbuilt and `ontology/` as unread by `saffron/`. Both are rewritten here.
- **34** upholds. T built the projection because a chain that never linked
  read the same as one that did. A stated edge is absent when the plan's hash
  or the diff's length breaks the chain. A same-length overwrite is outside what
  the record captures (b-0281e4).
- **36** upholds. A comparison over half the merged tasks is not taken as a
  result, and a zero with nothing compared reads as nothing comparable.
- **56** upholds. Each question got its own experiment. The analytical no did
  not answer the operational question, and neither answered N5.
- **57** upholds. Each answer here keeps its own evidence and its own scope.
  §1.4's refusal stays about execution, and the analytical no does not stand in
  for T's rule.
- **61** departs. Q4 now runs over real history, but only over half of it. The
  case T named as decisive has not been an input yet, and backlog item b-952c34
  holds that open.
- **62** upholds. The RATIONALE's refusal reached the analytical case. T
  reopened the emitter on a reason the refusal never covered.

## Consequences

`rdflib`, `pyshacl` and `pyoxigraph` are runtime dependencies, because
`saffron chains` imports them. T left that move to the operator at merge, and
it landed later, in #472 (backlog item b-e0bbbf).

Item 170 makes the commits on `refs/saffron/*` the authoritative record and the
ledger an index folded from them. That reverses §4.6's first rule, and a later
ADR supersedes this one when it lands. The projection is then derived from a
derivation. The overwrite T's rule looks for stops arising, so the rule
measures history recorded before item 170.

The roughly thirty `CONTEXT.md` terms O measured have no reader, and stay out
of the vocabulary.
