# Run record view: batches and tasks in a browser, read from the graph

Date: 2026-10-05. Decision record: ADR 9, written as step 1 below.

## Intent

The operator wants to see the task queue and its batches in a web page. A
page per task shows its phases, its attempts, and each attempt's gate results.
A gate result opens onto the failure lines the gate reported. The page reads
the RDF graph, so the vocabulary gains a reader that shows the run record.

History comes first. A live overlay for a running night follows later. The
history design must take that overlay without rework.

Success is one question answered from the page alone. Why did this task end
where it did, attempt by attempt?

## What exists at `96afa54b`

- `ontology/factory.ttl` names `Batch`, `Run`, `Task`, `Phase`, `Attempt`,
  `GateSuite`, `GateResult` and `Finding`, with the task states and stop reasons.
- `saffron/projection.py` writes a Turtle projection for Q4 (Appendix T).
  It keeps only ended tasks whose chain can be attributed. It states no batch,
  no timestamp, and no gate result.
- `saffron chains` loads that projection into `pyoxigraph`. The graph libraries
  are runtime dependencies already.
- The morning queue is a static `index.html` that reloads every 60 seconds
  (`saffron/report/index.py`). It is an index and never a viewer (§6).
- The real ledger holds 225 tasks and about 8,000 gate results. Its `failures`
  table is 564 MB of the 670 MB file.

## Decisions taken in the design session

1. **History first, live later.** The live overlay reuses the history path.
2. **Output stops at gate failure lines.** The agent's own turns stay in
   `events.jsonl` and out of this view.
3. **The graph holds structure, and the ledger holds failure text.** Failure
   lines never become triples. A page fetches them by gate result id.
4. **The view projection is a second projection, separate from Q4's.** Q4's
   projection drops a task whose chain breaks or is still in flight. The view
   must show exactly those tasks.

## Components

```
ledger.db ──► saffron/view/graph.py ──► view.ttl (SHACL-checked) ──► pyoxigraph Store
   │            (view projection)                                     │
   │                                                    ontology/queries/view/*.rq
   │                                                                  │
   └──── failures by gate_result_id ◄──── saffron/view/server.py ◄────┘
```

### The view projection

`saffron/view/graph.py` exposes `build(ledger) -> rdflib.Graph`. It states every
task in any state. It reuses `NS` and `DATA_NS` from `saffron/projection.py`, so
`data:task-N` names one node in both graphs. It skips the chain attribution,
which answers Q4's question and not this one. It validates against the shapes
and rebuilds from scratch on every call.

A task row the shapes would reject is left out with a reason. The page lists
every reason, so it never reads as complete when it is not.

### Vocabulary

Each new term is licensed by a view query that reads it (Appendix T).

| Term | On | Why |
|---|---|---|
| `factory:inState` | `Task` | `endedInState` ranges over end states, and the view shows `REPAIRING` too |
| `prov:wasInformedBy` | `Run` to `Batch`, `Task` to `Run` | batch membership, with PROV's own edge |
| `prov:startedAtTime`, `prov:endedAtTime` | `Batch`, `Run`, `Attempt` | the timeline |
| `factory:numTurns` | `Attempt` | turns beside cost |
| `factory:gate`, `factory:gateStatus` | `GateResult` | status ranges over `pass`, `fail`, `skip`, `error` (`gates/contract.py`) |
| `factory:failureCount` | `GateResult` | the count, while the lines stay in the ledger |
| `prov:wasGeneratedBy` | `GateResult` to `GateSuite` | which attempt's suite produced it |
| claim, verdict, file, line | `Finding` | the finding as the critic stated it |

`uv run python -m ontology.render` regenerates `CONTEXT.md` and the shapes.

### View queries

`ontology/queries/view/` holds one named query per page fragment. There is one
for the batch list, one for a batch's tasks, one for a task's timeline, and one
for a task's findings. Each has an expected result in
`ontology/queries/expected/`, and `tests/ontology/test_queries.py` runs them.

### The server

`saffron serve` starts `saffron/view/server.py` on stdlib `http.server`.

- It binds `127.0.0.1` only (`docs/HOST-HARDENING.md`). A non-loopback address raises.
- Pages are `/`, `/batch/N` and `/task/N`, rendered with f-strings as
  `report/index.py` renders. Tasks with no batch appear on `/`.
- `/sparql` accepts `SELECT` and `ASK` only. Anything else returns 400.
- Failure lines come from `failures` by `gate_result_id`. The ledger opens with
  `?mode=ro`, so SQLite itself refuses a write.

## The decision record

ADR 9 comes before any spec, because three records bear on this view.

- **§6 says the queue is an index, not a viewer.** The queue stays the index,
  and diffs stay on GitHub. The view answers a different question: why a task
  ended where it did. It lands as `DESIGN.md` §6.2, an added subsection.
- **ADR 5 says the ontology never controls execution.** The view only reads. A
  `structure` rule forbids importing `saffron.view` anywhere in `saffron/` but `cli.py`.
- **Appendix T says coverage follows readers.** The view queries are the readers.

## Error handling

- A projection that fails the shapes stops `serve` at start, with the SHACL report.
- In live mode a failed rebuild keeps the last good graph and shows a stale banner.
- A task left out shows its reason in a panel on `/`.
- A write to `/sparql` returns 400, and a write to the ledger fails at SQLite.

## Testing

- The view projection runs against a fixture ledger with one task per state
  family, a batch with two runs, and a gate result with failures. Tests assert
  triples and shape conformance.
- Each view query is tested against its expected result.
- The server starts on port 0 in process. Each page is fetched against the
  fixture ledger. One test proves `/sparql` rejects `INSERT DATA`. One proves
  a non-loopback bind raises.
- Each test first runs against the unfixed code, per `CLAUDE.md`.

## Delivery

`DESIGN.md`, `CONTEXT.md`, `docs/adr/**` and `.saffron/**` are protected. So the
protected parts are done by hand or ride in a spec's PR. The Python goes
through cells.

| # | Work | Path | After |
|---|---|---|---|
| 0 | Time `build` over the real ledger, as a throwaway script | by hand | none |
| 1 | ADR 9, `DESIGN.md` §6.2, a backlog item for the live overlay | by hand, one PR | 0 |
| 2 | Vocabulary, shapes, render output, view queries and their expected results | by hand, in SA-0209's PR | 1 |
| 3 | `SA-0209` the view projection and its tests | cell | 2 |
| 4 | `SA-0210` `saffron serve`, pages, `/sparql`, read-only ledger, loopback bind | cell | 3 |
| 5 | The import rule for `saffron.view` and its rule tests | by hand, in SA-0210's PR | 4 |

`SA-0210` declares `depends_on: SA-0209`, so the pair runs as a stack. Each
spec goes through `create-saffron-spec` before its first cell.

Step 0 decides the live overlay's shape. A rebuild in seconds lets live mode
rebuild on each `ledger.db` mtime change. A slower rebuild means live mode
tails `events.jsonl` instead, and ADR 9 says so.

## Not in scope

- A diff viewer. GitHub stays the place a diff is read (§6).
- The agent's turns and tool calls.
- Any write path, any adjudication, any action from the page.
- Moving the source to the record on `refs/saffron/*` (item 170). The view
  projection reads the ledger today and moves when the ledger is folded.
