# Is the RDF layer worth emitting?

One row per query, challenged against the §4.1 schema. "Would need a column" counts
as a SQL win, per `SA-0001` — speculation about a schema change that *would* make it
easy is answer (a).

| | SQL equivalent | Verdict |
|---|---|---|
| Q1 acceptance criteria on rejected tasks | Awkward — criteria are markdown checkboxes, in no table | **SQL, once a `criteria` table exists.** The RDF win is only that a gate and a lens reach a criterion through one join instead of two |
| Q2 blockers per lens, split by adjudication | Yes — `findings.adjudication` landed in rev 6 for this | **SQL.** The graph carries *who* held each position; the count does not need it |
| Q3 sole failures, and gates that never fired | Half. Sole-failure is a correlated subquery either way; "never fired" needs the declared set, which preflight parses and drops | **SQL, once declared gates are stored.** Same shape as Q1 |
| Q4 derivation chain of a merged PR | No. Each hop lands in a different table, so a recursive CTE has no edge relation to recurse over | **RDF.** One property path against one UNION arm per artifact kind |
| Q5 cost per accepted PR | Yes, easily | **SQL.** Included as the control |

## Bottom line: don't build the emitter.

Four of five are SQL questions, two of them only after a column the ledger should
have anyway. Q4 is the single query with no reasonable relational form — and N5 is
a property to spot-check when a merge looks wrong, not one to materialize a graph
store for nightly. Revisit at v2.5 (§9) only if reconstructibility has to be
*enforced continuously*; the vocabulary is committed and the emitter stays cheap
to write later.

It also does not beat the glossary rival of §4.6.2b, because Saffron already has
the glossary: `CONTEXT.md`, with the `_Avoid_` lists doing exactly the work prior
art reached for. The ontology had to earn the delta over it and earned one query.

## What the modelling found anyway, which is the part that paid

- **`earl:mode` is the axis §4.1 conflated.** `gate_results` and `findings` split on
  *how* an assertion was produced — deterministic versus not — which EARL states in
  one property over one class. That is the supertype `CONTEXT.md`'s open naming
  decision says cannot currently be written in Saffron's own vocabulary; it can be
  written in EARL's. Reconcile the two tables in §4.1 and the word follows.
- **The operator's rejection is an assertion too.** Modelled in the same shape as a
  `mypy` failure, "the operator rejected on a criterion nothing automatic had
  reached" becomes Q1 rather than a monthly reread. `decisions` cannot say it.
- **`prov:wasInvalidatedBy` is deliberately unmodelled**, though §4.6 names
  `spec_sha` invalidation as its natural fit. Nothing asks the question, and a term
  with no reader is what the dead-term test deletes.
