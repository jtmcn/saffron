---
id: SA-0001
title: Define a factory ontology — a PROV-O/EARL vocabulary for Saffron's run record
type: feature
priority: 3
depends_on: []
touches:
  - ontology/**
  - tests/ontology/**
forbidden:
  - saffron/**
  - pyproject.toml
  - DESIGN.md
budget_usd: 10
max_attempts: 4
risk: elevated
---

## Context

DESIGN.md §11 accepts "no factory analytics" as the price of a SQLite ledger, and
§8's flywheel is where that price is paid: triaging a rejection into gate /
`CLAUDE.md` / lens requires joining an acceptance criterion to a critic finding to
a gate result to a human decision, across four tables and a directory of logs.
Today that join happens in Joel's head, monthly, by rereading
`.saffron/rejections.md`.

An RDF projection of the ledger makes those joins queryable without giving up the
property that made SQLite the right choice — but only if the projection is
**derived and one-way**. The ledger stays authoritative. This spec produces the
*vocabulary and its proof*, not the projection: the emitter, the pyoxigraph store,
and any wiring into `saffron/` are deliberately a later task, because the layer is
only worth building if the queries below turn out to be worth reading.
`ontology/RATIONALE.md` is the artifact that decides that — **"all five queries
have easy SQL equivalents, don't build the emitter" is a successful outcome of this
task, not a failed one**, and is the cheapest form that answer can take.

Rev-2 principle this is meant to respect: the design's own build-order rule. This
is a design artifact validated against hand-authored fixtures, not a subsystem.

## Problem

Saffron has no shared vocabulary for its own run record. The ledger schema (§4.1)
names seven tables in SQL; the run tree (§4.1) names artifacts by file path; the
PR body (§5.7) renders both into prose. Nothing states what an *attempt* is in
relation to a *gate result*, whether an `EXHAUSTED` task's artifacts are reachable
entities, or how a critic's assessment of an acceptance criterion differs in kind
from a `mypy` failure. N5 ("any merged change reconstructible from stored
artifacts alone") is a provenance requirement written in non-provenance words and
is currently unenforceable, because nothing says what "reconstructible" means.

## Acceptance criteria

- [ ] `ontology/saffron.ttl` exists, is valid Turtle, and parses under `pyoxigraph`
      with no network access
- [ ] Batches, runs, tasks, phases, attempts, and gate suites are modelled as
      `prov:Activity`; specs, `plan.json`, `scope.json`, diffs, gate output, and
      PRs as `prov:Entity`; implementer sessions, each critic lens, and the human
      as `prov:Agent`
- [ ] The implementer/critic disagreement of §5.6 is modelled as a
      `prov:qualifiedAssociation`, not as a bare string field
- [ ] Gate results and critic findings are `earl:Assertion`s over an
      `earl:TestSubject`, so a `mypy` failure and a blocker on an acceptance
      criterion carry the same shape
- [ ] Acceptance criteria are first-class entities that a critic assessment can
      attach to individually
- [ ] **No dead terms.** `tests/ontology/test_no_dead_terms.py` asserts that every
      term in the `saffron:` namespace is referenced by at least one query in
      `ontology/queries/` or at least one shape in `ontology/shapes/`. A term that
      exists only in `saffron.ttl` and the fixture graph is unjustified and must be
      deleted, not commented
- [ ] SHACL shapes in `ontology/shapes/` constrain the vocabulary; every shape has
      at least one *negative* fixture that it correctly rejects
- [ ] `tests/ontology/fixtures/` contains a hand-authored graph covering one full
      task lifecycle — including a ratified `SCOPE_REVIEW`, a rebutted critic
      finding, and one `EXHAUSTED` task
- [ ] `ontology/queries/` contains the five SPARQL queries named below, each with a
      committed expected-result fixture
- [ ] `pytest tests/ontology/` runs every query against the fixture graph and
      asserts on results; all five return non-empty
- [ ] **SQL-equivalence challenge.** Each `.rq` file opens with a comment block
      giving either (a) the equivalent query over the §4.1 SQLite schema plus one
      line on why the SPARQL form is preferable, or (b) why no reasonable SQL
      equivalent exists. Speculation about a schema change that *would* make it
      easy in SQL counts as (a), not (b)
- [ ] `ontology/RATIONALE.md` (≤40 lines) tabulates that challenge — one row per
      query, SQL-equivalent yes/no/awkward, verdict — and closes with a bottom-line
      recommendation on whether the RDF layer is worth emitting at all
- [ ] Query Q4 reconstructs a merged change end to end from the fixture graph
      alone, demonstrating N5 as a machine-checkable property
- [ ] No file under `saffron/` is changed — the vocabulary is standalone and is
      not wired into the orchestrator by this task

### The five queries

| | Question it answers | Design ref |
|---|---|---|
| Q1 | For each rejected task, which acceptance criteria failed, and did any gate or lens assert on them? (bucket-triage evidence) | §8 |
| Q2 | Blockers raised per critic lens, split by whether the human agreed — the critic layer's ROI | §11 |
| Q3 | Gates ranked by how often they were the *sole* failure in an attempt, and gates that never fired at all | §8 |
| Q4 | Given a merged PR, the full derivation chain: spec → scope → plan → diff → gate suites → findings → rebuttal → PR | N5 |
| Q5 | Cost per *accepted* PR, grouped by spec type and risk tier | §7.1 |

## Out of scope

The ledger → RDF emitter. The pyoxigraph store and its materialization strategy.
Any change under `saffron/`. A repo-level gate script for term necessity — it rides
the existing `tests` gate. DCAT (the run tree is working artifacts, not a
published catalog — revisit only if a cross-repo artifact catalog is ever wanted).
Importing SWO (cite a handful of its IRIs for tool identity if useful; do not
`owl:imports` it). Modelling individual tool calls. OWL reasoning profiles beyond
RDFS. Publishing the vocabulary at a resolvable IRI.

## Notes for the agent

**No network.** The cell has no default route (§5.1), so PROV-O and EARL cannot be
dereferenced at parse or validation time. Vendored copies are expected at
`ontology/vendor/prov-o.ttl` and `ontology/vendor/earl.ttl`, committed by hand
before this task is queued. If they are absent, stop and raise it as a
`blocking_question` — do not fetch them, and do not stub them.

**Granularity is a decision, not a default.** Model batch / run / task / phase /
attempt / gate suite as activities. Tool calls stay in the plain transcript; modelling
`PreToolUse` events is where the triple count explodes and the queries stop being
fast. If a query below seems to need tool-call granularity, that is a finding worth
reporting, not a licence to add it.

**The failure mode both those criteria exist to catch** is an ontology that is an
isomorphic re-encoding of the §4.1 ledger — one class per table, one datatype
property per column, one object property per foreign key. That is a mechanical
transform (it is what W3C Direct Mapping does), it will pass Turtle parsing and
shape validation, and it is worth nothing: anything expressible over it was already
expressible in SQL. A term earns its place by delivering *alignment* (external PROV
tooling works on it), *qualification* (a relationship becomes a node that can carry
role, plan, time), or an *axiom the schema cannot state* (disjointness, set
containment across rows). An `rdfs:comment` explaining a term's purpose is welcome
but proves nothing and is not an acceptance criterion — prose is the part that is
cheap to fake.

**Do not invent where PROV covers it.** `wasGeneratedBy`, `used`, `wasDerivedFrom`,
`wasRevisionOf`, `wasInvalidatedBy` (useful for `spec_sha` invalidation, §4.1) and
the qualified pattern are the intended backbone. The genuinely Saffron-specific
material — and the only part that justifies a new vocabulary — is the gate taxonomy
with its blocking/advisory split, `envelope` versus ratified `touches`, lens
disjointness, and the terminal-versus-internal state distinction of §3.3.

**`pyproject.toml` is forbidden.** `pyoxigraph` is assumed to be an existing
dependency. If it is not, that is a `blocking_question`, not a dependency edit.

**Size — the likeliest reason this task fails.** `risk: elevated` makes the `size`
gate blocking at the 600-line feature ceiling (§5.6); Turtle is line-hungry and the
SQL-equivalence comment blocks add perhaps 60–80 lines on their own. Keep the
fixture graph to the single lifecycle named above, keep `RATIONALE.md` inside its
40-line cap, and do not pad `rdfs:comment`s. If the diff still cannot fit without
dropping an acceptance criterion, **stop and raise it** — splitting the fixtures and
queries into a follow-up spec is the correct answer, not trimming coverage.

**No new repo gate.** The dead-term check rides the existing blocking `tests` gate
as a pytest. Do not add a script under `gates/`; that path is outside `touches` and
would fail the `scope` gate.

**On the `revert` gate.** Stashing the source hunks here means removing
`saffron.ttl` and the shapes; the shape and query tests must fail without them.
Tests that pass against an empty graph will be caught.
