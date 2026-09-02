# Is the RDF layer worth emitting?

One row per query, challenged against the §4.1 schema. Per `SA-0001`, speculation
about a schema change that *would* make it easy in SQL counts as a SQL win.

| | SQL equivalent | Verdict |
|---|---|---|
| Q1 acceptance criteria on rejected tasks | Awkward — criteria are markdown checkboxes, in no table | **SQL, once a `criteria` table exists.** RDF's win is only that a gate and a lens reach a criterion through one join instead of two |
| Q2 blockers per lens, split by adjudication | Yes — `findings.adjudication` landed in rev 6 for this | **SQL.** The graph carries *who* held each position; the count does not need it |
| Q3 sole failures, and gates that never fired | Half. Sole-failure is a correlated subquery either way; "never fired" needs the declared set, which preflight parses and drops | **SQL, once declared gates are stored.** Same shape as Q1 |
| Q4 derivation chain of a merged PR | Yes, awkward. §4.1's foreign keys carry a chain that is fixed and shallow; scope, plan and diff being file paths is the awkward part | **SQL.** RDF states the edges instead of implying them from a path template, which is worth something for N5 and not worth an emitter |
| Q5 cost per accepted PR | Yes, easily | **SQL.** Included as the control |

## Bottom line: don't build the emitter.

> **Superseded 2026-09-02**, on stated grounds — see the closing section and
> `docs/superpowers/specs/2026-09-02-ontology-authoritative-design.md`. The table
> below is not disputed; the question it asked is not the question now being asked.

Five of five. Q4 was written up as the one query with no relational form, on the
grounds that SQL needs a UNION arm per artifact kind — which this query has four
of. Correcting it costs the vocabulary its last query-shaped justification, the
outcome `SA-0001` names as a successful one.

Nor does it beat the glossary rival of §4.6.2b: `CONTEXT.md` already is that
glossary. Revisit at v2.5 (§9) only if reconstructibility must be *enforced
continuously* rather than spot-checked.

## What the modelling found, which is the part that paid

- **`earl:mode` is the axis §4.1 conflated.** `gate_results` and `findings` split on
  *how* an assertion was produced — deterministic versus not — which EARL states in
  one property over one class. That is the supertype `CONTEXT.md`'s open naming
  decision calls unwritable in Saffron's own vocabulary. The operator's rejection
  fits that shape too, which is what makes Q1 a query rather than a monthly reread.
- **Two documents disagree about which states are terminal.** `CONTEXT.md` §6 lists
  six, `DESIGN.md` §3.3 lists nine, and neither holds `ORPHANED`, which
  `saffron/cell/session.py` writes. §3.3 governs here. Modelling it also forced a
  distinction neither document draws: the state a task *ends in* is a wider set than
  the states that *reach the operator*, and `tasks.state` is one TEXT column for both.
- **Left unmodelled because nothing reads them**: `prov:wasInvalidatedBy` for
  `spec_sha` invalidation, tool-call granularity, DCAT. The `owl:disjointWith`
  axioms are stated for external reasoners only; SHACL is what runs, and the shapes
  are what earn those terms.

## Revisit, 2026-09-02: the question changed

This document scored one question — *is the RDF layer worth emitting, given five
analytical queries?* — and answered five of five for SQL. Nothing below is
withdrawn, and the measurements stand. Three inputs changed.

1. **A knowledge graph became a goal rather than a means.** The table prices RDF
   as a query optimisation. It never evaluated the graph as a capability wanted
   for its own sake, so it does not govern that decision.
2. **Two verdicts were conditional and their conditions are still unmet.** Q1 is
   *"SQL, once a `criteria` table exists"* and Q3 *"once declared gates are
   stored"*. Measured 2026-09-02, the ledger holds `repos, runs, tasks,
   attempts, gate_results, failures, findings` — there is no `criteria` table,
   so Q1 remains awkward in SQL as first written.
3. **A sixth consumer appeared.** Part 3 of
   `docs/superpowers/plans/2026-08-31-operator-visibility.md` (`SA-0035`–`SA-0039`)
   is a query-and-render layer over the run record, and `saffron/report/render.py`
   is still unwritten. The five queries were scored with no renderer in view.

**What did not change.** The glossary finding holds: `CONTEXT.md` is the
system's glossary and the graph is not a rival to it. The successor design keeps
that split — only `CONTEXT.md`'s *run-record* sections are generated from the
vocabulary, and the whole-system terms stay hand-written.

**The successor keeps SQL as the write path.** The graph is a derived read model
projected from the ledger, not a replacement for it — so the case this document
actually made is preserved rather than overturned. The emitter is now built;
whether it *earns its keep* is re-tested in that design's Phase C, against
emitted graphs rather than a hand-written fixture, with stopping as an explicit
outcome.
