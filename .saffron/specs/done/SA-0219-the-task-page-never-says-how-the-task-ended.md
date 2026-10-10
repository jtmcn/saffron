---
id: SA-0219
title: The task page never says how the task ended, and a finding row reads like a failure row
type: feature
priority: 2
depends_on: [SA-0218]
consumes:
  - saffron/view/server.py:make_server
estimated_lines: 553
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
  - tests/test_cli.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 30
max_attempts: 3
max_turns: 160
acceptance:
  - claim: >-
      A task page heads with a `<dl id="summary">` of five terms. `state` and
      `risk` are local names, read from `V2` bound on `?task`, or from `V5`
      bound on `?task` when `V2` returns no row. `batch` is a link to the
      batch's page, labelled with the batch id, or the text `none`. `pull
      request` is a link to its URL, or `none`. `cost` is the sum of the
      task's attempts' `costUsdEst`, each attempt counted once however many
      gate results it has, rounded to cents. A task with no costed attempt
      shows `0.00`. The witness drives a batched task in an end state at
      `elevated` with five attempts. One carries three gate results and the
      cost `1.234`. The others carry no gate result, one gate result, no
      cost at all, and a cost equal to another attempt's. Its batch id
      differs from every task id in the fixture. It drives an unbatched
      task in flight at `standard` with no pull request and two costed
      attempts, and asserts its total. It drives a batched decoy task with
      its own batch, cost and pull request. It drives an unbatched decoy
      task with a higher id and its own state, risk, cost and pull request.
    witness: tests/test_view_server.py::test_a_task_page_heads_with_its_state_risk_batch_pull_request_and_cost
    wrong_versions:
      - The summary is read from `V2` alone, so the unbatched task's terms are empty.
      - The summary is read from `V5` alone, so the batched task's terms are empty.
      - "`V2` and `V5` run unbound, so the page shows the decoy task's batch and pull request."
      - "`V2` is bound on `?task` but `V5` runs unbound, so the unbatched page shows the unbatched decoy's terms."
      - The cost sums `V3`'s rows, so an attempt counts once per gate result.
      - The total is read from `V2`'s `?costUsd`, so an unbatched task shows none.
      - Costs are summed over distinct values, so two equal costs count once.
      - The cost is shown unrounded.
      - The cost is truncated to cents rather than rounded.
      - Each attempt's cost is rounded before the sum.
      - The batch link names the task id rather than the batch id.
      - An unbatched task's batch term is empty rather than `none`.
      - A task with no pull request shows an empty term rather than `none`.
      - The state shows its whole IRI.
      - The risk term is left out.
      - The pull request is shown as text with no link.
  - claim: >-
      A task page lists its attempts in a table with id `attempts`, one row
      per attempt in `V3`'s order, which is by start time. The cells are the
      phase, `n`, the start and the end as `V3` returns them, the turns and
      the cost rounded to cents. A value the attempt lacks is an empty cell.
      The witness drives five attempts whose start order differs from both
      their id order and their phase names' order. One carries three gate
      results, one carries none, and one was never closed. Two have equal
      costs.
    witness: tests/test_view_server.py::test_a_task_page_lists_each_attempt_once_with_its_times_turns_and_cost
    wrong_versions:
      - One row per `V3` row, so an attempt with three gate results shows three times.
      - Rows in attempt id order.
      - Rows sorted by phase name.
      - A value the attempt lacks shows as `None`.
      - The attempt's cost is shown unrounded.
      - Rows are built from gate results, so an attempt with none is missing.
      - The turns column is left out.
  - claim: >-
      A task with no attempts gets a page with its summary, the text
      `no attempts`, and no `<table>` at all. Its summary's cost reads
      `0.00`. The witness serves a batched task in `GATE_ERROR` with no
      attempts, and a task with attempts whose page lacks that text.
    witness: tests/test_view_server.py::test_a_task_with_no_attempts_shows_its_summary_and_no_table
    wrong_versions:
      - An empty attempts table is rendered beside the text.
      - The text is missing, so the page shows the summary alone.
      - The text appears on every task page.
      - The summary is left out when there are no attempts.
  - claim: >-
      A task page lists its gate results in a table with id `gate-results`,
      one row each, with the phase, `n`, the gate, the outcome and the
      failure count. An attempt with no gate result adds no row there. Each
      gate result with a failure count above zero gets its own table, with
      id `failures-<gate_result_id>`, after an `<h3>`. The heading's text is
      exactly the gate, `in`, the phase, `attempt` and `n`, as in `lint in
      GATING attempt 1`. That table lists the result's failure lines in the
      order they were recorded. A result with no failures gets none.
      Findings sit in a table with id `findings`. The witness drives `lint`
      failing in `GATING` attempt 1 and in `REPAIRING` attempt 2, and
      compares each heading's whole text. It drives a passing and an
      erroring gate with no failure lines, and two findings. It opens a
      `REPAIRING` attempt with no gate result before the `REPAIRING` one
      with `lint`, which is what makes that one attempt 2.
    witness: tests/test_view_server.py::test_gate_results_failure_lines_and_findings_sit_in_separate_tables
    wrong_versions:
      - Failure lines stay in the gate-results table.
      - Every gate result gets a failures table, a result with no failures included.
      - A failures table's id carries the attempt id.
      - The heading names the gate alone, so two `lint` tables read the same.
      - The heading names the gate and the phase but not `n`.
      - The heading names the attempt id where `n` belongs.
      - Findings are left out of the findings table.
      - An attempt with no gate result keeps a row of empty gate cells.
      - Failure lines are ordered by file rather than as recorded.
  - claim: >-
      Every `<table>` on the page at `/`, on a batch page and on a task
      page carries an id. Its first row is its only `<th>` row and names its columns, and
      each later row has as many `<td>` cells, apart from the `N more` row.
      `batches` names `batch`, `started`, `ended`, `ended because`,
      `budget`, `spent` and `tasks`. `no-batch` and `tasks`, the batch
      page's one table, name `task`, `spec`, `state` and `risk`. `left-out`
      names `task`, `spec` and `reason`. `attempts` names `phase`, `n`,
      `started`, `ended`, `turns` and `cost`. `gate-results` names `phase`,
      `n`, `gate`, `outcome` and `failures`. A failures table names `file`,
      `line`, `code` and `message`, and `findings` names `lens`, `severity`,
      `claim` and `verdict`. The page at `/` holds `batches`, `no-batch` and
      `left-out` in that order. A task page with attempts holds `attempts`,
      `gate-results`, its failures tables and `findings` in that order. The
      witness's task has a failing gate result with failure lines, so a
      failures table exists, and a finding. A task in a state the view
      leaves out fills `left-out`. So every table it reads has a row.
    witness: tests/test_view_server.py::test_every_table_on_every_page_has_a_header_row_naming_its_columns
    wrong_versions:
      - Header rows only on the task page's tables.
      - The header row is made of `<td>` cells.
      - The header row comes last.
      - The batch page's table carries no id.
      - A column is named otherwise, such as `because` for `ended because`.
      - A failures table has no header row.
      - The `left-out` table's header leaves out a column.
  - claim: >-
      The `no-batch` table on `/` and the `tasks` table on a batch page list
      tasks by id as a number, newest first. The `batches` table keeps
      `V1`'s order. The witness drives four unbatched tasks, and three
      batched tasks that share one batch. Each group's ids cross from one
      digit to two, so `V2`'s text order and its reverse both differ from
      newest first. Spec ids run in no order of their own. Three batches
      have a start order that differs from their id order both ways.
    witness: tests/test_view_server.py::test_task_lists_run_newest_first_by_id_as_a_number
    wrong_versions:
      - The `no-batch` table keeps `V5`'s order, which sorts IRIs as text.
      - The batch page keeps `V2`'s order.
      - Each query's order is reversed.
      - Tasks are sorted by id ascending.
      - Tasks are sorted by spec id.
      - Tasks are sorted by id as text.
      - Batches are sorted by id as well.
---

## Context

Backlog item **b-cf50dc**, which cites §6.2.

§6.2 (`DESIGN.md:1317`) gives the view its job. It reads "the view says
why it ended there".

ADR 9's context
(`docs/adr/0009-a-read-only-view-renders-the-run-record-from-the-graph.md:15-17`)
names attempts, gate results and failure lines as where that answer sits.
The final review of `SA-0218` found, on the real ledger, that the task page
cannot say it. `/task/226` ends in `GATE_ERROR` with no attempts, and its
page is a title and an empty table.

Line numbers below were read at `cc3f4622`. That is `SA-0218`'s branch
plus the backlog commits and this spec, and it is the base this spec
builds on.

**What the page does now.** `_render_task`
(`saffron/view/server.py:478-494`) shows the spec id in the title and the
`<h1>`, a pull request link, and one untagged `_table`. That table holds
every row `_gate_result_rows` (`saffron/view/server.py:436-475`) builds
from `V3`. It is a five-cell row per `V3` row, then each failure line as a
four-cell row, then a one-cell `N more` row. The finding rows follow, also
four cells (`saffron/view/server.py:487`). `_task_spec_id_and_pr`
(`saffron/view/server.py:389-406`) reads `V2` bound on `?task`, then `V5`,
and keeps only the spec and the pull request. `_table`
(`saffron/view/server.py:314-320`) writes `<td>` rows alone. It gives a
table an id only when asked. `_render_index`
(`saffron/view/server.py:357-373`) asks for three, and `_render_batch`
(`saffron/view/server.py:376-386`) asks for none.

**What the queries already return.** `V3` selects `?started ?ended ?turns
?cost` per attempt (`ontology/queries/view/V3-task-timeline.rq:8`). It has
one row per gate result, with `?result` unbound for an attempt with none
(`ontology/queries/view/V3-task-timeline.rq:17-22`). It orders by `?task
?started ?n ?gate` (`ontology/queries/view/V3-task-timeline.rq:24`). `V2`
selects `?batch ?state ?risk ?pr`
(`ontology/queries/view/V2-batch-tasks.rq:7`), and `V5` selects `?state
?risk ?pr` (`ontology/queries/view/V5-unbatched-tasks.rq:7`). `V2` orders
by `?batch ?task` (`ontology/queries/view/V2-batch-tasks.rq:22`) and `V5`
by `DESC(?task)` (`ontology/queries/view/V5-unbatched-tasks.rq:20`). Both
compare task IRIs as text, so `task-9` sorts after `task-89`. `V1` orders
by `DESC(?started) ?batch` (`ontology/queries/view/V1-batches.rq:16`).

The graph states a cost as an `xsd:decimal` built from the ledger's
float's `str` (`saffron/view/graph.py:133-136`). It states a time as an
`xsd:dateTime` in UTC (`saffron/view/graph.py:139-143`).

**Real-ledger facts**, measured by the final review on 2026-10-06. There
are 233 tasks, 1,999 attempts and 8,407 gate results. `/task/203` has two
gate results of about 12,400 failure lines each. The `no-batch` list on
`/` runs 99, 98, … 9, 89.

## Problem

1. **The summary.** `_task_spec_id_and_pr` reads one row from `V2` bound
   on `?task`, and falls back to `V5` bound on `?task`. Keep that, and
   keep the row's state, risk, batch and pull request beside its spec.
   Under the `<h1>`, write `<dl id="summary">` with the five terms
   criterion 1 names, each a `<dt>` followed by its `<dd>`. Sum the cost
   over distinct attempts, not over `V3`'s rows. Sum it as `Decimal`, so
   no float noise reaches the page.
2. **The attempts table.** Collapse `V3`'s rows to one per `?attempt`,
   keeping the first row of each in `V3`'s order. With no attempts, write
   the text `no attempts` and stop, with no table after it.
3. **Gate results, failure lines and findings, apart.** The
   `gate-results` table takes the `V3` rows with `?result` bound. Each
   result with failures gets an `<h3>` and its own failures table, read
   from the ledger as `_failure_rows` (`saffron/view/server.py:426-433`)
   reads it now. Keep the cap and the `N more` row, which becomes its
   table's last row. The findings table holds `_finding_rows`
   (`saffron/view/server.py:409-423`) unchanged.
4. **Header rows and ids.** Give `_table` the column names and a
   required id. It writes one `<tr>` of `<th>` cells first. Every table on
   the three pages takes the columns and the id criterion 5 names.
5. **Ordering.** Sort the `V5` rows on `/` and the `V2` rows on a batch
   page by the task id in the IRI. Compare it as a number, highest first.
   `_TASK_IRI` (`saffron/view/server.py:65`) and `_id_from`
   (`saffron/view/server.py:80-82`) parse it already.
   Leave `V1`'s rows as they come.

## Out of scope

- The query files. `ontology/**` is forbidden, and the order is fixed in
  `server.py`.
- The batch page's own window, stop reason and spend, and its tasks' cost
  and pull request. Item b-d269f4 holds those, with rounding the spend on
  `/`, the build time on each page, and an unanchored finding's mark.
- Escaping, the 200-line cap, the 404s, the `Host` check, `/sparql` and
  `POST`. They stay as they are, and their tests stay green.
- A cap on how many gate results get a failures table. `/task/203`'s two
  tables show 200 lines each, as one table did before.

## Notes for the agent

**This change rewrites code whose new spelling no spec can know.** It
edits `_render_index`, `_render_batch`, `_render_task` and `_table`. The
text the edit leaves is yours to choose. So each criterion declares a
witness and no mutant, and the `witness` gate reports `skip` for all six.
The wrong versions under each criterion are what its witness must kill.
Do not run them yourself.

**Commit as each witness passes.** Six witnesses and the updated tests
make seven commits at least. A turn cut by a bound then loses one
witness's work.

**Keep every test name in `tests/test_view_server.py`.** The `census`
gate fails a removed or renamed test. Six existing tests read a page's
untagged table, with `tables.get(None, [])`, and must read the new tables
by id instead. They read it at `tests/test_view_server.py:339`, `:369`,
`:409`, `:498` and `:518`, `:584` and `:607`, and `:1088` and `:1097`.
`_result_blocks` (`tests/test_view_server.py:447-470`) splits rows by
their width, and goes. The capped-lines test then reads each result's
failures table by the id `record_gate_result` returned.
`tests/test_view_server.py:424` asserts `"gate-" not in body`, which the
id `gate-results` now breaks. Assert it over the page's text instead,
leaving out tag attributes, so a leaked gate IRI still fails it. The
left-out test's kept task (`tests/test_view_server.py:310-313`) has one
attempt with no gate result. Its row now sits in the attempts table, with
the start time between the phase and the empty cells.

**The parser.** `_PageParser` (`tests/test_view_server.py:100-156`) keeps
`<td>` rows alone. A
`<th>` row it reads now is an empty row in `tables`, which breaks
`row[0]` in the existing tests. Keep `<th>` rows apart from `tables`.
The witnesses need five more things from it. They are each table's rows
in order with a header flag, and the page's table ids in order. They are
the `<h3>` text before each table, the summary's terms with their text
and any link, and the page's text.

**Fixtures.** Use `_ledger` and `_close`, so ids are offset and no id
equals its position. Set a task's state, risk and pull request with
`_set_task`. Set an attempt's times, turns and cost with a raw `UPDATE`
in the same shape, since `close_attempt` stamps the clock. The ledger
keeps times as `%Y-%m-%d %H:%M:%S`. `V3` returns them as, for example,
`2026-01-02T01:00:00Z`, measured on the host at `cc3f4622`. Pick costs
whose rounding tells the wrong versions apart. `1.234`, `2.004`, `0.459`
and `0.459` sum to `4.156`, which rounds to `4.16`. Truncating gives
`4.15`, and so does rounding each first. Summing distinct values gives
`3.70`. The unbatched task's `0.415` and `0.237` round to `0.65`, and a
total read from `V2` shows nothing there. A batched decoy shows `V2` read
unbound. An unbatched decoy with a higher id shows `V5` read unbound,
since unbound `V5` returns it first. Criterion 6 sets the
batches' `started_at` with a raw `UPDATE` too.

**Batch ids against task ids.** `_ledger` hands out batch ids from 4 and
task ids from 2 (`tests/test_view_server.py:44-77`). So a batch made early
can share its id with a task it links, and a link built from the task id
then passes. In criterion 1's fixture, make spare batches first until the
batch id differs from every task id the fixture makes, and assert that.

**Criterion 1's rounding.** Round half up or half even, as you like. The
witness drives no half-cent sum.

**Criterion 4's order.** Attempts opened in one second tie on
`?started`, and the claim fixes no order among gate results. Compare the
gate-results rows and the failures table ids as sorted lists. `n` counts
within one phase (`saffron/ledger.py:1353-1357`). So the attempt with no
gate result must be a `REPAIRING` one, opened before the `REPAIRING` one
with `lint`. That one's `n` is then 2. Assert each heading's whole text,
so a heading that leaves out `n` fails. Assert that each failing
result's id differs from its attempt's id, so a table id built from the
attempt id cannot match by coincidence.

**Measured on a prototype over `cc3f4622`.** A prototype passed all 24
tests in the file. Each of the six witnesses failed against the base
`server.py`. Each of the 50 wrong versions above was applied to it as an
edit, and each failed its own criterion's witness. Its diff was 2211
changed tokens by the `size` gate, against the `feature` ceiling of 3000.
