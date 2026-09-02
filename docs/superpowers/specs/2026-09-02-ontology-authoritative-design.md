# The ontology becomes authoritative — design

The run record has a vocabulary (`ontology/saffron.ttl`) and a glossary
(`CONTEXT.md`), and they overlap on five closed sets that are asserted equal and
nothing else. This design makes the vocabulary authoritative for the run record,
generates the glossary's run-record half from it, and emits the run record
itself as a graph so that a knowledge graph has a producer.

> **Citations:** a bare `§` cites `DESIGN.md`, per repo convention. This
> document's own sections are cited as *part N*; the operator-visibility
> plan's parts are always named as *the plan's part N*.

**It supersedes `ontology/RATIONALE.md`'s bottom line**, deliberately and on
stated grounds (part 1). That document is eight days old and its measurements
are not disputed; the question it asked is not the question being asked now.

## What was measured

Run, not reasoned. Every number below came from this repo at `6a7bdd9`.

- **The two documents overlap far less than they appear to.** Of the 27 terms
  `CONTEXT.md` defines in its run-record sections (that file's own §4
  Verification, §5 Review and §6 Outcomes — not `DESIGN.md` numbering), **8 exist in the graph and 19 do not**: `Gate contract`,
  `Status`, `Baseline`, `New failure`, `Pre-existing failure`, `Repair`,
  `No-progress`, `Critic`, `Implementer`, `Lens`, `Anchored`, `Verdict`,
  `Adjudication`, `Ratify`, `Approve`, `Trailing accept rate`, `Merge train`,
  `Stacked branch`, `Tree base`.
- **The graph is declarations, not prose.** 76 `saffron:` terms; **10** carry an
  `rdfs:comment`. `CONTEXT.md` is 501 lines, ~88 bolded terms, 56 `_Avoid_`
  lists and 24 lines of rationale block quote.
- **The graph is the side that has already drifted.** `saffron:TerminalState`'s
  comment says *"CONTEXT.md §6 lists six of these and DESIGN.md §3.3 lists
  nine"*. `CONTEXT.md` now lists nine. The prose in the graph is stale about the
  very disagreement it was written to record.
- **Declaring one gate on one side alone fails the suite.** Appending
  `saffron:revert a saffron:CoreGate` to `ontology/saffron.ttl` and running
  `tests/ontology/`: `1 failed, 6 passed`, `Extra items in the right set:
  'revert'`. `CONTEXT.md` is `forbidden` to every spec in flight, so a cell
  cannot repair it. This is the concrete defect that started the design.
- **`saffron/` has two runtime dependencies**, `pydantic` and `pyyaml`.
  `pyproject.toml` states the reason graph libraries are not among them:
  *"pyoxigraph and pyshacl are test-only … nothing under `saffron/` imports
  either (the emitter is a later, conditional task)."*
- **Two of RATIONALE's five verdicts rest on conditions still unmet.** Q1 is
  *"SQL, once a `criteria` table exists"*; Q3 *"once declared gates are
  stored"*. The ledger holds `repos, runs, tasks, attempts, gate_results,
  failures, findings`. There is no `criteria` table.
- **The plan's part 3 renderer does not exist.** `saffron/report/` holds `__init__.py`,
  `index.py`, `pr_body.py`. `render.py` — the file `SA-0035`–`SA-0039` all
  write to — is unwritten. This is the deadline in part 4.

## 1. Superseding `ontology/RATIONALE.md`

RATIONALE scored one question: *is the RDF layer worth emitting, given five
analytical queries?* It answered five of five for SQL, and added that the graph
does not beat *"the glossary rival of §4.6.2b: `CONTEXT.md` already is that
glossary."* Both conclusions are correct for that question.

Three things changed.

1. **The question.** A knowledge graph is now a goal in its own right, not a
   means of answering five queries faster. RATIONALE never evaluated that, so it
   does not govern it.
2. **Two of its conditions went unmet.** Q1 and Q3 were conditional on schema
   that still does not exist (*What was measured*). As things stand, Q1 remains
   *"awkward — criteria are markdown checkboxes, in no table."*
3. **A sixth consumer appeared.** Part 3 of `2026-08-31-operator-visibility.md`
   is an unwritten query-and-render layer over the run record. RATIONALE scored
   five queries with no renderer in view.

**RATIONALE's table is kept intact, and the revisit lives here, not there.**
`ontology/RATIONALE.md` is capped at 40 lines by
`tests/ontology/test_vocabulary.py::test_rationale_is_within_its_cap_and_covers_every_query`,
and the file is *exactly* at that cap — the cap is an acceptance criterion of
`SA-0001`, and a full file is what it is saying. Appending the revisit was tried
and failed the suite. So the record of why the verdict moved is this document,
and making it discoverable from RATIONALE.md is an open question (part 6).

## 2. Two authorities, not one

The framing that collided with RATIONALE was "the ontology is authoritative".
Authoritative over *what* is the whole question, and there are two answers:

- **The ontology is authoritative for vocabulary** — what the words mean.
- **The ledger is authoritative for facts** — what happened in a run.

Conflating them is what made the earlier framing read as a bid to replace
`CONTEXT.md` wholesale, which RATIONALE had already refused. Separated, the two
axes share the ontology and nothing else, and each can be built or abandoned
without the other.

## 3. The graph is a derived read model

```
cells ──▶ ledger.db  (SQL, write path, unchanged)
              │
              └─ emitter ──▶ run-record graph (N-Triples) ──▶ SPARQL ──▶ report
