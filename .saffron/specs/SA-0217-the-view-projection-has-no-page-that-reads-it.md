---
id: SA-0217
title: The view projection has no page that reads it, so no one can see why a task ended where it did
type: feature
priority: 2
depends_on: [SA-0216]
consumes:
  - saffron/view/graph.py:build
  - saffron/view/graph.py:open_read_only
  - saffron/view/graph.py:LeftOut
  - saffron/view/graph.py:ViewGraphError
estimated_lines: 565
estimate_measured: true
touches:
  - saffron/view/server.py
  - tests/test_view_server.py
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
  - saffron/view/graph.py
  - saffron/projection.py
  - saffron/ledger.py
  - saffron/cli.py
  - saffron/report/**
  - saffron/record/**
  - saffron/gates/**
  - tests/test_view_graph.py
  - tests/test_projection.py
  - tests/test_ledger.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
pending_symbols:
  - saffron/view/server.py::make_server
budget_usd: 35
max_attempts: 3
max_turns: 160
acceptance:
  - claim: >-
      GET / answers 200 with one row per `V1` batch. The row's first cell
      is the batch id, linked to /batch/<batch_id>. Its window, stop reason,
      budget, spend and task count follow in that order. The stop reason
      reads as its local name, such as `UNTIL`. An open batch's window end,
      stop reason and spend cells are empty. A second section, the no-batch
      section, lists `V5`'s tasks, one row each, whose first cell is the
      task id linked to /task/<task_id>, followed by its spec id. No task of
      a batched run appears in the no-batch section. The witness drives a
      batch closed `UNTIL` with four tasks over two runs, an open batch with
      one task, and two tasks on a run with no batch.
    witness: tests/test_view_server.py::test_the_index_lists_each_batch_and_the_tasks_with_no_batch
    wrong_versions:
      - Each batch is linked by its row's position rather than its `batch_id`.
      - The no-batch section lists every task, batched ones included.
      - The no-batch section is missing.
      - The stop reason is not shown.
      - The stop reason is shown as its whole IRI.
      - An open batch's unbound cells read `None`.
      - The task count is not shown.
  - claim: >-
      GET / lists each `LeftOut` in `build`'s `left_out` as a row whose
      first three cells are its task id, its spec id and its reason. A
      `findings_without_diff` task stays in the graph, so its task id links
      to /task/<task_id>, and that page answers 200. Its attempt has no gate
      result, so the page shows that attempt as one row of its phase label
      and `n`, with empty gate, outcome and count cells. An `unknown_state`
      or `unknown_risk` task is absent from the graph, so its task id is not
      linked. The witness drives one task for each of the three reasons,
      all on one batched run.
    witness: tests/test_view_server.py::test_the_index_lists_each_left_out_task_with_its_reason
    wrong_versions:
      - The `findings_without_diff` entry is skipped, since its task is kept.
      - Every left-out task id is linked, so an absent task's link answers 404.
      - No left-out task id is linked.
      - The reason cell holds a fixed phrase rather than the entry's reason.
      - An attempt with no gate result is skipped.
      - An attempt with no gate result shows `None` in its empty cells.
      - The gate cell reads the unbound gate's value, so the page fails.
  - claim: >-
      GET /batch/<id> answers 200 with `V2` bound on `?batch` to that
      batch's node, one row per task. Each row's first cell is the task id
      linked to /task/<task_id>, followed by its spec id. The witness
      drives a batch with one task on each of two runs, beside a second
      batch's task and a task with no batch.
    witness: tests/test_view_server.py::test_a_batch_page_lists_only_that_batchs_tasks
    wrong_versions:
      - "`V2` runs unbound, so every batch's tasks are listed."
      - The page adds `V5`'s tasks to the batch's own.
  - claim: >-
      GET /task/<id> lists `V3` bound on `?task`, one row per gate result.
      Its first four cells are the phase's label, the attempt's `n`, the
      gate's name and the outcome's local name. The gate's name is what
      follows `factory:` or `data:gate-` in its IRI. The outcome reads
      `passed`, `failed`, `cantTell` or `inapplicable`, so an `error`
      result never reads as `failed`. No `urn:` IRI appears on that page.
      The witness drives all four statuses in one `IMPLEMENTING` attempt,
      over the core gate `scope`, the role gates `lint` and `no-network`
      and a repo-defined gate. Two `REPAIRING` attempts follow. The first
      swaps `error` and `fail` on two gates, and the second passes `lint`.
      A second task has a `scope` result of its own.
    witness: tests/test_view_server.py::test_a_task_page_shows_each_attempts_gate_outcomes_with_error_apart_from_fail
    wrong_versions:
      - "`cantTell` is shown as `failed`, so a gate that broke reads as code that is wrong."
      - The gate cell shows the gate's whole IRI.
      - The gate's name is taken after the IRI's last hyphen, so `no-network` reads `network`.
      - "`V3` runs unbound, so another task's results are listed too."
      - Rows are keyed by phase and gate, so the second `REPAIRING` attempt's result is lost.
      - A gate is shown once per task, so the later attempts' results are lost.
      - The phase is not shown.
      - The attempt's `n` is not shown.
  - claim: >-
      Directly under each gate-result row whose `failureCount` is above 0,
      the task page lists that result's failure lines. They are the first
      `FAILURE_LINE_CAP` rows, 200, of `SELECT file, line, code, message
      FROM failures WHERE gate_result_id = ? ORDER BY failure_id`. Each is
      one row of four cells in that order. When the result has more, one
      further row holds the single cell `<N> more`. The gate result id is
      parsed from `data:gate-result-<gate_result_id>`. The witness drives a
      result with 205 failures, one with exactly 200 and one with 3 in a
      later attempt. Their files and lines run opposite to `failure_id`.
    witness: tests/test_view_server.py::test_a_task_page_shows_failure_lines_capped_with_a_count_of_the_rest
    wrong_versions:
      - The lines are ordered by `file`.
      - The lines are ordered by `line`.
      - The lines are ordered by `failure_id` descending.
      - No cap is applied, so all 205 lines are shown.
      - A result with exactly 200 lines gets a `0 more` row.
      - Every failure line of the attempt is listed under each of its results.
      - The failure lines follow all the gate-result rows rather than their own.
      - The `more` row counts every line rather than the ones not shown.
  - claim: >-
      Five ledger fields reach a page through `html.escape`. They are a
      task's spec id, a failure's file, code and message, and a left-out
      task's spec id. The spec id is read in a row on / and on a batch
      page, and in a task page's `<title>` and its heading. The heading's
      spec id is read through `V2` bound on `?task`, or through `V5` bound
      on `?task` when `V2` returns no row. The witness puts markup in each
      field, and reads a batched task's page and an unbatched task's page.
      Each value in a row renders as its own text in a cell. Each heading
      holds its escaped spec id, and no fixture tag appears in any page.
    witness: tests/test_view_server.py::test_markup_in_a_stored_value_renders_as_text
    wrong_versions:
      - The spec id in an index row is not escaped.
      - The spec id in a batch page row is not escaped.
      - The spec id in a task page's `<title>` is not escaped.
      - The spec id in a task page's heading is not escaped.
      - The heading is read from `V2` alone, so an unbatched task's heading lacks its spec id.
      - The heading is read from `V5` alone, so a batched task's heading lacks its spec id.
      - A failure's file is not escaped.
      - A failure's code is not escaped.
      - A failure's message is not escaped.
      - A left-out task's spec id is not escaped.
  - claim: >-
      An id segment under /task/ or /batch/ that is not one or more ASCII
      digits answers 404. So does one whose id names no `factory:Task` or
      `factory:Batch` node in the graph. So do /nowhere and a page path
      with a third segment. An `unknown_state` task is in the ledger and
      not the graph, so its page is 404, and a task with no attempt answers
      200. The witness drives /task/99999, /task/abc, /task/-1, /task/1.5,
      /task/+<id> of a real task, an `unknown_state` task, a run's id,
      /batch/99999, /batch/abc, /batch/-1, /batch/+<id> of a real batch, a
      task's id as a batch, /nowhere and /task/<id>/x of a real task. It
      also sends the raw byte `0xb2` as a task id, which the server decodes
      as a superscript two.
    witness: tests/test_view_server.py::test_an_unknown_or_malformed_id_is_404
    wrong_versions:
      - The id is parsed with `int()`, so `+<id>` answers 200.
      - The segment is checked with `str.isdigit()` alone, so a superscript two reaches `int()` and the request fails.
      - A task page is rendered for any digits, so /task/99999 answers 200.
      - A batch page is rendered for any digits, so /batch/99999 answers 200.
      - A task's existence is read from the ledger's `tasks` table, so an `unknown_state` task answers 200.
      - A segment after the id is ignored, so /task/<id>/x answers 200.
      - An unknown path renders the index.
---

## Context

Backlog item **b-a1d649**, which cites `DESIGN.md` §6 and §6.2, with ADR 9
(`docs/adr/0009-a-read-only-view-renders-the-run-record-from-the-graph.md`).
The design is `docs/superpowers/specs/2026-10-05-run-record-view-design.md`.
Its server section (`:105-114`) and its failure-line cap (`:56`) fix the
pages. A first writer measured a prototype of the plan's Task 4
(`docs/superpowers/plans/2026-10-05-run-record-view.md:662-750`) at 746
lines and split it in two. This spec is the parent and builds the pages
without the findings. `SA-0218` is the child. It adds `/sparql`, the 405
on a write, the loopback check on `host` and the `saffron serve` command.

Line numbers below were read at `531efcbc`.

**What `SA-0215` and `SA-0216` give this spec.** `saffron/view/graph.py`
does not exist at `531efcbc`. Their specs define it, and a cell for this
spec is cut from `SA-0216`'s branch. It has the frozen dataclasses
`LeftOut(task_id, spec_id, reason)` and `ViewGraph(turtle, left_out)`, the
exception `ViewGraphError` with pyshacl's report as its message,
`open_read_only(path)` and `build(db, *, shapes_path=DEFAULT_SHAPES)`.
`open_read_only` raises `sqlite3.OperationalError` on a missing file and
creates nothing. A `left_out` reason of `unknown_state` or `unknown_risk`
means the task is absent from the graph. `findings_without_diff` means the
task is present and only its findings were dropped. The node forms are
`data:batch-<batch_id>`, `data:task-<task_id>`,
`data:gate-result-<gate_result_id>`, and `factory:<name>` or
`data:gate-<name>` for a gate. The gate result id and the gate's name exist
only in those IRIs. `build` states a gate result's failure count and never
a failure's text.

**The queries.** Each is a file under `ontology/queries/view/`, with the
prefixes `saffron/projection.py` names: `NS` (`:53`) and `DATA_NS` (`:54`).
The batch list (ontology/queries/view/V1-batches.rq:6) selects each
batch with its window, stop reason, budget, spend and task count. Its stop
reason is an IRI such as `factory:UNTIL`
(ontology/queries/view/V1-batches.rq:11). The batch's tasks
(ontology/queries/view/V2-batch-tasks.rq:7-10) reach a task's spec, state,
risk and pull request through its run's batch. So that query, bound on
`?task`, returns no row for a task whose run has no batch. The unbatched
tasks (ontology/queries/view/V5-unbatched-tasks.rq:11) are exactly those.
The timeline (ontology/queries/view/V3-task-timeline.rq:8) selects each
attempt's phase label, gate, outcome and failure count. Its gate part is
optional (ontology/queries/view/V3-task-timeline.rq:17-22), so an attempt
with no gate result is one row with the gate variables unbound. Each
file's name starts with its query's name, `V1` to `V5`.

**The failure lines.** `failures` (`saffron/ledger.py:192-199`) holds
`file`, `code`, `message` and `line` per `gate_result_id`. ADR 9 keeps them
out of the graph (`docs/adr/0009-a-read-only-view-renders-the-run-record-from-the-graph.md:29-30`).
A page reads them by gate result id.

**The style.** `saffron/report/index.py:3` renders the morning queue with
f-strings rather than a template engine. The pages do the same.

## Problem

Nothing serves the view projection, so the question ADR 9 poses still has
no page. Build `saffron/view/server.py` with exactly this interface.

```python
FAILURE_LINE_CAP = 200

def make_server(
    ledger_path: Path, *, host: str = "127.0.0.1", port: int = 8765
) -> ThreadingHTTPServer: ...
```

1. **Build once.** `make_server` opens `ledger_path` with `open_read_only`,
   calls `build`, and closes the connection. It loads the turtle and
   `projection.VOCABULARY` into one in-memory `pyoxigraph.Store`. It returns
   an unstarted `ThreadingHTTPServer` on `(host, port)`. A graph that fails
   the shapes raises `ViewGraphError` from `build`, and `make_server` lets
   it propagate.
2. **Run each query from its file.** Bind a variable with
   `store.query(text, substitutions={pyoxigraph.Variable("task"):
   pyoxigraph.NamedNode(...)})`. That form was measured on pyoxigraph
   0.5.9.
3. **The pages.** `GET /`, `GET /batch/<id>` and `GET /task/<id>`, as the
   criteria say. The no-batch section on `/` is `V5` unbound. The left-out
   panel shows a `findings_without_diff` entry as a kept task whose
   findings were dropped.
4. **The graph decides which pages exist.** Accept an id segment that is
   non-empty ASCII digits, as `str.isascii()` and `str.isdigit()` decide
   together. Then ask the store whether the node is typed
   `factory:Task` or `factory:Batch`. Answer 404 otherwise.
5. **Failure lines come from the ledger.** Take each gate result with a
   count above 0. Parse its id from its IRI and run criterion 5's query.
   Open the connection with `open_read_only` inside the request, and close
   it there.
6. **Escape every text.** Each literal from the store or the ledger passes
   through `html.escape` before it reaches the page.

**The page contract.** The witnesses read each page with the standard
library's `html.parser`. Each listed item is one `<tr>`, and each value in
it is one `<td>`. Each link is an `<a href>`. An unbound value is an empty
cell. A row is one of these.

- A batch row on `/`: the batch id, then the window start, the window end,
  the stop reason's local name, the budget, the spend and the task count.
- A task row on `/` and on a batch page: the task id as its first cell,
  then the spec id, the state and the risk.
- A left-out row: the task id, the spec id and the reason, in that order.
- A gate-result row: the phase label, the attempt's `n`, the gate's name,
  the outcome's local name and the failure count. An attempt with no gate
  result is one such row with the last three cells empty.
- A failure row: the file, the line, the code and the message, in that
  order, directly after its gate-result row.

The task page puts its spec id in both its `<title>` and its heading. The
task page holds no other rows.

## Out of scope

- `/sparql`, the 405 on a write, the loopback check on `host`, and the
  `saffron serve` command. `SA-0218` adds them. `make_server` takes `host`
  as given here. `SA-0218`'s command also drives the `ViewGraphError` that
  `make_server` lets through.
- A task's findings and its pull request link. `V4` and `rdfs:seeAlso`
  are read by a later spec, which adds both to the task page.
- The import rule that keeps `saffron.view` to `cli.py`. It is protected,
  and it lands by hand in a spec pull request.
- A live overlay that rebuilds on each ledger change. The graph is built
  once per server.
- Any write path. Nothing here writes the ledger or the store.
- `saffron/view/graph.py`. `SA-0215` and `SA-0216` own it. Change none of
  its names, its IRI forms or its tests.

## Notes for the agent

**This change is new code.** Each criterion declares a witness and no
mutant, so the `witness` gate reports `skip` for all seven. The wrong
versions under each criterion are what its witness must kill. Do not run
them yourself.

**Commit as each witness passes.** Seven witnesses, seven commits at
least. A turn cut by a bound then loses one witness's work.

**Every witness must fail without this change.** Import
`saffron.view.server` inside each test body or helper, never at module
scope, for the reason `tests/test_projection.py:3-6` gives.

**Serve the way production does.** Each witness calls
`make_server(path, port=0)`, runs `serve_forever` on a daemon thread, and
fetches with `urllib.request`. It reads the port from
`server.server_address`. Call `shutdown` and `server_close` in a
`finally`.

**Fixtures.** Build each ledger with `Ledger(tmp_path / "ledger.db")`, then
close it before `make_server`. Set a task's state and risk with a raw
`UPDATE`. Record gate results with `record_gate_result` and `attempt_id=`
(`saffron/ledger.py:1828`). A task in state `PAUSED` is left out as
`unknown_state`, and one at risk `reckless` as `unknown_risk`.

**Offset the ids.** A fresh ledger numbers each table from 1. An id taken
from the wrong table, or a row's position, then reads right by accident.
First make spare batches, spare runs, spare baseline gate results with
failures, and a spare task with attempts and findings. No spare run names
a spare batch, since the ledger turns foreign keys on
(`saffron/ledger.py:344`). Then record the fixture's own rows. Only then
delete the spare batches, task, attempts and findings, and keep the spare
runs and baseline results. The order matters. Those tables number rows
without `AUTOINCREMENT` (`saffron/ledger.py:99`, `:123`, `:153`), so a
deletion made first hands the same ids out again. The spare failure text
must appear on no page. Build every expected link from the ids the ledger
returned.

**Criterion 1.** Find each batch's row by its first cell, and read each
cell by its position. Assert the set of `/batch/` links equals the two
batches, and the set of `/task/` links equals the two unbatched tasks.

**Criterion 2.** Put all three tasks on one batched run, so the left-out
panel is the index's only link to a task. Give the kept task one attempt
with no gate result.

**Criterion 4.** Take the first four cells of every row on the page.
Compare them, sorted, with the sorted expected rows. An extra row or a
lost one then fails.
Assert `urn:` and `gate-` appear nowhere in the body.

**Criterion 5.** Number each failure's message by its position, and give
its file and line in the opposite order. Assert the message cells under
each result equal the expected list in order. Assert the row after the
205-line block is exactly `["5 more"]`, and that no other cell ends in
` more`.

**Criterion 6 leaves fields undriven.** A gate name lives in an IRI,
which cannot carry markup through `build`. A state, a risk and a stop
reason are closed sets the shapes enforce. A phase label is escaped by
Problem item 6, and no witness puts markup in it. Assert each heading by
its escaped text, such as `&lt;b&gt;`.

**Criterion 7.** Give the bare task no attempt, and put it on a batched
run, so both its page and its batch's page answer 200. `urllib` cannot send
a non-ASCII path, so send the `0xb2` request on a raw socket and read the
status from the reply's first line.

**Measured on a prototype at `531efcbc`.** A prototype of this half passed
all seven witnesses over `SA-0216`'s prototype projection. Each failed with
the server module absent. Each of the 49 wrong versions above was applied
to it as an edit, and each failed its own criterion's witness. Its diff
measured 2257 changed tokens with `size_gate`.

**`make_server` has no production caller yet.** `SA-0218`'s command calls
it, and `pending_symbols` defers it until then. `do_GET` and `log_message`
are called by `http.server` by name, which vulture cannot see. This
spec's pull request adds both to `.saffron/deadcode-allow.py` by hand,
since that file is protected. Name the two methods exactly so. The `dead`
gate passed on the prototype with those lines in place.

**Annotate what you add.** The `types` gate checks the whole tree, and an
unannotated helper hides its values' types. Three spots failed it on the
prototype. `Store.query` returns a union of three result types, so narrow
it before you iterate. Its `substitutions` parameter wants a dict typed
with the full union of term types, so annotate the dict you pass. A test
helper that builds a `GateResult` or a `Finding` takes `GateStatus` or
`Severity`, not `str`.
