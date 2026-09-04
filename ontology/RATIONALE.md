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

Five of five. Q4 was written up as the one query with no relational form, on the
grounds that SQL needs a UNION arm per artifact kind — which this query has four
of. Correcting it costs the vocabulary its last query-shaped justification, the
outcome `SA-0001` names as a successful one.

Nor does it beat the glossary rival of §4.6.2b: `CONTEXT.md` already is that
glossary. Revisit at v2.5 (§9) only if reconstructibility must be *enforced
continuously* rather than spot-checked — or if Appendix O's spike reopens §1.4.

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
