---
id: SA-0215
title: The run record has no graph that states a task in flight, or the batch, run and attempts around it
type: feature
priority: 2
estimated_lines: 469
estimate_measured: true
touches:
  - saffron/view/__init__.py
  - saffron/view/graph.py
  - tests/test_view_graph.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - harness/**
  - records/**
  - hooks/**
  - images/**
  - saffron/projection.py
  - saffron/ledger.py
  - saffron/cli.py
  - saffron/report/**
  - saffron/record/**
  - saffron/gates/**
  - tests/test_projection.py
  - tests/test_ledger.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
pending_symbols:
  - saffron/view/graph.py::build
  - saffron/view/graph.py::open_read_only
  - saffron/view/graph.py::turtle
budget_usd: 58
max_attempts: 3
max_turns: 150
acceptance:
  - claim: >-
      `build` states a task in each of the eight in-flight states, `DRAFT`,
      `QUEUED`, `DIAGNOSING`, `IMPLEMENTING`, `GATING`, `REPAIRING`,
      `REVIEWING` and `REBUTTING`, as `data:task-<task_id>` typed
      `factory:Task`. Each states `factory:inState` its state and no
      `factory:endedInState`. Each states `factory:riskTier` its risk,
      `rdfs:label` its spec id, and `prov:wasInformedBy` its run's node.
      It states `rdfs:seeAlso` its `pr_url` as an IRI when the column is set,
      and no `rdfs:seeAlso` when it is null. The witness drives all eight
      states at risk `standard` with a null `pr_url`, a `REPAIRING` task with
      one set, and a `GATING` task at risk `elevated`.
    witness: tests/test_view_graph.py::test_an_in_flight_task_is_stated_with_its_state
    wrong_versions:
      - "The task node is not typed `factory:Task`."
      - "`endedInState` is stated for every task, in flight or not."
      - "The known states are the end states alone, so every in-flight task is left out."
      - "`rdfs:seeAlso` is stated as a string literal rather than an IRI."
      - "`rdfs:label` carries the task's `spec_sha` rather than its `spec_id`."
      - "`rdfs:seeAlso` is stated whatever `pr_url` holds, null included."
      - "`riskTier` is derived from the state, `elevated` for an end state and `standard` otherwise."
  - claim: >-
      `build` states a task in each of the seventeen end states that
      `factory:TaskShape`'s `factory:endedInState` property lists, with both
      `factory:inState` and `factory:endedInState` set to that state. Its
      `factory:riskTier` is its own risk. The witness drives all seventeen,
      each at risk `elevated`, and one more `MERGED` task at risk `standard`.
    witness: tests/test_view_graph.py::test_an_ended_task_states_both_its_state_and_its_end
    wrong_versions:
      - "An ended task states `endedInState` alone and no `inState`."
      - "`riskTier` is `standard` whatever the row holds."
      - "`riskTier` is derived from the state, `elevated` for an end state and `standard` otherwise."
      - "The end states are read from `TerminalStateShape`, so the six end states outside it state no `endedInState`."
  - claim: >-
      `build` states every run as `data:run-<run_id>` typed `factory:Run`,
      with `factory:baseSha` its `base_sha`. A run whose `batch_id` is set
      states `prov:wasInformedBy` its batch's node, and a run whose
      `batch_id` is null states none. A task on either run is stated and
      informed by its own run. The witness drives one run of each kind with
      one task on each.
    witness: tests/test_view_graph.py::test_a_task_whose_run_has_no_batch_is_still_stated
    wrong_versions:
      - "The run node is not typed `factory:Run`."
      - "A run with a null `batch_id` is linked to a `data:batch-None` node."
      - "Tasks are read through a join that requires a batch, so a task on an unbatched run is not stated."
      - "A task states no `prov:wasInformedBy` its run."
      - "A run is linked to `data:batch-<run_id>` rather than its batch's id."
      - "A task is linked to `data:run-<task_id>` rather than its run's id."
  - claim: >-
      `build` states every batch as `data:batch-<batch_id>` typed
      `factory:Batch`. It states `factory:budgetUsd` as an `xsd:decimal` and
      `prov:startedAtTime` as a UTC `xsd:dateTime`. When the column is set, it states
      `factory:spentUsdEst` as an `xsd:decimal`, `prov:endedAtTime` as a UTC
      `xsd:dateTime`, and `factory:endedBecause` the stop reason's
      vocabulary individual. A null column states nothing. The witness drives
      a closed batch for each of the five stop reasons, `DRAINED`,
      `BUDGET`, `UNTIL`, `INFRASTRUCTURE` and `INCOMPLETE`, and one batch
      still running, whose three columns are null.
    witness: tests/test_view_graph.py::test_a_batch_states_its_budget_spend_window_and_stop_reason
    wrong_versions:
      - "The batch node is not typed `factory:Batch`."
      - "`spentUsdEst` is stated as a float literal, `xsd:double`."
      - "`budgetUsd` is stated as a float literal."
      - "Times are stated without a timezone, so they read back as naive datetimes."
      - "Times are stated as plain strings."
      - "`endedBecause` is stated as a string literal rather than the vocabulary individual."
      - "A running batch states `spentUsdEst` 0."
  - claim: >-
      `build` states every attempt of a stated task as
      `data:attempt-<attempt_id>` typed `factory:Attempt`. It states
      `factory:withinPhase` the node `data:phase-<task_id>-<phase>`, which is
      typed `factory:Phase`, labelled with the phase name by `rdfs:label`, and
      `prov:wasInformedBy` the task. Two attempts in one phase of one task
      share that node. It states `factory:n` the row's `n` as an
      `xsd:integer`, and `prov:startedAtTime` as a UTC `xsd:dateTime`. When
      the column is set, it states `factory:numTurns` as an `xsd:integer`,
      `factory:costUsdEst` as an `xsd:decimal`, and `prov:endedAtTime`. A
      null column states nothing. The witness drives a closed
      `IMPLEMENTING` attempt, an open `REVIEWING` attempt, and a second open
      `IMPLEMENTING` attempt.
    witness: tests/test_view_graph.py::test_an_attempt_states_its_phase_number_turns_cost_and_times
    wrong_versions:
      - "The attempt node is not typed `factory:Attempt`."
      - "The phase node is not typed `factory:Phase`."
      - "The phase node is named per attempt, so two attempts in one phase name two phases."
      - "The phase node is named `data:phase-<run_id>-<phase>` rather than by the task's id."
      - "The phase node states no `prov:wasInformedBy` its task."
      - "`factory:n` carries the attempt's id."
      - "`costUsdEst` is stated as a float literal."
      - "`numTurns` is stated as an `xsd:decimal`."
      - "An open attempt states an `endedAtTime`."
  - claim: >-
      A task whose state is in neither the end-state set nor the in-flight
      set is left out. `left_out` holds one `LeftOut` with its task id, its
      spec id and the reason `unknown_state`. No triple names its task node,
      its attempts' nodes or its phase nodes. A known task read after it is
      still stated. The state is checked before the risk, so a task unknown
      on both counts gets exactly one `LeftOut`, with the reason
      `unknown_state`. The witness drives one such task beside the first.
    witness: tests/test_view_graph.py::test_a_task_in_an_unknown_state_is_left_out_and_the_rest_are_stated
    wrong_versions:
      - "The loop stops at the first unknown state, so the tasks after it are not stated."
      - "The reason is `unknown_risk`."
      - "The task is recorded as left out, but its attempts and phases are still stated."
      - "The risk is checked before the state, so a task unknown on both counts is left out as `unknown_risk`."
  - claim: >-
      A task whose risk is not in the risk set is left out. `left_out` holds
      one `LeftOut` with its task id, its spec id and the reason
      `unknown_risk`. No triple names its task node, its attempts' nodes or
      its phase nodes. A known task read after it is still stated.
    witness: tests/test_view_graph.py::test_a_task_at_an_unknown_risk_is_left_out_and_the_rest_are_stated
    wrong_versions:
      - "The loop stops at the first unknown risk, so the tasks after it are not stated."
      - "Risk is not checked, so the task is stated and the graph fails the shapes."
      - "`LeftOut.spec_id` carries the task id."
  - claim: >-
      The whole graph `build` makes is validated with pyshacl against the
      shapes at `shapes_path`, with the vocabulary and `ontology/vendor/*.ttl`
      as data beside it. `ViewGraph.turtle` is the graph alone, without the
      vocabulary. With `DEFAULT_SHAPES`, a ledger holding a closed batch, a
      batched and an unbatched run, an ended and an in-flight task and a
      closed attempt builds. Its turtle passes those shapes when the witness
      validates it itself, with the vocabulary and `ontology/vendor/*.ttl`
      beside it as `build` does. With a `shapes_path` that graph fails, `build` raises
      `ViewGraphError` carrying pyshacl's report text.
    witness: tests/test_view_graph.py::test_the_graph_passes_the_shapes
    wrong_versions:
      - "`build` never validates."
      - "`build` validates against `DEFAULT_SHAPES` whatever `shapes_path` names."
      - "The vocabulary is parsed into the graph that is serialized, so `turtle` carries it."
      - "`ViewGraphError` carries a fixed message rather than pyshacl's report."
  - claim: >-
      `build` reads each of its three closed sets from the shapes at
      `shapes_path`, never from a literal list. The end states are the `sh:in`
      of `factory:endedInState`'s property shape. The in-flight states are
      the `sh:in` of the node shape that targets `factory:InFlightState`. The
      risks are the `sh:in` of `factory:riskTier`'s property shape. The
      witness's shapes file drops `MERGED` from the first, adds `PAUSED` to the
      second, and drops `elevated` from the third. A `MERGED` task is then left
      out as `unknown_state`, and an `elevated` task as `unknown_risk`. A
      `PAUSED` task is stated in that state with no `factory:endedInState`.
    witness: tests/test_view_graph.py::test_the_closed_sets_are_read_from_the_shapes_it_is_given
    wrong_versions:
      - "The sets are read from `DEFAULT_SHAPES` whatever `shapes_path` names."
      - "The risks are a literal `standard` and `elevated`."
      - "The in-flight states are a literal list of eight."
      - "The in-flight states are read with `projection._sh_in`'s approach on `factory:inState`, which carries no `sh:in`, so every in-flight task is left out."
  - claim: >-
      `build` over `open_read_only`'s connection completes while a second
      connection holds an uncommitted write transaction on the same file.
      The graph states the committed state, not the uncommitted one.
    witness: tests/test_view_graph.py::test_build_reads_a_ledger_another_connection_is_writing
    wrong_versions:
      - "`open_read_only` constructs a `Ledger` on the path first, whose schema script waits on the writer's lock and fails."
  - claim: >-
      `open_read_only(path)` returns a connection whose `row_factory` is
      `sqlite3.Row` and on which an `INSERT` raises
      `sqlite3.OperationalError` naming a read-only database. On a path that
      does not exist, `open_read_only` itself raises
      `sqlite3.OperationalError`, and no file is created there.
    witness: tests/test_view_graph.py::test_the_connection_cannot_write
    wrong_versions:
      - "The path is passed to `sqlite3.connect` as a plain filename, so the connection writes and an absent path is created."
      - "The URI's mode is `rwc`."
      - "The URI's mode is `rw`."
      - "`row_factory` is left unset."
---

## Context

Backlog item **b-a1d649**. It cites `DESIGN.md` §6 and §6.2. ADR 9
(`docs/adr/0009-a-read-only-view-renders-the-run-record-from-the-graph.md`)
decides that `saffron serve` renders the run record from a second projection
of the ledger, beside Q4's. The design is
`docs/superpowers/specs/2026-10-05-run-record-view-design.md`. Its "Settled
while planning" section holds the decisions this spec builds on. The plan is
`docs/superpowers/plans/2026-10-05-run-record-view.md`, Task 3.

This spec is the first half of Task 3. It builds the graph's batches, runs,
tasks, phases and attempts. `SA-0216` adds gate results, diffs and findings
to the same `build`. `SA-0217` serves the pages and is the production caller
of `build`, `open_read_only` and `ViewGraph.turtle`.

**What exists.** `saffron/projection.py` defines `VOCABULARY` (`:49`),
`DEFAULT_SHAPES` (`:50`), `NS` (`:53`) and `DATA_NS` (`:54`). Its `_sh_in`
(`:255-267`) collects the `sh:in` members of every shape whose `sh:path` is
the given property. No `saffron/view/` package exists.

**The shapes.** In `ontology/shapes/factory-shapes.ttl`, `factory:TaskShape`
(`:12-26`) requires `factory:endedInState` or `factory:inState` through one
`sh:alternativePath` property (`:14-15`). Its `factory:endedInState`
property lists the seventeen end states in `sh:in` (`:16-23`). Its
`factory:inState` property has `sh:class factory:TaskState` and no `sh:in`
(`:24`). Its `factory:riskTier` property lists `standard` and `elevated`
(`:25-26`). `factory:InFlightStateShape` (`:43-49`) is a node shape. It
targets `factory:InFlightState` and lists the eight in-flight states in a
node-level `sh:in`. `_sh_in`'s approach therefore finds no in-flight state.
`factory:AttemptShape` (`:61-68`) requires `factory:withinPhase` a
`factory:Phase` and `factory:n` an `xsd:integer` of at least 1. A
`factory:costUsdEst` it states must be an `xsd:decimal`, though none is
required (`:68`). `factory:BatchShape` (`:77-85`)
requires `factory:spentUsdEst` an `xsd:decimal` (`:81`). `factory:RunShape`
(`:87-91`) requires one `factory:baseSha`.

**The ledger.** Every time column in `saffron/ledger.py` holds UTC text
in the form `%Y-%m-%d %H:%M:%S`, with no offset. The schema's defaults
write it with `datetime('now')` (`:100`, `:159`). A row written from a
fact takes its time from `_ledger_time` (`:315-318`). A new run's insert
converts it at `:609`. An attempt's insert takes the time converted at
`:656`, where `_ledger_time` is called once per fact. `batches.spent_usd_est`, `ended_at` and
`status` are nullable (`:101-106`). A run's `batch_id` is nullable (`:114`).
`attempts.num_turns`, `cost_usd_est` and `ended_at` are nullable
(`:160-164`). `open_attempt` numbers `n` within one task's phase
(`:1339-1344`). `Ledger.__init__` runs `executescript(SCHEMA)` (`:345`), so
it writes on open.

**The view queries.** `ontology/queries/view/V2-batch-tasks.rq` and
`V5-unbatched-tasks.rq` read `factory:inState` and `factory:endedInState`
each in an `OPTIONAL`, and bind one state with `COALESCE`. So a task stating
both is counted once.
`V3-task-timeline.rq` joins `?phase prov:wasInformedBy ?task` and
`?attempt factory:withinPhase ?phase ; factory:n ?n`. So the phase node
needs both edges.

## Problem

No code states the run record as a graph that holds a task in flight. Q4's
projection keeps only ended tasks whose chain can be attributed. Build
`saffron/view/graph.py` with exactly this interface.

```python
@dataclass(frozen=True)
class LeftOut:
    task_id: int
    spec_id: str
    reason: str

@dataclass(frozen=True)
class ViewGraph:
    turtle: bytes
    left_out: list[LeftOut]

class ViewGraphError(Exception): ...

def open_read_only(path: Path) -> sqlite3.Connection: ...
def build(db: sqlite3.Connection, *, shapes_path: Path = DEFAULT_SHAPES) -> ViewGraph: ...
```

- `open_read_only` returns `sqlite3.connect(f"file:{path}?mode=ro",
  uri=True)` with `row_factory` set to `sqlite3.Row`.
- `ViewGraphError` carries pyshacl's report text as its message.
- Import `NS`, `DATA_NS`, `VOCABULARY` and `DEFAULT_SHAPES` from
  `saffron.projection`. Name nodes in `DATA_NS` as `data:batch-<batch_id>`,
  `data:run-<run_id>`, `data:task-<task_id>`, `data:phase-<task_id>-<phase>`
  and `data:attempt-<attempt_id>`. The task IRI then names one node in both
  graphs.
- Nothing in `saffron/view/` constructs `Ledger` or imports
  `saffron.ledger`.
- The known states are the end-state set together with the in-flight set,
  each read from `shapes_path` as criterion 9 names. Reading them takes a
  helper that matches on `sh:targetClass` beside one that matches on
  `sh:path`.
- Costs and spend are `xsd:decimal`. Convert through `Decimal(str(value))`,
  so `12.4` reads back as `Decimal("12.4")`. On the real ledger, a float
  literal gave 1848 violations in the first prototype. Times are timezone-aware `xsd:dateTime`
  values in UTC.
- Validate once, after every node is added. The data graph is a copy of the
  view graph with `VOCABULARY` and each `ontology/vendor/*.ttl` parsed into
  it. Pass `advanced=True`. Serialize the view graph alone, as UTF-8
  turtle.
- `saffron/view/__init__.py` is empty.

## Out of scope

- **Gate results, gate suites, diffs and findings.** `SA-0216` adds them,
  with the `findings_without_diff` reason. This spec states no
  `factory:GateSuite`, `factory:GateResult`, `factory:Diff` or
  `factory:Finding`.
- **`saffron serve` and its pages.** `SA-0217` builds them.
- **The import rule** that keeps `saffron.view` to `saffron/cli.py`. It is
  written by hand, outside any cell (the plan's Task 5).
- **The view queries and the shapes.** They are in `ontology/**`, which is
  forbidden here. Edit neither to make a witness pass.
- **Run times.** The design lists `prov:startedAtTime` on a run. No
  criterion here states it, and the view queries do not read it.

## Notes for the agent

**Every criterion is new code.** `saffron/view/` does not exist at base, so
no text there fixes a spelling. No criterion declares a mutant, and the
`witness` gate reports `skip` for each.

**Import `saffron.view.graph` inside each test body**, never at module
scope. A module-scope import makes the `revert` gate's reverted run a
collection error, which it reads as `skip`.

**The fixture ledger.** Build it with `Ledger(tmp_path / "ledger.db")`,
`upsert_repo`, `create_run`, `create_batch`, `close_batch`, `create_task`,
`open_attempt` and `close_attempt`. Set a task's `state`, `risk` and
`pr_url`, and fixed times, with an `UPDATE` through `ledger._db` and a
commit. Close the ledger, then call `build(open_read_only(...))` and parse
`view.turtle` with rdflib. Compare each object set with `==` against the
whole expected set, and compare a decimal or a time by `toPython()` and its
datatype.

**Offset the ids across tables.** A fresh ledger numbers each table
from 1. So a batch, a run and a task can share an id. A node named from the
wrong table's id then reads right by accident. Create throwaway rows first,
such as one batch, three runs and six tasks, so no two tables share an id.
Build every expected IRI from the ids the ledger returned.

**Criterion 4's witness** asserts `factory:budgetUsd` on every batch it
makes, closed and running, each with its own value.

**Criterion 5's witness** opens the attempts in the order `IMPLEMENTING`,
`REVIEWING`, `IMPLEMENTING`. It asserts the `REVIEWING` attempt's `n` is 1
and the second `IMPLEMENTING` attempt's `n` is 2, so `n` is not the
attempt id.

**Criteria 6 and 7's witnesses** give the left-out task an attempt and
create a known task after it. They assert no triple names the left-out
task's node, its attempt's node or its phase's node, as subject or object.
Criterion 6's witness adds a second unknown-state task at risk `reckless`,
and compares `left_out` with the whole list of two.

**Criterion 8's witness** makes the failing shapes by copying
`DEFAULT_SHAPES` with `factory:spentUsdEst`'s `sh:maxCount` set to 0. The
ledger holds a closed batch, so the graph states one spend. Match the
raise on `Conforms: False`, which pyshacl's report text holds. Assert the
copy changed one line, so the test cannot pass on an unchanged file.

**Criterion 9's witness.** Shrinking `InFlightStateShape`'s node-level set
breaks the vocabulary's own individuals, since each in-flight state is
typed `factory:InFlightState`. So the in-flight half adds a member. Adding
`PAUSED` also needs the `sh:class factory:TaskState` clause dropped from the
`factory:inState` property, since `PAUSED` is no `TaskState`. That clause
also appears in `InFlightStateShape`, so anchor the edit on the
`factory:inState` property's own text. The end-state and risk sets are
property-level, so dropping a member leaves the vocabulary valid. Assert
each edited string occurs once before replacing it.

**Criterion 11's witness** puts the `open_read_only` call on the absent
path inside `pytest.raises`. SQLite refuses a read-only open of a missing
file at connect, so the open itself raises.

**Criterion 10's witness.** Close the `Ledger`. Open a plain
`sqlite3.connect(path, isolation_level=None)`, run `BEGIN IMMEDIATE` and
an `UPDATE` of the task's state, and build while that is open. Roll back
and close it in a `finally`.

**Measured on a prototype, 2026-10-05.** A prototype of this half was cut
from one of all of Task 3. It passed all eleven witnesses at `9831b2f2`.
Each failed with `saffron/view/` removed. Every wrong version
listed above was applied to it as an edit, and each failed its own
criterion's witness. `types` passed on it. `dead` reported exactly the
three `pending_symbols` entries. It built the real ledger read-only in
0.8 s, with no task left out and no `ViewGraphError`. Formatted, its
source and witnesses measured 1873 changed tokens under `size_gate`'s
counter, with few docstrings. `estimated_lines` is that figure over four.

**The prose gate** counts every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense, a hedge or a
sentence over 25 words.

**Commit as each witness passes**, before the full suite runs.
