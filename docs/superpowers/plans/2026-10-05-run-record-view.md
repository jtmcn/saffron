# Run Record View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A read-only `saffron serve` page that shows batches → tasks → phases → attempts → gate results and findings, read from an RDF view projection, with each gate result's failure lines read from the ledger.

**Architecture:** `saffron/view/graph.py` builds a SHACL-checked rdflib graph from a read-only SQLite connection to the ledger. `saffron/view/server.py` loads it into an in-memory `pyoxigraph` store, renders pages from named `.rq` queries in `ontology/queries/view/`, and serves `/sparql` read-only. Failure text never becomes triples.

**Tech Stack:** Python 3.12, stdlib `sqlite3` and `http.server`, `rdflib`, `pyshacl`, `pyoxigraph` 0.5 (all already runtime dependencies), pytest, ast-grep.

**Spec:** `docs/superpowers/specs/2026-10-05-run-record-view-design.md`

## Global Constraints

- Nothing in this work writes the ledger. The view opens it as `file:<path>?mode=ro` with `uri=True`, never through `Ledger`, whose constructor runs `executescript(SCHEMA)`.
- The server binds loopback only (`docs/HOST-HARDENING.md`). A non-loopback host raises `ValueError`.
- No diff viewer, no agent turns, no write path, no action from the page (design, *Not in scope*).
- §1.4 and ADR 5 stand: nothing outside `saffron/cli.py` and `saffron/view/` imports `saffron.view`.
- Every new `factory:` term has a reader in `ontology/queries/**.rq` or `ontology/shapes/` (`tests/ontology/test_no_dead_terms.py`).
- `error` ≠ `fail`: the four gate statuses map one-to-one onto EARL outcomes, `pass`→`earl:passed`, `fail`→`earl:failed`, `error`→`earl:cantTell`, `skip`→`earl:inapplicable`.
- Protected paths (`DESIGN.md`, `CONTEXT.md`, `docs/adr/**`, `docs/appendices/**`, `.saffron/**`, `uv.lock`) are edited by hand, never by a cell.
- Comments are one or two lines of non-obvious why. Docstrings stay within ten lines. Commit subjects are lowercase `type(scope): what changed`, written as a sentence about the defect. No co-author lines.
- Branch names are `joel/<kebab>`, under 50 characters.

## Review Focus