ontology/saffron.ttl (vocabulary) ──▶ generator ──▶ CONTEXT.md (+ drift gate)
```

**The ledger stays the system of record; the graph is projected from it.** Four
consequences, each load-bearing:

- **It preserves what RATIONALE actually defended.** Its case was that SQL
  serves the write path. Nothing here disputes that. A read model is additive,
  so abandoning it costs one module and no data.
- **The emitter needs no new dependency.** N-Triples is line-based — one
  `<s> <p> <o> .` per line — so *writing* it needs no library. Only *reading*
  needs an engine, and reading happens in the report path, which never runs in a
  cell. `pyoxigraph` becomes an optional `saffron[graph]` extra, not a runtime
  dependency, and `pyproject.toml`'s stated constraint holds.
- **The emitter reads the ledger and never writes it.** A bad emit costs one
  command re-run and cannot corrupt the record.
- **`test_no_dead_terms` stops being an obstacle and becomes the mechanism.**
  Its rule — every `saffron:` term is referenced by a query or a shape, so that
  the vocabulary is not *"an isomorphic re-encoding of the §4.1 ledger worth
  nothing"* — is exactly the right bar. The 19 orphan terms earn their place by
  being emitted and queried by a renderer that really reads them. **No exemption
  class, and no thin queries written to clear the gate.**

## 4. Sequencing, and the deadline

**This is two projects sharing one ontology, and they get separate plans.**
Phase A is the vocabulary axis; Phases B–D are the run-record axis. They share
`ontology/saffron.ttl` and nothing else — no module, no test, no schema. Phase A
can ship, or be abandoned, without touching the emitter, and vice versa. Writing
them as one plan would couple two things whose only real link is a file name.

**Phase A — vocabulary.** Marker-delimited regions in `CONTEXT.md`'s run-record
sections, a generator, and a drift test. Migrate the five closed sets *first*,
because they are already asserted equal: a faithful generator produces a
**zero-line diff**, which proves the renderer before it is trusted with anything
new. Then promote terms as they earn readers. Independent of every later phase.

**Phase B — the emitter.** `saffron/graph/emit.py`, validated by the **existing**
SHACL shapes. The shapes, their lifecycle fixture and their negative fixtures
are already written and tested; emitter correctness is validation against them
rather than a new assertion framework.

**Phase C — the honest check.** Port `Q1`–`Q5` to run against *emitted* graphs
instead of the hand-written fixture, and compare to the committed
`ontology/queries/expected/*.csv`. **This phase can invalidate the premise.** If
the queries are as painful as RATIONALE found, that is grounds to stop: keep the
graph as an external analytical artifact and leave the plan's part 3 on SQL. Phase C is
placed before the plan's part 3 depends on anything precisely so that stopping is cheap.

**Phase D — the plan's part 3, on the graph.** `SA-0035` becomes *"the queue's rows, from
the graph"*; `SA-0036`–`SA-0039` follow.

**The deadline.** `saffron/report/render.py` is unwritten. Building it
graph-first costs nothing extra today. Once `SA-0035`/`SA-0036` land against
SQL, it is a rewrite of shipped, gated, reviewed code. The whole
"foundational versus bolted-on" question reduces to that date.

**`2026-08-31-operator-visibility.md` is amended, not forked.** `SA-0035`'s
embedded spec text says "from the ledger", and the plan's part 3 dependency chain shifts.
That plan has been renumbered twice already and says so; a fork would make a
third numbering the reader has to reconcile.

## 5. Testing

- **Emitter:** SHACL validation of emitted triples against the existing shapes.
- **Round trip:** known ledger fixture → emit → query → assert against the
  committed `expected/*.csv`.
- **Generator:** the committed `CONTEXT.md` equals the render. The first
  migration must produce a zero-line diff (part 4, Phase A).
- **Escaping is a security boundary, not formatting.** Findings and claims are
  agent-authored and become RDF literals. A cell is untrusted, so a claim
  containing a quote, a backslash or a newline must not be able to forge a
  triple. A test asserts it, in the same spirit as `SA-0038`'s requirement that
  an event carrying `<script>` render inert.
- **Absent inputs are normal.** Every task that ran before `SA-0029` has no
  `events.jsonl`. The emitter projects those tasks from SQL alone.
- **Off the critical path:** a failed emit never fails a task. The graph is
  derived and projected after the fact, so the emitter stays outside the
  `error`/`fail` vocabulary rather than becoming a gate.

## 6. What stays open, and is stated rather than closed

- **The 56 `_Avoid_` lists stay hand-written.** They are enforced by a prek hook
  reading `CONTEXT.md`'s settled-naming section. Modelling them in RDF would
  mean rewriting that hook to read the graph, and nothing yet needs it.
- **Whole-system vocabulary stays in `CONTEXT.md`.** Only the run-record
  sections are generated. `CONTEXT.md` names the whole system — repos, style,
  the flywheel — and the graph names only the run record. That split is
  `test_vocabulary_agrees_with_context.py`'s own stated premise and this design
  keeps it.
- **The `revert` gate's declaration.** `SA-0044` currently must not declare
  `saffron:revert`, because the two sides cannot be reconciled from inside a
  cell. Phase A removes that constraint. Until then the spec carries a note
  saying so.

- **A superseded document that does not say so.** `ontology/RATIONALE.md` still
  reads as current, and its 40-line cap leaves no room for a pointer. Three ways
  out, none taken here: raise the cap by one line and amend `SA-0001`'s
  criterion; spend one of the 40 lines on the pointer, editing the record to
  describe its own supersession; or leave it and rely on this document being
  found first. The third is what ships today and it is the weakest, so this is
  the first thing to settle, not the last.

## 7. Success criterion

A new core gate can be declared in `ontology/saffron.ttl` alone, and
`CONTEXT.md` updates from it with the suite green — the defect measured above,
closed. And `Q1`–`Q5` run against a graph the emitter produced from a real
ledger, not a fixture written by hand.