- **A claim or failure message containing `<`, `&` or `"`** must render as text, never as markup. Owned by Task 4: every literal passes through `html.escape`.
- **A gate result with thousands of failure lines** (`failures` is 564 MB) must render the first 200 and a "N more" line, never stall the page. Owned by Task 4.
- **A task whose run has no batch** (213 of the real ledger's runs) must still appear, under "no batch" on `/`. Owned by Tasks 3 and 4.
- **A ledger a running batch is writing** must still be readable. The read-only connection must build while another connection holds an open write transaction. Owned by Task 3.
- **An unknown or non-integer id** in `/batch/<id>` or `/task/<id>` must return 404, not 500. Owned by Task 4.

---

## File Structure

| Path | Responsibility | Task |
|---|---|---|
| `scratchpad/measure_view_build.py` | throwaway timing of a full build over the real ledger | 0 |
| `docs/adr/0009-a-read-only-view-renders-the-run-record-from-the-graph.md` | the decision | 1 |
| `DESIGN.md` §6.2 | the view's place beside the morning queue | 1 |
| `docs/backlog/b-<hash>-the-view-shows-a-night-only-after-it-ends.md` | the live overlay, deferred | 1 |
| `docs/superpowers/specs/2026-10-05-run-record-view-design.md` | amended with the decisions this plan settles | 1 |
| `ontology/factory.ttl` | six new terms | 2 |
| `ontology/shapes/factory-shapes.ttl` | `TaskShape`, `GateShape`, `GateResultShape`, `AttemptShape` changes | 2 |
| `tests/ontology/fixtures/lifecycle.ttl` | an in-flight task, times, turns, failure counts, claims | 2 |
| `tests/ontology/ontology_paths.py` | `QUERIES` includes `queries/view/` | 2 |
| `ontology/queries/view/V1-batches.rq` … `V5-unbatched-tasks.rq` | one query per page fragment | 2 |
| `ontology/queries/expected/V1-batches.csv` … | their committed results | 2 |
| `saffron/view/__init__.py` | empty package marker | 3 |
| `saffron/view/graph.py` | `open_read_only`, `build`, `ViewGraph`, `LeftOut`, `ViewGraphError` | 3 |
| `tests/test_view_graph.py` | the projection against a fixture ledger | 3 |
| `saffron/view/server.py` | `make_server`, pages, `/sparql`, failure lines | 4 |
| `saffron/cli.py` | the `serve` subcommand | 4 |
| `tests/test_view_server.py` | pages, `/sparql`, bind, 404s, escaping | 4 |
| `.saffron/rules/view-is-cli-only.yml`, `.saffron/rule-tests/view-is-cli-only-test.yml` | the import boundary | 5 |

---

### Task 0: Measure a full build over the real ledger

Throwaway. It decides the live overlay's shape (design, *Delivery* step 0), so its number goes into ADR 9.

**Files:**
- Create: `/private/tmp/claude-502/-Users-jm-Code-saffron/aede5d6b-a281-45ee-9eff-922d8ff7b7ff/scratchpad/measure_view_build.py`

- [ ] **Step 1: Write the script**

It approximates the view's triple volume: per task 4 triples, per attempt 8, per gate result 7, per finding 7.

```python
import sqlite3, time
from pathlib import Path
import pyoxigraph as ox
import pyshacl
import rdflib

ROOT = Path("/Users/jm/Code/saffron/.claude/worktrees/atomic-dreaming-sunset")
F = rdflib.Namespace("urn:software-factory:ns#")
D = rdflib.Namespace("urn:software-factory:data:")
db = sqlite3.connect("file:/Users/jm/.saffron/ledger.db?mode=ro", uri=True)

t0 = time.perf_counter()
g = rdflib.Graph()
for (tid, state) in db.execute("SELECT task_id, state FROM tasks"):
    g.add((D[f"task-{tid}"], rdflib.RDF.type, F.Task))
    g.add((D[f"task-{tid}"], F.inState, F[state]))
for (aid, tid, phase, n, cost, turns) in db.execute(
    "SELECT attempt_id, task_id, phase, n, cost_usd_est, num_turns FROM attempts"
):
    a = D[f"attempt-{aid}"]
    g.add((a, rdflib.RDF.type, F.Attempt))
    g.add((a, F.withinPhase, D[f"phase-{tid}-{phase}"]))
    g.add((a, F.n, rdflib.Literal(n)))
    g.add((a, F.costUsdEst, rdflib.Literal(cost or 0)))
    g.add((a, F.numTurns, rdflib.Literal(turns or 0)))
for (gid, aid, gate, status, nfail) in db.execute(
    """SELECT g.gate_result_id, g.attempt_id, g.gate, g.status,
              (SELECT COUNT(*) FROM failures f WHERE f.gate_result_id = g.gate_result_id)
         FROM gate_results g WHERE g.attempt_id IS NOT NULL"""
):
    r = D[f"gate-result-{gid}"]
    g.add((r, rdflib.RDF.type, F.GateResult))
    g.add((r, F.failureCount, rdflib.Literal(nfail)))
    g.add((r, rdflib.RDFS.label, rdflib.Literal(f"{gate}:{status}")))
t1 = time.perf_counter()
data = g.serialize(format="turtle").encode()
t2 = time.perf_counter()
shapes = rdflib.Graph().parse(ROOT / "ontology/shapes/factory-shapes.ttl")
vocab = rdflib.Graph().parse(ROOT / "ontology/factory.ttl")
pyshacl.validate(g, shacl_graph=shapes, ont_graph=vocab, inference="none")
t3 = time.perf_counter()
store = ox.Store()
store.load(data, format=ox.RdfFormat.TURTLE)
t4 = time.perf_counter()
print(f"triples={len(g)} build={t1-t0:.2f}s serialize={t2-t1:.2f}s "
      f"shacl={t3-t2:.2f}s load={t4-t3:.2f}s total={t4-t0:.2f}s")
```

- [ ] **Step 2: Run it**

Run: `uv run python <scratchpad>/measure_view_build.py`
Expected: one line such as `triples=… build=…s … total=…s`. The `COUNT(*)` subquery over `failures` dominates, so note the build time with and without it.

- [ ] **Step 3: Record the decision rule's input**

Total under 10 s: the live overlay rebuilds on each `ledger.db` mtime change. Over 10 s: the live overlay tails `events.jsonl` for running tasks and rebuilds only when a task ends. Write the measured line and the branch taken into ADR 9's *Consequences* (Task 1). Nothing is committed from this task.

---

### Task 1: ADR 9, `DESIGN.md` §6.2, the live-overlay backlog item, and the design amendments

By hand, on `joel/run-record-view`, one PR.

**Files:**
- Create: `docs/adr/0009-a-read-only-view-renders-the-run-record-from-the-graph.md`
- Modify: `DESIGN.md` (append §6.2 after §6.1 *Merge train*)
- Create: `docs/backlog/b-<hash>-the-view-shows-a-night-only-after-it-ends.md`
- Modify: `docs/superpowers/specs/2026-10-05-run-record-view-design.md`

**Interfaces:**
- Consumes: Task 0's measured line.
- Produces: ADR 9's id, cited by SA-0209 and SA-0210. The amended design is what Tasks 2–5 build.

- [ ] **Step 1: Read the format of the records you are about to add**

Run: `sed -n 1,12p docs/adr/0008-*.md; sed -n 1,12p docs/backlog/b-00534f-*.md; uv run python -m records --help`
Expected: the ADR front matter (`id`, `title`, `status`, `date`, `supersedes`, `superseded_by`, `appendices`, `principles`) and the backlog front matter (`id`, `title`, `status`, `tier`, `filed`, `specs`, `prs`, `commits`, `cites`, `related`). If `records` has a `new` subcommand, use it for the backlog id. Otherwise take `b-` plus the first six hex characters of `sha256(title)`.

- [ ] **Step 2: Write ADR 9**

```markdown
---
id: 9
title: "A read-only view renders the run record from the graph"
status: accepted
date: 2026-10-05
supersedes: []
superseded_by: []
appendices: [O, T]
principles: [61]
---

## Context

The morning queue answers which tasks need the operator. It is an index, and
diffs are read on GitHub (§6). It does not answer why a task ended where it
did. That answer sits in the ledger as attempts, gate results and failure
lines, and the operator reads it today with `sqlite3` and `saffron watch`.

Appendix T rebuilt a projection of the run record for Q4 alone. Coverage
follows readers, so the vocabulary states no batch, no timestamp and no gate
outcome.

## Decision

A command, `saffron serve`, renders the run record as pages read from a view
projection. The projection is a second graph beside Q4's. It states every task
in every state, and it never decides whether a chain holds.

The graph holds structure. Failure lines stay in the ledger and are read by
gate result id. The ledger is opened read-only.

Nothing outside `saffron/cli.py` imports `saffron.view`, and a `structure`
rule says so. No page feeds a scheduler, a gate or a state change (ADR 5).

## Consequences

- Six terms join the vocabulary, each read by a view query.
- `GateShape` requires a blocking level only of a declared gate. A gate known
  only from its result carries none, because the policy text is not recorded.
- A full rebuild over the real ledger measured <Task 0 line>. The live overlay
  therefore <rebuilds on each ledger change | tails events.jsonl>.
- The morning queue keeps its job and its sort. §6.2 places the view beside it.
```

Replace both `<…>` with Task 0's result before committing.

- [ ] **Step 3: Write `DESIGN.md` §6.2**

Append after §6.1, renumbering nothing:

```markdown
### 6.2 The run record view

**The queue says which task needs you, and the view says why it ended there.**
`saffron serve` renders batches, tasks, phases, attempts and gate results from
a view projection of the ledger (ADR 9). A gate result opens onto the failure
lines its gate reported, read from the ledger and capped at 200. Diffs stay on
GitHub, and the page writes nothing.
```

- [ ] **Step 4: Write the backlog item**

```markdown
---
id: b-<hash>
title: "The view shows a night only after it ends"
status: open
tier: 3
filed: 2026-10-05
specs: []
prs: []
commits: []
cites: []
related: []
---

## Problem

`saffron serve` builds its graph once at start (ADR 9). A night that is
running shows the state it had when the server started.

## Direction

ADR 9's measured rebuild time decides the shape. Spec it after one night
has been read in the history view.
```

- [ ] **Step 5: Amend the design doc**

Add a section `## Settled while planning` to the design doc, after *Decisions taken in the design session*, with these bullets:

```markdown
- The view reads the ledger through its own `?mode=ro` connection. `Ledger`
  runs its schema on open, so it is never the view's reader.
- A gate status maps one-to-one onto an EARL outcome. `factory:gateStatus`
  is dropped from the vocabulary table.
- `GateShape`'s blocking level moves to declared gates. A core gate is its
  vocabulary individual. A repo gate is a `ContractGate` when its name is a
  gate role, and a `RepoDefinedGate` otherwise.
- Each gated attempt states one `Diff` node, the subject of its gate results.
- A phase and a spec are named by `rdfs:label`. A pull request is
  `rdfs:seeAlso` on its task.
- Failure lines are capped at 200 per gate result, with a count of the rest.
```

In the *Vocabulary* table, delete the `factory:gate, factory:gateStatus` row and replace the claim/verdict/file/line row with `factory:claim`, `factory:verdict` on `Finding`. Add rows `factory:spentUsdEst` on `Batch` and `factory:numTurns` on `Attempt` if they are absent.

- [ ] **Step 6: Render and check**

Run: `uv run python -m ontology.render && make check`
Expected: `DESIGN.md`'s indexes pick up ADR 9 if they index ADRs, and `make check` passes. A failing `prose` hit names its sentence: rewrite that sentence and rerun.

- [ ] **Step 7: Commit and open the PR**

```bash
git add docs/adr/0009-*.md DESIGN.md docs/backlog/b-*-the-view-shows-a-night-only-after-it-ends.md docs/superpowers/specs/2026-10-05-run-record-view-design.md
git commit -m "docs(adr): the run record has no page that says why a task ended where it did"
```

Read `.github/pull_request_template.md`, then `gh pr create --draft` with a body that follows it.

---

### Task 2: Vocabulary, shapes, fixture and view queries

By hand. It rides in SA-0209's spec PR, because `CONTEXT.md` is generated from the vocabulary and is protected. The terms, their readers and their expected results land in one commit.

**Files:**
- Modify: `ontology/factory.ttl` (the *Properties* block, after `factory:role`)
- Modify: `ontology/shapes/factory-shapes.ttl:12-23` (`TaskShape`), `:58-64` (`AttemptShape`), `:90-97` (`GateShape`), `:199-204` (`GateResultShape`), `:73-80` (`BatchShape`), `:186-194` (`FindingShape`)
- Modify: `tests/ontology/fixtures/lifecycle.ttl`
- Modify: `tests/ontology/ontology_paths.py:11`
- Create: `ontology/queries/view/V1-batches.rq`, `V2-batch-tasks.rq`, `V3-task-timeline.rq`, `V4-task-findings.rq`, `V5-unbatched-tasks.rq`
- Create: `ontology/queries/expected/V1-batches.csv` … `V5-unbatched-tasks.csv`

**Interfaces:**
- Produces, for Task 3: the terms `factory:inState`, `factory:numTurns`, `factory:failureCount`, `factory:spentUsdEst`, `factory:claim`, `factory:verdict`. Produces, for Task 4: five queries whose variables are bound with `substitutions`. `V2` binds `?batch`, `V3` and `V4` bind `?task`, and `V1` and `V5` bind nothing.

- [ ] **Step 1: Make the queries discoverable before they exist**

In `tests/ontology/ontology_paths.py` replace line 11:

```python
QUERIES = sorted((ONTOLOGY / "queries").glob("*.rq")) + sorted(
    (ONTOLOGY / "queries" / "view").glob("*.rq")
)
```

Run: `uv run pytest tests/ontology -q`
Expected: PASS, unchanged, because the directory is empty.

- [ ] **Step 2: Write the five queries (the failing tests)**

Each opens with the SQL-equivalence header `test_query_states_its_sql_equivalent` requires.

`ontology/queries/view/V1-batches.rq`:

```sparql
# V1 — every batch, newest first, with its window, stop reason and task count.
# SQL equivalent: a join of batches, runs and tasks with a GROUP BY. SQL is not
# preferable here: the page reads one graph, and a second reader would split it.
PREFIX factory: <urn:software-factory:ns#>
PREFIX prov:    <http://www.w3.org/ns/prov#>
SELECT ?batch ?started ?ended ?because ?budget ?spent (COUNT(?task) AS ?tasks)
WHERE {
  ?batch a factory:Batch ; factory:budgetUsd ?budget .
  OPTIONAL { ?batch prov:startedAtTime ?started }
  OPTIONAL { ?batch prov:endedAtTime ?ended }
  OPTIONAL { ?batch factory:endedBecause ?because }
  OPTIONAL { ?batch factory:spentUsdEst ?spent }
  OPTIONAL { ?run prov:wasInformedBy ?batch . ?task prov:wasInformedBy ?run ; a factory:Task }
}
GROUP BY ?batch ?started ?ended ?because ?budget ?spent
ORDER BY DESC(?started) ?batch
```

`ontology/queries/view/V2-batch-tasks.rq`:

```sparql
# V2 — the tasks of one batch, bound as ?batch, with state, risk, cost and PR.
# SQL equivalent: tasks joined to runs and summed attempts. SQL is not
# preferable here: the state is a vocabulary term, and the page links it.
PREFIX factory: <urn:software-factory:ns#>
PREFIX prov:    <http://www.w3.org/ns/prov#>
PREFIX rdfs:    <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?batch ?task ?spec ?state ?risk ?pr (SUM(?cost) AS ?costUsd)
WHERE {
  ?task a factory:Task ; factory:riskTier ?risk ; prov:wasInformedBy ?run .
  ?run prov:wasInformedBy ?batch .
  { ?task factory:inState ?state } UNION { ?task factory:endedInState ?state }
  OPTIONAL { ?task rdfs:label ?spec }
  OPTIONAL { ?task rdfs:seeAlso ?pr }
  OPTIONAL { ?phase prov:wasInformedBy ?task . ?attempt factory:withinPhase ?phase ;
             factory:costUsdEst ?cost }
}
GROUP BY ?batch ?task ?spec ?state ?risk ?pr
ORDER BY ?batch ?task
```

`ontology/queries/view/V3-task-timeline.rq`:

```sparql
# V3 — one task's attempts, bound as ?task, each with its gate outcomes.
# SQL equivalent: attempts left-joined to gate_results and a failures count.
# SQL is not preferable here: error and fail stay apart as two EARL outcomes.
PREFIX factory: <urn:software-factory:ns#>
PREFIX prov:    <http://www.w3.org/ns/prov#>
PREFIX earl:    <http://www.w3.org/ns/earl#>
PREFIX rdfs:    <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?task ?phase ?phaseName ?attempt ?n ?started ?ended ?turns ?cost ?result ?gate ?outcome ?failures
WHERE {
  ?phase prov:wasInformedBy ?task .
  ?attempt factory:withinPhase ?phase ; factory:n ?n .
  OPTIONAL { ?phase rdfs:label ?phaseName }
  OPTIONAL { ?attempt prov:startedAtTime ?started }
  OPTIONAL { ?attempt prov:endedAtTime ?ended }
  OPTIONAL { ?attempt factory:numTurns ?turns }
  OPTIONAL { ?attempt factory:costUsdEst ?cost }
  OPTIONAL {
    ?suite prov:wasInformedBy ?attempt .
    ?result prov:wasGeneratedBy ?suite ; earl:assertedBy ?gate ;
            earl:result [ earl:outcome ?outcome ] .
    OPTIONAL { ?result factory:failureCount ?failures }
  }
}
ORDER BY ?task ?started ?n ?gate
```

`ontology/queries/view/V4-task-findings.rq`:

```sparql
# V4 — one task's findings, bound as ?task, blockers first.
# SQL equivalent: a filter on findings by task_id. SQL is preferable on its own;
# it is a graph query so the page has one reader and the lens is a term.
PREFIX factory: <urn:software-factory:ns#>
PREFIX prov:    <http://www.w3.org/ns/prov#>
PREFIX earl:    <http://www.w3.org/ns/earl#>
SELECT ?task ?finding ?lens ?severity ?claim ?verdict
WHERE {
  ?finding a factory:Finding ; factory:severity ?severity ; earl:assertedBy ?lens ;
           earl:subject ?diff .
  ?attempt prov:generated ?diff ; factory:withinPhase ?phase .
  ?phase prov:wasInformedBy ?task .
  OPTIONAL { ?finding factory:claim ?claim }
  OPTIONAL { ?finding factory:verdict ?verdict }
}
ORDER BY ?task ?severity ?finding
```

`ontology/queries/view/V5-unbatched-tasks.rq`:

```sparql
# V5 — tasks whose run belongs to no batch: attended cells and replays.
# SQL equivalent: tasks joined to runs WHERE batch_id IS NULL. SQL is not
# preferable here: V2 and this query must partition one graph's tasks.
PREFIX factory: <urn:software-factory:ns#>
PREFIX prov:    <http://www.w3.org/ns/prov#>
PREFIX rdfs:    <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?task ?spec ?state ?risk ?pr
WHERE {
  ?task a factory:Task ; factory:riskTier ?risk ; prov:wasInformedBy ?run .
  ?run a factory:Run .
  FILTER NOT EXISTS { ?run prov:wasInformedBy ?batch . ?batch a factory:Batch }
  { ?task factory:inState ?state } UNION { ?task factory:endedInState ?state }
  OPTIONAL { ?task rdfs:label ?spec }
  OPTIONAL { ?task rdfs:seeAlso ?pr }
}
ORDER BY DESC(?task)
```

- [ ] **Step 3: Run the query tests to see them fail**

Run: `uv run pytest tests/ontology/test_queries.py -q -k V`
Expected: FAIL. `test_query_returns_the_committed_result` cannot find `expected/V1-batches.csv`. `test_query_is_not_empty` fails on `V5`, because the fixture has no run outside a batch.

- [ ] **Step 4: Add the terms**

In `ontology/factory.ttl`, after the `factory:role` property:

```turtle
factory:inState      a owl:ObjectProperty ; rdfs:domain factory:Task ; rdfs:range factory:TaskState ;
    rdfs:comment "The state the ledger holds now, in flight or ended. `endedInState` names only an end." .
factory:numTurns     a owl:DatatypeProperty ; rdfs:domain factory:Attempt ; rdfs:range xsd:integer .
factory:failureCount a owl:DatatypeProperty ; rdfs:domain factory:GateResult ; rdfs:range xsd:integer ;
    rdfs:comment "The count only. The lines stay in the ledger (ADR 9)." .
factory:spentUsdEst  a owl:DatatypeProperty ; rdfs:domain factory:Batch ; rdfs:range xsd:decimal .
factory:claim        a owl:DatatypeProperty ; rdfs:domain factory:Finding ; rdfs:range xsd:string .
factory:verdict      a owl:DatatypeProperty ; rdfs:domain factory:Finding ; rdfs:range xsd:string .
```

- [ ] **Step 5: Change the shapes**

`TaskShape` (lines 12–23) becomes:

```turtle
factory:TaskShape a sh:NodeShape ;
    sh:targetClass factory:Task ;
    sh:or ( [ sh:path factory:endedInState ; sh:minCount 1 ]
            [ sh:path factory:inState ; sh:minCount 1 ] ) ;
    sh:property [ sh:path factory:endedInState ; sh:maxCount 1 ;
        sh:class factory:EndState ;
        sh:in ( factory:SCOPE_REVIEW factory:PLAN_REJECTED factory:EXHAUSTED
            factory:READY_FOR_REVIEW factory:MERGE_FAILED factory:PREFLIGHT_FAILED
            factory:NOT_IMPLEMENTED factory:GATE_ERROR factory:RATE_LIMITED
            factory:SPEC_WITHHELD factory:PROVIDER_UNREACHABLE factory:APPROVED
            factory:CHANGES_REQUESTED factory:REJECTED factory:MERGED
            factory:ORPHANED factory:MERGE_TRAIN ) ] ;
    sh:property [ sh:path factory:inState ; sh:maxCount 1 ; sh:class factory:TaskState ] ;
    sh:property [ sh:path factory:riskTier ; sh:minCount 1 ; sh:maxCount 1 ;
        sh:class factory:RiskTier ; sh:in ( factory:standard factory:elevated ) ] .
```

Above it, change the comment's first line to `# A task states the state it is in, or the one it ended in, and an end state is one it can end in.`

`AttemptShape`: append `sh:property [ sh:path factory:numTurns ; sh:maxCount 1 ; sh:datatype xsd:integer ; sh:minInclusive 0 ] ;` before the `costUsdEst` property.

`BatchShape`: append `sh:property [ sh:path factory:spentUsdEst ; sh:maxCount 1 ; sh:datatype xsd:decimal ] ;`.

`FindingShape`: append `sh:property [ sh:path factory:claim ; sh:maxCount 1 ; sh:datatype xsd:string ] ;` and `sh:property [ sh:path factory:verdict ; sh:maxCount 1 ; sh:datatype xsd:string ] ;`.

`GateShape` (lines 90–97): drop its `blockingAt` property and add a shape for declared gates:

```turtle
factory:GateShape a sh:NodeShape ;
    sh:targetClass factory:Gate ;
    sh:xone ( [ sh:class factory:CoreGate ]
              [ sh:class factory:ContractGate ]
              [ sh:class factory:RepoDefinedGate ] ) .

# A blocking level belongs to a declaration. A gate known only from its result
# carries none, because the ledger keeps the policy's hash and not its text.
factory:DeclaredGateShape a sh:NodeShape ;
    sh:targetObjectsOf factory:declaresGate ;
    sh:property [ sh:path factory:blockingAt ; sh:minCount 1 ; sh:maxCount 1 ;
        sh:class factory:BlockingLevel ;
        sh:in ( factory:alwaysBlocking factory:blockingWhenElevated factory:advisory ) ] .
```

`CoreGateShape` members still carry `blockingAt` in the vocabulary, and `CoreGateBlockingShape` still checks them.

`GateResultShape`: append

```turtle
    sh:property [ sh:path ( earl:result earl:outcome ) ; sh:minCount 1 ; sh:maxCount 1 ;
        sh:in ( earl:passed earl:failed earl:cantTell earl:inapplicable ) ] ;
    sh:property [ sh:path factory:failureCount ; sh:maxCount 1 ;
        sh:datatype xsd:integer ; sh:minInclusive 0 ] ;
```

- [ ] **Step 6: Extend the fixture**

In `tests/ontology/fixtures/lifecycle.ttl`:

```turtle
:batch-1 prov:startedAtTime "2026-01-01T22:00:00Z"^^xsd:dateTime ;
    prov:endedAtTime "2026-01-02T05:10:00Z"^^xsd:dateTime ;
    factory:endedBecause factory:DRAINED ; factory:spentUsdEst 12.40 .
:task-t1 rdfs:label "SA-0001" ; rdfs:seeAlso <https://github.com/o/r/pull/1> .
:at-t1-i1 prov:startedAtTime "2026-01-01T22:05:00Z"^^xsd:dateTime ;
    prov:endedAtTime "2026-01-01T22:30:00Z"^^xsd:dateTime ; factory:numTurns 41 .
:at-t1-i2 prov:startedAtTime "2026-01-01T22:31:00Z"^^xsd:dateTime ;
    prov:endedAtTime "2026-01-01T22:40:00Z"^^xsd:dateTime ; factory:numTurns 12 .
:gr-t1-1-lint factory:failureCount 3 .
:gr-t1-2-lint factory:failureCount 0 .
:finding-t1-1 factory:claim "the retry loop never re-reads the lock" ; factory:verdict "confirmed" .

# An in-flight task: the case the view exists to show and Q4 drops.
:task-t4 a factory:Task ; prov:wasInformedBy :run-1 ; rdfs:label "SA-0004" ;
    factory:riskTier factory:standard ; factory:inState factory:REPAIRING .
:ph-t4-implement a factory:Phase ; prov:wasInformedBy :task-t4 .
:at-t4-i1 a factory:Attempt ; factory:withinPhase :ph-t4-implement ; factory:n 1 ;
    factory:costUsdEst 0.90 ; factory:numTurns 20 .

# An attended cell: a run in no batch, which V5 lists.
:run-2 a factory:Run ; factory:baseSha "8b01d4e" .
:task-t5 a factory:Task ; prov:wasInformedBy :run-2 ; rdfs:label "SA-0005" ;
    factory:riskTier factory:standard ; factory:endedInState factory:EXHAUSTED .
```

Add `@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .` to its prefixes if it is absent. `task-t4` states no `prov:used` spec. If a test or shape requires one of every task, add `prov:used :spec-t1`, the smallest change that satisfies it.

- [ ] **Step 7: Write the expected results from the fixture, then read them**

```bash
uv run python - <<'PY'
import pyoxigraph as ox
from pathlib import Path
s = ox.Store()
for p in ["ontology/factory.ttl", "tests/ontology/fixtures/lifecycle.ttl", *map(str, Path("ontology/vendor").glob("*.ttl"))]:
    s.bulk_load(path=p, format=ox.RdfFormat.TURTLE)
for q in sorted(Path("ontology/queries/view").glob("*.rq")):
    out = s.query(q.read_text()).serialize(format=ox.QueryResultsFormat.CSV).decode()
    Path(f"ontology/queries/expected/{q.stem}.csv").write_text(out.replace("\r\n", "\n"))
PY
cat ontology/queries/expected/V*.csv
```

Expected: `V1` has one row for `batch-1` with `tasks` = 4. `V2` has `task-t4` with state `REPAIRING`. `V3` has `lint` on `at-t1-i1` with `earl:failed` and `3`. `V4` has the confirmed blocker's claim first. `V5` has `task-t5` alone. A row that contradicts the fixture means the query is wrong: fix the query, never the CSV.

- [ ] **Step 8: Run the ontology suite and render**

Run: `uv run python -m ontology.render && uv run pytest tests/ontology -q && .saffron/gates/shacl`
Expected: PASS. `test_no_dead_terms` passes because the queries name every new term. `test_generated_surfaces_are_current` passes after render. If `shacl` lists a negative fixture under `tests/ontology/fixtures/negative/` that now validates, because it relied on `GateShape.blockingAt`, retarget its gate as an object of `factory:declaresGate`.

- [ ] **Step 9: Commit on the spec branch**

This commit lands on SA-0209's spec branch (Task 3, step 1), never on `main` directly.

```bash
git add ontology tests/ontology CONTEXT.md
git commit -m "feat(ontology): the vocabulary states no task in flight, no gate outcome and no batch window"
```

---

### Task 3: SA-0209, the view projection (through a cell)

**Files:**
- Create: `.saffron/specs/SA-0209-the-run-record-has-no-graph-that-states-a-task-in-flight.md` (by `create-saffron-spec`)
- Create (by the cell): `saffron/view/__init__.py`, `saffron/view/graph.py`, `tests/test_view_graph.py`

**Interfaces:**
- Consumes: Task 2's terms and shapes. From `saffron/projection.py`: `NS`, `DATA_NS`, `VOCABULARY`, `DEFAULT_SHAPES`.
- Produces, for Task 4:

```python
# saffron/view/graph.py
@dataclass(frozen=True)
class LeftOut:
    task_id: int
    spec_id: str
    reason: str          # "unknown_state" | "unknown_risk" | ...

@dataclass(frozen=True)
class ViewGraph:
    turtle: bytes        # the validated graph, serialized
    left_out: list[LeftOut]

class ViewGraphError(Exception):
    """The graph failed the shapes; the message is pyshacl's report."""

def open_read_only(path: Path) -> sqlite3.Connection: ...
def build(db: sqlite3.Connection, *, shapes_path: Path = DEFAULT_SHAPES) -> ViewGraph: ...
```

IRIs the server relies on: `data:batch-<batch_id>`, `data:run-<run_id>`, `data:task-<task_id>`, `data:phase-<task_id>-<phase>`, `data:attempt-<attempt_id>`, `data:gatesuite-<attempt_id>`, `data:gate-result-<gate_result_id>`, `data:diff-attempt-<attempt_id>`, `data:finding-<finding_id>`, `data:lens-<lens>`, `data:gate-<name>` for a repo gate, and `factory:<name>` for a core gate.

- [ ] **Step 1: Write the spec through the chain**

Invoke the `create-saffron-spec` skill with this brief. The skill runs its pre-flight, the writer and the reviewer rounds. Task 2's commit goes on the spec's branch before the first review.

> SA-0209. Cite ADR 9 and the design doc. `touches`: `saffron/view/**`, `tests/test_view_graph.py`. Build `saffron/view/graph.py` with exactly the interface above. `build` reads `tasks`, `runs`, `batches`, `attempts`, `gate_results` (attempt-bound only), a `COUNT(*)` of `failures` per gate result, and `findings`. It states:
> - every batch with `budgetUsd`, `spentUsdEst` when it is not null, `prov:startedAtTime`, `prov:endedAtTime` when it is not null, and `endedBecause` when `status` is not null;
> - every run with `baseSha` and `prov:wasInformedBy` its batch when `batch_id` is not null;
> - every task with `inState`, plus `endedInState` when the state is an end state, `riskTier`, `rdfs:label` spec_id, `rdfs:seeAlso` pr_url when not null, and `prov:wasInformedBy` its run;
> - every attempt with `withinPhase`, `n`, `costUsdEst` when not null, `numTurns` when not null, and both times, with the phase labelled by its name;
> - for each attempt that has gate results, one `GateSuite`, one `Diff` (`data:diff-attempt-N`, `prov:generated` by the attempt), and one `GateResult` per row: `earl:assertedBy` the gate node, `earl:subject` the diff, `earl:mode earl:automatic`, `earl:result [ earl:outcome … ]` by the one-to-one map in the Global Constraints, and `failureCount`;
> - for each finding, its `severity`, `earl:assertedBy` the lens, `earl:subject` the diff of the task's last gated attempt, `earl:mode earl:semiAuto`, `claim`, and `verdict` when not null. A task with findings and no gated attempt leaves its findings out, with a `LeftOut` reason `findings_without_diff`, and keeps the task.
>
> A gate node is `factory:<name>` when the name is a `CoreGate` individual. Otherwise it is `data:gate-<name>`, a `ContractGate` with `factory:role factory:<name>` when the name is a `GateRole` member, and a `RepoDefinedGate` otherwise. Read both sets from the shapes with `projection._sh_in`'s approach, never as a literal list.
>
> A task whose state or risk is not in the shapes' sets is left out, with reason `unknown_state` or `unknown_risk`. The rest are still stated. The whole graph is validated with `pyshacl` against the shapes and the vocabulary. Failure raises `ViewGraphError` carrying the report text. `open_read_only` returns `sqlite3.connect(f"file:{path}?mode=ro", uri=True)` with `row_factory = sqlite3.Row`. Nothing in `saffron/view/` imports `saffron.ledger.Ledger` except tests.

- [ ] **Step 2: Make sure the spec's acceptance criteria name these tests**

The reviewer checks that each criterion has a witness test. These are the witnesses, and the spec quotes their names. Each test builds its fixture ledger with `Ledger(tmp_path / "ledger.db")` (writes are fine in a test), closes it, then calls `build(open_read_only(...))`. Import `saffron.view.graph` inside each test body, never at module scope, for the reason `tests/test_projection.py`'s docstring gives.

```python
def test_an_in_flight_task_is_stated_with_its_state(tmp_path): ...
    # a REPAIRING task → (task, factory:inState, factory:REPAIRING), no endedInState
def test_an_ended_task_states_both_its_state_and_its_end(tmp_path): ...
def test_a_task_whose_run_has_no_batch_is_still_stated(tmp_path): ...
def test_each_gate_status_maps_to_its_own_earl_outcome(tmp_path): ...
    # four gate results pass/fail/error/skip → four distinct outcomes
def test_a_gate_result_counts_its_failures_and_states_no_line(tmp_path): ...
    # 3 failure rows → failureCount 3, and no failure message appears in turtle
def test_a_core_gate_is_its_vocabulary_individual_and_a_repo_gate_is_typed_by_role(tmp_path): ...
def test_a_task_in_an_unknown_state_is_left_out_and_the_rest_are_stated(tmp_path): ...
    # UPDATE tasks SET state='NOT_A_STATE' via raw sqlite3 before build
def test_findings_without_a_gated_attempt_are_left_out_and_the_task_kept(tmp_path): ...
def test_the_graph_passes_the_shapes(tmp_path): ...
def test_build_reads_a_ledger_another_connection_is_writing(tmp_path): ...
    # a second sqlite3 connection holds BEGIN IMMEDIATE + an INSERT, uncommitted
def test_the_connection_cannot_write(tmp_path): ...
    # open_read_only(...).execute("INSERT INTO repos ...") raises sqlite3.OperationalError
```

- [ ] **Step 3: Merge the spec PR, then run the cell**

```bash
gh pr ready <spec-pr> && gh pr merge <spec-pr> --squash
env CLAUDE_CODE_OAUTH_TOKEN=(bash -c 'source ~/.secrets; printf %s $CLAUDE_CODE_OAUTH_TOKEN') \
  uv run saffron cell .saffron/specs/SA-0209-*.md --repo .
```

Expected: exit `0` and a draft PR. Exit `1` means the task did not make it: read `saffron watch SA-0209 --no-follow`, revise the spec through the chain, and rerun. Exit `2` is infrastructure.

- [ ] **Step 4: Review the PR against this task's interface**

Check that the names and types match the *Produces* block exactly, because Task 4's spec is written against them. Then run the real ledger through it:

```bash
uv run python -c "from pathlib import Path; from saffron.view.graph import build, open_read_only; v = build(open_read_only(Path.home()/'.saffron/ledger.db')); print(len(v.turtle), len(v.left_out), {l.reason for l in v.left_out})"
```

Expected: no `ViewGraphError`, and few `left_out` entries, each with a reason you can explain. Compare the time with Task 0's.

---

### Task 4: SA-0210, `saffron serve` (through a cell)

**Files:**
- Create: `.saffron/specs/SA-0210-the-run-record-view-has-no-page.md` (by `create-saffron-spec`, with `depends_on: SA-0209`)
- Create (by the cell): `saffron/view/server.py`, `tests/test_view_server.py`
- Modify (by the cell): `saffron/cli.py` (subparser beside `chains`, dispatch beside `fold`)

**Interfaces:**
- Consumes: `build`, `open_read_only`, `ViewGraph`, `LeftOut`, `ViewGraphError` from Task 3. The five view queries from Task 2, by file name.
- Produces:

```python
# saffron/view/server.py
FAILURE_LINE_CAP = 200

def make_server(ledger_path: Path, *, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    """Builds the graph once, loads it into a pyoxigraph Store, and returns an
    unstarted server. Raises ValueError for a non-loopback host and
    ViewGraphError for a graph that fails the shapes."""
```

CLI: `saffron serve [--port N]`. Exit `2` with one line when `~/.saffron/ledger.db` is absent. Exit `2` and print the SHACL report when the graph fails the shapes. Otherwise it serves until interrupted and exits `0`.

- [ ] **Step 1: Write the spec through the chain**

Invoke `create-saffron-spec` with this brief:

> SA-0210, `depends_on: SA-0209`. Cite ADR 9 and the design doc. `touches`: `saffron/view/server.py`, `saffron/cli.py`, `tests/test_view_server.py`. Build `make_server` with exactly the interface above, on stdlib `http.server.ThreadingHTTPServer`. Accept a host only when `ipaddress.ip_address(host).is_loopback` or it equals `"localhost"`.
>
> Pages are rendered with f-strings in the style of `saffron/report/index.py`, with every literal passed through `html.escape`.
> - `GET /`: `V1`'s rows, then a "no batch" section from `V5`, then a "left out" panel listing each `LeftOut` with its reason.
> - `GET /batch/<id>`: `V2` with `substitutions={ox.Variable("batch"): ox.NamedNode(DATA_NS + f"batch-{id}")}`.
> - `GET /task/<id>`: `V3` and `V4` bound on `?task`. Under each gate result whose `failureCount` > 0, the first `FAILURE_LINE_CAP` rows of `SELECT file, line, code, message FROM failures WHERE gate_result_id = ? ORDER BY failure_id`, plus "N more" when it is capped. The page links the task's PR from `rdfs:seeAlso`.
> - `GET /sparql?query=…`: the result as SPARQL JSON when the result is `ox.QuerySolutions` or `ox.QueryBoolean`. Otherwise 400. A query that fails to parse is 400 with the parser's message. `POST` anywhere is 405.
>
> An id that is not an integer, or names no batch or task, is 404. The ledger connection is Task 3's `open_read_only`, used only from the request thread that opened it, or opened per request.
>
> In `cli.py`, add a `serve` subparser with `--port` (int, default 8765). Dispatch it before `Ledger(args.home / "ledger.db")` is constructed, as `fold` is, so `serve` never creates or migrates a ledger. Import `saffron.view.server` inside the dispatch function, as `_chains` defers its graph imports.

- [ ] **Step 2: Make sure the spec's acceptance criteria name these tests**

Each test starts `make_server(ledger, port=0)` on a thread, reads `server.server_address`, and fetches with `urllib.request`. It builds its fixture ledger as Task 3's tests do.

```python
def test_the_index_lists_each_batch_and_the_tasks_with_no_batch(tmp_path): ...
def test_the_index_lists_each_left_out_task_with_its_reason(tmp_path): ...
def test_a_batch_page_lists_only_that_batchs_tasks(tmp_path): ...
def test_a_task_page_shows_each_attempts_gate_outcomes_with_error_apart_from_fail(tmp_path): ...
def test_a_task_page_shows_failure_lines_capped_with_a_count_of_the_rest(tmp_path): ...
    # 205 failure rows → 200 rendered and "5 more"
def test_a_claim_with_markup_renders_as_text(tmp_path): ...
    # claim '<script>x</script>' → '&lt;script&gt;' in the body, no '<script>'
def test_an_unknown_or_malformed_id_is_404(tmp_path): ...
    # /task/99999, /task/abc, /batch/-1
def test_sparql_answers_a_select(tmp_path): ...
def test_sparql_refuses_an_update_and_a_construct(tmp_path): ...
    # 'INSERT DATA { <a:a> <a:b> <a:c> }' → 400; 'CONSTRUCT WHERE { ?s ?p ?o }' → 400
def test_a_non_loopback_host_raises(tmp_path): ...
    # make_server(ledger, host="0.0.0.0") raises ValueError
def test_serve_exits_2_and_prints_the_report_when_the_graph_fails_the_shapes(tmp_path, monkeypatch, capsys): ...
    # monkeypatch build to raise ViewGraphError("report text") → 2, "report text" in stdout
def test_serve_exits_2_when_there_is_no_ledger(tmp_path): ...
    # cli.main(["--home", str(tmp_path), "serve"]) == 2, and no ledger.db is created
```

- [ ] **Step 3: Add Task 5's rule to this spec's PR before it merges**

Task 5 is protected, so it goes in by hand on the spec branch.

- [ ] **Step 4: Merge the spec PR, then run the cell, stacked on SA-0209**

```bash
gh pr ready <spec-pr> && gh pr merge <spec-pr> --squash
env CLAUDE_CODE_OAUTH_TOKEN=(bash -c 'source ~/.secrets; printf %s $CLAUDE_CODE_OAUTH_TOKEN') \
  uv run saffron cell .saffron/specs/SA-0210-*.md --repo .
```

Expected: exit `0`. SA-0209 is at `READY_FOR_REVIEW` or later, so the child is cut from its branch (§4.2).

- [ ] **Step 5: Use it on the real ledger**

```bash
uv run saffron serve --port 8765
```

Open `http://127.0.0.1:8765/`. Check one merged task, one `EXHAUSTED` task and the `REPAIRING` one: each page must say why the task ended where it did. Any gap you find becomes a review finding on the PR, never a hand edit to the cell's branch.

---

### Task 5: The import boundary as a `structure` rule

By hand, on SA-0210's spec branch (Task 4, step 3), after SA-0209 merges. `.saffron/**` is protected.
It cannot land earlier: `test_every_rules_path_scope_still_reaches_a_file` fails while `saffron/view/` is absent (measured 2026-10-05).
A ready patch sits in the plan's workspace as `0001-feat-rules-a-module-outside-the-cli-could-import-the.patch`.

**Files:**
- Create: `.saffron/rules/view-is-cli-only.yml`
- Create: `.saffron/rule-tests/view-is-cli-only-test.yml`
- Modify: `CLAUDE.md` *Invariants*, one bullet marked **(gated over `saffron/`)** naming `view-is-cli-only` (`test_every_gated_rule_is_named_in_claude_md`)
- Modify: `tests/test_saffron_gates.py:669`, add `"view-is-cli-only": ["saffron/cli.py", "saffron/view/**"]` to the expected exemptions (`test_a_rules_exemptions_are_the_named_files`)

- [ ] **Step 1: Write the rule test first**

```yaml
id: view-is-cli-only
valid:
  - 'import json'
  - 'from saffron.projection import NS'
  - 'note = "saffron.view renders the record"'
invalid:
  - 'import saffron.view.server'
  - 'from saffron.view.graph import build'
  - 'from saffron.view import graph'
  - 'importlib.import_module("saffron.view.graph")'
```

- [ ] **Step 2: Run it to see it fail**

Run: `uv run ast-grep test -c .saffron/sgconfig.yml`
Expected: FAIL, `view-is-cli-only` has no rule.

- [ ] **Step 3: Write the rule**

```yaml
id: view-is-cli-only
language: python
severity: error
message: only saffron/cli.py may import saffron.view
note: |
  The view reads the run record and decides nothing (ADR 9, ADR 5). A second
  importer is how a page's query becomes a scheduler's input.
files:
  - "saffron/**/*.py"
ignores:
  - "saffron/cli.py"
  - "saffron/view/**"
rule:
  any:
    - kind: import_statement
      has: { regex: '^saffron\.view', stopBy: end }
    - kind: import_from_statement
      has: { field: module_name, regex: '^saffron\.view' }
    - kind: call
      all:
        - has: { field: function, regex: '(^|\.)import_module$|^__import__$' }
        - has:
            field: arguments
            has:
              kind: string
              nthChild: 1
              has: { kind: string_content, regex: '^saffron\.view' }
```

- [ ] **Step 4: Run the rule tests, then the gate over the tree**

Run: `uv run ast-grep test -c .saffron/sgconfig.yml --update-all && uv run ast-grep test -c .saffron/sgconfig.yml && .saffron/gates/structure`
Expected: PASS, and the gate reports no hit in the tree.

- [ ] **Step 5: Prove it fires on the tree, then revert**

```bash
echo 'from saffron.view.graph import build' >> saffron/batch.py
.saffron/gates/structure; git checkout saffron/batch.py
```

Expected: the gate reports `fail` naming `saffron/batch.py` and `view-is-cli-only`.

- [ ] **Step 6: Commit on SA-0210's spec branch**

```bash
git add .saffron/rules/view-is-cli-only.yml .saffron/rule-tests/view-is-cli-only-test.yml .saffron/rule-tests/__snapshots__
git commit -m "feat(rules): a module outside the cli could import the view and read its graph as input"
```
